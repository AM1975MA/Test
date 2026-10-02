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

2017-2026, 114 periodi per subset:

| Subset | Top1 agreement B / C | Top5 turnover B / C | Rank corr B / C | Rank MAE norm B / C |
|---|---:|---:|---:|---:|
| U120 | **42.11% / 31.58%** | **54.54% / 63.60%** | **0.891 / 0.868** | **0.098 / 0.108** |
| U100 | **40.35% / 23.68%** | **56.02% / 67.60%** | **0.877 / 0.786** | **0.106 / 0.142** |
| U70 | **30.70% / 27.19%** | **55.76% / 59.56%** | **0.764 / 0.731** | **0.147 / 0.159** |

Conclusione causale del test: **la representation è materialmente universe-dependent e un reference universe stabile riduce la sensibilità del ranking alla contrazione del candidate universe.** La regola preregistrata restituisce `SUPPORT_REFERENCE_UNIVERSE`.

Diagnostica representation:
- mean Adjusted Rand Index cluster reference/native: **0.734 U120**, **0.695 U100**, **0.623 U70**;
- il cluster drift cresce quindi al ridursi dell'universo;
- mean feature absolute drift: **0.0370 U120**, **0.0424 U100**, **0.0582 U70**;
- feature più sensibile in tutti i subset: **`cluster_eff_63_mean_rank`**;
- il preprocessing nativo perde anche supporto storico al ridursi dell'universo: retention del full-reference sul common support **99.47% U120**, **95.91% U100**, **69.01% U70**; restano comunque tutte le **114** date di valutazione.

**Caveat fondamentale:** questo test dimostra stabilità, non alpha. Le metriche performance erano preregistrate come diagnostiche e non migliorano in modo coerente con B. Per esempio il Top1 exact-winner B/C è 7.02%/8.77% su U120, 8.77%/9.65% su U100 e 4.39%/7.02% su U70. Quindi **B non viene promosso come selettore finale**.

Run valido `37055155515`; artifact `11248586812`; artifact SHA256 `8ecabaeb80268929ab5f7610ca5848c9b265ebfab7e794a0f4ed2d8df177d58a`; result commit `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`; risultati in `evidence_v1/results/universe_sensitivity_v1/`.

Audit tecnico: i run `37053782730` e `37054571788` sono **INVALIDI COME EVIDENZA**. Il primo si è fermato sul mismatch di supporto reference/native prima di produrre metriche; il secondo si è fermato perché richiedeva inutilmente anchor A su date pre-2011, fuori dalla finestra 2017-2026. Le due correzioni sono state preregistrate separatamente prima del run valido e non hanno modificato subset, modello, hyperparameter, metriche o decision rule. Protocolli: `UNIVERSE_SENSITIVITY_V1_PREREG.md`, `UNIVERSE_SENSITIVITY_V1_SUPPORTFIX.md`, `UNIVERSE_SENSITIVITY_V1_ANCHORFIX.md`.

## DIAGNOSTIC / BURNED

### Pairwise reranker v1 — SCARTATO

Top10 LTR OOS -> logistic pairwise L2 sulle differenze delle 42 feature + rank LTR; training annual expanding solo su shortlist OOS mature.

114 periodi:
- LTR top1 proxy: **22.06% CAGR**;
- reranker top1 proxy: **19.81% CAGR**;
- exact-winner: **8.77% -> 7.02%**;
- winner nel top2: **13.16% -> 8.77%**;
- margin reranker vs successivo differenziale ritorni: Spearman **0.065**;
- forte instabilità: **11.70%** nel 2017-2022, **35.10%** nel 2023-2026.

Conclusione: **la forma lineare pairwise v1 non risolve l'ordinamento della shortlist e non viene portata avanti.**

Action `37041677418`; artifact `11242493662`; SHA256 `13e227467d5f6a52624c71ac2e06b9a1d7fabb58d30fe2a4ff55250e2c829aad`; risultati in `evidence_v1/results/pairwise_reranker_v1/`.

### Nonlinear reranker v2 — SCARTATO

Top10 LTR OOS -> XGBoost `rank:pairwise`, shallow/regularized, singola configurazione preregistrata, 42 feature + posizione LTR normalizzata; annual expanding e maturity gate 63d. Il winner è valutato sul **full Original149**, mentre il reranker può scegliere solo nella shortlist OOS Top10.

