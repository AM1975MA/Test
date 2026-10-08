# L2-L — Revisione integrale della V2 e diagnosi della forma delle traiettorie

**8 ottobre 2026 — ANALISI TECNICA E SCREENING DIAGNOSTICO COMPLETATI; ZERO MODELLI ADDESTRATI, ZERO PROMOZIONI.** Scope GitHub: **solo `AM1975MA/Test`**, branch `research/target-redesign-level2-v1`. `Etf_trader` resta invariato. [Protocollo L2-L congelato PRIMA dei risultati](L2L_MORPHOLOGY_PROTOCOL.md), commit `b186fe5757e63e4552093d9f4a71d82a79b9c9fa`.

## Esito principale

**Non abbandonare il CAGR per cercare un ranker stabile**. L'obiettivo della ricerca non è un Alpha arbitrario con Top1 immutabile, ma conservare la capacità della **Annual V2 integrale** di catturare movimenti favorevoli, distinguendo in tempo reale le strutture ad alta volatilità che hanno *potenziale positivo* da quelle che hanno rischio di coda negativo. Non confondere la produzione di un ranking relativamente stabile con il riconoscimento del movimento più favorevole.

### I numeri non comparabili usati in precedenza

1. **Golden Annual V2 storica riferita nelle conversazioni precedenti**, periodo **2017-02-01→2026-07-01**, unrestricted 149 ETF, CAGR **43.145952%**, MaxDD **−25.0358%**, Sharpe **1.3635**, terminal equity circa **29.013×**, turnover circa 12.81×. È una **baseline storicamente riportata**, non ricalcolata in L2-L; la ricostruzione della sua provenienza è priorità P0. Fu calcolata con Parquet congelati e uno stato software non ancora integralmente fingerprinted.
2. **Replay full V2 BASE** testato successivamente su 3 revisioni Yahoo, con CAGR **29.753%, 30.844%, 34.677%** in `compact21_stability_v1/results/FULL_REPLAY.json`; sul Repeat2 circa **30.844%**. Questo replay include i componenti della catena integrale; non è un test prospettico nuovo. Una precedente ricostruzione della stessa linea ha indicato **31.604%**; prima di attribuire la differenza al modello occorre distinguere versione dati, date di taglio, runtime, code/revisions and artifacts.
3. **13.81%** L2-K: portafoglio diagnostico `TIT_R` Top2 **75/25 senza MA3/HighCAGR24/V6**, fee e calendario propri. **Non è lo stesso oggetto economico del 43.146%** e non deve essere usato come suo denominatore di degradazione.
4. Non utilizzare lo storico Original149 né Holdout70 ormai studiati ripetutamente come convalida intatta, anche quando si fissa il protocollo prima di un nuovo esperimento della stessa lunga ricerca.

**Gate P0:** identificare artifact storico, hash degli esatti 5 Parquet, raw manifest, codice/commit, versioni Python/numpy/sklearn/xgboost/numba, universi e membership, costi, MA3 producer, risk governor ed engine. Recuperare P&L per data, turnover, posizioni e loro scale numeriche. Ri-eseguire golden end-to-end con stessi identici input/versioni o motivare la mancata riproducibilità prima di giudicare feature o learner. Quindi eseguire un *input-swap* controllato (stesso codice, vintage vecchia vs nuova) e uno *engine-swap* (stessi identici scores/prezzi, diverse versioni risk) per attribuire i circa 11–12 punti percentuali persi in un replay successivo, ove effettivamente confrontabile. **Non promettere che sia possibile riprodurre 43% senza gli originali.**

## Audit della rappresentazione attuale: l'idea dell'utente è già presente parzialmente

**Compact21 F2D:** 125 caratteristiche scalari, fra cui `mom5/10/21/42/63/126/252`, `efficiency21/63/126`, `vol/downvol21/63/126`, `drawdown`, `skew/kurt63`, `acc_mom_5_21`, `acc_mom_21_63`, `gkvol21`, `rsi14`, `positive_frac63`, `autocorr1_63`, `sign_entropy63`, percentili e deviazioni cross-sectionally.

