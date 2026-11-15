# OLC110 — Revisione dell’analisi e del grafico

**Esito: PASS.** Le tabelle di analisi, il bootstrap e i valori del grafico corrispondono ai percorsi già verificati. Questo controllo legge e riconcilia risultati esistenti: non esegue un conto, una strategia o un nuovo percorso finanziario. Il manifest di completamento precedente rimane invariato.

## Bootstrap accoppiato

I 78 percorsi producono esattamente 80 rendimenti mensili, da marzo 2020 a ottobre 2026, per 6.240 righe. La somma dei log-rendimenti di ciascun percorso coincide con il logaritmo del rapporto fra patrimonio finale e EUR 10.000 iniziali. La ricostruzione usa gli ultimi Close di conto di ogni mese e concorda con MONTHLY_RETURNS.csv.

Per ciascuna delle 10.000 repliche, con seed 110 e generatore PCG64, vengono estratti 14 inizi uniformi fra i mesi 0–79. Ogni inizio genera sei mesi consecutivi con riavvolgimento circolare; le 84 osservazioni risultanti vengono troncate alle prime 80, mantenendo due osservazioni dell’ultimo blocco. Candidato e controllo usano gli stessi mesi, e la stessa matrice di indici è riutilizzata per tutti i confronti e gli scenari. Il confronto avviene sempre entro lo stesso scenario.

Il controllo indipendente costruisce per replica i conteggi dei mesi estratti, calcola le medie logaritmiche accoppiate tramite questi pesi e ricava i quantili con interpolazione lineare degli ordinamenti. Tutte le 78 righe di PAIRED_COMPARISONS.csv coincidono entro 1e-10 nelle rispettive unità.

La statistica è `100 × 12 × media[log(1+r_candidato) − log(1+r_controllo)]`. L’intervallo riporta i quantili empirici 2,5% e 97,5% di questa statistica. La frazione delle repliche positive non è un p-value, una probabilità bayesiana o la probabilità di successo futuro. I limiti dichiarati nel codice e nel riepilogo sono corretti: analisi descrittiva condizionata a un campione già osservato, senza correzione per confronti multipli e senza holdout incontaminato.

### L’ipotesi primaria: unità distinte

| Quantità, FRESHW contro BASE nello scenario BASE | Valore verificato |
| --- | ---: |
| Differenza di CAGR | -19.143062 punti percentuali |
| Differenza logaritmica relativa annualizzata | -16.507905% log |
| Limite descrittivo inferiore 2,5% | -28.470696% log |
| Limite descrittivo superiore 97,5% | -5.146774% log |
| Frazione di repliche positive | 0.2100% |
| Differenza di drawdown, positivo = miglioramento | -8.858177 punti percentuali |

La differenza fra −19,14 punti di CAGR e −16,51% log annualizzato è attesa: sono statistiche e unità diverse. L’intervallo del bootstrap non è un intervallo per la differenza di CAGR in punti percentuali.

## Confronti dichiarati

Le 13 coppie del codice corrispondono ai controlli e alle variazioni dichiarate nel protocollo. Ogni coppia è presente nei sei scenari: 78 righe senza duplicati o omissioni. Il confronto FRESHW contro BASE è il confronto primario complessivo; gli altri ricostruiscono controlli e variazioni successive. Non sono 13 conferme statisticamente indipendenti.

| Candidato | Controllo | Variazione dichiarata |
| --- | --- | --- |
| STATIC_HALF | BASE | Riduzione permanente al 50% |
| STATIC_75 | BASE | Riduzione permanente al 75% |
| REFRESH_WEEKLY | BASE | Ranking settimanale |
| EXIT21_MONTHLY | BASE | Uscita breve e attesa mensile |
| EXIT21_SLOW | EXIT21_MONTHLY | Rientro lento anche inframese |
| EXIT21_FAST | EXIT21_SLOW | Rientro veloce pieno |
| EXIT21_STAGED | EXIT21_FAST | Rientro veloce graduale |
| EXIT63_STAGED | EXIT21_STAGED | Uscita più lenta |
| TRAIL15_STAGED | EXIT21_STAGED | Uscita da massimo precedente |
| VOLTRAIL_STAGED | TRAIL15_STAGED | Soglia legata alla volatilità |
| EXIT21_STAGED_FRESHW | EXIT21_STAGED | Opportunità nuove settimanali |
| EXIT21_STAGED_FRESHD | EXIT21_STAGED_FRESHW | Opportunità nuove giornaliere |
| EXIT21_STAGED_FRESHW | BASE | Ipotesi primaria contro OLC109 |

