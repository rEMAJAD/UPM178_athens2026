"""CLI solver integration, explicit status handling, independent verification."""
from pathlib import Path
import json
import hashlib
import os
import platform
import shutil
import subprocess
import time
import numpy as np
from .dataset_generator import load_instance, coverage, required_count, allowed_heights, too_close

ROOT = Path(__file__).resolve().parents[1]
STRATEGIES = {
    'input_min': ('input_order','indomain_min','empty_annotation'),
    'first_min': ('first_fail','indomain_min','empty_annotation'),
    'first_max': ('first_fail','indomain_max','empty_annotation'),
    'degree_max': ('most_constrained','indomain_max','empty_annotation'),
    'weighted_random': ('dom_w_deg','indomain_random','empty_annotation'),
    'weighted_luby': ('dom_w_deg','indomain_random','restart_luby(100)'),
}


# Warianty modelu (porownanie w eksperymentach). Model bazowy pozostaje bez zmian.
MODELS = {
    'bool': 'src/radio_coverage.mzn',             # zmienne 0/1 x[i,k,p]
    'bool_dom': 'src/radio_coverage_dom.mzn',     # + dominance breaking + implied
    'int': 'src/radio_coverage_int.mzn',          # viewpoint: conf[i] in 0..K*P
    'int_dom': 'src/radio_coverage_int_dom.mzn',  # viewpoint + dominance + implied
}
SOLVERS = {
    'gecode': 'org.gecode.gecode',
    'chuffed': 'org.chuffed.chuffed',
    'cp-sat': 'cp-sat',
    'highs': 'org.minizinc.mip.highs',
    'coin-bc': 'org.minizinc.mip.coin-bc',
}
MAC_MINIZINC = '/Applications/MiniZincIDE.app/Contents/Resources/minizinc'


def executable():
    exe = os.environ.get('MINIZINC') or shutil.which('minizinc')
    if not exe and Path('C:/Program Files/MiniZinc/minizinc.exe').exists():
        exe = 'C:/Program Files/MiniZinc/minizinc.exe'
    if not exe and Path(MAC_MINIZINC).exists():
        exe = MAC_MINIZINC
    if not exe:
        raise RuntimeError('Install MiniZinc with Gecode and add it to PATH or set MINIZINC')
    return exe


def environment():
    return dict(platform=platform.platform(), processor=platform.processor(), python=platform.python_version(),
                numpy=np.__version__, cpu_count=os.cpu_count(),
                minizinc=subprocess.check_output([executable(),'--version'],text=True).strip(),
                solvers=subprocess.check_output([executable(),'--solvers'],text=True).strip())


def verify(meta, x, objective):
    raw = np.asarray(x)
    n,k,p = len(meta['stations']),len(meta['heights']),len(meta['powers'])
    if raw.size != n*k*p or not np.all((raw == 0) | (raw == 1)):
        raise ValueError('Invalid deployment domain or shape')
    x = raw.astype(int).reshape(n,k,p)
    if np.any(x.sum(axis=(1,2))>1):
        raise ValueError('Multiple height/power configurations at one site')
    if np.any(x.astype(bool) & ~allowed_heights(meta)[:, :, None]):
        raise ValueError('Selected antenna exceeds site height limit')
    active = x.any(axis=(1,2))
    if np.any(too_close(meta) & active[:,None] & active[None,:]):
        raise ValueError('Selected stations violate minimum distance')
    links = (coverage(meta) & x[:,:,:,None].astype(bool)).sum(axis=(0,1,2))
    mask = links >= 1
    if np.any(links[np.asarray(meta['critical'])] < 2):
        raise ValueError('Critical point needs coverage from two different stations')
    if mask.sum() < required_count(meta['minimum_percent'],len(mask)):
        raise ValueError('Coverage constraint violated')
    if int((np.asarray(meta['cost'])*x).sum()) != objective:
        raise ValueError('Objective does not match selected costs')
    return dict(selected=np.argwhere(x).tolist(), critical_support=links[np.asarray(meta['critical'])].tolist(), covered_points=int(mask.sum()),
                coverage_percent=100*float(mask.mean()), verified=True)


