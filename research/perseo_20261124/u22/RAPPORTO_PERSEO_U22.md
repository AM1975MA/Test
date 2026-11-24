# Perseo U22 — prova del filtro economico di cambio

23 novembre 2026. **Esito: proposta respinta nella forma provata.** Ho eseguito 24 conti continui: quattro regole, tre panieri, due livelli di costi. Ai costi ordinari tutte le varianti riducono il CAGR su tutti i panieri. Nessuna sostituisce U20.

## Risultati completi, costi ordinari

Periodo 2 gennaio 2020–1 luglio 2026. 10.000 unità iniziali, 1 unità per ordine + 15 bp per lato. EUR per EU/TR, USD per USA; quote frazionarie, cash senza interesse, fiscalità esclusa. Drawdown alle aperture. USA BASE è il nativo originale al 40,23%, non la variante separata di stop al 44,31%.

|Paniere|Regola|CAGR|Max drawdown|Ordini|
|---|---|---:|---:|---:|
|EU|Perseo U20|20,78%|-31,25%|423|
|EU|Vantaggio netto 21|19,04%|-31,25%|420|
|EU|Confidenza 21|17,42%|-31,26%|384|
|EU|Confidenza 5/21/63|18,97%|-33,87%|408|
|USA|Perseo U20|40,23%|-26,81%|645|
|USA|Vantaggio netto 21|34,79%|-26,81%|637|
|USA|Confidenza 21|37,37%|-26,81%|588|
|USA|Confidenza 5/21/63|38,36%|-26,81%|576|
|TR|Perseo U20|25,07%|-29,53%|535|
|TR|Vantaggio netto 21|23,75%|-29,53%|532|
|TR|Confidenza 21|19,76%|-29,53%|519|
|TR|Confidenza 5/21/63|23,24%|-29,53%|514|

![Variazione del CAGR](PERSEO_U22_CONFRONTO.png)

NET21 perde circa 1,74 punti di CAGR in Europa, 5,44 negli USA e 1,32 su TR. Riduce appena gli ordini: 423→420, 645→637, 535→532. Il filtro prudente LCB21 riduce maggiormente le operazioni, ma perde circa 3,36, 2,87 e 5,31 punti di CAGR. Il drawdown dell’intero periodo non migliora in modo utile. La variante multi-orizzonte peggiora il drawdown europeo fino a −33,87%.

## Come è stato costruito il test

Il ranking e i suoi segnali derivati dai 125/42 input restano congelati. È stato aggiunto un modello di ammissione del cambio; non è un nuovo addestramento di tutte le feature. Il filtro usa una regressione ridge con sei variabili: differenze fra proposta e detenzione di rendimento log a 5/21/63 sedute, volatilità a 21 sedute, distanza dal massimo a 63 e quota di composizione da sostituire. Parametri comuni ai tre mercati, senza identificatori di ticker o mercato fra i predittori.

L’azione confrontata è comprare la proposta rispetto a mantenere le quote realmente presenti nel conto, valorizzate alla chiusura precedente. I costi stimati includono entrambi i lati necessari al cambio e i ticket. Il veto mantiene il precedente target; non provoca ribilanciamenti quotidiani artificiali. Stop, esclusioni, riduzioni di rischio e rientri da cash conservano la precedenza. Le alternative difensive sono quelle congelate U20.

- **NET21:** cambia se il vantaggio medio previsto a 21 sedute supera il costo.
- **LCB21:** richiede che superi il costo anche il limite prudente della stima della media, quantile bootstrap 20%.
- **LCB_MULTI:** confronto esplorativo a 5/21/63 sedute, vantaggio prudente per seduta e quantile 20%/3. L’orizzonte influenza la successiva rivalutazione; non impone una vendita alla scadenza.

Il bootstrap descrive incertezza della media stimata. **Non è una probabilità calibrata di guadagno del singolo trade.** Le etichette sono differenze di rendimento buy-and-hold apertura/apertura; non includono gli stop. Il conto finale include invece tutti gli stop e i costi: questo disallineamento fra previsione e decisione operativa è un limite della versione provata.

## Walk-forward effettivo e limiti temporali

Refit a gennaio con etichette completamente maturate prima dell’inizio dell’anno. Standardizzazione e coefficienti sono stimati soltanto sul passato. Il training pesa in modo uniforme mercato e mese; il bootstrap usa blocchi di tre mesi comuni ai mercati, senza trattare EU, USA e TR come indipendenti.

La soglia fissata nel protocollo richiede almeno 18 mesi distinti per ciascun mercato. Con i campioni validi disponibili **i primi modelli sono utilizzabili nel 2023**, non nel 2022: l’Europa non raggiunge prima il requisito. Le prime decisioni filtrate sono 3 gennaio 2023 per EU/USA e 1 marzo 2023 per TR. Il 2020–2022 resta identico a BASE; quindi questo esperimento non risolve il periodo debole antecedente al 2023 e non può presentare un miglioramento su quel tratto.

CAGR del solo periodo 3 gennaio 2023–1 luglio 2026:

|Paniere|U20|Netto 21|Confidenza 21|Confidenza 5/21/63|
|---|---:|---:|---:|---:|
|EU|39,36%|35,65%|32,23%|35,51%|
|USA|48,10%|37,58%|42,51%|44,44%|
|TR|59,98%|56,85%|47,58%|55,65%|

Tutti questi anni sono già stati usati nella ricerca del progetto. La cronologia del nuovo filtro è verificata, ma ciò non trasforma lo storico in un holdout indipendente. Non abbiamo scelto dopo il test una regola diversa per ciascun paniere.

## Cosa ha fallito, mese per mese

