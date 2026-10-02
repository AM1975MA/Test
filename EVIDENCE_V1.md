# Evidence V1

## Regola di avanzamento

Questo file è la **source of truth** della linea Evidence V1. Prima di promuovere ogni nuova evidenza:
1. sorgenti eseguiti presenti nel repository e identificati da hash/commit;
2. dati ticker usati congelati nel repository e identificati da manifest/hash;
3. test causale/reproducibile con artifact e metriche;
4. questo file viene aggiornato: restano solo evidenze ancora valide; risultati smentiti/non comparabili vengono rimossi dallo stato corrente.

**Regola operativa:** i test Evidence V1 leggono sorgenti e dati solo da `evidence_v1/source/` e `evidence_v1/data/`. Nessun risultato dipendente solo da artifact temporanei, download live o codice esterno al branch può essere promosso.

**Data gate:** ogni nuovo download ticker va congelato prima del test e verificato con quality checks + seconda fonte esterna per prezzi/corporate actions.

## VALIDATED / baseline verificata

- Hybrid24 / ETF_trader V2 canonico, source byte-equivalente alla revisione produttiva storica.
- Full-universe, stessa vintage/motore:
  - Original149: **31.60% CAGR**
  - Holdout70 disgiunto: **18.89% CAGR**
- EW buy&hold ~10.35% vs ~10.62%: il gap non deriva da un Holdout70 passivamente peggiore.
- Hybrid24 ha segnale cross-sectional, ma il **top-tail** è molto meno affidabile del ranking medio.
- Il margin top1-top2 non è una confidence calibrata.
- Smoothing 40/30/30 e blend BASE/TAIL possono alzare IC medio ma peggiorare l'estremo tradato.
- BASE, ET e tail hanno informazione complementare; il blend fisso non è universe-invariant.

### Retriever LTR v1 — CONFERMATO come development evidence

XGBoost `rank:ndcg`, stessi 42 feature e hyperparameter XGB_B di Hybrid24 salvo l'obiettivo ranking; annual expanding, maturity gate 63d, Original149.

114 periodi 21d:
- winner nel top5: **28.07%** vs Hybrid24 **19.30%**;
- winner nel top10: **41.23%** vs Hybrid24 **28.07%**;
- rank mediano winner: **13**;
- top1 proxy: **22.06% CAGR**;
- IC medio: **0.006**.

Conclusione: **LTR migliora il retrieval top-k sacrificando ranking globale; non è ancora un selettore finale.**

Action `37040547189`; artifact `11241807171`; SHA256 `d139f0d31485dac1ae70c7b5fd7265887fac125626cb979e8054c18817496ead`; risultati in `evidence_v1/results/retriever_ltr_v1/`.

### Checkpoint Retriever LTR v1 OOS — MATERIALIZZATO

Il retriever non deve più essere riaddestrato per i test downstream già compatibili con questa versione. Il checkpoint riutilizzabile è in:

`evidence_v1/checkpoints/retriever_ltr_v1/`

Contiene prediction OOS, Top5, Top10, fit audit, config, validation, provenance e manifest con SHA256. Copertura OOS: **2011-01-31 → 2026-06-30**, **27,162** righe, **186** signal date. Il gate di materializzazione ha riprodotto prima del commit i conteggi certificati 2017-2026: **114** periodi, **10** winner Top1, **32** winner Top5, **47** winner Top10.

Action `37047338155`; artifact `11244813213`; artifact SHA256 `2f1baed6984184e2123aa6df140c34882523b2eaf5a47a1874354e6dd5627f74`; commit checkpoint `6f966895d92773dadf8a5963ca7a848950c45504`.

Regola downstream: join su `(signal_date, ticker)` al panel frozen e maturity gate indipendente prima di ogni fit.

### Universe Sensitivity v1 — CONFERMATO come validated diagnostic

Obiettivo: verificare se una representation calcolata su un **reference universe stabile** riduce l'instabilità del ranking quando cambia il candidate universe.

I sottouniversi `U120`, `U100`, `U70` sono stati congelati **prima del test**, in modo deterministico, bilanciato per macro-categoria e senza usare prezzi/performance. `Holdout70` non è stato usato.

