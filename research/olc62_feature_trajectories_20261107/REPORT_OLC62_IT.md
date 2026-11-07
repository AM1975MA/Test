# OLC62 — Traiettorie delle 42 feature: test a monte e verifica della capacità Top2

**7 novembre 2026 — Esperimento completato e verificato.** Solo ricerca; **NO PROMOTION**. Nessuna modifica a OLC19, al branch `main`, agli ordini o al motore stop/rischio. Il protocollo è stato salvato e committato su un branch separato **prima** di calcolare gli outcome OLC62. Tutto il periodo fino al 2025 è già stato esplorato ripetutamente, quindi non è un nuovo holdout vergine.

## Risposta sintetica

Il nuovo modello `OLC62_TRAJECTORY42` usa i **42 ranghi originali** del progetto OLC14 e **84 differenze temporali**, cioè il cambiamento di ciascun rango rispetto a un mese e a tre mesi prima. Usa la stessa architettura LightGBM LambdaRank, gli stessi iperparametri e lo stesso target economico `ECON21` di OLC61. La nuova rappresentazione viene introdotta **prima del learner**, senza bonus finali, filtri, score FUSION come input o layer decisionali.

La media del rendimento dei Top2 a 21 sedute nel periodo principale 2021–2024 **peggiora** nettamente contro la fusione originale: EU **0,41% vs 2,13%**, USA **0,45% vs 3,50%**. Peggiora anche contro OLC61 `ECON21`, che usa le stesse 42 feature e il medesimo learner senza lags. Pertanto questo specifico aggiornamento di feature **non supera il gate di selezione**. Nessun replay di portafoglio o nuovo CAGR è giustificato.

## Risultato economico Top2, MAIN 2021–2024 (48 date per mercato)

Medie aritmetiche per finestra di posizione Top2 50/50, senza costi/stop/rotazioni. **Non sono CAGR né rendimenti negoziati.**

| Metodo | EU r21 medio | USA r21 medio | EU r42 medio | USA r42 medio | EU Top2 persistente | USA Top2 persistente |
|---|---:|---:|---:|---:|---:|---:|
| Fusione originale `B0_FUSION_CONTEXT` | **2,13%** | **3,50%** | **3,75%** | **3,90%** | **33,33%** | 23,96% |
| Ranking nativo originale `B0_NATIVE` | 1,14% | 2,44% | 2,57% | 2,91% | 20,31% | 21,88% |
| OLC61 `ECON21` | 1,17% | 1,64% | 2,05% | 2,61% | 23,96% | **29,17%** |
| **OLC62 `TRAJECTORY42`** | **0,41%** | **0,45%** | **1,29%** | **2,72%** | **21,88%** | **26,04%** |

Persistenza = quota di posizioni Top2 effettivamente nel quintile superiore di *entrambi* i rendimenti futuri 21 e 42 sedute, calcolata a posteriori. Non è una probabilità di previsione.

