# Perseo — addestramento per scegliere il cluster

24 novembre 2026. **Il segnale sui cluster esiste in alcuni casi, ma questo test non giustifica un filtro che obblighi Perseo a investire soltanto nel cluster scelto dal modello.** Il caso migliore da verificare ancora è Ridge sugli otto cluster storici USA. Nei cluster ricostruiti per correlazione, il momentum a 21 sedute ha battuto tutti i modelli addestrati su tutti e tre i panieri una volta ripristinata la copertura TR.

## Cosa ha imparato il modello

Una riga è un cluster, con rendimento, dispersione, volatilità, ampiezza dei rialzi e regime di mercato calcolati dalle chiusure precedenti. L'obiettivo è il rango del rendimento del cluster equiponderato nel mese seguente, da apertura ad apertura. Il modello sceglie il gruppo senza ticker, nomi di gruppo o score individuali. Tutti i cluster ammessi hanno almeno due ETF. I due modelli sono Ridge e HistGradientBoosting, prima addestrati sui tre panieri insieme e poi su ciascun paniere per la verifica diagnostica. L'addestramento è rifatto ogni mese sulle sole etichette maturate prima dell'apertura della decisione. Il periodo di valutazione è ottobre 2021–giugno 2026, ultima apertura di valorizzazione il 1º luglio 2026. Le quotazioni precedenti servono alla costruzione delle feature e al primo fit.

Tre costruzioni del gruppo: correlazione, otto cluster storici Perseo e tassonomia economica EU165. La correlazione usa 126 variazioni passate, soglia 0,85 e complete-link. Trade Republic usa la whitelist U19 e un filtro sul turnover mediano osservato di almeno 100.000 EUR. Nei replay con costi, lo stesso metodo neutrale sceglie fino a due ETF per ciascuno dei due cluster. Usa il turnover storico se disponibile, altrimenti copertura osservata e ordine alfabetico a parità. Le metriche di prevedibilità usano invece tutti i membri del cluster, equiponderati.

## Risultato per correlazione

Sensibilità che recupera gennaio–giugno 2024 su TR. Il confronto economico è il rendimento lordo mensile medio dei due cluster scelti meno la media equiponderata dei cluster contemporaneamente disponibili. I valori dei modelli nella tabella indicano il migliore esito osservato per quel paniere fra Ridge e HGB nei fit comuni e nativi. È una descrizione, senza combinare modelli come strategia.

| Paniere | Mesi | Cluster medi | Momentum 21, cluster migliore | Caso uniforme | Momentum 21, vantaggio Top2 | Miglior modello, vantaggio Top2 |
|---|---:|---:|---:|---:|---:|---:|
| Europa | 57 | 26,8 | 19,3% | 3,8% | +0,70 pp/mese | +0,20 pp/mese |
| USA | 57 | 26,0 | 14,0% | 3,9% | +1,48 pp/mese | +0,46 pp/mese |
| Trade Republic | 57 | 81,7 | 7,0% | 1,3% | +1,37 pp/mese | +0,73 pp/mese |

Il dato più utile è la differenza di rendimento fra le scelte dei due metodi. La probabilità di trovare il singolo cluster migliore fra circa 82 gruppi TR è bassa anche per un segnale utile. Prima del 2024 il vantaggio medio del momentum a 21 sedute sulla media dei cluster era −0,41 punti mensili in Europa, +0,12 negli USA e +0,12 su TR. La parte più ampia del guadagno viene dal periodo successivo. Gli intervalli simultanei del vantaggio su media dei cluster contengono zero per il momentum a 21 sedute in tutti e tre i panieri.

## Dove resta un segnale da verificare

