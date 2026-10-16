# Bozza di test: pattern OHLCV e relazioni tra ETF

Richiesta16ottobre2026: pianificare flatten di pattern mensili,trimestrali,semestrali e reti Dense, per valutare se apprendere dai dati Yahoo congelati sia piu utile delle125feature costruite. Questa e una bozza, non una preregistrazione eseguibile. Nessun fit o download avviato per questa linea. Il test PCA95 gia avviato rimane distinto.

## Ipotesi e input

Tre finestre fisse alternative:21,63,126sedute, approssimazioni di1,3,6mesi. Ogni input e la sequenza OHLCV di un ETF fino al segnale, appiattita in105,315,630numeri. Non concatenare le tre finestre sovrapposte: duplicano osservazioni. Confrontarle separatamente; il target rimane rendimento/rank futuro21sedute, non tre diversi orizzonti.

Solo AM1975MA/Test,149ETFOriginal149,tre download Yahoo gia congelati,nessun nuovo prezzo e produzione intatta. Nessun indicatore tecnico,embedding ticker o informazione futura. Normalizzare OHLC rispetto a un prezzo di riferimento gia noto nella finestra (ad esempio primoClose), e volume con trasformazione log e scala storica; fissare le formule e verificarne l'invarianza ad aggiunte future prima del fit. Sono trasformazioni di scala necessarie, non input tecnici aggiuntivi. I prezzi nominali e volumi grezzi senza normalizzazione renderebbero difficilmente confrontabili ETF diversi. Le anomalie/fonti gia note non scompaiono cambiando rappresentazione.

Conservare chiavi/campioni e schema temporale del confronto controllato, con maturazione rigorosa delle etichette. Verificare prima la disponibilita continua OHLCV delle finestre; nessun riempimento dal futuro. Se il supporto differisce, riportare il confronto su chiavi comuni e ricostruire un controllo sullo stesso supporto. Non usare la PCA o le125feature come input di questa linea.

## Architettura iniziale piccola

Un solo modello condiviso tra ETF, addestrato sulle date cross-sectional: nessuna rete separata per ciascun ETF. Input Flatten(Lx5) -> Dense32 ReLU -> Dense8 ReLU -> Dense1 score. Numero parametri:3665/10385/20465 per21/63/126sedute. La rete e multistrato ma resta piccola; Dense non impedisce overfitting, aumenta i gradi di liberta.

Per ogni finestra confronto obbligatorio con score lineare regolarizzato sugli stessi input. Stesse normalizzazioni,coorti,label,ListNet,periodi e motore di portafoglio per isolare il valore della nonlinearita. Il confronto con LINEAR125feature resta anche un riferimento economico, ma da solo non isola architettura e rappresentazione.

Protezione dall'overfitting: capacita limitata,L2,criterio di arresto scelto su validazione temporale interna conpurge, nessuno shuffle tra train e validazione per data. Dropout possibile ma non obbligatorio: un coefficiente fisso da motivare nel pilot, non una garanzia statistica. Non ricercare molte architetture guardando ilCAGR2017–2026. Gli ETF nella stessa data e i tre download sono correlati: la numerosita indipendente non e il semplice conteggio ETFxgiorni.

## Fasi per contenere costi e selezione ex post

1. Audit dati e disegno prima dei fit: tensor schema,causalita/missingness,purging,target,maturazione,numero parametri e ambiente congelato. Deduplicare i precedenti test raw/MLP nel repository; i precedenti ListNet su125feature non sono equivalenti.
2. Pilot esclusivamente pre2017 per verificare training,qualita ranking contro lineare grezzo e ragionevolezza del costo. Massimo una architettura candidata fissata; i seed servono a misurare variabilita, non a scegliere il migliore. Finalizzare solo qui epoche,L2/dropout e regola di validazione/refit. Il noto holdout10% permanente di LINEAR va trattato esplicitamente: cambiarlo insieme agli input confonderebbe l'interpretazione; predisporre controlli con la medesima politica. Non assumere che apprendimento piu recente risolva automaticamente ilproblema.
3. Solo dopo congelamento:walk-forward annuale2017–2026,tre download e3finestre. Budget massimo90fit lineari e270fit neurali se3seedfissi per fold, con ensemble fissato prima dei risultati. Valutare costi pilot prima di autorizzare/eseguire questo budget completo. Possibile prima fase ridotta a una finestra primaria prefissata, ma non selezionata usando CAGR outer.
4. Replay completo con solo Compact21 sostituito, stessi altri moduli,rischio,costi,esecuzione. Opportunity escluso dal test principale. Riportare tutte le finestre e tutti gli esiti, inclusoCAGR/DDannuale2021/2023; nessun filtraggio degli anni peggiori.

