# OLC61 — Protocollo preregistrato: target economico e persistenza appresi nelle 42 feature native

**7 novembre 2026 — PRIMA DELLA PRIMA ESECUZIONE DEGLI OUTCOME OLC61.** Laboratorio isolato. Nessuna modifica al ranking operativo, a OLC19 o a main. Nessuna ricerca di fonti esterne. Tutte le finestre storiche 2019–2026 sono state ampiamente studiate: i risultati non sono conferma OOS indipendente.

## Quesito
Un learner a monte, addestrato direttamente sulle 42 feature native originarie OLC14/11 senza score FUSION come input, riesce a selezionare Top2 economicamente migliori e più persistenti rispetto al Top2 nativo e al **riferimento più severo della fusione originale**? Non applicare alcun correttore finale, bonus momentum, gate o timing.

## Fonti e cutoffs
OLC14 Heads ZIP SHA256 a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458: annual/{EU,USA}_{year}.joblib matrici X e XP, chiavi; *_LAYER_LABELS.csv.gz. Le 42 colonne originali restano identiche.
OLC14 Results ZIP SHA256 4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1: *_MEAN3_SCORES.csv.gz. Confronto sui medesimi ETF/date.
Un refit annuale per mercato × anno 2021–2025, expanding training sui soli gruppi con exit_date_63 < primo gennaio dell'anno di fit. MAIN: 48 mesi 2021–2024; LATE: 2025 diagnostico. Nessun holdout vergine.

## Target tre bracci fissi
Per ogni ETF e gruppo mensile maturo: l1 = log(1+fwd_ret_21), l2 = log(1+fwd_ret_42)-log(1+fwd_ret_21); g1=10000*(l1−mediana_j(l1_j)), g2=10000*(l2−mediana_j(l2_j)), log-bp. Il secondo è un periodo disgiunto 21→42.
ECON21: u=g1. STAY2: u=min(g1,g2). ECO_STAY: u=0.70*g1+0.30*min(g1,g2).
Relevance intera da soglie log-bp [-300,-100,0,100,300] => 0..5 e gains [0,1,3,7,15,31].
Per tutti gli arm, LightGBM LGBMRanker(objective='lambdarank',n_estimators=180,learning_rate=.04,num_leaves=7,min_child_samples=80,reg_lambda=10,max_bin=127,lambdarank_truncation_level=10,label_gain=[0,1,3,7,15,31],n_jobs=2,deterministic=True,force_col_wise=True,verbosity=-1,random_state=611). Rank groups monthly, same native X and XP, no ticker ID or additional features, missing handled natively. Direct Top2 from predicted rank, no fusion of original score. Fractional tied-weight original.

## Gate
Compare original OLC14 CURRENT (B0_NATIVE) and FUSION (B0_FUSION_CONTEXT), with original FUSION as strict main comparator. Evaluate equal-weight static Top2 future r21/r42, future percentile top20% hit21 and hit21+42, positive relative g1 & g2, log-economic spreads, year/month. Six-month circular block bootstrap paired difference against FUSION (descriptive only) with seed611. Require positive improvement vs original FUSION in r21 for BOTH markets, plus non-inferior persistence and r42 in BOTH; otherwise NO PROMOTION / no further tuning within same historic sample. No CAGR, portfolio replay, stop-cost speculation; all 2019-2026 data mined before. Validate archive hashes, 42 features, train maturity, no future information in prediction, same support, fractional ties, exact original baseline checks, model serialization/prediction parity.
