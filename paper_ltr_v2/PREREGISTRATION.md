# PAPER_LTR_V2 — due ricette fissate, audit prima dei nuovi fit

Registrazione: 12 ottobre 2026, Europe/Rome. Scritta dopo l'accesso completo
agli esiti V1 e prima di qualsiasi fit V2. Non modificare questo protocollo
per scegliere modelli o soglie dopo gli esiti V2. Repository AM1975MA/Test;
nessuna modifica ai file sincronizzati sources/ o alla produzione.

## Motivazione e limiti

Il ListNet V1 ha ridotto la sensibilità osservata, sacrificando qualità e CAGR.
90 checkpoint conservati: 63 arresti al limite 100 epoche, 27 per patience,
nessun checkpoint all'epoca zero. Negli ultimi dieci passi la piccola variazione
della validation loss non dimostra mancata convergenza né promette rendimento.
V2 testa il troncamento del budget e un riferimento lineare regolarizzato;
non certifica l'intera famiglia ListNet. Tutto il 2017–2026 è già esposto.

## Fonti e fase zero senza fit

Tre TI_COMPACT.parquet dal run 37150436612; prezzi frozen dal run 37121749852;
originale ListNet dal run 38179662587; BASE predictive dal run 37229180477;
cache economica BASE dal run 37195399755. Hash, contenuto e assegnazione
repeat devono essere verificati; il nome dell'artefatto non basta.

Prima dei fit eseguire audit dei 90 NPZ originali: feature/order, parametri,
preprocessing, train/subtrain/validation keys, target e label; ricalcolare per
checkpoint CE, H(q), KL=CE−H(q), riferimento uniforme log(n), massa al decile
alto, asset effettivi exp(H), dispersione score, pareggi, concentrazione leader,
qualità di validazione, rendimenti e migliori/peggiori decili ove disponibili.
I rendimenti vengono dai target reali, mai dai percentili. Volatilità antecedente
soltanto per colonne già presenti e nominate nel codice; nessun filtro ETF.
Ricalcolare senza dropout e senza fitting. Richiedere il medesimo profilo
numerico dei fit originali. Audit dati, output e hash rimangono conservati.

Separatamente il preflight replay --audit-only certifica raw→125 feature TI
e label/chiavi, collegamento hash input del fit–BASE–cache, e fingerprint
annuali. I leader dei tre replay V1 devono essere collegati alle date NPZ,
complete, uniche e uguali a BASE. Un fallimento blocca le pretese comparative;
non si riparano fonti mediante imputation nuova o dati Yahoo freschi.

## Ricetta BUDGET300

Modificare soltanto max_epochs 100→300. Conservare 125 feature, MLP64×64,
ReLU, dropout .2, Adam learning rate 1e−4, beta .9/.999, epsilon 1e−8,
clip globale 1, batch16 query, patience25, tre semi101/202/303, float64,
trasformazioni e decili1..10 identici. Stesso checkpoint di validation loss.
I 27 semi fermati per patience vengono riutilizzati con file/hash e predizioni
esatte. Per i 63 limitati, ripartire dalla medesima inizializzazione/RNG,
verificare il prefisso di 100 epoche esatto; i vecchi NPZ non contengono lo stato
Adam/RNG finale e non possono simulare una continuazione equivalente.
Non eseguire ulteriori fit identici di determinismo. Il test di prefisso e
riuso non dimostra determinismo generale di tutte le possibili piattaforme.

Gate diagnostico del budget, sui 63 checkpoint appaiati con stessa entropia,
supporto e target: riduzione relativa mediana KL validation ≥1%; almeno42
checkpoint con KL minore di oltre1e−12; qualità Top1 e NDCG5 validation ≥95%
del rispettivo controllo V1. Ciascun checkpoint media le proprie date e i63
checkpoint hanno peso uguale. KL originale zero produce riduzione0, non
infinita; non può contribuire al miglioramento. Un endpoint mancante non passa.
Queste soglie sono convenzionali, non una prova di convergenza o non inferiorità.

## Ricetta LINEAR

