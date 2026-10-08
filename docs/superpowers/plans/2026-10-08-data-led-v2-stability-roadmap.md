# ETF Trader V2 — Data-led training stability Implementation & Research Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** eliminate silent retraining/data-vintage drift and establish **at most one** mechanism-backed change to Compact21 which demonstrably reduces economically material prediction instability **without sacrificing full V2 upside capture**.

**Architecture:** Track A is a **research-only, strict replay/predict/refit model registry** with full as-of source identity and all V2 producer states. Track B is a **read-only fixed-price attribution + separate X-only and y-only pairwise-loss mechanism study**, then one conditional synthetic candidate if supported. Track C is a prospectively preregistered **full V2 economic release gate**, separately from portfolio stop/governor improvements. Baselines and experimental cohorts retain exact independent identities; no 2017–26 best-vintage selection.

**Tech Stack:** Python 3.13.5, numpy 2.3.5, pandas 2.2.3, XGBoost 3.1.3, sklearn/Numba versions pinned from run manifest, GitHub Test, pytest, SHA256 manifests, canonical full V2 Stage19/MA3 daily ledger. No external data download or strategy test during initial tasks.

**Spec:** [Data consolidated evidence decision](../reviews/2026-10-08-data-consolidated-stability-decision.md), [model lifecycle design](../specs/2026-10-08-v2-model-lifecycle-and-training-stability-v2-design.md), and [three architecture analysis addendum](../specs/2026-10-08-v2-three-architecture-analysis-addendum.md).

## LATEST EMPIRICAL PIVOT — 2026-10-09 — REAL 2.33M-PAIR EVIDENCE

**This section takes priority over earlier blanket proposals.** [Data R0-J/R0-K/R0-L evidence report](../reviews/2026-10-09-r0j-real-material-pairs-and-r0l-cost-aware-path.md); [research-only executable custom loss](../../../target_redesign_level2_v1/stability_program_v2/cost_pairwise.py) and [TDD tests](../../../target_redesign_level2_v1/stability_program_v2/tests/test_cost_pairwise.py).

- **Real matched Yahoo Repeat1/3 adjusted Open history**, 267 mature monthly 21d target dates, **2,333,613 unordered ETF pairs**. Among integer relevance pairs, only 8 strict order reversals +14 transitions into/out of tied grade. Strictly inverted original 21d forward return gaps **all <=0.0116 bp** and no pair had relevance > 81.3rd percentile. All 22 changed grade relations had spread **<=7.6489 bp**.
- **Existing strategy fee scale**: 0.1% buy + 0.1% sell => **20bp** roundtrip illustration, not a claim each potential pair comparison incurs exactly this cost. At a 20bp return-spread band, only **88,417 / 2,333,613 = 3.7888%** of real pairs are deemed indistinguishable; **96.2112%** remain. **0 of 118,939 high-decile-vs-bottom-quartile comparisons removed**. All retained pairs are directionally stable across Repeat1 vs Repeat3; **14 eligibility statuses** cross the fee-band boundary and must be handled by future soft weighting. Crucially this is **descriptive pair-level evidence**, not model-prediction/CAGR proof.
- **Native rank:ndcg (linear gain)** technical fit works with original 0-100 label grades in XGB3.1.3, but R0-K independent synthetic world A shows better X/Y Top1 agreement **while lower top5, exact winner and NDCG quality**; NO GO as a blanket replacement, second world incomplete/unreported, NOT a full candidate.
- **Custom mask feasibility**: TDD 4/4 GREEN, compile GREEN, actual XGB custom objective on artificial 10x149 groups/125 features returned 25 rounds and nonconstant scores. **Only feasibility**: the full-pair sampling/normalization does NOT match original native `rank:pairwise`, historical as-of maturity and financial alpha still unverified.
- **Priority #1 new unique hypothesis:** an economically justified **pairwise confidence weighting** against ambiguous near-tie returns, **not global label quantization L50**, no retraining on burnt Original149 for gain selection. Do not treat hard 20bp binary cutoff as already validated: X-only training instability previously 62.5% remains independent, and there are 14 fee-band eligibility edge flips. Consider *continuous* uncertainty weighting in a separately preregistered synthetic falsifier only after verifying native pair-gradient semantics, retaining all extreme-tail pairs.
- **STOP conditions:** if X-only decision instability remains severe or if synthetic high-upside capture falls, do not claim resolved. Do not invoke new financial full-V2 replay on 2017-26 to optimize band or loss. Keep P0 source/versioning and P1 capital attribution essential, and P4 new prospective full V2 gate compulsory.

