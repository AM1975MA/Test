# OLC61 — Riprogettazione a monte: opportunità economica e persistenza

**Data:** 7 novembre 2026. **STATO: RICERCA / NON PROMUOVERE.** OLC19, selezioni operative e branch `main` invariati. Il protocollo dei tre modelli è stato congelato prima dell'esito. Nessuna ricerca di nuove fonti, nessun ricalcolo di CAGR di strategia. Le cifre esprimono la media aritmetica **per finestra** del portafoglio statico Top2 con pesi 50/50, non rendimento effettivo investibile.

## Decisione in sintesi

Con le stesse **42 feature originali OLC14**, sono stati addestrati **30 LightGBM LambdaRank** (EU/USA × anni 2021–2025 × tre obiettivi). I target sono calcolati dai margini economici relativi al mercato: **ECON21** premia il rendimento relativo nelle prime 21 sedute; **STAY2** esige un premio in entrambe le finestre disgiunte 0→21 e 21→42; **ECO_STAY** miscela 70% economia 0→21 e 30% persistenza. Gli score selezionano **direttamente** i migliori due ETF, senza fondersi con FUSION o ricorrere a un layer successivo.

**I tre modelli FALLISCONO il gate principale in entrambi i mercati.** Pur battendo talvolta il ranking nativo isolato su specifici indicatori, non battono il Top2 della **fusione originale**, il riferimento economicamente rilevante. Non eseguire replay con OLC19, non scegliere ex post un arm o un parametro.

## Prestazione Top2 sul periodo MAIN (48 mesi, 2021–2024)

| Metodo | EU r21 medio | EU r42 medio | EU persistenza Top20% su 21+42 | USA r21 medio | USA r42 medio | USA persistenza Top20% su 21+42 |
|---|---:|---:|---:|---:|---:|---:|
| B0_NATIVE, prima della fusione | +1,14% | +2,57% | 20,31% | +2,44% | +2,91% | 21,88% |
| **B0_FUSION_CONTEXT, controllo** | **+2,13%** | **+3,75%** | **33,33%** | **+3,50%** | **+3,90%** | 23,96% |
| ECON21 (valore 21d) | +1,17% | +2,05% | 23,96% | +1,64% | +2,61% | **29,17%** |
| STAY2 (margine persistente) | +0,93% | +2,65% | 20,83% | +0,28% | +0,80% | 17,71% |
| ECO_STAY (70/30 nel target) | +1,01% | +2,46% | 29,17% | +2,43% | +1,98% | 25,00% |

Le percentuali di persistenza sono **quote ponderate delle posizioni** che ex post appartengono al miglior quintile del rendimento sia a 21 che a 42 sedute, non probabilità calibrate del modello né rendimento annuo.

**Confronti appaiati con la FUSION originale su r21, punti percentuali per finestra:** ECON21: EU **−0,96 pp**, USA **−1,87 pp**; STAY2: EU **−1,20 pp**, USA **−3,22 pp**; ECO_STAY: EU **−1,12 pp**, USA **−1,07 pp**. Anche la media r42 è peggiore per tutte le sei combinazioni modello×mercato contro FUSION.

## Robustezza temporale e distribuzione dei mesi

La quota di mesi 2021–2024 in cui il challenger supera B0_FUSION in r21 è:

| Challenger | EU (su 48) | USA (su 48) |
|---|---:|---:|
| ECON21 | 17 | 18 |
| STAY2 | 18 | 12 |
| ECO_STAY | 19 | 16 |

Bootstrap circolare appaiato 6 mesi, 4.000 ripetizioni, IC 95% **descrittivi** per la differenza di r21 challenger−FUSION: EU ECON21 −0,96 pp [−2,34;+0,51], STAY2 −1,20 [−2,60;+0,27], ECO_STAY −1,12 [−2,79;+0,49]; USA ECON21 −1,87 [−4,50;+0,36], STAY2 −3,22 [−5,54;−0,70], ECO_STAY −1,07 [−3,43;+1,22]. I CI non correggono l'ampia ricerca storica precedente né la dipendenza fra ETF.

**2025, sola diagnostica post-hoc e NON holdout vergine:** STAY2 mostra r21 EU **2,18%** contro **1,50%** FUSION e USA **6,71%** contro **2,00%** FUSION; persistenza Top2 EU 29,17% contro 20,83%, USA 54,17% contro 33,33%. Queste osservazioni positive sono reali nello stesso dataset, ma non controbilanciano il fallimento su MAIN: non selezionare la strategia basandosi sul 2025 già esplorato. L'instabilità fra anni è una scoperta diagnostica, non un nuovo regime gate validato.

## Diagnostica: cosa è diverso dal ranking globale?

