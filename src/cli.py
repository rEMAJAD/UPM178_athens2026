"""Proste polecenia terminala. Obliczenia sa w pozostalych plikach src/."""
import argparse
import json
from pathlib import Path

from .dataset_generator import generate_all, load_instance
from .optimization import solve, STRATEGIES, environment
from .visualization import deployment_plots
from .benchmarks import benchmark, accuracy, coverage_sweep


DEFAULT_INSTANCE = 'data/instance_01.dzn'


def show_data(path):
    """Wyswietl lokalizacje i limity bez ogromnej macierzy pokrycia."""
    data = load_instance(path)
    print(f"BTS: {len(data['stations'])}; punkty: {len(data['points'])}; wymagane pokrycie: {data['minimum_percent']}%")
    print('Dostepne wysokosci [m]:', data['heights'])
    print('Moce [dBm]:', data['powers'])
    print('Minimalny odstep wybranych BTS [km]:', data['min_distance_km'])
    print('Wazne punkty (wymagane dwie stacje):', [point for point, flag in zip(data['points'],data['critical']) if flag])
    print('BTS    X [km]    Y [km]    Limit [m]    Koszty wedlug wysokosci i podanej kolejnosci mocy')
    for i, (x, y) in enumerate(data['stations']):
        print(f"{i+1:3}    {x:6.2f}    {y:6.2f}    {data['max_height'][i]:9}    {data['cost'][i]}")


def run_optimization(args):
    result = solve(args.instance, args.strategy, args.seconds, Path(args.out) / 'solution.json')
    print('Status:', result['status'])
    if not result['verified']:
        print('Nie znaleziono poprawnego rozwiazania. Sprawdz status lub zwieksz limit czasu.')
        return

    data = load_instance(args.instance)
    print('Koszt sieci:', result['objective'])
    print(f"Pokrycie punktow pomiarowych: {result['coverage_percent']:.2f}%")
    print('Wybrane stacje:')
    for site, height, power in result['selected']:
        x, y = data['stations'][site]
        print(f"  BTS {site+1}: ({x:.2f}, {y:.2f}) km, antena {data['heights'][height]} m, moc {data['powers'][power]} dBm, limit {data['max_height'][site]} m")
    for name, count in zip(data['critical_names'], result['critical_support']):
        print(f'{name}: zasieg z {count} roznych stacji')
    deployment_plots(data, result, args.out)
    print('Wykresy i wynik zapisano w:', args.out)


def main():
    parser = argparse.ArgumentParser(description='Planowanie sieci BTS - Python + MiniZinc')
    commands = parser.add_subparsers(dest='command', required=True)

    generate = commands.add_parser('generate', help='Wygeneruj dane z settings.py')
    generate.add_argument('--out', default='data')
    generate.add_argument('--coverage', type=float, default=100)

    data = commands.add_parser('data', help='Pokaz czytelna tabele lokalizacji i limitow')
    data.add_argument('instance', nargs='?', default=DEFAULT_INSTANCE)

    optimize = commands.add_parser('solve', help='Wybierz stacje i wysokosci, zapisz wykresy')
    optimize.add_argument('instance', nargs='?', default=DEFAULT_INSTANCE)
    optimize.add_argument('--strategy', choices=STRATEGIES, default='weighted_random')
    optimize.add_argument('--out', default='results/deployment')
    optimize.add_argument('--seconds', type=float, default=30)

    # Ponizsze polecenia sluza do eksperymentow wymaganych w raporcie.
    bench = commands.add_parser('benchmark', help='Porownaj strategie MiniZinc')
    bench.add_argument('--data', default='data')
    bench.add_argument('--out', default='results/benchmark')
    bench.add_argument('--strategies', nargs='+', choices=STRATEGIES)

    acc = commands.add_parser('accuracy', help='Porownaj gestosc siatki pomiarowej')
    acc.add_argument('--out', default='results/accuracy')
    acc.add_argument('--sizes', nargs='+', type=int, default=[10,20,30,50])
    acc.add_argument('--stations', type=int, default=20)
    acc.add_argument('--strategy', choices=STRATEGIES, default='weighted_random')

    sweep = commands.add_parser('coverage-sweep', help='Porownaj wymagania 95%, 98%, 100%')
    sweep.add_argument('instance', nargs='?', default=DEFAULT_INSTANCE)
    sweep.add_argument('--out', default='results/coverage_sweep')

    for command in [bench, acc, sweep]:
        command.add_argument('--seconds', type=float, default=900,
                             help='Limit na pojedyncza probe, lacznie z kompilacja')
    commands.add_parser('doctor', help='Sprawdz instalacje MiniZinc')
    args = parser.parse_args()

    if args.command == 'generate':
        for path in generate_all(args.out, args.coverage):
            print('Zapisano:', path)
    elif args.command == 'data':
        show_data(args.instance)
    elif args.command == 'solve':
        run_optimization(args)
    elif args.command == 'benchmark':
        paths = sorted(Path(args.data).glob('*.dzn'))
        benchmark(paths, args.out, args.seconds, args.strategies)
    elif args.command == 'accuracy':
        accuracy(args.out, args.seconds, args.sizes, args.stations, strategy=args.strategy)
    elif args.command == 'coverage-sweep':
        coverage_sweep(args.instance, args.out, args.seconds)
    elif args.command == 'doctor':
        print(json.dumps(environment(), indent=2))


if __name__ == '__main__':
    main()
