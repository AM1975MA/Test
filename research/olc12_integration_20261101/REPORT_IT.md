# OLC-12 — integrare lo specialista senza confondere probabilità, scelta e capitale

**1 novembre 2026. Lotto concluso; integrazione nel ramo di ricerca, nessuna promozione operativa e nessuna modifica a main.**

## Risultato

Sono implementate e testate 13 configurazioni fisse di collegamento del classificatore, più due fusioni apprese con controlli abbinati. Totale 212 percorsi completi: 12 controlli esatti OLC06, 156 portafogli delle 13 configurazioni, 20 sensibilità con informazioni sistemiche ritardate e 24 portafogli META2/META3. Nessun nuovo fit dei predittori ETF originari; 24 piccoli fit annuali della fusione.

La sostituzione diretta del regressore non funziona come miglioramento comune. Un canale separato del classificatore al 20%, con memoria, è una candidata interessante sulla finestra completa ma non domina il riferimento nel periodo principale. Una fusione appresa sull'evento migliora leggermente il Brier e la precisione Top2 nei due universi rispetto alla stessa fusione senza classificatore; non migliora però contemporaneamente il risultato economico. Il layer rimane integrato come output distinto e candidato, non convertito automaticamente in pesi o promozione live.

## 1. Identità e contratto

Parent OLC11 congelato a `9180a6d7b0ffefbdac351d0a30d5eb688ecae476`. Protocollo OLC12 registrato a `e8d8dcd90cbcd3a02b405dfdb52aea5c6dc33c66` prima degli esiti. Dopo i primi 188 replay è stata dichiarata separatamente l'estensione META2/META3, a `d517a49d841d517381975dd1ddcb326cb99ed2ce`, prima dei suoi fit: è una ricerca post-osservazione, non conferma indipendente.

Sono riutilizzate le previsioni annuali autentiche OLC11. Il riferimento primario **MATCHED_REG** usa gli esperti regressivi addestrati sui gruppi interamente maturi, mediando i tre seed prestabiliti 101/211/307 prima dei percentili. Classificatori e regressori hanno lo stesso campione. Return125 con RSI corretto resta congelato. La correzione di maturazione OLC11 riguarda Hybrid: non è una nuova certificazione della pipeline storica del Return.

La curva storica con RSI e seed101 è conservata separatamente come ARCHIVE_S101. Nel2021–2024 IMMEDIATE vale17,31%EU/35,52%USA; MATCHED_REG vale20,03%/39,92%. La differenza non è merito del nuovo classificatore: riflette il distinto riferimento abbinato, con media dei seed e gruppi di training maturi. Il vecchio39,33% appartiene a un altro contratto/finestra e non viene cancellato.

Tutti i conti usano HALF50/50, gli stessi dati, prezzi, calendario, g e target V6. IMMEDIATE/DELAY3/PHASE5 sono distinti. Costi .001/.003 nella convenzione legacy di mezzo-turnover, NON automaticamente10/30bp per lato. Rendimenti attribuiti al successivo Open effettivo; ultima riga piatta esclusa. Le uscite mancanti delle label non eliminano candidati dalla decisione live.

## 2. Come il segnale entra nella catena

La probabilità XGB_CLASS è di appartenere al quintile migliore del target relativo `Y=.45rank21^1.5+.35rank42^1.5+.20rank63^1.5`. NON è probabilità di guadagnare, né rendimento atteso. È salvata separatamente dai percentili e dal capitale.

Le prove distinguono: miscela ET/classificatore; assenza/presenza della memoria(.4,.3,.3); memoria delle probabilità prima del percentile; classificatore autonomo; canale specialistico al20% aggiunto all'80% del segnale abbinato; riordinamento con classificatore delle sole cinque proposte migliori. I cinque candidati includono tutte le parità alla soglia. Nessuna scelta usa esiti futuri o un numero di candidati ottimizzato dopo i risultati.

La trasformazione monotona corrente non cambia l'ordine del classificatore isolato. La memoria e le fusioni possono invece cambiarlo. Sono riprodotti esattamente, NaN compresi, quattro controlli OLC11 MATCHED_REG/NAIVE_CLASS nei due universi.

## 3. Diagnosi per layer prima del rendimento del conto

Segnali2021–2024 con target completo maturo prima del2025:44mesiEU/45USA; payoff21 su46mesi per mercato. Queste metriche non includono costi o protezioni.

|Output|NDCG@2 EU|NDCG@2 USA|Top2 excess a21 EU|Top2 excess a21 USA|
|---|---:|---:|---:|---:|
|Fusione regressiva abbinata|0,5411|0,5283|+1,631pp|+3,099pp|
|Sostituzione diretta XGB_CLASS, memoria originale|0,5391|0,4666|+1,316pp|+1,098pp|
|Stessa sostituzione, senza memoria|0,4807|0,5416|+0,533pp|+2,888pp|
|Return + solo classificatore corrente|0,4666|0,5085|+0,208pp|+1,670pp|
|Return + solo classificatore con memoria|0,5058|0,4145|+0,886pp|+0,018pp|
|Canale separato20% con memoria|0,5429|0,5258|+1,858pp|+2,808pp|