Nel 2021–2024, la qualità del ranking **sui primissimi due posti**, misurata con NDCG@2 calcolato ex post contro la relevance economica del primo intervallo, è:

| Metodo | EU NDCG@2 | USA NDCG@2 |
|---|---:|---:|
| B0_NATIVE | 0,530 | 0,537 |
| **B0_FUSION_CONTEXT** | **0,564** | **0,618** |
| ECON21 | 0,546 | 0,557 |
| STAY2 | 0,498 | 0,424 |
| ECO_STAY | 0,536 | 0,557 |

In contrasto, la correlazione media **Spearman IC sull'universo intero** con `g1_bp` è molto vicina a zero perfino per FUSION (EU circa +0,0002, USA +0,0041), mentre FUSION conserva il miglior Top2. Questo riconferma che il problema economico non si riduce al ranking di tutti gli ETF: **conta stimare bene la coda alta, l'entità dei payoff e la stabilità della coppia selezionata**. Non si può attribuire causalmente il vantaggio della fusione a una sola feature o trasformazione senza ablation native dedicate.

ECON21 USA predice un Top2 con *hit rate* su quintile 21d di **41,67%** contro 40,63% della FUSION, ma perde **1,87 punti** di r21 medio. È una distinzione decisiva: *prevedere correttamente l'appartenenza a un gruppo di winner non equivale a prevederne la magnitudine economica*. L'etichetta per 21d categorizzata in bande da −300 a +300 log-bp, scelta ex ante, può comprimere tail events: è un'ipotesi da sottoporre a un nuovo protocollo, non una giustificazione per ritoccarla ora.

## Integrità del test

- Sorgente binaria OLC14 Heads SHA256 `a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458`; Results SHA256 `4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1`. Schema identico delle 42 feature; nessun ticker ID.
- 30 modelli saved, 18.099 righe di forecast (9.159 EU, 8.940 USA). **Tutti** i gruppi di training hanno `exit_date_63` anteriore al 1° gennaio del proprio fit. Nessun label futuro come feature.
- Modelli salvati ricaricati e previsioni riprodotte esattamente. Rappresentazione degli score originali/Top2 verificata contro OLC60: **485 record selezionati** coincidenti su ticker/score; differenza massima di peso `5,55e-17` dovuta a float, nessun cambio di decisione.
- Verifica indipendente da pannelli: **600** aggregazioni mensili Top2 (2 mercati × 60 mesi × 5 metodi) ricostruite e identiche; controllo autonomo dei 48 mesi MAIN e della baseline OLC60; PASS (`results/OLC61_INDEPENDENT_QA.json`). 
- Durante la prima esecuzione la verifica di uguaglianza **bitwise** dei pesi da CSV ha bloccato il report per una differenza floating-point di `5,55e-17`, non per selezioni discordanti. Il guard è stato corretto a `1e-12` senza cambiare dati, target, modello o parametri; gli stessi modelli salvati sono stati ricaricati, non riottimizzati. Questo è documentato nel log. La QA finale è PASS.
- Software: Python con LightGBM 4.6.0, sklearn 1.8.0, numpy 2.3.5. I risultati OLC61 sono research only: **nessun replay con risk/V6/stop/fee e nessun CAGR**.

## Conseguenze e prossimo esperimento (da NON eseguire come retuning del lotto)

La nuova informazione ottenuta non è che «la persistenza non serve». È che anche un learner di *learning-to-rank* con tre target economicamente espliciti **non recupera** in modo coerente il vantaggio della fusione sulla coppia. Il risultato del 2025 mostra che la qualità relativa può invertire segno fra epoche, ma è improprio imparare un nuovo selettore di regime da un anno già analizzato.

**Priorità metodologica OLC62:** prima di un altro addestramento, verificare *quale informazione manca* nella rappresentazione 42-rank (confronto fra rank statico, velocità/accelerazione dei rank, turnover del Top10, breadth, coda della distribuzione e rischi di concentrarsi su categorie correlate), ricostruendo tutte le misure in modo puramente *as-of*. Usare un protocollo preregistrato che confronti opportunità economiche grandi e piccole, con una nuova finestra prospettica dopo il congelamento. Solo se emerge informazione effettivamente incrementale, valutare una rappresentazione temporale e un obiettivo multi-task su payoff immediato e secondo intervallo, prima della fusione. Niente layer finale e niente ricerca di parametri sui rendimenti 2021–2025.

## Pacchetto e riferimenti

Sorgenti, script, QA, tutte le 18.099 previsioni, Top2 selezioni e modelli fitted OLC61 vengono conservati insieme al presente rapporto. Gli archivi originali OLC14 da 364MB/40MB restano nelle cartelle di Library già esistenti, non vengono duplicati qui. Tutte le modifiche sono state sviluppate in branch di ricerca distinto da `main`.