Differenze r21 OLC62 meno fusione originale: **EU −1,720 punti percentuali per finestra** (IC 95% bootstrap descrittivo 6 mesi **[−3,294;−0,120]**), **USA −3,050 pp** (IC **[−5,662;−0,580]**). Rispetto al solo modello statico OLC61 ECON21: EU −0,760 pp, USA −1,184 pp (IC di quest'ultimo confronto comprendono zero). Nessun intervallo è corretto per la lunga sequenza di esperimenti già svolti.

## Diagnostica delle traiettorie, senza nuove regole trading

Con correlazioni cross-sectional per mese tra cambiamento del rango e il reale vantaggio economico successivo `g1_bp` (Spearman, MAIN 48 eventi):

| Feature **variata rispetto a 1 mese prima** | IC medio EU | IC medio USA |
|---|---:|---:|
| `ret_21_rank` | +0,0026 | +0,0148 |
| `eff_63_rank` | +0,0082 | +0,0088 |
| `cluster_breadth63_rank` | −0,0775 | −0,0607 |

Variazioni a 3 mesi per `ret_21_rank`: EU −0,0544, USA −0,0032. Queste relazioni **descrittive e deboli** non certificano un segnale aggiuntivo trasferibile; molte feature possono essere ridondanti, e la predittività potrebbe essere non lineare/condizionata. Le correlazioni non vengono usate per scegliere retrospettivamente un filtro.

**Recupero della coda alta:** sullo stesso MAIN, la quota delle **due vere migliori opportunità future** (definite solo ex post) già incluse fra i primi dieci score è **36,46% EU e 30,21% USA** per la fusione originale. Con OLC62 è 33,33% EU e 30,21% USA. Questo è un *recall di posizioni* (96 future opportunità per mercato), non la quota dei mesi con almeno una opportunità intercettata, e non equivale a un rendimento tradabile. Il nuovo modello non migliora nemmeno il recupero iniziale dei migliori candidati.

## Il 2025 è diverso — ma non è convalida

Rendimento medio statico r21 nel **solo** 2025: EU OLC62 **3,91%** contro fusione **1,50%**; USA OLC62 **6,39%** contro fusione **2,00%**. Sono osservazioni nello storico già ricercato, quindi **non** sono un test fuori campione indipendente o una base per aggiungere un gate di regime. Risultati di anni precedenti peggiorano nettamente (specialmente 2022–2024). Scegliere 2025 dopo l'esito sarebbe selezione retrospettiva.

## Meccanismo, limiti e decisione

Non abbiamo falsificato la tesi generale che la persistenza sia utile; abbiamo falsificato **questa implementazione**: aggiungere 84 differenze di feature al medesimo ranking statico e target `ECON21` non migliora le opportunità Top2. L'esperimento non isola causalmente l'importanza delle singole feature; allargare da 42 a 126 dimensioni può favorire overfitting/ridondanza. Il confronto con la fusione originale è severo perché quest'ultima incorpora stadi ulteriori non rappresentati nello stesso learner. Non è lecito dedurre che la qualità della fusione dipenda necessariamente da uno stadio specifico.

Una ricerca futura sensata richiede prima una **decomposizione controllata dell'informazione economica già esistente** (quali head originali, orizzonti 21/42/63 e contributi di fusione/persistenza producono effettivamente i migliori Top2), senza inventare nuove soglie dai risultati. La priorità successiva è stabilire un piano di validazione su date prospettiche realmente non usate per scegliere il modello.

**Decisione: NO PROMOTION / non modificare OLC19.** Nessun nuovo CAGR, nessun nuovo layer finale, nessun risultato live.

## Verifica e riproducibilità

- Sorgente HEADS OLC14 SHA256 `a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458`. **42 snapshot feature + 84 differenze** per ETF.
- **10 fit** (2 mercati × 5 anni 2021–2025), etichette mature solo prima del cutoff annuale, nessuna identità ticker usata come feature del modello. Per i lags di fine/inizio anno sono impiegati anche gli XP disponibili dell'anno precedente **solo come storia, senza etichette**.
- **18.099 score** totali, supporto identico al file OLC61. Tutti i 10 modelli salvati e ricaricati riproducono le stesse previsioni entro 1e-10. Le feature coincidenti fra checkpoint annuali sono identiche (errore max 0).
- **480 eventi mensili** (2 mercati × 60 mesi × 4 metodi) e **965 record di posizioni** ricostruiti indipendentemente, con errore massimo della metrica in log-bp inferiore a 5e-13. Due fit per mercato, uno iniziale e uno finale, sono stati rigiocati dai checkpoint originali con un **secondo calcolo dei lag**, e le previsioni coincidono entro 2,3e-16.
- QA indipendente: `results/OLC62_INDEPENDENT_QA.json` (PASS). Protocollo preregistrato: `PROTOCOL_PRE_RESULTS.md`. Script: `run_olc62.py`, `verify_olc62_independent.py` e copia integrale immodificata del modulo OLC61 (`olc61_parent_unchanged.py`). Le due ZIP OLC14 grandi non sono duplicate nel pacchetto: restano nella Library utente.
- Criticità storiche irrisolte: source adjusted/raw PIT, listini delisted, quote osservate USA, dividendi, valuta, spread, fills, data mining multiplo 2019–2026. I rendimenti dei portafogli Top2 statici non riproducono OLC19 rischio/stop/commissioni.