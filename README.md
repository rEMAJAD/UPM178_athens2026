# Planowanie sieci BTS

Wybieramy stacje, wysokości anten i moce nadajników, żeby zapewnić wymagane pokrycie
najniższym kosztem. Każda lokalizacja ma limit wysokości. Szpital i uczelnia muszą
mieć zasięg z dwóch różnych stacji, niezależnie od wymaganego procentu pokrycia mapy.
Wybudowane stacje muszą być oddalone od siebie o co najmniej 2 km.

## Układ projektu

```text
main.py          uruchamiasz program
settings.py      zmieniasz wysokości, limity i rozmiary danych
requirements.txt biblioteki do zainstalowania
README.md        instrukcja

src/             cały kod Pythona i model MiniZinc
data/            dane wejściowe
results/         wyniki, wykresy, raport i ZIP
```

## Uruchomienie

Terminal otwórz w folderze projektu. Przy pierwszym uruchomieniu:

```powershell
python -m pip install -r requirements.txt
```

Potrzebny jest MiniZinc z Gecode. Standardowa instalacja Windows w
`C:\Program Files\MiniZinc` jest wykrywana automatycznie. Alternatywnie dodaj
MiniZinc do PATH albo ustaw zmienną MINIZINC na jego plik wykonywalny.

```powershell
python main.py data
python main.py solve
```

Pierwsze polecenie pokazuje dane. Drugie rozwiązuje pierwszy przykład:
10 kandydatów BTS, 100 punktów siatki oraz 2 ważne punkty (łącznie 102).
Wyniki i mapy są w `results/deployment/`.

```powershell
Start-Process .\results\deployment\heatmap.png
```

Inny przykład:

```powershell
python main.py solve data/instance_05.dzn --seconds 60 --out results/deployment_05
```

OPTIMAL_SOLUTION = udowodnione optimum. SATISFIED = poprawny wynik bez dowodu,
że jest najtańszy. UNSATISFIABLE = niewykonalne wymagania. UNKNOWN = brak rozstrzygnięcia.

## Zmiana wysokości

W `settings.py` lista MAX_HEIGHTS podaje limity dla kolejnych stacji.
Limit 50 m pozwala wybrać 30 lub 50 m, a wyklucza 80 i 120 m.
W większych datasetach lista się powtarza. Po zmianie ustawień:

```powershell
python main.py generate
python main.py data
python main.py solve
```

Zbyt niskie limity mogą uniemożliwić wymagane pokrycie — generator to sprawdza.
Po zmianie danych stare eksperymenty i raport trzeba przeliczyć ponownie.

W `data/` każdy zestaw ma:

- `.dzn` — wejście MiniZinc, w tym macierz pokrycia 0/1;
- `.json` — dokładne współrzędne i parametry dla Pythona;
- `_sites.csv` — małą tabelę lokalizacji, limitów i kosztów do obejrzenia.

CSV jest podglądem, nie wejściem programu. Zmieniaj settings.py i generuj dane ponownie.

## Kod — wszystko w src/

| Plik | Zadanie |
|---|---|
| propagation.py | Model radiowy: odległość → tłumienie → moc odbierana |
| dataset_generator.py | Lokalizacje, siatka punktów, koszty, zapis danych |
| radio_coverage.mzn | Wybór stacji i wysokości, minimalizacja kosztu |
| optimization.py | Uruchomienie MiniZinc i sprawdzenie wyniku |
| visualization.py | Mapy i wykresy |
| cli.py | Obsługa terminala |
| benchmarks.py | Eksperymenty do raportu |

Pozostałe pliki to testy i narzędzia do raportu oraz ZIP-a.
`default_search.dzn` zawiera ustawienia do bezpośredniego uruchomienia MiniZinc.
`requirements-tested.txt` zapisuje wersje bibliotek użyte do sprawdzenia projektu.

W MiniZinc x[i,k,p]=1 oznacza wybór stacji i z wysokością k i mocą p. Model pozwala
wybrać najwyżej jedną konfigurację wysokości i mocy w lokalizacji i zabrania anten ponad limit.
Punkt jest pokryty, jeśli dociera do niego przynajmniej jedna wybrana stacja.
Wymagamy odpowiedniej liczby pokrytych punktów i minimalizujemy sumę kosztów.
Python liczy propagację wcześniej; MiniZinc dostaje gotową macierz 0/1.

## Moce, ważne punkty i odległość między stacjami

W `settings.py` są teraz również:

```python
POWERS_DBM = [34, 37, 40, 43] # około 2,5 / 5 / 10 / 20 W
POWER_COST = [0, 15, 35, 60]  # dopłaty do kosztu konfiguracji
CRITICAL_POINTS = [(3, 3), (7, 7)]
CRITICAL_NAMES = ['Szpital', 'Uczelnia']
MIN_STATION_DISTANCE_KM = 2.0
```

Każdy kolejny poziom mocy daje sygnał silniejszy o 3 dB, ale kosztuje więcej.
Zysk anteny pozostaje stały. Współrzędne ważnych punktów są w kilometrach.
Ważne punkty dopisujemy do każdej siatki, dzięki czemu ich położenie nie zmienia
się w eksperymencie gęstości siatki. Największy dataset ma 2500 + 2 punkty.

