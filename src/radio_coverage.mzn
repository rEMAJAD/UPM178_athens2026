% RADIO COVERAGE: wybor lokalizacji, wysokosci i mocy nadajnika.
% Python oblicza propagacje; MiniZinc wybiera najtansza konfiguracje sieci.

% 1. DANE WEJSCIOWE
int: N; % liczba kandydatow na BTS
int: M; % punkty siatki oraz dodatkowe wazne punkty
int: K; % liczba dostepnych wysokosci
int: P; % liczba poziomow mocy
float: minimum_percent;
int: required_points;
array[1..K] of int: heights; % metry
array[1..P] of int: powers; % dBm
array[1..N] of int: max_height;
array[1..M] of bool: critical; % szpital, uczelnia itp.
array[1..N,1..N] of bool: too_close; % Python porownal odleglosci z limitem
array[1..N,1..K,1..P] of int: cost;
array[1..N,1..K,1..P,1..M] of 0..1: coverage;

% Gotowe strategie przeszukiwania do porownania w eksperymentach.
ann: variable_order;
ann: value_order;
ann: restart_policy;

% 2. ZMIENNE DECYZYJNE
% x[i,k,p]=1: budujemy BTS i z wysokoscia k oraz moca p.
array[1..N,1..K,1..P] of var 0..1: x;
array[1..N] of var bool: active; % czy w tej lokalizacji budujemy BTS?
% Liczba roznych wybranych stacji docierajacych do punktu j.
array[1..M] of var 0..N: links;
array[1..M] of var bool: covered;

% 3. OGRANICZENIA
constraint assert(required_points >= 0 /\ required_points <= M,
                  "Invalid required_points");

% Na lokalizacje przypada najwyzej jedna konfiguracja wysokosci i mocy.
constraint forall(i in 1..N)(
    sum(k in 1..K, p in 1..P)(x[i,k,p]) <= 1
);
constraint forall(i in 1..N)(
    active[i] <-> (sum(k in 1..K, p in 1..P)(x[i,k,p]) = 1)
);

% Zbyt bliskie lokalizacje nie moga byc aktywne jednoczesnie.
constraint forall(i,j in 1..N where i < j /\ too_close[i,j])(
    not (active[i] /\ active[j])
);

% Antena nie moze przekraczac lokalnego limitu wysokosci.
constraint forall(i in 1..N, k in 1..K, p in 1..P
                  where heights[k] > max_height[i])(
    x[i,k,p] = 0
);

% Liczymy wybrane stacje, ktore zapewniaja wystarczajacy sygnal.
constraint forall(j in 1..M)(
    links[j] = sum(i in 1..N, k in 1..K, p in 1..P
                   where coverage[i,k,p,j] = 1)(x[i,k,p])
);

% Zwykle pokrycie wymaga co najmniej jednej stacji.
constraint forall(j in 1..M)(covered[j] <-> (links[j] >= 1));
constraint sum(j in 1..M)(bool2int(covered[j])) >= required_points;

% Wazne punkty MUSZA miec dwie rozne stacje, nawet przy celu ponizej 100%.
% Dwie konfiguracje tego samego BTS nie wystarcza: zabrania tego limit powyzej.
constraint forall(j in 1..M where critical[j])(links[j] >= 2);

% 4. CEL: minimalny koszt lokalizacji, wysokosci i poziomu mocy.
var int: total_cost = sum(i in 1..N, k in 1..K, p in 1..P)(
    cost[i,k,p] * x[i,k,p]
);
solve :: int_search(array1d(x), variable_order, value_order, complete)
      :: restart_policy minimize total_cost;

% 5. WYNIK: Python odczytuje decyzje i sprawdza je ponownie.
output ["{\"x\":" ++ show(array1d(x)) ++
        ",\"objective\":" ++ show(total_cost) ++ "}\n"];
