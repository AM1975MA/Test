# Original149 — Ranking globale + Top5 a due stadi: risultati finali (20 ottobre 2026)

**Completato, eseguito e verificato indipendentemente.** Ramo `research/original149-two-stage-top5-20261020`, produzione invariata. Esperimento primario: https://github.com/AM1975MA/Test/actions/runs/39496396121 (SUCCESS). Audit indipendente: https://github.com/AM1975MA/Test/actions/runs/39496838738 (SUCCESS).

## Domanda e protocollo preregistrati

L'ipotesi era che si potesse migliorare la selezione dei migliori 5 ETF in due fasi: prima un modello poco profondo ordina tutti gli ETF per estrarre candidati, poi un modello più profondo riordina la shortlist. Nel run di profondità precedente, RankIC globale cadeva aumentando le foglie, mentre la coincidenza con la vera Top5 aumentava: le due metriche non sono equivalenti.

Utilizzati **solo score originali fuori campione già congelati** del run https://github.com/AM1975MA/Test/actions/runs/39492170319. Nessun XGBoost riaddestrato. File `ALL_OOS_SCORES.parquet` originali per d=2,3,4,5,6,7, stessi esatti **70.924 ticker-date su 476 settimane**. Verificati SHA roster, mapping ticker/id, date, future labels, individual Top5 e metriche originali. Sei esperti singoli, quattro sistemi a due stadi e due fusioni statiche 50/50, fissati **prima** dei risultati in `TWOSTAGE_PREREGISTRATION.md`. Top5 long-only equal-weight, ingresso open(t+1), uscita open(t+6), 20bp roundtrip ad ogni ciclo, NAV giornaliero come baseline. Tutte le regole di selezione usano solamente gli score predetti e mai i rendimenti futuri. I punteggi XGB identici vengono ordinati in modo deterministico per ticker_id.

## Risultati 2017–giugno 2026

| Strategia | RankIC | CAGR netto | MaxDD | Sharpe | True Top5 overlap |
|---|---:|---:|---:|---:|---:|
| Singolo XGB profondità 2 (4 foglie max) | .06789 | +6.31% | −41.94% | .3667 | 5.88% |
| **Singolo XGB profondità 3 (8 foglie max)** | .06373 | **+17.48%** | −43.58% | **.7648** | 9.33% |
| Singolo XGB profondità 4 (16 foglie max) | .05910 | +15.57% | −41.57% | .7115 | 10.67% |
| Singolo XGB profondità 5 (32 foglie max) | .05342 | +10.38% | −42.92% | .5141 | 11.47% |
| Singolo XGB profondità 6 (64 foglie max) | .03865 | +8.17% | −42.59% | .4418 | 11.89% |
| Singolo XGB profondità 7 (128 foglie max) | .03594 | +4.37% | −46.97% | .2959 | 12.35% |
| Filtro profondità 3 Top20 → profondità 4 Top5 | .06339 | +13.71% | −42.33% | .6517 | 9.29% |
| Filtro profondità 3 Top20 → profondità 7 Top5 | .06310 | +6.48% | −46.52% | .3730 | 10.04% |
| Filtro profondità 3 Top30 → profondità 7 Top5 | .06268 | +7.87% | −45.34% | .4216 | 10.76% |
| Filtro profondità 2 Top20 → profondità 7 Top5 | **.06751** | +7.15% | −42.71% | .3941 | 7.77% |
| Blend di ranghi 50/50 profondità 3 e 4 | .06216 | +14.10% | **−41.23%** | .6682 | 8.91% |
| Blend di ranghi 50/50 profondità 3 e 7 | .05366 | +10.66% | −44.66% | .5225 | 10.42% |

**Esito:** il metodo semplice «seleziona con alberi poco profondi, riordina con alberi profondi» non supera il miglior esperto singolo depth3 nel CAGR storico e non introduce una combinazione rischio-rendimento chiaramente migliore. Il BLEND3_4 riduce leggermente il massimo drawdown vs depth4 (-41.23% vs -41.57%) ma riduce il CAGR di 1.47 punti annui. Nessun modello è candidato alla produzione in base a questi soli backtest.

