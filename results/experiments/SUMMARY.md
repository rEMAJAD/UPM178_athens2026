# Porownanie metod - wyniki eksperymentow

Wygenerowane przez `python -B src/analyze_experiments.py` z plikow w `results/experiments/`. Kazda proba: 1 watek, seed 178, limit czasu obejmuje kompilacje MiniZinc. Proby szly po 4 rownolegle (Apple M4), wiec czasy sa porownywalne miedzy soba, ale nie z wynikami z Windows.

## Dominance breaking - ile konfiguracji usuwa

| instancja | BTS | punkty | dozwolone konf. | usuniete | % |
|---|---|---|---|---|---|
| instance_01 | 10 | 102 | 116 | 59 | 50.9 |
| instance_02 | 15 | 227 | 172 | 49 | 28.5 |
| instance_03 | 20 | 402 | 232 | 61 | 26.3 |
| instance_04 | 25 | 627 | 288 | 73 | 25.3 |
| instance_05 | 30 | 902 | 348 | 89 | 25.6 |
| instance_06 | 35 | 902 | 404 | 104 | 25.7 |
| instance_07 | 40 | 1227 | 464 | 121 | 26.1 |
| instance_08 | 45 | 1602 | 520 | 126 | 24.2 |
| instance_09 | 50 | 2027 | 580 | 145 | 25.0 |
| instance_10 | 60 | 2502 | 696 | 189 | 27.2 |

## Najlepsze znane koszty

| instancja | koszt | optimum udowodnione |
|---|---|---|
| instance_01 | 1289 | tak |
| instance_02 | 1143 | tak |
| instance_03 | 1210 | tak |
| instance_04 | 1298 | tak |
| instance_05 | 1158 | tak |
| instance_06 | 1141 | tak |
| instance_07 | 1035 | tak |
| instance_08 | 986 | tak |
| instance_09 | 1015 | tak |
| instance_10 | 1018 | tak |

## Warianty modelu (Gecode, limit 60 s)

Punkt widzenia 0/1 vs. calkowitoliczbowy, dominance breaking + ograniczenie nadmiarowe. Dwie strategie: `dom_w_deg/indomain_random` i `first_fail/indomain_min`.

| model | strategia | optimum (z 10) | brak rozw. | sredni gap % | sredni czas s |
|---|---|---|---|---|---|
| 0/1 (bazowy) | dom_w_deg | 2 | 0 | 11.43 | 51.9 |
| 0/1 (bazowy) | first_fail | 1 | 0 | 10.28 | 54.5 |
| 0/1 + dominance | dom_w_deg | 2 | 0 | 10.52 | 48.7 |
| 0/1 + dominance | first_fail | 2 | 0 | 6.42 | 51.7 |
| int viewpoint | dom_w_deg | 6 | 0 | 10.98 | 32.8 |
| int viewpoint | first_fail | 4 | 0 | 2.60 | 39.0 |
| int + dominance | dom_w_deg | 6 | 0 | 17.93 | 31.7 |
| int + dominance | first_fail | 5 | 0 | 1.35 | 37.4 |

## Solvery (limit 60 s, 1 watek)

Gecode = klasyczne CP (propagacja + przeszukiwanie z nawrotami, branch & bound). Chuffed i CP-SAT = lazy clause generation (uczenie sie klauzul z porazek). HiGHS i COIN-BC = MIP (relaksacja LP + branch & cut).

| solver | model | optimum (z 10) | brak rozw. | sredni gap % | sredni czas s |
|---|---|---|---|---|---|
| COIN-BC (MIP) | 0/1 (bazowy) | 10 | 0 | 0.00 | 3.0 |
| COIN-BC (MIP) | int + dominance | 10 | 0 | 0.00 | 3.2 |
| CP-SAT (free search) | 0/1 (bazowy) | 10 | 0 | 0.00 | 2.6 |
| CP-SAT (free search) | int + dominance | 10 | 0 | 0.00 | 1.7 |
| Chuffed (first_fail) | 0/1 (bazowy) | 1 | 0 | 7.14 | 54.6 |
| Chuffed (first_fail) | int + dominance | 8 | 0 | 0.43 | 17.4 |
| Chuffed (free search) | 0/1 (bazowy) | 3 | 0 | 0.57 | 50.4 |
| Chuffed (free search) | int + dominance | 10 | 0 | 0.00 | 3.6 |
| Gecode (dom_w_deg+min) | 0/1 (bazowy) | 1 | 0 | 96.76 | 54.2 |
| Gecode (dom_w_deg+min) | int + dominance | 8 | 0 | 0.00 | 14.7 |
| Gecode (dom_w_deg+random+luby) | 0/1 (bazowy) | 1 | 0 | 5.76 | 54.7 |
| Gecode (dom_w_deg+random+luby) | int + dominance | 5 | 0 | 11.65 | 40.8 |
| HiGHS (MIP) | 0/1 (bazowy) | 10 | 0 | 0.00 | 2.4 |
| HiGHS (MIP) | int + dominance | 10 | 0 | 0.00 | 1.7 |

