# OLC71 — Audit dell'informazione residua delle 125 feature Return

**Data:** 7 novembre 2026 · **Esito:** evidenza negativa per l'aggiunta indiscriminata delle 125 feature; criticità strutturali e un'anomalia 2025 da approfondire. **RESEARCH ONLY — NON PROMUOVERE.** OLC19, OLC67 e `main` invariati. Tutto lo storico 2019–2026 è già ripetutamente esplorato; nessuna finestra usata qui è un holdout indipendente.

## 1. Correzione della mappa concettuale

La pipeline originale **non riduce le 125 feature alle 42**. Sono due specialisti distinti:

- **Return125**: 125 ingressi nel ranker XGBoost del ramo Return, target di forza relativa/ranking. Il ramo è già addestrato su tutte e 125 le colonne.
- **Hybrid42**: 42 ingressi distinti, condivisi dagli esperti ET e XGB del ramo modellistico (39 unici più tre alias nella rappresentazione compatibile).
- I tre segnali RETURN, ET, XGB vengono normalizzati, integrati con memoria sul ramo modellistico e fusi nel ranking. In seguito il layer TOP2_CONTEXT_REVALUE può cambiare la coppia proposta, e V6/FAST_LOCK3 modifica contabilità e rischio.

L'ipotesi corretta è **informazione residua non sfruttata dagli score già disponibili**, non un insieme di 83 feature eliminate dalla rete a monte. I dati OLC08F e OLC14 confermano questa distinzione; OLC63/66 identificano le parti della fusione.

## 2. Fonti, finestre e controlli

Tre checkpoint immutati sono stati letti e confrontati per SHA256:

| Origine | SHA256 |
|---|---|
| OLC08F_01_FeaturePack_20261101.zip | `420faa56547721fd58db9f75ceef1370483047073d91c1b675587bd2d2e9db6c` |
| OLC14_Fitting_Risultati_20261101.zip | `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1` |
| OLC19_Rischio_Rientro_Checkpoint_20261102.zip | `3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540` |

Il risultato del ramo **FUSION autentico** è riprodotto come `0,475×RETURN + 0,525×ORIGINAL_SMOOTH`, entro 1e-12 sui record validi. Gli endpoint dei rendimenti futuri a 21 e 42 sedute corrispondono alle etichette indipendenti OLC14 entro 1e-10. Nessuna `source_date` successiva al segnale. Le finestre di addestramento richiedono gruppi interi con `exit_date_63 < 1 gennaio` dell'anno di previsione. **18.099 previsioni out-of-year**, 60 date 2021–2025 per mercato, 2021–2024 principale; 2025 soltanto diagnostico. Per simulare una decisione operativa servirebbe un replay completo TOP2_CONTEXT_REVALUE/V6/FAST_LOCK3, NON effettuato qui.

**Limitazione importante:** gli score FUSION originali sono disponibili da 2019, quindi per il test incrementale condizionale i nuovi correttori iniziano con soltanto 21 gruppi di training nel 2021. Questo non replica il training storico più lungo degli esperti Return. La condizione vale però allo stesso modo per il controllo e per tutti i suoi modelli arricchiti. Inoltre mancano una verifica completa dei prezzi USA osservati e un nuovo periodo non esplorato.

## 3. OLC71A — Informazione condizionale di tutte le 125 feature

Un modello di controllo impara il vantaggio economico relativo futuro a 21 sedute usando **RETURN, ORIGINAL_CURRENT, ORIGINAL_SMOOTH**, ossia le previsioni già disponibili. Una versione equivalente aggiunge le 125 feature. Entrambe usano lo stesso training expanding, lo stesso target e la stessa coorte. La versione lineare è `Ridge(alpha=100)` con imputazione/standardizzazione train-only; la non lineare è `HistGradientBoostingRegressor` con parametri congelati, 75 iterazioni e regolarizzazione elevata. Tre controlli Ridge rimescolano insieme le 125 feature fra ETF della stessa data in training e test.

**MAIN 2021–2024, errore RMSE sul rendimento relativo 21 sedute in basis point (minore è meglio):**

| Modello | Europa | USA |
|---|---:|---:|
| Solo tre score, Ridge | **311,32** | **488,73** |
| Tre score + 125 feature, Ridge | 351,40 | 521,79 |
| Solo tre score, non lineare | **311,07** | **490,95** |
| Tre score + 125 feature, non lineare | 326,94 | 494,07 |

Le differenze MSE del Ridge `CTRL−125` sono **−26.561 bp²** EU (CI95 bootstrap a blocchi sei mesi **[−41.251; −12.290]**) e **−33.400 bp²** USA (**[−52.486; −17.769]**). Il segno negativo indica che l'aggiunta peggiora l'errore. Il modello non lineare peggiora nel punto stimato in entrambi i mercati, ma il suo intervallo americano include zero. Tutti gli intervalli sono descrittivi e non corretti per i molti precedenti OLC.

