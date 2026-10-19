# F3 × H1 × H3 — Complementarità, rotazioni, causalità e verdetto scientifico
19 ottobre 2026 · `research/149-complementarity-regime-meta-20261019` · originale **149 ETF** (NON 150 e NON soli europei)

## ESITO SCIENTIFICO IN BREVE
La complementarità tra F3 e H1 è **strutturale come rischio/allocazioni storiche**, ma non abbiamo ancora dimostrato che i mesi favorevoli a un modello siano prevedibili. La soluzione conservativa che sopravvive ai test del campione è il **portafoglio STATICO 50% F3 / 50% H1 sulle loro posizioni effettive**, con 10 bps per lato e ribilanciamenti ogni 21 sedute: CAGR 23.215%, max drawdown daily-open −24.844%, Sharpe log/giornaliero annualizzato .8869, Expected Shortfall peggior 5% giornaliero −3.302%. È un'osservazione retrospettiva su un dataset **ripetutamente sfruttato**, non una garanzia prospettica, e NON supera il rigido preregistrato "CAGR entro 1pp da H1" perché 23.215% vs 24.625%.

Successivamente, la sola ipotesi economica posthoc **USO63>QQQ63 ⇒ H1, altrimenti F3** ha dato un interessantissimo CAGR storico **29.379%**, maxDD −29.223%, Sharpe .9669. La scelta **USO/QQQ è stata fatta DOPO aver guardato le esposizioni di F3 e H1 negli anni migliori**: non è un test fuori campione. Bootstrap accoppiato 64 mesi contro 50/50 sul guadagno log medio del periodo: **+.004080 log/mese, 95% CI [−.002912,+.011254]**, contiene ZERO. La soglia di promozione precongelata NON è superata, peggiora il DD (−29.22% vs −24.84%) e l'ES giornaliero (−3.805% vs −3.302%). Quindi il 29.38% NON è rendimento prospettico attendibile.

Due GitHub Actions realmente riuscite (numeri e archivi fissi):
1. Complementarità, cause, 10 politiche con uguaglianza matematica delle curve preesistenti: https://github.com/AM1975MA/Test/actions/runs/39245013007
2. Due controlli economici posthoc pre-fissati (oil vs tech e inverse 63d basket risk): https://github.com/AM1975MA/Test/actions/runs/39246135639

Dati e codice con SHA256:
`research_reset/predict149/complementarity/{PREREGISTERED.md,run.py,results/RESULT.json,results/ASOF_64_MONTH_EXPERT_STATES_AND_CHOICES.csv,results/EXPERTS_AND_REAL_COSTED_MIXTURES_DAILY.csv,results/SHA256_MANIFEST.txt}`.
`research_reset/predict149/complementarity/mechanisms/{PREREGISTERED_AFTER_I.md,run.py,results/RESULT.json,results/EXANTE_64_MONTH_MECHANISM_WEIGHTS_AND_RETURNS.csv,results/MECHANISM_TRUE_SHARES_NEXT_OPEN_CASH_PATHS.csv,results/SHA256_MANIFEST.txt}`.
Precedenti due tentativi della seconda Action fallirono per problemi di sintassi/colonna, corretti senza cambiare il protocollo o le regole economiche; la terza Action è COMPLETATA con successo e risultati archiviati.

## PERCHÉ HANNO INFORMAZIONI COMPLEMENTARI
Esatta correlazione dei **64 log rendimenti di intervalli da 21 sedute**, dati da due portafogli reali con gli stessi nominali di costo: F3–H1 **+.5902**, F3–H3 **+.5964**, H1–H3 **+.9589**. Media ETF in comune su ogni coppia delle cinque posizioni: F3/H1 **0.516 su 5**, F3/H3 **0.672 su 5**, H1/H3 **3.75 su 5**. H3 è molto più simile a H1 del previsto; la VERA ortogonalità sta fra F3 e H1.

Composizione storica, per NOME degli ETF selezionati (categorie molto grossolane):
- **F3** classifica i movimenti futuri via distribuzione signed q10/q50/q90 e predilige molti settori tecnologici, semi, ETF country/emergenti: 2021 52% ETF settoriali; 2023 52% settoriali (SMH, SOXX, QQQ, TAN), 2025 43% settoriali +25% mercati emergenti (IWM, ARGT, SMH, XBI etc).
- **H1** cerca la leadership di fattori e spesso sceglie interi gruppi di ETF altamente correlati fra loro: nel 2021 50% delle scelte `C06_REAL_ASSETS`, numerosi `USO/BNO/DBO/USL` e `GSG` legati a materie prime petrolifere via FUTURES ROLL, con 23% obbligazionari. 2023 C06 ~48%, 2024 C06 ~43% più ~30% ETF settoriali SMH/SOXX/XLK, 2025 C06 ~42% e C02 settori ~43%. Quindi **H1 non è semplicemente una strategia oil**; nel 2024 H1 ha anche selezionato semiconduttori.
- "Cinque ETF" H1 come USO/BNO/DBO/USL/GSG possono essere **una sola grande scommessa economica** in termini di rischio. Le 9.5 posizioni medie del mix F3/H1 non corrispondono a 9.5 fattori indipendenti; la neutralizzazione della concentrazione va validata PIT con volatilità/covarianze e costo roll.

