# Perseo U24 — protezione condizionata e rientro

24 novembre 2026. **Migliorato il compromesso rendimento/drawdown, ma ancora nessun vantaggio comune dimostrato in walk-forward.** Il candidato più equilibrato è PROFIT_RAMP: 23,85% di CAGR EU, 39,99% USA, 25,36% TR. Riduce il drawdown rispetto a U20 su tutti e tre, a costo di 0,24 punti di CAGR USA. La variante migliore in Europa arriva al 24,95% con drawdown −22,98%, ma danneggia gli altri panieri. Non viene adottata scegliendo retrospettivamente il mercato vincente.

Sono stati eseguiti 120 conti:108 fissi/stress e12 walk-forward. Sono simulazioni correlate. Nove regole nuove, tre controlli U23. Protocollo congelato nel commit locale c2f17b8 prima dei risultati; nessuna variante aggiunta dopo l'esito.

## Confronto completo

Apertura 2 gennaio 2020–apertura 1 luglio 2026. Capitale 10.000; ticket 1 unità/ordine e 15 bp/lato, EUR EU/TR, USD USA. Quote frazionarie, cash senza interessi, niente leva sul conto o fiscalità. Drawdown marcato alle aperture. Il campione termina a luglio, non a novembre. Ranking e input 125/42 congelati, senza riaddestramento del selettore.

|Regola|EU CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|20,78% / -31,25%|40,23% / -26,81%|25,07% / -29,53%|
|Trailing U23|22,68% / -24,53%|36,06% / -26,41%|23,31% / -33,48%|
|Rampa U23|20,66% / -31,25%|41,71% / -25,27%|23,96% / -28,88%|
|Trailing confermato|24,60% / -22,98%|38,76% / -26,67%|23,92% / -33,61%|
|Trailing metà quota|22,05% / -27,56%|37,52% / -26,25%|24,21% / -29,58%|
|Rientro rapido|22,34% / -24,53%|35,54% / -27,08%|21,85% / -33,31%|
|Protezione dei guadagni|23,51% / -27,43%|39,57% / -26,81%|25,39% / -28,41%|
|Banda più ampia|20,50% / -32,40%|39,36% / -27,02%|23,46% / -31,08%|
|Rampa condizionata|21,11% / -31,24%|40,66% / -25,61%|25,05% / -29,06%|
|Conferma + rampa|24,95% / -22,98%|38,82% / -26,67%|23,89% / -33,44%|
|Metà quota + rampa|22,40% / -27,56%|37,77% / -25,65%|24,18% / -29,39%|
|Guadagni + rampa|23,85% / -27,43%|39,99% / -26,60%|25,36% / -27,93%|

![Confronto](PERSEO_U24_CONFRONTO.png)

## Cosa è cambiato

La protezione originale usciva dopo una discesa dal massimo anche se la posizione era appena stata proposta. PROFIT_RAMP permette quella uscita solo dopo un guadagno dal prezzo iniziale della proposta almeno pari alla banda di volatilità. Rientra con il breakout originale; accelera il cooldown soltanto con S&P e proposta entrambi in recupero. La regola è identica nei tre panieri.

La banda è quella U23: clamp(2×sigma21×sqrt5,8%,18%). Il massimo riguarda il ciclo della proposta del selettore, non il costo medio effettivo di carico: non va interpretato come profitto contabile garantito. La rampa conserva stop individuali, allarmi sistemici e limite macro. Le condizioni usano esclusivamente chiusure precedenti; revisione ogni cinque sedute o al cambio della proposta.

Il trailing confermato richiede invece due chiusure deboli consecutive e rendimento 21 negativo. Migliora molto EU, ma non risolve la rotazione TR. Allargare soltanto la banda o rientrare più rapidamente non basta: TRAIL_FAST porta TR al 21,85%, TRAIL_WIDE al 23,46%. Ridurre a metà l'uscita attenua i danni senza creare un vantaggio comune.

![Percorsi](PERSEO_U24_PERCORSI.png)

## Diagnosi mese per mese

|Paniere|Mese|U20|Guadagni + rampa|Differenza pp|
|---|---|---:|---:|---:|
|EU|2020-03|-9,27%|-1,55%|+7,72|
|EU|2025-03|-12,02%|-7,15%|+4,87|
|EU|2020-04|-8,66%|-7,25%|+1,42|
|USA|2024-12|0,61%|-1,25%|-1,86|
|USA|2022-01|14,66%|12,80%|-1,86|
|USA|2020-04|1,51%|3,17%|+1,66|
|TR|2020-08|-0,18%|1,32%|+1,50|
|TR|2021-03|-2,65%|-3,06%|-0,41|
|TR|2026-04|15,94%|15,58%|-0,36|

