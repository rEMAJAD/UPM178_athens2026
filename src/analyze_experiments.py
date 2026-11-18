"""Analiza wynikow z results/experiments: tabele, wykresy, SUMMARY.md.

Uruchom: python -B src/analyze_experiments.py
Miary:
  opt   - liczba prob z udowodnionym optimum (OPTIMAL_SOLUTION),
  gap   - (koszt - najlepszy znany) / najlepszy znany * 100 % na koniec limitu,
  czas  - czas do dowodu optimum; proba bez dowodu liczona jako limit czasu,
  brak  - liczba prob bez zadnego poprawnego rozwiazania.
Najlepszy znany koszt instancji = minimum ze wszystkich zweryfikowanych prob.
"""
from collections import defaultdict
from pathlib import Path
import json
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.experiments import OUT, load_part, VAR_ORDERS, VALUE_ORDERS, RESTARTS

# Paleta kategoryczna (stala kolejnosc, sprawdzona pod katem daltonizmu) + rampa sekwencyjna.
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#6250d6', '#e34948']
BLUES = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']
INK, INK2, GRID = '#0b0b0b', '#52514e', '#e4e3df'
PARTS = ['models', 'solvers', 'search', 'search_hard', 'restarts', 'coverage']

plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
                     'ytick.color': INK2, 'axes.grid': True, 'grid.color': GRID, 'grid.linewidth': 0.6,
                     'axes.spines.top': False, 'axes.spines.right': False, 'legend.frameon': False,
                     'lines.linewidth': 2, 'figure.dpi': 110})

MODEL_LABEL = {'bool': '0/1 (bazowy)', 'bool_dom': '0/1 + dominance', 'int': 'int viewpoint',
               'int_dom': 'int + dominance'}


def solver_label(r):
    s = r['solver']
    if s in ('highs', 'coin-bc'):
        return {'highs': 'HiGHS (MIP)', 'coin-bc': 'COIN-BC (MIP)'}[s]
    if r.get('free_search'):
        return {'chuffed': 'Chuffed (free search)', 'cp-sat': 'CP-SAT (free search)'}[s]
    if s == 'gecode':
        return 'Gecode (dom_w_deg+min)' if r.get('value_order') == 'indomain_min' else 'Gecode (dom_w_deg+random+luby)'
    return {'chuffed': 'Chuffed (first_fail)'}.get(s, s)


def load_all():
    data = {p: load_part(p) for p in PARTS if (OUT / p).exists()}
    best, proven = {}, defaultdict(bool)
    for rows in data.values():
        for r in rows:
            if r.get('verified') and r.get('objective') is not None:
                best[r['instance']] = min(best.get(r['instance'], 1e18), r['objective'])
            if r.get('proven_optimal'):
                proven[r['instance']] = True
    # Spojnosc: wszystkie udowodnione optima tej samej instancji musza byc rowne.
    for rows in data.values():
        for r in rows:
            if r.get('proven_optimal'):
                assert r['objective'] == best[r['instance']], f"Sprzeczne optimum: {r['run_id']}"
    for rows in data.values():
        for r in rows:
            b = best.get(r['instance'])
            r['gap'] = 100 * (r['objective'] - b) / b if r.get('verified') and b else np.nan
            lim = r.get('limit_seconds') or 0
            r['time'] = r['total_runtime'] if r.get('proven_optimal') else lim
    return data, best, proven


def agg(rows):
    gaps = [r['gap'] for r in rows if not np.isnan(r['gap'])]
    return dict(runs=len(rows), opt=sum(bool(r.get('proven_optimal')) for r in rows),
                nosol=sum(not r.get('verified') for r in rows),
                gap=float(np.mean(gaps)) if gaps else np.nan,
                time=float(np.mean([r['time'] for r in rows])) if rows else np.nan,
                errors=sum(r['status'] == 'ERROR' for r in rows))


def fmt(v, d=1):
    return 'N/A' if v is None or (isinstance(v, float) and np.isnan(v)) else f'{v:.{d}f}'


def table(header, rows):
    out = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    out += ['| ' + ' | '.join(map(str, r)) + ' |' for r in rows]
    return '\n'.join(out)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=160, facecolor='white')
    plt.close(fig)


def inst_no(name):
    return int(name.split('_')[1])


# ---------------------------------------------------------------- czesci

