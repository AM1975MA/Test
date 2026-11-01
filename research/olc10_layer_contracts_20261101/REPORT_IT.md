# OLC-10 — migliorare il compito del layer, non scegliere dal solo CAGR

**1 novembre 2026. Lotto concluso. Integrazione nel ramo di ricerca, non in produzione. Nessuna modifica a main.**

## Risultato

Sono stati integrati i contratti verificati di RSI, schema canonico/alias, vista originale42 da39 colonne e salvataggi atomici con hash. Sono state rivalutate16 configurazioni archiviate sui compiti dei primi layer e addestrate24 piccole calibrazioni annuali, senza riaddestrare i learner originari e senza eseguire un nuovo backtest di portafoglio.

La decisione non dipende da un CAGR: un pacchetto può migliorare la stima media del target ma peggiorare la qualità dei primi due ETF. PATH a campionamento fisso è proprio un esempio. Le nuove calibrazioni migliorano alcune misure USA e peggiorano Europa; non vengono integrate come nuovi default. Il canale di ranking originale resta separato dalla stima del target, che NON è una probabilità.

## 1. Che cosa è effettivamente integrato

- RSI: convenzione già verificata per finestra matura senza perdite (100) e interamente piatta (50); aritmetica degli altri casi conservata. Non viene rivendicato un nuovo fit o nuovo beneficio RSI in questo lotto.
- Schema: ordine canonico esplicito, rifiuto di colonne inattese/mancanti, verifica degli alias.39colonne distinte possono ricostruire esattamente i42ingressi originali; non si riaddestra silenziosamente a39.
- Persistenza: marker completo scritto atomicamente soltanto dopo dimensioni/hash di tutti i file, rifiuto di checkpoint corrotti o incompleti.
- Interfacce: ranking relativo, previsione del target e rendimento di portafoglio sono oggetti separati. Un numero compreso tra0e1 non viene chiamato probabilità.

Sono identiche32matrici reali train/predict del contratto originale, oltre ai test sintetici di permutazione e alias. La composizione finale riproduce esattamente14850celle europee e13410americane archiviate, NaN compresi. Non sono stati toccati parametri di selezione, pesi, rischi, timing o costi.

Il modulo sperimentale è importabile da src/. L'integrazione non significa merge su main, certificazione dei dati o autorizzazione al trading.

## 2. Domanda e metrica di ciascun layer

|Layer|Domanda|Valutazione diretta|
|---|---|---|
|Dati e feature|L'informazione è quella dichiarata e disponibile alla decisione?|Dominio, timestamp, copertura, identità degli alias, riproducibilità|
|Return|Quali ETF offrono le maggiori opportunità economiche a21sedute?|NDCG@2/@5 sui gradi economici0..15 originali, payoff/rammarico Top2, errori sui perdenti|
|Hybrid come regressore|Quanto vale il target di persistenza relativa a21/42/63sedute?|MSE/MAE/bias rispetto alla media del training, peso uguale per mese|
|Hybrid come selettore|Quali ETF esprimono meglio quel target?|Qualità dei primi due, presenza nel quintile migliore/peggiore, payoff futuro statico|
|Media temporale|Conservare i segnali precedenti aiuta senza perdere le nuove opportunità?|Confronto current vs smoothed sul medesimo insieme di candidati|
|Fusione|Le due fonti si completano nelle scelte?|Top2 della fusione contro ciascuna fonte, a supporto identico|
|Allocazione/rischio/esecuzione|Come impiegare il capitale sulle idee?|Invariati e non riottimizzati in questo lotto; CAGR solo verifica successiva|

Il target Hybrid originale è precisamente

`Y = .45 * rank21**1.5 + .35 * rank42**1.5 + .20 * rank63**1.5`.

I rank sono percentili realizzati dell'ETF nel suo universo. È un target relativo, non un rendimento percentuale, né la probabilità di guadagno. Il suo MSE misura una previsione dell'intero target; NDCG e precisione Top2 verificano invece l'uso selettivo. La correlazione sull'intero universo non sostituisce la qualità della coda alta.

## 3. Rivalutazione di PATH sul compito del modello

Periodo principale: segnali2021–2024 con esiti completi maturati prima del2025. Stesso numero di colonne campionate, stesso seed101, righe e target uguali. Questi sono nuovi calcoli sui forecast già archiviati OLC09, NON nuovi addestramenti base.

|Metrica Hybrid|EU core39|EU core39+PATH6|USA core39|USA core39+PATH6|
|---|---:|---:|---:|---:|
|MSE del target, più basso migliore|0,066534|0,066500|0,068625|0,068540|
|Variazione relativa MSE del candidato|—|−0,052%|—|−0,123%|
|NDCG@2 sul target, più alto migliore|0,4900|0,4462|0,4591|0,4819|
|Quota delle due scelte nel quintile migliore del target|35,23%|27,27%|36,67%|37,78%|

Conclusione: PATH migliora di poco l'accuratezza media della stima nei due universi, ma peggiora la selezione dei primi due inEuropa. Non viene respinto perché aveva un CAGR inferiore; resta una pista sul target medio, non un selettore già migliore.

