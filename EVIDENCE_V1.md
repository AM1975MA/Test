# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1.

Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. protocollo e decision rule congelati prima dell'esecuzione;
5. nessuna ottimizzazione ex-post viene promossa.

**Regola operativa:** i test Evidence V1 leggono sorgenti e dati solo da `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato dipendente soltanto da artifact temporanei, download live o codice esterno al branch può essere promosso.

**Data gate:** ogni nuovo universo/ticker set deve essere congelato prima del test e verificato con quality checks + seconda fonte esterna per prezzi/corporate actions.

## VALIDATED / baseline verificata

### Hybrid24 / ETF_trader V2 canonico

- source-only / maturity-safe, byte-equivalente alla lineage produttiva storica;
- Original149: **31.60% CAGR**;
- Holdout70 disgiunto: **18.89% CAGR**;
- EW buy&hold ~10.35% vs ~10.62%: il gap non deriva da un Holdout70 passivamente peggiore.

Il baseline canonico non è un semplice Top1 cross-sectional: ricostruisce `BASE + ET_RANK + XGB_RANK`, combina `TAIL = 0.6*ET + 0.4*XGB`, applica smoothing `40/30/30`, power `1.10`, blend `47.5/52.5`, selezione basket, two-name allocation e layer di rischio HighCAGR24.

### Retriever LTR v1 — CONFERMATO come development evidence

XGBoost `rank:ndcg`, stesse 42 feature di Hybrid24 e configurazione frozen, annual expanding, maturity gate 63d, Original149.

114 periodi 21d:
- winner Top5: **32/114 = 28.07%** vs Hybrid24 **19.30%**;
- winner Top10: **47/114 = 41.23%** vs Hybrid24 **28.07%**;
- Top1 exact winner: **10/114 = 8.77%**;
- rank mediano winner: **13**;
- Top1 CAGR proxy: **22.06%**;
- IC medio: **0.006**.

Conclusione: **LTR migliora il retrieval top-k ma non è un selettore finale.**

Run `37040547189`; artifact `11241807171`; SHA256 `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead`.

### Checkpoint Retriever LTR v1 OOS — MATERIALIZZATO

Path:
`evidence_v1/checkpoints/retriever_ltr_v1/`

Copertura OOS: **2011-01-31 -> 2026-06-30**, **27,162** righe, **186** signal date. Validation 2017-2026: **114** periodi, **10** winner Top1, **32** winner Top5, **47** winner Top10.

Run `37047338155`; artifact `11244813213`; artifact SHA256 `2f1baed6984184e2123aa6df140c34882523b2eaf5a47a1874354e6dd5627f74`; checkpoint commit `6f966895d92773dadf8a5963ca7a848950c45504`.

### Universe Sensitivity v1 — CONFERMATO come validated diagnostic

Test preregistrato Original149 -> U120/U100/U70, con subset congelati prima del test e senza usare Holdout70.

Confronto:
- A: frozen LTR149 ristretto ai candidati;
- B: LTR riaddestrato sui candidati, feature/cluster calcolati sul reference universe Original149;
- C: LTR con feature/cluster ricalcolati nel candidate universe.

**Esito: PASS, 12/12 metriche di stabilità a favore di B.**

| Subset | Top1 agreement B/C | Top5 turnover B/C | Rank corr B/C | Rank MAE norm B/C |
|---|---:|---:|---:|---:|
| U120 | **42.11% / 31.58%** | **54.54% / 63.60%** | **0.891 / 0.868** | **0.098 / 0.108** |
| U100 | **40.35% / 23.68%** | **56.02% / 67.60%** | **0.877 / 0.786** | **0.106 / 0.142** |
| U70 | **30.70% / 27.19%** | **55.76% / 59.56%** | **0.764 / 0.731** | **0.147 / 0.159** |

Mean cluster ARI reference/native: **0.734 / 0.695 / 0.623**; mean feature drift: **0.0370 / 0.0424 / 0.0582**. Feature più sensibile: `cluster_eff_63_mean_rank`.

Conclusione: **la representation è universe-dependent; stable reference universe è supportata come scelta architetturale di representation, non come prova di alpha.**

Run `37055155515`; artifact `11248586812`; SHA256 `8ecabaeb80268929ab5f7610ca5848c9b265ebfab7e794a0f4ed2d8df177d58a`; result commit `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`.

## DIAGNOSTIC / BURNED

Original149 è ora un **development set fortemente burned**. I risultati sotto possono supportare o respingere ipotesi architetturali ma non costituiscono promotion evidence.

### Reranker v1 pairwise lineare — SCARTATO

- Top1 CAGR **22.06% -> 19.81%**;
- exact winner **8.77% -> 7.02%**;
- Top2 **13.16% -> 8.77%**.

Run `37041677418`; artifact `11242493662`.

### Reranker v2 nonlinear — SCARTATO

- Top1 **8.77% -> 7.02%**;
- Top2 **13.16% -> 9.65%**;
- Top3 **18.42% -> 14.04%**;
- CAGR diagnostico **22.06% -> 25.51%**, ma ranking gate fallito e 2023-2026 fortemente peggiore.

Run `37046279447`; artifact `11244841228`.

### Reranker v3 target-aligned 21d — SCARTATO

Stessa capacità del v2, target ordinale 21d e maturity `exit_date_21 < cutoff`.

- Top1 **10/114 -> 10/114**;
- Top2 **15/114 -> 14/114**;
- Top3 **21/114 -> 19/114**;
- CAGR **22.06% -> 18.77%**.

Run `37056519705`; artifact `11248488705`; result commit `5e57b61302ed76ac0c28756d519e74d019b82ea9`.

### Reranker v4 best-in-shortlist classifier — SCARTATO; LINEA CHIUSA

Target binario: un positivo + nove negativi nella frozen Top10; XGBClassifier shallow/regularized, singola configurazione preregistrata.

- global winner Top1 **10/114 -> 8/114**;
- Top2 **15/114 -> 12/114**;
- Top3 **21/114 -> 16/114**;
- CAGR **22.06% -> 14.16%**;
- sulle 47 date retrievable: Top1 condizionale **21.28% -> 17.02%**, Top2 **31.91% -> 25.53%**.

**Conseguenza vincolante:** deterministic reranker / learned single-winner head su Original149 **CHIUSO**. Nessun v5 e nessun tuning v4.

Run `37059193405`; artifact `11249798147`; SHA256 `1329862ae79af04b98aa5f26946a0be6fdbc9f210a000a1e31e0fb73b7ae32fe`; result commit `34f8f997ae1858a9007f6cc1809e6ad058855fca`.

### Allocation v1 LTR-EW5 — SCARTATA dal gate CAGR

Frozen LTR Top5, 20% per ETF, nessun training, nessun score sizing, nessun K sweep.

| Metrica | LTR Top1 | LTR-EW5 | Universe-EW |
|---|---:|---:|---:|
| CAGR | **22.06%** | **20.36%** | 9.92% |
| Ann. vol | 37.47% | **24.97%** | 12.72% |
| Sharpe rf0 | 0.714 | **0.869** | 0.810 |
| Max DD | -51.47% | **-31.94%** | -19.28% |
| Calmar | 0.429 | **0.637** | 0.514 |

Fallisce il criterio CAGR, pur mostrando forte beneficio di diversificazione. 2017-2022 Top1 **23.72%** vs EW5 **16.26%**; 2023-2026 Top1 **19.27%** vs EW5 **27.73%**. Il break temporale è diagnostico e non può diventare una regola hard-coded.

Run `37059734467`; artifact `11249119736`; result commit `0117b203d83d0a0af478c7778a7de07e5ee3cc5e`.

### Allocation v2 causal expert blend — SCARTATA

Due expert frozen (`LTR Top1`, `LTR-EW5`). A ogni signal date usa esclusivamente i 12 periodi precedenti già maturi (`exit_date_21 < signal_date`) e pesa gli expert in proporzione alla trailing compounded wealth. Nessun market regime, margin, leverage, hard switch o tuning.

Full 114:

| Metrica | Top1 | EW5 | Causal blend |
|---|---:|---:|---:|
| CAGR | **22.06%** | 20.36% | **21.93%** |
| Ann. vol | 37.47% | 24.97% | **30.26%** |
| Sharpe rf0 | 0.714 | 0.869 | **0.832** |
| Max DD | -51.47% | -31.94% | **-40.12%** |
| Calmar | 0.429 | 0.637 | **0.547** |

Il blend manca il CAGR Top1 di circa **0.14 pp**, quindi fallisce la regola preregistrata anche se migliora nettamente il rischio.

Diagnostica non-promozionale post-result: trailing relative wealth vs successivo `Top1-EW5` ha Spearman circa **-0.052**; il trailing leader anticipa l'expert vincente successivo solo **48.25%** delle volte. Non emerge skill adattiva utile. **Nessuno sweep di lookback/temperature/switch è consentito.**

Run `37060563323`; artifact `11249594252`; SHA256 `77a1914d46f9f32bb8d9cd27e42be9a0a289f71b8fcadd76ba894abbada8c134`; result commit `3fdcf97f92c5b23a3e49fc8bd71bf8813052efe8`; risultati in `evidence_v1/results/allocation_v2_causal_expert_blend/`.

### Hybrid24 OOS checkpoint — MATERIALIZZATO; ENGINEERING GATE PASS

Il segnale Hybrid24 canonico è stato ricostruito source-only da Original149 frozen e materializzato prima di qualsiasi test della cascata.

- MA3 rebuild: PASS;
- Titanium rebuild: PASS;
- annual fit maturity audit: PASS;
- cluster/source causality: PASS;
- historical scores/paths/cluster/basket artifacts consumed: **false**;
- canonical baskets generati da sorgente, seed `20260721`, SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`;
- checkpoint: `evidence_v1/checkpoints/hybrid24_oos_v1/`;
- `OOS_SCORES.csv` SHA256 `661feb2b9b80997e78e51b4701a2f4d9501b1ac390ceb331d59bec837b0db4f7`.