114 periodi:
- LTR exact-winner Top1: **8.77%**;
- v2 exact-winner Top1: **7.02%**;
- LTR winner nel Top2: **13.16%**;
- v2 winner nel Top2: **9.65%**;
- LTR winner nel Top3: **18.42%**;
- v2 winner nel Top3: **14.04%**;
- top1 21d CAGR proxy: **22.06% -> 25.51%**, ma era metrica diagnostica e non criterio di avanzamento;
- margin v2 vs successivo differenziale ritorni: Spearman **-0.006** circa;
- 2023-2026: exact-winner **9.52% -> 2.38%**, Top2 **11.90% -> 2.38%**, CAGR proxy **19.27% -> 12.57%**.

La regola preregistrata richiedeva Top2 migliore dell'LTR e Top1 non peggiore: **fallita**. Quindi il v2 non viene promosso e non viene ritoccato ex-post.

Run valido `37046279447`; artifact `11244841228`; artifact SHA256 `ea8d03b91db5aa7fa3643dc7b93f575ea6d0b874599465cfa5a7b05e1e3865f4`; risultati in `evidence_v1/results/reranker_v2_nonlinear/`.

Audit: il precedente run tecnico `37045478600` è **INVALIDO COME EVIDENZA** perché l'evaluator definiva erroneamente il winner dentro la Top10 anziché sul full universe. È stato escluso prima di qualsiasi tuning; modello/configurazione non sono stati modificati nel rerun valido. Protocollo: `evidence_v1/protocols/RERANKER_V2_EVALFIX.md`.

**Holdout70 resta BURNED**: può essere usato solo per diagnostica e progettazione di ipotesi, non per promozione.

## HYPOTHESIS corrente

L'ipotesi `representation universe-dependent` è ora **supportata** dal test preregistrato. Questo elimina una parte importante dell'ambiguità: quando cambia il candidate universe, non conviene ricalcolare ranks/clusters come se il nuovo universo fosse il mondo intero.

Architettura di representation da portare avanti:

`features = f(asset, stable_reference_universe)` con `selection ∈ candidate_universe`.

Restano invece aperti due problemi distinti:
- il target multi-horizon del producer è utile al retrieval ma non ha ancora dimostrato di ordinare bene il top-tail tradato;
- maggiore stabilità del ranking non equivale automaticamente a maggiore performance Top1.

Linea Evidence V1 ora supportata:

`stable reference representation -> LTR top-k retrieval -> top-tail / decision-horizon reranker -> calibrated top1/top2 probability -> sizing`

Vincoli invariati:
- label mature;
- training downstream solo su prediction OOS precedenti;
- Holdout70 = burned/diagnostico;
- nuovo Holdout-B congelato prima di osservare performance;
- nessuna ottimizzazione ex-post promossa;
- reference universe e candidate universe devono essere esplicitamente distinti nel codice e nella provenance.

## NEXT TEST

1. Definire e preregistrare **Reranker v3 target-aligned**, senza sweep: frozen LTR Top10 OOS come retriever; representation da reference universe stabile; target del reranker allineato direttamente all'orizzonte decisionale 21d anziché riusare il target multi-horizon del producer.
2. Training v3 annual expanding solo su shortlist OOS storiche con label 21d mature; nessuna riga in-sample del retriever.
3. Valutazione primaria sul winner 21d del full Original149: Top2 containment deve superare LTR v1 e Top1 exact-winner non deve peggiorare; 2017-2022 e 2023-2026 devono essere riportati separatamente. CAGR resta diagnostico.
4. Se v3 passa sul development set, congelare **Holdout-B nuovo e disgiunto** prima di qualunque promotion test; nessun tuning dopo il freeze.
5. Calibrazione confidence/sizing solo dopo un reranker che migliori stabilmente l'ordinamento del top-tail.
6. Mantenere il data-validation gate esterno per ogni nuovo ticker/reference universe.

## Frozen state

- Branch: `research/evidence-v1`
- Baseline frozen commit: `ea1c4e83118309bc7d4bc85f3ea93f658c687d3b`
- Latest validated diagnostic result commit: `91ad9a5d9d717eb1a40f8d6bacb5cf12bbae8cc9`
- Data: `evidence_v1/data/original149/`, `evidence_v1/data/holdout70/`
- Source baseline: `evidence_v1/source/baseline/`
- Original149 files: **151**; Holdout70 files: **72**
- Data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- Source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`
- Environment: `evidence_v1/ENVIRONMENT.lock.txt`, `evidence_v1/requirements.lock.txt`
- Frozen-data provenance: `evidence_v1/PROVENANCE.json`
- Reusable LTR checkpoint: `evidence_v1/checkpoints/retriever_ltr_v1/`
- Frozen universe-sensitivity subsets: `evidence_v1/protocols/universe_sensitivity_v1/`
- Universe-sensitivity durable results: `evidence_v1/results/universe_sensitivity_v1/`
- Results/artifacts registry: `evidence_v1/RESULTS_REGISTRY.md`
