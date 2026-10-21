# V3 L06.3 — Forecast loss risk conditional on the actual selected Top3 ETFs

**21 October 2026: complete, negative experiment, NOT PROMOTED.** Standalone intrinsic risk skill only: neither expert rank, allocation, risk veto nor portfolio weights are changed.

Successful [GitHub Actions run 39670543932](https://github.com/AM1975MA/Test/actions/runs/39670543932), artifact **12378644359**, `v3-l06-conditional-risk-classification-results`.

## Causal and matching controls

- Frozen 149 ETF risk scores **already genuine OOS** for 2018–2026: original logistic45 global relative risk 39662062361, original Tail45 expert scores from run 39655513813.
- 500 canonical fixed baskets × 24 names; only the basket's top three Tail picks are used as conditional event candidates.
- Predeclared prediction target: whether the ETF ended among the basket's worst **three** realized future 21-trading-day ETF returns. This differs deliberately from the previous 149-ETF bottom10% label. It is a **relative** event, not necessarily an absolute financial loss.
- Annual expanding refit from 2022 to 2026, 53 fully matured held-out monthly signals. Training examples use prior years' already OOS expert scores and only label exits before the annual Jan 1 fit cutoff. The same 21-trading-day next-open SPY trading calendar is used to enforce maturity.
- Overlapping selected ETF appearances across baskets are weighted by inverse count per (month, ETF), so each unique ETF-month contributes total training weight one (not thousands of independent observations). At evaluation, overlapping 500 basket candidates are aggregated by calendar month.
- Compare frozen original global `p_bad` score ranking, train-only one-feature `LogisticRegression(C=.2)` calibration of this probability on the new conditional event, and the two additional inputs `TAIL_ELITE45` and a pre-trade Top3 slot position (0, 0.5, 1) with identical logistic training setup. No hyperparameter sweep, no CAGR or PnL.

## Intrinsic conditional classification (53 later-year months)

| Metric | Frozen original score | Calibrated risk head | Added Tail & slot |
|---|---:|---:|---:|
| Selected-candidate basket-worst-three Average Precision | **0.436831** | **0.436831** | 0.422687 |
| ROC AUC | 0.576819 | 0.576819 | **0.577641** |
| Top 15% risk-flag precision | 0.360040 | 0.360040 | **0.362252** |
| Top 15% risk-flag recall | **0.230523** | **0.230523** | 0.218229 |
| Brier vs basket-worst-three label | N/A, uncalibrated target | 0.194183 | **0.194129** |
| Log loss | N/A | 0.575396 | **0.575280** |

Paired 6-calendar-month circular bootstrap (6000 replicates):
- New minus calibrated: **Average Precision −0.014144**, exploratory 95% CI **[−0.019777,−0.009010]**.
- New minus calibrated: ROC-AUC +0.000823, CI [−0.002134,+0.003600] — no established improvement.
- New minus calibrated: Brier −0.000054, CI [−0.000273,+0.000138] — no established improvement.
- New minus calibrated: top-15%-risk precision +0.002212, CI [−0.018570,+0.019237] — indeterminate.

## Decision and methodological insight

**Reject `CONDITIONED3`**, keep the trained global risk scores as a diagnostic and leave Top3 allocations and winner expert unchanged. The new model is not better at identifying candidate-specific negative outcomes. The conditional model and global-risk model are predicting different events, which is important for interpretation.

Further L06 work should align the actual safety outcome with the strategy's purpose: **predict absolute next-21-trading-day losses (e.g. fixed -10% downside event) and peak-to-trough stress**, not declare the basket's third-worst name to be financially dangerous during broad positive markets. This must be a separately preregistered prediction-only test before any risk decision rule is modified.

Historical 2018–2026 periods have been used extensively in research: these confidence intervals are exploratory, not an untouched future confirmation.