## Heurystyki przeszukiwania (Gecode, instancje 01-04, limit 20 s, bez restartow)

8 heurystyk wyboru zmiennej x 6 wyboru wartosci, w obu punktach widzenia. Komorka: sredni gap % / liczba udowodnionych optimow (z 4).

### 0/1 (bazowy)

| zmienna \ wartosc | indomain_min | indomain_max | indomain_median | indomain_random | indomain_split | indomain_reverse_split |
|---|---|---|---|---|---|---|
| input_order | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 |
| first_fail | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 |
| anti_first_fail | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 |
| smallest | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 |
| largest | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 | 12.12 / 1 | 100.00 / 0 |
| occurrence | 38.29 / 1 | 1.20 / 2 | 38.29 / 1 | 5.49 / 1 | 38.29 / 1 | 1.20 / 1 |
| most_constrained | 38.29 / 1 | 1.20 / 1 | 38.29 / 1 | 5.49 / 1 | 38.29 / 1 | 1.20 / 2 |
| dom_w_deg | 28.82 / 1 | 1.20 / 2 | 28.82 / 1 | 2.38 / 2 | 28.82 / 1 | 1.20 / 2 |

### int viewpoint

| zmienna \ wartosc | indomain_min | indomain_max | indomain_median | indomain_random | indomain_split | indomain_reverse_split |
|---|---|---|---|---|---|---|
| input_order | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |
| first_fail | 0.00 / 4 | 0.00 / 3 | 1.77 / 3 | 1.29 / 3 | 1.12 / 3 | 0.00 / 3 |
| anti_first_fail | 0.00 / 4 | 0.00 / 4 | 5.33 / 2 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |
| smallest | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |
| largest | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |
| occurrence | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |
| most_constrained | 0.00 / 4 | 4.70 / 3 | 1.77 / 3 | 1.29 / 3 | 1.12 / 3 | 0.00 / 3 |
| dom_w_deg | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 | 0.00 / 4 |

## Heurystyki na trudniejszych instancjach (Gecode, int + dominance, 05-10, limit 30 s)

Komorka: liczba udowodnionych optimow (z 6) / sredni czas s (bez dowodu = limit) / sredni gap %.

| zmienna \ wartosc | indomain_min | indomain_max | indomain_median | indomain_random | indomain_split | indomain_reverse_split |
|---|---|---|---|---|---|---|
| input_order | 2 / 25.2 / 2.59 | 1 / 26.6 / 25.94 | 0 / 30.0 / 26.81 | 1 / 28.4 / 22.89 | 1 / 28.2 / 6.74 | 3 / 23.5 / 22.80 |
| first_fail | 1 / 27.9 / 2.26 | 0 / 30.0 / 49.22 | 0 / 30.0 / 67.81 | 0 / 30.0 / 53.74 | 0 / 30.0 / 4.00 | 0 / 30.0 / 46.95 |
| anti_first_fail | 3 / 16.1 / 8.82 | 3 / 20.8 / 11.10 | 0 / 30.0 / 88.84 | 0 / 30.0 / 40.48 | 2 / 25.8 / 43.22 | 4 / 15.2 / 7.31 |
| smallest | 4 / 13.4 / 1.31 | 2 / 23.7 / 25.94 | 1 / 29.6 / 25.58 | 2 / 22.5 / 17.30 | 3 / 20.5 / 2.34 | 3 / 18.7 / 15.33 |
| largest | 3 / 21.4 / 13.83 | 2 / 22.3 / 9.54 | 1 / 29.4 / 18.95 | 2 / 25.1 / 18.65 | 0 / 30.0 / 73.19 | 3 / 20.6 / 13.36 |
| occurrence | 4 / 13.2 / 5.65 | 3 / 20.4 / 8.21 | 1 / 28.4 / 35.49 | 1 / 26.2 / 27.12 | 1 / 26.5 / 48.89 | 4 / 15.0 / 6.42 |
| most_constrained | 1 / 28.3 / 3.22 | 0 / 30.0 / 55.04 | 0 / 30.0 / 72.17 | 0 / 30.0 / 53.93 | 0 / 30.0 / 4.00 | 0 / 30.0 / 47.73 |
| dom_w_deg | 4 / 14.2 / 0.00 | 3 / 20.7 / 29.60 | 1 / 28.3 / 40.93 | 2 / 24.6 / 32.23 | 3 / 18.6 / 0.26 | 3 / 19.0 / 29.66 |

Ranking (najwiecej optimow, potem najkrotszy czas):

