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
