# ETF_TRADER_PERTURBATION_FORENSICS_V1 — preregistration

Frozen before new causal ablations. Purpose is attribution, not performance optimization.

## Fixed evidence set
- Original149.
- Three already-frozen consecutive Yahoo/yfinance snapshots `_repeat1`, `_repeat2`, `_repeat3` from run 37121749852.
- Canonical source-only ETF_trader V2 source chain, hash-gated to the same blobs used by the controlled replay.
- Pinned recent numerical environment used in the repeatability experiment.
- Evaluation interval and execution contract unchanged from the controlled Original149 replay.

Observed facts entering the forensic (not hypotheses selected after the fact):
- raw perturbations are ppm-scale;
- canonical CAGR: repeat1 29.7534477%, repeat2 30.8437049%, repeat3 34.6770791%; span 4.9236313 pp;
- identical raw bytes reproduce bit/economically identical pipeline outputs across repeated runs and different runners.

## Hypotheses to distinguish

H_CODE_NONDETERMINISM: identical inputs can produce different outputs because of code/hardware/thread stochasticity.
Status entering forensic: strongly disfavored by exact same-raw replay; rechecked where relevant.

H_PREPROCESS_RANK: ppm raw differences are amplified by deterministic feature construction, percentile/cross-sectional ranking, normalization, or other preprocessing before ML fitting.

H_CLUSTER: ppm differences materially alter clustering/persistent cluster state, which then drives the divergence.

H_ML_TRAIN: training the same model family on slightly perturbed feature/target data creates large model/prediction divergence beyond the preprocessing divergence. Includes ExtraTrees/XGBoost fit sensitivity, but not nondeterministic execution.

H_EXECUTION: most economic dispersion is due to slightly different realized OHLC execution prices while decisions remain materially similar.

H_OTHER: risk/stop/allocation/execution state transitions or another deterministic downstream discrete mechanism materially amplifies otherwise modest decision differences.

## Stage amplification map
For each pair (1,2), (1,3), (2,3), compare on the same signal-date/ticker grid where available:
1. raw OHLC and daily returns;
2. raw/non-ranked feature panel values;
3. ranked/cross-sectional feature values;
4. cluster ids and cluster-derived features;
5. TIT_R;
6. ET component;
7. XGB component;
8. final blended score;
9. d1/d2, weight1, margin;
10. risk/execution states;
11. P&L.

Metrics include absolute/relative difference, fraction changed, rank correlation, first divergence, Top1/Top2 disagreement, and a stage-to-stage amplification description. No threshold will be tuned to maximize explanatory power.

## Causal ablations
A. Freeze canonical decisions from one snapshot and execute them on the other frozen raw snapshots. This estimates the execution/raw-price contribution.
B. Execute repeat-native decisions against one common frozen execution raw where technically possible. This estimates decision/model contribution independent of execution-vintage differences.
C. Compare frozen-model scoring versus native retraining where technically possible:
   - frozen model + perturbed inputs isolates preprocessing/input sensitivity;
   - native retraining minus frozen-model effect isolates training sensitivity.
D. Component attribution: BASE/TIT_R, ET, XGB, final blend, allocation/risk.
E. Cluster attribution: compare cluster identity stability and cluster-derived feature drift; do not classify clustering as root cause merely because cluster-derived features differ.

## Lookahead / leakage audit
Static audit of:
- source_only/kernel.py
- source_only/features.py
- source_only/models.py
- source_only/_xgb_worker.py
- scripts/build_tit_r_source_only.py
- ma3/ensemble.py
- ma3/hybrid_producer.py
- ma3/producer.py
- ma3/ddfirst.py
- ma3/v6.py
- vendor/p45/v2_stage19_kernel.py
- controlled canonical replay runner.

Search specifically for:
- negative shifts / future indexing;
- centered rolling windows;
- backward filling that could use future observations;
- full-sample statistics or clustering used for historical dates;
- target columns entering feature vectors;
- training rows whose target maturity date is after the prediction cutoff;
- signal/entry/exit same-session ordering violations;
- future risk or execution information;
- ex-post universe membership / survivorship, reported separately from code lookahead.

Dynamic anti-lookahead tests:
1. FUTURE_MUTATION: alter raw observations strictly after a chosen cutoff; predictions/decisions dated at or before the cutoff must remain unchanged.
2. TRUNCATION_INVARIANCE: full raw history versus history physically truncated after cutoff; pre-cutoff outputs must be identical, except where a documented provider adjustment representation requires a fixed pre-cutoff raw snapshot.
3. BFILL_USAGE: quantify every evaluation-period location where `.bfill()` supplies a value from a future row; zero use is required for a clean pass unless the filled series is proven non-predictive/non-tradable at that timestamp.
4. MATURITY_GATE: for every fitted training row, target exit/maturity timestamp must be strictly before its fit cutoff.
5. EXECUTION_CAUSALITY: entry/open and stops must use only information available by their simulated decision/action time.

## Classification rules
- Technical failures before valid metrics are INVALID TECHNICAL, not evidence.
- Same-input exact reproducibility rejects code/runtime nondeterminism as a material explanation.
- A stage is called a material amplifier only if its divergence increases substantially relative to the immediately preceding representation and propagates to later decisions; qualitative attribution will be accompanied by measured values.
- Lookahead is PASS only when both static inspection and the relevant dynamic invariance tests pass. If a dynamic test cannot be run, report INCOMPLETE rather than PASS.
- Ex-post universe construction/survivorship is a separate research-design caveat, not silently relabeled as code lookahead.

## No-sweep rule
No hyperparameter, threshold, model, seed, feature, or controller is selected because it explains the observed CAGR gap better. Repairs, if later proposed, are a new preregistered line.
