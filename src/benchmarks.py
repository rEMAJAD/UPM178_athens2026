from pathlib import Path
import csv
import json
import numpy as np
from .dataset_generator import make_instance, write_instance, load_instance, grid
from .optimization import solve, STRATEGIES, environment
from .propagation import Radio, covered, deployment_power
from .visualization import benchmark_plots, accuracy_plot, save_plot

STATS=['solveTime','flatTime','initTime','failures','nodes','propagations','propagators','nogoods','restarts','peakDepth']


def save_results(rows, folder, name):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    (folder/f'{name}.json').write_text(json.dumps(rows,indent=2)+'\n',encoding='utf-8')
    flat=[]
    for r in rows:
        row={k:r.get(k,'N/A') for k in ['instance','n','m','strategy','limit_seconds','total_runtime','status','timeout','proven_optimal','verified','objective','coverage_percent','validation_percent','minimum_percent']}
        row.update({s:r['statistics'].get(s,'N/A') for s in STATS})
        flat.append(row)
    if flat:
        with (folder/f'{name}.csv').open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(flat[0])); writer.writeheader(); writer.writerows(flat)


def benchmark(paths, folder='results/benchmark', seconds=900, strategies=None):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    (folder/'environment.json').write_text(json.dumps(environment(),indent=2)+'\n',encoding='utf-8')
    rows=[]
    for path in paths:
        for strategy in strategies or STRATEGIES:
            r=solve(path,strategy,seconds,folder/f'{Path(path).stem}_{strategy}.json')
            rows.append(r); save_results(rows,folder,'benchmark')
            print(f'{r["instance"]} {strategy}: {r["status"]}, cost={r["objective"]}',flush=True)
    benchmark_plots(rows,folder)
    return rows


def accuracy(folder='results/accuracy', seconds=900, sizes=(10,20,30,50), n=20, seed=17803, strategy='weighted_random'):
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    (folder/'environment.json').write_text(json.dumps(environment(),indent=2)+'\n',encoding='utf-8')
    rows=[]
    for side in sizes:
        meta=make_instance(n,side,seed,100)
        path=write_instance(meta,folder/'instances'/f'grid_{side}.dzn')
        r=solve(path,strategy=strategy,seconds=seconds,output=folder/f'grid_{side}.json')
        if r['verified']:
            power=deployment_power(meta['stations'],meta['heights'],grid(100,True),r['selected'],Radio(**meta['radio']),meta['powers'])
            r['validation_percent']=100*float(covered(power,Radio(**meta['radio'])).mean())
        (folder/f'grid_{side}.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
        rows.append(r); save_results(rows,folder,'accuracy')
        print(f'{side}x{side}: {r["status"]}, cost={r["objective"]}, validation={r.get("validation_percent")}',flush=True)
    accuracy_plot(rows,folder/'accuracy.png')
    return rows


def coverage_sweep(path, folder='results/coverage_sweep', seconds=900, percentages=(95,98,100)):
    import matplotlib.pyplot as plt
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    (folder/'environment.json').write_text(json.dumps(environment(),indent=2)+'\n',encoding='utf-8')
    meta=load_instance(path); rows=[]
    for percent in percentages:
        meta=dict(meta,minimum_percent=percent)
        p=write_instance(meta,folder/'instances'/f'coverage_{percent}.dzn')
        r=solve(p,seconds=seconds,output=folder/f'coverage_{percent}.json')
        r['minimum_percent']=percent; rows.append(r)
        print(f'{percent}%: {r["status"]}, cost={r["objective"]}',flush=True)
    save_results(rows,folder,'coverage_sweep')
    fig,ax=plt.subplots(figsize=(6,4))
    valid=[r for r in rows if r['verified']]
    ax.plot([r['minimum_percent'] for r in valid],[r['objective'] for r in valid],'o-')
    ax.set(xlabel='Required sample coverage (%)',ylabel='Deployment cost (units)',title='Cost versus coverage (see CSV for proof status)')
    fig.tight_layout(); save_plot(fig, folder/'coverage_sweep.png',dpi=160); plt.close(fig)
    return rows