def part_models(rows, md):
    groups = defaultdict(list)
    for r in rows:
        groups[(r['model'], r['var_order'])].append(r)
    md.append('## Warianty modelu (Gecode, limit 60 s)\n')
    md.append('Punkt widzenia 0/1 vs. calkowitoliczbowy, dominance breaking + ograniczenie nadmiarowe. '
              'Dwie strategie: `dom_w_deg/indomain_random` i `first_fail/indomain_min`.\n')
    md.append(table(['model', 'strategia', 'optimum (z 10)', 'brak rozw.', 'sredni gap %', 'sredni czas s'],
                    [[MODEL_LABEL[m], v, a['opt'], a['nosol'], fmt(a['gap'], 2), fmt(a['time'])]
                     for (m, v), g in sorted(groups.items()) for a in [agg(g)]]) + '\n')
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, var in zip(axes, ['dom_w_deg', 'first_fail']):
        for c, model in enumerate(['bool', 'bool_dom', 'int', 'int_dom']):
            g = sorted([r for r in rows if r['model'] == model and r['var_order'] == var],
                       key=lambda r: inst_no(r['instance']))
            xs = [inst_no(r['instance']) for r in g]
            ax.plot(xs, [r['time'] for r in g], '-', color=SERIES[c], label=MODEL_LABEL[model])
            ax.scatter([x for x, r in zip(xs, g) if r.get('proven_optimal')],
                       [r['time'] for r in g if r.get('proven_optimal')], s=28, color=SERIES[c], zorder=3,
                       edgecolor='white', linewidth=1.5)
            ax.scatter([x for x, r in zip(xs, g) if not r.get('proven_optimal')],
                       [r['time'] for r in g if not r.get('proven_optimal')], s=28, facecolor='white',
                       edgecolor=SERIES[c], linewidth=1.5, zorder=3)
        ax.set(yscale='log', xlabel='instancja', title=f'strategia {var}', xticks=range(1, 11))
    axes[0].set_ylabel('czas do dowodu optimum [s]\n(puste kolko = brak dowodu w limicie)')
    axes[1].legend(loc='lower right')
    save(fig, 'models.png')


def part_solvers(rows, md):
    groups = defaultdict(list)
    for r in rows:
        groups[(solver_label(r), r['model'])].append(r)
    md.append('## Solvery (limit 60 s, 1 watek)\n')
    md.append('Gecode = klasyczne CP (propagacja + przeszukiwanie z nawrotami, branch & bound). '
              'Chuffed i CP-SAT = lazy clause generation (uczenie sie klauzul z porazek). '
              'HiGHS i COIN-BC = MIP (relaksacja LP + branch & cut).\n')
    md.append(table(['solver', 'model', 'optimum (z 10)', 'brak rozw.', 'sredni gap %', 'sredni czas s'],
                    [[s, MODEL_LABEL[m], a['opt'], a['nosol'], fmt(a['gap'], 2), fmt(a['time'])]
                     for (s, m), g in sorted(groups.items()) for a in [agg(g)]]) + '\n')
    labels = sorted({solver_label(r) for r in rows})
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
    for ax, model in zip(axes, ['bool', 'int_dom']):
        for c, lab in enumerate(labels):
            g = sorted([r for r in rows if r['model'] == model and solver_label(r) == lab],
                       key=lambda r: inst_no(r['instance']))
            xs = [inst_no(r['instance']) for r in g]
            ax.plot(xs, [r['time'] for r in g], '-', color=SERIES[c], label=lab)
            for x, r in zip(xs, g):
                ax.scatter([x], [r['time']], s=24, zorder=3, linewidth=1.5,
                           facecolor=SERIES[c] if r.get('proven_optimal') else 'white',
                           edgecolor='white' if r.get('proven_optimal') else SERIES[c])
        ax.set(yscale='log', xlabel='instancja', title=f'model: {MODEL_LABEL[model]}', xticks=range(1, 11))
    axes[0].set_ylabel('czas do dowodu optimum [s]\n(puste kolko = brak dowodu w limicie)')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3, fontsize=8)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.savefig(OUT / 'solvers.png', dpi=160, facecolor='white'); plt.close(fig)
    # Przebieg branch & bound na najwiekszej instancji.
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, model in zip(axes, ['bool', 'int_dom']):
        for c, lab in enumerate(labels):
            g = [r for r in rows if r['model'] == model and solver_label(r) == lab and r['instance'] == 'instance_10']
            if g and g[0].get('trajectory'):
                t = np.array(g[0]['trajectory'])
                ax.step(np.r_[t[:, 0], g[0]['total_runtime']], np.r_[t[:, 1], t[-1, 1]], where='post',
                        color=SERIES[c], label=lab)
        ax.set(xlabel='czas [s]', title=f'instance_10 (60 BTS, 2502 pkt), {MODEL_LABEL[model]}')
    axes[0].set_ylabel('koszt najlepszego rozwiazania')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=3, fontsize=8)
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    fig.savefig(OUT / 'bnb_trajectory.png', dpi=160, facecolor='white'); plt.close(fig)