Il confronto memoria/no memoria è opposto nei mercati: l'informazione corrente del classificatore aiuta di più gliUSA, la memoria aiutaEuropa. Non viene selezionata una regola differente per paese. I payoff sono punti percentuali per orizzonte, non CAGR; orizzonti sovrapposti. Togliere ET e la memoria non dimostra un miglioramento generale.

Il canale separato20% conserva quasi l'NDCG del riferimento e riduce la quota nel quintile peggiore:EU19,32%→17,05%, USA25,56%→24,44%. Il payoff statico63 cresce da3,304a3,419ppEU e da3,087a4,007ppUSA. Non domina tutte le metriche: payoff21USA e NDCGUSA calano lievemente.

## 4. Primo collegamento al portafoglio completo

2021–2024, HALF, IMMEDIATE, costo legacy .001:

|Configurazione|CAGR EU|CAGR USA|MaxDD EU|MaxDD USA|
|---|---:|---:|---:|---:|
|Riferimento MATCHED_REG|20,03%|39,92%|-23,25%|-27,00%|
|Sostituzione diretta NAIVE_CLASS|14,75%|11,13%|-30,39%|-25,91%|
|Canale20% corrente|19,02%|37,98%|-25,81%|-28,99%|
|Canale20% con memoria|25,00%|35,65%|-20,56%|-29,92%|

Il canale con memoria miglioraEuropa e peggioraUSA nel periodo principale. Sulla finestra completa febbraio2019–1luglio2026 produce19,12%EU/43,50%USA contro14,94%/38,13%. Con costi stressati16,49%/39,75% contro12,29%/34,40%. MaxDD full a costo originale:EU identico -33,68%, USA -29,92% contro-30,69%; a costo stressato il MaxDDUSA del candidato è leggermente peggiore. Il20%era fissato prima degli esiti; non è un peso ottimale appreso.

Il2025 effettivo del canale con memoria è16,44%EU/34,16%USA, contro19,54%/12,16%. Nel2026parziale19,46%/64,40%, contro11,58%/54,16%. Sono rendimenti effettivi di periodo, NON CAGR annualizzati del frammento. Questa dipendenza dai periodi è conservata, non nascosta dietro la finestra completa favorevole.

Le prove LAG1 su cinque strutture mantengono il danno della sostituzione diretta. Non sono una certificazione live; gap/breadth ritardati incidono anche sull'armamento degli stop. Il canale20%con memoria non era tra le cinque strutture di questa sensibilità: non gli viene attribuito un test che non ha eseguito.

## 5. Fusione appresa sul compito, non sul CAGR

META2 usa Return percentile e il segnale Hybrid regressivo smussato. META3 aggiunge il logit della probabilità corrente del classificatore. Entrambe imparano lo stesso evento di quintile superiore da previsioni passate fuori campione, con almeno18mesi completi e tutti gli esiti del gruppo anteriori al1gennaio del fit. Pesi mensili uguali, standardizzazione solo sul training, regressione logistica monotona con coefficienti nonnegativi, L2=.01 fissato prima dei risultati. Seianni2021–2026 × due mercati × due modelli =24fit. Warm-up2019–2020: ranking abbinato, probabilità non disponibile e dichiarata come tale.

|Compito del layer, pre2025|EU META2|EU META3|USA META2|USA META3|
|---|---:|---:|---:|---:|
|Brier, inferiore migliore|0,158112|0,157971|0,156985|0,156772|
|Top2 nel quintile migliore|38,64%|39,77%|41,11%|43,33%|
|NDCG@2|0,5557|0,5353|0,5078|0,5370|
|Top2 nel quintile peggiore|18,18%|19,32%|24,44%|16,67%|

L'informazione incrementale del classificatore migliora leggermente la previsione dell'evento e la precisione Top2 nei due mercati. Non dimostra miglioramento di ogni compito: l'NDCG e gli errori di coda europei peggiorano. Un evento binario non distingue l'ampiezza del vantaggio dentro il quintile né la gravità di ogni errore fuori da esso. Anche il piccolo miglioramento Brier non certifica tutte le probabilità per fascia o per regime.

Il payoff21 cambia da1,851a1,130ppEU e da2,656a2,396ppUSA; a63 da3,414a2,792ppEU, da3,110a4,343ppUSA. La qualità dell'evento non viene scambiata per rendimento monetario.

## 6. La verifica integrata dei due metodi appresi

2021–2024, HALF, IMMEDIATE, costo .001:

|Configurazione|CAGR EU|CAGR USA|MaxDD EU|MaxDD USA|
|---|---:|---:|---:|---:|
|Riferimento non appreso MATCHED_REG|20,03%|39,92%|-23,25%|-27,00%|
|META2 senza classificatore|23,29%|26,56%|-23,25%|-24,06%|
|META3 con classificatore|13,80%|30,16%|-31,32%|-26,14%|

