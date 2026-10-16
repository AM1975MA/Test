# Bozza di test: pattern OHLCV grezzi, senza indicatori tecnici

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

Test sensato come ipotesi controllata sulla rappresentazione. Il modello deve comunque estrarre internamente delle caratteristiche: senza indicatori manuali non significa senza feature apprese. Non e dimostrato che flatten o reti Dense battano gli indicatori; possono semplicemente adattarsi al rumore. Partire dal controllo lineare e dalla piccolaMLP permette di misurarlo. Conv1D/TCN sarebbe un successivo confronto sulla struttura temporale, non un'altra variante da aggiungere subito alla griglia.
