# Opportunity su LINEAR annuale: due varianti separate

Autorizzazione utente: aggiungere entrambi i moduli Opportunity, risultati separati. Repository esclusivo AM1975MA/Test; nessuna modifica produzione. Branch research/linear-opportunity-20261014. Nessun nuovo dato Yahoo, nessun tuning di soglie o iperparametri.

Controllo: LINEAR_NUMERICAL_REPAIR annuale verificato, artifact listnet-linear-relative-repair run38580178650. Hash RESULT del fit 19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f. Tre download originali run37121749852, verifica byte hash INPUT_LINKAGE. Periodo2017-02-01–2026-07-01,114segnali disponibili e113periodi completi,2366osservazioni. Pannello MA3 autentico recuperato da learner-full-BASE-r1/r2/r3, run37195399755, con verifica hash e contratto originali. Tutti i modelli esistenti riusati, nessun refit Compact/Tail/Macro/MA3. Storico originale crescente. Nessun refit full-mature LINEAR in questo esperimento.

Deduplicazione: ispezionate descrizioni PR1–73, PR69/71 e ledger locali. Esistono precedenti esperimenti Opportunity su altre ricette e definizioni Stage19; non trovata variante LINEAR annuale con questi due moduli. Non ripetere i precedenti modelli/neural/history tests. Non rappresentare il risultato come replica esatta delle precedenti strategie500panieri.

## OPP_CAP

Funzione Stage19 esistente: cap=1-.25*clip((.80-scoreTop1)/.20,0,1); G2=min(g,cap). ScoreTop1 e score_matrix finale, determinato al segnale. Stessi Top1/Top2, confidence, V6, GALT=g, costi, stop, esecuzione. Nessun nuovo fit. Se non vincolante nel portafoglio149, riportare il risultato nullo senza cambiare soglie.

## OPP_ROUTER_CAUSAL

Ricostruzione raw delle feature e cluster del kernel storico; modelli Opportunity originali: ExtraTrees300 depth4 leaf30 seedyear; Ridge100 spread/excess; RF300 depth3 leaf30 balanced seedyear+1; stessa imputazione, standardizzazione e miscela di ranghi .35top2+.15spread+.35excess+.15explosive. Fit annuali strettamente con signal<cutoff e label_exit21<cutoff; 2017–2026. Cluster8 KMeans n_init20 e seed originali invariati; le identita numeriche dei cluster non sono persistenti nel tempo (limite preesistente).

Due correzioni causali esplicite, senza le quali non e valido attivare il codice storico:
1. Escludere `target_excess_max` e `target_excess_max_rank` dalla discovery per suffisso: restano120feature non-forward. Il difetto era gia registrato in history_window_v1.
2. Il router consuma solo shadow con exit_date<=signal_date corrente, almeno12periodi maturi, somma ultimi12log-differenziali DIRECT-controllo>0. Il codice storico consumava talvolta l'uscita all'open successiva al segnale: non consentito qui.

DIRECT aumenta a100% il peso Top1 dopo confidence quando il cluster del Top1 ha opp_z migliore e gap>=.50; altrimenti mantiene il peso canonico. Nessuna sostituzione ticker, V6 invariato. Il router applica DIRECT soltanto quando la condizione shadow e attiva. DIRECT shadow viene calcolato con lo stesso simulatore continuo canonico, costi e rischio, non con periodi riazzerati. E[k] valorizza open[k+1]; shadowperiodo include logincrementi entry_index:exit_index e diventa disponibile all'exit. DIRECT e solo diagnostica, non un terzo candidato da selezionare ex post. OPP_CAP non combinato col router.

## Verifiche e decisione

Parita OFF equity e turnover con archivio annuale assoluta1e-12 prima di accettare varianti. Fonti/input e previsioni archiviati con SHA. Test unita su maturita training/shadow, futuroshadowinvariance, esclusione target e convenzioneE[k]. Ricostruzione prefisso raw2022-12-30: uguaglianza esatta feature causali e cluster sulle date comuni; verifica input predittori invarianti rispetto a cambi target. Intero trainingOpportunity strettamente maturo. Salvataggio E/T/gross/altweight e decisioni router per attribuzione.

Riportare perogni variante/download CAGR,MaxDD,Sharpe,turnover,esposizione, rendimentiannui e media/range/SD CAGR. I segnali Top1/Top2 restano invariati per costruzione; non presentarlo come miglioramento della selezione. Tre download correlati, periodo giaesposto: nessuna validazione indipendente o promozione automatica.

Filtro di avanzamento ricerca: meanCAGR>=controllo, ogniCAGR>=95%controllo, meanMaxDD>=controllo, ogniMaxDD>=controllo-2pp, meanSharpe>=95%controllo, rangeCAGR<=controllo, con almeno un miglioramento numerico materiale(>1e-10). Riferire comunque tutti gli esiti e 2021/2023; non promuovere solo per CAGR medio. Nessuna modifica della ricetta sulla base dei risultati.
