# OLC66 — Rilettura della fusione ETF e ricomposizione dei layer (7 novembre 2026)

**Research only / non promuovere.** Risultati nelle tabelle e nel `REPORT_OLC66_IT.md`.

Il ranking originale FUSION è 0,475 * RETURN + 0,525 * SMOOTH, dove CURRENT è 0,6 * percentile(ET) + 0,4 * percentile(XGB), e SMOOTH applica memoria 40/30/30 al ramo CURRENT (con trasformazione di potenza originale 1,1). `TOP2_CONTEXT_REVALUE` è un passaggio successivo e distinto, non è la FUSION. V6, stop, FAST_LOCK3 e commissioni appartengono invece al motore esecutivo.

OLC66 confronta sei modifiche al solo ranking: classifier OLC11, anticipazione blend, ordinamento economico entro Top10 nativo o ampliato e due ordini alternativi memoria/fusione. Nessuna supera il ranking FUSION su entrambi i mercati nel MAIN 2021–2024. Il confronto statico non costituisce un nuovo backtest contabile con stop.

`recompose_olc19.py` importa le decisioni di selezione e le scorecard dell'engine nativo OLC19 per confrontare `ORIGINAL`, `CUM_FIT`, `TOP2_STATIC_REVALUE`, `TOP2_CONTEXT_REVALUE` a medesima data. **Le metriche contabili/rischio sono archiviate**, non rieseguite qui sui sei candidati OLC66. I codici controllano la parità originale e il test indipendente OLC66 ricostruisce 826 gruppi di scelte e 118 riferimenti al checkpoint OLC63.

## Ripristino dati

Gli originali sono nella ChatGPT Library. Eseguire `run_olc66.py`, `recompose_olc19.py` e `verify_olc66_independent.py` con gli argomenti richiesti dalle rispettive CLI `--help` e gli ZIP OLC11/14/16/19 congelati. I file binari sorgente non sono incorporati nel pacchetto OLC66; i loro digest verificati sono nei QA JSON.

Decisione: mantenere come riferimento verificato **FUSION → TOP2_CONTEXT_REVALUE → V6 / FAST_LOCK3**, senza dichiarare che sia universalmente la migliore combinazione del futuro. Il trade-off USA FULL fra `BASE` (CAGR più elevato e drawdown peggiore) e `FAST_LOCK3` (CAGR inferiore e drawdown meglio contenuto) è riportato nel report.