Confronto preregistrato, sempre sul medesimo common support `(signal_date, ticker)` e con label candidate-relative identiche:
- **A / fixed anchor:** LTR v1 Original149 OOS congelato, semplicemente ristretto ai candidati;
- **B / reference:** stesso LTR v1 riaddestrato sui candidati, ma `FEATURES_42` e cluster calcolati nel reference universe Original149;
- **C / native:** stesso LTR v1, ma feature e cluster ricalcolati dentro il candidate universe.

Regola preregistrata: B deve avere Top5 turnover inferiore a C in **tutti** U120/U100/U70 e vincere almeno 3 delle 4 metriche di stabilità in ogni subset.

**Esito: PASS, 12/12 metriche a favore di B.**

| Subset | Top1 agreement B / C | Top5 turnover B / C | Rank corr B / C | Rank MAE norm B / C |
|---|---:|---:|---:|---:|
| U120 | **42.11% / 31.58%** | **54.54% / 63.60%** | **0.891 / 0.868** | **0.098 / 0.108** |
| U100 | **40.35% / 23.68%** | **56.02% / 67.60%** | **0.877 / 0.786** | **0.106 / 0.142** |
| U70 | **30.70% / 27.19%** | **55.76% / 59.56%** | **0.764 / 0.731** | **0.147 / 0.159** |

Conclusione causale: **la representation è materialmente universe-dependent e un reference universe stabile riduce la sensibilità del ranking alla contrazione del candidate universe.**

Diagnostica representation:
- mean Adjusted Rand Index cluster reference/native: **0.734 U120**, **0.695 U100**, **0.623 U70**;
- mean feature absolute drift: **0.0370 U120**, **0.0424 U100**, **0.0582 U70**;
- feature più sensibile in tutti i subset: **`cluster_eff_63_mean_rank`**;
- retention del full-reference sul common support: **99.47% U120**, **95.91% U100**, **69.01% U70**.

**Caveat:** il test dimostra stabilità, non alpha. Le metriche performance non migliorano in modo coerente con B, quindi B non viene promosso come selettore finale.

Run `37055155515`; artifact `11248586812`; SHA256 `8ecabaeb80268929ab5f7610ca5848c9b265ebfab7e794a0f4ed2d8df177d58a`; result commit `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`; risultati in `evidence_v1/results/universe_sensitivity_v1/`.

Audit tecnico: i run `37053782730` e `37054571788` sono invalidi come evidenza e sono documentati nel registry. Le correzioni erano strettamente tecniche e preregistrate prima del run valido.

## DIAGNOSTIC / BURNED

### Pairwise reranker v1 — SCARTATO

Top10 LTR OOS -> logistic pairwise L2 sulle differenze delle 42 feature + rank LTR; annual expanding solo su shortlist OOS mature.

114 periodi:
- LTR top1 proxy **22.06% CAGR** vs reranker **19.81%**;
- exact-winner **8.77% -> 7.02%**;
- winner nel Top2 **13.16% -> 8.77%**;
- margin Spearman **0.065**;
- forte instabilità temporale.

Action `37041677418`; artifact `11242493662`; SHA256 `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad`.

### Nonlinear reranker v2 — SCARTATO

Top10 LTR OOS -> XGBoost `rank:pairwise`, shallow/regularized, singola configurazione preregistrata, 42 feature + posizione LTR normalizzata; annual expanding e maturity gate 63d.

114 periodi:
- Top1 exact-winner **8.77% -> 7.02%**;
- Top2 **13.16% -> 9.65%**;
- Top3 **18.42% -> 14.04%**;
- CAGR proxy **22.06% -> 25.51%**, ma diagnostico e incapace di salvare il ranking gate;
- 2023-2026 fortemente peggiore.

Run valido `37046279447`; artifact `11244841228`; SHA256 `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4`.

### Reranker v3 target-aligned 21d — SCARTATO