META3 migliora la crescitaUSA rispetto aMETA2, ma peggioraEuropa. A costo triplicato:EU11,16% contro20,73%, USA26,07% contro23,12%. DELAY3 e PHASE5 non risolvono la direzione opposta dell'effetto. Non si ritoccano le penalità dopo il risultato e non si usaMETA2perEuropa/META3perUSA per proclamare una sola strategia riuscita.

Esempio europeo al segnale28aprile2023: META2 proponeEEPG.DE/VVSM.DE, META3EEPG.DE/EXX1.DE. Nel maggio effettivo il contoMETA2 rende+6,42%, META3-5,59%. Il confronto è fra proposte ex ante, non un oracle sui vincitori futuri. Il mese incorpora anche la risposta dei controlli e lo stato del conto: non è una causalità attribuita soltanto a un ticker senza controfattuale. Tutti i peggiori mesi per mercato sono conservati.

## 7. Incertezza e decisione

Blocchi mensili appaiati3/6,6000estrazioni,seed20261101; stesse estrazioni nei due universi. Per i target44mesi comuni inseriti nella griglia48 con mancanze esplicite; payoff21 su46; conti su48mesi. GliUSA delle tabelle native hanno45mesi: i delta bootstrap su44possono differire lievemente. Intervalli simultanei entro famiglia conservati; non correggono l'intera ricerca passata.

Incremento precisioneMETA3-META2: EU+1,14punti percentuali, IC esplorativo95%[-7,29;+9,78]; USA su44mesi+2,27pp,[-9,09;+13,41]. Sono effetti incerti, non probabilità posteriori. Lo zero non è un veto automatico. Il vincolo di entrambi i mercati e la separazione dei compiti rimangono.

**Integrato:** interfaccia nativa del classificatore, mapping senza confondere le scale, due fusioni apprese task-native, shortlist controllata, collegamento completo al simulatore e separazione degli output. Registro di integrazione e sorgenti consegnati.

**Conservato come candidato:** canale20%con memoria; META3per la sua informazione sull'evento e il vantaggio condizionaleUSA. Nessuno diventa automaticamente default di capitale.

**Non promosso:** sostituzione diretta del regressore, previsione probabilistica usata come peso, un vincitore scelto dal CAGR migliore. Il classificatore rimane uno specialista; serve ancora una soluzione condivisa per utilizzare la sua informazione senza peggiorare opportunità e rischio europei. Non vengono modificati i riferimenti storici.

## 8. Verifiche e limiti

212percorsi;398454intervalli ricostruiti indipendentemente dalle quantità/cash/Open; errore massimo3,55e-15.11024metriche indipendenti, scarto1,74e-13.4361NDCG confrontati con sklearn, errore3,33e-16. Dodici curveOLC06 esattamente identiche suNAV/quantità/target/ledger; quattro scorecontrolloOLC11 identici. Otto perturbazioni reali del futuro:quattro sui punteggi e quattro sui gruppi/fitMETA3, senza cambiamenti passati.23test nuovi e15inheritedOLC11 passati nei rispettivi progetti. Ripristino in directory pulita:23test,24portafogli ricostruiti con array identici,24probabilità da parametri salvati e tutti i punteggi fissi riprodotti. Nessun verde dichiarato per tutta la storia del repository. Revisione dell'autore, non indipendente.

Un terminale streaming non supportato ha impedito il primo avvio del runner; il log con file assente è conservato. Dopo la creazione del runner la campagna è stata eseguita integralmente. Nessun output parziale è stato usato come risultato finale. Non restano processi di ricerca in esecuzione alla consegna.

Le serie del rischio e i targetV6 sono congelati per isolare il selettore: non è un ridisegnoV6specifico della nuova composizione e le interazioni rimangono possibili. Quote osservate richieste per operare; i controlli non certificano prezzo total-return, distribuzioni, universo sopravvivente, equivalenze economiche, spread, tagli minimi o esecuzione live. Rimane l'assunzione legacy di utilizzare il gap nella stessa apertura. Annualizzazione252sedute come i riferimenti, non un confronto di esposizioni valutarie identiche.

## 9. File e persistenza

Sorgenti e test nuovi sono versionati nel branch `research/olc12-classifier-integration-20261101`; protocolli/checkpoint/report sono leggibili. I parent restano congelati. La copia completa con forecast preparati,12oracleoriginali,24parametriappresi,212NAV/ledger e verifiche è nellaLibrary persistente `/ETF_Research/OLC12_Integrazione_20261101`. L'archivio non equivale a un assetGitHub; l'arretrato dei binari storici non è dichiarato risolto.

Il checkpoint è autonomo per ricalcolare le integrazioni e le simulazioni dai forecast preparati. Rifare gli originali240modelliOLC11 o rigenerare i prezzi richiede i parent identificati daSHA256. Non viene caricata alcuna credenziale né eseguito trading. `main` rimane invariato.

Riferimenti metodologici: documentazione ufficiale scikit-learn su calibrazione e NDCG. Sono definizioni degli strumenti, non validazione dei nostri risultati.
