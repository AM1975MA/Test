# ETF Trader V2 — Data × Superpowers: consolidated evidence and decision review
**Decision memo | 2026-10-08 | `AM1975MA/Test` only | `research/v2-xgb-immutable-checkpoints-20261008`**

## Executive decision

**Main recommendation:** preserve the exact canonical V2 and shift research from trying more learner smoothers, leaf constraints, tree counts, cascade thresholds, or post-selection risk overlays to a **causally audited model-and-data lifecycle** and a **single mechanistic investigation of XGBoost training instability**. The new full-V2 economic challenger, if any, must be preregistered and assessed against a **matched same-vintage, same-universe full-V2 reference** on genuinely new as-of material. Keep a separate risk-policy gap review because the 2025 drawdown is not solved by a training-stability metric.

This is a **source synthesis and research plan**, not a new backtest, not a claim that Golden performance can be recovered, not a model trained by this work. Superpowers agent delegation is not exposed in the current session, so its specialist lanes are review assignments, not separate completed subagent reports.

## 1. Sources of authority and non-comparable grain

| Source type | What it can establish | What it cannot establish |
|---|---|---|
| Matched full annual V2, 2,366 daily valuation rows, all components/fees | Effect of same-universe raw vendor vintage on actual model, MA3, governor and economic results; the outcome release gate | Attribution of Golden-vs-fresh gap entirely to Compact21; true future profitability |
| XGB 4-year factorial, frozen test-input | The annual fitting stage is a powerful amplifier; X-only and y-only perturbations both matter | Unique first flipped split, additive X/Y causation, entire full V2 CAGR attribution |
| Single ETF / top-1 O2O 21d proxies, monthly sampled DD | Hypothesis screening and whether an alternative learner preserves exceptional-opportunity capture | Full V2 CAGR, day-level DD, fee/stop equivalence |
| R0-E/F/H synthetic generated grouped rankers | XGBoost API and **possible** split/label sensitivity at fixed fixtures | Financial economic noninferiority, choice of optimal real leaf/round count |
| R0-G frozen raw-price-derived labels | Exact existence of grade flips, tie transitions and pair inversions between two Yahoo snapshots | Exact original feature-valid training cohort, ranking objective's internal pairs/gradients, full portfolio economics |
| Frozen OOS LTR Top38 recall and R0-D | An upper bound on retaining ex-post realized best ETF in the **different** retriever | Actual Compact21 cascade/Full V2 outcome |
| L2-N/O/P original-risk ledgers | Actual full-V2 repeat2 2025 drawdown drivers and results of tested overlays | Effectiveness of an untested new risk rule |

**Strict rule:** Never put historical Golden 43.146%, Yahoo fresh 31.604%, Repeat2 30.844%, monthly Titanium-only 13.81%, or standalone XGB proxy 19–32% in a performance comparison without documenting their distinct data, strategy and horizon contract. The original `2026-10-02` fresh Yahoo run is separate from the three rapid Repeat snapshots.

## 2. Reconciled quantitative source ledger

### Full V2, not proxies

- Golden original Annual V2: **CAGR 43.1459524203%**, already reproduced *within its own archived 5-Parquet snapshot* by `gap_analysis/results/PARITY_43PP.json`. Source code identity parity was audited. The old system runtime is not fully byte-proved identical to a modern fit environment. **Do not label Golden an unverified reference**.
- Fresh Oct 2 Yahoo V2: **31.6039945629%**, delta **−11.5419578574 percentage points** vs historical Golden, controlled **code** factor, changed **raw-data vintage**. Which component of the delta is from changing signals and which from changes to execution prices has **not** been fully attributed for the Golden-vs-fresh comparison.
- Three consecutive frozen Yahoo Original149 repeat full V2: **29.7534477466%, 30.8437049256%, 34.6770790748%**, spread **4.9236313282 pp**. Full V2 daily top1 disagreement between pairs ~**30.09–33.26%**, either top1/top2 changed **57.52–66.10%**.
- **Six same-byte V2 runs** gave exact **30.8437049256%**; not a generic nondeterministic execution issue.
- **Execution-price/risk ablation** `forensics_v1/results/EXECUTION_ABLATION.json`: reuse exactly frozen Repeat2 portfolio **decisions**, execute across all three raw Yahoo versions -> all CAGR about **30.84368–30.84370%**, spread **0.00002198 pp**. Same decisions largely eliminate the 4.9236 pp spread. Thus the repeat-source dispersion is **upstream decision/model-state instability**; the Golden-vs-fresh 11.54 pp cannot automatically inherit this exact attribution because it is a separate comparison.

