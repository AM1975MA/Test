# ETF Trader V2 — Revised Model Lifecycle & Training Stability Design (v2)
**Superpowers design revision · 2026-10-08 · proposal for review, NOT authorization to implement.**

**Project:** `AM1975MA/Test`. **Development branch:** `research/v2-xgb-immutable-checkpoints-20261008`.
**Supersedes the intent**, not the history, of `docs/superpowers/specs/2026-10-08-etf-v2-checkpoint-integration-design.md` and its original checkpoint-only plan. The old artifacts remain intact as evidence. **No change to `Etf_trader`, `Trader_selector`, or `vendor/etf_trader_v2` until a subsequent separate approval. No prior financial tests repeated.**

## 1. Correction of the original goal

**Wrong implicit interpretation to avoid:** a frozen trained XGBoost is a solution to the sensitivity of training; or it ought to be used indefinitely when new tickers/time periods arrive; or it ought to be preferred merely because an old historical CAGR was high.

**Actual goals, in order:**
1. Identify and independently reproduce *any* fitted model, its exact as-of input labels/features/grouping, all parameters/runtime/source, and historical predictions (**provenance/reproducibility**).
2. Accommodate **new signal dates, updated labels, changed eligible ETF universe and legitimate market changes** through explicit, causal, versioned new model fits; never silently refit a historical model on revised provider past.
3. Make annual XGB training **intrinsically less sensitive to economically negligible historical data perturbations without materially impairing the ability to select extreme winning opportunities**. Existing evidence points at Compact21 training X and labels, but does not demonstrate specific split-node pathology or an established cure.
4. Select/reject a new model via a **pre-specified, prospective champion–challenger gate**, not ex-post selection of the vintage with highest realized CAGR.

**Track A (engineering)** makes Tracks B's experiments inspectable. **Track B (learning stability)** is the economic research objective. They are separate deliverables with distinct exit gates. There is NO claim the checkpoint by itself improves prediction robustness, alpha or historical CAGR.

## 2. Three explicit operating modes

### REPLAY (audit historical state)
User supplies checkpoint ID, training vintage, universe ID, source/runtime identity and archived input. Load exactly that fitted model. Verify all file/input/schema/sha hashes and prediction provenance; do not train. If missing, state **NOT REPRODUCIBLE** rather than recreating a historical model with fresh 2026 data and calling it authentic. Legacy score-only material remains marked legacy (not a recovered booster).

### PREDICT (new date with old valid fitted model)
Given a supported model cutoff and **as-of** newly available OHLCV/features/cluster state, generate new scores **without training**. New inference `Xte` invalidates *prediction cache* but not *fit checkpoint*. Explicitly log as-of feature eligibility, unknown categories, missing history and current universe compatibility. A saved model may technically score unseen ETF tickers when ordered feature schema and feature construction are compatible; that is **not** proof the model is appropriate for the enlarged universe. Never use future data to construct past feature/cluster states.

### REFIT (new annual cutoff, genuine updates, or changed universe)
Create a **new immutable model ID**, using only training rows and labels mature as of the training cutoff. Record universe as ordered membership, eligibility definition, ticker mapping, category mapping and cluster construction contract. If universe changes and rank-percentile labels depend on the candidate universe, recompute labels causally from that version; **never** compare different universe runs as a matched stability test. Retraining from scratch remains a valid **control**, not banned by checkpoints. Do not silently replace original checkpoint, and do not use automatic training on a vendor raw-history correction as if a new year of economic information had arrived.

Two cases: (i) legitimate annual update within the same universe -> incumbent and challenger may be compared on same economically future interval, (ii) new ETF universe -> separate development identity and matched baseline *retrained/evaluated under that same new universe*; carry-over predictions from 149 allowed only as a labeled zero-shot diagnostic.

## 3. What to do when the NEW training is worse

Maintain **incumbent ("champion")** and **new candidate ("challenger")** concurrently; original training state and raw-as-of bytes never overwritten.

**Causal approval policy:** register the evaluation rubric **before observing challenger outcomes**, based on predictions/trading outcomes available after both models' respective fit cutoffs. Use time-split/rolling-origin or forward shadow paper period with fees/daily risk engine and only mature labels. No model selection using 2017–2026 "winning vintage", retrospective Golden 43.146%, or the three Yahoo re-downloads as independent holdouts.

