# OLC54 — Curva BCE incrementale e gate dei dati ECFIN (5 novembre 2026)

**Esito: NO PROMOTION**. Codice e risultati riproducibili sono archiviati nella ChatGPT Library sotto `/ETF_Research/OLC54_Curva_BCE_ECFIN_20261105/` (report, Excel, sorgenti, previsioni, NAV, Q/A). **Nessun cambiamento a OLC19 o alla produzione.**

## Esperimento preregistrato

- Baseline OLC52 Ridge 3 variabili di rischio, con training expanding causale, 18 etichette mature minimo, StandardScaler train-only, alpha20; policy min-var totale 25/75 contro 50/50, motore nativo OLC19 FAST_LOCK3.
- Nuove feature: curva AAA spot 10Y-2Y, differenza AAA10Y ultimi 3 mesi, spread all-issuer10Y meno AAA10Y, tutte da osservazioni disponibili almeno 7 giorni prima dell'ingresso; ablation aggiunta della sola slope.
- Fonte primaria BCE serie `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y`, `SR_10Y`, `G_N_C.SR_10Y`; dati giornalieri riprodotti nel repo pubblico [`treetisarkar24-ops/macro-shock-analyser`](https://github.com/treetisarkar24-ops/macro-shock-analyser/blob/main/DATA_SOURCES.md) sino al 2026-06-24. Per l'esperimento sono state estratte 102 ultime osservazioni mensili 2018-01..2026-06, e validate contro i file sorgente usando conteggi/somme/checksum numerici indipendenti.

## Risultati CAGR (costo legacy .001; % annuo)

| Policy | EU 2021–24 | EU FULL 2019–lug2026 | USA 2021–24 | USA FULL |
|---|---:|---:|---:|---:|
| OLC19 50/50 | 23,20 | 19,76 | 50,77 | 39,48 |
| Min-var 25/75 permanente | 29,31 | 20,84 | 47,73 | 38,98 |
| OLC52 Ridge 3-risk | **25,85** | **21,05** | 49,21 | 37,69 |
| OLC54 3-risk+3 curva | 25,57 | 20,26 | 47,64 | 37,54 |
| OLC54 3-risk+solo slope | 25,43 | 20,83 | 49,54 | 38,49 |

Europa 2021–24: RMSE previsioni edge mensile 141,99bp OLC52, 147,61bp OLC54 curva completa, 144,64bp slope-only, su 45 eventi appaiati. Direzione corretta 53,3% -> 60,0% ma payoff peggiora. Bootstrap MSE gain OLC52-OLC54 in bp²: -1627 [-7647,+2958], intervallo che attraversa zero. Annualità EU: 2022 curve +3,97pp rendimento vs OLC52; 2023 -4,91pp; 2024 -2,72pp; 2026 parziale -4,64pp.

## ECFIN Business and Consumer Surveys: solo source audit

L'archivio originale [DG ECFIN releases](https://economy-finance.ec.europa.eu/economic-forecast-and-surveys/business-and-consumer-surveys/download-business-and-consumer-survey-data/press-releases_en) elenca i comunicati mensili originali datati. Il download provato di PDF non è riuscito (HTTP 429), pertanto **non sono stati ricostruiti i valori vintage ESI/EEI e non è stato eseguito nessun backtest ML ECFIN**. Non impiegare lo storico destagionalizzato corrente come se fosse vintage point-in-time.

## Qualità e limiti

Parità delle sette matrici OLC19, delle predizioni OLC52 rischio e dei CAGR della baseline integrale verificata nel nuovo runner. Lag quote <= entry-7d e maturity cutoff `exit_date < entry_date`. I dati sono pubblicazioni aggregate di un mirror BCE con indicazione dei blob Git, non audit completo delle revisioni PIT. Storico 2019–2026 già esplorato ripetutamente; assente holdout indipendente; eseguibilità degli Open, stop e costi broker non certificati.

**Decisione:** non adottare le feature della curva nel selettore OLC52. Priorità futura: dati ECFIN originali accessibili e un dataset di aspettative/posizionamento fattoriale realmente PIT, da valutare separatamente su nuovi mesi congelati.