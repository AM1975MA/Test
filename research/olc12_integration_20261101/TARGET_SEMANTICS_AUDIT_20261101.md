# Audit del target Hybrid: origine, significato e alternative

1 novembre 2026. Analisi richiesta dall'utente dopo OLC12. Nessun nuovo fit, backtest, cambio di formula produttiva o promozione. Questa nota registra verifiche dei sorgenti, deduzioni matematiche e un disegno sperimentale proposto, non eseguito.

## 1. Provenienza verificata e limite della ricostruzione

Fonti lette in AM1975MA/Test al commit congelato 13443836649d0f107d2063eb7acc1039135d6e9b:
- vendor/etf_trader_v2/config/ma3_highcagr24.json: specification_date 2026-09-23, target_power=1.5, target_weights rank21=.45, rank42=.35, rank63=.20. Configurazione legacy ExtraTrees, non l'attuale intero sistema.
- vendor/etf_trader_v2/src/etf_trader/ma3/producer.py: intestazione riferita alla correzione del 23 settembre; corrected_target applica la potenza a ciascun percentile PRIMA della somma.
- vendor/etf_trader_v2/config/ACTIVE_STRATEGY_SPEC.json: specifica 2026-09-26 che conserva lo stesso target nel producer Hybrid.
- vendor/etf_trader_v2/src/etf_trader/ma3/hybrid_producer.py: TARGET_POWER e TARGET_WEIGHTS sono costanti; la selezione documentata 60/40 riguarda la combinazione ET/XGB, NON dimostra che i pesi temporali .45/.35/.20 siano stati selezionati nello stesso modo.
- vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py, add_labels: rendimenti Open-to-Open a21/42/63 dalla stessa entrata, percentili per signal_date; target_multi_rank usa già .45/.35/.20 in forma lineare. y_tailmix è invece un diverso target .60/.25/.15 con potenza4: non va confuso con Hybrid.

La storia di questo percorso producer.py nel ramo congelato contiene l'importazione vendor del 1 ottobre 2026, commit19d8628b19899f0673d27d86ce4cc620d6e0d07d. È una data d'importazione, non la prova della prima invenzione della formula. Nei file e nella storia del percorso esaminati non è documentata una derivazione economica o una prova isolata che giustifichi precisamente .45/.35/.20 e1.5. Non si conclude che tale prova non esista in qualsiasi altro archivio: la sua origine decisionale non è stata ricostruita qui. La parola corrected è un nome storico, non una dimostrazione di ottimalità.

OLC11 mantiene questo Y per i regressori e definisce il classificatore dall'evento percentile(Y)>.8. Dunque il classificatore migliore impara meglio questa definizione di successo; ciò non dimostra che la definizione sia quella economicamente desiderata.

## 2. Che cosa misura

Y=sum_h w_h*r_h^alpha, h=21,42,63, w=(.45,.35,.20), alpha=1.5. r_h è il percentile realizzato del rendimento cumulativo all'orizzonteh. È una label relativa, non una feature disponibile oggi, non una probabilità, non un rendimento percentuale e non NDCG. Le metriche del learner valutano l'apprendimento di questa label, ma non ne giustificano il disegno.

Interpretazione possibile, non provenienza dimostrata: qualità relativa su più possibili orizzonti, priorità maggiore al breve e preferenza convessa per ranghi elevati. Formalmente si può interpretare Y come E[u(r_H)] per un orizzonte discreto H con masse .45/.35/.20 e u(r)=r^1.5. Non è stato dimostrato che le durate reali della strategia seguano quelle masse.

alpha controlla la curvatura nel RANGO, non lo sconto temporale. La derivata è1.5*sqrt(r). La trasformazione prima della somma può cambiare l'ordine degli ETF; applicare la potenza dopo la somma sarebbe una trasformazione monotona della stessa graduatoria delle label, anche se potrebbe ancora influenzare un regressore addestrato a errori quadratici.

Controesempio sintetico: A=(.6,.6,.6), B=(.9,.3,.45). Entrambi hanno rango medio ponderato .6. Y_A=.46475800154489, Y_B=.5021014396409949. La formula premia B, meno uniforme; non è quindi una misura pura di persistenza e non contiene una penalità esplicita per il deterioramento. È un esempio matematico, non un risultato sui prezzi.

I ranghi cancellano l'ampiezza monetaria dei divari: leader in mercato in calo non equivale a rendimento positivo. La trasformazione non può rispondere da sola a quanto capitale assegnare o quanto vale economicamente un vantaggio.

## 3. Sovrapposizione degli orizzonti

r21,r42,r63 sono costruiti su rendimenti cumulativi dalla stessa entrata, non su tre blocchi disgiunti. Una forte salita iniziale può lasciare alto anche il rango a42 e63, pur senza nuovi guadagni successivi. Questo è coerente con un obiettivo di buon risultato cumulativo a più scadenze; non dimostra prosecuzione del movimento.

