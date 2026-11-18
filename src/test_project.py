from dataclasses import asdict
from itertools import product
import json
import math
from pathlib import Path
import numpy as np
import pytest
from src.propagation import Radio, path_loss, received_power, covered, deployment_power, power_matrix
from src.dataset_generator import make_instance, write_instance, load_instance, coverage, grid, required_count, SIZES, allowed_heights
from src.optimization import solve, verify, executable, STRATEGIES


def test_independent_exact_log_reference():
    # f=1000, hb=100, hm=1, d=10: logs are exactly 3,2,1.
    # a(hm)=-1.28; L=69.55+78.48-27.64+1.28+31.8=153.47 dB.
    radio=Radio(frequency_mhz=1000,mobile_height_m=1)
    assert path_loss(10,100,radio)==pytest.approx(153.47,abs=1e-10)
    assert received_power(10,100,radio)==pytest.approx(-97.47,abs=1e-10)


def test_default_reference_scalar_math():
    f,hb,hm,d=900,50,1.5,5
    a=(1.1*math.log10(f)-.7)*hm-(1.56*math.log10(f)-.8)
    expected=69.55+26.16*math.log10(f)-13.82*math.log10(hb)-a+(44.9-6.55*math.log10(hb))*math.log10(d)
    assert path_loss(d,hb)==pytest.approx(expected,abs=1e-10)


def test_height_monotonic_and_distance_clamp():
    distances=np.linspace(1,20,500)
    losses=np.array([path_loss(distances,h) for h in [30,50,80,120,200]])
    assert np.all(np.diff(losses,axis=0)<0)
    assert np.all(np.diff(losses,axis=1)>0)
    assert path_loss(0,30)==path_loss(.5,30)==path_loss(1,30)


def test_coverage_threshold_and_margin():
    assert covered([-85.00001,-85,-84.99999]).tolist()==[False,True,True]
    assert covered(-95,Radio(margin_db=0))
    assert not covered(-95)


@pytest.mark.parametrize('distance,height',[(21,30),(-1,30),(1,29),(1,201),(float('nan'),30)])
def test_invalid_hata(distance,height):
    with pytest.raises(ValueError): path_loss(distance,height)


@pytest.mark.parametrize('kwargs',[{'frequency_mhz':149},{'mobile_height_m':11},{'margin_db':-1}])
def test_invalid_radio(kwargs):
    with pytest.raises(ValueError): Radio(**kwargs)


def test_grid_and_fraction_rounding():
    assert grid(100).shape==(10000,2)
    assert grid(10).min()==0 and grid(10).max()==10
    assert grid(100,True).min()==.05
    assert required_count(98,225)==221
    assert required_count(95,225)==214
    with pytest.raises(ValueError): required_count(101,100)


@pytest.mark.parametrize('n,side',SIZES)
def test_generated_feasible_nontrivial_repeatable(n,side):
    meta=make_instance(n,side,seed=17800+n)
    assert meta==make_instance(n,side,seed=17800+n)
    c=coverage(meta)
    assert c.shape==(n,4,4,side*side+2)
    support = (c & allowed_heights(meta)[:, :, None, None]).any(axis=(1,2)).sum(axis=0)
    assert (support >= 1).all()
    assert (support[meta['critical']] >= 2).all()
    assert c.sum(axis=3).max()<len(meta['points'])
    assert np.all(np.diff(meta['cost'],axis=1)>0)


def test_dzn_shape_order_and_integrity(tmp_path):
    meta=make_instance()
    p=write_instance(meta,tmp_path/'sample.dzn')
    txt=p.read_text()
    flat=txt.split('coverage=array4d(1..N,1..K,1..P,1..M,[')[1].split(']')[0]
    assert np.array_equal(np.fromstring(flat,sep=',',dtype=int).reshape(10,4,4,102),coverage(meta))
    assert load_instance(p)['stations']==meta['stations']
    p.write_text(txt+'\n% edit')
    with pytest.raises(ValueError): load_instance(p)


def tiny_meta(percent=100):
    return dict(n=4,side=3,seed=1,heights=[30,120],stations=[[2,2],[2,8],[8,2],[8,8]],
                points=grid(3).tolist(),cost=[[[100,145],[270,315]],[[120,165],[310,355]],[[110,155],[260,305]],[[150,195],[290,335]]],
                powers=[40,43], min_distance_km=0.0, critical=[False]*9, critical_names=[],
                minimum_percent=percent, max_height=[120]*4, radio=asdict(Radio()))


