# OLC15 — contesto di mercato e scelta della formula

2 novembre 2026. **Audit dei sorgenti e disegno dell'analisi, NON esperimento economico concluso.** CUM_FIT è registrata in `research/integration_candidates/CUM_FIT_OLC14.md` come candidata prioritaria, non promossa. Padre congelato OLC14: `6fcc215eeaa9834f5bcf8581e1fa6549a403f5b2`.

## Stato effettivo

Sono stati riletti il report OLC14, il codice `src/chrono_fit.py` e lo schema canonico Hybrid42. Nessun nuovo fit, indicatore temporale, correlazione regime-parametri, backtest o revisione di prezzi è stato calcolato. Gli strumenti locali di esecuzione hanno restituito ClientError prima dell'accesso ai file; non si dichiara perso l'archivio né svolto un test. GitHub è accessibile e conserva questa analisi. Nessun processo è stato lasciato in esecuzione.

## 1. Risposta alla domanda: i parametri dipendono dai trend?

È un'ipotesi economicamente plausibile, ma NON è stata verificata nel nostro campione. I cambi di beta/alpha annuali non bastano a dimostrarla.

Il codice OLC14 stima beta su score z, utilità u, date e identità del mercato per bilanciare le osservazioni. Seleziona alpha e penalità nelle ultime due finestre annuali interne ammissibili e rifitta sul passato maturo. Non riceve un vettore esplicito dello stato di mercato corrente. I coefficienti sono comuni a USA/EU e costanti nell'anno; cambiano comunque gli input z e quindi le scelte mensili. Il 2019–2020 è warm-up fisso; esistono sei fit annuali attivi 2021–2026, non 72 osservazioni indipendenti di parametri.

Correlare beta del primo gennaio con il rendimento dello stesso anno sarebbe ex post. La correlazione ammessa è con il contesto già noto al cutoff, ma sei vettori stimati sono troppo pochi per identificare in modo affidabile una funzione multivariata del regime. Replicarli sui mesi o sui ticker non aumenta le osservazioni indipendenti.

Beta può cambiare per trend, composizione del training, rumore, seed, scelta di regolarizzazione o collinearità delle tre previsioni. Se due teste ordinano quasi allo stesso modo, pesi diversi possono produrre scelte simili. Occorre valutare anche distribuzione dei coefficienti nei ricampionamenti del SOLO training, correlazione degli score, sovrapposizione Top2 e variazione del payoff; non interpretare ogni movimento dei pesi come cambiamento strutturale.

## 2. Un'opportunità informativa concreta

Lo schema canonico `vendor/etf_trader_v2/src/etf_trader/ma3/producer.py`, al commit `13443836649d0f107d2063eb7acc1039135d6e9b`, contiene 42 ingressi espressi come ranghi (incluse misure di cluster). Le nuove teste OLC14 conservano quello schema.

Un percentile della forza relativa conserva l'ordine ma elimina il livello comune della grandezza trasformata. Esempio matematico: rendimenti (-12,-8,-5)% e (2,6,9)% danno gli stessi tre ranghi. NON segue che l'intero vettore Hybrid sia identico nei due mercati o che il modello non contenga alcuna informazione indiretta di regime. Segue invece che livelli assoluti di trend, volatilità e ampiezza possono apportare contesto non duplicato dalla sola graduatoria.

La domanda utile diventa: dato il contesto noto oggi, quale combinazione aggiunge valore al selettore e alla fusione, rispetto alla combinazione di controllo? Non semplicemente: il mercato è rialzista?

## 3. Quale stato costruire

Separare quattro dimensioni prima di assegnare nomi come bull/bear:

| Dimensione | Informazione proposta, tutta disponibile alla chiusura del segnale | Domanda |
|---|---|---|
| Direzione | Trend 63/126 sedute e distanza dalla media lunga, su proxy comune o aggregato economico congelato | Il movimento comune sale o scende? |
| Persistenza | Efficienza del percorso a63: abs(sum(r))/sum(abs(r)); direzione mantenuta separatamente | È un movimento coerente oppure una sequenza di oscillazioni? |
| Stress | Volatilità21/126, livello storico della volatilità e drawdown corrente | Il rischio sta accelerando o rientrando? |
| Leadership | Stabilità delle graduatorie passate e quota di leader che persistono; ampiezza come controllo | Gli stessi gruppi continuano a guidare oppure ruotano? |

Le finestre sono proposte di partenza, non parametri ottimizzati o validati. Prima di un'esecuzione numerica, congelare esatti input, calendari, supporti, finestre e trattamento dei mancanti in un protocollo operativo. Evitare uno sweep indiscriminato delle finestre dopo i risultati.

Ampiezza: frazione di esposizioni sopra la propria media, non numero di prodotti quasi identici. Dispersione/correlazione possono essere diagnostiche aggiuntive, non tutte nuovi gradi di libertà del primo modello. La direzione di un mercato equity non rappresenta necessariamente bond, credito, commodity e FX presenti nello stesso catalogo. Mercato di quotazione non equivale a esposizione economica: usare proxy/categorie congelati e verificati, senza inventare equivalenze o identificazioni di copertura valutaria. Se la tassonomia non è verificata, dichiarare il limite e usare un controllo robusto a duplicazioni; non correggerla scegliendo gli ETF che hanno reso meglio.