## Audit statistico realmente eseguito

Il workflow indipendente 39496838738 ha rilevato che tutte le **12 strategie condividono precisamente 476 date**, gli esperti depth3/depth4 riproducono i loro benchmark in RankIC, CAGR e MaxDD, ed ogni metodo usa lo stesso costo. Bootstrap circolare con **5 settimane di blocco**, 2400 estrazioni, intervalli descrittivi al 95% (storico intensamente minato, non CI corretti per ricerca multipla).

Variazione rispetto all'esperto depth3, migliore CAGR storico:

| Metodo ibrido | Δ RankIC [IC 95%] | Δ rendimento nominale medio Top5 ogni 5 sedute in punti percentuali [IC 95%] |
|---|---|---|
| d3 Top20 → d4 | −.00034 [−.00087,+.00017] | −.06478 [−.22199,+.06478] |
| d3 Top20 → d7 | −.00063 [−.00124,−.00005] | **−.19029 [−.41478,−.00243]** |
| d3 Top30 → d7 | −.00105 [−.00207,−.00010] | −.16117 [−.38248,+.03517] |
| d2 Top20 → d7 | +.00378 [−.00426,+.01324] | −.17661 [−.40664,+.02447] |
| Blend d3/d4 | −.00157 [−.00410,+.00100] | −.06193 [−.17547,+.04101] |
| Blend d3/d7 | −.01007 [−.01797,−.00293] | −.11496 [−.29213,+.04134] |

Il riordinamento profondo aumenta talvolta la frequenza di presenza degli ETF realmente top5, ma gli errori che restano possono essere economicamente costosi. In particolare d3 Top30 → d7 aumenta il Top5 overlap di 1.43 punti percentuali vs depth3, senza miglioramento positivo del payoff. **Non confondere Top5 overlap, RankIC e media rendimenti Top5.**

## Controlli operativi / deviazioni non scientifiche

Due tentativi intermedi si sono fermati correttamente durante controlli automatici, senza produrre performance valide: un caso di parità degli score depth7 ha evidenziato una differente regola di tie-breaking; poi il confronto tra valori originali CSV e ricostruiti da Parquet richiedeva un'impossibile esattezza 1e-10. Corretto tie-breaking per ticker_id e utilizzata tolleranza aritmetica 1e-6 per metriche, mantenendo **identiche le selezioni Top5** dei sei modelli; registrati i differenziali massimi e verificati i dati. Risultati considerati soltanto dal run successivo verde 39496396121; nessuna regola economica modificata dopo osservazione risultati.

Sorgenti `two_stage_top5.py`, `test_two_stage_top5.py`, `verify_two_stage_top5.py`, protocolli e workflow nel ramo dedicato. Artefatti contengono `REPORT.json`, `OOS_WEEKLY_SELECTIONS.csv`, `DAILY_NET_EQUITY.csv`, `PERFORMANCE.csv`, `ANNUAL_BY_MODEL.csv`, `SHORTLISTS_AS_OF.csv`; indipendente `INDEPENDENT_AUDIT.json`, `HYBRID_VS_FROZEN_SINGLE_95CI.csv`.

## Direzione successiva motivata dai dati

L'esperimento **falsifica il semplice stack senza training** come fonte di alpha aggiuntivo stabile. Le capacità diverse tra modelli emergono realmente, ma non basta selezionare i top20 e delegare il riordino a un modello più profondo. Se si prosegue, la formulazione sensata è apprendere un meta-modello *parsimonioso* **sui rendimenti nominali e sul downside della Top5** con precedenti score OOS, addestrandolo su sole settimane precedenti già maturate, e un **vero holdout nuovo/disgiunto**; evitare ulteriori tuning retrospettivi sullo stesso 2017–2026. Un modello d3 congelato rimane benchmark per CAGR, d4 per DD. Nessuna promozione in produzione.

**Limiti:** Original149 ETF scelti retrospettivamente, dati aggiustati e costi di transazione semplificati, 476 settimane ripetutamente osservate, bootstrap esplorativo, nessuna verifica prospectiva live.