## Dominanza del controllo STATIC_75

Nello scenario BASE, STATIC_75 ha CAGR **20.502083%** e drawdown campionato **-31.963091%**. Per tutte le nove protezioni il suo CAGR è strettamente maggiore e il drawdown strettamente meno negativo. La dominanza è quindi verificata anche nella forma più forte, con entrambe le coordinate migliori.

| Protezione BASE | Vantaggio STATIC_75 di CAGR, punti | Vantaggio STATIC_75 di drawdown, punti |
| --- | ---: | ---: |
| EXIT21_MONTHLY | 5.468639 | 1.000815 |
| EXIT21_SLOW | 14.751686 | 19.940432 |
| EXIT21_FAST | 15.590432 | 18.770699 |
| EXIT21_STAGED | 14.529529 | 16.246700 |
| EXIT63_STAGED | 2.998302 | 4.658552 |
| TRAIL15_STAGED | 6.154669 | 13.567173 |
| VOLTRAIL_STAGED | 11.453456 | 16.002119 |
| EXIT21_STAGED_FRESHW | 13.892532 | 14.815576 |
| EXIT21_STAGED_FRESHD | 10.542581 | 14.901960 |

Il vantaggio minimo di CAGR è 2.998302 punti; quello minimo di drawdown è 1.000815 punti. Il controllo verifica anche tutte le 162 righe della tabella di dominanza (nove protezioni × sei scenari × tre controlli).

La conclusione delle nove dominanze deve restare esplicitamente riferita allo scenario BASE. I conteggi per STATIC_75 negli altri scenari sono: BASE: 9/9, ZERO_COST: 9/9, DOUBLE_COST: 9/9, LAG1: 7/9, LAG2: 6/9, NEXT_CLOSE: 9/9.

## Grafico e altre tabelle

L’immagine OLC110_RISULTATI.png è stata esaminata visivamente. Le 13 etichette di CAGR e i 13 punti CAGR/perdita massima concordano con SCORECARD.csv nello scenario BASE. Le quattro curve di patrimonio terminano ai valori indicati in legenda; le quattro curve complete di drawdown concordano con una ricostruzione che include esplicitamente EUR 10.000 iniziali. L’omissione di un prefisso iniziale separato nel codice del grafico non cambia i valori: il primo nav_open è già EUR 10.000 in tutti e quattro i percorsi raffigurati.

| Curva | Patrimonio finale EUR | Drawdown campionato |
| --- | ---: | ---: |
| BASE | 46045.576847 | -37.920490% |
| STATIC_75 | 34653.972199 | -31.963091% |
| EXIT63_STAGED | 29297.466396 | -36.621643% |
| EXIT21_STAGED_FRESHW | 15319.165657 | -46.778667% |

Le direzioni degli assi sono corrette: a sinistra minore perdita massima, in alto maggiore CAGR. La scala del patrimonio è logaritmica ed è dichiarata. Tutti i valori rientrano nei limiti degli assi; non sono rilevate etichette numericamente errate o curve troncate. Lo scenario BASE e i costi sono indicati nel sottotitolo e nelle note.

Sono riconciliati anche i 13 prospetti di costo/attività, le 78 celle dei CAGR per scenario e le 91 celle annuali BASE, comprendenti il 2024. Le differenze fra percorsi con costi diversi sono correttamente descritte come differenze di conti completi, non come sottrazione lineare delle commissioni.

## Qualificazioni di lettura

- I nomi STATIC_75 e STATIC_HALF descrivono il target al ribilanciamento; i pesi effettivi possono variare fra due decisioni mensili.
- La descrizione breve TRAIL15 «Uscita da massimo precedente» va letta insieme alla definizione tecnica congelata: peak63 include il Close corrente. I valori verificati seguono quella definizione.
- La dominanza in due misure osservate non è una superiorità prospettica e non sostituisce il confronto fra costi, ritardi e annualità.

Nessun rilievo materiale richiede di correggere valori, bootstrap, confronti o grafico. Sono stati scritti soltanto ANALYSIS_REVIEW.json e questo documento. Gli hash dei file letti, il dettaglio numerico e i margini di confronto sono conservati nel JSON.
