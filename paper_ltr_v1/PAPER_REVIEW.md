# Valutazione del lavoro e trasferimento a V2

Fonte primaria: [Poh, Lim, Zohren e Roberts, Building Cross-Sectional Systematic
Strategies By Learning to Rank](https://arxiv.org/html/2012.07149).

Il paper studia azioni NYSE nel periodo1980–2019, portafogli mensili long/short
di100 titoli per lato e volatilità obiettivo15%. Confronta regressione, momentum,
RankNet, il ranker ad alberi, ListNet e ListMLE. Nei risultati pubblicati,
ListNet ha Sharpe1,970 e il ranker ad alberi2,156; i costi di transazione sono
esclusi. Gli autori non trovano una superiorità generale dei metodi listwise.
La loro implementazione ad alberi usa XGBoost rank:pairwise: questa famiglia
è già presente in V2 e non va proposta come una scoperta nuova.

Il contributo utile è l'addestramento sulle relazioni fra strumenti della stessa
data. La rete ListNet e la sua loss forniscono un candidato diverso dal ranker
V2 e dai Ridge già testati. Il paper non testa revisioni dei prezzi o refit
fra download: i suoi risultati non dimostrano la robustezza che cerchiamo.

## Cosa misuriamo realmente

La nostra prova trasferisce una singola rete ListNet a Compact21:125 feature,
tre seed, decili futuri a21 sedute, fit annuale causale, query complete,
validazione temporale purgata e checkpoint migliore. Ricetta e scelte non
specificamente documentate dagli autori sono in PREREGISTRATION.md. Non
riproduciamo CRSP, le50 ricerche HyperOpt o il portafoglio long/short del paper.
L'obiettivo è misurare se questo trasferimento produce selezioni migliori e
meno sensibili ai nostri tre download, conservando la strategia economica V2.

La sensibilità ha tre livelli diversi: confronto fra reti su feature comuni
Repeat2; selezioni su ciascun input nativo; risultati economici dopo allocazione
e gestione del rischio. Un miglioramento di uno solo non prova gli altri.
Gli esiti futuri per qualità sono comuni Repeat2 per evitare di cambiare
contemporaneamente modello e metro di giudizio.

Un limite dei decili è che strumenti diversi nello stesso decile ricevono
identica supervisione: una buona separazione fra gruppi può lasciare debole
la discriminazione del singolo vincitore. V2 investe su Top1/Top2, mentre
il caso empirico del paper diversifica molto di più. Questa è una questione
da valutare nei risultati, non una spiegazione già provata del loro esito.

La loss è liscia negli score; la rete e la scelta dell'epoca non sono un
problema convesso con ottimo unico. Label a decili, ReLU ed early stopping
introducono comunque soglie. La determinazione dei seed assicura soltanto
una procedura ripetibile: non garantisce selezioni invarianti ai dati.

## Valore e limiti della prova economica

Il replay riusa modelli invariati soltanto dopo aver verificato che non sono
discendenti del valore Compact21 nel training. TIT_R e la colonna BASE della
composizione MA3 vengono invece ricostruiti. Il controllo riproduce prima
la BASE storica: equivale a verificare il percorso prima di interpretare
il trattamento. La richiesta dell'utente di ottenere il CAGR ha esteso
il protocollo al replay anche in caso di gate predittivo fallito.

Original149 è un campione di sviluppo già consultato. Le tre acquisizioni
sono revisioni correlate dello stesso mercato, non tre repliche indipendenti.
Un risultato favorevole dimostra al massimo una possibilità empirica locale;
una promozione richiede verifica successiva fuori dal campione usato per
scegliere il metodo. Un risultato sfavorevole respinge la ricetta provata,
non l'intera famiglia Learning to Rank.

## Revisori e responsabilità

- Agente di ranking finanziario: lettura paper, ricetta dichiarata, runner.
- Agente matematico/implementazione: loss e gradienti, causalità dello split,
  rete NumPy e replay del grafo dei componenti.
- Agente statistico: supporti appaiati, target comuni, incertezza e verifica
  indipendente dei gate. Ha individuato il caso BASE con denominatore zero
  e controlli di provenienza mancanti, corretti senza cambiare il fit.
- Coordinatore: verifica indipendente, Actions, conservazione degli artefatti
  e sintesi. La discussione finale avverrà sui risultati, in italiano.

Questi sono ruoli di agenti AI; gli autori reali del paper non partecipano
alla revisione e non hanno approvato il nostro esperimento.
