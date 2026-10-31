# Verifica USA / Europa a ogni incremento e decisioni sotto incertezza

31 ottobre 2026 — precisazioni vincolanti dell'utente alla proposta RH-50.

**Ogni step e ogni singolo miglioramento devono essere verificati su entrambi gli universi. Non basta validare in Europa la strategia finale o soltanto il vincitore selezionato negli USA.**

**Un intervallo di confidenza o di credibilità che comprende zero NON comporta esclusione automatica di una strada di ricerca, né equivale a dimostrazione di assenza di beneficio. Le decisioni devono considerare entità degli effetti, distribuzione dell'incertezza, probabilità interpretabili, danno possibile e utilità economica, non un solo verdetto di significatività.**

Questo addendum aggiorna i criteri di lavoro successivi e prevale sulle precedenti formulazioni della proposta RH-50 che possano far intendere un veto automatico basato sulla sola inclusione dello zero. Non modifica retroattivamente i protocolli congelati dei test già eseguiti o i loro risultati. Nessun codice operativo viene cambiato e nessun nuovo esperimento viene dichiarato eseguito con questo documento.

## Unità di avanzamento

Partire da una baseline identificata e riprodotta separatamente negli USA e in Europa. La versione e le regole strategiche sono comuni; dati, strumenti negoziabili e costi devono rispettare il contratto prestabilito di ciascun universo. Finché non esiste una baseline verificata su entrambi, il lavoro è qualificazione del riferimento, non promozione di miglioramenti.

Per ogni baseline B_k e modifica candidata delta:

B_k -> stessa modifica delta -> confronto appaiato USA + confronto appaiato Europa -> stima degli effetti e dell'incertezza -> decisione congiunta motivata -> eventuale B_(k+1).

**PASS_USA e PASS_EU indicano il soddisfacimento del contratto economico/probabilistico prestabilito nei due universi, NON due intervalli al 95% obbligatoriamente sopra zero.** Non si sommano i risultati dei due mercati per nascondere un danno materiale in uno. Dati mancanti o un test non eseguito non equivalgono a PASS.

## Ogni variante, non soltanto il finalista

Ogni candidato oggetto di valutazione o selezione deve essere verificato sui due universi. Non ottimizzare sugli USA, congelare il vincitore e presentare soltanto il suo successivo test europeo come applicazione di questo requisito. I confronti sui due universi devono entrare nella decisione fin dall'inizio.

Il vincolo copre aggiunta, rimozione e modifica di feature; target; learner e iperparametri; combinazione dei modelli; selettori; numero di posizioni; calibrazione e pesi; filtri di regime; esposizione; stop; altre protezioni; regole di esecuzione e trattamento dei costi. Comprende semplificazioni e modifiche apparentemente minori.

L'intervento deve essere esplicito e versionato. Mantenere invariato tutto ciò che non è oggetto del test. Quando due componenti devono essere valutati insieme per una precisa ipotesi d'interazione, dichiarare il fattoriale e i controlli prima dei risultati e ripeterli in entrambi gli universi, senza nascondere un pacchetto di cambiamenti sotto il nome di singolo miglioramento.

All'interno di ciascun universo, baseline e candidato devono usare gli stessi snapshot, eleggibilità, date confrontabili, costi e convenzioni di esecuzione salvo l'intervento dichiarato. Conservare i confronti appaiati e le incertezze temporali separatamente. Fra universi restano ammesse soltanto le differenze strutturali prestabilite di calendario, valuta, strumenti e costi. Un refit locale può produrre coefficienti diversi, ma la procedura e gli iperparametri non si ritoccano separatamente dopo gli esiti.

## Il criterio dipende dal compito del layer

Prima dell'esecuzione fissare metrica primaria, controlli, beneficio economicamente rilevante, danno materiale, costi di complessità, trattamento dell'incertezza e regola decisionale. Non introdurre soglie numeriche osservando chi vince. Non richiedere che ogni singolo indicatore cresca in entrambi i mercati: richiedere che il cambiamento soddisfi in entrambi il proprio contratto di miglioramento.

Per feature e selettori verificare qualità predittiva e delle scelte, cattura delle opportunità, regret e contributo economico incrementale, senza ridurre tutto a CAGR o hit-rate. Per allocatori verificare l'utilità netta del capitale assegnato, a selezione controllata. Per controlli di rischio verificare perdite e drawdown evitati insieme al costo delle opportunità eliminate e ai costi operativi. Un controllo difensivo può ridurre il CAGR entro il compromesso dichiarato; questo non lo rende automaticamente fallito. Costi, rischio e integrazione restano guardrail anche quando non sono la metrica primaria.