Stessa capacità/config del v2 e stessa frozen LTR Top10, ma label ordinale futura 21d `9=best ... 0=worst` e maturity `exit_date_21 < cutoff`.

114 periodi:
- Top1 **10/114 -> 10/114**;
- Top2 **15/114 -> 14/114**;
- Top3 **21/114 -> 19/114**;
- CAGR proxy **22.06% -> 18.77%**.

2017-2022 e 2023-2026 mostrano trade-off opposti; il target 21d non risolve l'ordinamento del top-tail.

Run `37056519705`; artifact `11248488705`; SHA256 `e3f380b4e33e7b6b6b824d4a47a646af4c1b13afe670a87ef0abee67015d3855`; result commit `5e57b61302ed76ac0c28756d519e74d019b82ea9`.

### Reranker v4 best-in-shortlist classifier — SCARTATO; LINEA CHIUSA

Ultima famiglia deterministica consentita su Original149. Frozen Top10 OOS, stable-reference `FEATURES_42` + `LTR_POSITION`; target binario: una sola classe positiva per signal date, l'ETF con miglior `fwd_ret_21` nella shortlist; XGBClassifier shallow/regularized con `scale_pos_weight=9`, singola configurazione preregistrata.

114 periodi:
- exact global winner Top1: **10/114 -> 8/114**;
- global winner Top2: **15/114 -> 12/114**;
- global winner Top3: **21/114 -> 16/114**;
- CAGR proxy: **22.06% -> 14.16%**;
- sulle 47 date in cui il global winner era effettivamente retrievable nella Top10: Top1 condizionale **21.28% -> 17.02%**, Top2 **31.91% -> 25.53%**.

Il v4 migliora marginalmente alcune metriche di `shortlist-best`, ma peggiora il compito economico primario e fallisce nettamente la regola preregistrata.

**Conseguenza vincolante:** la linea dei deterministic reranker su Original149 è **CHIUSA**. Nessun v5, nessun tuning v4, nessun altro head costruito per scegliere un singolo winner sul development set.

Run `37059193405`; artifact `11249798147`; SHA256 `1329862ae79af04b98aa5f26946a0be6fdbc9f210a000a1e31e0fb73b7ae32fe`; result commit `34f8f997ae1858a9007f6cc1809e6ad058855fca`; risultati in `evidence_v1/results/reranker_v4_best_classifier/`.

### Allocation v1 LTR-EW5 — SCARTATA dal gate CAGR, ma rischio migliorato

Prima ipotesi portfolio-level dopo la chiusura reranker. Frozen LTR Top5, 20% per ETF, nessun uso di score margin, nessun tuning K, nessun training.

Full 114:

| Metrica | LTR Top1 | LTR-EW5 | Universe-EW |
|---|---:|---:|---:|
| CAGR | **22.06%** | **20.36%** | 9.92% |
| Ann. vol | 37.47% | **24.97%** | 12.72% |
| Sharpe rf0 | 0.714 | **0.869** | 0.810 |
| Max DD | -51.47% | **-31.94%** | -19.28% |
| Calmar | 0.429 | **0.637** | 0.514 |

La regola preregistrata richiedeva che EW5 battesse Top1 in CAGR, non peggiorasse il drawdown e battesse universe-EW. **Fallisce solo il primo criterio:** 20.36% < 22.06%. Quindi EW5 semplice non avanza e non si prova ex-post Top3/Top10.

Diagnostica temporale:
- 2017-2022: Top1 **23.72% CAGR** vs EW5 **16.26%**;
- 2023-2026: Top1 **19.27%** vs EW5 **27.73%**, con EW5 vol 24.07%, max DD -18.21%, Sharpe 1.142 e Calmar 1.523.

Questa inversione **non** autorizza una regola hard-coded sul 2023. È solo evidenza che il trade-off concentrazione/diversificazione è non-stazionario e merita, se proseguito, una regola causale basata esclusivamente su risultati già maturi.

Run `37059734467`; artifact `11249119736`; SHA256 `3c1a3b4522f1149b8e00336838eb00c38acd7e3f0343b0e1ed157b6a2e14b7ba`; result commit `0117b203d83d0a0af478c7778a7de07e5ee3cc5e`; risultati in `evidence_v1/results/allocation_v1_ltr_ew5/`.