I tre blocchi rimescolati peggiorano la MSE Ridge meno del blocco originale: l'aumento di dimensionalità è penalizzante, ma qui le 125 variabili autentiche **non forniscono un guadagno predittivo condizionale convincente**. L'originale FUSION NON riceve una RMSE: il suo score è un percentile adimensionale, non una stima calibrata in basis point.

**Payoff Top2 statico 21 sedute 2021–2024 (rendimenti medi per finestra, NON CAGR):**

| Metodo | Europa | USA |
|---|---:|---:|
| **FUSION originale** | **+2,13%** | **+3,50%** |
| Ridge tre score | +0,52% | +0,11% |
| Ridge tre score +125 | +0,64% | +1,47% |
| Modello non lineare tre score +125 | −0,73% | +0,41% |

Questo spiega perché una piccola riduzione dell'errore medio, anche se ci fosse, NON basterebbe: il sistema seleziona due ETF, non tutto il paniere medio. Non è stato ottenuto un CAGR di portafoglio.

## 4. OLC71B — Quali sottoinsiemi creano ridondanza?

Follow-up **dichiarato dopo OLC71A, ma prima di osservare gli esiti del follow-up**, a scopo diagnostico e non di selezione retrospettiva. Stessi training, Ridge e score; quattro blocchi fissati: RAW46, PCT46, DEV33, NO_LIQ119 (125 meno sei misure di liquidità/volume). Risultati MAIN:

| Feature aggiunte ai tre score | RMSE EU | RMSE USA |
|---|---:|---:|
| Nessuna: solo score | **311,32** | **488,73** |
| RAW46 | 329,67 | 508,81 |
| PCT46 | 326,67 | 500,03 |
| DEV33 | 337,27 | 501,46 |
| NO_LIQ119 | 350,55 | 520,79 |

**Tutti i gruppi aggiunti peggiorano l'errore** nel test incrementale lineare. Questo NON cancella il precedente risultato OLC08-F, nel quale riaddestrare il **ramo Return originale** con 119 variabili aveva mostrato alcune finestre favorevoli, soprattutto 2025–2026, ma peggiorato il MAIN USA. Sono esperimenti, target, training e contabilità differenti. Non si possono sovrapporre i risultati o attribuirli a un unico effetto.

## 5. Ridondanza effettiva e qualità delle feature

**125 colonne = 46 indicatori RAW, 46 percentili intra-mercato per data, 33 deviazioni robuste.** Nei dati 2021–2024, nei 4.391 accoppiamenti raw/percentile con almeno 15 valori, la correlazione di Spearman entro la data è **1,000**; le trasformate `_dev` hanno mediana 1,000 e media >0,9999 (lievi differenze per valori mancanti, clipping/ties). Sono quindi numerose rappresentazioni dello stesso *ordinamento* dei ticker, pur cambiando la scala, la distanza numerica e le interazioni possibili in un learner ad alberi.

In una PCA **soltanto descrittiva**, con standardizzazione entro ciascuna data e valori mancanti riempiti con la mediana *solo per questa diagnostica*, bastano circa **12 direzioni** per spiegare l'80% della varianza delle 125 colonne sia in EU sia negli USA; il rank effettivo da partecipazione spettrale è **8,31 EU** e **8,92 USA**. Questi NON sono conteggi di otto/nove segnali economici indipendenti né criteri per tagliare automaticamente a 12 input: misurano la forte concentrazione della rappresentazione numerica.

**Missingness materiale:** `downvol126` è mancante nel **87,86%** dei record europei 2024 e nell'**82,89%** degli USA 2024, nonostante il prezzo possa essere presente. `downvol63` è mancante circa nel 71,0% EU e 69,0% USA, `downvol21` circa nel 47,3% EU / 48,3% USA. Le rispettive versioni RAW/PCT/DEV trasmettono essenzialmente la stessa condizione di mancato dato. La causa, documentata nella ricerca precedente `compact21_downvol_cleanup_v1`, è una definizione downside condizionale che richiede almeno 10/31/63 sedute negative per finestre 21/63/126: assenza non equivale a volatilità zero. La variante di semideviazione a soglia zero era stata costruita e testata nel 2026-10, ma non aveva superato i gate di stabilità/qualità. Non ripetere la stessa correzione come se fosse una novità.

La tabella precedente `PRIOR_FEATURES_125.csv` ha minimo FDR_q **0,168**, nessun segnale con q<0,05 nella specifica analisi univariata archiviata. Non è un test di indipendenza condizionale.

