# OLC31 — Magnitudine economica, calibrazione e persistenza: protocollo maestro

**Data:** 2 novembre 2026. **Stato:** protocollo e piano di collaudo, concepiti prima di esaminare qualunque nuovo risultato economico OLC31. **Studio:** retrospettivo esplorativo EU165/USA149 su storia ripetutamente ispezionata; non costituisce holdout indipendente. Nessuna modifica a `main`, nessun ordine, nessuna modifica della strategia di produzione. Baseline economica immutabile OLC20 `AUTH`, rischio `ALARM`/`FAST_LOCK3`, motore OLC19, costo legacy 0,001/0,003; `FAST_LOCK3,0.001` è il contratto economico primario. Baseline informativa: punteggi e forecast originali congelati, non versioni ricostruite per convenienza.

## A. Decisione di ricerca: cosa possiamo dimostrare e cosa no

**Domanda primaria:** dopo aver controllato per il rango e per la forza relativa del modello attuale, i **valori grezzi e le loro distanze** contengono informazione predittiva **addizionale sulla magnitudine del rendimento effettivamente conseguibile** nel successivo intervallo di investimento (Open d'ingresso → Open successivo)?

Non confondere: (1) classificazione/ranking; (2) differenza di punteggio; (3) rendimento medio atteso; (4) distribuzione/errore di previsione; (5) vantaggio netto fra due candidati; (6) valore di trattenere un leader; (7) esposizione/costo/rischio del portafoglio. Un rango elevato NON significa che un +0,01 di score equivalga a +1% di rendimento. Le differenze fra raw-score di learner differenti non sono direttamente sommabili. La trasformazione in percentili conserva ordine intra-mese, ma perde le distanze originali. La normalizzazione delle feature non è di per sé il difetto: il problema da verificare è il **target** e la **calibrazione delle uscite**.

**Ipotesi primarie, con possibilità reale di falsificazione**:
- H1: lo spread dei raw-score, entro universo/data e condizionatamente al ranking AUTH, spiega la differenza di ritorno Open→Open oltre la sola graduatoria. H0: non c'è miglioramento fuori-training.
- H2: una mappatura causale previsioni→rendimenti preserva l'informazione sulla magnitudine, supera gli estimatori senza raw-score e resta calibrata in EU e USA.
- H3: il vantaggio della magnitudine è **locale ai primi due/cinque ETF** e permette di evitare sostituzioni sfavorevoli; alternativa H3b: il vantaggio riguarda leader lontani nella classifica, per cui il Top5 è strutturalmente insufficiente.
- H4: la forza condizionale predetta distingue continuazione ed esaurimento senza usare l'identità QDVE, ARGT o SMH. Non definire vincitore in base al miglior ticker retrospettivo.
- H5: soltanto se H1–H4 superano la validazione potrà aver senso ricalcolare i portafogli con V6, stop, costi e rischio.

**Controllo storico essenziale:** in OLC23 il target 21 sedute non corrispondeva all'esatto intervallo d'investimento, provocando veto perdenti. In OLC25–30 una migliore descrizione/ranking medio del trend non si è convertita in utilità economica Top2. Pertanto la variabile dipendente primaria è *esattamente la differenza Open→Open tra due date di esecuzione archiviate*, non il rango futuro o un rendimento forward di durata fissa. Gli orizzonti 42/63/126 restano **diagnostiche separate** (persistenza), mai surrogati non dichiarati dell'intervallo tradato.

## B. Contratti dati e sorgenti fissate

**Scoring (identità primaria del riferimento):** `OLC20_Regime_Validation_Final_20261102.zip`, SHA256 `a81be0fad1da73b48ba0af0080985657ee33e18a10f278db2318f9da06738a9c`, `results/trials/AUTH/{EU,USA}_SCORES.csv.gz`; OLC20 parent branch commit `6c387fac4c2e544bb9dc90f6622cd94faba6d7c2`.

**Prezzi, time mapping e accounting:** `OLC19_Rischio_Rientro_Checkpoint_20261102.zip`, SHA256 `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540`. Nel checkpoint: `olc16_contextual_rank_20261102/inputs/{EU,USA}_STATE_HALF.npz`, `.../{EU,USA}_CALENDAR.csv`, `.../{EU,USA}_FITTING_FRAME.csv.gz` e `.../{EU,USA}_MEAN3_SCORES.csv.gz`. Controlli parent 32 conti OLC19/20; preservare dtype, NaN, calendario, V6 e accounting.

**Punteggi prima della quantilizzazione:** `OLC08_03_RSI_Confronto_Verificato_20261101.zip`, SHA256 `0dbcb8ee93cd0acaefd7505a202fbf30c9fda8df1804d90a0dd1578abd704f4b`, `{EU,USA}_R_RSI_DOMAIN_FORECASTS.csv.gz` con `RETURN_RAW`, `ET_RAW`, `XGB_RAW`, già trasformati poi in `RETURN`, `ET`, `XGB`; `OLC11_Selezione_Risultati_20261101.zip`, SHA256 `fc536d786f42f724df8102544c33e3da0e347d216d16b871f805525d9f467b6c`, forecast annuali `ET_REG`, `XGB_REG`, altri specialisti, 3 seed. `OLC12_Integrazione_Risultati_20261101.zip`, SHA256 `f899576dcb3230ceab98cb59a939f4ceb7e9bd9215a7f2c140f0a1df8131b3dd`, contiene punteggi integrati.

**Regola di lineage obbligatoria:** `RETURN_RAW` OLC08 non è lo stesso oggetto di `ET_REG/XGB_REG` OLC11; OLC20 usa previsioni multi-orizzonte C21/C42/C63 dell'OLC14 riordinate/rivalutate nel contesto, non la semplice somma diretta dei raw OLC08. Nessuna affermazione su uno score viene estesa a un altro senza prova di corrispondenza date/ticker/modello/seed/cutoff. Salvare i lineage ID dei singoli layer e le identità dei test di parity.

**Grano delle osservazioni:** `(market,signal_date,ticker)` per forecast/prezzi di ingresso, `(market,signal_date,entry_date,next_entry_date,ticker)` per etichette economiche, `(market,signal_date,ticker_i,ticker_j)` per coppie/spread. Un solo evento mercato-mese pesa una volta; ~165 ticker del mese e molte coppie condividono lo stesso shock e NON sono osservazioni indipendenti.

**Qualità dei prezzi:** EU: le due aperture e gli indicatori di disponibilità `observed=True` sono obbligatori per le etichette; USA: maschera `observed` storica originale NON presente, usare solo valori preparati finiti e positivi e marcare il caveat. Vietato usare prezzi imputati, zeri-sentinella, forward fill o un prezzo futuro per determinare eleggibilità/score al segnale. Prezzi senza certificazione total-return, FX, corporate actions, delistings, spread bid/ask e first-executable fill: nessuna conclusione di redditività reale senza audit supplementare.

## C. Dizionario quantitativo e metriche (con formule)

Per una data di segnale `s`, con primo Open eseguibile `e0` e Open successivo `e1`, su ETF `i` e mercato `m`:

- `r_i(s) = ln(O_i[e1] / O_i[e0])`. Si usa solo se entrambe le aperture sono osservate nel contratto dichiarato. Un target di regressione è noto **solo a `e1`**.
- `market_component_m(s) = median_i r_i(s)` fra ticker con prezzo valido; è un target di training, **non disponibile** al segnale. `relative_bp_i = 10000*(r_i-market_component_m)`: conserva la grandezza, a differenza del percentile futuro.
- `economic_pair_bp(i,j,s) = 10000*(r_i-r_j)`; `net_advantage` sottrae **solo** la frizione economica del cambiamento coerente con il nozionale e la fee legacy 0,001/0,003. Non trattare automaticamente `0,001` come 10 bp/lato.
- `persistence`: realizzazione di differenziali 42/63/126 giorni come outcomes ausiliari con date di maturazione precise; report per durata, non sommare outcome sovrapposti.
- Raw spread `d_raw`: differenza fra raw-score del medesimo learner sullo stesso asof. Calcolare due forme: raw non trasformato dopo calibrazione annuale (livello/evoluzione) e centered/spread per query con scaler robusto **fit solo sul training**. Mai comparare direttamente ET_RAW contro XGB_RAW come se avessero unità fisiche equivalenti.
- Incertezza: scarto predittivo calibrato per fold/mercato, quantili di errore, tasso di copertura intervalli; un `p` di classificatore misura l'evento per cui è stato addestrato, non automaticamente `P(r_i>0)`.

**Cosa misurare prima dei conti:** calibratura (errore, bias e andamento affidabilità per decili, condizioni trend/vol), MAE e RMSE sulle magnitudini O2O, correlazione condizionale all'ordinamento, hit-rate della direzione dei differenziali quando il vantaggio predetto è grande, quantile pinball/coverage ove disponibile, regret economico Top2, margine vincitore corretto, criticità su perdenti estremi. Qualità valutata **per mese**, poi aggregata con identico peso di mercato, non su righe iid per ticker.

**Benchmark di significato economico:** massimo ticker realizzato della finestra intera (QDVE, ARGT, SMH) solo nel report diagnostico di cattura/temporizzazione; selezionarlo guardando il passato NON lo rende una baseline implementabile. Alternative ex-ante: hold-to-next-entry AUTH, top5 FUSION congelato, rendimento mediano paniere, best tradabile ex ante secondo forecast del candidato. Gli errori vs best ex post sono regret-oracle, non prova di alpha.

## D. Disegno sperimentale a cancelli, prima di ogni fitting

**G0 — Provenienza/parità, prerequisito BLOCCANTE:** verificare digest degli archivi, ogni chiave mensile e ticker, duplicate/near-duplicate, date/seduta/valuta, label terminale disponibile, ranghi alle parità e NaN. Confrontare `RETURN` OLC20 vs forecast RSI e il layer C21/C42/C63 originale. Allineare `e0/e1` da calendario e verificare con i `DECISIONS` e coi conti parent. Riprodurre 8 parent OLC20 e 32 OLC19 con array identici (o dichiarare errore e bloccare). Verificare `observed` EU e il limite USA. Scrivere test di perturbazione dei soli prezzi futuri, dei peer e della maschera. **Nessuna stima di alpha finché G0 è verde.**

**G1 — Diagnostica d'informazione (ZERO fit nuovi):** costruire una tabella unificata e due report EU/USA: (i) conditional-magnitude by AUTH rank-bin e per spread raw, (ii) scatter decili predicted raw gap vs realized Open→Open spread nei Top2/Top5/Top20 e su tutto il paniere. Stratificare per mercato, anno, volatilità, ampiezza del mercato, positivo/negativo, tipi di ETF quando supportati da metadati di periodo. Confrontare quartili di raw spread **a parità di rank bucket**; testare un raw-score non informativo ottenuto da permutazione entro data/rank-bucket (distribuzione preservata). Controllo monotonic transform: applicare una trasformazione strettamente crescente ai raw produce stessi percentili e stesso AUTH; se cambia, c'è un bug.

**G2 — Calibrazione prequential (solo se G1 non è vacuo):** tutti i candidati condividono le **stesse righe** del target di training, segnali e prezzi; una stima a blocchi mensili, non per ticker mescolati. Tre baseline/candidate fissi:
  - `B0`: riferimento AUTH puro per decisioni; previsione economica ingenua `mean/median` storica train-only e ranghi AUTH.
  - `B1`: mappatura causale semplice del FUSION percentile a rendimento/rendimento relativo, senza score grezzi (Ridge alpha=10, oppure calibrazione isotona solo se dimostrata necessaria in train CV: NON scegliere ex-post).
  - `B2`: stessa architettura di B1 con raw RETURN/ET/XGB **dopo matching di lineage** e spread C21/C42/C63; prevedere *due teste*, `r_abs` e `r_rel`, per poter ricostruire vantaggio ed esposizione sistemica. Base Ridge alpha=10 standardizzato solo su train; stress Huber con epsilon predefinito in un lotto successivo, senza tuning opportunistico.
  - `B3`: modello pairwise differenziale solo se B2 migliora in G2: regressione ridge identica su differenze feature tra due ETF candidati Top5, target `economic_pair_bp`; ricontrollare simmetria `(i,j)=-(j,i)` e transitività. Niente classifica indipendente per mercato.

**Rispetto agli esempi negativi OLC23:** la label per coppie e B3 usa l'esatto mese Open→Open, e il training termina prima del cutoff. Includere separatamente `r_abs` vs `r_rel` per misurare se un all-rising/all-falling market venga distinto dal solo ordinamento.

**G3 — Decisioni controfattuali soltanto se qualità economica calibrata:** usare lo stesso AUTH Top2 e una shortlist Top5/Top20 definita prima; censire separatamente quanto un leader storico distava dalla shortlist (QDVE 2020/21). Non promettere di recuperare ETF in posizione 52 usando una shortlist di 5. Calcolare al segnale il vantaggio **conservativo** del candidato rispetto all'incumbent dopo fee e incertezza; non obbligare alcun cambio per score positivo. Si registra per ogni decisione: previsto, banda di errore OOF, riscontro futuro dopo maturazione, scarto, frizione evitata, scelta controfattuale, motivo/no-trade. Non ottimizzare pesi/threshold con CAGR retrospettivo. Opzioni di ridimensionamento del capitale in un lotto separato, non parte della prima validazione.

**G4 — Replay end-to-end solo per challenger promosso dai gate predittivi:** V6 specifico del candidato senza sovrapposizioni, medesimi ALARM e FAST_LOCK3, fee .001/.003, stop/tempi/nominale 50/50, nessun nuovo rischio/parametro. OLC20 AUTH e tutti i candidati su ENTRAMBI EU/USA, 2021–2024 e FULL febbraio2019–1luglio2026, 2020 isolato, anni 2025 e 2026 parziale, cost-stress e exposure. Ritardi di informazione ed eseguibilità prezzo intraday sono separati. Nessuna promozione se curve identiche per astensione.

## E. Chronological validation, ricorsione e controlli avversari

**Train/validation:** expanding, per anno, `train_label_exit < cutoff` (strettamente). Scaler, imputazione, mappa raw, selezione features, incertezza e calibrazione fit solo su sotto-training. Validation su anni storici completi già maturi; se un fold interno ha etichette 63/126 overlapping, purge delle finestre di label di quel fold: l'ultimo training outcome deve terminare prima dell'inizio della validazione. Non usare split random e non mescolare mesi a caso. L'eventuale gap temporale è basato sulla data effettiva `label_exit`, non su un numero fisso di righe. Lo schema è prequential; purging/embargo per CV non può creare un holdout nuovo dopo la ricerca pregressa.

**Anni:** 2019/2020 sono warm-up/crash diagnostic; principale 2021–2024 (storia già esaminata); 2025/2026 parziale sono sensibilità anch'esse già viste. Per ciascun test confrontare medesime date valide in EU/USA e riportare differenze di supporto; l'assenza di un titolo non equivale a zero. Non scegliere finestre o mercati a posteriori.

**Negative controls preregistrati e ablation:** (i) features raw solo, (ii) rank solo, (iii) raw extra, (iv) raw permutati fra ticker con uguale rank-bucket nella stessa data, (v) label future permutate nel solo training entro mercato/data, (vi) feature da una sola data ritardate di un mese, (vii) trasformazione monotona dei raw per verificare invariabilità del rank, (viii) bootstrap a blocchi sincronizzato fra EU/USA, e prove di inversione di segno pairwise. Ogni null fissato in anticipo, non scegliere il più favorevole; lo shuffle può preservare per caso parte delle informazioni. Non è un p-value esatto di mercato.

**Valutazione della stabilità:** walk-forward su tutti gli anni; blocchi mensili appaiati 3,6,12 (4000 draw, seed fisso nel protocollo operativo); riportare intervalli individuali e simultanei, sensitività leave-one-year, leave-three-best-months **diagnostica soltanto**, turnover e distribution tails, problemi 2020, calendario regime, dati mancanti/delistati. I test multipli richiedono family-wise/SPA/Hansen o almeno correzione documentata; 6 anni non consentono inferenze di precisione elevata. Frequenze bootstrap non sono posteriori. Contenere il numero dei challenger (B1, B2, B3 condizionale) per evitare ricerca infinita.

**Recursive hypothesis review** (ogni ciclo obbligatorio):
1. Formulare ipotesi, meccanismo previsto, dato osservabile che la falsifica; salvare nella branch `HYPOTHESIS_REGISTER.csv` PRIMA di testare.
2. Unit test failing-first e baseline/parity test; solo poi implementare trasformazioni.
3. Eseguire G1: se raw gap è solo monotonia del rango o null simile, chiudere H1 e NON allenare B2.
4. Eseguire G2: se migliora ranking medio ma non magnitude/calibration delle code, chiudere H2 per uso economico e indagare eventi estremi fuori portafoglio senza promozione.
5. Eseguire G3: se `Top2` è identico, niente alpha; se più leader ma O2O peggiore, orizzonte di target da riesaminare nel NUOVO protocollo, non modificare quello corrente.
6. Eseguire G4: se crescita EU migliora e USA peggiora, conservare challenger non comune e non introdurre tuning geografico opportunistico. Se MaxDD o crisi peggiorano, separare rischio da previsione e non cambiare stop nello stesso esperimento.
7. Red-team obbligatorio: revisore su dati/leakage, revisore sulla calibrazione, revisore economico/contabile; annotare obiezioni non risolte. **Nessun agente automatizzato indipendente viene dichiarato usato senza tool disponibile**; applicare comunque il workflow failing-test / green / refactor / review di Superpowers già documentato nei piani OLC08.
8. Congelare risultati positivi/negativi, hash, ricostruzione da archivio pulito e nuova ipotesi dichiarata come post-osservazione su branch successivo. Mai ritoccare soglie, seed, features o target dopo aver letto i risultati e continuare a chiamarlo lo stesso test.


### Decision metrics frozen for the first causal calibration pass

The **primary G2 predictive statistic** is the market-balanced, month-equalized mean squared error of the predicted **relative log return in basis points** (`r_i - median_group`) on identical OOF observations, with improvement defined as `loss(B1) - loss(B2)`; publish the EU and USA difference individually. Since square loss can be dominated by a few shocks, report the equivalent paired absolute-error difference as a co-primary diagnostic, not a replacement selected after seeing outcomes. Report slopes/intercepts of calibration by decile and on the top5/top20 subcohorts; baseline and candidate use precisely the same eligible dates and tickers. The primary G3 decision criterion, if reached, is paired next Open-to-Open **net advantage** of modified choices versus AUTH, aggregated by market-month with no row multiplicity. G4 separates economic CAGR/risk from the question of predictive magnitude.

Predeclare a fixed resampling seed `20261102`, 4000 paired resamples, month blocks of 6 for the principal uncertainty table (3 and 12 only sensitivity). Do not declare 4000 draws to be 4000 independent observations. If a test produces just 2021–24 retrospective favorable evidence, classify it `research candidate`, not success on a new holdout. No extra calibration method, hyperparameter, rank threshold, or portfolio weight may be selected on these displayed outcomes; modifications must start a newly frozen protocol with the number of explored prior trials disclosed.

## F. Gates e criteri di arresto (decisione prima di ricerca)

- **STOP G0:** non si riproducono i raw, i forecast, i calendari, le etichette maturate o gli 8 parent accounts; oppure non è possibile attribuire dati punto-nel-tempo. Riparare il contratto, non ottimizzare il modello.
- **STOP G1:** raw-score non mostra informazione sulla differenza economica O2O condizionatamente a rank e a feature banali; test null non peggiora; in tal caso una regressione addizionale sul raw ha bassa priorità.
- **STOP G2:** nessun beneficio robusto e ripetibile su errore di magnitudine e calibrazione/Top2 excess in ENTRAMBI i mercati; anche con qualche anno positivo vietata la promozione.
- **STOP G3:** candidato scambia soltanto ETF indistinguibili o score shift non cambia Top2; nessun “alpha da astensione”.
- **STOP G4:** costo stress .003 annulla vantaggio, peggioramenti materiali di MaxDD/2020 oppure esito dovuto a pochi mesi. Rischio come veto da motivare, non un unico limite numerico arbitrario; mantenere ogni risultato avverso.
- **SUCCESSO PROVVISORIO:** informazione incrementale misurabile condizionata al rango; previsione calibrata di spread economico che produce un differenziale positivo abbinato in EU e USA; aumento di cattura dei leader senza aumento sproporzionato di falsi positivi; replay costato e con protezioni non dominato; robustezza sufficientemente convincente da giustificare **solo** un challenger congelato e logging prospettico. Zero incluso in IC non è automaticamente un veto, ma limita la forza delle conclusioni.

## G. Piano di collaudo software / probabilistico / economico

**Unità e proprietà:** log-return simmetria, trattamento Open zero/NaN, exact `observed` EU; calendar next-entry per EU/USA; test della stessa data di taglio; group maturity; rank affine-invariance; raw-score gap unit; percentile cross-sectional con ties; pair antisymmetry; stesso ticker escluso; top-k e no duplicate; bootstrap month-block resampling univoco, seed deterministico.

**Integrazione:** identità OLC20 FUSION e relative maschere, OLC12/OLC11 lineage per le singole teste, exact scalar+model reload, array shape/contracts, data type e unità; dataset paralleli ricostruiti con implementazioni matematicamente indipendenti; digest input & source registrati.

**Property/adversarial tests:** aggiungere rendimenti futuri enormi per una serie dopo cutoff non altera nessuna decisione precedente; permutare tickers e riordinare righe non cambia risultato; cambiare un raw-score con trasformazione strettamente monotona mantiene percentile; perturbare prezzo *di oggi* altera solo forecast futuri/non già passati; rimuovere observed/quote in EU produce NaN non 0; falsificare data exit produce blocco (fail closed). Include input negativo e dummy asset/unit tests.

**End-to-end/accounting:** resettare ambiente pulito e rigenerare predizioni senza fit futuro; portfolio v6 per coppia; reconciliazione giornaliera NAV da logrendimenti/ledger, verifica costi e stop diretta; conti baseline bitwise; 0 mismatch non è prova di accuratezza raw-price, solo parity della replica.

**Output obbligatorio:** `00_SOURCE_MANIFEST.json`, `01_KEY_COVERAGE.csv`, `02_SCORE_LINEAGE.csv`, `03_RAW_VS_RANK_GAP.csv`, `04_PREDICTIVE_CALIBRATION.csv`, `05_PAIR_EVENTS.csv`, `06_LEADER_OPPORTUNITY.csv`, `07_ANNUAL_AND_COSTED_SCORECARDS.csv`, `08_BLOCK_UNCERTAINTY.csv`, `09_FAILURE_CASES.csv`, `10_VERIFICATION.json`, `REPORT_IT.md`, `HYPOTHESIS_REGISTER.csv`, `CHECKPOINT_XX.md`, sorgenti e test. Dati di training, fit, freeze, seed, versioni e cutoff persistiti con hash. Mai dichiarare completato un lotto solo perché il runner è partito.

## H. Criticità già note e limiti non aggirabili con algoritmi

Paniere EU stato 167 ticker nel file NPZ vs per-signal universe EU165 variabile, quote non sempre disponibili. Stato USA149 senza `observed`. Il primo Open mensile può non essere eseguibile al prezzo ipotizzato con informazione completa sul gap; prezzi normalizzati da vendor, corporate-action/total-return/FX/delistings incompleti; dipendenza temporale cross-ETF e sovrapposizione di target; tutti gli anni 2019–2026 già esplorati. Non trasformare l'analisi del miglior ticker ex-post in una raccomandazione anticipabile.

## I. Ordine delle attività e ripresa

**0. Prima la revisione metodologica e il presente piano.** Audit del codice, grafo di lineage e manifeste sorgenti; checklist di fallimenti, confronto con i risultati storici; preregistrazione remota su branch isolato.

**1. Solo dopo:** generare e testare G0, poi G1 (senza nuovo fitting). Se G1 positivo, G2 con pochi modelli preregistrati e riaddestramento annuale causale. Se G2 supera i criteri, G3 e G4; altrimenti arrestare e consegnare l'esito negativo. Ogni gate ha report + prove che lo sbloccano; nessuna attività asincrona promessa.

**Superpowers:** il checkpoint OLC08 contiene `docs/superpowers/plans/2026-11-01-feature-pack.md` con workflow di verifiche, test failing-first, replay, review e persist; questo protocollo adotta tali pratiche. Il plugin Superpowers non risulta installato come tool invocabile in questa conversazione: non rivendichiamo l'attivazione di agenti inesistenti.
