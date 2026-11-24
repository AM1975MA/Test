# Perseo U23 — nove altre strade e selezione walk-forward

24 novembre 2026. **Ho individuato due miglioramenti storici specifici di paniere e un compromesso comune fra rendimento e rischio. Nessuna delle nove regole migliora il CAGR su tutti i panieri; il processo walk-forward comune non supera U20.** Il riferimento rimane U20.

Sono stati eseguiti 102 conti: 60 confronti fissi ai due costi, 30 stress di ritardo e 12 conti walk-forward. Sono simulazioni correlate, non 102 esperimenti statisticamente indipendenti. La famiglia e le regole di scelta sono state scritte nel protocollo prima di produrre i risultati.

## Confronto completo

Periodo apertura 2 gennaio 2020–apertura 1 luglio 2026. Capitale iniziale 10.000; costi 1 unità per ordine e 15 bp per lato; EUR per EU/TR, USD per USA. Quote frazionarie, nessuna leva del conto, cash senza interesse, imposte escluse. Drawdown alle aperture. USA U20 è il nativo originale al 40,23%, non la variante separata al 44,31%.

|Regola|Europa CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|20,78% / -31,25%|40,23% / -26,81%|25,07% / -29,53%|
|25% nell’indice|19,57% / -28,50%|33,33% / -22,55%|22,45% / -24,68%|
|25% condizionato|20,68% / -28,84%|35,81% / -27,08%|24,25% / -27,86%|
|Metà dei titoli deboli → indice/cash|20,56% / -26,32%|34,40% / -26,63%|22,82% / -29,08%|
|Filtro di trend → cash|16,49% / -29,37%|23,99% / -28,70%|20,08% / -28,05%|
|Protezione dal massimo → cash|22,68% / -24,53%|36,06% / -26,41%|23,31% / -33,48%|
|Rientro anticipato|21,05% / -31,24%|40,71% / -27,06%|24,62% / -29,04%|
|Rientro graduale|20,66% / -31,25%|41,71% / -25,27%|23,96% / -28,88%|
|Trend + rientro anticipato|16,98% / -29,35%|23,08% / -29,27%|20,09% / -27,50%|
|Titoli deboli + rientro anticipato|20,87% / -26,31%|34,49% / -26,85%|22,62% / -28,32%|

![Confronto completo](PERSEO_U23_CONFRONTO.png)

## I risultati utili

**Europa: protezione dal massimo della posizione.** Il CAGR passa da 20,78% a 22,68%, mentre il drawdown scende da −31,25% a −24,53%. La regola mette in cash la quota di un ETF quando perde una distanza dal massimo coerente con la volatilità, e rientra dopo una rottura delle dieci chiusure precedenti. Mantiene gli stop originali e rivaluta ogni cinque sedute o al cambio della proposta. La banda è fissata a clamp(2×sigma21×sqrt(5),8%,18%); non è stata scelta dopo il risultato.

Il beneficio europeo compare in entrambi i sottoperiodi: CAGR 2020–2022 da 2,27% a 3,16%, 2023–2026 da 39,36% a 42,40%. Ma la stessa regola porta USA al 36,06% e TR al 23,31%; su TR il drawdown peggiora a −33,48%. Non la promuoviamo selezionando il mercato vincente a posteriori.

**USA: rientro graduale dopo il cooldown.** Al posto di tre sedute tutte al 25%, la quota principale risale a 25%,50%,75%, con limite macro originale e blocchi individuali mantenuti. CAGR 40,23%→41,71%; drawdown −26,81%→−25,27%. Nel 2020–2022 il CAGR passa da 31,62% a 35,04%; nel 2023–2026 scende leggermente, da 48,10% a 47,72%. Europa resta al 20,66% e TR scende al 23,96%.

**Compromesso comune: 25% nell’S&P 500 del paniere.** Riduce la perdita massima su tutti i mercati, ma costa circa 1,21 punti di CAGR EU, 6,90 USA e 2,62 TR. Non è un aumento di rendimento. In TR attenua la debolezza 2020–2022, da −6,05% a −2,92% annuo, ma riduce il CAGR successivo da 59,98% a 49,54%. La quota è all’interno del portafoglio principale e resta sottoposta alle protezioni del motore; non è un investimento passivo esterno al conto.