**Next action sequence:** (1) implement historical as-of label maturity and pair-gradient contract in research-only package; (2) compare exact native pair selection/sampling and loss scale vs custom objective on synthetic fixtures; (3) prereg one X/Y separate + joint perturbed synthetic test without tuning band or seeds; (4) only with independent future financial evidence evaluate same-vintage full V2 and tail economic non-inferiority. **No production adoption and no new CAGR reported.**

---


## Aggiornamento eseguito — 9 ottobre 2026: R0-J / R0-K / R0-L CHIUSI

**Rapporto tecnico e fonte delle nuove decisioni:** [Completamento R0-J/R0-K/R0-L](../reviews/2026-10-09-r0j-r0k-r0l-completion.md). Il prototipo e i [risultati strutturati](../../../target_redesign_level2_v1/stability_program_v2/r0j_r0k_r0l/real_market_pair_statistics.json) sono sul branch di ricerca. **Questo aggiornamento è successivo agli esiti; non costituisce una nuova preregistrazione.**

**Dato reale perseguibile ma non validazione:** 8 inversioni strette nel Compact21, tutte entro **0,0115991 bp** di differenza di rendimento 21d su due Yahoo vintages; nessun ETF nel decile superiore fra queste inversioni. Una banda di 20 bp elimina 88.417/2.333.613 coppie teoriche (3,78885%), zero sign flips tra quelle eleggibili in almeno una vintage, **ma 14 status eligibility flips persistono**, e 2.373 coppie escluse coinvolgono il top-decile. 20 bp è motivazione iniziale di costi, NON scala ottimale provata del noise o della loss; i costi comuni alle alternative non giustificano automaticamente una banda economica. Le coppie enumerate non equivalgono alle coppie effettivamente campionate da XGBoost.

**R0-K obiettivo generale rank:ndcg: NO GO su base sintetica preliminare**: nel mondo A 10/12 Top5 vs 11/12 pairwise con stabilità più alta; B `rank:ndcg` completato (9 fit rimasti) ma il baseline `rank:pairwise` B era stato allenato nel run interrotto **senza output persistito**, quindi B matched comparison non disponibile e NON rifatto. Non descrivere R0-K come 36/36 fit validamente confrontabili.

**R0-L custom pairwise masker: FEASIBLE TECHNICALLY, NOT ECONOMICALLY VERIFIED**: codice `Test` con gradiente/diagonale Hessiana, 8 unit test GREEN, 12-round QuantileDMatrix smoke PASS. Attenzione: obiettivo su tutte le coppie ammissibili (non campionamento nativo XGB), Hessiana diagonale approssimata, rendimenti futuri del training devono essere MATURI; adapter full-V2/source-only non realizzato.

### Conseguenza sulla sequenza

