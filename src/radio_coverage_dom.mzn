% WARIANT: model bazowy (zmienne 0/1) + dominance breaking + ograniczenie nadmiarowe.
include "radio_coverage.mzn";
include "dominance.mzn";

% Zdominowane konfiguracje usuwamy przed przeszukiwaniem (statyczne dominance breaking).
constraint forall(i in 1..N, k in 1..K, p in 1..P
                  where height_ok(i,k) /\ dominated(i,k,p))(
    symmetry_breaking_constraint(x[i,k,p] = 0)
);

% Ograniczenie nadmiarowe (implied): wazne punkty wymagaja dwoch roznych stacji,
% wiec (o ile jest jakis wazny punkt) potrzebne sa co najmniej dwie aktywne lokalizacje.
constraint if exists(j in 1..M)(critical[j]) then
    redundant_constraint(sum(i in 1..N)(bool2int(active[i])) >= 2)
endif;
