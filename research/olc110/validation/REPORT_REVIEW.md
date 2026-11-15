# OLC110 — Revisione finale del rapporto

**Esito: APPROVATO PER IL SALVATAGGIO. Nessun errore materiale rilevato e nessuna modifica obbligatoria residua.**

Rapporto: `RAPPORTO_OLC110_IT.md`.
SHA-256: `07e20914831f302ea06fe0329717ad49f64d25407b6be14ff78fbab456c26eeb`.
Generatore: `analysis/build_report.py`, SHA-256 `5d95e6d3bc7412c7b8707b2544ca8f9755f356185acfc3f15f7e03b35237b495`.

La revisione riguarda la versione finale, comprese le precisazioni su LBRA e sui cinque scenari del candidato OLC109 archiviato. Sono stati scritti soltanto questo documento e REPORT_REVIEW.json. Nessun conto, strategia, diagnostica di esecuzione, bootstrap o nuovo percorso finanziario è stato rieseguito. Rapporto, codice, grafici e manifest precedente non sono stati modificati dal revisore.

## Numeri e decisione

Le sei tabelle, per **48 righe e 227 celle numeriche**, corrispondono alle fonti archiviate dopo il corretto arrotondamento. Il controllo comprende tutti i 13 casi BASE, i 78 CAGR per scenario, attività/costi, le annualità visualizzate con il 2024, il segmento 2021–2026 e i cinque gruppi diagnostici a 21 sedute.

La mancata promozione di nuove protezioni è coerente con i conti: il candidato primario registra CAGR 6,61% e drawdown −46,78%, contro 25,75% e −37,92% del riferimento. Nessuno dei 78 percorsi raggiunge CAGR30. EXIT63_STAGED è il miglior CAGR dinamico BASE, ma STATIC_75 lo supera nelle due misure dichiarate.

La dominanza delle nove protezioni da parte di STATIC_75 è **esplicitamente limitata allo scenario BASE**. Il rapporto riconosce risultati non monotoni con i ritardi e il confronto favorevole di TRAIL15 in LAG1, senza promuoverlo come variante scelta a posteriori. I controlli nominali e il drift dei pesi fra ribilanciamenti sono descritti correttamente.

## CAGR, bootstrap e NEXT_CLOSE

La differenza di **−19,14 punti percentuali di CAGR** è distinta dalla differenza media logaritmica annualizzata **−16,51**, con intervallo descrittivo **[−28,47; −5,15]** nelle medesime unità logaritmiche scalate per cento. Il testo esplicita la differenza di definizione rispetto ai CAGR basati sui giorni di calendario, gli 80 mesi, i blocchi circolari di sei mesi, 10.000 repliche e seed 110. Non presenta l’intervallo come una correzione dei confronti multipli o come prova fuori campione.

La ricostruzione a blocchi resta una descrizione condizionata al campione; non costituisce un test formale di esclusione a turno di ciascun anno. Il rapporto mostra separatamente le annualità e il segmento successivo al 2020.

NEXT_CLOSE è correttamente descritto come esecuzione al primo Close osservato e accettato successivo al segnale. Il drawdown Close prima/dopo costi è distinto dal campionamento Open/Close e non viene presentato come una misura intraday equivalente.

## Ingressi puri, istruzioni miste e censura

Il candidato primario BASE ha **69 istruzioni FRESH pure**, delle quali **68 complete a 21 sedute**. Il solo ingresso puro censurato è l’istruzione 486 su **IS0D, ISIN IE00B6R51Z18**, non LBRA.

Le medie e le frequenze del rapporto sono state riconciliate anche aggregando INTERVAL_MARKOUTS.csv, senza rieseguire rami finanziari. Per gli ingressi puri sono corretti +37,73 bp medi a 21 sedute, 57,35% di casi favorevoli e +1,80 bp a cinque sedute. Le medie annuali 2022 e 2024 sono negative, come dichiarato.

| Istruzione | Categoria | Segnale | Esecuzione | Orizzonte disponibile | Differenza parziale |
| --- | --- | --- | --- | ---: | ---: |
| 479 | Mista: FRESH LBRA e rientro dell’altro ETF | 9 ottobre 2026 | 12 ottobre 2026 | 15 sedute | −607,75 bp |
| 481 | Conferma del probe LBRA | 13 ottobre 2026 | 14 ottobre 2026 | 13 sedute | −578,94 bp |

Il rapporto attribuisce espressamente **−607,75 bp all’intera istruzione mista**, comprendente anche IE000O5M6XO1. Non lo attribuisce al solo LBRA. Entrambe le finestre sono censurate rispetto a 21 sedute, si sovrappongono e il testo vieta di sommarle.

La lettura economica è circoscritta adeguatamente: il rapporto esclude che la media degli ingressi puri dimostri alpha o il successo globale delle opportunità. Dichiara il confronto con cash, il possibile premio per il rischio, la selezione condizionata ai conti del modello fallito, le finestre sovrapposte, le azioni miste e la censura. L’indizio locale non viene trasformato in una giustificazione del conto complessivamente negativo.

I totali di **3.869 eventi**, **11.607 intervalli**, **101 intervalli troncati**, **82 eventi coinvolti** e **4.395 esecuzioni diagnostiche** corrispondono all’evidenza conservata.

## Fonti, capienza e archivio

Sono coerenti con l’audit delle fonti i 235 ISIN negoziati, 81 nuovi, 238 storie esaminate, l’anzianità massima di cinque giorni e i 65 ordini almeno pari al turnover giornaliero di sede, ripartiti in 55 Open e dieci Close. I massimi di partecipazione e gli impatti LBRA riportati corrispondono alle tabelle. I limiti su capacità, catalogo, aggiustamenti e disponibilità dell’Open sono conservati.

EUR566,41 per REFRESH_WEEKLY rappresenta il P&L di prezzo intraday prima della commissione di acquisto, come nella colonna sorgente; non è un nuovo rendimento netto di strategia. Perdite e guadagno di prezzo restano conservati. I numeri del contributo VIX e della quota di perdita nei gap dei 20 peggiori giorni corrispondono alle tabelle forensi e sono presentati come descrittivi e retrospettivi.

La descrizione dell’archivio OLC109 — 200 risultati, cinque conti completi dei diversi scenari di un unico candidato e 428 file remoti verificati — corrisponde a GITHUB_SAVE_RECEIPT.json. Il controllo usa audit e ricevute archiviati; non scarica nuovamente oggetti GitHub, dati di mercato o articoli scientifici.

## Giudizio

La versione identificata dagli hash sopra può essere salvata. Le conclusioni conservano gli esiti negativi, distinguono bootstrap e CAGR, limitano la dominanza a BASE e non trasformano i markout degli ingressi puri in una promozione delle opportunità complessive. Il JSON conserva hash, copertura e dettagli dei casi censurati.