1. **Next task = Track A provenance e shadow objective test**, non un altro filtro/leaf/rounds/stock-picking backtest. Precisare matematicamente la loss rispetto a XGBoost native e documentare in anticipo il criterio per impostare la banda senza usare P&L storici. Validare freeze/replay/predict/refit e maturità delle etichette prima di un fit su dati reali.
2. **Next TDD scope**: gruppi, ticker/date e `exit_date_h < cutoff`; diag Hessiana, pair normalization, finite-difference grad, X-only/Y-only/joint perturbations, tail-recall, rank-robustness; same native 125-feature input contract. Due fixture sintetiche NUOVE, non stessa seed R0-F/H/K. Un solo candidato fissato prima dei risultati.
3. **Nuovi dati**: usare un nuovo campione as-of maturato, senza accettare le tre vintage Yahoo come tre mercati indipendenti. Full-V2 matched portfolio gate e risk-policy gate separati. NO GO se la capacità di selezionare top-tail scende.
4. **Se non è possibile dimostrare la stabilità contemporaneamente per X-only e Y-only**, conservare `rank:pairwise` canonico, senza ulteriori griglie sullo stesso Original149.

**Stato:** diagnostica R0-J/K/L completata nei limiti documentati, report salvato. Nessuna prova di CAGR migliorato, nessuna modifica in `Etf_trader`, nessuna validazione completa V2 in questo aggiornamento.

---

## 2026-10-09 R0-M — completed pre-registered synthetic three-arm mask test (active stop decision)

[Original R0-M preregistration](../reviews/2026-10-09-r0m-pair-band-prereg.md), [new Data review with results](../reviews/2026-10-09-r0m-data-pairmask-results.md). **18 synthetic XGBoost fits**, 2 independent artificial worlds, 3 training conditions and 3 model objectives, seed101 and 360 rounds; **no real ETF train, no full V2 financial backtest**. The proper mask-only comparison is custom full-pair logistic **20bp versus 0bp**, NOT native rank:pairwise versus custom. A pair reversal under 0.1bp of synthetic forward return produces **Top1 stability 40/40 vs 38/40** in the matched custom models; however **top5 capture changes 17→18 in world A, 16→15 in world B**, exact synthetic winner aggregate **13→12/40**, average NDCG drops **.917695→.915921**, and selected synthetic return worsens in both worlds. Train-X stability **40/40→39/40**. **Predeclared joint gate: FAIL / NO GO; do not integrate 20bp hard-mask objective or tune a new threshold on Original149**. Programmatically validated: **12/12 focused Python tests GREEN**, independent Data results audit PASS. Full source/test/JSON artifact zipped for download; not all source files are GitHub-committed. 

**Subsequent direction:** (1) preserve source-native pair sampling/scale/curvature as far as possible; (2) define ambiguous pairs using independently measured data-revision uncertainty, not the assumed trade fee as a sufficient measurement-error bound; (3) avoid hard threshold eligibility discontinuities (14 real Repeat1/3 threshold flips at 20bp), consider *hypothetical* continuous weighting only after a different pre-registration; (4) require train-X-only stress and high-upside selection alongside rank consistency. **This is a research hypothesis, not a proven solution.** Existing V2 360 rounds, three seeds, MA3 and risk remain untouched.

---

## Active decision update — 9 October 2026 (R0-J / R0-M / R0-N)

**Read this before launching any future learner tests.** [R0-M preregistered hard-20bp-mask test](../reviews/2026-10-09-r0m-pair-band-results.md): 18 synthetic fits, two worlds, Data audit PASS, **FAIL_JOINT_GATE**. The mask neutralized a constructed near-tie flip, but exact winner capture fell 13/40→12/40 and mean synthetic selected return fell in both worlds relative to identical custom full-pairs unmasked loss. The 20bp transaction-fee assumption is **not** a validated noise floor; do not integrate or tune the hard mask.

**Genuine native-XGB finding**: the original source has **no explicit** LambdaRank pair settings. XGBoost 3.1.3 native training objective defaults to `topk`, `lambdarank_num_pair_per_sample=4294967295` (effectively exhaustive pairs); **do not** misinterpret the separate evaluation `ndcg@3` pair count **3** as a training objective truncation. Tested config on 4×18 toy group shows original and explicit k=18 **predictions exactly equal**, while topk=3 is different. Verified official version-specific docs at https://xgboost.readthedocs.io/en/release_3.1.0/parameter.html.