La precedente richiesta di parity a **31.60%** è stata corretta prima della Fase B perché confrontava statistiche non omogenee: il 31.60% è il replay V2 full-universe, mentre il runner di materializzazione riporta la media sui 500 basket canonici. Nessun dato della cascata è stato osservato durante questa correzione.

Run `37065765114`; artifact `11253020356`; artifact SHA256 `74fbeeb35eadeb625a86d5a1d15e6ad5d69a90a2c48223a3514be212918f5f18`.

### Cascade v1 LTR Top5 -> Hybrid24 — SCARTATA; EVIDENCE V1 CHIUSA

Protocollo singolo preregistrato: frozen `LTR Top5` -> selezione del candidato con massimo `HYBRID24_SCORE` canonico. Nessun training, nessun blend di score, nessun Top10 e nessun altro layer Hybrid24.

Full 114:

| Metrica | LTR Top1 | Hybrid24-only | Cascade Top5->Hybrid24 |
|---|---:|---:|---:|
| CAGR proxy | **22.06%** | 15.66% | **15.60%** |
| Ann. vol | 37.47% | **32.94%** | 37.65% |
| Sharpe rf0 | **0.714** | 0.605 | 0.569 |
| Max DD | -51.47% | -54.60% | **-46.60%** |
| Calmar | **0.429** | 0.287 | 0.335 |
| Exact global winner | **10/114** | 3/114 | **5/114** |

