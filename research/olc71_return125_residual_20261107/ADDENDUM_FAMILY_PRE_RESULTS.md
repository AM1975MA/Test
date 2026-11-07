# OLC71B — Analisi di causalità/collinearità dei blocchi Return125 (registrata prima degli outcome di famiglia)
**Stato:** il risultato OLC71A è GIÀ NOTO: +125 peggiora la MSE 2021–24 in entrambi i mercati e non supera FUSION nei Top2. OLC71B è un follow-up diagnostico, NON una nuova conferma indipendente, e non può essere usato per scegliere retrospettivamente un nuovo modello operativo.

## Controllo strutturale
Return125 consta di 46 RAW, 46 percentili, 33 dev; confrontare qualità data/anno/mercato, confronti raw vs _pct per medesimo segnale, dipendenze correlazionali train-only e presenza di feature altamente incomplete. Registrare FDR-q del precedente PRIOR_FEATURES_125.csv soltanto come analisi precedente, non calcolare p-value nuovi su periodi selezionati.

## Quattro famiglie preregistrate per interpretare il fallimento di +125
Riutilizzare gli stessi input/OFFOOF monthly train/control del run_olc71.py, StandardScaler+imputer train-only+Ridge(alpha=100), stessi cutoffs conservativi `exit_date_63 < Jan1`, label mediana 21d, stessi score B0 e stesso split annuale. Sostituire il solo blocco Return125 in CTRL_RIDGE con:
1. RAW46 (solo 46 indicatori base)
2. PCT46 (solo 46 trasformate di rango)
3. DEV33 (solo 33 robust dev)
4. NO_LIQ119 (125 meno sei canali `log_adv63` e `volume_surprise21` RAW/PCT/DEV: candidato preesistente OLC08F)
Non modificare alpha, target o modello sulla base dei risultati. Valutare RMSE, future 21/42 static Top2 e hit @20%, per mercato/anno 2021–24, 2025. Nessun CAGR senza contabilità nativa.

## Importanza del learner originale
Esaminare modelli originali Return125 XGBoost (2019–2026) negli archivi OLC08_03, se salvati; mappare i `f0..f124` con ordine da audit `return_features`, aggregare gain/weight e stabilità per anno, NON interpretare gain come predittività causale o informazione residua. Per la mancanza dei modelli USA nella stessa copia, dichiarare la limitazione, senza riportare quote di feature importanti come evidenza di due mercati.

Qualunque risultato OLC71B resta diagnostico perché 2019–26 è già stato ampiamente esplorato; nessun tuning ulteriore e nessun uso operativo.
