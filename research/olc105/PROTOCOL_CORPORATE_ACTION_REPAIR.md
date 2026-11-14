# OLC105 — Correzione verificata di operazione societaria

Data: 14 novembre 2026. Correzione della sorgente identificata DOPO il primo replay diagnostico; non e un nuovo tuning della strategia e non viene dichiarata preregistrata prima di qualsiasi risultato.

## Difetto riprodotto
Lo snapshot Yahoo di P500.DE / ISIN IE00B3YCGJ38 passa da circa EUR 1.157,40 il 12 dicembre 2025 a EUR 11,5705 il 15 dicembre 2025. Nel file congelato Close e Adj Close coincidono e Stock Splits e zero. Il salto non rappresenta una perdita del 99%: manca lo split.

## Fonte primaria
Il comunicato ufficiale Invesco del 30 ottobre 2025 conferma 100 nuove quote per ciascuna vecchia, record date 12 dicembre 2025, ex-date/payment date 15 dicembre 2025, senza variazione dell'ISIN. Pagine 2 e 3 verificate visivamente.

https://www.invesco.com/content/dam/invesco/emea/en/product-documents/etf/fund/shareholder-notice/invesco-sp-500-ucits-etf-acc_shareholder-notice_en_281025.pdf

## Correzione e limiti
1. Raw e manifest originari restano invariati. I risultati del replay non rettificato sono invalidati, non presentati come performance economica.
2. Nella copia derivata di ricerca si adottano unita economiche forward: dal 15 dicembre 2025 OHLC moltiplicati per 100 e volume diviso per 100. Ogni unita economica rappresenta da quella data 100 quote effettive. Nessun valore precedente alla data viene cambiato; nessun prezzo viene interpolato o ricostruito arbitrariamente.
3. La correzione riguarda una sola operazione verificata dall'emittente, non uno schema che deduce split dai rendimenti. L'asserzione sul rapporto impedisce una doppia rettifica della stessa sorgente.
4. Sono rieseguiti tutti i passaggi derivati: feature, cluster, previsioni dei modelli congelati, pesi, V6/FAST_LOCK3, conti e controlli World/momentum. Nessun refit o cambiamento dei parametri per recuperare una performance sfavorevole.
5. Conservare l'output non valido e la diagnosi separatamente. Gli altri flag OHLC non sono corretti in modo automatico e i dati non diventano broker-certified.
6. Le unita economiche frazionarie non sono una simulazione di quote intere, disponibilita del conto Trade Republic o fill reali. Questi limiti devono rimanere accanto ai risultati finali.
