"""Ustawienia zadania. Po zmianie uruchom: python main.py generate.

Zysk i pozostale parametry radiowe: klasa Radio w src/propagation.py.
"""

# Dostepne wysokosci anten [m]. Kazda kolejna ma wyzszy koszt.
HEIGHTS = [30, 50, 80, 120]

# Cztery poziomy mocy: ok. 2.5, 5, 10 i 20 W.
POWERS_DBM = [34, 37, 40, 43]
# Doplaty do kosztu konfiguracji (umowne jednostki, nie cena energii).
POWER_COST = [0, 15, 35, 60]
# Te same wazne punkty w kazdym zestawie i przy kazdej gestosci siatki.
# Dopisujemy je do siatki; kazdy wymaga zasiegu z DWOCH ROZNYCH stacji.
CRITICAL_POINTS = [(3.0, 3.0), (7.0, 7.0)]
CRITICAL_NAMES = ['Szpital', 'Uczelnia']

# Maksymalna wysokosc w kolejnych lokalizacjach [m].
# Np. stacja 1: tylko 30 lub 50 m; stacja 3: wszystkie cztery wysokosci.
# Dla wiecej niz 10 stacji powtarzamy te liste.
MAX_HEIGHTS = [50, 80, 120, 50, 80, 120, 80, 50, 120, 50]

# (liczba kandydatow BTS, bok siatki pomiarowej)
# Bok 20 oznacza 20 * 20 = 400 punktow na tym samym obszarze 10 x 10 km.
DATASET_SIZES = [
    (10, 10), (15, 15), (20, 20), (25, 25), (30, 30),
    (35, 30), (40, 35), (45, 40), (50, 45), (60, 50),
]

# Minimalny odstep dotyczy WYBRANYCH BTS, nie wszystkich kandydatow.
MIN_STATION_DISTANCE_KM = 2.0

# Stala lista kandydatow (x, y) w km. Mozesz edytowac te wspolrzedne.
# Dataset z N kandydatami bierze pierwszych N pozycji; nic nie losuje lokalizacji.
# Pierwszych 9 miejsc sluzy tez jako prosty sprawdzalny zestaw kontrolny.
CANDIDATE_SITES = [
    (1.7, 1.7), (1.7, 5.0), (1.7, 8.3), (5.0, 1.7), (5.0, 5.0),
    (5.0, 8.3), (8.3, 1.7), (8.3, 5.0), (8.3, 8.3), (0.5, 0.5),
    (0.5, 2.0), (0.5, 3.5), (0.5, 5.0), (0.5, 6.5), (0.5, 8.0),
    (0.5, 9.5), (2.0, 0.5), (2.0, 2.0), (2.0, 3.5), (2.0, 5.0),
    (2.0, 6.5), (2.0, 8.0), (2.0, 9.5), (3.5, 0.5), (3.5, 2.0),
    (3.5, 3.5), (3.5, 5.0), (3.5, 6.5), (3.5, 8.0), (3.5, 9.5),
    (5.0, 0.5), (5.0, 2.0), (5.0, 3.5), (5.0, 6.5), (5.0, 8.0),
    (5.0, 9.5), (6.5, 0.5), (6.5, 2.0), (6.5, 3.5), (6.5, 5.0),
    (6.5, 6.5), (6.5, 8.0), (6.5, 9.5), (8.0, 0.5), (8.0, 2.0),
    (8.0, 3.5), (8.0, 5.0), (8.0, 6.5), (8.0, 8.0), (8.0, 9.5),
    (9.5, 0.5), (9.5, 2.0), (9.5, 3.5), (9.5, 5.0), (9.5, 6.5),
    (9.5, 8.0), (9.5, 9.5), (1.0, 5.0), (9.0, 5.0), (5.0, 1.0),
]