La ricostruzione per ticker mostra che nel marzo 2020 il vantaggio europeo deriva soprattutto dalla minore perdita su IS3N.DE ( +5,72 punti di contributo mensile) ed EXH1.DE (+1,93 punti). Nel marzo 2025 la riduzione di VVSM.DE vale +5,18 punti, meno 0,31 di costi aggiuntivi. Nel dicembre 2024 USA, invece, la gestione di SMH costa −1,72 punti e i maggiori costi −0,15 punti: l'uscita interrompe un percorso successivamente favorevole. Sono attribuzioni contabili, non una prova causale dell'efficacia futura dei segnali.

**Il 92,62% del vantaggio logaritmico europeo di PROFIT_RAMP proviene da soli tre mesi: marzo 2020, marzo 2025, aprile 2020.** Togliendoli in una verifica descrittiva, il differenziale log annualizzato scende da +2,51 a +0,19 punti. Su TR diventa negativo. Questa esclusione non è una strategia investibile né un test indipendente; misura la concentrazione del risultato.

Molti altri mesi hanno differenze positive minuscole perché il capitale più alto diluisce il ticket fisso. Non sono altrettante previsioni corrette. Con soglia di rilevanza 5 bp di rendimento mensile, PROFIT_RAMP migliora 6 mesi EU e ne peggiora 0; USA 8/5; TR 3/3. I CSV contengono tutti i mesi, anche quelli sfavorevoli, e la decomposizione per ticker/costi dei casi principali.

CAGR per sottoperiodo; il confine comune è l'apertura 3 gennaio 2023:

|Paniere|U20 2020–22|Nuova 2020–22|U20 2023–26|Nuova 2023–26|
|---|---:|---:|---:|---:|
|EU|2,27%|6,02%|39,36%|41,57%|
|USA|31,62%|31,88%|48,10%|47,37%|
|TR|-6,05%|-5,46%|59,98%|59,81%|

La fragilità TR prima del 2023 resta: −5,46% annuo contro−6,05% della base. Non è stata risolta dall'aggiunta di protezioni.

## Costi e ritardo

30bp per lato, ticket invariato:

|Regola|EU CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|16,49% / -32,99%|32,96% / -28,11%|19,44% / -36,04%|
|Guadagni + rampa|19,40% / -29,47%|32,76% / -28,03%|19,71% / -34,83%|
|Conferma + rampa|20,52% / -25,20%|32,06% / -27,67%|18,43% / -41,46%|
|Rampa condizionata|16,81% / -32,98%|33,36% / -26,94%|19,41% / -35,88%|

Una seduta di ritardo, confronto con BASE anch'essa ritardata:

|Regola|EU CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|17,89% / -32,13%|41,02% / -29,85%|28,62% / -26,66%|
|Guadagni + rampa|19,39% / -31,56%|39,63% / -29,85%|28,53% / -26,66%|
|Conferma + rampa|20,38% / -29,85%|41,12% / -26,80%|28,46% / -24,98%|
|Rampa condizionata|17,90% / -32,13%|40,69% / -29,85%|28,38% / -26,66%|

Il vantaggio EU di PROFIT_RAMP mantiene il segno; il piccolo vantaggio TR scompare con il ritardo. Gli stop originari restano tempestivi: lo stress differisce selezione, macro, difesa e nuovi segnali, non simula un'interruzione completa del broker.

## Walk-forward dell'intero processo di scelta

Ogni gennaio dal 2022: scelta di una sola regola comune usando i 24 mesi precedenti; rendimento relativo minimo sui tre panieri e penalità drawdown. Versione prudente con limite bootstrap positivo. I dati di addestramento si fermano a chiusure anteriori al primo gennaio. Nessuna concatenazione di NAV, reset di capitale o cooldown. Prima del 2022 si usa BASE. Gli scenari 30 bp selezionano sui propri costi.

|Anno|WF economico 15bp|WF prudente 15bp|
|---|---|---|
|2022|Guadagni + rampa|U20|
|2023|Banda più ampia|U20|
|2024|Guadagni + rampa|Rampa condizionata|
|2025|Rampa condizionata|Rampa condizionata|
|2026|Rientro rapido|U20|

|Regola|EU CAGR / DD|USA CAGR / DD|TR CAGR / DD|
|---|---:|---:|---:|
|U20|20,78% / -31,25%|40,23% / -26,81%|25,07% / -29,53%|
|WF economico|20,90% / -31,25%|40,21% / -26,81%|24,19% / -29,53%|
|WF prudente|20,78% / -31,25%|40,25% / -26,81%|25,07% / -29,53%|