### Mechanism in canonical Compact21 and MA3

- Raw perturbation: 137/149 ticker CSVs differ; max OHLC relative diff about **2.511e−6**, no missing historical dates.
- Four-year Compact21 XGB forensic (held inference X, 2017/2020/2023/2026, vintage1 vs vintage3): inference-feature-only Top1 disagreement **0%**; full refit **43.75%**; **training X only 62.5%**, **training labels only 58.33%**; effects are NON-ADDITIVE and sample is narrow (four years).
- `forensics_v1/results/TITANIUM_COMPONENT_ABLATION.json`, repeat1/3: raw `compact21` mean absolute score delta **0.0358121**; alternative Tail raw score mean abs **0.00006468**. Compact21 percentile rank MAD **0.0534115**, Tail rank MAD **0.00043858**. These score scales/transformations differ, so not an exact fractional attribution of final capital effects, but the observation prioritizes Compact21.
- `forensics_v1/results/STAGE_AMPLIFICATION.json`, repeat1/3: `TIT_R` mean abs delta **0.0422982**, `FINAL_SCORE` **0.0214444**. MA3 model outputs vary too: `ET_TAIL` mean abs delta **0.0279101**, `XGB_TAIL` **0.0138096**; final daily top1 disagreement **30.7692%**. A Compact21-only fix is not *full* V2 reproducibility; MA3/cluster states need checkpoint/invalidation.
- R0-G labels: two frozen price vintages and canonical integer relevance grades, 267 historical month rows, Compact21 **16 changed integer grades, 8 strict rank-pair inversions, 7 tie→ordered and 7 ordered→tie**; Compact63 10 grades, 5 inversions, 3+3 ties. Counts reconcile 4/4 original forensic cutoff year differences 12/16/16/16. This **does not** show how many XGB internal sampled pairs or gradient weights are affected; old annual Booster files have not been found in tracked Test Git objects. X-only instability is major independently, so solving only ties cannot close the incident.

### Model replacements / overlays that did not solve joint objective

| Evidence | Measured result | Reason for decision |
|---|---|---|
| L2-D Ridge vs XGB on 113 dates | Ridge common-input vintage Top1 agreement **100%** vs XGB **45.13–56.64%**; XGB chosen ETF within realized 21d top5 **19.17%**, Ridge **7.96%** | Stability alone erases opportunity selection; monthly top1 proxy only |
| L2-G HGB direct/teacher | Fails required Top1 stability, Rank-MAD and/or opportunity gates | Not canonical XGB; smoothing/distillation not demonstrated replacement |
| L2-H Fourier smooth/consistency | Same-seed controlled variant can stabilize rankings but loses realized Top5/selected return vs XGB/Ridge | Cannot promote merely by low rank-MAD |
| L2-E/F score blends and 75% Ridge +25% XGB capital sleeve | Improved monthly sampled drawdown and narrower proxy CAGR range, but does not stabilize learner and loses XGB upside in 2 of 3 snapshots | Not unchanged full V2; no ex-post weight tuning |
| L2-I committees on multiple Yahoo vintages | Leave-one-vintage-out Top1 agreement ~65.5–69.9%, below prereg 90% | Vendor repeats are same market, consensus has structural instability |
| L2-J 6m moving block bootstrap | NDCG@5 fell **0.56935→0.51696**; chosen net 21d ETF mean **3.391%→1.945%** | Reduces top-tail capture and does not materially solve Top1 robustness |
| full V2 Q4 rounding | Vintage CAGR span ~4.92→~2.24 pp but mean CAGR ~31.76→29.01%, Top1 agreement worsened | Lower spread with reduced economic result is not success |
| L2-N orthogonal-vol gross overlay full V2 | Matched Repeat2 CAGR **30.8437→29.5656%**, daily maxDD stays **−25.6896%** | Overlay loses return without reducing worst drawdown |
| L2-P remove market-stress gate for single-name stops full V2 | CAGR **30.8437→25.9749%**, daily MaxDD **−25.6896→−33.0970%**, 20→48 stop events | Worse economics and risk, do not retune on burnt 2025 |
| Prior LTR Top5→Hybrid24 and four Top10 rerankers | Rejected; frozen LTR Top38 retains true future 21d winner **97/114**, loses **17/114** | This is NOT Compact21; hard early exclusion creates irreversible positive-tail loss |
| R0-D trailing 21/63 cross-sectional dispersion | Predicts future return dispersion Spearman **0.4846/0.4950**, but miss-AUC **0.515/0.531** | Volatility regime cannot identify Top38 false negatives on studied dates |
| R0-E fixed leaf cap 8, 120-tree toy | Initially appears favorable | **Superseded** by stronger R0-F; +1 integer grade did not reverse pair |
| R0-F cap8, true pair inversion, 360-tree toy | Some X/Y scenarios cap8 worse Top1 than original | Hard leaf cap not a proven robust fix; stop sweeps |
| R0-H boosting-prefix count 60/120/180/240/300/360, 2 toy worlds ×3 seeds | Y-only Top1 agreement cross-world **21/24,19/24,20/24,21/24,21/24,22/24** | **No monotonic stability gain** from fewer trees, keep 360 incumbent |

