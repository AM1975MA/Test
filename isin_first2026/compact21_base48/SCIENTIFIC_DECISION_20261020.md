# Compact21 BASE autentico su 48 ETF europei (20 ottobre 2026)

## Verdetto
**Test realmente completato e verificato:** [GitHub Actions 39343219473](https://github.com/AM1975MA/Test/actions/runs/39343219473) (conclusion SUCCESS). Compact21 BASE, da sorgente canonico con **125 feature, XGBoost rank:pairwise, 360 round e tre seed 101/202/303**, riaddestrato per ciascun anno 2021–2026 sul solo universo **48 diversi ISIN Europe-underlying**, senza 500 panieri e senza vincoli settoriali, **non sviluppa capacità predittiva utilizzabile**: Spearman medio cross-section al vero orizzonte 21 sedute soltanto +0.0251; Top1 selezionato percentile medio 50.577%, meno del percentile casuale atteso (49 rank media /48 = 51.042%). Il Top5 ha excess log futuro a 21 sessioni -0.00000085 per mese, praticamente nullo, prima dei costi. Il piccolo CAGR positivo deriva dall'evoluzione del mercato e da complesse esposizioni contingenti, non da alpha provata.

## Parametri originali e input immutati
- Fonte XGB autentica: vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py, funzione originale build_features() e add_labels(); fitting originale compact21_learner_swap_v1.learners.fit(...,'BASE'), originale worker isolato _xgb_worker.py, senza cambiare COMPACT_PARAMS, seeds, objective, label_rank21, pari a 360 iterazioni per ciascun seed. Sei veri fit annuali e original 48 legal ISIN:
  - 2021: 2,208 training ETF-mese, 46 mesi target già maturi; 2022: 2,784/58; 2023: 3,360/70; 2024: 3,936/82; 2025: 4,512/94; 2026: 5,088/106.
  - Target vero: rendimento EUR Open→Open delle successive 21 sedute europee, rank percentuale fra 48 ETF della medesima data. Ogni training fold ha il massimo exit_date_21 strettamente precedente al 1 gennaio dell'anno in prova. Non vengono usate previsioni o modelli già fittati sui 149 USA.
- SPY originale usa l'ultimo Close adjusted USA già pubblicato nel calendario **precedente** alla seduta europea, come fattore mkt beta/correlazioni. SPY non entra nel rank, l'unico sourcing patch nella originale funzione build_features è mkt=US_SPY_PRIOR_EU_DAY_RET.reindex(ret.index) invece di fallback della mediana quando SPY non è ETF candidato. Nessun ETF non europeo eleggibile. Le 48 quote EUR usano l'originale upstream 2015–2026 rivisto, con 49 correzioni solo High/Low su derivato e Open/Close invariati.
- Contratti monetari: 65 mesi segnale Jan2021–May2026, operazioni da Feb2021 a Jul1 2026, 1,374 Open autentici comuni delle 48 venue, 10bp per notional di acquisto e vendita, EUR patrimonialmente finanziato, Top1/Top2/Top5 a pesi 100%,50%,20%, rebalance mensile. NO stop, DD controller, V6 o concentrazione extra. Confronto stessa data e stesso motore con MA3 originale e ADAPT4 congelato dalla ricerca precedente.

## Risultato economico (CAGR netto, NO Full-V2)
| Metrica | Compact21 BASE | MA3 originale | ADAPT4 online |
|---|---:|---:|---:|
| CAGR Top1 | **+4.7279%** | +3.6168% | +17.5694% |
| CAGR Top2 | **+3.7339%** | +6.0086% | +17.5927% |
| CAGR Top5 | **+4.9605%** | +8.1956% | **+15.3732%** |
| MaxDD Top5 | -22.7582% | -23.4215% | -24.9017% |
| Sharpe giornaliero log Top5 | +0.3119 | +0.3940 | +0.8058 |
| 21-session signed Spearman, 65 signal dates | **+0.02512** | +0.04066 | **+0.05193** |
| Spearman per month-calendar Open/ Open | +0.01884 | +0.04823 | +0.05679 |
| Realized future target percentile Top1 (mean) | 50.577% | 51.250% | 59.359% |
| Future 21-session Top5 equal48-relative log (mean monthly) | **-0.000085%** | +0.09237% | +0.62757% |
| Realized next month Top5 vs equal48 (mean monthly log) | -0.08648% | +0.09347% | +0.65982% |

Il modello non migliora significativamente MA3 sulla capacità di classificazione: differenza signed Spearman Compact–MA3 -0.01553, bootstrap paired blocchi di 3 mesi CI 95% [-0.0672,+0.0414]. Per ritorno relativo a 21 giorni Top5 rispetto ad ADAPT4: -0.62766 punti percentuali log per data, bootstrap CI circa [-1.2203,-0.0345] punti, esploratorio (il campione era già oggetto di numerose ricerche). Non un'osservazione prospettica nuova.

## Non uniformità temporale: Compact21 forecast rank
Spearman mese per mese medio, contemporaneo col futuro 21 sedute:
- 2021 +0.0315; 2022 +0.0909; 2023 +0.0574; **2024 -0.0328; 2025 -0.0722**; 2026 fino a maggio +0.1472 (solo 5 osservazioni).
- Top1 cade nel *vero miglior decile dei 48* in 10 di 65 mesi (15.4%, contro 5/48≈10.4% random): 0 nel 2021, 5 nel 2022, 0 nel 2023, 2 nel 2024, 0 nel 2025, 3 nei 5 primi mesi del 2026. Tuttavia percentile medio Top1 50.58%, proprio perché quando sbaglia può finire lontano dai migliori. I 10 eventi di hit su 65 non costituiscono prova di skill per un modello campionato post-selezione universo.

## Render annuale Top5 su Open autentici, prezzi in EUR
2021 Feb–Dec +16.964%, 2022 -7.228%, 2023 +6.626%, 2024 -0.297%, 2025 +3.611%, 2026 Jan–Jul1 +8.718%. Da non confondere i due anni parziali con CAGR annuale.

## Cosa NON indica il risultato
- Il **31.76% CAGR USA149 BASE** discusso in precedenza appartiene a un sistema **completo** con altri ranker, componenti e risk controller, secondo le tre revisioni di fonte, **non** al Compact21 isolato e non sul solo periodo europeo 2021–2026. Neppure il 30.96% rerank Top5 è un Compact21 standalone. Non è lecito confrontare quei CAGR con +4.96% qui come misura di sola transferable alpha.
- Il sistema full V2 originale Europa48 **già includeva** Compact21 e Compact63, MA3 e risk source; i precedenti replay con riferimento EU +1.64% e con SPY/HYG/IEF originali refittati circa -0.22% mostrano che l'insieme è peggiorato; questo studio separa specificamente il Compact21 BASE nel suo obiettivo originale di 21 sedute, invece di confondere i layer.
- I 48 sono ETF sopravvissuti e selezionati nel 2026, non universo point-in-time 2017; quotazioni vendor adjusted e possibili mismatch cross-venue e spread in real trading. Il periodo di sviluppo e valutazione è già stato molto esplorato.
- Nessuna spiegazione definitiva che lo scarso Compact21 dipenda SOLO dalla geografia. Cambiano oltre ai sottostanti la numerosità cross-section, duplicazioni settoriali dei costituenti, training disponibile, regime e maturità; ogni singola causa richiede un'ablazione.

## Evidenze e dati congelati in Test
Branch: research/eu48-compact21-base-original-125-20261020; workflow Actions SUCCESS 39343219473. Source protocol e run in isin_first2026/compact21_base48/PREREGISTERED.md e run.py. Output:
- results/RESULT.json — tutti i 9 portafogli standalone e CI paired
- results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv — 3,120 punteggi realmente stimati prima dei payoff
- results/FITTED_3SEED_ANNUAL/ANNUAL_125F_XGB_21DAY_MATURITY_AND_SEED_AUDIT.csv — 6 fit source train hashes, sample and target maturity
- results/MONTHLY_21_SESSION_AND_NEXT_MONTH_FORECAST_SKILL.csv — 65 mesi × 3 metodi × 3 K; 21-session source target, nextmonth forward
- results/DAILY_COSTED_NAV_48_ISIN_9_STANDALONE_METHODS.csv — 1,374 sedute e 9 equity curves
- results/MONTHLY_TOP1_TOP2_TOP5_UNIQUE_ISIN_SELECTIONS.csv — costed investing TopK one fund/one ISIN
- results/SOURCE_AND_ISIN_INPUT_AUDIT.json — archived USD SPY and EUR source SHA lineage; results/SHA256_MANIFEST.txt — checksum.
- AM1975MA/Etf_trader production remain UNCHANGED.

**Research recommendation:** keep Compact21 BASE as a control. Do not use it as an autonomous Europe48 alpha estimator based on these data. Further prospectively independent testing is needed for ADAPT4; do not select new backtest hyperparameters on already repeatedly observed EU48 data.
