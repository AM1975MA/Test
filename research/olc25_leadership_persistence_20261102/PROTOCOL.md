# OLC25 — Persistenza ex-ante della leadership, due universi

Data: 2 novembre 2026. Lotto esplorativo separato dopo OLC24 (non ancora concluso). Parent economico congelato: OLC20 6c387fac4c2e544bb9dc90f6622cd94faba6d7c2; punteggi AUTH FUSION OLC20, stato OHLC/prezzi e motore OLC19. NON è un holdout vergine; nessuna promozione operativa.

## Ipotesi
EU165 potrebbe sottopesare leader persistenti su 6–12 mesi nonostante segnali di forza già noti. Evitare una regola costruita sul ticker QDVE.DE: feature computate identicamente per tutti gli ETF di entrambi gli universi. La prova va fatta anche su USA149; preservare i risultati sfavorevoli.

## Origini, casualità e missing
Per ogni data di segnale t dopo la chiusura, usare esclusivamente C[t] e C[t-L] da STATE_HALF, L=126 e 252 sedute; i dati del giorno di ingresso successivo NON entrano nella feature. EU richiede observed sia a t che t-L, USA non ha la maschera originale: accettare solo quote finite positive della matrice preparata, limitazione dichiarata. Nessun fill di valori mancanti nella feature. Fino a quando l'intera finestra L non è disponibile il segnale è neutro. Ticker senza dati sufficienti rimane eleggibile nel ranking AUTH, con contributo neutro.

Momentum relativo: r_L(t,i)=ln(C[t,i]/C[t-L,i]); trasformazione cross-sectional in rango percentuale P_L in [0,1] tra i ticker validi dello stesso mercato e data, con pareggi medi e ordine deterministico di ticker. P=1 significa momentum più alto.

Tre famiglie prestabilite:
- M126: percentile del momentum a 126 sedute.
- M252: percentile del momentum a 252 sedute.
- PERSIST3: media aritmetica di P126 del segnale corrente e dei due segnali mensili precedenti; occorrono tutti e tre, altrimenti P=0.5 neutro.

Due pesi per famiglia: w in {0.20,0.40}, formula S=(1-w)*AUTH_FUSION+w*P. Per missing P=0.5; non utilizzare le etichette future nel segnale. Come controllo, w=0 riproduce esattamente AUTH.

## Negative controls
Per ciascuna delle tre famiglie a peso 0.40: cinque repliche con seed {25001,..,25005}, rimescolando il blocco percentile fra ticker della stessa data e mercato, mantenendo distribuzione e maschera; niente selezione dei seed. Le repliche sono descrittive, non p-value o probabilità posteriori. Sono 6 varianti autentiche + 15 controlli negativi + AUTH, senza ricerca ulteriormente guidata dagli esiti.

## Verifiche causali
- Perturbare soltanto prezzi successivi alla data testata non modifica punteggi/decisioni antecedenti.
- Tutti i percentili derivano solo da Close <= signal_date e maschera quote prevista.
- QDVE non viene privilegiato; stessi pesi e parametri USA/EU, anche per ETF mancanti.
- AUTH w0: scelte e 8 conti EU/USA/ALARM+FAST_LOCK3/fees .001+.003 esattamente identici a OLC20.
- V6 ricostruito per coppia candidata senza duplicare Top2; ogni convalida economica ricalcolata indipendentemente.

## Obiettivi e analisi
Primario: CAGR 2021–2024 HALF, OLC20 FAST_LOCK3 e ALARM, fee legacy .001, confronto matched contro AUTH sia EU165 sia USA149. Evidenziare i peggioramenti. Una variante è un challenger comune solo se aumenta CAGR nei due mercati sotto *lo stesso* contratto; ranghi di candidati condivisi, niente scelta di w per mercato.

Secondari: fee .003, full febbraio 2019–luglio 2026, MaxDD, turnover, anno per anno, frequenza Top2 del miglior ticker retrospettivo solo come diagnostica, non criterio selettivo, e diagnostica su più top-decile ex-ante. Anche se il CAGR sale, controllare che non dipenda da pochissimi mesi.

## Limiti
Non dimostra alpha prospettico; confronto col miglior ETF ex-post soffre selection bias. I dati total-return/FX/delistings/USA quote masks e fill intraday non sono certificati. Non si cambia main, non si opera sul mercato.