La scelta economica resta sotto U20 su TR (24,19% contro 25,07%). La prudente replica EU/TR e cambia USA di appena +0,02 punti: **non è un salto qualitativo**. Nei costi 30 bp la scelta economica aiuta EU/USA ma penalizza TR. I risultati fissi promettenti non equivalgono quindi a una procedura capace di sceglierli in anticipo.

## Confidenza statistica

Bootstrap appaiato a blocchi 12 mesi, 3.000 repliche, dipendenza fra panieri preservata. Intervalli sul vantaggio di log-rendimento annualizzato, non sul CAGR e non sulla probabilità che un ticker salga. La diagnostica simultanea, aggiunta dopo gli esiti senza nuove strategie, corregge approssimativamente i 33 confronti della famiglia U24 con max-|t| bootstrap:

|Paniere|Vantaggio log annuo pp|IC95% nominale pp|Intervallo simultaneo famiglia pp|
|---|---:|---:|---:|
|EU|+2,51|+0,15 / +5,62|-1,86 / +6,87|
|USA|-0,17|-0,97 / +0,62|-1,43 / +1,09|
|TR|+0,23|-0,18 / +0,92|-0,63 / +1,10|

Gli intervalli simultanei includono zero. Anche l'evidenza europea nominalmente positiva si indebolisce correggendo i tentativi. La frequenza bootstrap del vantaggio minimo positivo è 26,97% per PROFIT_RAMP: frequenza di ricampionamento, non probabilità futura. La correzione U24 non copre l'intero storico dei test Perseo;78mesi restano pochi per stimare eventi rari.

## Benchmark e interpretazione

Confronti U21 già ricalcolati sullo stesso periodo: S&P 500 14,78% EUR e 15,31% USD; Nasdaq 20,99% EUR e 21,42% USD; tecnologia USA 24,97% EUR con drawdown −33,57%; SMH 40,60% USD con drawdown −46,91%. PROFIT_RAMP EU resta sotto la tecnologia in CAGR, con drawdown inferiore; USA resta vicino al CAGR SMH con drawdown inferiore. Sono confronti di strumenti diversi e rischio diverso, non stima di alpha. Le aperture mancanti EU/TR e le ipotesi di valorizzazione sono documentate in U21.

La letteratura di Levine/Pedersen, [Which Trend Is Your Friend?](https://www.aqr.com/insights/research/journal-article/which-trend-is-your-friend), invita a valutare implementazione, costi e costruzione del portafoglio oltre alla formula del filtro. È un riferimento metodologico, non una validazione di Perseo. Qui le prove mostrano che protezioni simili possono avere esiti diversi per via di stop, rientri e composizione.

## Verifiche e riproducibilità

- Tre BASE identiche a U20; nove controlli BASE/TRAIL/RAMP identici bit per bit a U23.
- 120 ricostruzioni indipendenti di quote e cash dagli ordini, riconciliazione P&L/commissioni.
- Nove perturbazioni future sui segnali di tutte le 12 regole, nove sui conti, tre sui dati di scelta annuale; 30 cutoff verificati e sei parità iniziali WF.
- 15 conti con attribuzione mensile per ticker; 3.587 righe, riconciliazione mensile con errore massimo 1,45e−15.
- 918 file dei manifesti U20–U23 verificati: nessun file mancante o hash diverso.

QA.json e ATTRIBUTION_QA.json registrano i controlli. Il repository preparato include tutti gli stati necessari al replay dei 107 conti U20, input U22/U23, codice, protocolli, risultati e rapporti U20–U24. La ricostruzione dell'addestramento originale precedente richiede ancora U19; non è stata eseguita qui.

Restano aperti: cataloghi non point-in-time completi, rettifiche non verificate con una seconda fonte, maschera osservazioni USA mancante, stop intraday sintetici e liquidità. Lo storico è già stato esplorato: il nuovo walk-forward non cancella il riuso dei dati.

## Decisione

U20 resta il riferimento. PROFIT_RAMP viene conservato come candidato di ricerca per un compromesso più favorevole, non promosso live. Il passo utile successivo riguarda soprattutto la selezione TR nei mesi 2020–2022 e la previsione degli errori di rotazione; i soli filtri di protezione hanno mostrato rendimenti marginali e dipendenza da pochi episodi. Per dimostrarlo servono esiti maturati in avanti o storia non ancora usata, oltre a cataloghi e dati verificati.