LTR Top5 conteneva il global winner **32/114 = 28.07%** delle volte, ma Hybrid24 lo seleziona dalla shortlist solo **5/32 = 15.63%** delle volte retrievable. La cascata coincide con LTR Top1 nel 35.09% dei periodi e con Hybrid24-only nel 42.98%.

Subperiodi diagnostici:
- 2017-2022 CAGR: LTR **23.72%**, Hybrid24-only **4.79%**, cascade **19.96%**;
- 2023-2026 CAGR: LTR **19.27%**, Hybrid24-only **36.99%**, cascade **8.49%**.

Il gate preregistrato fallisce nettamente: la cascata non batte il CAGR LTR Top1, non batte Hybrid24-only e riduce gli exact winner da 10 a 5 rispetto a LTR. Il risultato 2023-2026 di Hybrid24-only è diagnostico e non può essere trasformato in una regola temporale ex-post.

**Conseguenza vincolante:** nessun Top10, Top3, BASE-only, ET-only, XGB-only, blend alternativo o altro cascade tuning su Original149. Non si congela Holdout-B perché la development hypothesis non ha superato il gate.

Run `37067343776`; artifact `11252753465`; artifact SHA256 `d3526b8306797f917c34495d153083e69441e539b91d68f4db5cd9f9af75ca74`; result commit `a505666e61e25c8827fd66d6076fd175f2b6fe23`; risultati in `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/`.

