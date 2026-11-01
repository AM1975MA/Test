# OLC14 — fit the ranking, not the backtest

2026-11-01. User authorizes the fitting proposal after OLC13. Research branch only; preserve main and every prior experiment. Parent c7e831cab0934ac7e51ce94ee39b47a2cb875526. This protocol is committed before new learner fits, fitted parameters or new economic outcomes.

## Two questions and explicit scope
A. Can chronological selection among the FOUR authenticated OLC13 target formulas improve the selector? This is bounded discrete target selection, NOT continuous optimization of all possible target parameters. No additional candidate target grid is introduced.
B. Is it better to predict three outcomes separately and fit their combination from historical out-of-sample predictions? Compare cumulative horizons and disjoint increments with exactly matched feature/training populations. This is genuine constrained fitting of ranking weights and curvature, not a fit to CAGR.

No symbolic search, no data downloads, no hidden market-specific formula, no promise of a global optimum. Historical periods have already been examined; nested timing does not restore virgin holdout status.

## Sources and learner controls
OLC11 checkpoint SHA256 6802adb5ee54db9142c49b1ea13511c354b200ee84e3cdf3cae8bbd491275eeb; OLC12 checkpoint 3e1582d60dfea6a86b45d368ddde1c1466d4d1447873de177636b423690bd50a; OLC13 results/source f406f36e0628835dacf5d3ef5fa65d45e77a66f8020dd497465cf0944fdbf99f. Verify member hashes before joblib loading. Use original ordered Hybrid42 inputs and OLC11 whole-group-mature annual training2019–2026. Same imputation, source dates, model parameters and seeds101/211/307. Return RSI forecasts remain frozen. Refit original ET and XGB in2022,seed101,both markets before interpreting new predictions.

Five new elementary targets: C21=r21^1.5,C42=r42^1.5,C63=r63^1.5; I42=percentile((1+R42)/(1+R21)-1)^1.5; I63 analogously for42–63. C21 also serves as first incremental block. Incremental percentile groups must use all members of the exact stored training group. All five heads use the SAME training rows and latest group exit63, even though some could mature sooner. Insufficient future labels never remove candidates from live prediction. Each target has ET and XGB, eight years, three seeds and both markets:480 planned new models plus4 parity fits. Preserve model and input/code hashes per completed batch.

Within each head, average the raw three-seed predictions then form .6*percentile(ET)+.4*percentile(XGB). Maintain per-seed diagnostics; no best-seed selection.

## Common economic task, fixed before fitting
Use U=(L0_21 + q*L21_42 + q^2*L42_63)/(1+q+q^2), q=2^(-21/42). L denotes log return. Each block is counted once; U is a discounted block-utility, NOT a realized portfolio return or CAGR. Discount is piecewise at21-session blocks, not an exact daily exponential integral. No drawdown penalty is smuggled into U. Equal-weight same-date universe is the excess benchmark. Evaluate U regret/top2 excess AND unchanged raw returns/excess/regret at21/42/63, incremental outcomes, negative/bottom-quintile selections and legacy target ranking. Every candidate faces the same endpoints.

## Chronological fitted ranking
Inputs z=(head1,head2,head3), either CUM=(C21,C42,C63) or INC=(C21,I42,I63). Fixed anchors use beta0=(.45,.35,.20), alpha=1. Learned score S=sum beta_k*z_k^alpha, beta>=0,sum beta=1. alpha is a curvature of AVAILABLE PREDICTIONS, not the power of the realized training labels. Candidate alpha={1,1.5,2}; shrinkage lambda={.01,.1,1} toward beta0. No unconstrained leverage or market-specific intercept/weights.

Fit beta with weighted pairwise logistic loss log(1+exp(-5*(S_good-S_bad))) + lambda*||beta-beta0||^2. Pairs include at least one ETF in the realized top quintile of U; weight=min(|U_i-U_j|/IQR(U),3), with zero/tied gaps omitted and nonpositive IQR handled explicitly. Normalize pair weights per month and market, then give EU and USA each50% total weight. This emphasizes meaningful top-selection mistakes while capping individual gaps. Score is not a calibrated success probability.

Annual outer decisions2021–2026. Historical OOS forecasts begin2019. For each outer Jan1 use only dates with the entire outcome group mature strictly before that date, in BOTH markets. Tune alpha/lambda on the latest TWO available prior calendar-year inner validation blocks, training each inner model only on earlier whole-group-mature dates. Require at least8 training dates and4 validation dates per market per fold. If no fold, alpha1/lambda1; if insufficient outer training, fixed anchor. Joint validation criterion is mean(EU Top2 U-excess,USA Top2 U-excess) minus .25*absolute market difference. Equal market weight; report each market separately. Ties favor stronger regularization and alpha closest to1. Refit chosen beta on all available OOS past after inner selection.2019–2020 use fixed anchors, explicitly warm-up, not fitted successes.

For TARGET_SELECT, select one of four OLC13 native-current scores using the same fixed U validation criterion on the same valid historical inner blocks. It is a small candidate menu, no optimized portfolio parameter. Insufficient history defaults ORIGINAL_P15. Chosen formula is common to both markets and frozen for the outer year. Preserve all candidate validation results, selected parameters and max outcome dates. No current/future outcome can influence selection. Perturbation tests must demonstrate this.

## Integration and comparisons
Six variants: ORIGINAL, TARGET_SELECT, CUM_FIXED, CUM_FIT, INC_FIXED, INC_FIT. Compare fitting against its own fixed-head control, and head decomposition against ORIGINAL; never attribute the entire difference to fitted weights. Native current scores are evaluated before all portfolio layers. For integration, use unchanged .4/.3/.3 historical-score memory, power1.1, .475 Return+.525 Hybrid. Each historical signal uses the coefficients known then; changing annual coefficients never rewrites earlier signals. Common support fixed independently of outcomes.

Replay six variants with target50/50, IMMEDIATE/DELAY3/PHASE5, legacy costs.001/.003,both markets=72paths. Add IMMEDIATE LAG1 systemic-input sensitivity for all variants/both costs/markets=24paths. Total96. Original16paths must match OLC13. Risk/exposure/V6 frozen as parent for attribution, not a rebuilt whole-chain optimum. No trading or main change. Primary2021–2024, full/annual and2026partial separately; native evaluation has group-maturity-specific coverage.

## Evidence, robustness, preservation
Native fitted-minus-fixed paired monthly U/excess differences and seed controls; joint EU/USA calendar-block bootstrap6months,4000 draws,seed20261101. Intervals crossing zero are not vetoes and bootstrap frequencies are not posteriors. No pooled score hides damage to one market. Show coefficient paths, parameter boundary hits, sensitivity around solution, train-versus-validation-versus-outer performance and semantic loss. No untouched-test claims.

TDD for target construction, simplex fitting, date/group purging, equal-market weighting, ties, prediction transforms and future perturbations. Reload every new model to reproduce predictions; independently verify selected metrics and path accounting. Review is self-review unless a real second reviewer is used. Save source and compact results on this branch at concrete milestones, complete binary checkpoints in persistent Library with hashes; never conflate manifest commit with full binary upload to GitHub.