**Promising but explicitly limited first native candidate, R0-N**: [pre-frozen one-axis design](../reviews/2026-10-09-r0n-native-topk5-prereg.md), [results and Data independent audit](../reviews/2026-10-09-r0n-native-topk5-results.md). Only change is native `lambdarank_num_pair_per_sample=5`, preserving `rank:pairwise`, all ETF candidate eligibility, 125 features, 360 rounds, seeds 101/202/303 and original hyperparameters. Exactly **36 synthetic-only fits**, two *new* 20-query eval worlds, X-only/Y-only distinct perturbations, saved 36 model-score .npz and checksum. In world A Top5 18/20 both, X/Y Top1 concordance 20/20 both; world B top5 improves **15/20→17/20**, X-only concordance **17→20/20**, Y-only **16→19/20**, exact winner 4/20 both; artificial mean selected returns improve in both worlds. **Counterevidence**: world B **NDCG@5 drops .90339→.87849**, paired descriptive 95% interval for delta [−.05159,−.00079]; selected return improvements have broad intervals crossing zero. **Classification: SYNTHETIC_MECHANISM_PLAUSIBLE_WITH_RANKING_REGRESSION, NOT MODEL APPROVAL**. The source program first created only 18 entries in the hash manifest; QA caught it, test RED then fix GREEN, verified 36 hashes; no booster rerun.

**Updated shortest economically responsible progression**:
- P0: exact source/preprocessing/fit/MA3 state snapshots and valid `REPLAY/PREDICT/REFIT` contract; original Booster missing means no fake historical replay.
- P1: decision/exposure-weighted economic attribution with already saved materials only; do not re-run 2017–26 portfolio or fit experiments.
- P2: for genuinely new causal ETF data, preregister **one** native topk5 versus untouched exhaustive objective *provided* we have enough as-of time forward to measure daily portfolio economics. **Rank-quality noninferiority is an explicit fourth gate**, not merely Top1 and Top5 hit; a ~.025 drop in artificial NDCG is a risk warning that must be measured on future ETF outcomes. No alternative K / custom loss / smoothing / rounds search on burned histories.
- Gate future: full unchanged V2 net paired results per data vintage, daily MaxDD, fees/turnover, exposure-weighted material flip rate, and rare realized positive-tail capture. Short clean future sample => report provisional cumulative daily economics rather than annualized CAGR and defer go/no-go.
- If topk5 lacks rank/financial quality, **NO GO**; keep original native exhaustive objective and no learner changes. Dense and cascade remain untrained design alternatives; no new training until evidence changes.

**Development scope** remains `AM1975MA/Test@research/v2-xgb-immutable-checkpoints-20261008`; production `Etf_trader` and `Trader_selector` untouched. Only test protocols, diagnostics and future criteria changed.

---

## Hard constraints

- Repository `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008` **only**; no `Etf_trader`, `Trader_selector`, production vendor source, live funding/risk code, merge or PR without explicit later authorization. This document is **an execution proposal, not permission to fit or deploy financial learners**.
- Preserve canonical `rank:pairwise` objective and train group/row ordering, 125 features, `max_depth=4`, **360 boosting rounds for each of seeds 101/202/303 and each horizon 21/63**, all original MA3 states and daily risk engine as the baseline, unless an *individual preregistered* new candidate explicitly changes one chosen axis.
- All training labels must be mature: `signal_date < annual_cutoff` and `exit_date_h < annual_cutoff`; never inject future ETF composition, future close or recently revised adjusted factors into old as-of snapshots and claim original-point-in-time equivalence.
- Distinguish Golden archived `43.145952%`, fresh Oct 2 `31.603995%`, frozen Repeat1/2/3 `29.7534/30.8437/34.6771%` and proxy Top1 returns; NEVER share an unlabelled comparative CAGR plot.
- Keep 2017–26 Original149, three Yahoo repeat versions and the R0 synthetic seeds as **development-burned**; no broad retraining, hyperparameter tuning or new full V2 replay on these periods.
- The three Yahoo repeats are **same market, different raw revisions**, suitable for numerical stress testing but **not three independent financial validation datasets**.
- No blind reruns of L2-D/E/F/G/H/I/J, R0-D/E/F/G/H, Q4/L50, bootstrap, HGB/Ridge/Fourier, multi-snapshot committee, 75/25 risk capital, Top5/Top10 rerankers, 25% hard screening, new thresholds for L2-N/P, tree cap8 or 60–360 round searches.
- Keep actual XGB fitting, synthetic or financial, behind the gate explicitly stated per Task. New learners and new financial return calculations must have a pre-result protocol and source hash.
- No independent expert agent invocation can be claimed without an exposed agent dispatcher. Reviewer roles are explicit source-audit checklists; self-reviews are not independent expert opinions.