If challenger violates the predefined economic/robustness guardrails, **REJECT** challenger and retain incumbent for the period for which incumbent remains valid. Retain drift, training-age and universe-compatibility alarms; if both models cease to be valid (e.g. unsupported universe) the system must declare **NO APPROVED MODEL** and require a new qualified fit, not indefinitely reuse a stale predictor. Manual review is allowed; no automatic risk/position change in this project.

**Do not demand impossible guarantee** that CAGR never declines in future. The gate must separately constrain: worst matched-vintage full V2 CAGR and per-vintage degradation, daily MaxDD, cost/turnover and worst outcome tail, top-opportunity capture, effective portfolio selection disagreement and prediction stability. Numeric tolerances must be approved **before** any new financial test; previous studies did not establish a universal optimal trade-off.

## 4. Track A architecture — identity + version control, not freeze forever

Research-only package `target_redesign_level2_v1/checkpoint_contract_v2/` and future MA3 component.

- **FitIdentity**: `universe_id`, as-of cutoff, actual train X/y/group per horizon, row IDs/mature exit dates, ordered 125-feature schema, fixed `rank:pairwise` hyperparameters, 360 rounds, seeds 101/202/303, preprocessing and cluster snapshots, source code/blob/runtime fingerprints. **Training and inference data have DIFFERENT identities**.
- **PredictionIdentity**: model digest + ordered as-of `Xte` features, ticker/date eligibility keys, inferred version and prediction settings. Only prediction cache changes when infer inputs change.
- **UniverseIdentity**: ordered ETF population, point-in-time membership/effective date, mapping/corporate-action contract, ranking label denominator / cohort, cluster-feature eligibility; a new ticker may require new training regime but cannot contaminate old backtests.
- **Model lifecycle**: status `LEGACY_SCORE_ONLY` | `CHECKPOINTED` | `CHALLENGER` | `APPROVED` | `REJECTED` | `RETIRED`, with date and explicit references, never overwrite successful artifacts. Content-addressed checkpoint writer fails closed on mismatch or race; creating a **new** fit on a **new valid ID** is allowed.
- **Security**: sha256 is for integrity, not authenticity; lock/atomic no-clobber, symlink/path traversal controls and full snapshots. A flag stating labels mature is not proof: **verify each label exit before fit cutoff**. Store saved models and env, not pickle untrusted data.
- **MA3 reality check**: Compact21 booster checkpoint alone cannot reproduce V2. Freeze MA3 ExtraTrees, XGBRegressor, fitted imputer and PCA/KMeans/cluster membership/versioned state in a later separate design. No production promotion claiming "V2 stable" on a partial checkpoint.

## 5. Track B — diagnose and improve the **training process**, not smooth predictions

Known experimental facts, **already exhausted**:
- Exact same-input replay is deterministic; perturbing inference only on fixed trained model gives Top1 disagreement 0% in prior four-year diagnostic.
- Change **training X** with labels held constant -> 62.5% Top1 disagreement; change **training y** with X held constant -> 58.33%; joint train difference 43.75%. These are **non-additive**, and not a node-by-node proof of which split is responsible.
- Tiny ~0.05–0.07% changes in discretized pairwise relevance labels can alter fitted ranker dramatically. Ridge/HGB/Fourier, Q4 feature rounding, L50 label coarsening, bootstrapping, consensus, multiple blends/sleeves and stop/volatility adjustments already tried and did not meet joint economic/stability requirements.
- Annual historical 43.146% Golden vs fresh 31.604% same-source is a **vintage effect**, not solely an XGB training causal attribution; clusters and execution prices also matter. Do not attribute entire ~11.54pp to XGB alone.

