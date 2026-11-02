# OLC27 — Predicting persistent top-tail leaders with a constrained Top5 decision

2 November 2026. Exploratory research registered AFTER negative OLC25/OLC26, before OLC27 outcomes. Parent OLC26 0b61c9b4c1a1dd10c53451f20551a2315ea3681c; economic/decision baseline OLC20 AUTH frozen at 6c387fac4c2e544bb9dc90f6622cd94faba6d7c2. No modification to main and no trading. This reused 2019–2026 sample is not an independent prospective holdout.

## Question and guardrails
Does a strictly chronological classifier of the top decile of six-month ETF performance help choose among ETFs already shortlisted by AUTH, without promoting retrospective QDVE.DE specifically or destroying the strong USA strategy?

The classification event is not a probability of financial gain. Its calibrated probability must be evaluated on matured out-of-sample dates. Improved average rank IC alone is not an economic result.

## Immutable data
Use exactly archived OLC26 EU_FRAME.csv.gz and USA_FRAME.csv.gz plus OLC20 AUTH scores and OLC19 execution engine. Features available at decision: AUTH FUSION, m63, m126, m252, persist3, and interaction m126*persist3. A market-specific ticker identity, future return, future price, date of maturity or realized result never appears in model inputs. EU momentum requires original observed mask; USA prepared finite-positive only (known original-mask limitation). Missing features at prediction cause fallback to original AUTH Top2.

Target: event=(future126 percentile >= 0.90) computed from actual 126-trading-session future Close rank. Each record has a maturity_date, included in annual fitting ONLY IF maturity_date < Jan 1 of model year. Inference uses the full currently eligible AUTH universe regardless of future label availability.

## Models preregistered
Three fitted recipes plus frozen control:
1. AUTH_ONLY: pooled EU/USA logistic model using FUSION alone.
2. LONG_POOL: pooled logistic model using all six features.
3. LONG_STRAT: two separately fitted logistic models with identical features and hyperparameters for EU/USA.

All use StandardScaler and sklearn LogisticRegression(C=0.1, penalty='l2', solver='lbfgs', max_iter=500, class_weight=None). Sample weights are balanced by market, then signal month, then ticker to avoid a broad universe/date dominating. For STRAT, months and tickers balanced within the market. No parameter tuning on portfolio outcomes, same rule applied to both universes. Require >=12 eligible mature signal months per fitted market. Otherwise use AUTH. 2021 fallback AUTH, later annual fits after strict maturity check. No fit by month or post-observation winner selection.

Negative controls: for LONG_POOL, 3 fixed seeds 27001/27002/27003 independently permute target labels among mature valid ETF rows of same market/signal date within each annual training set. No null replica is a candidate for deployment or allowed to be chosen due to its outcome. Frequencies do not mean posterior probabilities or calibrated p-values.

## Decision action (identical in EU and USA)
On each signal date:
- Compute AUTH Top5 with stable score descending/ticker ascending.
- Keep AUTH Top2 by default. Obtain classifier probabilities for the five (fall back to AUTH when any relevant probability is missing).
- At most ONE swap per month: choose the out-of-Top2 ETF from ranks 3..5 with largest probability and consider replacing the lower-probability member of AUTH Top2.
- Swap only if probability improvement >= 0.05 AND the original AUTH FUSION score gap between the dropped and added ticker <=0.05.
- Never choose a ticker outside the AUTH Top5. Never use future score/target to choose swap. Do not optimize either threshold after outcomes.
- If a swap is authorized, assign its new FUSION score as (old Top2 threshold + 1e-8) so the unchanged adapter selects it with the other Top2 member; preserve all other scores exactly and check resulting Top2. This is a minimal adapter convention, not a new probabilistic score for the entire ranking.

## Evaluation
Baseline AUTH must reproduce all 8 parent economic arrays bit-exact. Every candidate needs candidate-specific rebuilt V6 excluding primary holdings, unchanged OLC20 ALARM/FAST_LOCK3, fees .001/.003. Primary: 2021–2024 HALF matched, CAGR in BOTH EU165+USA149 under the same risk policy. Report adverse results. A candidate counts as common improvement only if CAGR strictly exceeds AUTH for both at fee .001 (tolerance 1e-8 pp). Also require cost stress .003, FULL 2019–2026, 2020 crash, MaxDD, annual turnover, number of swaps, difference in realized top-decile hit rate and out-of-sample Brier/precision (descriptive).

Tests: maturity cutoff, missing support, deterministic null mapping, equal market/month weights, no target leakage, Top5-only and single-change rule, score and V6 parity, independently reconstructed NAV intervals. Train/test data overlap at the 126-day horizon is acknowledged; maturity strictness, not arbitrary random split, is the safeguard.

## Research limitations
First view of these years is not a holdout; top-decile accuracy and score Brier are not investable alpha. No intraday bid/ask, original USA observed-mask, delisted universe, total-return/FX completeness or auction-fills certification. No automatic promotion even with higher CAGR.
