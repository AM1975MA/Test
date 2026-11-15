# OLC109 — Blocco adattivo2: mantenere il ranking individuale

Questo blocco viene deciso **dopo aver osservato tutti i110 risultati del blocco1**. È ricerca adattiva dichiarata. Non corregge né sostituisce i casi falliti. Nessun risultato del blocco2 è stato calcolato quando questo protocollo viene scritto e congelato.

## Motivo concreto

CLUSTER_DUAL21 rende10,41%CAGR contro16,82% di LIQ_DUAL21 e peggiora il DD50,61% contro39,26%. Il clustering ha cambiato contemporaneamente il punteggio (mediana di gruppo), l'ETF rappresentante (più scambiato) e la diversificazione. Il nuovo confronto conserva ranking e singoli ETF, cambiando soltanto il vincolo di correlazione. Nel primo blocco PEERS2 raggiunge17,61% con una distribuzione annuale migliore nel2024/2026 ma DD36,91%: due varianti di rischio ne misurano il costo di protezione. Non sono conferme indipendenti del vincitore osservato.

## Regole comuni

Stessi dati V3, costi, ritardi, calendario, contabilità e criteri di successo del protocollo principale. Solo l'universo storico idoneo con mediana turnover63>=EUR100.000 e osservazione corrente valida. Tutti i parametri restano quelli già dichiarati: corr126<=0,85; due posti50/50; soglie15/20% di volatilità; SMA63/SMA200; stop15% dal massimoClose63. Nessuna griglia aggiuntiva dei parametri.

DEDUP_LEADERS: classifica dei singoli ETF per m252, parità ISIN; primo leader immutato; secondo è il primo ETF della graduatoria con correlazione126<=0,85 rispetto al primo. La correlazione usa126 log-rendimenti completati. Se manca un secondo candidato, metà resta in cassa.

DEDUP_DUAL21: stessi leader; emergenti identificati con le regole individuali LIQ_DUAL21 del blocco1, esclusi i due leader, ordinati per accelerazione21 e ISIN. Si prende il primo emergente con corr126<=0,85 rispetto al primo leader; sostituisce il secondo solo se il suo m21 è maggiore. Nessuna ricerca successiva se il primo compatibile non supera il confronto. Si mantiene50/50.

DEDUP_DUAL_PEERS2: stesso algoritmo ma universo limitato ai componenti dei gruppi con almeno2 membri nel clustering già dichiarato. I percentili recenti e precedenti vengono ricalcolati su questo insieme di individui. Ogni titolo mantiene il proprio punteggio; non viene sostituito con il rappresentante del gruppo.

DEDUP_DUAL_TREND_OPP: stessi leader DEDUP_LEADERS e stesse graduatorie recenti di DEDUP_DUAL21; per essere sfidante si richiedono inoltre m252>0, m63>0 e prezzo>SMA200. Si sceglie il primo emergente compatibile dopo questo filtro. Il filtro non modifica i leader o i percentili di partenza. È un test mirato alle sostituzioni deboli, non una protezione dal peggior ribasso2024.

Varianti RISK15/RISK20 ed EXIT63/TRAIL15 applicano le regole identiche del blocco1 alla stessa selezione DEDUP_DUAL21. Rischio senza leva e riduzioni giornaliere; uscite settimanali sell-only, rientri mensili e filtro di ingresso mensile sul criterio di uscita. CLUSTER_PEERS2_RISK15/RISK20 sono esattamente CLUSTER_DUAL_PEERS2 del blocco1 con il controllo di volatilità.

## Matrice:10 configurazioni×5scenari=50 percorsi

1. DEDUP_LEADERS
2. DEDUP_DUAL21 — confronto principale di questo blocco
3. DEDUP_DUAL_PEERS2
4. DEDUP_DUAL_TREND_OPP
5. DEDUP_DUAL_RISK15
6. DEDUP_DUAL_RISK20
7. DEDUP_DUAL_EXIT63
8. DEDUP_DUAL_TRAIL15
9. CLUSTER_PEERS2_RISK15
10. CLUSTER_PEERS2_RISK20

Scenari BASE,ZERO_COST,DOUBLE_COST,LAG1,LAG2 tutti inclusi. Output separati results_stage2; dati, codice finanziario e risultati del blocco1 immutabili. Audit contabile e di segnali anche per questi50 casi. Totale ricerca OLC109:160 percorsi finanziari e32 configurazioni, senza contare gli studi precedenti.

Si riportano tutti i risultati, anni e stress. Confronto principale DEDUP_DUAL21 vs LIQ_DUAL21 controlla il vincolo di correlazione; vs CLUSTER_DUAL21 mostra l'effetto congiunto di mantenere ranking/ETF individuali. Nessuna affermazione di significatività o holdout indipendente derivata dalla scelta adattiva. Il risultato migliore ex post rimane una descrizione.