def part_search(rows, md):
    md.append('## Heurystyki przeszukiwania (Gecode, instancje 01-04, limit 20 s, bez restartow)\n')
    md.append('8 heurystyk wyboru zmiennej x 6 wyboru wartosci, w obu punktach widzenia. '
              'Komorka: sredni gap % / liczba udowodnionych optimow (z 4).\n')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))
    for ax, model in zip(axes, ['bool', 'int']):
        M = np.full((len(VAR_ORDERS), len(VALUE_ORDERS)), np.nan)
        lines = []
        for a, var in enumerate(VAR_ORDERS):
            row = [var]
            for b, val in enumerate(VALUE_ORDERS):
                g = [r for r in rows if r['model'] == model and r['var_order'] == var and r['value_order'] == val]
                s = agg(g)
                # brak rozwiazania karzemy gapem 100 %, zeby nie wygladal jak dobry wynik
                M[a, b] = np.mean([100 if np.isnan(r['gap']) else r['gap'] for r in g]) if g else np.nan
                ax.text(b, a, f"{fmt(M[a, b])}\n{s['opt']}/4", ha='center', va='center', fontsize=6.8,
                        color='white' if M[a, b] > 6 else INK)
                row.append(f"{fmt(M[a, b], 2)} / {s['opt']}")
            lines.append(row)
        cmap = matplotlib.colors.LinearSegmentedColormap.from_list('b', BLUES)
        ax.imshow(M, cmap=cmap, vmin=0, vmax=max(10, np.nanmax(M)), aspect='auto')
        ax.set_xticks(range(len(VALUE_ORDERS)), [v.replace('indomain_', '') for v in VALUE_ORDERS], rotation=30)
        ax.set_yticks(range(len(VAR_ORDERS)), VAR_ORDERS)
        ax.grid(False)
        ax.set_title(f'model {MODEL_LABEL[model]} - sredni gap % (brak rozw. = 100)')
        md.append(f'### {MODEL_LABEL[model]}\n')
        md.append(table(['zmienna \\ wartosc'] + VALUE_ORDERS, lines) + '\n')
    save(fig, 'search_heatmap.png')


def part_search_hard(rows, md):
    md.append('## Heurystyki na trudniejszych instancjach (Gecode, int + dominance, 05-10, limit 30 s)\n')
    md.append('Komorka: liczba udowodnionych optimow (z 6) / sredni czas s (bez dowodu = limit) / sredni gap %.\n')
    T = np.full((len(VAR_ORDERS), len(VALUE_ORDERS)), np.nan)
    lines, ranking = [], []
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for a, var in enumerate(VAR_ORDERS):
        row = [var]
        for b, val in enumerate(VALUE_ORDERS):
            g = [r for r in rows if r['var_order'] == var and r['value_order'] == val]
            s = agg(g)
            T[a, b] = s['time']
            ax.text(b, a, f"{s['opt']}/6\n{fmt(s['time'], 0)} s", ha='center', va='center', fontsize=7,
                    color='white' if s['time'] > 18 else INK)
            row.append(f"{s['opt']} / {fmt(s['time'])} / {fmt(s['gap'], 2)}")
            ranking.append((-s['opt'], s['time'], var, val, s))
        lines.append(row)
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list('b', BLUES)
    ax.imshow(T, cmap=cmap, vmin=0, vmax=30, aspect='auto')
    ax.set_xticks(range(len(VALUE_ORDERS)), [v.replace('indomain_', '') for v in VALUE_ORDERS], rotation=30)
    ax.set_yticks(range(len(VAR_ORDERS)), VAR_ORDERS)
    ax.grid(False)
    ax.set_title('Gecode, int + dominance, instancje 05-10: optima/6 i sredni czas')
    save(fig, 'search_hard_heatmap.png')
    md.append(table(['zmienna \\ wartosc'] + VALUE_ORDERS, lines) + '\n')
    md.append('Ranking (najwiecej optimow, potem najkrotszy czas):\n')
    md.append(table(['#', 'zmienna', 'wartosc', 'optimum (z 6)', 'sredni czas s', 'sredni gap %'],
                    [[i + 1, v, w, s['opt'], fmt(s['time']), fmt(s['gap'], 2)]
                     for i, (_, _, v, w, s) in enumerate(sorted(ranking, key=lambda t: t[:2])[:10])]) + '\n')