Ogni intervento destinato alla strategia deve inoltre essere verificato nel sistema integrato in entrambi gli universi prima di entrare nella baseline successiva. Le ablation di layer non sostituiscono il test delle interazioni a valle. Nessun componente viene promosso perché migliora soltanto il proprio indicatore isolato.

## Interpretazione delle distribuzioni: non confondere oggetti diversi

Un intervallo di confidenza frequentista non assegna direttamente una probabilità al valore vero dell'effetto. Il p-value non è la probabilità che il miglioramento esista e 1-p non è la probabilità di successo. La quota di ricampionamenti bootstrap positivi può essere documentata come stabilità empirica sotto il ricampionamento dichiarato, ma non viene rinominata automaticamente probabilità posteriore di alpha o probabilità di guadagno futuro.

Per affermazioni del tipo P(Delta > 0 | dati, modello), specificare un modello probabilistico appropriato, la prior, il significato di Delta e le assunzioni. Verificare sensibilità a prior e modello, diagnostica dell'inferenza e adeguatezza alle dipendenze temporali. Le probabilità sono condizionate a tali assunzioni; non sono certezze oggettive indipendenti dal modello. Le stesse osservazioni non possono diventare contemporaneamente una prior informativa e dati di aggiornamento senza gestire il doppio conteggio.

Distinguere la distribuzione dell'effetto medio incrementale dalla distribuzione predittiva del rendimento futuro. Un'alta probabilità che l'effetto medio sia positivo non implica la stessa probabilità di battere la baseline nel prossimo mese o anno; una previsione richiede un orizzonte esplicito e la variabilità futura, non soltanto l'incertezza della media.

I confronti frequentisti, il bootstrap temporale e gli intervalli esistenti restano utili. L'eventuale stima bayesiana è un'analisi aggiuntiva da dichiarare e verificare, non una conversione arbitraria degli estremi degli intervalli già pubblicati. Un approccio bayesiano non elimina automaticamente leakage, scelta retrospettiva dei modelli, test multipli o cambiamenti di regime.

## Scheda di evidenza per ogni incremento

Per ciascun universo riportare stima centrale, distribuzione/quantili dell'incertezza e unità dell'effetto; beneficio netto; rischio e costo delle opportunità perse; contributo nel layer e nel sistema integrato; sensibilità temporale, ai dati, ai costi e alle assunzioni. Quando il modello lo consente, aggiungere:

- P(Delta_US > 0 | D,M) e P(Delta_EU > 0 | D,M): probabilità condizionate di beneficio medio nel rispettivo compito.
- P(Delta_US > delta_US, Delta_EU > delta_EU | D,M): probabilità congiunta di un beneficio almeno economicamente rilevante in entrambi.
- P(Delta_US < -epsilon_US oppure Delta_EU < -epsilon_EU | D,M): probabilità di danno materiale in almeno un universo.
- Utilità incrementale attesa e gravità della coda sfavorevole, con costi e complessità inclusi una sola volta e secondo la funzione dichiarata.

D sono i dati e M il modello; delta e epsilon sono soglie di rilevanza e danno fissate prima del confronto, non percentuali inventate in questa specifica. Delta può essere un effetto sul criterio del layer; non è obbligatoriamente il CAGR. Un'unica utilità composita richiede pesi espliciti e guardrail separati: non nascondere il peggioramento di un mercato nella somma.

La probabilità congiunta non è ottenuta moltiplicando due probabilità marginali salvo indipendenza giustificata. Valutare dipendenza temporale e fra universi, eventuali sottostanti condivisi e numerosità effettiva; i panieri sovrapposti e le revisioni degli stessi prezzi non sono repliche indipendenti. Mostrare i risultati separati anche se si usa un modello congiunto. Non forzare una prior che imponga concordanza USA/Europa e poi presentarla come trasferibilità dimostrata.

## Decisioni: esplorazione, baseline di ricerca e impiego operativo

**Proseguire una strada di ricerca.** Un candidato può meritare nuovi test anche con un intervallo che comprende zero: pesano beneficio plausibile, danno possibile, motivazione tecnica, valore dell'informazione aggiuntiva e costo del test. Il confronto USA/Europa resta obbligatorio per ciascun nuovo incremento. La mancanza di significatività non è un fallimento sostanziale, ma nemmeno una prova che il beneficio esista.