## Decision logic (Data output, not a grid)

| Branch | Trigger from **observable** evidence | Next action | Stop if |
|---|---|---|---|
| A, mandatory | Historical predictions exist but original Booster/feature-lineage may not | Build provenance & immutable **multi-version** lifecycle; no change to learner | Missing as-of source cannot be fabricated |
| B-X (features) | Economically important raw score/portfolio flips correlate with X-only perturbation and split/hist near ties | One **feature-side** mechanism probe, canonical y fixed | No node/feature mechanism evidenced |
| B-Y (labels) | Economically important flips tied to identified ordinal inversions or tie transitions and pairwise gradient inclusion | One **pairwise-label loss** mechanism probe, canonical X fixed | Near-tie downweighting would remove large-upside pairs |
| B-none | Both channels unidentifiable or only synthetic effects | **Keep incumbent**; archive uncertainty, no model replacement | No new economic signal |
| C, later | Single preregistered learner candidate survives synthetic structural and top-tail gates | One untouched-vintage, matched full V2 experiment after user approval | Failed economics, missing maturity, insufficient new sample |
| Risk, separate | Position concentration/reentry concern as in full V2 2025 | Separate risk-policy project informed by L2-O/P, no training fix conflation | Rule effectively optimizes the known 2025 crash |

## Review focus (high-risk QA)

1. **Data vintage and unrecognized rewrites:** exact adjusted Open/Close provenance, same-date adjusted factors, train-vs-prediction hash, source commit/runtime/ETF universe and MA3 cluster remap; failure => no cache/replay claim.
2. **Group pairing and label maturity:** per-ETF name alignment, same monthly group populations and row keys, ties in rounded percentile labels, `exit_date_h < cutoff`; failure => no gradient claim.
3. **Repeated outcome leakage:** same ETF-month panel across Yahoo repeats and multiple historical variants; no spurious confidence from 3-vintage bootstrap, no post-hoc cutoff selection or 2023 split promotion.
4. **Metric non-equivalence:** monthly proxy vs true daily full V2, 21d vs 63d horizon, Top1 rank-MAD vs exposure-weighted costs, 113 vs 114 months; failure => do not present combined ranking.
5. **Risk coverage:** stop-market gate, UNG concentration and reentry; don't infer replacing learner fixes risk policy or disabling market gate improves DD.

---

### Task 1: Establish immutable source inventory and contract of record (Track A1)

**Files:** Create `target_redesign_level2_v1/stability_program_v2/source_inventory.py`; Test `target_redesign_level2_v1/stability_program_v2/tests/test_source_inventory.py`; Create `target_redesign_level2_v1/stability_program_v2/SOURCE_AVAILABILITY.json`.

**Interfaces:** `inventory_sources(repo_artifacts, source_commit, annual_year, horizons, seeds)->dict`; outputs status `FULL_TRAIN_MODEL`/`PREDICTIONS_ONLY`/`MISSING` per year/horizon/seed; `assert_causal_training_rows(rows, cutoff, horizon)->None`.