La controprova sul target, non sul CAGR, è ancora rilevante: a budget fisso tutti e tre i blocchi rimescolati USA hanno MSE inferiore al PATHautentico; inEuropa accade il contrario. I MSE null USA sono0,068526/0,068481/0,068506 contro0,068540 del blocco autentico. Non è dimostrato un contributo informativo comune robusto; tre estrazioni non sono un p-value calibrato. I controlli rimescolati NON sono strategie da adottare.

Il grafico OLC10_Qualita_Primi_Due.png è incluso nel pacchetto consegnato e nella Library; non si presume un asset binario GitHub non verificato.

## 4. Nuovi esperimenti: calibrare il target, non ottimizzare il capitale

Sono stati fissati prima degli esiti due piccoli modelli e un controllo:

**AFFINE:** retta a pendenza nonnegativa della previsione grezza .6ET+.4XGB verso il target vero, intercetta stimata, penalità0,1sulla varianza e pendenza limitata0..2.

**STACK2:** combinazione lineare nonnegativa dei due output grezzi, regolarizzata verso i pesi.6/.4. Può modificare l'ordine; resta un challenger.

**SHRINK50:** media al50%fra previsione grezza e media del target nel training annuale originale. È un controllo fisso, non scelto dal risultato.

Ogni gennaio i due modelli apprendono soltanto da previsioni annuali passate fuori campione i cui esiti63sono maturati prima del cutoff. Servono almeno18mesi: attivi2021–2026,6anni×2mercati×2calibratori=24fit. Le righe dello stesso mese dividono un peso totale costante.2019–2020rimangono warm-up, non un periodo di successo dei calibratori.

### Accuratezza pre2025

La tabella indica quanto il MSE è inferiore a quello della sola media del training. Più alto è meglio. NON è una percentuale di rendimento o di probabilità.

|Output|Europa|USA|
|---|---:|---:|
|Previsione Hybrid originale|1,380%|0,080%|
|AFFINE ricalibrata|0,803%|0,351%|
|STACK2 ricalibrata|0,806%|0,364%|
|SHRINK50|1,165%|0,487%|

La calibrazione migliora gliUSA ma peggioraEuropa nel periodo principale. STACK2riduce inoltre la precisione Top2 del target dal29,55%al25,00%inEuropa e dal35,00%al32,22%negliUSA. Non viene quindi integrata come nuova risposta comune del layer.

AFFINE e SHRINK50 mantengono per costruzione il canale ranking originale: hanno esattamente gli stessi NDCG, scelte attese e payoff statici di quel canale. La loro scala non viene sostituita furtivamente nella fusione o nel dimensionamento. Migliorare l'errore USA non significa aver individuato nuovi vincitori.

La media costante è conservata come controllo di perdita: può essere competitiva nel MSE, ma non sa ordinare i candidati. Nelle parità complete la qualità Top2 è calcolata come scelta uniforme attesa, non scegliendo retrospettivamente i ticker più fortunati.

I risultati2025e2026sono separati e mostrano ulteriori inversioni. Non vengono ritoccati parametri o finestre per salvare un candidato. La copertura europea2025è limitata: soltanto5mesi con tutte le etichette63complete prima di fineanno, contro9USA; non è il rendimento del2025e non rappresenta tutti i suoi segnali.

## 5. Che cosa aggiunge ogni passaggio alla selezione

Supporto contemporaneo identico per i quattro output, senza pesi/rischi/costi. Si comprano ipoteticamente i primi due al successivo Open osservato e si mantengono per l'orizzonte della label. Misura: rendimento medio aggiuntivo rispetto alla media dello stesso universo. **Punti percentuali per orizzonte, non CAGR; intervalli sovrapposti.**

|Output|EU21sedute|USA21sedute|EU63sedute|USA63sedute|
|---|---:|---:|---:|---:|
|Return isolato|+0,43|+1,75|+0,70|+1,22|
|Hybrid corrente|−0,14|+1,10|+1,52|+0,64|
|Hybrid con media temporale originale|+1,04|+1,05|+2,91|−1,34|
|Fusione originale|+1,29|+2,38|+2,57|+2,20|

Questo individua compiti e interazioni: la media temporale aiuta fortemente l'Europa ma non allo stesso modo gliUSA; la fusione migliora le scelte a21sedute rispetto ai singoli componenti in entrambi. Il layer Return ha correlazione globale negativa nel campione, ma Top2excess positivo: non va cancellato soltanto perché l'IC globale è debole. Per contro, una media temporale non va promossa per l'effetto su un solo universo.

La fusione non domina tutte le metriche: a63sedute Europa è inferiore al solo Hybrid smussato. Il risultato statico non include turnover, interruzioni, stop o il capitale effettivamente trasferito; non può essere sommato per promettere un CAGR.

## 6. Copertura, incertezza e limiti

Per le metriche principali di Hybrid sono richiesti tutti gli esiti del mese disponibili sul supporto predetto, evitando di eliminare singoli candidati usando la conoscenza del futuro. Restano44mesiEU e45USA pre2025. Per il payoff21sono46per mercato. I bootstrap abbinati usano44mesi di calendario comuni, non date di borsa esattamente identiche: fine maggio2021è il31inEuropa e il28negliUSA. La scelta di supporto completo spiega le differenze rispetto alle vecchie medie row-wise; non abbiamo modificato esiti.