- **USA, otto cluster storici.** Ridge addestrato insieme sui tre panieri sceglie il cluster migliore in 14 mesi su 57, pari al 24,6% contro 12,5% atteso dal caso. Nella sensibilità completa il Top2 guadagna +0,61 punti mensili rispetto alla media dei cluster, intervallo simultaneo 95% da +0,12 a +1,11. Contro momentum a 21 sedute il guadagno è +0,62 punti, con intervallo da −0,34 a +1,57. Il segno rimane positivo prima del 2024 (+1,01 punti) e dal 2024 (+0,26), con margine più piccolo. Nel conto a 15 bp con ETF scelti secondo la stessa regola neutrale il CAGR passa dal 4,18% del momentum al 12,29% del Ridge, con drawdown −27,10% e −23,04%. Questo è il confronto entro gli stessi otto cluster e non un risultato del motore U27.
- **Trade Republic, cluster per correlazione.** HGB nativo passa da +0,22 a −0,83 punti mensili rispetto al momentum a 21 sedute quando entrano i sei mesi mancanti e si rifà il fit. La diagnosi trova una caduta da circa 1.200 ticker osservati a 21, 13 e 23 nelle sedute del 4–6 dicembre 2023. La sensibilità filtra dal calendario delle feature le sedute sotto il 20% della copertura mediana storica. Identifica anche il 24 ottobre 2025. I prezzi di esecuzione restano quelli originali. Il risultato non sostiene un selettore TR appreso.
- **Europa, tassonomia economica.** HGB migliora di +0,12 punti mensili rispetto al momentum a 21 sedute e di +0,39 rispetto al momentum combinato. L'evidenza statistica resta debole. I gruppi derivano dalla classificazione archiviata e includono categorie grossolane, con possibili cambi di indice storici.

## Controlli e interpretazione

I tuoi dati contengono maschere di osservabilità per EU e TR. Per USA la fonte congelata fornisce prezzi finiti e positivi senza una maschera separata. Restano i limiti dei cataloghi retrospettivi, dei prezzi e della liquidità. La sensibilità esclude sedute anomale dalle feature senza trasformare una quotazione mancante in un'esecuzione. I conti simulano 1 unità per ordine più 15 o 30 punti base per lato, senza protezione U27. I file rendono disponibili copertura, scelte, ordini e NAV. Sono stati verificati 56 conti per passaggio, 21 controlli sulle feature dopo perturbazione dei prezzi futuri e 27 sui fit dopo perturbazione di etichette non maturate per passaggio. La statistica usa blocchi di sei mesi e confronti simultanei fra i candidati di ciascuna metrica. L'estensione nativa e il filtro sui buchi TR sono analisi successive al protocollo iniziale. Lo storico resta già esplorato.

Perseo ha quindi evidenza di un possibile **segnale di contesto**, in particolare negli otto gruppi USA, e di una regola semplice di momentum utile come riferimento. Prima di addestrare un selettore all'interno del cluster serve stabilire su mesi nuovi se il primo stadio batte il momentum e quante volte escluderebbe un ETF che il ranking completo avrebbe selezionato con profitto. In questo test la selezione intra-cluster è rimasta neutrale.

## Riproduzione

Lo ZIP completo contiene sorgenti, audit, scorecard, previsioni per tutti i cluster e risultati dei due passaggi. Per ricostruire le feature occorrono i quattro input di origine, con SHA-256 in `results/QA.json`:

- `PERSEO_UNIFICATO_RICONCILIAZIONE_20261121.zip` per prezzi EU165 e USA149.
- `PERSEO_U19_DATI_COMPLETI.zip` per prezzi, turnover e appartenenze TR.
- `OLC07_Calendario_Risultati_20261101.zip` per le appartenenze storiche P0 Europa e USA.
- `EU165_ECONOMIC_TAXONOMY.csv` per il controllo a tassonomia economica.

Da `cluster_only` con il file `../u24/broker_cost.py` disponibile:

```sh
python experiment.py --inputs /percorso/input
python native.py
python analyze.py
python experiment.py --inputs /percorso/input --output results/outage_sensitivity --skip-tr-outages
python native.py --results results/outage_sensitivity
python analyze.py --results results/outage_sensitivity
```