- [ ] RED TDD: detect duplicated ticker/date/group, missing XGB Booster, as-of cutoff equality or expired label, changed universe membership, inconsistent feature order, implicit future corporate-action version.
- [ ] Read source-only `models.py`, `_xgb_worker.py`, `ma3/hybrid_producer.py`, `a4_cluster_destination.py` and previous manifests; inventory authentic original Golden 5 Parquets (known Parity 43), current Repeat1/2/3 + MA3 states. **Distinguish historical Parquet parity proof from missing original booster models.**
- [ ] Implement minimal hash/list audit only; do not refit any model or replay strategy.
- [ ] Execute package tests, record SHA+counts and missing artifacts honestly, commit Test branch.

### Task 2: Add full as-of model lifecycle contract (Track A2, separate detailed approved implementation gate)

**Files:** Create `target_redesign_level2_v1/checkpoint_contract_v2/{universe.py,identity.py,archive.py,lifecycle.py}`; tests `target_redesign_level2_v1/checkpoint_contract_v2/tests/test_{universe,identity,archive,lifecycle}.py`.

**Interfaces:** `universe_identity`, `fit_identity`, `prediction_identity`, `publish_fit`, `load_fit`, `replay`, `predict`, `refit`; seeded annual XGB fit outputs and stored MA3 component provenance.

- [ ] TDD RED: modified single training label, X, model version, seed, universe, data vintage, feature schema and historical cutoff each invalidate old `fit_id`; changed inference X only invalidates `prediction_id`; new future year and new legitimate ETF universe can create **new distinct fit** while legacy model remains intact.
- [ ] Implement immutable UBJ plus train/label/group bytes for **two horizons × three seeds**; include MA3 ExtraTrees/XGB/Imputer/PCA/KMeans states as explicit future adapter artifacts. Existing read-only checkpoint v1 is a prototype; avoid unsafe pickle deserialization.
- [ ] TDD GREEN, compare saved/reloaded **synthetic** score arrays to same-XGB worker, exact time/group eligibility, concurrency and no-clobber. No historical V2 retrain. `REPLAY/PREDICT/REFIT` are explicit, so models are *not frozen forever*.
- [ ] Gate: complete MA3/cluster snapshot and source-level inference equality must be covered before calling full V2 reproducible; document any missing state and stop full parity claims.

### Task 3: Trace actual *economic* impact of score and position changes from existing frozen artifacts (Track B0)

**Files:** Create `target_redesign_level2_v1/stability_program_v2/decision_ledger.py`; Tests `.../tests/test_decision_ledger.py`; Artifact `DECISION_DELTA_ATTRIBUTION.csv`; report `B0_ATTRIBUTION.md`.

**Interfaces:** `align_same_vintage_decisions(scores,positions,open_tape)->validated_rows`; `attribute_fixed_execution_price(books)->dict`, `economically_material_flip(...)->dict`.

- [ ] RED tests for date/ticker sort, source-vintage mismatch, sampled open-`t+1` ledger date labeling, fees and missing days; positive and negative trade contribution directions; net weights sum and no look-ahead.
- [ ] Read existing `forensics_v1/results/{STAGE_AMPLIFICATION,TITANIUM_COMPONENT_ABLATION,EXECUTION_ABLATION}.json` and frozen full V2 daily ledgers. **Do NOT redo already completed Cross-Execution test**; it establishes trading-price differences do not materially account for 4.92 pp spread with frozen decisions.
- [ ] Only if full input books exist, generate a **new** matched per-signal/decision flip consequence table, annual breakdown by high-opportunity months, actual Top1/Top2 exposure and turnover; reconcile ledger with already frozen totals. No refitting or retuning on actual returns.
- [ ] If scores/MA3/ledger missing, output exact `BLOCKED_MISSING_ARTIFACTS` with source needed and do not fabricate contribution percentages. Document any unexplained residual.

### Task 4: Pairwise gradient and X-only feature sensitivity diagnosis (Track B1)

