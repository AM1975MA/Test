# COMPACT21_FLIP_REGRET_V1 — descriptive investigation protocol (2026-10-09)

## Question and locked inputs
On which exact dates do the frozen 2017–2026 Compact21 BASE rankers trained on three separately acquired Original149 snapshots disagree about Top1, and are these disagreements due to weak score margins or divergent confident decisions? How large are the ex-post *cross-sectional* 21-session forward-return differences between their picks?

Inputs: ALL ten validated annual attribution artifacts from GitHub Actions run 37916159772, one common-repeat2 score vector for each (date,ticker,vintage,variant); finalized independently in recovery 37931212920. Frozen original source Repeat2 `TI_COMPACT.parquet` from run 37150436612, SHA256 as `compact21_semidev_v1.run.FROZEN_TI["2"]`. No acquisition refreshing, predictor fitting, allocation/model retuning, trade/rebalance simulation, future-data selection or changes to portfolio logic. The explored Original149 history is not a holdout.

## Cohorts / choices
Reconstruct full monthly common prediction surface for each variant in `BASE_NATIVE`, `OWN_X_R2_Y`, `R2_X_OWN_Y`. Require 114 query dates and 16986 per-vintage prediction keys, exact common universe across variants and vintages, no duplicates/nulls/nonfinite scores, and all 10 annual result contracts `COMPLETE`. Enforce exact Repeat2 source keys/outcome agreement on (signal_date,ticker), rejecting unmatched keys. Source outcome `exit_date_21` must be after signal date, target return `fwd_ret_21` must be finite and label mature (exit <= 2026-07-01) before used for any return metric. Inference stability includes the final immature date, economic diagnostics omit it.

Within each date/vintage/variant, tie-break scores descending then ticker ascending (fix before looking at outcomes). Define raw Top1-Top2 score margin and **normalized margin** = (score1-score2) / (cross-sectional score Q75 - score Q25) on that date/vintage/variant. If denominator is zero, report margin as missing (never call it near tie silently). The margin only compares scores from that model/date; score scales across separately fitted models are never assumed comparable.

## Diagnostic bins fixed ex ante
For each date × pair among (1,2),(1,3),(2,3):
- same Top1 or flip;
- if flip: `min_margin` = minimum of two normalized margins. Declare weak-margin if <=0.1; clear-margin if both >0.1. Also report sensitivity of counts for thresholds 0.05, 0.2, no threshold tuning or promotion.
- If both picked instruments have a mature finite forward return on the **same Repeat2 outcome panel**, report their absolute 21-session realized simple-return difference in **percentage points** (100 * abs(r_a-r_b)), and signed pairwise difference 100*(r_a-r_b). Report medians, p90, and fraction >1pp, >5pp among eligible flip pairs. This measures *observed ex-post divergence of two candidate choices*, NOT a trading strategy's CAGR or counterfactual benefit of detecting a flip in advance.
- For all query/date/vintage choices with mature fwd_ret_21, report mean realized Top1 target percentile and simple return, plus number of date observations; never annualize these means into a CAGR.
- Report near/clear-margin conditional flip rates over all date pairs and flipped pairs, and actual counts not just percentages. Retain per-date/pair evidence for audit and year-level split.

Return availability/exit maturity cannot be inferred from score or target_rank alone; fail if the necessary original return column is absent. Feature score margin is a hypothesis diagnostic, never a model-quality gate.

## Sanity controls
Independently recompute all-base variant pairwise Top1 disagreement from physical vectors and compare to the original `per_variant` annual metrics and independent recovery summary; include 114 dates, 3 pairs, 342 date-pair comparisons per variant. Frozen source SHA and original annual result sha for all 10 must be recorded. Retain exact result/protocol identity and source hashes. Fail on corrupted artifacts, coverage changes or nonfinite scores. Test synthetic near/far ties, ticker tie breaker, maturing-exit exclusion and return-difference units.

## Decision
Output an audit document and machine-readable metrics. Do **not** select a new decision rule, claim improved stability/CAGR, optimize thresholds, or promote a model from these diagnostics. Only after inspecting these results specify the *one* next model candidate to test with frozen stability and quality gates; only a quality-preserving candidate may advance to three-source unchanged full economic replays (CAGR/MaxDD/turnover), and then genuine independent forward validation.
