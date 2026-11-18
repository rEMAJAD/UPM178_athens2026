% WARIANT: punkt widzenia calkowitoliczbowy + dominance breaking + ograniczenie nadmiarowe.
include "radio_coverage_int.mzn";
include "dominance.mzn";

% Zdominowane konfiguracje usuwamy z dziedziny conf[i].
constraint forall(i in 1..N, k in 1..K, p in 1..P
                  where height_ok(i,k) /\ dominated(i,k,p))(
    symmetry_breaking_constraint(conf[i] != cfg(k,p))
);

% Ograniczenie nadmiarowe: co najmniej dwie aktywne lokalizacje (wazne punkty).
constraint if exists(j in 1..M)(critical[j]) then
    redundant_constraint(sum(i in 1..N)(bool2int(conf[i] != 0)) >= 2)
endif;