**New hypothesis-screening sequence, deliberately NON a fishing expedition:**
1. **Observe what changes inside trees** using saved tree dumps and causal new training snapshots (if old native booster dumps unavailable, state this; do not claim old exact split comparisons). Compare first divergent tree/node/threshold, gain margin for near-tied splits, histogram cut placement, groupwise pair gradients and resulting 149-ticker score differences. Separate feature perturbation, label perturbation and category/cluster propagation using EXISTING prior findings. NO new fitting for a task framed merely as reading existing artifacts.
2. Build **counterexamples on synthetic controlled grouped data** to falsify mechanism (identical order/data deterministic; tiny X/y changes with/without ties; confirm whether structural margins track output sensitivity). No real Original149 rerun for probing.
3. Before ANY financial new experiment, choose **at most one causal intervention** based on (1)–(2), preregister against a genuinely new acquisition / prospective observation:
   - **Candidate 1: fixed-tree topology + leaf refresh on legitimate new labels**, using DMatrix for update; source L2-Q synthetic showed it runs and preserves splits, **not** that it preserves opportunity alpha.
   - **Candidate 2: stable split-selection/cut/near-tie resolution** only if identified at the **specific divergent split**. This is NOT Q4 feature rounding, L50 target bins, HGB swap, Ridge smoothing or blanket bagging. Needs XGBoost integration feasibility check before allocating financial testing effort.
4. On prospectively new as-of periods, separate `Top1 agreement` from **economic influence of changed positions** (exposure-weighted P&L/decision regret), and preserve selection skill on high-upside tails. If no novel mechanism can be established, stop; do not conduct new candidate search on burnt history.

## 6. Training-cycle invariants and evaluation gates

- **Annual causal fit** uses only `signal_date < Jan 1 of fit year` and `exit_date_h < cutoff`; new universe changes labels/features only on information available as of cutoff. Require >=30 nonmissing canonical features and original source-only maturity/eligibility rules; never backfill future membership or historic Yahoo 2026 revisions as original point-in-time observations.
- **Same-universe matched comparisons** use identical actual trading calendar, adjusted OHLC data vintage, daily execution kernel, risk policies, transaction fees, ranking and eligible securities. Original149 2017–26 is *development history*, not a legitimate future holdout.
- **Full V2 mandatory** for future financial release: CAGR **per acquisition**, worst-case and dispersion, daily MaxDD, Sharpe, turnover, transaction fees, concentration, tail opportunities, selection changes and risk events; golden 43.146% remains a different historical provenance.
- **Three failure paths**: poor challenger -> keep compatible incumbent for defined validity window; expired/unsupported incumbent -> no approved model; incomplete data/provider revision -> fail closed and preserve as-of provenance, not silently switch/retrain.

## 7. Work packages and delivery order

**Package A1 — immutable model + train/prediction IDs, synthetic parity**: no financial fitting; implements TDD contract and ability to build new versions, unlike former 'freeze-only' pitch. Requires prior separate plan review. **A1 exit is engineering-only, not 'problem solved'.**

**Package A2 — annual model lifecycle and universe compatibility**: REPLAY/PREDICT/REFIT APIs, as-of ETF membership and label contracts, two-version cache coexistence, incumbent/challenger registry; synthetic tests and no real trading policy changes. Separate TDD plan/review following A1.

**Package B1 — training-instability mechanisms and one non-redundant candidate**: artifact inventory, pretrain on synthetic, split-diff instrumentation, fixed-leaf option only if supported; economic gates fixed before new prospective outcomes. Does not require A2 full UI but DOES require A1 auditable source identity.

**Package B2 — independent economic validation**: new prospectively collected as-of windows, one locked candidate vs original matching baseline, full V2 engine; requires new pre-registration and explicit user release approval. NO automatic path from A1 to B2.

**Package C — MA3/KMeans state lifecycle**: separate specification before calling V2 fully reproducible.

## 8. Superpowers decision gate

This revised document directly addresses user's questions about future dates, new tickers and bad new fits; it is a **design proposal for review**, not implementation consent. The original plan `2026-10-08-v2-xgb-immutable-checkpoints.md` is incomplete as a project roadmap; write **two separate revised plans A and B** with independent scopes. Request user review of the revised design and plans before dispatch/execution; do not claim independent agents were invoked unless a dispatch tool actually ran.

### Source reference index
- `vendor/etf_trader_v2/src/etf_trader/source_only/models.py`, `_xgb_worker.py`, `ma3/hybrid_producer.py`
- `forensics_v1/results/COMPACT21_XGB_FORENSIC_V1.json`, `target_redesign_level2_v1/L2D_RESULTS.md`, `L2G_RESULTS.md`, `L2H_RESULTS.md`, `L2J_RESULTS.md`
- `target_redesign_level2_v1/L2Q_SUPERPOWERS_CHECKPOINT_RESULTS.md`
- `gap_analysis/results/BASELINE_LINEAGE_DECISION.md`, `compact21_stability_v1/results/FULL_REPLAY.json`