def brute_force(meta):
    best=None
    for choices in product(range(-1,len(meta['heights'])*len(meta['powers'])),repeat=len(meta['stations'])):
        selected=[(i,k//len(meta['powers']),k%len(meta['powers'])) for i,k in enumerate(choices) if k>=0]
        if any(meta['heights'][k] > meta['max_height'][i] for i,k,p in selected):
            continue
        signals = [deployment_power(meta['stations'],meta['heights'],meta['points'],[choice],Radio(**meta['radio']),meta['powers']) for choice in selected]
        counts = sum((covered(signal).astype(int) for signal in signals), np.zeros(len(meta['points']),dtype=int))
        if np.any(counts[meta['critical']] < 2):
            continue
        p=deployment_power(meta['stations'],meta['heights'],meta['points'],selected,Radio(**meta['radio']),meta['powers'])
        if covered(p).sum()>=required_count(meta['minimum_percent'],len(p)):
            cost=sum(meta['cost'][i][k][p] for i,k,p in selected)
            if best is None or cost<best: best=cost
    return best


@pytest.mark.parametrize('percent',[0,50,95,98,100])
def test_solver_matches_exhaustive_enumeration(tmp_path,percent):
    executable()  # A missing MiniZinc installation is a failing dependency, never a silent skip.
    meta=tiny_meta(percent); p=write_instance(meta,tmp_path/'tiny.dzn')
    result=solve(p,seconds=10)
    assert result['status']=='OPTIMAL_SOLUTION'
    assert result['verified'] and result['objective']==brute_force(meta)


@pytest.mark.parametrize('strategy',STRATEGIES)
def test_annotations_supported(tmp_path,strategy):
    p=write_instance(tiny_meta(),tmp_path/'tiny.dzn')
    result=solve(p,strategy,10)
    assert result['status']=='OPTIMAL_SOLUTION'
    assert not result['stderr']
    assert result['objective']==brute_force(tiny_meta())


def test_verifier_rejects_invalid_results():
    meta=tiny_meta()
    with pytest.raises(ValueError): verify(meta,[0]*16,0)
    with pytest.raises(ValueError): verify(meta,[1]*16,100)
    with pytest.raises(ValueError): verify(meta,[.5]*16,100)
    with pytest.raises(ValueError): verify(meta,[0,0,0,1]*4,1)


def test_unsatisfiable_is_not_reported_as_valid(tmp_path):
    meta=tiny_meta(); meta['stations']=[[0,0]]; meta['cost']=[[[100,145],[200,245]]]; meta['n']=1; meta['max_height']=[120]
    result=solve(write_instance(meta,tmp_path/'impossible.dzn'),seconds=10)
    assert result['status']=='UNSATISFIABLE'
    assert not result['verified'] and result['objective'] is None and not result['timeout']


def test_height_limit_changes_optimum(tmp_path):
    meta = tiny_meta(50)
    unlimited = brute_force(meta)
    meta['max_height'] = [30, 30, 120, 120]
    result = solve(write_instance(meta, tmp_path/'limited.dzn'), seconds=10)
    assert result['proven_optimal']
    assert result['objective'] == brute_force(meta)
    assert result['objective'] > unlimited
    assert all(meta['heights'][k] <= meta['max_height'][i] for i,k,p in result['selected'])


def test_height_limit_can_make_instance_infeasible(tmp_path):
    meta = tiny_meta()
    meta['max_height'] = [29]*4  # zadna z dostepnych anten nie jest dozwolona
    result = solve(write_instance(meta, tmp_path/'limited.dzn'), seconds=10)
    assert result['status'] == 'UNSATISFIABLE'
    with pytest.raises(ValueError, match='height limit'):
        verify(meta, [0,0,0,1]*4, sum(c[1][1] for c in meta['cost']))


def test_height_limit_boundary(tmp_path):
    meta = tiny_meta()
    meta['max_height'] = [120]*4
    result = solve(write_instance(meta, tmp_path/'boundary.dzn'), seconds=10)
    assert result['verified']
    assert any(meta['heights'][k] == meta['max_height'][i] for i,k,p in result['selected'])


def test_power_choice_adds_exact_db_and_cost():
    signal = power_matrix([[0,0]], [50], [[3,0]], powers=[40,43])
    assert signal[0,0,1,0] - signal[0,0,0,0] == pytest.approx(3)
    data = make_instance()
    assert np.all(np.diff(data['cost'],axis=2) > 0)


def test_critical_point_is_mandatory_even_at_zero_percent(tmp_path):
    meta = tiny_meta(0)
    meta['critical'][4] = True  # srodek mapy
    result = solve(write_instance(meta,tmp_path/'critical.dzn'),seconds=10)
    assert result['proven_optimal']
    assert result['objective'] == brute_force(meta)
    assert result['critical_support'][0] >= 2
    assert len({i for i,k,p in result['selected']}) == len(result['selected'])
    # Po awarii dowolnej jednej wybranej stacji wazny punkt nadal ma zasieg.
    for failed in result['selected']:
        remaining = [choice for choice in result['selected'] if choice != failed]
        signal = deployment_power(meta['stations'],meta['heights'],meta['points'],remaining,
                                  Radio(**meta['radio']),meta['powers'])
        assert covered(signal)[4]


def test_two_configurations_of_one_site_cannot_provide_backup(tmp_path):
    meta = tiny_meta(0)
    for key in ['stations','cost','max_height']:
        meta[key] = meta[key][:1]
    meta.update(n=1, points=[[2,2]], critical=[True])
    result = solve(write_instance(meta,tmp_path/'one_site.dzn'),seconds=10)
    assert result['status'] == 'UNSATISFIABLE'
    with pytest.raises(ValueError, match='Critical point'):
        verify(meta,[1,0,0,0],meta['cost'][0][0][0])


def test_candidate_locations_do_not_depend_on_seed():
    assert make_instance(seed=1)['stations'] == make_instance(seed=999)['stations']
    assert make_instance(n=10)['stations'] == make_instance(n=20)['stations'][:10]


def test_station_spacing_and_exact_boundary(tmp_path):
    meta = tiny_meta(0)
    meta.update(n=2, stations=[[5,5],[6,5]], points=[[5,5]], critical=[True],
                cost=meta['cost'][:2], max_height=[120,120], min_distance_km=2.0)
    result = solve(write_instance(meta,tmp_path/'close.dzn'),seconds=10)
    assert result['status'] == 'UNSATISFIABLE'
    with pytest.raises(ValueError, match='minimum distance'):
        verify(meta,[1,0,0,0]*2,meta['cost'][0][0][0]+meta['cost'][1][0][0])
    meta['min_distance_km'] = 1.0
    result = solve(write_instance(meta,tmp_path/'boundary_distance.dzn'),seconds=10)
    assert result['proven_optimal'] and len(result['selected']) == 2