Zmienna `links[j]` liczy wybrane stacje docierające do punktu. Zwykły punkt wymaga
przynajmniej jednej, ważny punkt przynajmniej dwóch. Dwie konfiguracje tego samego
BTS nie mogą udawać dwóch stacji. Po awarii jednej stacji ważny punkt zachowuje
zasięg; nie jest to gwarancja pojemności sieci ani pokrycia całej mapy po awarii.
Przy celu 95% ważne punkty nadal muszą mieć podwójne pokrycie.
Macierz ma teraz postać `coverage[stacja, wysokość, moc, punkt]`.

W `settings.py` lista `CANDIDATE_SITES` zawiera **60 stałych lokalizacji (x,y)**.
Możesz edytować ich współrzędne. Dataset z N kandydatami bierze pierwsze N pozycji.
Seed zmienia koszty, nie lokalizacje. Python nie losuje już położenia stacji.

Kandydaci mogą leżeć blisko siebie — wtedy solver nie może wybrać obu naraz.
Python tworzy tabelę `too_close`, a MiniZinc zakazuje jednoczesnego wyboru zbyt
bliskich lokalizacji. Odległość dokładnie 2 km jest dozwolona.
Generator sprawdza prosty zestaw kontrolny z pierwszych dziewięciu miejsc.
Jeśli po zmianach ustawień ten zestaw nie spełnia warunków, zgłasza błąd;
nie oznacza to automatycznie, że żadna inna kombinacja nie jest możliwa.

## Eksperymenty i testy

```powershell
python main.py benchmark --seconds 10
python main.py accuracy --seconds 10
python main.py coverage-sweep --seconds 10
python main.py doctor
python -B -m pytest src/test_project.py -q -p no:cacheprovider
```

Benchmark porównuje 6 strategii na 10 datasetach. Accuracy porównuje gęstości siatki.
Coverage-sweep porównuje wymagania 95%, 98%, 100%. Wyniki są w podfolderach results/.
Nie trzeba ich przeglądać przy zwykłym uruchomieniu.

Limit obejmuje kompilację MiniZinc i dotyczy jednej próby. Domyślnie solve ma 30 s,
a eksperymenty 900 s na próbę. Pełny benchmark bez krótkiego limitu może trwać 15 godzin.
Dostarczone wyniki to krótkie próby; nie wszystkie większe zadania mają udowodnione optimum.
Nieudostępnione statystyki oznaczamy N/A. Surowe logi zachowano w results/.

## Założenia radiowe

Obszar 10 × 10 km, 900 MHz, moc nadajnika wybierana z 34/37/40/43 dBm, zysk BTS 15 dBi,
odbiornik 1,5 m. Próg pokrycia −85 dBm zawiera margines 10 dB.
Parametry są w klasie Radio w src/propagation.py. Koszty są umowne.
Dla odległości poniżej 1 km przyjmujemy tłumienie jak dla 1 km — to uproszczenie,
nie dokładny model blisko anteny. Pomijamy teren, interferencje i ruch.
Pokrycie siatki nie gwarantuje pokrycia każdego miejsca pomiędzy punktami.
Walidacja używa osobnej siatki 100 × 100 punktów.
Na wykresie porównawczym „All sites (no spacing)” to radiowe odniesienie z wszystkimi
stacjami, pomijające odstępy — nie jest to dopuszczalny projekt sieci.

## Raport i oddanie

Raport: `results/report.pdf`. ZIP: `results/upm178_2026_name_surname.zip`.
Po przeliczeniu eksperymentów można je odtworzyć:

```powershell
python -B src/verify_results.py
python -B src/build_report.py
python -B src/package.py
```

Imię i nazwisko wpisz w src/build_report.py, odbuduj raport i ZIP, zmień nazwę ZIP-a.
Nic nie jest wysyłane automatycznie. Instrukcja kursu podaje termin przed 20 listopada 2026.

Źródła: specyfikacja projektu, wykłady i wymagania UPM178 oraz
[dokumentacja MiniZinc](https://docs.minizinc.dev/en/stable/mzn_search.html).

## Porównanie metod MiniZinc (results/experiments/)

```powershell
python main.py experiments --part models solvers --seconds 60
python main.py experiments --part search --seconds 20
python main.py experiments --part search_hard restarts --seconds 30
python main.py experiments --part coverage --seconds 60
python -B src/analyze_experiments.py
```

Warianty modelu (ten sam plik .dzn, ten sam weryfikator):

| Plik | Co dodaje |
|---|---|
| radio_coverage.mzn | model bazowy, zmienne 0/1 x[i,k,p] |
| radio_coverage_dom.mzn | + dominance breaking (dominance.mzn) + redundant_constraint |
| radio_coverage_int.mzn | drugi punkt widzenia: conf[i] in 0..K*P, koszt przez element |
| radio_coverage_int_dom.mzn | punkt widzenia int + dominance breaking + redundant_constraint |

Części: `search` (8 heurystyk zmiennej × 6 wartości), `search_hard` (to samo na 05–10),
`restarts` (constant/linear/geometric/luby), `models`, `solvers` (Gecode, Chuffed, CP-SAT,
HiGHS, COIN-BC), `coverage` (95/98/100%). Każda próba to osobny JSON; przerwaną serię
wystarczy uruchomić ponownie. Wyniki, tabele i wykresy: `results/experiments/SUMMARY.md`.
Na macOS MiniZinc jest wykrywany w /Applications/MiniZincIDE.app.
