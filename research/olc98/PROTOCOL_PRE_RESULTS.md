# OLC98 — Revisione completa dei layer e ordinamenti alternativi

Data di protocollo: 12 novembre 2026, prima di osservare gli outcome di OLC98.
Ricerca offline; nessuna modifica a OLC19, OLC67, al modello operativo o a GitHub main.

## Scopo
Verificare quali layer hanno evidenza autonoma, dove esistono ridondanze e se cambiare l'**ordine logico** dei layer di fusione, ranking, shortlist e contesto migliora la strategia senza alterare training, universo, labels, rischi e calendario. Distinguere evidenze pregresse da nuovi replay OLC98.

## Dati e ground truth
- OLC19_Rischio_Rientro_Checkpoint_20261102.zip: input OLC18 originali, stati giornalieri nativi EU/USA, score per ticker/data, controlli Original e Context, serie OHLC, motore OLC19.
- 90 segnali mensili per mercato dal 2019 a giugno 2026; FULL dalla prima apertura febbraio 2019 fino alla prima apertura luglio 2026, 2026 parziale.
- Previsioni disponibili al giorno di segnale (`signal_date`); rendimenti ex post usati per la valutazione *solo* dopo la selezione e nel simulatore.
- Nessun refit degli esperti Return/ET/XGB e nessuna ottimizzazione di parametri su risultati OLC98.
- Medesima V6, FAST_LOCK3, stop friction .001, fee legacy .001 e .003, esposizione originale. Solo variabile: selezione Top2; timing fisso IMMEDIATE come confronto primario; DELAY3 come sensibilità separata, non selettore di regime.

## Bracci congelati prima del test
B0_ORIGINAL: Top2 per ORIGINAL_FUSION (originale, senza contesto).
B1_CONTEXT: Top2 per TOP2_CONTEXT_REVALUE_FUSION (OLC19 baseline ufficiale).
R1_POSTRANK: rank cross-sectional di ORIGINAL_SMOOTH dopo memoria, poi 0.475 RETURN + 0.525 rank(SMOOTH); testa ordine `memoria → rango → fusione` anziché `memoria → fusione → rango`.
R2_FUSION_GATE10_CONTEXT: shortlist Top10 con ORIGINAL_FUSION, poi scelta dei migliori due per TOP2_CONTEXT_REVALUE_FUSION (ranking prima della rivalutazione contestuale).
R3_CONTEXT_GATE10_FUSION: shortlist Top10 con TOP2_CONTEXT_REVALUE_FUSION, poi scelta dei migliori due con ORIGINAL_FUSION (inversione del gate di shortlist/ranking).
R4_RANK_CONSENSUS: media 50/50 dei percentili cross-sectional di ORIGINAL_FUSION e TOP2_CONTEXT_REVALUE_FUSION, scelta dei migliori due (fusione fra due graduatorie già costituite).
R5_RETURN_GATE10_CONTEXT: shortlist Top10 dal ramo RETURN, poi scelta Top2 per TOP2_CONTEXT_REVALUE_FUSION (ordine `Return shortlist → context rerank`).
R6_HYBRID_GATE10_CONTEXT: shortlist Top10 dal ramo ORIGINAL_SMOOTH, poi scelta Top2 per TOP2_CONTEXT_REVALUE_FUSION (`Hybrid shortlist → context rerank`).

Non sono inclusi nuovi learner o nuovi parametri liberi; Top10 e coefficienti noti da OLC19/66; consenso 50/50 diagnostico, NON ottimizzato. Per ranking di rango usare `rank(method='average', pct=True)` nello stesso mese e tickers. In ogni braccio, tie-break ticker alfabetico; richiedere 180/180 decisioni B0/B1 identiche ai CSV originali.

## Metriche e gate
- Prevalenti: CAGR e MaxDD FULL e MAIN 2021–24 dal motore nativo per EU e USA, rispetto al B1_CONTEXT a parità di timing/fee.
- Secondarie: rendimenti cumulati annuali 2024/2025/2026*; cambi di Top2 vs B1, overlap Top10, turnover, stop, esposizione, costo fee e DELAY3.
- Incertezza: bootstrap paired circular block6 su log-rendimenti *mensili* delle policy con identica esposizione, 4000 repliche con seed fisso 98112. Intervalli descrittivi, non corretti per ~97 esperimenti precedenti.
- Gate per candidabilità (non promozione): CAGR MAIN e FULL almeno B1 in entrambi mercati; MaxDD FULL non peggiore di 3pp in alcun mercato; sensibilità a fee .003 non distruttiva; nessun claim di alpha OOS anche con gate superato.
- Criterio di interpretazione: nessun braccio può essere proclamato migliore in produzione su 2019–luglio 2026, periodo interamente riutilizzato in ricerca. Un eventuale candidato va congelato per shadow prospettico, con dati osservati e implementazione eseguibile certificata.

## Sensibilità pregresse (non nuove prove OLC98)
- OLC66: `fuse_then_smooth`, `smooth_both_then_fuse`, classifier early blend, reranking logit Top10 già provati; riportarli separatamente.
- OLC67: pesi MINVAR63 × DELAY3 × FAST_LOCK3 replay nativo; non sommare CAGR di layer indipendenti.
- OLC69–70, OLC74–97: risultati di routing, allocazione, futures e short da rileggere e classificare per stabilità; non riottimizzare su data già esplorata.