La perdita di copertura ha una traccia: per esempio marzo–maggio2025EUhanno un'etichetta63mancante e non vengono usati nelle graduatorie completamente osservate. A settembre2024la maturazione europea63oltrepassa il cutoff2025. I segnali stessi rimangono disponibili: un'etichetta futura mancante non li elimina dalle decisioni.

Blocchi3/6mesi,6000estrazioni,seed20261101. Intervalli individuali e simultanei della famiglia in LAYER_PAIRED_UNCERTAINTY.csv. L'inclusione dello zero non è un veto; le frequenze bootstrap non sono probabilità posteriori. La storia è già usata in molte ricerche e USA/EUcondividono sottostanti; non sono repliche indipendenti. Nessuna selezione di un nuovo seed o feature dagli esiti di questo lotto.

## 7. Decisione di integrazione

**Integrato nel modulo di ricerca:** contratti verificati di input, RSI, alias, composizione esatta e checkpoint; registro domanda-output-metrica per7layer; diagnostica per obiettivi; distinzione ranking/expected-target.

**Non integrato come default:** PATH, STACK2, AFFINE,SHRINK50o ensemble come presunto miglioramento generale. Il riferimento numerico e la strategia originale rimangono intatti.

**Indicazione per gli esperimenti successivi:** migliorare la discriminazione delle opportunità alte e il valore residuo del segnale, senza confonderli con una piccola riduzione dell'errore medio. Si può conservare un miglioramento del regressore come tale, ma deve guadagnarsi separatamente il ruolo di selettore o allocatore. Non sono stati addestrati nuovi modelli tempo-evento, nuovi campionatori di gruppi o introdotti dati fondamentali in questo lotto.

## 8. Verifiche e problemi incontrati

26test del progetto superati.32matrici reali canoniche/legacy identiche;28260celle di score integrato identiche.334647label forward riconciliate con gliOpen osservati salvati, senza errori; non è una certificazione esterna dei prezzi.27191righe del target controllate con formula indipendente;1368MSEmensili e184riepiloghi ricontrollati;400NDCGconfrontati con implementazione sklearn. Sei perturbazioni di previsioni/label future lasciano invariati training e parametri passati. Errore numerico massimo3,33e−16nei controlli metrici.

Un primo runner è stato interrotto dal timeout ed è stato rieseguito completamente; nessun output parziale è usato come finale. Un adapter provvisorio usava il vecchio smoothing che propagavaNaN: la parità con la fonte corrente lo ha respinto. Ripristinata la rinormalizzazione già presente inCL01, con test rosso/verde. Il pairing statistico è stato corretto da date esatte a mesi di calendario, con test dedicato. Sono errori individuati durante lo sviluppo del nuovo audit, non nuovi difetti attribuiti alla vecchia strategia.

Ripristino pulito: tutti i CSV necessari inclusi,26test passati, pipeline e24calibrazioni rieseguite senza rete. Ranking e composizione identici; alcune stime calibrate2025/2026 differiscono soltanto alla precisione numerica (massimo2,22e−16). Il primo confronto bit-per-bit fallito è conservato; non viene dichiarata identità binaria di quelle stime. Le metriche e le conclusioni restano invariate alla precisione riportata.

Revisione dell'autore, non indipendente. Non è dichiarata verde tutta la suite del repository. Restano total-return/dividendi, universo sopravvivente, duplicati economici reali, spread e filllegacy; questo lotto non li certifica. Zero nuovi fit dei learner originali,zero nuovi backtest di portafoglio,zero ordini live.

## 9. Riproduzione e conservazione

Il pacchetto conserva i CSV di input necessari, previsioni archiviate, etichette,Open osservati, media training, parametri dei24calibratori, nuovi sorgenti e test. I grandi parent modello/cache sono identificati perhash, non inclusi nuovamente: ricostruire il training originale richiede quei parent. Il nuovo calcolo per layer è invece ripetibile dai CSV inclusi senza scaricare prezzi o riaddestrare gli alberi.

Comandi: `python -m pytest -q`, `python src/run_experiment.py`, `python src/diagnose_composition.py`, `python src/verify_results.py`, `python src/verify_labels.py`, `python src/uncertainty.py`.

GitHub: branch research/olc10-layer-contracts-20261101. Library persistente: /ETF_Research/OLC10_Contratti_Layer_20261101. I dieci moduli Python e la suite sono presenti in chiaro e byte-verificati nel commit e68551743163f224f483b6eec62fecf3621fc6bd. La presenza dei checkpoint nellaLibrary non equivale a upload dei binari suGitHub; lo storico arretrato rimane distinto. Main non modificato.

Riferimenti primari: documentazione scikit-learn sulle metriche, NDCG e calibrazione. Sono riferimenti metodologici, non evidenza di validità economica del tool. https://scikit-learn.org/stable/modules/model_evaluation.html e https://scikit-learn.org/stable/modules/calibration.html
