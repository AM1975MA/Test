# OASIS V2: G1 paired economic predictability gate — frozen BEFORE first Action run
Date 2026-10-18; research branch research/oasis-v2-paired-forecast-g1-20261018

## Why this is not another backtest optimization
Four independent deterministic audits [39133850072](https://github.com/AM1975MA/Test/actions/runs/39133850072) established OASIS V1's as-of momentum ranking has virtually zero 21-session skill in normal markets; normal-state real switches lost against incumbents; 100% two-ETF exposure concealed large holding-specific crashes. Thus, NO new optimization of Top5, holding period, fee hurdle, crisis exposure or backtest CAGR is permitted before an independently measured information gain.

## One falsifiable decision problem
At date t, already holding ETF j, is ETF i an **economically significant superior substitute** over the next 21 *tradable US-market* sessions? Outcome in adjusted Open-to-Open log return:
 Y(i,j,t)= [log(Open(i,t+21)/Open(i,t)) - log(Open(j,t+21)/Open(j,t))] - 0.003.
The 30bp pair transition hurdle is an illustrative aggregate cost/turnover allowance, not actual spread or tax. True pair superiority event = (Y>0). "Forecast" is an ex-ante calibrated probability p_t(Y>0). Model can output uncertainty; no automatic switching in G1.

The old OASIS P3 *as-of portfolio holdings* are used exclusively to supply incumbent names for a conditional hold-versus-challenger dataset. No old model predictions, future labels or strategy outcomes are features. For each nonoverlapping 21-session anchor, select up to 8 candidates from the as-of top by a frozen simple 21/63 day price-only screen against each incumbent, and 64 additional deterministic hash-seeded diverse ETF pairs, both within and across the six predefined asset categories. This is a research design, not an unbiased random investor. Train and score all candidate comparisons with identical labels/cost.

## Frozen hypotheses
H0 **NULL_PRIOR**: online completed-label base rate p of advantage after the 0.003 log hurdle, clipped [0.10,0.90].
H1 **RAW_TREND_LOGIT**: chronologically refitted regularized logistic regression using 21/63/126d raw relative trend only (3 features); conservative benchmark.
H2 **FACTOR_RESIDUAL_LOGIT** (PRIMARY PROPOSED INFORMATION MODEL): the paired *within-group peer-adjusted residual* trend and relative downside, 10/21/63d drift acceleration, lagged risk and class-adjusted expected growth, shrinkage logistic L2 C=0.15. It is not a pure Bayesian posterior; predictive probabilities must be calibrated and validated ex-ante.
H3 **REGIME_HIERARCHICAL_LOGIT**: H2 plus group-class indicators and interaction of relative rebound and downside with as-of market return and volatility; stronger model, with L2 C=0.08 to shrink categories to global mean. This approximates hierarchical regularization, not a fully specified Bayesian state-space/HMM.
H4 **STUDENT_T_GEN**: fit **NO future outcomes**; approximate Student-t(df=5) distribution from as-of mean relative residual log drift + empirical 63d paired return vol. Use unconditional fixed shrinkage coefficient 0.25 and predictive 21d sqrt variance; CDF computes p(Y>0). Not a calibrated Bayesian posterior and must compete with H0/H1.
Do NOT choose a fifth more exotic model if these fail.

## Causal rolling fit
- Dates and source: frozen 150 same-vintage adjusted Open/Close histories, selected by completeness over the complete 2017–2026 period (survivorship-biased). Use exact source hash roster \`oasis150/results/frozen/OASIS_TOP150.csv\`, historical \`oasis150/results/frozen/P3_OASIS_CRISIS_ACTIVE.csv\` 2366 US-market sessions from 2017-02-01 through 2026-07-01.
- Anchors every 21 tradable sessions, starting with 2017-02-01; forward-open label horizon=21, all 150 price series have positive opens during period.
- Observation on prior close preceding first entry open; all features known by this close.
- For an anchor at signal close t, fit ONLY examples with **future label's realization next-Open strictly earlier than signal close t**; prevents training on forward returns that have not matured. Fit scaler on training data only. Refit at each eligible anchor. Drop the last anchor with unavailable exit Open.
- Early 2017–2020 data **development-only**; no proper-score evaluation before 2021-01-01. Report both chronological 2021–2023 and 2024–2026 (previously examined and NOT independent holdout), as well as combined 2021–2026. All currently burned as of 2026-10-18; do not claim prospective evidence.
- Pair generation deterministic from as-of information and a fixed seeded RNG independent of future outcomes, with asymmetric incumbent/challenger orientation and constant per-anchor count. Overlapping cross-sectional pair outcomes are heavily dependent; error bars must be calculated at the ANCHOR level, never count thousands of pairs as independent trades.

## Primary and secondary validation
1. Primary: paired **average Brier score** vs H0 on the predeclared challenger-vs-real-held subset (not all random pairs). Secondary: log loss, calibration-by-bin and mean economic log advantage of highest-conviction accepted challengers.
2. H2 must beat H0 and H1 in mean anchor-scored Brier AND predictive log loss; if not, G1 FAIL and prohibit portfolio backtest. H3 wins status only if genuinely improves H2 with the same criteria; do not pick whichever model has an attractive CAGR.
3. Counterfactual opportunity: shadow ACCEPT if p>0.65, predicted relative expected net advantage >0 and model predicted probability exceeds H0 by 0.10; only select *one most confident challenger* per anchor. Evaluate actual net log gain and share positive versus hypothetical holding. Do not convert that to a real portfolio or CAGR.
4. Report Brier/log loss/AUC if applicable, mean class-specific and crisis-conditioned scores, n independent ANCHORS, number of shadow acceptances, concentration of wins and negatives, confidence interval paired anchor Brier difference using 1,500 circular 3-anchor (63-session) block draws. CI including zero => no proven improvement.
5. Null/structure diagnostic: positive G1 skill must be robust in both 2021–23 and 2024–26 exploratory slices and should not be entirely carried by one rare asset.
6. Stop rule: if no positive proper skill, investigate dataset signals/scale at scientific level, but **never** retune this test to force a positive result. In that case focus G0 PIT and G2 standalone capital preservation; do not launch G4 switch strategy.

## Strict limits
Hindsight-conditioned original149+holdout70 excludes dead/unlisted ETFs. Same-vintage back-adjusted Yahoo prices, unknown ISIN venue spread and EUR FX; the "150 most complete" selection explicitly uses end-of-period information. Expected true live EUR advantage not established by success here. This panel has already been mined by OASIS V1, so model evaluation is strictly a *diagnostic developmental step*.

Theory: proper forecast calibration/sharpness per Gneiting & Raftery 2007, https://doi.org/10.1111/j.1467-9868.2007.00587.x; no lookahead using matured labels with purged chronological evaluation. All source hashes and exact per-anchor forecasts, labels, surprise and score receipts must be preserved on this new research branch.
