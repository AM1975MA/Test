# L2-C — protocollo prima della lettura degli esiti

**2026-10-08.** Repo ammesso: solo `AM1975MA/Test`. Il canonico `Etf_trader` resta invariato. Original149 è "burned": ogni confronto di questo studio è **solo ricerca diagnostica**, non prova out-of-sample nuova.

## Modifica richiesta dal committente: eliminazione BIL

Il riferimento BIL è **totalmente rimosso dagli obiettivi di fit** e dalla regola di eleggibilità: escludeva 2.817 osservazioni storiche a 21 giorni. SPY resta un comparatore opzionale perché già presente nella storia 2004+, non un sostituto di BIL come "cash".

## Vettore di modelli (fisso; nessuna selezione da CAGR)

Stesse **125 feature Compact21** ricostruite secondo `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py`; stesso universo 149, stessi dati adjusted OHLC 2004-2026, stessi cutoffs 2017-2026, stessi segnali mensili, stessa regola di feature coverage `>=30`, stessa pre-elaborazione `SimpleImputer(strategy=median,keep_empty_features=True) -> StandardScaler -> Ridge(alpha=30)`. Le trasformazioni sono fittate solo sul training.

L'implementazione di test può stimare simultaneamente i tre target mediante Ridge multioutput: equivale matematicamente a tre Ridge indipendenti che condividono X, cutoff e alpha, senza blending.

1. `RANK_PCT`: percentile continuo dei ritorni Open(+1)→Open(+22) a 21 sessioni, controllo rappresentazione storica (NON l'XGBRanker canonico).
2. `NET_RETURN`: rendimento Open→Open a 21 sessioni, con due costi costanti `0.1%` per lato.
3. `SPY_ALPHA`: log(1+NET_RETURN) - log(SPY Open_exit/SPY Open_entry).

**Coorte training identica** per i tre target: per anno `signal_date<cutoff AND exit_date_21<cutoff` e tre target finiti e 30+ feature non-missing. Nessun filtro su target realizzato nel periodo di inferenza. Fitting annual expanding.

## Qualità e robustezza: lettura diagnostica

Su periodi mensili `2017-02-01..2026-06-30` maturati entro `2026-07-31`, valutare top1 net return, realized return regret vs winner, percentile del top1, hit top5, top1 exact, NDCG@5 con rank economico, Spearman predetto-vs-realizzato. Le tre vintage sono il medesimo mercato: aggregare entro data *prima* di aggregare metriche; riportare breakdown annuale.

Per ciascuna delle tre coppie di vintage, confrontare su sole chiavi native di inferenza comuni: rank-MAD, Top1 agreement, Top5 overlap. Separare il concetto di stabilità della label dalla stabilità del learner. Per considerare una soluzione plausibile occorrono **qualità predittiva e stabilità entrambe**; evitare una scelta basata soltanto sul risultato medio o sul CAGR.

La validazione qui non usa un holdout nuovo: nessun modello può essere promosso in produzione. Non eseguire backtest portfolio né tuning iperparametri, per evitare contaminazioni ulteriori.

## Deliverable

Codice e metriche del runner riproducibili come artefatti della conversazione e, dove fattibile, summary su `Test`. Nessuna scrittura a `Etf_trader`. Conservare fit audit e score native per ogni data/ticker/vintage.
