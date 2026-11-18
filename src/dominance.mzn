% DOMINANCE BREAKING (rozdzial 4, Chu & Stuckey 2015) - wspolne testy na danych.
% Plik dolaczaja radio_coverage_dom.mzn i radio_coverage_int_dom.mzn.
%
% Odwzorowanie sigma: w lokalizacji i zamieniamy konfiguracje c=(k,p) na c2=(k2,p2).
%  - zbior aktywnych lokalizacji sie nie zmienia, wiec odstep 2 km nadal jest spelniony;
%  - jesli c2 pokrywa NADZBIOR punktow c, to links[j] nie maleje: pokrycie zwykle
%    i podwojne pokrycie waznych punktow nadal sa spelnione;
%  - jesli cost(c2) <= cost(c), koszt nie rosnie.
% Zatem c jest zdominowana i mozna zakazac jej wyboru bez utraty optimum.
% Remisy (ten sam zasieg i koszt) rozstrzygamy mniejszym indeksem - to zwykle
% lamanie symetrii. Relacja jest acykliczna, wiec zawsze zostaje niezdominowana konfiguracja.

function int: cfg(int: k, int: p) = (k - 1) * P + p;

% Zbior punktow pokrywanych przez konfiguracje (i,k,p) - liczony raz, jako parametr.
array[1..N,1..K,1..P] of set of int: reach = array3d(1..N, 1..K, 1..P,
    [ {j | j in 1..M where coverage[i,k,p,j] = 1} | i in 1..N, k in 1..K, p in 1..P ]);

test height_ok(int: i, int: k) = heights[k] <= max_height[i];

test dominates(int: i, int: k2, int: p2, int: k, int: p) =
    (k2, p2) != (k, p) /\ height_ok(i, k2) /\
    cost[i,k2,p2] <= cost[i,k,p] /\ reach[i,k,p] subset reach[i,k2,p2] /\
    ( cost[i,k2,p2] < cost[i,k,p]
      \/ reach[i,k,p] != reach[i,k2,p2]
      \/ cfg(k2,p2) < cfg(k,p) );

% Konfiguracja bez zasiegu jest zdominowana przez "nie budujemy" (koszt 0).
test dominated(int: i, int: k, int: p) =
    reach[i,k,p] = {} \/
    exists(k2 in 1..K, p2 in 1..P)(dominates(i, k2, p2, k, p));