**Holdout70 resta BURNED**: solo diagnostica/progettazione, mai promotion.

## HYPOTHESIS corrente

Le evidenze ora separano quattro fatti:

1. **Retrieval supportato:** LTR v1 porta il winner nella Top5/Top10 molto più spesso di Hybrid24.
2. **Representation supportata:** una stable reference universe rende ranking/cluster materialmente più invarianti al candidate set.
3. **Single-winner head non supportato:** quattro famiglie preregistrate di reranker/decision head hanno fallito. Questa linea è chiusa.
4. **Diversificazione Top5:** EW5 sacrifica ~1.70 pp di CAGR full-window ma migliora fortemente vol, max DD, Sharpe e Calmar; inoltre la competenza relativa Top1/EW5 cambia nel tempo.

Architettura ancora plausibile:

`stable reference representation -> frozen LTR top-k retrieval -> causal portfolio-of-experts allocation -> eventuale risk sizing -> Holdout-B promotion`

La prossima ipotesi non deve usare market regime labels, score margin o una data di break osservata ex-post. Deve imparare solo dalla **competenza relativa già maturata** dei due expert frozen (`Top1`, `EW5`).

Vincoli:
- Original149 = development set fortemente burned; nessun risultato qui è promotion evidence;
- nessun K sweep;
- nessun ritorno ai deterministic reranker;
- maturity gate esplicito anche per i rendimenti degli expert;
- Holdout70 burned;
- nuovo Holdout-B congelato prima di ogni promotion;
- nessuna ottimizzazione ex-post promossa.

## NEXT TEST

1. Preregistrare **Allocation v2 causal expert blend** con soli due expert frozen: `LTR Top1` e `LTR-EW5`.
2. Una sola regola, senza sweep: per ogni signal date calcolare per ciascun expert la ricchezza composta sui **12 più recenti periodi già maturi** (`exit_date_21 < current signal_date`); peso dell'expert = sua trailing wealth / somma delle due trailing wealth. Nessun hard switch, nessun leverage, pesi sommano a 1.
3. Usare anche la storia OOS frozen pre-2017 (checkpoint dal 2011) per inizializzare causalmente il trailing window; se non esistono 12 periodi maturi, usare 50/50 solo come bootstrap.
4. Primary gate full 114: `CAGR(meta) > CAGR(frozen Top1)` e `MaxDD(meta) >= MaxDD(frozen Top1)`. EW5 e universe-EW restano comparatori diagnostici; sottoperiodi non possono cambiare il verdetto.
5. Se Allocation v2 passa, **non** fare tuning sul 149: congelare un nuovo Holdout-B disgiunto prima di ogni test di promotion.
6. Se Allocation v2 fallisce, non provare altri lookback/temperature/switch ex-post: fermare la linea adattiva e riesaminare l'architettura prima di qualunque nuovo test.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Latest validated diagnostic result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`
- Latest deterministic reranker result commit: `34f8f997ae1858a9007f6cc1809e6ad058855fca`
- Latest allocation result commit: `0117b203d83d0a0af478c7778a7de07e5ee3cc5e`
- Data: `evidence_v1/data/original149/`, `evidence_v1/data/holdout70/`
- Source baseline: `evidence_v1/source/baseline/`
- Original149 files: **151**; Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Environment: `evidence_v1/ENVIRONMENT.lock.txt`, `evidence_v1/requirements.lock.txt`
- Frozen-data provenance: `evidence_v1/PROVENANCE.json`
- Reusable LTR checkpoint: `evidence_v1/checkpoints/retriever_ltr_v1/`
- Frozen universe-sensitivity subsets: `evidence_v1/protocols/universe_sensitivity_v1/`
- Durable v4 results: `evidence_v1/results/reranker_v4_best_classifier/`
- Durable allocation v1 results: `evidence_v1/results/allocation_v1_ltr_ew5/`
- Results/artifacts registry: `evidence_v1/RESULTS_REGISTRY.md`
