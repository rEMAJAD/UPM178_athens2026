from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from .dataset_generator import grid
from .propagation import Radio, deployment_power, covered


def save_plot(fig, path, **options):
    """Zapis przez nowy plik pomaga przy nadpisywaniu PNG w OneDrive."""
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    fig.savefig(temporary, format='png', **options)
    temporary.replace(path)


def deployment_plots(meta, result, folder):
    if not result.get('verified'):
        raise ValueError('Cannot plot an unverified solution')
    folder=Path(folder); folder.mkdir(parents=True,exist_ok=True)
    stations, points = np.asarray(meta['stations']),np.asarray(meta['points'])
    heights, selected, radio = meta['heights'],result['selected'],Radio(**meta['radio'])
    fig,ax=plt.subplots(figsize=(7,6))
    p=deployment_power(stations,heights,points,selected,radio,meta['powers'])
    mask=covered(p,radio)
    ax.scatter(*points[mask].T,s=5,c='#a3ceb7',label='Covered sample')
    if (~mask).any(): ax.scatter(*points[~mask].T,s=12,c='#e34b4b',label='Uncovered sample')
    critical_points = points[np.asarray(meta['critical'])]
    if len(critical_points): ax.scatter(*critical_points.T,marker='*',s=150,c='red',label='Critical: 2 stations')
    ax.scatter(*stations.T,c='gray',marker='x',s=35,label='Candidate site')
    for k,h in enumerate(heights):
        ids=[i for i,j,p in selected if j==k]
        if ids: ax.scatter(*stations[ids].T,marker=['o','s','^','D'][k%4],s=100,label=f'Selected: {h} m',edgecolor='black')
    for i,k,p in selected: ax.annotate(str(i+1),stations[i],xytext=(6,6),textcoords='offset points')
    ax.set(xlim=(0,10),ylim=(0,10),xlabel='East (km)',ylabel='North (km)',
           title=f'Deployment | cost {result["objective"]} | {result["status"]}')
    ax.set_aspect('equal'); ax.legend(fontsize=8,loc='upper left',bbox_to_anchor=(1,1))
    save_plot(fig, folder/'deployment.png',dpi=160,bbox_inches='tight'); plt.close(fig)
    dense=grid(100,validation=True)
    power=deployment_power(stations,heights,dense,selected,radio,meta['powers']).reshape(100,100)
    fig,ax=plt.subplots(figsize=(7,6))
    im=ax.imshow(np.maximum(power,-120),origin='lower',extent=(0,10,0,10),vmin=-105,vmax=-65,cmap='viridis')
    if np.any(power<radio.threshold_dbm):
        a=(np.arange(100)+.5)/10
        ax.contourf(a,a,power<radio.threshold_dbm,levels=[.5,1.5],colors='none',hatches=['////'])
    for i,k,p in selected:
        ax.plot(*stations[i],marker='^',color='white',markeredgecolor='black')
        right_edge = stations[i,0] > 7
        ax.annotate(f'{i+1}: {heights[k]}m / {meta["powers"][p]}dBm', stations[i],
                    xytext=(-6 if right_edge else 6,5), textcoords='offset points',
                    ha='right' if right_edge else 'left', color='white', fontsize=8)
    if len(critical_points):
        ax.scatter(*critical_points.T,marker='*',s=120,c='red',edgecolor='white')
        for point,name in zip(critical_points,meta['critical_names']):
            ax.annotate(name,point,xytext=(5,5),textcoords='offset points',fontsize=8,color='white')
    fig.colorbar(im,ax=ax,label='Best serving received power (dBm)')
    ax.set(xlabel='East (km)',ylabel='North (km)',title=f'100 x 100 validation grid | threshold {radio.threshold_dbm:g} dBm\nHatching: uncovered; d < 1 km clamped to 1 km')
    save_plot(fig, folder/'heatmap.png',dpi=160,bbox_inches='tight'); plt.close(fig)
    # Radiowe odniesienie: wszystkie lokalizacje; celowo pomija odstep.
    # To nie jest dopuszczalny projekt sieci, tylko gorna referencja zasiegu.
    baseline=[]
    for i in range(len(stations)):
        legal=[k for k,h in enumerate(heights) if h <= meta['max_height'][i]]
        if legal:
            baseline.append((i,legal[-1],len(meta['powers'])-1))
    before=covered(deployment_power(stations,heights,dense,baseline,radio,meta['powers']),radio).mean()*100
    after=covered(power,radio).mean()*100
    fig,axes=plt.subplots(1,3,figsize=(12,3.7))
    axes[0].bar(['All sites (no spacing)','CP deployment'],[before,after],color=['gray','#277c8e'])
    axes[0].set(ylabel='Validation-grid coverage (%)',ylim=(0,105),title='Explicit baseline comparison')
    axes[1].bar([str(h) for h in heights],[sum(j==k for i,j,p in selected) for k in range(len(heights))])
    axes[1].set(xlabel='Selected antenna height (m)',ylabel='Number of stations')
    axes[2].bar([str(power) for power in meta['powers']],
                [sum(p==q for i,k,p in selected) for q in range(len(meta['powers']))])
    axes[2].set(xlabel='Selected transmitter power (dBm)',ylabel='Number of stations')
    fig.tight_layout(); save_plot(fig, folder/'comparison.png',dpi=160); plt.close(fig)


def benchmark_plots(rows, folder):
    folder=Path(folder)
    fig,axes=plt.subplots(1,2,figsize=(11,4))
    for strategy in dict.fromkeys(r['strategy'] for r in rows):
        rs=[r for r in rows if r['strategy']==strategy]
        axes[0].plot([r['m'] for r in rs],[r['total_runtime'] for r in rs],'.-',label=strategy)
        axes[1].plot([int(r['instance'].split('_')[-1]) for r in rs],
                     [r['statistics'].get('failures',np.nan) for r in rs],'.-',label=strategy)
    axes[0].set(xlabel='Measurement points',ylabel='MiniZinc wall time (s)',title='Includes compilation; capped runs included')
    axes[1].set(xlabel='Dataset',ylabel='Failures (log scale)',yscale='log',title='Failures within the same time budget')
    axes[1].legend(fontsize=7)
    fig.tight_layout(); save_plot(fig, folder/'benchmarks.png',dpi=160); plt.close(fig)


def accuracy_plot(rows, path):
    valid=[r for r in rows if r.get('verified')]
    fig,axes=plt.subplots(1,3,figsize=(12,3.5))
    x=[r['m'] for r in valid]
    axes[0].plot(x,[r['objective'] for r in valid],'o-'); axes[0].set(ylabel='Deployment cost (units)')
    axes[1].plot(x,[r['coverage_percent'] for r in valid],'o-',label='Optimization grid')
    axes[1].plot(x,[r['validation_percent'] for r in valid],'s-',label='Independent 100 x 100 grid')
    axes[1].set(ylabel='Covered points (%)'); axes[1].legend(fontsize=7)
    axes[2].plot(x,[r['total_runtime'] for r in valid],'o-'); axes[2].set(ylabel='MiniZinc wall time (s)')
    for ax in axes: ax.set_xlabel('Optimization measurement points')
    proof='all costs proven optimal' if valid and all(r['proven_optimal'] for r in valid) else 'includes time-limited incumbents'
    fig.suptitle(f'Grid accuracy study: same candidate sites and costs; {proof}')
    fig.tight_layout(); save_plot(fig, path,dpi=160); plt.close(fig)