**Adottare una baseline di ricerca.** La decisione può essere favorevole anche senza due intervalli al 95% interamente positivi, se la regola di utilità e rischio prestabilita è soddisfatta in entrambi gli universi e nel sistema integrato. Conservare la baseline precedente e tutte le alternative come controlli; etichettare l'incertezza e l'adozione come decisione di ricerca, non come beneficio dimostrato. Se le assunzioni cambiano facilmente la conclusione o il danno resta troppo incerto rispetto al contratto, mantenere il candidato in valutazione anziché promuoverlo. Non sostituire il vecchio automatismo p<0.05 con un nuovo automatismo P(Delta>0)>95% non giustificato economicamente.

**Accettazione operativa.** E' una decisione distinta, soggetta ai controlli di dati, causalità, eseguibilità, rischio e conferma previsti nella proposta. Continuare la ricerca o adottare provvisoriamente una baseline non autorizza operazioni reali o modifiche della strategia produttiva. Il requisito di verifica su entrambi gli universi non viene attenuato.

**Respinta o accantonamento.** Una strada può essere accantonata per danno materiale plausibile, utilità insufficiente rispetto ai costi, mancata trasferibilità, difetto tecnico o scarso valore informativo dei test ulteriori. Una stima puntuale leggermente negativa non equivale da sola a danno dimostrato; un intervallo contenente zero non è da solo motivo di esclusione. Un test mancante, dati non affidabili o risultati non riproducibili restano blocchi reali alla promozione, non semplici inconclusività statistiche.

Nessuna soglia di adozione o di probabilità viene scelta retrospettivamente per far passare RH-50 o un altro candidato già noto. La nuova regola è un aggiornamento prospettico della metodologia di ricerca; non converte i risultati passati in una validazione indipendente.

## Registro e risultati precedenti

Per ogni esperimento registrare ID, baseline, intervento, ipotesi, protocollo congelato, metriche per ciascun universo, differenze appaiate, incertezza, metodo e assunzioni, eventuali probabilità condizionate, verifiche integrate, costi/rischi e motivazione della decisione. Conservare i tentativi respinti e i risultati inconclusivi. Ogni ritaratura crea un nuovo esperimento da verificare su entrambi.

Non dichiarare fallito un esperimento soltanto perche' l'intervallo comprende zero. Le ipotesi accantonate esclusivamente per quel motivo possono essere riesaminate con la scheda completa, senza alterare gli esiti storici o scegliere ora prior e soglie favorevoli. I risultati che mostrano danno, errori o assenza di un beneficio economicamente utile non vengono automaticamente riabilitati.

Le correzioni obbligatorie di errori, leakage o formule non diventano facoltative perché riducono il rendimento storico: vanno controllate su entrambi, invalidano dove necessario il riferimento precedente e non possono ereditare le sue performance. Non si preserva un bug per ottenere PASS economico.

## Conseguenza per RH-50 e per la validazione futura

Return-Rank + Hybrid, esclusione del Ridge Tail e allocazione 50/50 restano ipotesi da qualificare individualmente e nelle interazioni su USA ed Europa. I risultati Original149 non costituiscono un'esenzione; RH-50 non è una baseline già accettata su entrambi. Gli intervalli che includono zero ne descrivono l'incertezza, non ne impongono l'abbandono.

Il test congiunto finale resta necessario e si aggiunge alla verifica incrementale di ogni step. Usare ripetutamente USA ed Europa per scegliere i miglioramenti rende entrambi universi di ricerca: conservare quindi validazione cronologica con selezione interna, controlli della molteplicità/ottimismo di selezione, tracciabilità di tutti i tentativi e verifica successiva con specifica e segnali congelati prima degli esiti. Non ripetere i test fino a ottenere la probabilità desiderata, né considerare i medesimi dati nuove prove indipendenti.

## Riferimenti metodologici

- Wasserstein e Lazar (2016), The ASA's Statement on p-Values: Context, Process, and Purpose, DOI 10.1080/00031305.2016.1154108. Le decisioni scientifiche ed economiche non devono dipendere soltanto dal superamento di una soglia di p-value.
- ASA President's Task Force (2021), Statement on Statistical Significance and Replicability. P-value, intervalli e altre misure restano strumenti utili se interpretati correttamente; nessuna singola misura esaurisce incertezza e rilevanza pratica.
- Kruschke (2021), Bayesian Analysis Reporting Guidelines, Nature Human Behaviour, DOI 10.1038/s41562-021-01177-7. Separare distribuzione posteriore e regola decisionale; dichiarare modello, prior, sensibilità, costi e benefici; distinguere stima da previsione.

**Stato di questa modifica: aggiornamento della metodologia e del criterio di accettazione. Nessun nuovo backtest, nessuna probabilità empirica/posteriore di RH-50 calcolata e nessuna promozione operativa.**
