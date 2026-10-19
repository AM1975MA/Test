# G149 — Orthogonal alpha vs volatility: F3 frozen falsification, before seeing G149 results
Date 2026-10-19. Branch `research/149-f3-factor-neutral-diagnostics-20261019`. No model refitting, no economic-switching-parameter optimization, no new backward target search.

### Why
F3 conditional q10/median/q90 **signed benchmark excess** is the most promising research idea, but the 20.02% 2021–26 CAGR still failed its 250 as-of sector+volatility matched placebo (86th percentile, placebo 95th CAGR 23.03%). Before adding complicated multi-horizon mixtures or HMM/physics priors, *directly measure whether F3 encodes any economic direction beyond risk/sector classification*.

### Immutable evidence
Read F3/N4/F2/frozen per-ETF prediction file `research_reset/predict149/signed_value/results/ALL_9536_SIGNED_VALUE_FORECASTS.csv`; join `oasis149.canonical.load_149` original exact 149 prior-close 63d volatility (original 19 feature `v63`), full 64 non-overlapping evaluation anchors; as-of predictions never refit; source roster SHA **must** be equal to archived F3 output. 9,536 ETF-anchor records. Future excess outcomes are used ONLY in evaluation, never in prior-close features or pair matching.

### Strong and interpretable conditional directional test
For each anchor individually, form all unordered ETF pairs within the **same original group** AND with as-of 63d historical volatility ratio `abs(log(vol_i/vol_j))<=.20`. This is a fixed predeclared similarity bandwidth. Compare if higher predicted F3 signed quantile score correctly indicates the ETF that actually earns higher future 21d USD log return (paired 60/40 benchmark cancels). Score concordance 1 if prediction sign matches outcome sign, 0 if opposite, 0.5 if either tied. Equal-weight individual MONTH ANCHORS, not individual pairs (massive pair dependence). Never use future returns to select pairs. Same exact pair set tests three controls: N4 prior top15, F2 hurdle sign+size and N7 prior63 realized vol.
- Primary: mean 64-anchor F3 same-risk/group concordance >0.5 with 95% 3-anchor circular bootstrap lower bound >0.5; and F3−N4 paired improvement 95% lower >0; and each 2021–23 / 2024–26 mean >0.5. Do not change the threshold or select a different stratum ex post.
- Secondary: mean Spearman in each date before and after residualization by as-of group and logarithmic volatility (future residual outcome used for *diagnosis only*, not for fitting or generating trades); calibration of raw F3 q10 and q90 by anchor and era as signed benchmark-relative return quantiles. No claims of future coverage guarantee just from historic 90%.
- The economic 30% CAGR is NOT an optimization criterion here; no strategy is run at all. All source, per-month matched pairs, confidence interval and caveats archived.

Even a positive check would be purely developmental: same 2017–26 survivor universe has been repeatedly explored; this does NOT constitute fresh, prospective, PIT, ETF-broker-executable or USD→EUR consistent alpha. A negative check vetoes further attempts to combine F3 with other preexisting price-only signals on 2021–26 to maximize historical CAGR.

### Downstream paths if genuine residual information exists
Hypothesis H8a: factor-relative return distribution = **causal factor premium** plus **idiosyncratic signed residual** modeled separately, with factor exposures determined strictly before t and option/credit/fund-underlying inputs timestamped as-of. No claim that a future factor return can be known at t.
Hypothesis H8b: quantile calibration (q05,q10,q25,q50,q75,q90,q95) with robust proper WIS/pinball scoring, crossing prevention, and time-local conformal risk coverage checks on matured observations only; financial dependent nonexchangeable series preclude naive coverage guarantees.
Hypothesis H8c: 5/21/63 day competing-forecast hypotheses with fixed horizon weights, distinguish tradable persistence from crisis response with online change-point algorithm, no oracle regime inputs.
Actual validation: freeze one challenger code and predict newly arriving observations, preserve source/PIT timestamps and delays, compare 60/40 and as-of risk/class null. Stop immediately if no independent directional alpha. No changes to `etf_trader`.

References for research direction: Gibbs & Candès 2024 JMLR adaptive online conformal; Retzlaff et al. 2025 PMLR tests of nonstationary time-series interval coverage; Liu & Luger 2026 International Journal of Forecasting quantile scale dynamics and VaR/ES.