Il filtro non distingue abbastanza bene i cambi utili da quelli evitabili. La riduzione delle operazioni elimina anche rotazioni vantaggiose. Questi sono i sei mesi con maggiore deterioramento del filtro NET21; il file MONTHLY_DIAGNOSIS.csv contiene tutti i mesi, inclusi i miglioramenti:

|Paniere|Mese|U20|Netto 21|Differenza|
|---|---|---:|---:|---:|
|EU|2023-05|4,08%|-5,19%|-9.27 pp|
|USA|2023-01|11,30%|3,65%|-7.65 pp|
|USA|2023-09|-1,08%|-6,66%|-5.57 pp|
|USA|2026-03|-0,05%|-5,55%|-5.50 pp|
|USA|2024-10|6,82%|1,98%|-4.84 pp|
|USA|2023-06|12,82%|9,10%|-3.72 pp|

Un caso concreto: il 2 maggio 2023 il portafoglio europeo propone di sostituire EL4C.DE con VVSM.DE, mantenendo EEPG.DE. NET21 stima un vantaggio di circa 0,028% contro un costo di 0,174% e blocca il cambio; lo blocca anche nelle rivalutazioni successive di maggio. Il conto del mese passa da +4,08% di U20 a −5,19%. È un errore economico molto più grande del costo che il filtro tentava di risparmiare.

Un secondo caso: a gennaio 2023 negli USA viene inizialmente respinta la rotazione da EPOL/PALL a EWN/EIRL. Il rendimento mensile scende da +11,30% a +3,65%. Il risultato dipende anche dai successivi stop e dalle rivalutazioni: non equivale a un semplice rendimento statico dei quattro titoli.

Come controllo descrittivo, fra le valutazioni NET21 respinte con esito osservabile, la proposta avrebbe superato la detenzione e il costo stimato nell’80% dei casi EU, 89,5% USA e 71,4% TR. I campioni sono appena 5, 19 e 14 e comprendono rivalutazioni sovrapposte: **non sono operazioni indipendenti né percentuali di successo affidabili**. Sono differenze buy-and-hold controfattuali, non P&L certificato con stop. Rafforzano la diagnosi di un filtro che scarta opportunità, senza dimostrare una regola alternativa vincente.

## Stress dei costi

Costi portati a 30 bp per lato, stesso ticket e stessa regola; il costo atteso entra coerentemente nelle decisioni:

|Paniere|Regola|CAGR|Max drawdown|Ordini|
|---|---|---:|---:|---:|
|EU|Perseo U20|16,49%|-32,99%|423|
|EU|Vantaggio netto 21|14,50%|-33,01%|418|
|EU|Confidenza 21|15,54%|-34,59%|379|
|EU|Confidenza 5/21/63|14,09%|-34,48%|397|
|USA|Perseo U20|32,96%|-28,11%|645|
|USA|Vantaggio netto 21|30,51%|-28,11%|627|
|USA|Confidenza 21|30,13%|-28,11%|586|
|USA|Confidenza 5/21/63|35,09%|-28,48%|558|
|TR|Perseo U20|19,44%|-36,04%|535|
|TR|Vantaggio netto 21|14,98%|-36,04%|521|
|TR|Confidenza 21|15,49%|-36,04%|521|
|TR|Confidenza 5/21/63|17,48%|-36,04%|515|

L’unico caso favorevole è USA LCB_MULTI: CAGR 35,09% contro 32,96% della base, con drawdown −28,48% contro −28,11%. Europa e TR peggiorano. Non è un miglioramento unificato e non giustifica scegliere quella variante solo negli USA a posteriori.

## Statistica e verifiche

STATISTICS.csv riporta differenze annualizzate di log-rendimento dal 2023, con bootstrap appaiato a blocchi di 12 mesi e 3.000 repliche. Gli intervalli sono nominali e non correggono l’intera ricerca precedente. Per NET21 l’intervallo del peggior paniere è circa da −12,93 a −2,68 punti log annualizzati: il test non fornisce evidenza di miglioramento comune. Gli intervalli non sono intervalli sul CAGR e non vanno confusi con essi.

Verifiche completate: tre repliche BASE bit per bit uguali a U20; 24 ricostruzioni indipendenti di quote e cash dagli ordini; riconciliazione di commissioni e P&L; nove controlli delle variabili rispetto a mutazioni dei prezzi futuri; tre controlli del conto e delle decisioni dopo mutazioni future; tre verifiche che cambiare etichette non ancora mature non alteri i modelli già utilizzabili. QA.json contiene gli errori numerici e i cutoff.

Restano i limiti originari: panieri non completamente point-in-time, prezzi rettificati non verificati con un secondo fornitore, osservabilità USA incompleta, stop a barra e liquidità non garantita. Nessun dato successivo a luglio 2026 è incluso nelle performance.

## Decisione di ricerca

Conservare U20. Respingo queste tre formulazioni del filtro, senza concludere che ogni gestione economica del turnover sia inutile. Questa versione tenta di controllare un selettore ricco con un modello aggiuntivo molto più semplice: le sue previsioni non giustificano il potere di veto sulle rotazioni.

La revisione da considerare deve stimare il valore della decisione comprensivo di protezioni e collegarlo alle previsioni del selettore, verificandone la calibrazione prima di usarlo come veto. Per affrontare il 2020–2022 serve inoltre una base di calibrazione precedente e realmente disponibile a quelle date. Non introduco tali modifiche dopo aver visto questi risultati nello stesso esperimento.

Codice, dati congelati, modelli annuali, ordini, decisioni, risultati mensili e protocollo sono conservati nell’archivio U22. Nessuna modifica alla strategia di riferimento o alle automazioni.