Prima versione: stesso significato delle feature e stessa funzione per USA ed Europa; stato locale per ciascun universo, eventualmente affiancato da uno stato globale separato. Standardizzazione stimata solo sul training e contributo bilanciato dei mercati. Timestamp espliciti: la chiusura USA successiva a quella europea non è disponibile per una decisione europea precedente. Non assumere sincronismo da sole date prive di orario.

## 4. Non confondere stato osservato e futuro che si vuole prevedere

Un mercato può avere trend lungo positivo e breve negativo, oppure trend lungo negativo e breve positivo. Sono candidati a correzione/ripresa, non etichette certe di inversione. Il gate deve imparare se tale configurazione cambia il valore relativo delle formule; non assegnare a mano beta63 alto al bull e beta21 alto al bear.

Ipotesi da verificare: trend coerente e leadership persistente potrebbero rendere utile il lungo; rotazione rapida potrebbe aumentare l'utilità del breve; stress con alta correlazione potrebbe ridurre il vantaggio di qualsiasi selettore. Sono IPOTESI, non risultati né prescrizioni operative.

C63 resta un target cumulativo: dare più peso a63 non equivale a prevedere correttamente la continuazione21–63, né obbliga a detenere per63 sedute. Valutare separatamente esiti incrementali. In transizione occorre verificare anche la persistenza prevedibile dello stato; un regime attuale non è necessariamente quello che prevarrà nel prossimo trimestre.

## 5. La prima prova consigliata: condizionare la scelta fra formule esistenti

Non stimare subito una beta e una alpha completamente libere per ciascuno di molti regimi. Primo confronto: CUM_FIXED e CUM_FIT congelati come esperti, ORIGINAL come controllo esterno immutabile.

Per ciascuna data t, ottenere previsioni veramente fuori campione di entrambi gli esperti. La risposta nativa da analizzare è:

Delta_t = U(Top2(CUM_FIT)_t) - U(Top2(CUM_FIXED)_t).

Le U sono valutate sugli stessi candidati e diventano utilizzabili nel training solo quando TUTTI gli esiti del gruppo sono maturi. Non convertire un trade ancora aperto in un insuccesso. Delta è un beneficio differenziale, non il rendimento generale del mercato. Il rischio di scelta avversa resta una diagnostica e un vincolo separato.

Un gate piccolo e regolarizzato usa x_t per produrre un peso g_t in[0,1]:

S_i,t = (1-g_t) A_t(S_FIXED_i,t) + g_t A_t(S_FIT_i,t).

A_t porta gli score su una scala contemporanea comune senza usare esiti e mantenendo le graduatorie; preservare il controllo OLC14. g è un peso di miscela, NON automaticamente una probabilità calibrata di regime, né un peso di capitale. La miscela può selezionare ticker che nessuno dei due esperti sceglieva: simulare lo score e le posizioni realmente risultanti, non mediare a posteriori due curve del capitale.

La funzione che genera g ha gli stessi coefficienti nei due universi, ma gli stati locali possono produrre valori diversi. Non equivale a scegliere ex post una formula per Europa e un'altra per USA. Si può iniziare senza stati discreti: una funzione continua di pochi indicatori facilita l'attribuzione e riduce i cambi improvvisi. Annuale il fit della funzione, mensile l'applicazione al contesto aggiornato: separare aggiornamento dei parametri da frequenza di decisione. La frequenza finale va congelata prima del test.

Attenzione al warm-up: nel2019–2020 CUM_FIT=CUM_FIXED, quindi non esiste un contrasto informativo sul contributo del fitting. Queste date non costituiscono evidenza di skill del gate. Un fallback dichiarato mantiene la candidata/confronto prestabilito finché manca un campione sufficiente; mostrare separatamente il periodo davvero adattivo.

La prima versione NON modifica esposizione totale, stop, V6 o velocità di transizione. Uno stato di stress non diventa automaticamente un nuovo veto o una liquidazione: il rischio ha già un layer dedicato. Testare prima il contributo informativo, poi l'integrazione, infine eventuali modifiche del rischio in un lotto separato.

## 6. Solo dopo: parametri della curva condizionati al regime

Se il contesto aggiunge valore al confronto semplice, provare pesi dinamici con condivisione dell'informazione fra stati:

beta_t = (1-lambda) beta_base,y + lambda sum_r p_r,t beta_r,y.

Ogni beta_r è sul simplesso; p_r,t>=0 e somma p=1. lambda controlla quanto discostarsi dal riferimento globale. La shrinkage deve riportare al riferimento quando lo stato è poco rappresentato o incerto, senza chiamare tale peso una probabilità di successo. Nella prima estensione tenere alpha al valore annuale di riferimento: far cambiare contemporaneamente beta, alpha, memoria e rischio impedirebbe di attribuire il beneficio.

