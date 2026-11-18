% RADIO COVERAGE - drugi punkt widzenia (viewpoint, rozdzial 2).
% Zamiast N*K*P zmiennych 0/1 mamy jedna zmienna calkowita na lokalizacje:
%   conf[i] = 0          -> nie budujemy BTS w lokalizacji i,
%   conf[i] = (k-1)*P+p  -> BTS z wysokoscia k i moca p.
% "Najwyzej jedna konfiguracja na lokalizacje" wynika wprost z modelu,
% a heurystyki zalezne od dziedziny (first_fail, smallest, indomain_split...)
% maja sens, bo dziedziny maja rozne rozmiary.

% 1. DANE (ten sam plik .dzn co model bazowy)
int: N;
int: M;
int: K;
int: P;
float: minimum_percent;
int: required_points;
array[1..K] of int: heights;
array[1..P] of int: powers;
array[1..N] of int: max_height;
array[1..M] of bool: critical;
array[1..N,1..N] of bool: too_close;
array[1..N,1..K,1..P] of int: cost;
array[1..N,1..K,1..P,1..M] of 0..1: coverage;

ann: variable_order;
ann: value_order;
ann: restart_policy;

constraint assert(required_points >= 0 /\ required_points <= M,
                  "Invalid required_points");

set of int: CONF = 0..K*P;
function int: height_of(int: c) = (c - 1) div P + 1;
function int: power_of(int: c) = (c - 1) mod P + 1;

% Dozwolone konfiguracje kazdej lokalizacji (limit wysokosci) - jako dziedzina.
array[1..N] of set of int: legal = [ {0} union
    {(k-1)*P+p | k in 1..K, p in 1..P where heights[k] <= max_height[i]} | i in 1..N ];

% Koszt konfiguracji; 0 = nie budujemy.
array[1..N, CONF] of int: price = array2d(1..N, CONF,
    [ if c = 0 then 0 else cost[i, height_of(c), power_of(c)] endif | i in 1..N, c in CONF ]);

% Konfiguracje lokalizacji i, ktore docieraja do punktu j (dane pomocnicze).
array[1..N,1..M] of set of int: serves = array2d(1..N, 1..M,
    [ {(k-1)*P+p | k in 1..K, p in 1..P where coverage[i,k,p,j] = 1} | i in 1..N, j in 1..M ]);

% 2. ZMIENNE DECYZYJNE
array[1..N] of var CONF: conf;

% 3. OGRANICZENIA
constraint forall(i in 1..N)(conf[i] in legal[i]);

% Odstep: z pary zbyt bliskich lokalizacji co najwyzej jedna jest aktywna.
constraint forall(i, j in 1..N where i < j /\ too_close[i,j])(
    conf[i] = 0 \/ conf[j] = 0
);

% Liczba roznych stacji docierajacych do punktu j.
function var int: links(int: j) =
    sum(i in 1..N where serves[i,j] != {})(bool2int(conf[i] in serves[i,j]));

% Pokrycie. Przy celu 100% kazdy punkt wymaga klauzuli "ktoras stacja dociera"
% (bez bool2int - dobra praktyka z wykladu). Przy celu < 100% liczymy punkty.
constraint if required_points = M then
        forall(j in 1..M where not critical[j])(
            exists(i in 1..N where serves[i,j] != {})(conf[i] in serves[i,j]))
    else
        sum(j in 1..M)(bool2int(links(j) >= 1)) >= required_points
    endif;

% Wazne punkty: dwie rozne stacje (zawsze, niezaleznie od procentu pokrycia).
constraint forall(j in 1..M where critical[j])(links(j) >= 2);

% 4. CEL: koszt przez globalne ograniczenie element (price[i, conf[i]]).
var int: total_cost = sum(i in 1..N)(price[i, conf[i]]);

solve :: int_search(conf, variable_order, value_order, complete)
      :: restart_policy minimize total_cost;

% 5. WYNIK w tym samym formacie co model bazowy (x[i,k,p]), zeby Python
% mogl go sprawdzic tym samym weryfikatorem.
output ["{\"x\":" ++ show([ if fix(conf[i]) = (k-1)*P+p then 1 else 0 endif
                           | i in 1..N, k in 1..K, p in 1..P ]) ++
        ",\"objective\":" ++ show(total_cost) ++ "}\n"];
