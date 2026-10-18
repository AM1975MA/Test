# OASIS — implementation, Action evidence and research decision | 2026-10-18

## Saved in repository
- Isolated branch: `research/opportunity-crisis-switching-20261018`; do **not** merge into production `etf_trader`.
- Full scientific line: `oasis/SCIENTIFIC_ARCHITECTURE_V0_1.md`.
- Before-result frozen executable protocol: `oasis/EXPERIMENT_V1_FROZEN.md`.
- Model and conditions: `oasis/observers.py`, `oasis/switch_contract.py`; daily portfolio engine: `oasis/daily_backtest.py`; unit tests `oasis/test_daily_engine.py`, `oasis/test_switch_contract.py`.
- Executed Actions: initial `39123868147` (failed integrity gate on sparse data); `39123924683` (completed initial); `39124068263` (fee-fair daily-greedy fix); **`39124549957` (final corrected incumbent-missing-close semantics; SUCCESS)**.
- Audited permanent archived source: `oasis/results/frozen_daily_corrected/`. SHA256 ledger manifest `SHA256_MANIFEST.txt`, full 7 daily portfolios `P*.csv`, `MARKET_STATES.csv`, `RESULT.json`, `DIAGNOSTIC_CORRECTED.json`.
- Crisis opportunity diagnostic Action [39124433434](https://github.com/AM1975MA/Test/actions/runs/39124433434), file `research_extensions/oasis_crisis/RESULT.json`. This diagnostic was run on the previous completed selector before missing-close fix; its *pure score cross-sectional correlation* and as-of state classification are unchanged by the execution fix, but its reported switch win/loss examples refer to the SUPERSEDED earlier portfolio. Do not mix its actual-switch figures with corrected results.
- Final archive Action: [39124744355](https://github.com/AM1975MA/Test/actions/runs/39124744355) SUCCESS.

## What V1 actually implements — and what it does not
- Active daily as-of close signal and next-open execution on 2,389 shared research sessions, 2017-02-01 to 2026-07-01.
- Factor-adjusted 21/63/126-day relative efficiency **heuristic** with 126-session rolling beta, conservative volatility penalty and 21d predictive horizon proxy, NOT a statistically calibrated optimal Bayesian posterior.
- 63-session paired return volatility used to compute a conservative uncertainty proxy, one-sided 95% Bonferroni multiple candidate penalty, 30bp hypothetical round-trip hurdle and minimum five-session hold in the alpha switching arm.
- Causal approximate Gaussian-mean BOCPD and filtered two-volatility-state HMM for market crisis and recovery. Crises result in 50% hypothetical zero-yield cash, recovery full equity.
- Long-only two ETF portfolios in most arms, share-level accounting, actual observed Open fills, accounting for 10bp one-way fees, missing orders and value mark only for held positions with stale prices no older than five observations.
- Scientific issue fixed: missing historical Close for incumbent must **never** trigger arbitrary replacement or 2-for-2 switch. Regression tests added; no parameter change to engineer favorable returns.
- V1 does NOT yet implement genuine independently calibrated Student-t predictive densities, regime-conditioned residual forecasts, BOCPD per ticker, survival/hazard opportunity lifespan, production EUR cash products or realistic bid-ask/spread/market impact, and cannot certify investability.

## Matched daily-open economics — final corrected 39124549957
| Policy | Net historical CAGR | Daily MaxDD | Daily Sharpe | Name switches |
|---|---:|---:|---:|---:|
| P0 Monthly same independent raw-price selector | 7.142% | -33.231% | .372 | 97 |
| P1 Daily greedy, no hysteresis, no gratuitous rebalance | -6.674% | -66.073% | -.375 | 889 |
| P2 Daily conservative cost/uncertainty-aware switching | 8.373% | -36.816% | .425 | 49 |
| **P3 Complete OASIS price-opportunity + crisis overlay** | **8.722%** | **-24.196%** | **.497** | **49** |
| P4 P0 monthly selector + crisis overlay only | 7.796% | -25.106% | .454 | 97 |
| P5 naive daily Top5 hysteresis | 2.857% | -33.783% | .154 | 301 |
| P6 P2 economic + BOCPD jump-veto | 8.373% | -36.816% | .425 | 49 |

Matched capital curves, 10bp per SIDE, no leverage. P3 vs P0 incremental historical CAGR +1.58pp, daily drawdown ~9.04pp less negative; however P3 minus P0 paired monthly mean log gain .001208, 95% exploratory 12m circular bootstrap **[-.003119,+.005791]**, INCLUDES ZERO. No evidence of deployable alpha. Older R_H/H7 ML baselines were calculated under a different calendar/execution path; do not rank them in same table as directly parity verified.

## Critical as-of crisis attribution
P3 vs P0 total historical log-wealth uplift .137743, with phase contributions:
- BREATHING 2,046 return intervals: +.177067
- SHOCK 83 intervals: +.197758
- CONTINUATION 63 intervals: **-.129986**
- RECOVERY 196 intervals: **-.107096**.
Those are *cumulative relative log-return units*, **not annualized percentages**. Phase intervals are historical, depend on the model's classification and do not represent independent samples.

Just 3 of 49 P2 economic name switches happened in 146 sessions classified as active SHOCK/CONTINUATION (46 elsewhere). **The model is NOT YET an effective active crisis opportunity rotator**. P6's extra change-point veto had exactly zero effect on every wealth observation, so has no demonstrated marginal benefit. Defensive overlay helped initial shocks, but continuation and recovery caused loss of relative value. It is NOT correct to deploy a binary 50%-cash crisis flag as a universally successful rule.

## Price-signal predictive adequacy (exploratory ex-post audit from prior selector)
The factor-adjusted signal itself was unchanged by the missing-incumbent fix. Across dates, average cross-sectional Spearman(score vs next **21-session** ETF return):
- BREATHING +.0134 (2006 days, heavily overlapping labels)
- SHOCK -.0372 (81 days)
- CONTINUATION **-.1791** (61 days)
- RECOVERY +.0071 (193 days).
Thus score has essentially no positive rank predictive validity in ordinary markets and appears anti-correlated in sustained crises on this sample. This goes directly against the intended opportunity-discovery mechanism. The ex-post daily correlations are not independent samples or valid p-values; do not infer universal negative predictive power.

Correct next research direction is **conditional relative residual return forecasting calibrated by regime**, not more hysteresis tuning on EUR60. In a downturn, latent resilience/leadership transitions and recovery hazard must be separately modeled. Test proper prequential predictive log scores/coverage and actual economically valuable relative switching with an independent PIT fund set before modifying cash/threshold controls.

## Data quality and research classification
The archived daily 60x2389 panel contains **4,189 zero-Volume records**, exact operating venue currencies/ISIN uniqueness/PIT births/delistings unverified. Actual spreads and zero-yield EUR cash placeholder not validated. Historical cohort is the 2026-selected EUR60 survivor group that has been repeatedly studied; prior results include possible adjusted historic Open and no true bid/ask executable prints. The source data's zero-Volume observations make fills at observed Opens unverified. Results are `RESEARCH_EXPLORATORY_ONLY`, NOT live-validated expected returns or an actual advisory portfolio.
  
No original production or prior experiment files were modified. Earlier flawed V1 archives deliberately retained for forensic version provenance; only `frozen_daily_corrected` is the authoritative final V1 economic result.
