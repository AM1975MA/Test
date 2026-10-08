# RESET DI RICERCA DOPO L2-J — 2026-10-08

**Stato: REVISIONE, non nuova strategia.** Gli esperimenti learner sullo storico Original149 si fermano. L'intero storico è stato già riutilizzato per numerosi esperimenti; né Original149 né Holdout70 sono test freschi. `Etf_trader` rimane invariato. Questa revisione non pretende che siano stati eseguiti agenti AI indipendenti: applica in modo distinto competenze ML, economofisica, statistica e portfolio risk al codice e ai dati congelati.

## Correzioni fondamentali

1. La configurazione Compact21 canonica in `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py` e `models.py` è `rank:pairwise`, 125 feature, 360 round, 3 seed e label di rango percentile arrotondato ×100. `eval_metric=ndcg@3` non coincide con l'obiettivo ottimizzato. Rank:pairwise dà preferenze di coppie senza peso monetario per profitto, tail loss o turnover. Non inferire edge da NDCG@5 o Top5 hit soli.
2. Nel sistema completo Compact21 è un segnale, non il trader: blend 70% Compact21 / 30% Tail, regola Macro e decisione Top1/Top2 con protezioni e governor. Gran parte di L2-D→J ha studiato **Top1 isolato**. Il precedente BASE source-only full replay (vedere `compact21_stability_v1/results/FULL_REPLAY.json`) dà tre CAGR 29.75%,30.84%,34.68% (span 4.92 pp). Il Top1 proxy L2-D ha invece 19.56%,22.14%,31.88% (span 12.32 pp). Non confrontare questi oggetti per attribuzione causale senza un full replay matched.
3. Tre acquisizioni Yahoo nel 2026 sono tre copie revisionate dello stesso mercato, non tre holdout. Le ~16.837 osservazioni mese×ETF condividono rischio fattoriale e soltanto 113 date mensili OOS diagnostiche. Il corpus Original149 è "burned", come il registro `evidence_v1/RESULTS_REGISTRY.md` riconosce per i reranker già scartati.
4. **Nuovo controllo basilare, senza fitting, sul Repeat2 2017-02–2026-06 e stesse 16.837 righe:** strategia *12–1 momentum* = `Close(t-21)/Close(t-252)-1`, top1 al segnale:
   - XGB: top5 realized 19.47%; next21 net return medio +2.25%; percentile realizzato 58.2%; bottom-decile selection 19.5%.
   - Ridge: 7.96%; +1.76%; 54.9%; 13.3%.
   - Semplice momentum: **21.24%** top5 realized, ma **solo +1.07%** rendimento medio, percentile 51.5%, **26.5%** di selezioni nel decile peggiore.
   *Conclusione: il Top5 hit-rate può favorire una selezione altamente volatile e non misura la qualità economica. Questo benchmark è un controllo diagnostico, non una nuova strategia promossa.*
5. XGB refit fra acquisizioni, tutti valutati sul medesimo input e stessi ritorni Repeat2: scelte Top1 diverse 49–62 volte su 113. **Quando differiscono, il gap assoluto medio di ritorno netto futuro fra gli ETF è 5.50–7.51 punti percentuali**, con categoria identica in solo 31.7–37.1% dei casi. L'instabilità è economicamente materiale, ma non basta imporre identità nominale dell'ETF.
6. Le scelte XGB sono concentrate in real assets / emergenti / ETF settoriali; pochi US broad o bond. Occorre distinguere premio fattoriale, regime e skill di selezione. Il source-only risk engine `kernel.period_path` presuppone esecuzione dello stop a livello deterministico `STOP + STOP_SLIP` dopo un minimo infragiornaliero; verificare gap sotto stop ed eseguibilità reale. Un PnL di ricerca senza questi controlli potrebbe essere ottimistico.

## Valutazione per competenza

- **ML**: non cercare il prossimo learner. Verificare prima dove il modello produce informazione incrementale sui fattori, il motivo per cui rank:pairwise non corrisponde all'obiettivo economico, e quanto è dovuto a feature correlate o selezione estrema.
- **Statistica**: trattamento delle date mensili come cluster, backtest overfitting e multiple trials; evitare di interpretare le tre Yahoo vintage come tre campioni di mercato.
- **Econofisica**: test di heavy tails, volatilità condizionata/regimi, exposure betas e differenze fra categorie. Non trasformare segmenti ex post ad alta/bassa volatilità in regole operative.
- **Portfolio risk/execution**: attribuzione del vantaggio di Compact21 **dentro il portafoglio completo**; test matched su costi, drawdown, turnover, gap, capital-at-risk e risk-adjusted returns.

## Percorso corretto, senza nuovo tuning

**A. Data/engine gate:** universo point-in-time, adjusted OHLC & negoziabilità, stop/gap slippage, nessun forward information leakage, commissioni e calendari coerenti. Blocca i fit se ci sono anomalie materiali.

**B. Attribution gate:** usando i segnali congelati e l'intero engine, scomporre fonte del risultato in esposizione mercato, categoria/fattore, momentum, ranking ETF intraclasse, sizing e governor. Impostare baseline passive/fattoriali semplici su **stesse date, stesso rischio e stessi costi**. Testare l'effetto marginale Compact21, non un nuovo Top1 standalone.

**C. Predictive-value gate:** calcolare vantaggio **netto, a rischio comparabile e residualizzato per categoria/volatilità**; pari attenzione a coda sinistra, conditional expected shortfall, MaxDD, turnover, e regret economico delle scelte instabili. Senza incremento convincente, dismettere XGB come *decision engine* indipendente anche se NDCG è buono.

**D. Solo se B–C positivi:** formulare una domanda di apprendimento più adatta (es. decisione causale stay/select/reduce rispetto alla posizione corrente, condizionata a rischio e costi; oppure fattore/categoria prima di ETF), con capacità limitata e assenza di soglie scelte dal backtest. Non iterare sul quinto reranker: quattro tentativi e i semplici EW5/adaptive blend sono già stati scartati nel registro storico.

**E. Valutazione prospettica:** versionare ora train/labels, dataset point-in-time e schema di scoring; congelare il prossimo modello candidato prima dei nuovi mesi di mercato. Successi sullo storico già esplorato restano diagnostici e non autorizzano deployment.

## Sources

- [Canonical model source](../vendor/etf_trader_v2/src/etf_trader/source_only/models.py), [kernel](../vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py)
- [L2-D](L2D_RESULTS.md) e [L2-J](L2J_RESULTS.md)
- [Full baseline replay](../compact21_stability_v1/results/FULL_REPLAY.json)
- [Prior failed rerank/allocations](../evidence_v1/RESULTS_REGISTRY.md)
- https://xgboost.readthedocs.io/en/stable/tutorials/learning_to_rank.html ; Bailey & López de Prado *Deflated Sharpe Ratio* (2014); Rama Cont *Stylized Facts* (2001).

**NO NEW LEARNER FIT / NO PARAMETER TUNING / NO PRODUCTION PROMOTION.**