## 6. Uso reale nell'originale XGBoost

L'archivio RSI03 contiene 24 modelli Return125 XGBoost **europei** per il periodo 2019–2026, tre seed per anno. Nel 2021–2024 ogni modello assegna guadagno da split a **tutte e 125** le feature. Quindi non sono 125 colonne ignorate dal codice. Quote medie del guadagno totale degli split 2021–2024: **34,5% RAW, 34,3% PCT, 31,1% DEV**. Il guadagno da split è una misura interna condizionata dalla collinearità, non un valore causale o una misura di alpha residuo. Gli archivi disponibili non includono gli equivalenti UBJ originali USA: non attribuiamo a quel mercato le percentuali EU.

Questa distinzione è centrale: **essere impiegata da un albero non garantisce che una feature abbia potere incrementale stabile dopo la FUSION**.

## 7. OLC71C — Audit specifico dei Top10, coerente con OLC65

Poiché OLC65 aveva attribuito oltre metà dell'oracolo teorico perso all'ordinamento nella shortlist, un ulteriore test diagnostico prende **sempre il Top10 autentico FUSION**, senza vedere il futuro, e riaddestra un correttore economico solo sui Top10 storici. Stessi cutoffs, Ridge alpha100, bracci: tre score, +PCT46, +125. Il protocollo Top10 era registrato dopo aver visto gli esiti OLC71A/B, ma prima degli esiti OLC71C.

| Top2 statico 21 sedute entro il Top10, 2021–2024 | Europa | USA |
|---|---:|---:|
| **Score FUSION originale, senza refit** | **+2,13%** | **+3,50%** |
| Correttore score-only | +0,40% | −0,73% |
| Correttore score+PCT46 | +0,96% | +0,27% |
| Correttore score+125 | +1,42% | +0,35% |

Le 125 migliorano il correttore score-only, ma **non battono FUSION**. L'intervallo descrittivo block6 per braccio +125 meno FUSION nel MAIN: EU **−0,71 pp** [−1,74; +0,45], USA **−3,15 pp** [−5,86; −0,42]. Gli output nel sottogruppo restano particolarmente rumorosi e la MSE del correttore +125 peggiora rispetto al controllo in entrambi i mercati.

Nel **2025 USA**, il Top2 del correttore +125 produce +7,35% per finestra contro +2,00% FUSION, ma la differenza si concentra in pochi mesi: gennaio, maggio e settembre spiegano **circa l'86,8% del vantaggio netto annuale**. Nel 2024 USA lo stesso correttore rende **−1,93%** contro **+4,85%** FUSION. Siamo di fronte a un'interazione storica non stabile fra rappresentazione e regime, non alla conferma di un vantaggio generale. Tutto il 2025 era già stato esplorato prima del protocollo.

## 8. OLC71D — Test *nativo* XGBoost Return europeo, senza riaddestrare

Questo ultimo approfondimento è stato **registrato dopo OLC71A/B/C ma prima di eseguirne gli esiti** (addendum GitHub OLC71D). È una verifica della sensibilità della FUSION originale alle 46 famiglie, non una prova di migliore alpha. Ho recuperato i **modelli Return125 originali EU**, non un correttore Ridge: per il 2021–2025 le previsioni con i tre modelli annuali riproducono **esattamente i ranghi Return e il punteggio FUSION archiviato in OLC19**, su tutte le date. Gli score grezzi differiscono al massimo di pochi punti nell'ottava cifra decimale per la precisione numerica di inferenza.

Per ciascun indicatore economico ho permutato congiuntamente le versioni RAW/PCT/DEV, **solo fra ticker nella stessa data**, per due repliche con seed fissati, poi ho ricalcolato XGBoost Return e FUSION con il ramo ET/XGB+memoria invariato. L'esperimento comprende **46 gruppi × 2 repliche × 60 mesi = 5.520** combinazioni mensili, con metriche verificabili e ricalcolo indipendente dei rendimenti dei Top2 (errore massimo 1,05e−16).

### Quali famiglie muovono davvero la FUSION?

| Gruppo di feature Return | % mesi 2021–24 con Top2 FUSION diverso dopo la permutazione | Δ payoff Top2 21 sedute originale−permutato, pp | Δ payoff 2025, pp |
|---|---:|---:|---:|
| `acc_mom_5_21` | 63,5% | +0,06 | −0,14 |
| `mom5` | 59,4% | +0,27 | −0,08 |
| `autocorr1_63` | 46,9% | +0,20 | ≈0,00 |
| `corr_mkt63` | 45,8% | +0,03 | −0,16 |
| `beta_mkt126` | 42,7% | +0,20 | −0,17 |
| `acc_mom_21_63` | 27,1% | **+0,45** | **−0,42** |
| `vol21` | 29,2% | +0,44 | +0,41 |
| `vol63` | 14,6% | −0,13 | +0,24 |

