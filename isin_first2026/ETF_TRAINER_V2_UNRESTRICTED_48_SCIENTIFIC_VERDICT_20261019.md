# ETF_TRAINER_V2 libero su tutti i 48 ETF europei — conclusione scientifica 19/10/2026

**Esecuzione source-only completa e PASS:** [GitHub Action 39320679509](https://github.com/AM1975MA/Test/actions/runs/39320679509). Branch isolato research/etf-trainer-v2-unrestricted-eu48-20261019. Sono stati realmente riaddestrati sei modelli annuali Titanium 2021–2026 e sei MA3 Hybrid24 ET+XGB, mantenendo i parametri originali, i cutoff di maturity e senza leggere storici USA di modelli, punteggi o posizioni.

## Risposta precisa alla richiesta
L'algoritmo può scegliere **liberamente ogni ETF fra i 48 ISIN europei distinti**, senza i 500 panieri da 24 fondi né il vincolo di 4 fondi per ciascuna macro-categoria. Il ranking avviene su **un solo paniere completo di 48 ETF**; ogni mese si selezionano top1/top2 dall'intera cross-section. Le categorie sono utilizzate solo come attributi delle feature; NON costituiscono un limite di selezione. Nessun ETF USA è comprabile; l'ETF IHYG.MI è consultato unicamente come segnale di stress creditizio esterno.

Il modello V2 è l'esatta regola incrementale dichiarata nel file immutato vendor/etf_trader_v2/versions/ETF_TRAINER_V2/VERSION.json: in C4/SEVERE risk-off, se il margine top1-top2 >=3% e entrambi ET e XGB favoriscono il leader, concentrarvi il 100% dello **sleeve rischioso** senza alterare gross. Con gross pieno il modello usa invece l'originale HighCAGR24. Benchmark Hybrid24 usa esattamente le medesime nuove previsioni (genuinamente refit) e gli stessi costi/execution engine, con V2 spento. V2 è tecnicamente frozen *candidate*, NON modello production-promoted neppure nell'originale 149.

## Numeri definitivi: 65 mesi, segnale 2021-01-29→2026-05-29, primo acquisto 2021-02-01→2026-07-01
Sono 1.374 sedute comuni alle 48 venue Europe; original F3/H1 comparatore usa 1.331 sedute di intersezione con i 10 fattori ETF USA. La tabella sotto ha esecuzione a Open europei autentici osservati, same dates intra-V2, costo 10bp per turnover unit, stop 5.5% e slip 0.1%, come fonte V6. Performance **calcolate con la definizione identica al modulo score originale ETF Trader**: padded NAV iniziale 1, 252 sedute/anno; primo giorno di P&L/fee non omesso.

| Statistica | Hybrid24 port 48 top2 senza vincoli | ETF_TRAINER_V2 port 48 top2 senza vincoli |
|---|---:|---:|
| CAGR netto | **+1,360158%** | **+1,636234%** |
| Max drawdown (daily Open) | **-37,193364%** | **-37,193364%** |
| Sharpe annualizzato su rendimenti semplici giornalieri | +0,17518 | +0,18698 |
| Volatilità annualizzata | 23,37398% | 23,45952% |
| Expected Shortfall peggiori 5% log giornalieri | -3,65192% | -3,66092% |
| Turnover annualizzato in quote di patrimonio | 12,40273 | **11,70417** |
| Valore finale da NAV 1 | 1,076442 | **1,092525** |

**V2 = +0,27608 pp CAGR rispetto a Hybrid24**, drawdown invariato e ES5 lievemente peggiore. Interviene **3 su 65 mesi, 41 giornate**: 2022-01-31 (10 sedute, leader EXV5.DE), 2022-06-30 (19 sedute, leader EXV5.DE), 2022-09-30 (12 sedute, leader EXV5.DE). Tutto il vantaggio è nel 2022; negli altri anni le posizioni di V2 e baseline sono identiche.

Rendimenti da ricchezza di fine periodo (2021 è Feb–Dic, 2026 è Gen–Lug, NON anni completi):
| anno | Hybrid24 | V2 |
|---|---:|---:|
| 2021 | +6,868% | +6,868% |
| 2022 | -10,205% | **-8,863%** |
| 2023 | +27,060% | +27,060% |
| 2024 | -5,475% | -5,475% |
| 2025 | -6,757% | -6,757% |
| 2026 parziale | +0,166% | +0,166% |

## Allocazione: osservazione centrale
Il Top1 mensile è un ETF IT europeo 22/65 periodi, discrezionali 14/65, finanziari 12/65, materiali 8/65, property 5/65 e altri settori 4/65 (reale tabella ALL48_MONTHLY_LEADERS...); nessun sovrano è primo. In particolare:
- XS8R.DE, settore tecnologico Europa: top1 **13 mesi**, B&H completo storico +1,19% CAGR.
- EXV5.DE, consumer discretionary/auto Europa: top1 **9 mesi**, B&H circa -0,02% CAGR.
- EXV3.DE, tecnologia Europa: top1 **9 mesi**, B&H +10,35%.
- EXV6.DE, materiali: top1 **7 mesi**, B&H +11,74%.
- EXV1.DE, banche STOXX Europe: top1 **6 mesi**, B&H storico +34,34% (rendimento noto ex-post, NON previsione realizzabile).
Quindi rendimenti deboli NON si spiegano con impossibilità del mercato Europa: precedenti buy-and-hold dello **stesso archivio** sul MSCI Europe IMEU.AS erano +12,66% CAGR, mentre equal weight azionario settoriale +11,17%; entrambi hanno rischi e calendari differenti e non sono un confronto perfettamente matched di daily execution. Il modello libero sceglie spesso ETF con rendimenti 2021-26 scarsi e il turnover ~12/anno aggiunge frizione.

## Fidelity / limiti importanti
Questo NON è il programma USA149 bit-identical: l'adattamento indispensabile, registrato nei file fonte, ha trasformato l'S3B da 7 cluster dinamici con minimo 8 fondi ciascuno a **5 cluster dinamici (min4) e un 6° sovrano**, lasciando seed26072026/PCA e matching source invariati. Ha usato MSCI Europe IMEU.AS come riferimento SPY, EUNH.DE governativo e IHYG.MI corporate in euro come credit-risk, IBCA.DE/IBCN.DE al posto di BIL/SHV come sleeve difensivo. I nuovi riferimenti non sono equivalenti economici esatti e le soglie di rischio sono ancora calibrate negli USA. Non è un test perfettamente parametrico della V2 USA, ma un test autentico del suo meccanismo portato coerentemente a 48.

Prezzi Yahoo **grezzi originali e aggiustati originali restano conservati** a monte. Nel solo input temporaneo del motore fonte, 49 barre High/Low che violavano max/min di Open/Close sono espanse in modo tracciato; Close, Open, Volume non modificati e date senza quotazioni mai riempite artificialmente. Questa correzione potrebbe influenzare l'ipotetico stop intraday; NON considerare drawdown/stop certificati broker reali. Fattori dividend-adjusted retroattivi e anagrafiche 2026-survivor non point-in-time 2017. Strategia mai promossa per esecuzione reale.

**Valutazione**: non promuovere la V2 Europe48, perché CAGR 1.64% e DD -37.19% sono economicamente scadenti e non indicano robustezza statistica. Il +0.28 pp di V2 deriva da tre soli eventi in un unico anno, insufficienti per attribuirvi potere generalizzabile. Valutare esperimenti futuri mirati al ranking predittivo e ai proxy/stop europei, non a riottimizzare marginalmente la concentrazione V2 sullo stesso campione.

## File e tracciabilità
- isin_first2026/v2_unrestricted48/results/RESULT.json — numeri netti/evidenze, flags source.
- isin_first2026/v2_unrestricted48/results/MA3_HYBRID24_48_TICKER_PREDICTIONS.csv — previsioni MA3 source 65 mesi × 48 ETF.
- isin_first2026/v2_unrestricted48/results/MA3_HYBRID24_MATURITY_FIT_AUDIT.csv — anni con label mature.
- isin_first2026/v2_unrestricted48/results/ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv — veri leader e modifiche del V2.
- isin_first2026/v2_unrestricted48/results/DAILY_NAV_DD_AND_V2_TRADING.csv — due equity curve e turnover/weight.
- isin_first2026/v2_unrestricted48/results/TITANIUM_RETRAIN_MANIFEST.json e SOURCE_AND_OHLC_REPAIR_AUDIT.csv — lineage 48 dati e genuine fits.
- isin_first2026/v2_unrestricted48/results/SHA256_MANIFEST.txt — checksum degli output economici.
- isin_first2026/v2_unrestricted48/prepare.py, train_tit.py, cluster_adapter.py, run.py, PREREGISTERED.md — sorgenti riproducibili/Test-only; zero modifiche nel privato AM1975MA/Etf_trader.
