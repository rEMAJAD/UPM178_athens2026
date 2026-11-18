"""Porownanie metod z wykladow UPM178 na problemie BTS.

Czesci (python main.py experiments --part ...):
  search_hard - ta sama siatka na instancjach 05-10, model int + dominance
  search   - wszystkie heurystyki wyboru zmiennej x wartosci (Gecode, rozdz. 3)
  restarts - polityki restartow: brak / constant / linear / geometric / luby (rozdz. 3)
  models   - punkty widzenia + dominance breaking + ograniczenie nadmiarowe (rozdz. 2 i 4)
  solvers  - CP (Gecode), LCG (Chuffed, CP-SAT), MIP branch & cut (HiGHS, COIN-BC)
  coverage - wymagane pokrycie 95/98/100% dla wybranych solverow

Kazda proba ma osobny plik JSON; ponowne uruchomienie pomija gotowe proby (wznowienie).
Proby ida rownolegle (--workers), kazda na jednym watku solvera.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import csv
import json
import time
import numpy as np

from .dataset_generator import load_instance, write_instance, coverage, allowed_heights
from .optimization import solve, environment

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/experiments'

VAR_ORDERS = ['input_order', 'first_fail', 'anti_first_fail', 'smallest', 'largest',
              'occurrence', 'most_constrained', 'dom_w_deg']
VALUE_ORDERS = ['indomain_min', 'indomain_max', 'indomain_median', 'indomain_random',
                'indomain_split', 'indomain_reverse_split']
RESTARTS = {
    'none': 'empty_annotation',
    'constant': 'restart_constant(100)',
    'linear': 'restart_linear(100)',
    'geometric': 'restart_geometric(1.5,100)',
    'luby': 'restart_luby(100)',
}
NONE = 'empty_annotation'


def instances(names):
    return [ROOT / 'data' / f'instance_{i:02d}.dzn' for i in names]


def plan(part):
    """Lista prob: dict(id, path, model, solver, search, free)."""
    runs = []

    def add(path, model, solver, var, val, restart='none', free=False, tag=None):
        rid = '__'.join([Path(path).stem, model, solver, 'free' if free else f'{var}-{val}-{restart}'])
        runs.append(dict(id=tag or rid, path=str(path), model=model, solver=solver,
                         search=(var, val, RESTARTS[restart]), restart_name=restart, free=free))

    if part == 'search':
        for path in instances(range(1, 5)):
            for model in ['bool', 'int']:
                for var in VAR_ORDERS:
                    for val in VALUE_ORDERS:
                        add(path, model, 'gecode', var, val)
    elif part == 'search_hard':
        # Na 01-04 model int rozwiazuje prawie kazda heurystyka - tu trudniejsze instancje.
        for path in instances(range(5, 11)):
            for var in VAR_ORDERS:
                for val in VALUE_ORDERS:
                    add(path, 'int_dom', 'gecode', var, val)
    elif part == 'restarts':
        for path in instances(range(1, 11)):
            for model in ['bool', 'int_dom']:
                for var in ['dom_w_deg', 'first_fail']:
                    for restart in RESTARTS:
                        add(path, model, 'gecode', var, 'indomain_random', restart)
    elif part == 'models':
        for path in instances(range(1, 11)):
            for model in ['bool', 'bool_dom', 'int', 'int_dom']:
                add(path, model, 'gecode', 'dom_w_deg', 'indomain_random')
                add(path, model, 'gecode', 'first_fail', 'indomain_min')
    elif part == 'solvers':
        for path in instances(range(1, 11)):
            for model in ['bool', 'int_dom']:
                add(path, model, 'gecode', 'dom_w_deg', 'indomain_random', 'luby')
                add(path, model, 'gecode', 'dom_w_deg', 'indomain_min')  # najlepsza z search_hard
                add(path, model, 'chuffed', 'first_fail', 'indomain_min')
                add(path, model, 'chuffed', 'first_fail', 'indomain_min', free=True)
                add(path, model, 'cp-sat', 'first_fail', 'indomain_min', free=True)
                add(path, model, 'highs', 'input_order', 'indomain_min', free=True)
                add(path, model, 'coin-bc', 'input_order', 'indomain_min', free=True)
    elif part == 'coverage':
        for path in instances([1, 3, 5, 7]):
            for percent in (95, 98, 100):
                meta = dict(load_instance(path), minimum_percent=percent)
                variant = OUT / 'coverage/instances' / f'{Path(path).stem}_p{percent}.dzn'
                if not variant.exists():
                    write_instance(meta, variant)
                for model in ['bool', 'int_dom']:
                    add(variant, model, 'gecode', 'dom_w_deg', 'indomain_random', 'luby')
                    add(variant, model, 'cp-sat', 'first_fail', 'indomain_min', free=True)
                    add(variant, model, 'highs', 'input_order', 'indomain_min', free=True)
    else:
        raise ValueError(f'Unknown part {part}')
    return runs


def run_part(part, seconds, workers=4):
    folder = OUT / part
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'environment.json').write_text(json.dumps(environment(), indent=2) + '\n', encoding='utf-8')
    runs = plan(part)
    todo = [r for r in runs if not (folder / f"{r['id']}.json").exists()]
    print(f'{part}: {len(runs)} prob, do zrobienia {len(todo)}, limit {seconds}s, watki {workers}', flush=True)
    started = time.time()

    def one(r):
        out = folder / f"{r['id']}.json"
        try:
            res = solve(r['path'], seconds=seconds, output=out, model=r['model'], solver=r['solver'],
                        search=r['search'], free=r['free'], strategy='custom')
        except Exception as exc:  # zapisujemy blad zamiast przerywac cala serie
            res = dict(instance=Path(r['path']).stem, model=r['model'], solver=r['solver'],
                       status='ERROR', error=str(exc)[:2000], verified=False, objective=None,
                       limit_seconds=seconds, statistics={})
        res.update(run_id=r['id'], part=part, restart_name=r['restart_name'])
        out.write_text(json.dumps(res, indent=2) + '\n', encoding='utf-8')
        return res

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(one, r) for r in todo]
        for done, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            print(f"[{done}/{len(todo)} {time.time()-started:6.0f}s] {res['run_id']}: "
                  f"{res['status']} cost={res.get('objective')}", flush=True)
    return summarize(part)


STAT_KEYS = ['solveTime', 'flatTime', 'failures', 'nodes', 'propagations', 'restarts', 'peakDepth']
COLUMNS = ['run_id', 'instance', 'n', 'm', 'model', 'solver', 'free_search', 'var_order', 'value_order',
           'restart_name', 'limit_seconds', 'status', 'proven_optimal', 'verified', 'objective',
           'total_runtime', 'time_to_first', 'time_to_best', 'coverage_percent', 'minimum_percent']


def load_part(part):
    rows = []
    for f in sorted((OUT / part).glob('*.json')):
        if f.name == 'environment.json' or f.name.endswith('.solver.json'):
            continue
        r = json.loads(f.read_text(encoding='utf-8'))
        if 'run_id' in r:
            rows.append(r)
    return rows


def summarize(part):
    rows = load_part(part)
    for r in rows:
        if r.get('instance', '').endswith(('_p95', '_p98', '_p100')):
            r['minimum_percent'] = int(r['instance'].rsplit('_p', 1)[1])
    flat = []
    for r in rows:
        row = {k: r.get(k, 'N/A') for k in COLUMNS}
        row.update({k: r.get('statistics', {}).get(k, 'N/A') for k in STAT_KEYS})
        flat.append(row)
    if flat:
        with (OUT / part / f'{part}.csv').open('w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(flat[0]))
            w.writeheader()
            w.writerows(flat)
    errors = [r for r in rows if r['status'] == 'ERROR']
    print(f'{part}: {len(rows)} wynikow, bledow: {len(errors)}')
    return rows


def dominance_stats():
    """Niezalezne (Python) policzenie konfiguracji usuwanych przez dominance breaking."""
    out = []
    for path in instances(range(1, 11)):
        meta = load_instance(path)
        cov = coverage(meta)                      # N,K,P,M
        cost = np.asarray(meta['cost'])
        ok = allowed_heights(meta)                # N,K
        n, k, p, m = cov.shape
        legal = removed = 0
        for i in range(n):
            confs = [(a, b) for a in range(k) for b in range(p) if ok[i, a]]
            legal += len(confs)
            for (a, b) in confs:
                r1 = cov[i, a, b]
                if not r1.any():
                    removed += 1
                    continue
                for (c, d) in confs:
                    if (c, d) == (a, b):
                        continue
                    r2 = cov[i, c, d]
                    if cost[i, c, d] <= cost[i, a, b] and np.all(r1 <= r2) and (
                            cost[i, c, d] < cost[i, a, b] or np.any(r1 != r2) or c * p + d < a * p + b):
                        removed += 1
                        break
        out.append(dict(instance=path.stem, n=n, m=m, legal=legal, removed=removed,
                        kept=legal - removed, removed_percent=100 * removed / legal))
    (OUT).mkdir(parents=True, exist_ok=True)
    with (OUT / 'dominance.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    return out