def part_restarts(rows, md):
    md.append('## Restarty (Gecode, indomain_random, limit 30 s)\n')
    groups = defaultdict(list)
    for r in rows:
        groups[(r['model'], r['var_order'], r['restart_name'])].append(r)
    md.append(table(['model', 'zmienna', 'restart', 'optimum (z 10)', 'brak rozw.', 'sredni gap %', 'sredni czas s'],
                    [[MODEL_LABEL[m], v, rs, a['opt'], a['nosol'], fmt(a['gap'], 2), fmt(a['time'])]
                     for (m, v, rs), g in sorted(groups.items()) for a in [agg(g)]]) + '\n')
    combos = [('bool', 'dom_w_deg'), ('bool', 'first_fail'), ('int_dom', 'dom_w_deg'), ('int_dom', 'first_fail')]
    names = list(RESTARTS)
    fig, ax = plt.subplots(figsize=(9, 3.6))
    w = 0.8 / len(combos)
    for c, (m, v) in enumerate(combos):
        vals = [agg(groups[(m, v, rs)])['gap'] for rs in names]
        xs = np.arange(len(names)) + (c - 1.5) * w
        ax.bar(xs, vals, width=w - 0.03, color=SERIES[c], label=f'{MODEL_LABEL[m]}, {v}')
        for x, rs, val in zip(xs, names, vals):
            ax.text(x, (0 if np.isnan(val) else val) + 0.05, str(agg(groups[(m, v, rs)])['opt']),
                    ha='center', va='bottom', fontsize=7, color=INK2)
    ax.set_xticks(range(len(names)), names)
    ax.set(ylabel='sredni gap % (nad slupkiem: liczba optimow z 10)', title='Polityki restartow')
    ax.legend(fontsize=7.5)
    save(fig, 'restarts.png')


def part_coverage(rows, md):
    md.append('## Wymagane pokrycie 95 / 98 / 100 %\n')
    groups = defaultdict(list)
    for r in rows:
        base, p = r['instance'].rsplit('_p', 1)
        r['percent'], r['base'] = int(p), base
        groups[(base, int(p))].append(r)
    lines = []
    for (base, p), g in sorted(groups.items()):
        best = min((r['objective'] for r in g if r.get('verified')), default=None)
        opt = [solver_label(r) + '/' + r['model'] for r in g if r.get('proven_optimal')]
        fastest = min((r for r in g if r.get('proven_optimal')), key=lambda r: r['total_runtime'], default=None)
        lines.append([base, p, best, 'tak' if opt else 'nie',
                      f"{solver_label(fastest)}, {MODEL_LABEL[fastest['model']]} ({fastest['total_runtime']:.1f} s)"
                      if fastest else 'N/A'])
    md.append(table(['instancja', 'pokrycie %', 'najnizszy koszt', 'optimum udowodnione', 'najszybszy dowod'],
                    lines) + '\n')
    fig, ax = plt.subplots(figsize=(6, 3.6))
    for c, base in enumerate(sorted({r['base'] for r in rows})):
        ps = [95, 98, 100]
        ys = [min((r['objective'] for r in groups[(base, p)] if r.get('verified')), default=np.nan) for p in ps]
        ax.plot(ps, ys, 'o-', color=SERIES[c], label=base, markersize=6, markeredgecolor='white')
    ax.set(xlabel='wymagane pokrycie siatki [%]', ylabel='koszt sieci', xticks=[95, 98, 100],
           title='Koszt a wymagane pokrycie')
    ax.legend(fontsize=7.5)
    save(fig, 'coverage.png')


def main():
    data, best, proven = load_all()
    md = ['# Porownanie metod - wyniki eksperymentow\n',
          'Wygenerowane przez `python -B src/analyze_experiments.py` z plikow w `results/experiments/`. '
          'Kazda proba: 1 watek, seed 178, limit czasu obejmuje kompilacje MiniZinc. '
          'Proby szly po 4 rownolegle (Apple M4), wiec czasy sa porownywalne miedzy soba, '
          'ale nie z wynikami z Windows.\n']
    dom = (OUT / 'dominance.csv')
    if dom.exists():
        import csv
        rows = list(csv.DictReader(dom.open(encoding='utf-8')))
        md.append('## Dominance breaking - ile konfiguracji usuwa\n')
        md.append(table(['instancja', 'BTS', 'punkty', 'dozwolone konf.', 'usuniete', '%'],
                        [[r['instance'], r['n'], r['m'], r['legal'], r['removed'],
                          fmt(float(r['removed_percent']))] for r in rows]) + '\n')
    md.append('## Najlepsze znane koszty\n')
    md.append(table(['instancja', 'koszt', 'optimum udowodnione'],
                    [[k, best[k], 'tak' if proven[k] else 'nie'] for k in sorted(best) if '_p' not in k]) + '\n')
    for part, fn in [('models', part_models), ('solvers', part_solvers), ('search', part_search),
                     ('search_hard', part_search_hard),
                     ('restarts', part_restarts), ('coverage', part_coverage)]:
        if data.get(part):
            errs = [r for r in data[part] if r['status'] == 'ERROR']
            fn([r for r in data[part] if r['status'] != 'ERROR'], md)
            if errs:
                md.append(f'Uwaga: {len(errs)} prob zakonczonych bledem: ' +
                          ', '.join(r['run_id'] for r in errs[:10]) + '\n')
    (OUT / 'SUMMARY.md').write_text('\n'.join(md), encoding='utf-8')
    print('Zapisano', OUT / 'SUMMARY.md')


if __name__ == '__main__':
    main()