La miscela di beta non è in generale equivalente alla miscela di score con esponenti diversi. Il contratto deve dichiarare quale operazione viene eseguita e dove si applica la trasformazione di scala.

Con HMM/Markov/BOCPD, usare probabilità filtrate note al tempo t, non quelle smoothed con dati futuri. Anche il fit del modello di stato, lo scaler e l'identificazione dei regimi devono usare solo il passato: chiamare filtered un output di un modello stimato sull'intera storia non elimina la contaminazione. Allineare le etichette degli stati fra refit con criteri del training, non con performance futura. L'HMM è un'estensione, non un requisito della prima versione.

## 7. Come distinguere un effetto di regime da rumore

1. Audit input e disponibilità: recuperare parent/hashes, date, schema, prezzi e previsioni. Riprodurre CUM_FIXED/CUM_FIT e ORIGINAL senza scarti prima di modificarli.
2. Diagnostica: confronto di beta con contesto noto al rispettivo cutoff solo descrittivo; campione annuo insufficiente per concludere causalità. Studiare invece Delta mensile, concentrazione per episodio, collinearità delle teste e instabilità dei coefficienti nel training. Non contare coppie di ticker come nuovi anni indipendenti.
3. Attribuzione minima: controlli sempre-FIXED, sempre-FIT, miscela costante stimata con stesso budget, controllo basato soltanto sulla skill recente già maturata, gate che usa il contesto. Il gate deve aggiungere qualcosa oltre a una semplice diversa ponderazione o maggiore recenza.
4. Validazione annidata cronologica: tutte le decisioni sui parametri interne al passato; stesso cutoff temporale per i mercati; gruppi di label maturi, non gap in righe ticker. Nessuna scelta sul CAGR del periodo esterno. Mercati correlati e storia già studiata: non sono repliche indipendenti o un nuovo holdout vergine.
5. Controprove: perturbazioni dei dati futuri, stati ritardati, indicatori rimescolati a blocchi all'interno dei soli dati di training e controllo di frequenza dei cambi. Non far entrare nel modello dati futuri con una permutazione di tutta la storia; eventuali shuffle ex post sono diagnostiche placebo, non strategie causalmente realizzabili.
6. Risultati: DeltaU, eccessi21/42/63, continuazione, scelte avverse e opportunità perse separatamente USA/EU; poi CURRENT -> memoria -> fusione -> conto. Intervalli a blocchi con griglia comune dei mercati. Lo zero negli intervalli non è un veto automatico. Nessuna proclamazione da un miglioramento concentrato in un solo mercato o episodio.
7. Esecuzione/rischio: replay abbinati ai due costi, stress sugli input sistemici ritardati, turnover dovuto al gate, transizioni e peggiori episodi. I flussi V6 congelati sono un limite dell'attribuzione; una ricostruzione completa va dichiarata separatamente.

Prima di lanciare il test, fissare numero di input, finestre, complessità del gate, minimo di date realmente informative, calendario dei refit e grid di regolarizzazione. Questo documento è un disegno motivato; non pretende che tali dettagli non ancora verificati sui file siano già implementati.

## 8. Decisione attuale

Conservare CUM_FIT come candidata prioritaria. È giustificato studiare la dipendenza della sua utilità dal contesto, soprattutto perché il layer usa rappresentazioni relative e il beneficio cambia dopo la fusione. Non abbiamo ancora provato che i coefficienti dipendano dai trend, né addestrato un selettore di regimi. La scelta raccomandata è un gate piccolo fra formule esistenti, prima di una curva completamente dinamica o di molti modelli per stato.

## Fonti effettivamente lette

- OLC14 report consegnato `OLC14_Report_Fitting_20261101.md`, sezioni2–9; repository padre e `src/chrono_fit.py` al commit congelato sopra.
- Schema canonico Hybrid42: `vendor/etf_trader_v2/src/etf_trader/ma3/producer.py` al commit13443836649d0f107d2063eb7acc1039135d6e9b.
- Ang e Timmermann, Regime Changes and Financial Markets, NBER w17182: https://www.nber.org/papers/w17182 . Fondamento generale della plausibilità dei regimi, non validazione di CUM_FIT.
- Statsmodels, esempio Markov autoregression: https://www.statsmodels.org/v0.13.5/examples/notebooks/generated/markov_autoregression.html . Distinzione filtered/smoothed.
- Statsmodels, MarkovRegression.predict: https://www.statsmodels.org/stable/generated/statsmodels.tsa.regime_switching.markov_regression.MarkovRegression.predict.html . Documenta che il default delle probabilità è smoothed; non usarlo implicitamente in un replay causale.
- Scikit-learn, TimeSeriesSplit: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html . Per il nostro panel serve comunque splitting per date e disponibilità degli esiti, non una chiamata generica per riga.
- Cawley e Talbot, JMLR2010: https://www.jmlr.org/beta/papers/v11/cawley10a.html . Rischio di sovradattamento della selezione dei modelli.
