from dataclasses import asdict
from decimal import Decimal, ROUND_CEILING
from pathlib import Path
import hashlib
import json
import csv
import numpy as np
from .propagation import Radio, power_matrix, covered
from settings import HEIGHTS, MAX_HEIGHTS, DATASET_SIZES, POWERS_DBM, POWER_COST, CRITICAL_POINTS, CRITICAL_NAMES
from settings import CANDIDATE_SITES, MIN_STATION_DISTANCE_KM

SIZES = DATASET_SIZES


def required_count(percent, count):
    p = Decimal(str(percent))
    if not p.is_finite() or not 0 <= p <= 100:
        raise ValueError('Coverage percent must lie in [0,100]')
    return int((p * count / 100).to_integral_value(rounding=ROUND_CEILING))


def grid(side, validation=False):
    if isinstance(side, bool) or int(side) != side or side < 2:
        raise ValueError('Grid side must be an integer >=2')
    # Optimization grids include area boundary; validation samples cell centres.
    a = (np.arange(side) + 0.5) * 10 / side if validation else np.linspace(0, 10, side)
    x, y = np.meshgrid(a, a)
    return np.column_stack((x.ravel(), y.ravel()))


def make_instance(n=10, side=10, seed=17801, percent=100):
    if not 9 <= n <= len(CANDIDATE_SITES):
        raise ValueError('Choose between 9 and the number of sites in CANDIDATE_SITES')
    rng = np.random.default_rng(seed)
    # Wspolrzedne sa ustalone. Seed zmienia tylko koszty, nie polozenie BTS.
    stations = np.asarray(CANDIDATE_SITES[:n], dtype=float)
    if stations.shape != (n,2) or not np.all(np.isfinite(stations)) or np.any((stations < 0) | (stations > 10)):
        raise ValueError('Site coordinates must be finite (x,y) within the 10 x 10 km area')
    base = rng.integers(65,151,size=n)
    # Synthetic integer cost units, with varying local construction premiums.
    costs = base[:,None] + np.array([25,65,130,235])[None,:] * rng.uniform(0.8,1.25,(n,1))
    costs = np.rint(costs).astype(int)[:, :, None] + np.asarray(POWER_COST)[None, None, :]
    limits = [MAX_HEIGHTS[i % len(MAX_HEIGHTS)] for i in range(n)]
    points = grid(side).tolist() + [list(point) for point in CRITICAL_POINTS]
    critical = [False] * (side * side) + [True] * len(CRITICAL_POINTS)
    meta = dict(n=n, side=side, seed=seed, heights=HEIGHTS, max_height=limits, stations=stations.tolist(),
                powers=POWERS_DBM, min_distance_km=MIN_STATION_DISTANCE_KM,
                points=points, critical=critical, critical_names=CRITICAL_NAMES,
                cost=costs.tolist(),
                minimum_percent=percent, radio=asdict(Radio()), coordinate_unit='km', cost_unit='synthetic units')
    cov = coverage(meta)
    needed = required_count(percent, len(points))
    allowed = allowed_heights(meta)
    # Zasiegi rosna z wysokoscia: wystarczy sprawdzic najwyzsza DOZWOLONA
    # antene w kazdej lokalizacji. To test wykonalnosci, nie optymalizacja.
    legal_coverage = cov & allowed[:, :, None, None]
    # Liczymy ROZNE stacje, a nie warianty tej samej stacji.
    # Pierwszych 9 stacji w najwyzszych dozwolonych konfiguracjach jest
    # swiadkiem wykonalnosci tylko wtedy, gdy spelniaja tez odstep.
    if too_close(meta)[:9,:9].any():
        raise ValueError('The nine-site feasibility witness violates spacing; adjust sites/spacing. This is not an UNSAT proof.')
    station_support = legal_coverage[:9].any(axis=(1, 2)).sum(axis=0)
    if (station_support >= 1).sum() < needed or np.any(station_support[critical] < 2):
        raise ValueError('The nine-site witness does not meet coverage; adjust settings. This is not an UNSAT proof.')
    if legal_coverage.sum(axis=3).max() >= needed and needed > 0:
        raise ValueError('Instance is trivial: one station achieves target')
    return meta