**Holdout70 resta BURNED**: solo diagnostica/progettazione, mai promotion.

## CONCLUSIONI FINALI EVIDENCE V1

Le evidenze separano ora sei fatti:

1. **LTR retrieval è reale come development evidence**: Top5/Top10 recall del winner è superiore al ranking Hybrid24 usato come retriever.
2. **Stable-reference representation è supportata**: ranks/clusters sono più invarianti quando le feature restano ancorate a un reference universe stabile.
3. **Il problema è la conversione retrieval -> scelta finale**: quattro learned reranker, il classifier best-in-shortlist e la cascata con Hybrid24 non migliorano la selezione del winner.
4. **Top5 diversification migliora il rischio ma non il CAGR full-window**.
5. **Trailing relative expert performance non fornisce una meta-allocation causale utile**.
6. **Il segnale Hybrid24 non è complementare a LTR nel modo necessario**: dentro la shortlist Top5 peggiora materialmente CAGR e exact-winner rate rispetto a LTR Top1.

Quindi **Evidence V1 è CHIUSA**. Original149 è troppo burned per giustificare ulteriori varianti e il protocollo preregistrato impone di non trasformare i risultati osservati in nuovi parametri locali.

## NEXT TEST

**Nessun altro test è consentito dentro Evidence V1 su Original149.**

Un eventuale programma successivo deve essere una nuova linea (`Evidence V2`) con una nuova ipotesi esplicita, non una variante locale di K/layer/blend/reranker. La nuova ipotesi deve essere preregistrata prima di utilizzare un nuovo dataset di sviluppo o un nuovo Holdout; Holdout70 resta escluso dalla promotion.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Latest validated diagnostic result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`
- Latest deterministic reranker result commit: `34f8f997ae1858a9007f6cc1809e6ad058855fca`
- Latest allocation result commit: `3fdcf97f92c5b23a3e49fc8bd71bf8813052efe8`
- Hybrid24 OOS checkpoint run: `37065765114`; artifact `11253020356`
- Latest cascade result commit: `a505666e61e25c8827fd66d6076fd175f2b6fe23`
- Data: `evidence_v1/data/original149/`, `evidence_v1/data/holdout70/`
- Source baseline: `evidence_v1/source/baseline/`
- Original149 files: **151**; Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Environment: `evidence_v1/ENVIRONMENT.lock.txt`, `evidence_v1/requirements.lock.txt`
- Frozen-data provenance: `evidence_v1/PROVENANCE.json`
- Reusable LTR checkpoint: `evidence_v1/checkpoints/retriever_ltr_v1/`
- Reusable Hybrid24 checkpoint: `evidence_v1/checkpoints/hybrid24_oos_v1/`
- Frozen universe-sensitivity subsets: `evidence_v1/protocols/universe_sensitivity_v1/`
- Durable v4 results: `evidence_v1/results/reranker_v4_best_classifier/`
- Durable allocation v1: `evidence_v1/results/allocation_v1_ltr_ew5/`
- Durable allocation v2: `evidence_v1/results/allocation_v2_causal_expert_blend/`
- Durable cascade v1: `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/`
- Results/artifacts registry: `evidence_v1/RESULTS_REGISTRY.md`