| # | zmienna | wartosc | optimum (z 6) | sredni czas s | sredni gap % |
|---|---|---|---|---|---|
| 1 | occurrence | indomain_min | 4 | 13.2 | 5.65 |
| 2 | smallest | indomain_min | 4 | 13.4 | 1.31 |
| 3 | dom_w_deg | indomain_min | 4 | 14.2 | 0.00 |
| 4 | occurrence | indomain_reverse_split | 4 | 15.0 | 6.42 |
| 5 | anti_first_fail | indomain_reverse_split | 4 | 15.2 | 7.31 |
| 6 | anti_first_fail | indomain_min | 3 | 16.1 | 8.82 |
| 7 | dom_w_deg | indomain_split | 3 | 18.6 | 0.26 |
| 8 | smallest | indomain_reverse_split | 3 | 18.7 | 15.33 |
| 9 | dom_w_deg | indomain_reverse_split | 3 | 19.0 | 29.66 |
| 10 | occurrence | indomain_max | 3 | 20.4 | 8.21 |

## Restarty (Gecode, indomain_random, limit 30 s)

| model | zmienna | restart | optimum (z 10) | brak rozw. | sredni gap % | sredni czas s |
|---|---|---|---|---|---|---|
| 0/1 (bazowy) | dom_w_deg | constant | 0 | 4 | 18.61 | 30.0 |
| 0/1 (bazowy) | dom_w_deg | geometric | 2 | 0 | 13.99 | 27.2 |
| 0/1 (bazowy) | dom_w_deg | linear | 0 | 0 | 9.70 | 30.0 |
| 0/1 (bazowy) | dom_w_deg | luby | 1 | 0 | 8.63 | 27.4 |
| 0/1 (bazowy) | dom_w_deg | none | 2 | 0 | 11.32 | 25.7 |
| 0/1 (bazowy) | first_fail | constant | 0 | 7 | 46.23 | 30.0 |
| 0/1 (bazowy) | first_fail | geometric | 0 | 6 | 88.01 | 30.0 |
| 0/1 (bazowy) | first_fail | linear | 0 | 7 | 68.30 | 30.0 |
| 0/1 (bazowy) | first_fail | luby | 0 | 6 | 68.90 | 30.0 |
| 0/1 (bazowy) | first_fail | none | 0 | 7 | 126.27 | 30.0 |
| int + dominance | dom_w_deg | constant | 1 | 0 | 13.65 | 27.0 |
| int + dominance | dom_w_deg | geometric | 5 | 0 | 21.21 | 18.5 |
| int + dominance | dom_w_deg | linear | 3 | 0 | 19.31 | 22.6 |
| int + dominance | dom_w_deg | luby | 4 | 0 | 15.10 | 21.5 |
| int + dominance | dom_w_deg | none | 6 | 0 | 20.18 | 15.9 |
| int + dominance | first_fail | constant | 0 | 0 | 35.67 | 30.0 |
| int + dominance | first_fail | geometric | 3 | 0 | 40.05 | 22.7 |
| int + dominance | first_fail | linear | 2 | 0 | 35.99 | 26.6 |
| int + dominance | first_fail | luby | 2 | 0 | 33.54 | 24.5 |
| int + dominance | first_fail | none | 4 | 0 | 32.92 | 20.5 |

## Wymagane pokrycie 95 / 98 / 100 %

| instancja | pokrycie % | najnizszy koszt | optimum udowodnione | najszybszy dowod |
|---|---|---|---|---|
| instance_01 | 95 | 1060 | tak | CP-SAT (free search), int + dominance (0.1 s) |
| instance_01 | 98 | 1109 | tak | HiGHS (MIP), 0/1 (bazowy) (0.2 s) |
| instance_01 | 100 | 1289 | tak | HiGHS (MIP), 0/1 (bazowy) (0.2 s) |
| instance_03 | 95 | 980 | tak | HiGHS (MIP), int + dominance (0.6 s) |
| instance_03 | 98 | 1070 | tak | CP-SAT (free search), int + dominance (1.0 s) |
| instance_03 | 100 | 1210 | tak | CP-SAT (free search), int + dominance (0.5 s) |
| instance_05 | 95 | 1002 | tak | CP-SAT (free search), int + dominance (2.7 s) |
| instance_05 | 98 | 1048 | tak | HiGHS (MIP), int + dominance (3.3 s) |
| instance_05 | 100 | 1158 | tak | CP-SAT (free search), int + dominance (0.9 s) |
| instance_07 | 95 | 762 | tak | HiGHS (MIP), int + dominance (3.2 s) |
| instance_07 | 98 | 820 | tak | CP-SAT (free search), int + dominance (1.9 s) |
| instance_07 | 100 | 1035 | tak | CP-SAT (free search), int + dominance (1.4 s) |
