# Diagnosi post-PCA: direzioni conservate e scartate, senza nuovi fit

Richiesta16ottobre2026: verificare se il calo dopoPCA dipende da informazione discriminante nelle direzioni escluse. Analisi esplorativa formulata dopo il risultatoPCA95; non una conferma indipendente. Solo AM1975MA/Test,nessuna modifica produzione,nessun nuovo Yahoo. Nessun fit o nuovoCAGR in questa diagnosi.

Prima risposta verificata: PCA95 e stata seguita da30nuovi fit annuali, inizializzati a zero. Le43componenti conservate sono combinazioni delle125feature, non43colonne originali;82direzioni ortogonali sono state escluse. Varianza input e informazione sul rendimento futuro sono oggetti diversi.

Usare i coefficienti completi annuali gia archiviati w e la base conservata B di ciascun anno/download:
- w_conservato=B(B'w).
- w_scartato=w-w_conservato.
- score_completo=score_conservato+score_scartato suogni riga.

Confrontare quattro punteggi standalone Compact21: FULL_FROZEN, RETAINED_FROZEN, DISCARDED_FROZEN e PCA95_REFIT gia completato. Non riaddestrare e non rifare il replay di portafoglio. La coppia di proiezioni isola la rimozione a coefficienti congelati; il confronto conPCA95_REFIT mostra anche l'effetto del riadattamento. DISCARDED_FROZEN non e un modello allenato soltanto sulle direzioni escluse: i suoi coefficienti sono stati appresi congiuntamente agli altri. Eventuale test successivo: una sola variante rifittata sul complemento, da preregistrare prima dei fit, con stessi controlli e portafoglio completo.

Stessi30subtraining, mediane/scale originali, basi43 e hash di input/modelli/previsioni autenticati dai run38580178650 e38968119427. Verificare ricostruzioneesatta scorecompleto e parita inferenza diFULL/PCA95entro1e-12. Nessun apprendimento dalla validazione o dal futuro.

Quantificare: norma quadratica dei coefficienti nelle due parti (non percentuale di informazione); varianza input totale,entro-date e fra-medie delle date sulsubtraining; quota conservata in ciascuna; variabilita dello score entrodata e covarianza tra le due parti; correlazione dei ranghi con lo scorecompleto. La media fraETF non e un fattore mercato identificato e non dimostra causalita economica.

Qualita su113date mature fino2026-07-01: percentileTop1,NDCG5,RankIC,rendimentoTop1,peranno e media uniforme perdata, revisioni mediate entrodata. Blocchi calendariali6mesi primari e12sensibilita,3000bootstrap,seed20261016, intervalli95%descrittivi non corretti permolteplicita. Confronti retained-full,discarded-full,discarded-retained. Nessuna scelta di k,lag ocluster basata sul risultato. Non dedurre significativita confermativa daquesta analisi posthoc.

Interpretazione possibile: qualita relativa elevata del sottospazio scartato renderebbe plausibile che bassa varianza non equivalga a rumore. Per dimostrare autonomia e miglioramento economico servirebbe il successivo refit sul complemento e replay su tutti gli anni/tre download, seguito da verifica futura. Il divarioCAGR31.65->19.96% da solo non localizza l'informazione, poiche anche pesi,selezioni e percorso di esecuzione cambiano.
