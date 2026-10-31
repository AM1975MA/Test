# OLC-04 — relative deterioration and peer confirmation

31 October 2026. Research only. User authorizes continuation after OLC03. This protocol precedes new fits/results. Preserve main, CL01 opportunities, original protections, fills, costs and actual-state accounting. Every intervention runs identically in USA149 and EU165; no automatic rejection when an interval includes zero.

## Question
Do additional past-price measurements distinguish an incumbent's relative deterioration from ordinary volatility, and improve the economic decision on an existing CL01 proposal? This tests NEW REPRESENTATIONS of existing observed prices, not newly sourced fundamentals, ETF flows or macro releases. It is not a claim that a residual-momentum equity paper validates our ETF gate.

## Frozen comparisons
Use the verified OLC03 checkpoint and its unchanged OLC02 training pairs, including chosen and unchosen proposals from four causal holding policies. Same row IDs, maturity rules, local annual expanding fits, sample weights totaling one per signal month, 2021–2026, targets y21/y42/y63, seeds and model parameters. No model/threshold search.

Three feature sets:
- OLD: archived OLC02 features and models; reproduce saved predictions and paths.
- REL: OLD plus 12 measures of the proposed equal-weight basket divided by the actual incumbent basket: relative log growth5/21/63, 5-versus21 acceleration, relative drawdown63, relative log-price distance from20-session mean, 21-session OLS slope, signed trend efficiency63, positive relative-day fraction21, relative movement on market-up/down days63, distance from previous63-session relative high. Historical basket paths use current known weights fixed over the feature lookback; they are not misreported as actual past holdings.
- PEER: REL plus per-ticker peer and market residual context, aggregated as incumbent level and proposal-minus-incumbent. Peers are up to five other ETF names with highest positive trailing126-session return correlation, at least84 matched observations and at least3 peers; no future returns or outcome-based taxonomy. Use peer residual21/63 normalized by residual daily volatility, residual acceleration, peer positive breadth21, peer momentum63, mean correlation, and local-market residual21/63. The peers are statistical exposure proxies, not independently certified sectors. Residuals are obtained from past-only regression with intercept and slope, not differences inferred from future returns.

All feature histories are truncated at the signal close; forward valuation carry maximum3 local union sessions, never prelisting backfill, never synthetic trade Open. Invalid/missing features remain NaN and are imputed from training only. The full forward state is not used for eligibility. Features for test/live state are computed by the same code as training. Quantify sparse histories and finite feature rates.

## Models and controllers
Preserve RIDGE alpha20 with train-only median/scaling and HGB120 iterations,15 leaves,min_leaf60,l2=10,learning_rate=.05,seed101,early_stopping=False. Two new feature sets imply144 new annual models;72 archived OLD models reused. No new absolute-return learner or opportunity selector.

Run the identical narrow full-proposal direct gate (gross forecast minus cost positive => accept; otherwise HOLD) as a diagnostic, and the unchanged OLC03 UTILITY veto with chronological OOS calibration, scale .05,12 mature signal months, missed-opportunity cost multiplier2 and age/forecast support abstention. Test horizon21 and mean profile21/42/63. Each uses actual holdings and cash state; no discretionary CASH, new ticker search or exposure cuts. Both legacy fee coefficients .001/.003, same conditional stops and V6. OLD versus REL isolates relative-path features; REL versus PEER isolates statistical-peer context. Include CL01 half/original controls. Expected104 paths including controls, not104 independent experiments.

Primary predictive evaluation: same BASE full-proposal action rows with exit<2025, equal-month weighting, mean-squared error against zero/training mean, payoff of refused/accepted proposals and forecast-outcome association. Evaluate all historical action rows secondarily. Primary economic window2021–2024; show2025,2026partial,full active period separately. New model decisions begin February2021. Do not select a different feature set or family for each universe to claim transferability.

## Interpretation and checks
Paired monthly log differences, calendar blocks3/6months,6000 draws seed20261031, same sampled months in both markets. Bootstrap positive frequencies are resampling stability, not posterior success probabilities. No invented significance gate; judge economic effect, downside, cost sensitivity and false veto opportunity losses. All history is reused and model selection remains exploratory.

Tests before implementation: future-close prefix invariance, scaling invariance, no prelisting fill, absent data remains unavailable, self excluded from peers, minimum peer/history support, log-ratio identity, and exact same feature functions on training and live state. Verify training rows and mature exits, independently rebuild NAV/metrics, and compare OLD forecasts/paths to frozen checkpoints. Keep all adverse results; no tuning after seeing outcomes. Review is self-review unless an independent reviewer actually participates.

Legacy fill-at-same-Open assumptions, survivorship and uncertified dividends remain unresolved. New feature arithmetic and backtest parity do not certify live execution. If information remains weak, conclude on the tested transforms only; do not claim impossibility of useful opportunity models.

## Implementation plan
1. Verify checkpoint digests and restore in isolated directory; write failing feature tests then implement causal feature module.
2. Build augmented pairs without deleting difficult rows; validate matched keys and labels; fit REL and PEER with fixed parameters.
3. Plug feature banks into unchanged direct and selective controllers; replay all paired configurations and controls.
4. Independently verify model maturity, future-input invariance, prediction parity, accounting and aggregate metrics; analyze decision-level opportunity costs.
5. Persist code, results, manifest and limitations on this research branch and provide downloadable evidence. No asynchronous work claim and no production merge.