**Files:** Create `target_redesign_level2_v1/stability_program_v2/{pair_margin_audit.py,feature_split_inventory.py}`; tests `.../tests/test_pair_margin_audit.py`, `test_feature_split_inventory.py`; reports `PAIR_MARGIN_AUDIT.md`, `X_ONLY_SPLIT_DIAGNOSTIC.md`.

**Interfaces:** `label_pair_transitions(old,new,keys)->{strict_reversal,tie_create,tie_drop,...}`; `return_margin_for_pairs(canonical_price_vintages,matched_dates)->rows`; `feature_split_inventory(fitted_dump_or_metadata)->dict`.

- [ ] RED TDD on name-aligned ETF pairs with duplicate/misordered columns (fix discovered in R0-G), banked dates and tie sign; verify 21/63 target maturity.
- [ ] **Reuse**, don't refit, R0-G's 8 strictly flipped 21-day pairs and 7+7 ties, 16 changed grades. Audit actual margin in basis points from as-of adjusted Open and whether changes involve positive-return tails. Avoid choosing a return margin after observing model CAGR.
- [ ] Separately record high-variance engineered feature columns and X-only split-node availability; historical boosters are currently unarchived in tracked Test; no claim to know first authentic diverging split. If scores allow, tie X perturbation to material position flips without retraining.
- [ ] Report structural uncertainty and whether a label-target-only intervention could plausibly address X-only sensitivity; if not, prioritize X-side or NO MODEL CHANGE.

### Task 5: One hypothesis-falsifying synthetic experiment only if Task 4 isolates a mechanism (Track B2)

**Files:** `target_redesign_level2_v1/stability_program_v2/synthetic_mechanism_probe.py`, tests `.../tests/test_synthetic_mechanism_probe.py`, contract `B2_SINGLE_CANDIDATE_PREREG.md`.

**Interfaces:** `run_frozen_pairwise_probe(spec_manifest)->{baseline,perturbedX,perturbedY,common_test,top_tail,node_diff}`. Source exact objective/params unless one clearly documented intervention.