Stesse feature, decili, query, split purgato e preprocessing V1. Score x@w;
nessun bias perché non identificato dalla loss invariante a shift comune.
Loss ListNet media per query +(.001/2)||w||². Penalità .001 fissata, nessuna
griglia. È controllo lineare regolarizzato, non isolamento puro della capacità.
Un vettore per anno/acquisizione, inizializzazione zero, nessun ensemble semi.
L-BFGS NumPy float64, memoria10, Armijo1e−4, massimo50 passi line search,
massimo2000 iterazioni, arresto ||gradiente penalizzato||∞≤1e−7.
Al limite senza tale residuo: fallimento chiuso, checkpoint dei fit completati
e dettaglio del fallimento conservati;
nessun aumento di budget o cambio solver dopo l'accesso ai nuovi esiti.
Audit fase zero collegato agli input obbligatorio prima del fit.

## Split e confronti fissati

Training espansivo annuale2017–2026, acquisizioni native senza intersezione;
signal_date e exit_date21 strettamente anteriori al primo gennaio.
Validazione ultimo10% delle query mature, arrotondamento per eccesso; purge
integrale delle query con qualsiasi exit ≥prima data validation.
Preprocessing solo subtraining purgato, senza full-training refit.
Inferenza fino al30 giugno2026 indipendente dalle label future; qualità solo
query interamente mature entro1 luglio2026. Stessi supporti originali.

Ricalcolare la qualità primaria sulle predizioni native e gli esiti comuni
Repeat2; date equiponderate e poi modelli delle tre acquisizioni equiponderati.
Qualità su feature comuni Repeat2 rimane diagnostica. Stesso gain NDCG lineare,
pareggi score decrescente/ticker crescente. Stabilità: media delle tre coppie,
non disaccordo any. Per ogni ricetta riportare confronti contro BASE e V1.

Schermo predittivo descrittivo vs BASE: RankMAD comune e disaccordo Top1 nativo
ridotti≥25%; Top2 ordinato nativo non peggiore; qualità Top1, NDCG5, Precision5
ciascuna≥95%. Denominatore BASE0 richiede candidato0. Tutte le verifiche dati,
checkpoint, prefix/riuso o residuo solver devono passare. Per BUDGET300 il gate
KL è richiesto congiuntamente. Bootstrap appaiato descrittivo20000 campioni,
seed20261012, blocchi3mesi, sensibilità1/6; acquisizioni unite nella data.
I suoi intervalli non sono ulteriori criteri e non correggono la storia dei test.

## Budget, replay e regola di arresto

Due sole varianti; massimo90 stati MLP annuali/semi (63 nuovi fit,27 riusi)
e30 fit lineari. Nessun nuovo rifit2017, HyperOpt, blending, combinazioni,
feature selection, cambi label, soglia, solver o stopping dopo gli esiti.
Timeout operativo massimo120 minuti per job; un timeout conserva risultati
parziali ed è un'esecuzione incompleta, mai un pass. Nessun rilancio con
budget maggiore senza nuovo protocollo. Controlli originali sempre riutilizzati.

L'utente richiede tutti i CAGR: replay diagnostico entrambe le ricette anche
se gli schermi falliscono, con raw/costi/calendario invariati e discendenti
ricalcolati; il CAGR non può salvare un gate fallito. Gate economici descrittivi:
CAGR media e ogni repeat≥95% BASE, Sharpe media≥95%, drawdown per repeat non
oltre2 punti peggiore, spread CAGR≤75%, disaccordo Top1≤75%, Top2 non peggiore.
Ammissibilità tollerante non equivale a successo: per rivendicare migliore
compromesso, CAGR medio≥BASE e drawdown medio≥BASE (signed negativo), almeno
una disuguaglianza stretta e nessun tradeoff occulto nei repeat. Riportare ogni
repeat, worst case, differenze appaiate e tutte le metriche; nessun vincitore
scelto dal massimo CAGR medio e nessuna adozione in produzione.

Una politica nested2020–2026 è eventualmente una successiva analisi separata
senza fit: selezione nelle sole tre annualità precedenti, label interamente
mature prima del gennaio esterno, scelta su qualità/stabilità, non CAGR.
Non confonderla con il confronto delle due ricette qui fissate e non chiamarla
holdout vergine. Tre download correlati misurano solo sensibilità condizionale
alle revisioni osservate. Gap pregressi di qualità/as-of/universo restano aperti.
