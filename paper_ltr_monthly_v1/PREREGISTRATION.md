# LINEAR_MONTHLY — confronto fissato prima dei nuovi fit

14 ottobre 2026, Europe/Rome. Utente: «ok prova», dopo proposta di cambiare
soltanto frequenza annuale→mensile. Solo AM1975MA/Test; produzione esclusa.

Riferimento annuale: LINEAR_NUMERICAL_REPAIR run38580178650,
RESULT SHA19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f;
certificato30gradienti run38609447579. Non ripetere fit annuali o BUDGET300.

Unica variazione: cutoff al primo giorno di ciascun mese, anziché solo
1 gennaio; inferenza sulle query del mese corrispondente. Storia espansiva
originale invariata,125 feature identiche, score x@w, L2.001, nessun bias,
zero iniziale, float64, L-BFGS relativo già certificato, memoria10,
Armijo1e-4/max50, max2000, gradinf≤1e-7. Nessuna ricerca di configurazioni.
Le date signal_date ed exit_date21 devono essere strettamente anteriori
al cutoff mensile. Validazione ultimo10% query mature, arrotondamento
superiore; purge intere query con exit≥inizio validation. Preprocessing
stimato solo sul subtraining; nessun refit sull'intero train.

114mesi2017-01–2026-06 ×3download =342 stati. Gennaio coincide esattamente
con l'annuale: riusare30NPZ annuali identici, fingerprint train/split e
predizioni gennaio originali identici per chiave; controllare inferenza
ricalcolata con tolleranza assoluta1e-12. Nuovi fit attesi312, nessun
duplicato di determinismo. Nessuna continuazione warm-start dei coefficienti.
Ogni output appartiene solo al mese corrente, mai a una query passata.

Input: gli stessi tre TI run37150436612 e raw run37121749852, chiusura
raw→TI storica certificata run38565181684/38565352286, BASE cache37195399755.
Nessun nuovo download Yahoo. Confronti sugli stessi supporti/etichette/calendari
2017-02-01–2026-07-01. Tail, MA3, Macro, Opportunity, allocazione, costi,
stop ed esecuzione rimangono canonici; ricalcolare discendenti di Compact21.

Prima del replay, verificare tutti342checkpoint: hash/split/preprocessing,
residui indipendenti, inferenza/parquet e maturazione. Fallimento numerico
o input chiude FAIL; conservare parziali, non cambiare soglia o budget.
Timeout120min/job invariato. Replay diagnostico anche se gate qualità fallisce,
purché integrità/maturazione/solver siano verificati.

Riportare per download CAGR/MaxDD/Sharpe, media e worst case, span e SD CAGR,
Top1/Top2 ordinato/non ordinato any e pairwise; differenze peso sui giorni
con stessa coppia. Qualità Top1/NDCG5/Precision5 su esiti comuni Repeat2,
identica procedura annuale. Confronto primario annuale; BASE contestuale.

Schermo descrittivo mensile vs annuale: CAGR medio≥annuale, ogni CAGR≥95%
del corrispondente annuale; MaxDD medio≥annuale (segno negativo), nessun
repeat peggiore oltre2pp; Sharpe medio≥95%; span CAGR≤annuale; disaccordi
Top1any e Top2ordinatoany≤annuale; qualità Top1/NDCG5/Precision5≥95%.
Tutti richiesti, almeno un miglioramento stretto in CAGR medio/MaxDD medio/
span/disaccordoTop1. Soglie convenzionali, nessuna prova di non inferiorità.
I gate BASE già fissati restano riportati separatamente senza cambiarli.

Decisione di ricerca motivata con tutti i risultati, nessuna promozione
automatica. Non scegliere il massimo CAGR medio ignorando stabilità o DD.
Periodo già esposto e tre revisioni dello stesso mercato, non holdout
vergine né campioni indipendenti. Nessun correttore di feature o terzo test.