All L2 metrics and R0 toy results are exploratory and subject to multiple-hypothesis reuse of same market history; no longer a clean historical model-selection holdout. All R0 synthetic outputs are artificial and cannot be put on the same CAGR axis as full V2.

### Separate drawdown concentration concern (full V2 Repeat2)
L2-O attributed approx **−19.887 pp** of the **−25.69%** 2025 worst full-V2 daily drawdown (peak-to-trough accounting basis) to UNG top1/top2; during the interval the market broad benchmark SPY was positive ~12.64%. No existing stop fired because combined market-stress gate was absent. L2-P removed that gate, but increased repeated UNG stop/reentry activity and worsened both CAGR and DD. **A ranking training stability fix is not necessarily protection from a correctly but riskily chosen concentrated ETF.** Any future risk-design is a **separate problem statement**, not an opportunistic new threshold tuned to 2025. Note report date-labeling difference versus actual next-Open valuation: does not change DD.

## 3. Decision framework for next research

**Primary financial decision:** Is it possible to reduce economically important decision instability under legitimate point-in-time vendor revisions **while retaining capture of extreme upside** in the complete annual V2?

### Three metrics + guardrails (Data metric design)
1. **Primary economic**: paired *full V2* daily-compounded net CAGR on *matched* pristine future dataset, with cross-snapshot worst-case and mean/worst per-vintage delta vs canonical baseline, and explicit portfolio vintage spread. **CAGR per vintage, not best-of-vintages**. For short follow-up windows report cumulative returns/daily P&L instead, not annualized precision.
2. **Primary robustness**: `portfolio_deviation` = mean absolute target exposure difference per symbol and date across data snapshots (position-weighted, not just Top1 agreement); `economically_material_flip` = fraction of dates when a changed decision generates meaningful signed P&L difference on **the same** execution tape; its future realized consequences are computed only after maturity.
3. **Primary tail skill**: chosen top1/top2 exposure-weighted recall of realized 21/63d top-decile/upside, matched mean realized selected returns vs XGB baseline and missed winner return-regret; never report a better NDCG as equivalent to greater full V2 alpha.

**Guardrails**: daily maximum drawdown, concentration in single ETF/correlation family, realized costs + turnover (not monthly sampled DD), label maturity and universe compatibility, no hindsight selection of champion using same test outcome. Use exposure-per-day ledger, not disconnected raw rank metrics.

Do not invent a universal `90% Top1 agreement` threshold or accept `no CAGR degradation` based solely on a noisy handful of months. Numeric margins for prospective economic non-inferiority and risk concentration must be explicitly locked **before** access to holdout outcomes and justified by risk budget and measurement uncertainty.

## 4. Causal priorities and stopping criteria

