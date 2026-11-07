# OLC63 — Protocollo fissato prima dei nuovi risultati: attribuzione dei componenti del ranking originale

Data: 7 novembre 2026. **RESEARCH-ONLY — nessuna promozione, nessuna modifica a OLC19/main.** Ricerca retrospettiva su dati 2019–2026 già ripetutamente esplorati; risultati non OOS vergini.

## Domanda
Perché la selezione originale Top2 resiste meglio di nuovi learner OLC60–62? Quale ruolo hanno RETURN, ET, XGB e memoria temporale **all'interno della stessa funzione FUSION originale**, prima dei layer finali?

## Fonti immutabili
- OLC14 Fitting Results ZIP SHA256 `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1`, `results/{EU,USA}_MEAN3_SCORES.csv.gz`.
- OLC16 Input Code Checkpoint ZIP SHA256 `ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7`, `inputs/{EU,USA}_FITTING_FRAME.csv.gz`.
- OLC19 Rischio Rientro Checkpoint ZIP SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`, `restore/olc18_execution_20261102/inputs/{EU,USA}_ORIGINAL_DECISIONS.csv`.

Non caricare ulteriori quote né rifare fitting. Le etichette future sono **solo** per valutazione; nessun target futuro usato nella costruzione dei punteggi.

## Identità matematica e gate QA
In ciascun mese/mercato, `ET_rank=rank_pct(ORIGINAL_P15_ET)`, `XGB_rank=rank_pct(ORIGINAL_P15_XGB)`, `CURRENT=.6 ET_rank+.4 XGB_rank`, smoothing temporale sui ticker `.4 CURRENT(t)+.3 CURRENT(t−1)+.3 CURRENT(t−2)` con missing renormalization e potenza 1.1, `FUSION=.475 RETURN+.525 SMOOTH`. Ricostruire `ORIGINAL_CURRENT`, `ORIGINAL_SMOOTH`, `ORIGINAL_FUSION` entro tolleranza `1e−12` e l'insieme Top2 di **90/90** segnali per mercato contro le decisioni originali OLC19. Ties distribuiti fra pari come nell'engine `topk_weights`, senza sort alfabetico per punteggi pari.

## Disegno sperimentale congelato
Analisi fattoriale di **4 componenti**: `R=RETURN`, `E=ET_rank`, `X=XGB_rank`, `M=memoria` (16 sottoinsiemi). Un componente R/E/X assente è sostituito da **0,5 costante neutra**, e i pesi originali restano **immutati**, non rinormalizzati. Se M è assente, `SMOOTH=clip(CURRENT,0,1)^1.1`; se presente, usare identica gestione dei 2 lag dell'engine originale. Full-on ricostruisce bitwise/1e−12 FUSION. No tuning di soglie, orizzonti, proporzioni o subset dopo i risultati.

Score neutro (R/E/X assenti) costante in ogni mese: tutti gli ETF eleggibili hanno peso `1/n`. Escludere dal confronto **a posteriori** i mesi con etichette di rendimento mancante per qualunque ETF eleggibile; non usare la mancanza del futuro per alterare eleggibilità o Top2. Periodo primario 2021–2024, diagnostico secondario 2025, separati EU/USA. 2019–2020 esclusi dai confronti principali per criticità storica di osservabilità Xetra. Valutazione statica prospettica Open→Open a 21 e 42 sedute, non NAV né CAGR, costi non applicati.

Output primari:
1. Contributo **Shapley esatto** di ogni componente al rendimento statico Top2 **meno media uniforme dell'universo**, su 16 subset, per mese, separatamente per 21/42 sedute e mercato. Riportare somme, interazioni e valori negativi. Questa è attribuzione descrittiva condizionata alla rappresentazione neutra, non effetto causale o alpha validato.
2. **Leave-one-component-out** contro FUSION originale: differenza rendimento medio a 21/42 sedute; quota mesi con modifiche Top2, win/loss quando differisce; correlazione dei componenti, beneficio distinto dallo score globale.
3. Distribuzione annuale del contributo, bootstrap circolare a blocchi di 6 mesi descrittivo (5000 repliche, seed 63001), sensibilità leave-one-year-out. Nessun p-value corretto per l'intera ricerca.
4. Orizzonti originali 21/42/63: **solo diagnosi di head** C21_ET/XGB, C42_ET/XGB, C63_ET/XGB e loro blend 60/40, confrontati sul medesimo supporto statico. Questi **non** sono addendi diretti della FUSION (i modelli ORIGINAL_P15_ET/XGB sono stati addestrati su target composito); non interpretarli come ablation del modello originario.
5. Verifiche metriche e parità su supporto, source hashes, decisioni e tie policy. Valutazione 2025 solo diagnostica, non scelta di vincenti.

## Gate / interpretazione
Il test non autorizza cambi ai pesi né promuove un nuovo score; identifica componenti ridondanti, complementari e rischio di selezione della coda. Segnalare che la sola sostituzione a 0.5 influenza le interazioni; Shapley non costituisce una stima causale né un test indipendente OOS. Qualsiasi ristrutturazione successiva richiederà nuovo protocollo e nuove osservazioni o validazione rigorosa predefinita.