## PERFORMANCE INTERAMENTE FINANZIATA E CON STESSI COSTI
Regole pratiche: 5 ETF al 20% in F3/H1/H3; composizione union ad esempio F3/H1 50:50 imposta 10% dell'equity su ciascun ticker prima di sommare duplicati. Prezzi US ETF Adjusted Open; esatta soluzione per quote acquistate e fee pari a 0.1% per lato ogni scambio, valore monetario sempre autofinanziato. Integrale delle tre curve di ricostruzione devia dal vecchio archivio al massimo di **4.44e−16** a qualsiasi dei 1345 punti giornalieri.

| Politica | CAGR | MaxDD daily Open | Sharpe log daily ×sqrt252 | ES giornaliero peggior5% |
|--|--:|--:|--:|--:|
| F3 |20.020%|−29.737%|.693|−3.702%|
| H1 |24.625%|−33.774%|.793|−4.112%|
| H3 |23.526%|−28.783%|.759|−4.137%|
| **50:50 F3/H1** |23.215%|**−24.844%**|**.887**|**−3.302%**|
| 50:50 F3/H3 |22.692%|−25.387%|.863|−3.313%|
| Equal F3,H1,H3 |23.570%|−26.026%|.876|−3.483%|
| Causal switch F3/H1 previous 3 matured blocks |22.474%|−35.762%|.775|−3.893%|
| Causal switch F3/H1 previous 6 matured blocks |17.601%|−41.870%|.616|−4.042%|
| Online ridge meta 8 asof inputs, shrinkage |22.491%|−25.758%|.825|−3.505%|
| **Causal USO63>QQQ63** |**29.379%**|−29.223%|**.967**|−3.805%|
| Inverse-asof-63d expert basket vol |22.989%|−26.719%|.903|−3.209%|

Il criterio `2021–26` non è PIL (performance investibile reale). Le esperienze US ETF sopravvissuti, leveraged/futures, 10bps cost hypothetical, no EUR FX/venue/tax, retroactive adjusted OHLC e dataset esaminato decine di volte restano limiti NON CORRETTI.

## COME CAPIRE SE UN MODELLO VINCERÀ: FALSE PISTE
Test sul periodo successivo con decisione nota SOLO alla Close del segnale.
- `SWITCH_PAST3` e `SWITCH_PAST6` conoscono soltanto i tre/sei mesi dei risultati che hanno completamente maturato **prima** del segnale. L'intero ultimo intervallo `k−1` termina all'OPEN corrente ed è vietato anche a un meta-learner. Questi meccanismi peggiorano il rischio rispetto al 50/50.
- Meta-learner online Ridge(alpha=25) usa SOLO mesi maturi, 8 macro-feature asof (SPY 21/63 momentum, SPY 21/63 vol, HYG−AGG credito, breadth originale149, cross-sectional dispersion, overlap dei 5). CAGR 22.49%, maxDD −25.76%, non migliora il 50/50. Gli intervalli bootstrap dei guadagni log mensili dei tre switch vs statico comprendono zero, ogni GO scientifico = FAIL.
- Descrizione condizionale posthoc *as-of* degli stati: nessuno fra SPY positivo a 63 giorni, vol21 > vol63, credito HYG/AGG positivo o market breadth >50% separa affidabilmente vittorie F3/H1: tutti gli intervalli bootstrap esplorativi dell'excess del gruppo contengono zero.
- **Oracle clairvoyant** che sa il vincitore della prossima mensilità ex post: CAGR **67.63%, maxDD −22.37%**: solo un limite diagnostico con conoscenza **proibita**, dimostra che perfetto timing sarebbe prezioso, NON che sia anticipabile.