def coverage(meta):
    return covered(power_matrix(meta['stations'], meta['heights'], meta['points'], Radio(**meta['radio']), meta['powers']), Radio(**meta['radio']))


def allowed_heights(meta):
    """Tabela: czy wysokosc k jest dozwolona w lokalizacji i?"""
    limits = np.asarray(meta['max_height'])
    if limits.shape != (len(meta['stations']),) or not np.all(np.isfinite(limits)):
        raise ValueError('Provide one finite height limit per site')
    if np.any(limits < 0) or np.any(limits != np.floor(limits)):
        raise ValueError('Height limits must be nonnegative integer metres')
    return np.asarray(meta['heights'])[None, :] <= limits[:, None]


def too_close(meta):
    """Pary kandydatow, ktorych nie wolno jednoczesnie wybrac."""
    minimum = meta['min_distance_km']
    if not np.isfinite(minimum) or minimum < 0:
        raise ValueError('Minimum station distance must be finite and nonnegative')
    sites = np.asarray(meta['stations'])
    distance = np.linalg.norm(sites[:,None,:] - sites[None,:,:], axis=2)
    # Pomijamy przekatna: stacji nie porownujemy z nia sama.
    return (distance < minimum) & ~np.eye(len(sites),dtype=bool)


def write_instance(meta, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cov = coverage(meta)
    allowed_heights(meta)
    n,k,p,m = cov.shape
    if np.asarray(meta['cost']).shape != (n,k,p):
        raise ValueError('Cost must have shape station x height x power')
    if len(meta['critical']) != m or any(type(v) is not bool for v in meta['critical']):
        raise ValueError('Provide one Boolean critical flag per point')
    data = [f'N={n}; M={m}; K={k}; P={p};',
            f'minimum_percent={meta["minimum_percent"]}; required_points={required_count(meta["minimum_percent"],m)};',
            'heights=['+','.join(map(str,meta['heights']))+'];',
            'powers=['+','.join(map(str,meta['powers']))+'];',
            'critical=['+','.join(str(v).lower() for v in meta['critical'])+'];',
            'too_close=array2d(1..N,1..N,['+','.join(str(bool(v)).lower() for v in too_close(meta).ravel())+']);',
            'max_height=['+','.join(str(int(h)) for h in meta['max_height'])+'];',
            'cost=array3d(1..N,1..K,1..P,['+','.join(map(str,np.asarray(meta['cost']).ravel()))+']);',
            'coverage=array4d(1..N,1..K,1..P,1..M,['+','.join(map(str,cov.astype(int).ravel()))+']);']
    path.write_text('\n'.join(data)+'\n', encoding='utf-8')
    meta = dict(meta, dzn_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    path.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n',encoding='utf-8')
    # Mala, czytelna tabela do obejrzenia w edytorze lub Excelu.
    with path.with_name(path.stem + '_sites.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['site', 'x_km', 'y_km', 'max_height_m'] + [f'cost_{h}m_{p}dBm' for h in meta['heights'] for p in meta['powers']])
        for i, (x, y) in enumerate(meta['stations']):
            writer.writerow([i + 1, round(x, 3), round(y, 3), meta['max_height'][i]] + np.asarray(meta['cost'][i]).ravel().tolist())
    return path


def load_instance(path):
    path = Path(path)
    meta = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
    if hashlib.sha256(path.read_bytes()).hexdigest() != meta['dzn_sha256']:
        raise ValueError('DZN changed since generation; regenerate it with its metadata')
    return meta


def generate_all(folder='data', percent=100):
    return [write_instance(make_instance(n,s,17800+i,percent), Path(folder)/f'instance_{i:02d}.dzn')
            for i,(n,s) in enumerate(SIZES,1)]