Valori medi sulle **due permutazioni**, sample di 48 mesi MAIN e 12 mesi 2025; l'esito `+` significa soltanto che *in questa perturbazione* rimuovere/rompere la relazione del blocco con il ticker ha peggiorato il Top2. Il segno `−` significa miglioramento ex post dopo permutazione. **Non equivale** a beneficio causalmente attribuibile né autorizza a rimuovere le famiglie negative.

Tutte e 46 le famiglie perturbate cambiano almeno una volta i Top2 nel 2021–24: la frequenza media delle modifiche di Top2 è circa **25,0%** delle decisioni mensili; il minimo per famiglia è **9,4%**, il massimo 63,5%. Dunque il ramo Return originale è effettivamente sensibile a tutta la rappresentazione, non ignora semplicemente i 125 campi.

**Diagnosi nuova:** alcuni blocchi che nel 2021–24 sembrano economicamente utili nel ranking FUSION diventano contrari nel 2025 (es. accelerazione 21→63). È una vulnerabilità coerente con la **non-stazionarietà dell'associazione fra feature e successi Top2**, ma una permutazione nel modello congelato NON prova che una regola dinamica possa anticipare questa inversione. Inoltre il dato 2025 è già stato esplorato; i 46 confronti multipli non consentono di promuovere le famiglie col miglior Δ storico. La permutazione può creare combinazioni di feature fuori dalla distribuzione di training, poiché lascia altri blocchi intatti, e non certifica la dipendenza causale del rendimento da una singola famiglia. Sono disponibili soltanto i modelli Return EU: nessuna inferenza nativa analoga è certificata per USA.

Questo distingue chiaramente le due domande: **le 125 feature sono usate? Sì, e modificano in modo significativo le scelte. Sappiamo estrarne un'informazione residua stabile rispetto alla FUSION? Non ancora.**

## 9. Decisione e prossimo esperimento metodologicamente corretto

**Non promuovere nessuna nuova combinazione e non calcolare un CAGR non simulato.** Gli score e la FUSION originali sono più efficienti nell'ordinare i Top2 dell'intero universo sul periodo principale. Gli schemi con 125 input espandono la rappresentazione ma introducono sovra-adattamento/dimensionalità, sparsità e un obiettivo economico diverso rispetto al ranker Return nativo. Non abbiamo dimostrato che il *contenuto informativo* della Return125 sia privo di residui: abbiamo falsificato diversi modi semplicistici di estrarlo.

**Passo seguente prioritario (progetto, non outcome realizzato):** OLC71D ha ora misurato la sensibilità del **learner Return125 europeo nativo** con permutazioni **a blocchi RAW/PCT/DEV** per tutte le **46 famiglie**, senza dimostrarne il valore predittivo causale. Servono quindi test di importanza **condizionale** che rispettino le dipendenze fra famiglie (anziché ricampionamenti potenzialmente fuori distribuzione), la replica con i **modelli originali USA**, e un confronto nel TOP2_CONTEXT_REVALUE autentico con validazione prospettica. Solo così si può separare la ridondanza delle rappresentazioni dalla loro reale informazione economica. In seguito, un solo refit **family-aware** del Return XGBoost con budget di campionamento equo per famiglia e controllo anti-leakage, prima del motore OLC19; niente griglia di pesi/timing o ottimizzazione sul 2025. Richiede i modelli nativi di entrambi i mercati e date fuori dal perimetro già esplorato per una prova di alpha credibile.

Una nuova selezione eventuale deve superare FUSION/CONTEXT autentici sul Top2, preservare l'anno 2024 USA e dimostrare performance più ampia di pochi mesi 2025, prima di essere sottoposta a replay OLC19. Nessun effetto riportato qui prova eseguibilità reale degli stop, prezzi delle aste o qualità della maschera USA.

## 10. Riproduzione

Vedere `README.md`. Codice: `run_olc71.py`, `run_family_diagnostics.py`, `run_top10_residual.py`, `feature_geometry.py`, `original_xgb_gain_audit.py`, `verify_olc71.py`, `run_native_family_permutation.py`, `verify_native_family_permutation.py`. Tutti gli output CSV/JSON, previsioni OOF e QA si trovano in `results/`. Per i gain europei occorre anche l'archivio separato `OLC08_03_RSI_Confronto_Verificato_20261101.zip` (riutilizza solo modelli originali, nessun training). Le tre sorgenti originali sono *richieste* per rieseguire gli esperimenti, ma non vengono incluse nel nuovo pacchetto per evitare duplicare centinaia di megabyte di checkpoint già salvati nella Library.