## NUOVA IPOTESI ECONOMICA USO vs QQQ: COSA FUNZIONA E COSA NON FUNZIONA
Precongelata per esperimento Ib dopo esposizioni 2021/2025:
`USO ultimi63 Close log return > QQQ ultimi63 Close log return ? H1 : F3`.
- Scelte H1 in 29/64 mesi, F3 in 35/64; il modello scelto ha superato l'altro soltanto **38 su 64 mesi** (59.4%). Ecco perché l'idea è promettente ma fragile.
- Migliora fortemente 2021 e 2025, ma sbaglia in modo rilevante il **2024**: H1 +48.05% vs F3 +7.76%, mentre la regola sceglie F3 in 10 dei 12 segnali mensili. Risultato del filtro in 2024 **+8.57%** vs 50/50 +26.88%. Questo confuta che oil/growth come singolo proxy predica SEMPRE leadership H1.
- Altra fase critica 2022: filtro H1 in 8/11 mesi nonostante F3 abbia vinto annualmente; reddito del filtro circa +1.41% vs 50/50 +1.34% (non un miglioramento).
- In 2023 e 2025 il filtro, invece, supera fortemente 50/50: 2023 +63.79% vs +44.96%; 2025 +69.54% vs +37.67%. Nel 2026 solo gennaio–giugno F3/H1 filtro +6.32% vs statico +9.10%, altro errore.
- Distribuzione incremento log rispetto al 50/50 **fortemente concentrata**: totale cumulato differenziale +.261125, le 3 migliori date 2021-04-05, 2022-04-01, 2021-02-02 da sole sommano +.197244, **75.5% del vantaggio cumulato**; le cinque migliori >100%, compensate da molte perdite. Sono segnali classici di alta fragilità. Precisazione: confronto dinamico è su quote sempre monetizzate e costi applicati (non semplice media delle curve).
- Il test di validità condizionale precongelato fallisce: vantaggio log mensile vs 50/50 +.004080 ma 3-ancora bootstrap 95% [−.002912,+.011254], comprende ZERO; peggiora maxDD ed ES giornaliero vs 50/50.
- Ulteriore peso risk parity as-of (F3 σ vs H1 σ 63 giorni): 22.99% CAGR, −26.72% DD, .903 Sharpe, ES −3.209%; ha ES marginalmente migliore, ma rende meno e fa peggio in DD del mix 50/50; il suo vantaggio log vs statico [−.00149,+.00113] include zero.

## DOVE È LA VERA INFORMAZIONE CHE MANCA?
1. La complementarità non è soltanto "F3 buono se Nasdaq, H1 buono se petrolio": H1 stesso muta da futures oil a semiconduttori e obbligazioni; manca una semantica economica più precisa delle esposizioni e del loro momento. Una regola in un solo differenziale ETF è insufficiente.
2. Per decidere il peso ex-ante servirebbe un **modello causale di utilità relativa di due PORTAFOGLI**, stimando `P(R_F3>R_H1 | X_t)` e `E[R_F3-R_H1 | X_t]` con evento rischio/costi, non forecast simultaneamente 149 winners; la vera unità è il DIFFERENZIALE DI RENDIMENTO dei due panieri.
3. Come feature candidate per un reale test futuro (non retroottimizzare 2021–26): fattori di mercato PIT e regime cross-asset con petrolio **futures carry/roll**, liquidità del credito, real rate e semiconduttori; esposizioni dei due portafogli all'apertura e loro expected ES/CVaR; dispersione dei forecast quantili F3, incertezza dei fattori H1 e loro disaccordo. Non dichiarare "causa" dai semplici proxy correlati.
4. Validazione rigorosa: congelare F3/H1 e 50/50 come baseline semplice; scegliere UNA regola ex ante o un meta-distributional model distinto e testarlo su date realmente future o una PIT nuova coorte, con costo EUR/spread reali. Occorrono centinaia di ANCORE temporali o indipendenti periodi, non 64 mesi già riutilizzati; più modelli/iperparametri sullo stesso 2021–26 peggiorano il selection bias.

## VERDETTO E DECISIONI OPERATIVE
- **Migliore opzione prudente per paper trading comparativo**: 50/50 delle scelte F3/H1, prossima Open, nessun timing, controllo reale e costo broker prima di decidere. Storicamente Sharpe .887 / daily MaxDD -24.84 / ES -3.30, nettamente meglio di ogni singolo esperto negli indici di rischio. L'ipotesi H3 è utile come baseline, ma troppo simile a H1 per contribuire alla diversificazione F3/H1.
- **Miglior sfidante sperimentale di rotazione**: oil>Nasdaq 63d ⇒ H1, altrimenti F3; CAGR storico 29.38% ma **NON convalidato** e associato a trade timing/parametro ex post scelto DOPO analisi delle esposizioni. Non merita capitale reale.
- Il vero salto di qualità sarebbe un meta-modello con feature **nuove e timestamped**, validazione futura, calibrata direzione/rischio. Non manipolare pesi, lookback o futures ticker solo per arrivare al 30% sul campione noto.

Entrambe le Actions finali hanno restituito SUCCESS con archiviazione SHA256. `etf_trader` e produzione invariati.