Per rendimenti LOGARITMICI, ma non per ranghi/potenze, vale l'identità:
.45*L(0,21)+.35*L(0,42)+.20*L(0,63)
=1.00*L(0,21)+.55*L(21,42)+.20*L(42,63).
È un'analogia lineare esatta per quei rendimenti, NON una scomposizione esatta del targetY. Evidenzia che pesare endpoint cumulativi non è uguale a pesare incrementi di ricchezza.

## 4. Sconto esponenziale interpretabile

Proposta di confronto, non nuova baseline:
w_h(tau)=2^(-h/tau)/sum_{j in {21,42,63}}2^(-j/tau).
Y_exp=sum_h w_h(tau)*r_h^alpha.

tau è l'emivita in sedute: ogni tau sedute aggiuntive l'importanza non normalizzata dimezza. È una scelta esplicita di orizzonte/preferenza, non la prova che la prevedibilità economica decada così. Il decadimento del target FUTURO è distinto dalla memoria delle previsioni PASSATE .4/.3/.3 già presente nel sistema.

Pesi calcolati:
- tau21:57.1429%,28.5714%,14.2857%.
- tau42:45.3082%,32.0377%,22.6541%.
- tau63:41.2599%,32.7480%,25.9921%.

Gli originali45/35/20 sono già vicini a tau42, ma non sono esattamente esponenziali:35/45 !=20/35, equivalentemente .35^2 !=.45*.20. Perciò sostituirli può migliorare l'interpretabilità senza necessariamente cambiare molto l'informazione richiesta al modello. Non è ragione sufficiente per promettere maggiore CAGR.

## 5. Tre domande, tre possibili target

A. Qualità relativa cumulativa: Y_exp con alpha1 come controllo interpretabile, alpha1.5 come contrasto isolato. Si conserva la natura relativa e la compensazione fra scadenze.

B. Valore economico generato nel tempo: V_tau=sum_{d=1}^{63}2^(-(d-1)/tau)*ell_d, dove ell_d è il log-rendimento incrementale da prezzi coerenti, eventualmente in eccesso a un benchmark prestabilito. Ogni intervallo è contato una volta. È un punteggio di utilità scontata, non il rendimento composto di un conto; non misura automaticamente il drawdown. Dati total-return/FX/costi vanno definiti e verificati, non supposti certificati. Per conservare una metrica relativa si può calcolare il percentile di V_tau, perdendo però di nuovo l'ampiezza monetaria: tenere separato il canaleV.

C. Persistenza/valore residuo: mantenere tre target sui rendimenti dei blocchi0-21,21-42,42-63, oppure un evento congiunto di forza relativa sui blocchi successivi. Una congiunzione fra ranghi cumulativi può imporre coerenza di scadenza ma non elimina il problema del rialzo iniziale; per la prosecuzione reale occorrono blocchi incrementali. Un unico minimo o una penalità di variabilità cambiano la preferenza economica e richiedono un contratto separato, non un tuning per salvare un backtest.

Per il progetto la priorità proposta è distinguere individuazione dell'opportunità iniziale e vantaggio che continua a maturare. Non tutto deve essere compresso in una sola label.

## 6. Esperimento minimo proposto e non eseguito

Prima matrice2x2: pesi originali/esponenziali con tau42 e potenza1.5/1.0, stessa natura cumulativa dei ranghi. tau42 è una scelta interpretabile per questo controllo, non un optimum. Sensibilità prefissata21/63 solo se registrata prima dei nuovi esiti; non scegliere una durata diversa per mercato.

Poi confrontare target incrementale/persistenza come cambiamenti di domanda distinti, senza attribuire il beneficio al solo sconto. Congelare input, schema, modelli, seed, campioni e disponibilità dell'intero gruppo di etichette. Usare un controllo con maturazione63 abbinata anche per il target21, separando poi l'eventuale valore dei dati di training recenti. Cambi di scala della label/gradiente e di eventi positivi vanno documentati.

Il confronto non deve essere vinto da ciascun candidato sulla propria definizione modificata di migliori: mantenere endpoint comuni, payoff/excess Top2 a21/42/63, rendimenti dei blocchi successivi, scelte nel quintile peggiore, ampiezza degli errori, calibrazione degli eventi realmente uguali e stabilità per seed/periodo/mercato. NDCG o MSE su label diverse non sono direttamente graduatorie di superiorità. Solo dopo verificare la strategia completa con composizione/allocazione/rischio inizialmente invariati.

Ogni variante su USA149 ed EU165; nessun veto automatico per intervalli che attraversano zero; storia riutilizzata, dipendenza fra mercati e molteplicità restano esplicite. Nessun nuovo CAGR o risultato del modello viene dichiarato in questa nota.

## Riferimenti metodologici

- XGBoost3.1.3, Learning to Rank: https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/learning_to_rank.html (distinzione label di rilevanza, obiettivo e metrica).
- pandas2.2.3, Windowing operations: https://pandas.pydata.org/pandas-docs/version/2.2/user_guide/window.html (convenzione di emivita/decadimento esponenziale; non validazione finanziaria di un target futuro).

Il risultato concreto di questa fase è l'audit documentale/matematico. Nessun codice operativo è stato cambiato e nessun nuovo modello è stato addestrato.