### P0 — provenance / causal model registry (engineering, no strategy change)
Freeze exact as-of raw history, point-in-time corporate-action state, ETF universe and membership, 125-feature ordered X/y/group matrices with mature exit dates, sample keys, source/runtime hashes, all **three XGB UBJ per horizon/annual cutoff**, MA3 ExtraTrees/XGB/imputer/PCA-KMeans states, prediction and risk-engine checkpoints, before studying fit interventions. Separate `REPLAY`, `PREDICT`, `REFIT`: freeze version, **not retraining ability**. Fail closed on stale scores, dates, schema, labels and model selection. Validate same-input checkpoint reload prediction identity and copied daily trade book. This is reproducibility, not inherently better out-of-sample alpha. Existing `checkpoint_contract_v1` is an isolated verified prototype, NOT integrated.

### P1 — **economic impact of decision changes** with already frozen scores/books
Avoid repeating earlier source-vintage fit/replay. Inspect existing TIT_R, MA3 pred/final scores, daily top1/top2 weights and L2-O ledger to rank **high-impact switches** by fixed-tape paired P&L/turnover (properly controlled), and separate:
- Compact21 vs Tail-driven rank perturbation (TITANIUM_COMPONENT_ABLATION already measured; don't recompute);
- MA3 ExtraTrees/XGB/cluster-induced drift;
- exposure/gross/stop-induced propagation.
Cross-execution-price cause on 3 repeats is **already falsified**; do not redo.
**Only** if missing specific score–ledger linkage requires a new reconstruction, preregister the minimum new ablation and demand byte/source parity; do not launch a new full-year retrain.

### P2 — label-pair mechanism and feature-histogram mechanisms **as separate orthogonal falsifiers**
Read-only examine R0-G's 8 actual strict inversions and 14 tie transitions, **actual return margins** and whether modified pair was in a high-relevance tail; note `rank(pct=True)` then `round(*100)` per monthly query can produce ties. A tiny rank flip can change the pair pool and gradients but this is not proved by merely counting flips. Separately inspect X-only perturbations, rank-percentile/tie changes in engineered features, histogram bin thresholds/near-tied competing splits and whether rank decisions for important ETF exposures change. Old Boosters absent; instrument a *new synthetic* exact-matched `QuantileDMatrix` fit if needed, with single intentionally changed factor, source-frozen settings, and no Original149 P&L. Independent check that perturbing only features changes something even if no label flip. Avoid pretending original `max_leaves=8` fixes X/Y.

### P3 — single mechanism-led next learner candidate, else **NO MODEL CHANGE**
Choose **one** based on P1/P2 evidence:
- If ranking pair inclusion/near-ties are the dominant economically important channel and X-only pathology can be separately bounded, consider a **confidence-weighted pairwise loss** that downweights only truly ambiguous mature return margins while retaining all pairs involving extreme upside. This is a research hypothesis, not an approved XGB API switch; feasibility and label-maturity must be verified; L50/Q4 discretization repeats forbidden.
- If real X-only histogram/near-equal split candidates dominate, consider **one** numerically stable split selection strategy or preprocessing representation *tied to a proven split mechanism*, not blanket feature quantization or another max-depth/max-leaves sweep.
- If no concrete pair/split mechanism can be isolated, **STOP** candidate generation, keep XGB canonical. A small regularized Dense groupwise ranker may receive a separately reviewed feasibility spec only if point-in-time temporal sample size supports it; stacking Dense layers alone is not regularization.
- Hard Top38 waterfall remains out of scope unless true canonical Compact21 as-of Top25% retention and positive-tail preservation improve materially in genuinely new evidence. Historical LTR 85% overall and 17 missed winners caution against it.

### P4 — preregistered, staged validation
- **Gate 0 provenance/parity**: all changed code only `AM1975MA/Test` isolated branch; source SHA/model manifest, temporal label maturity and year/seed coverage. If impossible to reproduce original Booster, mark legacy-only, don't reconstruct Golden from modern Yahoo data and claim identity.
- **Gate 1 synthetic** (TDD, read/write only research harness): independent grouped fixtures, separate X/Y/joint, actual pair flips, distinct seed/worlds, 360-round source-compatible fit, native/common-inference comparison, structural split and top-tail quality. Reject if any scenario loses high-upside capture or merely smooths predictions.
- **Gate 2 fresh *point-in-time* market snapshots**: precommit universe, ETF eligibility, vendor version, cutoff and a single candidate **before** reading labels/strategy performance. Compare original vs candidate on exactly same OHLCV, same MA3/risk/cost and daily engine, and genuine new dates that were not used in old strategy design. Repeat download vintages are same market and stress sources, NOT independent performance test sets. EU120 or other universe only as conditional domain shift and *separate development identity*, never silently renamed independent market holdout.
- **Gate 3 full V2 economic decision**: per-vintage net CAGR/daily P&L, worst case and span, daily MaxDD, Sharpe, turnover and fees, drawdown tail, positive-tail capture and exposure-weighted decision divergence. Daily ledger source/implementation parity, maturity/walk-forward, no model selection after a maximum historical CAGR result.
- **Champion / challenger**: new calendar training can create a new immutable model; reject unsupported/expired models; no indefinite freezing of stale training. If candidate fails, leave incumbent unchanged. If both invalid, explicit `NO_APPROVED_MODEL`.
- **Gate 4 monitored deployment only after separate approval**, never default promotion to `Etf_trader`.

### Separate P-RISK (not conflated with model fit)
Use existing L2-O/P to document risk-driver **UNG concentration** and current stop market-gate vs reentry interaction. Test a separately preregistered *position-state/entry/reentry* policy only on genuinely fresh evidence, not another threshold combination fit to the 2025 loss. Do not allow risk overlay to mask a failed learner or claim training stability.

## 5. Do-not-repeat register

No new historical performance search over: HGB/Ridge/Fourier, L50 and Q4, multiple XGB vintage votes/blends/75-25 sleeves, temporal bootstrap, global leaf-8 cap, reducing rounds to any observed "best" among 60/120/180/240/300, old LTR Top5/Top10 rerankers and fixed 25% / trailing-dispersion adaptive screens, R0 synthetic repeated same seeds/labels, orthogonal-vol and market-gate stop ablations L2-N/P. Avoid mixing 2017–26 prior-year evidence with a fresh prospective result to claim independent statistical significance.

## 6. Independent specialist review briefs (NOT ACTUALLY DISPATCHED)
- **XGB internals/gradient specialist:** find precise pair sampling and loss gradient discontinuities and first differing histogram split if model dumps available; explain training-X-only mechanism.
- **Numerical lineage/data specialist:** deterministic snapshot/feature/label/group hashes, revision provenance, time leakage and original Golden parity.
- **Stats/risk analyst (Data review):** audit grain, sample independence, selection-snooping, epsilon non-inferiority and tail-skill metrics.
- **Quant portfolio engine reviewer:** matched full-V2 replayer, daily risk ledger, exposure-weighted P&L, concentration/stops, evaluate only same-vintage decisions.

Reviews are assignments for agents if a callable dispatcher becomes available; current session has **no** such tool. Do not imply four independent reviews occurred.

## 7. Next smallest executable milestone recommended

**Deliver a P0+P1 shadow evidence package without changing trading decisions**:
1. Table of availability for exact annual Boosters / historical raw source matrices; mark missing.
2. FitIdentity, UniverseIdentity, PredictionIdentity contract, with the correct `REPLAY/PREDICT/REFIT` transitions already designed.
3. A **single source-backed, no-fit** daily economic switch-attribution table using existing Repeat1/3 model-output and full V2 ledgers **if** files are sufficient; otherwise explicitly `BLOCKED_MISSING_SCORES` with exact artifact need.
4. First 8 pair-return-margin forensic (read-only) and X-only binning trace design.
5. Review gate: decide whether the next authorized synthetic intervention should target X-side bins, label pair gradients or **no candidate**. Do not preselect a new model solely from this memo.

## Source links
- `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`, `PARITY_43PP.json`, `CROSSED_REPLAY_MATRIX.json`, `canonical_v2_determinism_control_v1/RESULT.json`
- `compact21_stability_v1/results/FULL_REPLAY.json`
- `forensics_v1/results/{EXECUTION_ABLATION,COMPACT21_XGB_FORENSIC_V1,TITANIUM_COMPONENT_ABLATION,STAGE_AMPLIFICATION}.json`
- `target_redesign_level2_v1/L2{D,E,F,G,H,I,J,N,O,P}_RESULTS.md`
- `docs/superpowers/reviews/2026-10-08-r0{d,e,f,g,h}-*.md`
- `target_redesign_level2_v1/checkpoint_contract_v1/` prototype