**MA3 source producer**: 42 altre features, fra cui `jerk_rank`, `slope_21/63_rank`, `eff_63_rank`, `directional_energy_63_rank`, `dominant_energy64_rank`, accelerazione, volatilità a 10–126 sessioni, indici rispetto al cluster, `atr_ratio_rank`. Source: `vendor/etf_trader_v2/src/etf_trader/ma3/producer.py`.

Quindi **non è vero che il sistema ignori variabilità, accelerazione o regolarità**. Manca però una rappresentazione comune e coerente del **profilo temporale ordinato**: coefficienti dei segmenti passati, persistenza e continuità del drift, fit di trend detrended, concentrazione dei salti, transizioni tra regimi e correlazione con shock di mercato. Le 125 feature riducono una curva a una collezione di riassunti; due percorsi con stessa volatilità/momentum possono avere sequenze molto differenti. L'associazione statistica marginale non è sufficiente per concludere che un encoder di traiettoria sarà migliore.

## Nuovo controllo: diagnosi della forma delle curve, senza fitting

Abbiamo calcolato **11 descrittori predefiniti** (63 sessioni di ritorni fino alla data del segnale, oppure 252 per l'unico controllo momentum 12−1) sui **149 ETF × 113 mensilità = 16.837 righe**; prezzi Repeat2 adjusted Close; forward return Open-to-Open 21 sessioni da score già congelati L2-D. Zero feature dal futuro; universo storico già studiato e revisionato nel 2026. Audit indipendente **PASS**, 50 estrazioni date/ticker ricontrollate sugli originali (errori <1e−15), nessuna chiave duplicata, fonte ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`.

| Descrittore | Mean date-level cross-sectional Spearman IC vs forward21 | IC dopo confronto intra-categoria | Correlazione media con XGB score |
|---|---:|---:|---:|
| `mom63` | +0.0027 | +0.0067 | +0.3084 |
| `positive_day_share_63` | +0.0197 | +0.0226 | +0.2071 |
| `trend_t_63` (OLS log-close slope t-stat) | +0.0124 | +0.0261 | +0.1478 |
| `trend_r2_signed_63` | +0.0129 | +0.0176 | +0.2726 |
| `path_eff_signed_63` | +0.0023 | +0.0211 | +0.1440 |
| `accel_21_vs_42` | +0.0080 | +0.0333 | −0.0626 |
| `vol_63` | **+0.0487** | **−0.0003** | **+0.6813** |
| `vol_ratio_21_42` | −0.0070 | −0.0102 | +0.0335 |
| `single_jump_share_63` | +0.0213 | +0.0274 | +0.0728 |
| `sign_change_rate_63` | +0.0081 | −0.0122 | +0.1055 |
| `mom252_ex21` | +0.0093 | +0.0172 | +0.3063 |

**Interpretazione delicata:** la volatilità globale sembra associata ai risultati futuri perché identifica soprattutto esposizione a categorie estremamente variabili; l'associazione scompare quasi completamente **within-category**. Il punteggio XGB è fortemente correlato a volatilità (Spearman +0.681 mediamente sulle 113 cross-sections). Di fatto il **Top1 XGB appartiene alla metà più volatile degli ETF nel 94.7% delle date** (Repeat2). Top1 solo 59.3% con trend positivo t-stat; XGB sceglie spesso anche rimbalzi/asset in ribasso. Non attribuire causalmente il rendimento agli indicatori prima di un esperimento condizionale matched.

Il primo screening delle curve ha altresì rivelato **NON-stazionarietà**:
- `accel_21_vs_42` IC medio **−0.0486 (2017–21) vs +0.0697 (2022–26)**;
- `trend_t_63` +0.0401 vs −0.0178;
- `positive_day_share_63` +0.0414 vs −0.0041;
- `vol_63` +0.0515 vs +0.0456, ma il suo IC intra-categoria resta nullo mediamente sull'intero periodo.

Per i tre confronti preregistrati contro il solo `mom63`, differenze IC e CI 95% *esplorative* per bootstrap mesi in blocchi di 3, 5k ripetizioni:
- trend_t − mom63: **+0.0097**, intervallo **[−0.0206,+0.0353]**;
- positive days − mom63: **+0.0170**, intervallo **[−0.0134,+0.0495]**;
- acceleration − mom63: **+0.0052**, intervallo **[−0.0720,+0.0854]**.
**Tutte contengono zero; nessuna feature è qualificata come miglior predittore marginale per questo test.** Gli IC intra-categoria sono diagnostici, non stime di rendimento economico e non isolano l'effetto di beta/fattori o delle altre 125 features.

### Quattro stati di rischio/forma descrittivi (nessuna strategia)

Median volatility cross-sectional date, segno slope OLS recent 63d:
- LOW-vol/downtrend: next21 mean +0.352%, top5 realized 1.95%, worst-decile outcome 6.56%.
- LOW-vol/uptrend: +0.246%, top5 0.61%, worst-decile 5.54%.
- HIGH-vol/downtrend: +0.404%, top5 7.42%, worst-decile 19.57%.
- HIGH-vol/uptrend: **+0.722%**, top5 6.48%, worst-decile 15.75%.

Le aree **ad alta volatilità sono al contempo fonte di Top5 winners e di moltissimi bottom-decile losers**. La regolarità da sola non separa i due tipi. Questi sono valori medi pooled per gruppo, non corrispondenze di un portafoglio reale e non profitti causalmente catturabili.

## Valutazione da prospettive specialistiche — non fake agents

**ML/Signal processing**: problema non è che manchi un altro algoritmo; occorre separare una *rappresentazione ordinata multi-window* della curva da basi già fortemente correlate, preservare i ranker e policy che producevano 43%, e misurare solo contributo marginale netto. Un eventuale upgrade comincia da un piccolo set predefinito di shape descriptors non già duplicati, poi da segment embeddings e interazioni condizionali su regimi. Non lanciare una deep CNN senza numerosità di date veramente indipendenti.

**Econofisica**: la strategia sembra esposta a un regime high-dispersion/high-volatility. Occorre caratterizzare *volatilità con convex upside* contro *left-tail jump risk*, autocorrelazione e clustering, asimmetria dei salti, volatilità di volatilità, trend pre-shock, comportamento relativo al macrosettore. Un smoothness-only filter molto probabilmente elimina opportunità e taglia CAGR. Considerare 21/63/126 sessioni; esponenti di Hurst e frattali su finestre brevi sono instabili e NON costituiscono scorciatoie predittive.

**Statistica**: almeno 149 serie contemporanee sono cross-correlate: la numerosità temporale qui è solo **113 mesi**, con storia già bruciata. Target forward 21/42/63 e segnali mensili possono sovrapporsi; serve purging per label maturity, embargo esplicito se fold con test non puramente successivo, standardizzazione/trattamento missing train-only, block bootstrap, DSR e un vero periodo futuro. Più feature senza questo controllo crea pseudo-edge.

**Risk & Execution**: exact parity 43.146% Golden vs nuovi replay è P0. Misurare odds dei grandi win, perdita nei peggiori mesi, contribution-by-leg e per regime, non solo Top5 o NDGC. Non scambiare la vecchia funzione ausiliaria `kernel.period_path` con la contabilità monetaria MA3 `ddfirst.py`/`v6.py`; preservare Basket/HighCAGR24/V6 con costi, gap, fills, gross e drawn-down giornalieri, non mensili.

**Disclosure on agents:** nella sessione attuale non sono disponibili subagenti indipendenti invocabili; le quattro prospettive sono verifiche analitiche dello stesso assistente, basate su codice e dati. Non presentarle come quattro esperti esterni che abbiano votato.

## Nuova roadmap rigorosa — non iterazioni casuali

**Gate 0: RECUPERO 43.146%** — riconciliare vecchio Golden e 31.6% sui prezzi/versioni congelati con budget P&L giornaliero e layer contribution; se il golden non è riproducibile, dichiararlo esplicitamente. Questo è il principale lavoro da completare, prima dei nuovi training.

**Gate 1: SIGNATURE/SHAPE DIAGNOSTIC** — salvare causalmente per ogni ETF gli ultimi 21/63/126 ritorni standardizzati rispetto a categoria e volatilità storica; aggregare un *piccolo set fissato* di: trend fit R² e slope, signed path efficiency, acceleration and jerk, directional consistency, jump concentration and asymmetry, vol-of-vol, cluster-relative trend. Molte esistono già, devono essere **ablationed** invece che duplicate; nel test L2-L non si è dimostrato alcun vantaggio marginale, quindi quest'ultimo resta un'ipotesi.

**Gate 2: TARGET ECONOMICO CONDIZIONALE** — non addestrare un modello per diventare soltanto meno volatile. Se Gate0+1 chiariscono un segnale incrementale, prevedere per categoria/regime **probabilità e magnitudine dell'upside** in 21/42 giorni e **left-tail/drawdown hazard** come heads distinte. Model evaluation rispetto a politiche 100% Original V2, matched on same gold data and same risk engine; non promuovere un cambiamento soltanto perché produce Top1 identico tra download.

**Gate 3: POLICY V2 CONGELATA** — testare **un solo challenger** morfologico con un'architettura limitata, senza toccare sotto-pesi, stop, veto, MA3 e governor. Controllo full V2 vs challenger su stesse vintage e stessi segnali/drawdown/fees. Prespecificare non-inferiorità economica (ad esempio <=5% riduzione relativa di CAGR contro la baseline full stessa vintage) e miglioramento documentabile di stability/capital dispersion/drawdown; la baseline storica 43% non è sufficiente per un gate comparativo se non replicata sui medesimi input.

**Gate 4: VALIDAZIONE FUTURA** — congelare ora predictions e parameter set per nuovi mesi dopo il cutoff luglio 2026; datestamped raw price snapshots, membership causale e storico auditabile. Nessuna promessa di 43% CAGR futuro. Nuovo periodo reale e scenari di stress sono necessari.

## Fonti esterne (supporto contestuale, non sostituto del test)

- Moskowitz, Ooi, Pedersen, *Time Series Momentum*, Journal of Financial Economics (2012), DOI 10.1016/j.jfineco.2011.11.003: persistenza di prezzo e inversione su orizzonti diversi.
- Daniel & Moskowitz, *Momentum Crashes*, JFE (2016), DOI 10.1016/j.jfineco.2015.12.002: rischi delle code e crash in shock/regimi.
- Bailey & López de Prado, *Deflated Sharpe Ratio*, JPM (2014), DOI 10.3905/jpm.2014.40.5.094: correzioni selection bias/backtest overfitting.

## Consegnabili numerici

Protocolli, codice (senza fit) `l2l_screen.py`, `l2l_regime_probe.py`, `l2l_independent_audit.py`, `SHAPE_FEATURE_PANEL.csv.gz` (16,837 righe), `SHAPE_SCREEN_SUMMARY.csv`, `SHAPE_SCREEN_BY_DATE.csv`, `SHAPE_SCREEN_SPLITS.csv`, `SHAPE_IC_BY_YEAR.csv`, `RISK_SHAPE_2X2.csv`, `PRESPECIFIED_CONTRASTS.csv`, `MANIFEST.json`, `INDEPENDENT_AUDIT.json` nel pacchetto ZIP allegato alla chat. Input Yahoo originali non duplicati: artifact GitHub sopra. Nessuna produzione promossa.