Il rientro anticipato è la modifica meno invasiva: 21,05% EU, 40,71% USA, 24,62% TR. Sono variazioni contenute e senza evidenza di un vantaggio comune stabile.

## Le strade che hanno fallito

Il filtro di trend lento taglia anche i rimbalzi: su USA il CAGR scende al 23,99%, su TR al 20,08%. Aggiungere il rientro anticipato non recupera la perdita. Anche la riduzione dei titoli con rendimento negativo a 21 e 63 sedute sacrifica rendimento, specialmente negli USA. Il vincolo di una regola comune non è soddisfatto da un collage dei migliori risultati per mercato.

Il ranking e gli input 125/42 rimangono quelli congelati. Questo lavoro modifica allocazione e protezione; non riaddestra un selettore e non attribuisce alle regole di trend una probabilità calibrata di successo. Nessun filtro U22 è usato.

## Mesi che spiegano il risultato

|Caso|Mese|U20|Variante|Differenza|
|---|---|---:|---:|---:|
|Europa, protezione dal massimo|2020-03|−9,27%|−4,28%|+4,99 pp|
|Europa, protezione dal massimo|2025-03|−12,02%|−7,15%|+4,87 pp|
|Europa, protezione dal massimo|2025-04|−7,81%|−2,85%|+4,96 pp|
|Europa, protezione dal massimo|2024-12|+3,25%|−0,14%|−3,39 pp|
|USA, rientro graduale|2020-04|+1,51%|+6,26%|+4,75 pp|
|USA, rientro graduale|2026-02|+2,33%|−0,94%|−3,27 pp|
|TR, protezione dal massimo|2021-05|−8,31%|−12,89%|−4,58 pp|
|TR, filtro di trend|2024-09|+15,70%|+4,32%|−11,38 pp|

Sono esempi esplicativi, non la selezione usata per le metriche. Il CSV di diagnosi riporta tutti i mesi delle varianti e tutti gli scenari. Le differenze mensili sono punti percentuali di rendimento del mese; non si sommano per ottenere il CAGR. Il percorso dipende da posizioni, stop e capitale precedenti: una protezione aggiuntiva può anche peggiorare un mese o il drawdown, cambiando i successivi rientri.

## Robustezza a costi e ritardo

Costi raddoppiati a 30 bp per lato, ticket invariato:

|Regola|Europa CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|16,49% / -32,99%|32,96% / -28,11%|19,44% / -36,04%|
|25% nell’indice|16,10% / -29,16%|27,29% / -23,48%|17,81% / -27,20%|
|Protezione dal massimo → cash|18,33% / -26,94%|29,35% / -27,41%|17,82% / -41,49%|
|Rientro graduale|16,30% / -32,77%|34,12% / -26,77%|18,27% / -36,43%|
|Rientro anticipato|16,75% / -32,98%|33,72% / -28,40%|19,15% / -35,59%|

Segnali differiti di una seduta, costi ordinari; il confronto corretto è con la BASE anch’essa differita:

|Regola|Europa CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|17,89% / -32,13%|41,02% / -29,85%|28,62% / -26,66%|
|25% nell’indice|17,23% / -28,34%|33,72% / -23,96%|25,38% / -24,72%|
|Protezione dal massimo → cash|19,56% / -30,47%|37,82% / -26,46%|26,74% / -31,03%|
|Rientro graduale|18,44% / -30,95%|43,55% / -28,27%|26,93% / -27,76%|
|Rientro anticipato|18,81% / -32,07%|43,58% / -31,22%|28,55% / -26,67%|

I due miglioramenti locali conservano il segno in questi stress. Tuttavia, il ritardo cambia molto anche U20: TR passa da 25,07% a 28,62%, Europa da 20,78% a 17,89%. Non promuoviamo quindi il calendario ritardato dopo averne osservato il rendimento. Questo stress differisce ranking, macro g, alternativa difensiva e guardie nuove; gli stop originali rimangono tempestivi. Non simula un broker completamente indisponibile.