def solve(path, strategy='weighted_random', seconds=900, output=None,
          model='bool', solver='gecode', search=None, free=False):
    """strategy: nazwa z STRATEGIES albo search=(var, val, restart) podane wprost.
    free=True: solver uzywa wlasnego przeszukiwania (Chuffed/CP-SAT -f, MIP i tak ignoruje)."""
    if seconds <= 0 or not np.isfinite(seconds):
        raise ValueError('Time limit must be positive and finite')
    path = Path(path).resolve()
    meta = load_instance(path)
    var,val,restart = search or STRATEGIES[strategy]
    model_path = ROOT/MODELS[model]
    mip = solver in ('highs','coin-bc')
    cmd = [executable(),'--solver',SOLVERS[solver],'--json-stream','--statistics',
           '--intermediate-solutions','--output-time','--time-limit',str(max(1,int(seconds*1000)))]
    if solver == 'gecode':
        cmd += ['--fzn-flags','-r 178 -p 1']
    elif solver == 'chuffed':
        cmd += ['-r','178'] + (['-f'] if free else [])
    elif solver == 'cp-sat':
        cmd += ['-p','1','-r','178'] + (['-f'] if free else [])
    else:
        cmd += ['-p','1']
    cmd += ['-D',f'variable_order={var};value_order={val};restart_policy={restart};',
            str(model_path),str(path)]
    started = time.perf_counter()
    proc = subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8')
    elapsed = time.perf_counter()-started
    statistics, messages, solution, status, trajectory = {}, [], None, None, []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        msg = json.loads(line)
        kind = msg.get('type')
        if kind == 'statistics': statistics.update(msg['statistics'])
        elif kind == 'solution':
            solution = json.loads(msg['output']['default'])
            # Przebieg branch & bound: [czas od startu w s, koszt] dla kolejnych rozwiazan.
            trajectory.append([msg.get('time', 0) / 1000, solution['objective']])
        elif kind == 'status': status = msg['status']
        else: messages.append(msg)
    errors = [m for m in messages if m.get('type') == 'error']
    unsupported = [m for m in messages if 'ignored' in str(m).lower() or 'unsupported' in str(m).lower()]
    # Solvery MIP z natury ignoruja adnotacje przeszukiwania; przy free search tez je pomijamy.
    tolerant = mip or free
    if proc.returncode or errors or (not tolerant and (unsupported or any(w in proc.stderr.lower() for w in ('ignored','unsupported')))):
        raise RuntimeError(f'MiniZinc failed or ignored annotation: {messages}\n{proc.stderr}')
    # MiniZinc may omit a status when it has an incumbent but hits the limit.
    status = status or ('SATISFIED' if solution else 'UNKNOWN')
    terminal = status in ('OPTIMAL_SOLUTION','UNSATISFIABLE','ALL_SOLUTIONS')
    result = dict(instance=path.stem, n=len(meta['stations']), m=len(meta['points']), strategy=strategy,
                  model=model, solver=solver, free_search=free, var_order=var, value_order=val, restart=restart,
                  seed=178, threads=1, limit_seconds=seconds,
                  total_runtime=elapsed, status=status, proven_optimal=status=='OPTIMAL_SOLUTION',
                  timeout=not terminal, objective=None, verified=False, statistics=statistics,
                  trajectory=trajectory,
                  time_to_first=trajectory[0][0] if trajectory else None,
                  time_to_best=trajectory[-1][0] if trajectory else None,
                  messages=messages, stderr=proc.stderr.replace(str(ROOT)+os.sep, ''),
                  # sciezki wzgledem projektu - bez nazwy uzytkownika w zapisanych wynikach
                  command=[c.replace(str(ROOT)+os.sep, '') for c in cmd],
                  instance_sha256=meta['dzn_sha256'],
                  model_sha256=hashlib.sha256(model_path.read_bytes()).hexdigest())
    if solution:
        result.update(solution)
        result.update(verify(meta,solution['x'],solution['objective']))
    if output:
        output=Path(output); output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        output.with_suffix('.solver.jsonl').write_text(proc.stdout,encoding='utf-8')
    return result

