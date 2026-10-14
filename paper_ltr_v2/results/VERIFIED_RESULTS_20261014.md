# Risultati verificati e diagnosi

Fonte economica: run38565352286, artefatto11897835491 BUDGET300.
Periodo comune1 febbraio2017–1 luglio2026,2366 osservazioni canoniche.
Tre download dello stesso mercato, non tre campioni indipendenti.

| Ricetta | CAGR r1 | CAGR r2 | CAGR r3 | Media | Span pp | MaxDD medio | Sharpe medio |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE |29.7534%|30.8437%|34.6771%|31.7581%|4.9236|−32.2164%|1.10535|
| ListNet100 |22.8594%|22.1741%|21.3070%|22.1135%|1.5524|−30.6275%|.79916|
| BUDGET300 |22.3416%|20.2949%|21.6360%|21.4242%|2.0467|−31.8049%|.78266|

Disaccordi giornalieri any tra download: Top1 BASE43.0262%,10024.0068%,
30023.1192%; Top2 ordinato76.5850%,50.7185%,51.5638%.
Non confondere con media delle tre coppie nello schermo predittivo.

Decisione: respingere BUDGET300. Variazione CAGR medio−.6893pp vs100;
drawdown peggiore in tutti3, span più ampio. Tutte90reti fermate per patience,
nessuna al limite300; riduzione mediana KL validation sui63 checkpoint
.26054%, sotto1% fissato. Non dimostra sovra-addestramento né inutilità
di ogni ListNet possibile. BASE conserva vantaggio economico, ma resta
instabile: non viene dichiarata pronta per produzione.

LINEAR originale: FAILED, primo2017/r1, gradinf1.1632278976516936e−7
contro soglia1e−7 a2000 iterazioni. Nessun CAGR disponibile.
La diagnostica38578561014 riproduce esattamente il residuo e mostra memoria
L-BFGS congelata dopo iterazione370,1629 correzioni scartate. Loss/gradiente
corretti nei controlli matematici/sintetici. Protocollo separato per eventuale
riparazione: diagnostics_solver/LINEAR_NUMERICAL_REPAIR_PROTOCOL.md.

Analisi nuova dei percorsi salvati: diagnostics_download/NOTA.md e
ATTRIBUTION.json. Nel confronto BASE r3-r1,95.66% del gap logwealth emerge
nei giorni con stessa coppia ordinata, soprattutto con pesi differenti.
È partizione contabile, non prova causale. Lo studio già concluso
forensics_v1/results/EXECUTION_ABLATION.json aveva mostrato span di appena
.000021979pp eseguendo le stesse decisioni r2 sui tre raw: non ripetuto.
Priorità diagnostica successiva: costruzione dei pesi/confidence e stati
upstream, oltre alla sola stabilità dei leader. Nessun nuovo correttore
basato sulle feature sviluppato o stimato.

Fonti: https://github.com/AM1975MA/Test/actions/runs/38565352286
e https://github.com/AM1975MA/Test/actions/runs/38578561014.

## Nuova esecuzione LINEAR_NUMERICAL_REPAIR completata

Run38580178650/job115907692294 SUCCESS. Artefatto11904405387,
ZIP SHA4b3ab7c8bc2a8e2ee235628633a793928fc3f94112bb470269bd0d89419ab0a1.
Il FAILED originale rimane tale; questa esecuzione usa il protocollo separato
con filtro curvatura relativo. Tutti30fold completati, massimo495 iterazioni,
massimo residuo dichiarato9.99575440173981e−8 (soglia invariata1e−7).

| Download | CAGR LINEAR | MaxDD LINEAR | Sharpe LINEAR |
|---|---:|---:|---:|
| r1 |29.6646%|−28.7053%|1.03274|
| r2 |32.8665%|−28.2428%|1.11609|
| r3 |32.4212%|−28.4096%|1.10239|

Media CAGR31.6508%, MaxDD−28.4525%, Sharpe1.08374. Span CAGR3.2018pp,
deviazione standard popolazione1.4161pp. Disaccordi any: Top120.7523%,
Top2 ordinato52.8740%, non ordinato41.4624%.

Contro BASE: CAGR medio−.1073pp, MaxDD medio migliore3.7639pp,
span inferiore34.97%, disaccordo Top1 più che dimezzato. Il rischio migliora
in r1/r3 ma peggiora in r2 di2.5531pp. Il CAGR r3 è soltanto93.4946% BASE,
sotto95% fissato. Lo schermo economico resta FAILED; niente promozione.
Non è dominanza su ogni acquisizione né soluzione definitiva della stabilità.

Anche lo schermo predittivo fallisce qualità Top1 e NDCG5: percentile Top1
.495880 contro BASE.583437, NDCG5.504631 contro.551994, RankIC.002036.
Il CAGR è quello del portafoglio V2 completo con solo Compact21 sostituito,
non il rendimento di un ListNet lineare usato autonomamente. Gli altri moduli
e l'allocazione contribuiscono al risultato. Non attribuire il CAGR a qualità
standalone del ranking non dimostrata; il test cambia insieme capacità,
regolarizzazione e forma di ensemble secondo il protocollo già dichiarato.

Ricalcolo locale indipendente dei6 NPZ candidate/control: tutte le metriche
entro2.22e−16 dai risultati CI; dettaglio LINEAR_INDEPENDENT_PATH_CHECK.json.
Certificazione indipendente dei30 gradienti salvati PASS: run38609447579,
job116008713092, nessuna ottimizzazione né rifit. Massimo residuo ricalcolato
9.995754402520435e−8, differenza massima dai residui dichiarati2.9924e−17.
Script diagnostics_solver/verify_linear_stationarity.py; THIRTY_GRADIENTS.json.
Artefatto11917183387, ZIP SHA
49acce3ef4fe7a41a79fb7e0320548a85656e403cb4df7d105d4ab03735f34f0.

Decisione tecnica: respingere le reti100/300 come sostituti attuali. Conservare
LINEAR_NUMERICAL_REPAIR come candidato di ricerca più interessante per il
compromesso osservato, senza adottarlo. Priorità successiva: spiegare
l'amplificazione da score/confidence a pesi e la qualità standalone insufficiente,
senza tuning dei CAGR del periodo già esposto.
