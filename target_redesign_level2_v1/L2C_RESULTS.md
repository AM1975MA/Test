# L2-C — risultati verificati: target economici senza BIL

**Data** 2026-10-08. **Status**: DEVELOPMENT DIAGNOSTIC ONLY / NON PROMOSSO. **Repo**: solo `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. Il repository `Etf_trader` NON è stato modificato.

## Esito di ricerca

Sulle stesse feature e learner Ridge, il **target di percentile di rango continuo** resta superiore ai target di ritorno in qualità di ranking OOS storico; nessun chiaro aumento di rendimento selezionato è dimostrato per gli altri due. Tutti i Ridge sono molto stabili su piccole revisioni delle acquisizioni Yahoo, ma questo non equivale a una conferma di efficacia economica rispetto all'originale XGBoost né a una strategia investibile. **Nessuna promozione e nessun tuning ex post.**

## Fonti e riproducibilità

- Raw frozen acquisition: GitHub Actions run [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact ID `11272972639`, ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. 149 ETF, tre vintage; periodo 2004-01-01 fino al 2026-07-31. I 447 raw ticker files erano stati verificati contro gli SHA256 dei manifest originali in L2-B.
- Target generator e comparazione originale definiti in [L2-C preregistration](L2C_PREREGISTRATION.md), inserito prima della lettura dei risultati ma dopo l'avvio del primo fit (non presentare lo studio come validazione pre-registrata indipendente).
- Effettivo codice sorgente del runner standalone riproducibile come allegato `l2c_run.py`: SHA256 `d6223d98124a6e9896e9a34aeafe10597668d8a84631f2d8e808c899cc2ab82a`; inferenza sui dati comuni `l2c_common_input.py`: SHA256 `c1ba522865e1833382e8ed3dd43b0b0ceceba5b9cb3a8f7c620a6d39db222161`; analisi paired/bootstrap `l2c_infer.py`: SHA256 `41199609821642fd61306edab1d55cc4f36a18e860988cb64e2f21df6b08c129`.
- L'esecuzione finale del runner **non importa né richiede BIL**: `net_ret_21` e `alpha_spy_log_21` usano esclusivamente Open aggiustati degli ETF e di SPY. Test di parità prima/dopo la rimozione della precedente dipendenza dallo script L2-B: **51.405 righe di predictions, stesse chiavi, identità esatta bit-a-bit delle predizioni su tutti e tre i target (differenza massima = 0)**.
- Costruzione delle 125 feature Compact21 riprodotta dalle formule nel [kernel canonico di sola lettura](https://github.com/AM1975MA/Test/blob/research/compact21-orthogonal-feature-ablation-run-v1/vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py): features finali = 33 base + 33 cross-sectional percentile + 33 robust deviation + 13 addizionali + 13 percentili; input adjusted OHLCV invariati.
- `SimpleImputer(strategy='median',keep_empty_features=True) -> StandardScaler -> Ridge(alpha=30)`, train annuale expanding 2017–2026, label cutoff `signal_date<1 Jan train year` e `exit_date_21<1 Jan train year`; **train cohort identico** fra i tre target entro ciascuna vintage. 30 fits annuali (10 per vintage), tre output indipendenti per fit. Nessuna scelta di parametri dalle performance.
- 113 signal date mensili **2017-02-01..2026-06-30**, exit 21 sedute entro 2026-07-31, 149 ETF/data, 16.837 osservazioni maturate per vintage. Trattare le vintage come repliche della stessa storia: si aggregano prima entro ogni data.
- Costi per target etichetta: 0.1% al lato di acquisto e 0.1% al lato di vendita ipotizzati, non la simulazione dei costi effettivi del portafoglio. **Nessun CAGR calcolato**.

## Risultato predittivo (date equally weighted, 3 vintages averaged within date)

| Target del Ridge | NDCG@5 ↑ | Rank IC ↑ | Mean net 21-session return selected | Return regret vs actual winner ↓ | Realized top1 percentile ↑ | Realized top5 winner hit | Exact winner |
| --- | ---:| ---:| ---:| ---:| ---:| ---:| ---:|
| `rank_pct_21` | **0.561932** | **0.092917** | **+1.7618%** | **17.3764 pp** | **0.548752** | 7.9646% | 5.3097% |
| `net_ret_21` | 0.519170 | 0.043169 | +1.2473% | 17.8909 pp | 0.497832 | **11.7994%** | 6.1947% |
| `alpha_spy_log_21` | 0.533583 | 0.042284 | +1.6819% | 17.4563 pp | 0.508186 | 11.2094% | **7.6696%** |

La differenza tra metriche è informativa: il rango continuo ottiene maggiore NDCG e IC, ma **non** il migliore exact-winner hit rate. Gli esiti reali dell'ETF scelto sono molto variabili tra anni, e nessuna differenza media dei rendimenti selezionati è chiaramente affidabile. Il regret elevato è rispetto al miglior ETF *ex post* (oracolo irraggiungibile), non una perdita monetaria effettiva.

## Confronti paired contro il target rango

Bootstrap moving block da **3 date mensili**, 10.000 repliche, media vintage entro data e 113 date aggregate; intervalli 95% **descrittivi NON corretti per test multipli**:

| Candidato vs rango | Delta mean NDCG@5 | Intervallo 95% | Delta mean Rank IC | Intervallo 95% | Delta selected return | Intervallo 95% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Rendimento netto | -0.042762 | [-0.092625, -0.001932] | -0.049748 | [-0.088865, -0.006889] | -0.005145 | [-0.023995, +0.010789] |
| Extra-SPY | -0.028349 | [-0.061367, +0.006807] | -0.050633 | [-0.084538, -0.016843] | -0.000799 | [-0.017088, +0.014433] |

Il rango migliora Rank IC rispetto a entrambi. Per il solo NDCG di alpha-SPY l'intervallo include zero. Tutti gli intervalli per il rendimento del Top1 includono zero.

## Stabilità inter-vintage sul medesimo training calendar

Native inference (dati della propria vintage; 113 date per coppia):

| Model | Range Top1 agreement | Range mean rank-MAD | Range Top5 overlap |
| --- | ---: | ---: | ---: |
| Rango continuo | 99.115–100% | 0.000987–0.001146 | 99.646–100% |
| Rendimento netto | 98.230–99.115% | 0.001065–0.001859 | 99.292–99.823% |
| Extra-SPY | 98.230–99.115% | 0.001008–0.001399 | 99.646–100% |

Common input frozen at **Repeat2 inference features**, independently fit three vintages:

| Model | Range Top1 agreement | Range rank-MAD |
| --- | ---: | ---: |
| Rango continuo | **100% su tutte le coppie** | 0.000892–0.001008 |
| Rendimento netto | 99.115–100% | 0.000920–0.001731 |
| Extra-SPY | 98.230–99.115% | 0.000859–0.001174 |

Il forte aumento di stabilità rispetto al precedente learner XGB è **suggestivo ma NON un confronto scientifico perfettamente matched** contro la pipeline completa originale; l'obiettivo successivo è ricostruire un control XGB sugli stessi segnali e misure.

## Limiti e decisione

- Original149 e Holdout70 sono già development/burned; nessuno di questi numeri approva un nuovo modello per produzione.
- Le 149 serie sono ETF oggi conosciuti: possibili survivorship/inception biases; nessuna verifica punto-in-tempo dell'universo in L2-C.
- La storia utilizza adjusted OHLC Yahoo; restano problemi di revisioni, corporate action ed eseguibilità in mercato; un costo piatto per trade non corrisponde all'execution engine originario.
- Per separare learner stability e pure target sensitivity occorre confrontare Ridge vs XGB **a pari target e a pari coorte**. Il canonical XGB usa `rank:pairwise` con rilevanze arrotondate ed è quindi diverso dal Ridge continuo.
- NDCG più alto non implica automaticamente migliore Top1 profit, soprattutto nell'originale caso d'uso a concentrazione estrema.
- Ridotta volatilità della previsione non equivale a rendimento reale maggiorato. Nessun CAGR della pipeline completa è stato stimato.

**Decisione:** Non adottare `net_ret_21` né `alpha_spy_log_21` come sostituti. Mantenere **Ridge(alpha=30) su rango continuo** come candidato stabile sperimentale. Prossimo gate: XGB vs Ridge su stesse 113 date e replay decisionale/di execution congelato, senza selezionare parametri da Original149.