Metriche:qualitaTop1/NDCG/RankIC,dispersione tra seed,Top1/Top2tra download,CAGR,MaxDD,Sharpe,turnover,concentrazione. Fissare gate prima dell'esecuzione. Nessuna promozione perCAGRmedio solo e nessuna interpretazione dei tre download come mercati indipendenti. Periodo2017–2026 gia ripetutamente esaminato: necessita futura verifica indipendente.

## Giudizio iniziale

Test sensato come ipotesi controllata sulla rappresentazione. Il modello deve comunque estrarre internamente delle caratteristiche: senza indicatori manuali non significa senza feature apprese. Non e dimostrato che flatten o reti Dense battano gli indicatori; possono semplicemente adattarsi al rumore.

## Estensione richiesta: multipattern e contesto del paniere

Ipotesi16ottobre2026: i percorsi degli altri ETF possono aggiungere informazione per il ranking del singolo ETF, comprese relazioni inverse o ritardate tra gruppi. Non assumere che le correlazioni siano costanti o causali. La matrice completa149x126x5 contiene93870valori per segnale; collegarla direttamente aDense32 richiederebbe circa3milioni di parametri nel primo strato, ingiustificati come punto di partenza rispetto alle date indipendenti disponibili.

V2 contiene gia informazioni relative/cluster: producer MA3 includeclusterret,momentum,breadth e rendimenti relativi; a4_cluster_destination contiene covarianza,cross-cluster correlation e identita persistenti. Il test proposto riguarda contesto appreso daOHLCV; non presentare il semplice uso dei cluster come novita assente dalla baseline.

Prima candidata da finalizzare: piccolo encoder temporale condiviso fraETF (Conv1D/TCN), viste21/63/126sedute come pattern su scale diverse, pooling e piccolo headDense per score cross-sectional. La condivisione dei pesi evita una rete distinta perETF. Piu viste non sono piu osservazioni indipendenti: le finestre si sovrappongono. Nessun indicatore125comeinput.

Contesto incrementale: prima aggregazione compatta degli embedding degli altri ETF, escludendo il titolo stesso per misurare il contributo esterno; poi, soltanto se utile nel pilot, una piccola attenzione cross-asset per rendere i legami dipendenti dallo stato. L'attenzione puo apprendere pesi di interazione ma non dimostra che un ETF ocluster ne causi un altro. Evitare di partire da una grande retegraph/Transformer o da molti cluster e lag liberamente selezionati.

Se si usano cluster espliciti, appartenenza e allineamento temporale devono essere costruiti soltanto dal passato OHLCV disponibile al segnale; non usare la classificazione ottenuta sull'intera storia. Non importare gli indicatori MA3 nel test dichiarato senzaindicatori. Il contesto puo essere formato da embedding aggregati delle serie grezze normalizzate; tutto compreso nell'audit causale.

Controlli del pilot, da congelare senza eseguire una griglia illimitata:
1. Lineare suinputOHLCV: riferimento economico e predittivo minimo.
2. Piccolo encoder temporale del soloETF: misura qualita della rappresentazione locale.
3. Stesso encoder con contesto aggregato del paniere: verifica contributo della situazione generale.
4. Solo se ilcontesto mostra valore nelpilotpre2017: singolo blocco relazionale compatto, per verificare informazione aggiuntiva rispetto al contesto generale.

Confrontare capacita/parametri e regolarizzazione dei controlli, altrimenti il miglioramento potrebbe dipendere dalla sola maggiore dimensione della rete. Le finestre singole e il modello multipattern non vanno aggiunti tutti automaticamente al budgetMLP precedente: scegliere una piccola progressione primaria prima di qualsiasi replay2017–2026. Non scegliere cluster,lag,soglie oseed sul2021/2023. Stessi target21giorni,lossListNet e protocollomaturazione/portafoglio per confronti interpretabili. Relazioni su ritardi diversi richiedono test incrementali fissati prima dei risultati, non correlazioni scelte guardando il futuro.

Migliore percorso significa test che distinguano input,capacita e contesto, non certezza a priori che una specifica architettura vinca. Valutare ranking futuro,CAGR/DD e stabilita suseed/download; nessuna decisione per sola accuracy oCAGRmedio. Questa estensione e esclusivamente pianificazione: nessun addestramento aggiuntivo avviato.