## Walk-forward dell’intero processo di scelta

Ogni gennaio dal 2022, una sola regola per i tre panieri viene scelta sui 24 mesi precedenti. La valutazione usa rendimenti relativi a U20 e una penalità per peggioramento del drawdown; la versione prudente richiede anche un limite bootstrap positivo. Il conto continua con le posizioni e il capitale già presenti. Non vengono concatenate curve di candidati.

La scelta usa esclusivamente patrimoni marcati a chiusure già concluse entro il 31 dicembre. Non entra il rendimento dell’ultima apertura di dicembre verso la prima apertura di gennaio. I cutoff sono salvati in WF_INPUT_CUTOFFS.csv. La valutazione finale resta apertura/apertura.

|Anno|Costi 15 bp: economica|Costi 15 bp: prudente|Costi 30 bp: economica|Costi 30 bp: prudente|
|---|---|---|---|---|
|2022|25% nell’indice|Rientro anticipato|25% nell’indice|25% nell’indice|
|2023|U20|U20|U20|U20|
|2024|U20|U20|U20|U20|
|2025|U20|U20|U20|U20|
|2026|Protezione dal massimo → cash|U20|Protezione dal massimo → cash|U20|

Esito ai costi ordinari:

|Regola|Europa CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|20,78% / -31,25%|40,23% / -26,81%|25,07% / -29,53%|
|Scelta annuale economica|20,26% / -31,25%|37,28% / -26,81%|24,03% / -29,53%|
|Scelta annuale prudente|20,48% / -31,25%|40,06% / -26,81%|24,97% / -29,53%|

La procedura economica sceglie CORE25 nel 2022 e TRAIL_CASH nel 2026, tornando a BASE negli anni intermedi. Il risultato complessivo peggiora. La procedura prudente applica RECOVERY nel 2022 e poi BASE; resta vicina al riferimento ma leggermente sotto. Non c’è una selezione causale comune che realizzi i vantaggi dei migliori casi osservati ex post.

## Confidenza e controlli

Il bootstrap appaiato usa blocchi di 12 mesi e 3.000 repliche, con mesi condivisi fra panieri. Per Europa TRAIL_CASH il vantaggio log annualizzato stimato è +1,56 punti, con intervallo nominale 95% da −1,56 a +4,89. Per USA RAMP è +1,05 punti, intervallo da −0,38 a +2,36. Entrambi includono zero: **i miglioramenti storici locali non sono vantaggi statisticamente dimostrati**. Sono punti di log-rendimento, non intervalli sul CAGR. Non è stata calcolata una correzione integrale per tutti i tentativi storici del progetto.

Verifiche: BASE identica bit per bit a U20 sui tre panieri; 102 ricostruzioni indipendenti di quote e cash dagli ordini; riconciliazione commissioni/P&L; nove mutazioni future dei segnali su tutte le dieci regole; nove verifiche dei conti effettivi; tre mutazioni future delle curve usate per la scelta annuale; sei verifiche di parità del percorso iniziale WF e trenta cutoff annuali validi. Gli errori numerici sono in QA.json.

I dati ripristinati iniziano nel 2020: le nuove variabili usano un riscaldamento causale, senza inventare osservazioni precedenti. Il confronto termina a luglio 2026 e non è aggiornato ai prezzi di novembre. Restano i limiti originari di cataloghi non point-in-time, osservabilità USA incompleta, prezzi rettificati non verificati indipendentemente, esecuzioni degli stop a barra e liquidità. Lo storico era già stato esplorato: il walk-forward nuovo non lo rende indipendente dall’intera ricerca.

## Stato della ricerca

U20 rimane il riferimento. Le due linee locali vengono conservate per approfondimento, con esiti completi e senza adozione automatica. Il risultato utile è aver distinto protezione dalle perdite persistenti, utile in alcuni percorsi europei, e velocità del rientro, utile in alcuni percorsi USA. La difficoltà ancora irrisolta è riconoscere in anticipo quando applicarle con una regola comune, preservando il rendimento di TR. Nessuna modifica alle automazioni o a posizioni reali.