- [ ] Select exactly **one** mechanism from Task 4, **before opening target outcomes**: a justified top-tail-preserving *pairwise confidence weighting* **OR** a split/hist near-tie remedy; else write `NO_CANDIDATE`, stop.
- [ ] Preregister numerically: one feature/label perturbation design with true rank reversals and tie transitions (not R0-E's nonreversing +1), distinct synthetic seeds not used R0-E/F/H; groups/months and 3 XGB seeds, 360 rounds, 125 features and exact original baseline parameters. No sweep of max_leaves, rounds, eta, pair cutoff or label bins.
- [ ] RED→GREEN tests and synthetic fitting in *isolated Test only* (after implementation approval); assert no output mixed from real ETF or future labels. Report Top1 stability AND top5/positive-decile capture, predicted exposure turnover, rank-MAD and first divergent split. If stable but tail skill collapses, fail; do not "fix" by selecting another weight after seeing result.
- [ ] If candidate not better in independent synthetic worlds, **STOP**, keep baseline, no financial backtest.

### Task 6: Prepare first clean prospective economic validation package (Track C, later independent approval)

**Files:** `docs/superpowers/specs/2026-10-08-v2-prospective-evaluation-contract.md`; `target_redesign_level2_v1/stability_program_v2/PROSPECTIVE_GATE.md`; external future dated datasets / hash manifest only when available.

**Interfaces:** `compare_full_v2_same_market(base,candidate,cutoffs,vintage)->{cagr,daily_dd,fees,turnover,tail_capture,exposure_delta}`.

- [ ] Declare ***before*** candidate fit the evaluation period, eligible new point-in-time data, allowed universe / membership and 21/63 realized label maturity; if prospective period is too short for credible CAGR, use paired daily/multi-month net P&L and report uncertainty rather than inflated CAGR.
- [ ] Approve together a concrete numeric `epsilon` economic noninferiority and daily-DD guardrail with risk budget; require matched per-vintage outcomes (not best-of-3, not 43% Golden target) and no noncausal corporate-action revisions.
- [ ] Freeze one matched baseline and one challenger, use identical unmodified full MA3/Hybrid/HighCAGR24/V6/Stage19 engine with daily fees, stops and cash BIL/SHV; independent ledger equality and no hidden model change.
- [ ] Evaluate full V2 net economics, exact futures-as-of cohort, top-tail capture per eligible month, confidence/turnover; separate training-vintage instability from portfolio amplification. A bad challenger is **REJECTED**, not silently optimized/retrained on the same holdout.
- [ ] No production deployment without explicit distinct approval and model registry `APPROVED` evidence; if both existing/prospective fit become invalid, `NO_APPROVED_MODEL`.

### Task 7: Separate financial-risk policy review (NOT an additional training fix)

**Files:** `target_redesign_level2_v1/stability_program_v2/RISK_CONCENTRATION_FOLLOWUP.md`; test only if later authorized `test_reentry_state.py`.

- [ ] Use L2-O's actual 2025 concentration and 20 stop occurrences, L2-P disabled market gate harmful repetition; identify whether loss stems from selection, concentrated allocation, no-market-stress stop gate or reentry sequence.
- [ ] Define prospective, state-machine-style **entry / invalidation / exit / reentry** hypotheses, no hindsight cutoff or retrospective 2025 tuning, no immediate code changes.
- [ ] Keep economics/risk and learner stability **distinct approval gates**; neither is claimed to solve the other.

### Task 8: Independent evidence QA and handoff

**Files:** `target_redesign_level2_v1/stability_program_v2/REVIEW_QA.md`; original source map and test execution logs.

- [ ] Cross-check all counted rows/horizons/periods (113 vs 114 months; 2017/2020/2023/2026 four-year factorial; ~2,366 daily full V2); check that sources labelled full V2 vs proxy vs toy are not conflated.
- [ ] Inspect scope diff: `AM1975MA/Test` branch and explicitly no modified `vendor` or productive repo. Run full new focused Python test suite + compile checks, save actual output.
- [ ] Validate manifest, R0-G ticker alignment fix, no future label leakage, costs and no phantom terminal switch, numeric precision; have a second *real* reviewer inspect if callable.
- [ ] Publish honest outcomes: `source verified`, `hypothesis`, `proven test`, `no fit`, `blocked artifact`, `model NO GO/GO to next gate`. Do not assert independent expertise if none ran.
- [ ] Continue only with user-requested future work after review of this written plan and scope; no automatic full V2 financial test.

## Handoff / implementation priority

**First implement Tasks 1 and 3/4 read-only contracts, then minimal Task 2 synthetic parity/integrity as required.** Task 5 is conditional on actual mechanistic evidence; Task 6 is conditional on new financial as-of dataset and separate approval; Task 7 is a separate risk roadmap. This sequencing avoids building an extensive standalone checkpoint system and synthetic experimental suite with no proved relevance to actual capital.

## Stop rules

- If trained historical boosters or exact source files are not present, do not claim reproduction via refit.
- If P1 ledger cannot be reconciled, do not interpret XGB rank/Top1 flips as economic cause.
- If label-only remedy ignores independent X-only instability, don't promote it as complete stability fix.
- If synthetic tail capture weakens, no live real-data challenger.
- If economic noninferiority, risk, cost, or maturity fails prospectively, retain original V2; don't tune based on failed same-period result.
- Never conflate 2025 risk drawdown with the raw-vintage CAGR instability as the same causal phenomenon.

**State:** proposed implementation plan, not executed. Superpowers methodology used; Data evidence review used. Original `docs/superpowers/plans/2026-10-08-v2-xgb-training-stability-research.md` remains a technical experiment ledger, but this is the *new decision-level roadmap* based on the latest full evidence.
