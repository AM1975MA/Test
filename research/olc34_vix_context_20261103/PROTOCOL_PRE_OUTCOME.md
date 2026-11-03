# OLC34 — Option-implied volatility as new external ex-ante context (PRE-OUTCOME PROTOCOL)

Preregistered: 2026-11-03. **This protocol is written to GitHub before fitting or evaluating the OLC34 augmented model.** Research only; do not change OLC33, main, live capital or archived models.

## Fixed input provenance
- ETF outcomes/features: exact OLC32 corrected `OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz`, SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16`; parent OLC32 commit `3717924`.
- Baseline OLC33 model: frozen pre-outcome protocol commit `05b1d17` and run committed as `8cf230b`; no retrospective modification.
- **Independent externally sourced variable**: Cboe VIX daily CLOSE, market-derived from S&P 500 options, from open source dataset `datasets/finance-vix`, file `data/vix-daily.csv`, pinned Git blob `c05e0d9c28ddf3b98d0531017ef5b5180df05ae1` (source attribution Cboe, mirror at https://github.com/datasets/finance-vix/blob/main/data/vix-daily.csv). VIX is not independently new information if already indirectly reflected by FUSION: the measured question is **incremental** conditional value, not independence of market processes.
- Strict causal VIX as-of: for ETF signal date D, choose the most recent U.S. VIX CLOSE with observation DATE **strictly earlier** than D (never same-day CLOSE). Require age <=7 calendar days, positive finite close, and at least 21 prior VIX trading observations. Derived VIX level and `log(vix_close / vix_close_21_prior_trading_sessions)`; no backfill from later data, forward-fill beyond 7 days or period-end values. Identical feature treatment for EU and USA, retaining separate dates where signals differ. Freeze input snapshot and content digest in repository. NO original ETF labels consulted when generating VIX features.

## Prespecified hypothesis
H0: adding VIX level and its 21-session log change does not improve probabilities of *economic extreme* (challenger rank2–5 beats AUTH Top1 by >=300 log bp **after** a flat 20bp hypothetical switch cost) beyond prior OLC33 features and unconditional training prevalence, both EU165 and USA149.

H1: pooled regularized classifier augmented by these two external contextual features lowers forward-year probabilistic error and identifies enough profitable interventions after costs, with no worse severe losses.

## Matched annual prequential experiment (2021–2026)
**P0**: OLC33 weighted historical event prevalence; **P1**: OLC33 `StandardScaler + LogisticRegression(C=.1,solver=lbfgs,max_iter=1000,random_state=33001)`, 12 ETF contrast/context features; **P2**: same model and fixed hyperparameters PLUS **two VIX features**, using VIX in natural index points and log-change in dimensionless units; scaler learned only on train. No grid search, target tweaks, ticker/market ID, calendar year as feature, crossover feature selection or alternative thresholds. Match identical model eligibility rows and matured training labels for P1/P2 and P0. All ETFS, train weights = equal weight markets, each month equal within market, alternatives equal within month. Fit at Jan 1 Y exclusively on data with **both** challenger/incumbent corrected exit_date < Jan 1 Y. All predictions performed with no use of future labels. Fallback P0 for years lacking OLC33's training conditions (>=12 mature months for both regions and >=20 positive labels).

**Predictions**: one forecast per AUTH rank2..5 candidate for each market/signal date. Keep rows with missing labels in prediction files. No filtering eligibility by future returns or `eligible_label`, `eval_valid`, `label_valid`, `exit_date` for choosing candidates. If VIX absent or ETF feature missing, no switch, record explicit missing reason. EU source-observed mask and repaired 2020 dates, USA merely prepared, 2026 terminal labels missing; same as OLC32/33.

**Frozen action rule:** each date select max predicted P2 among challenger ranks2–5 (tie: smaller rank, then alphabetic ticker). Switch only if P2 >= 0.40 **and** P2 − P0 >= 0.10; otherwise keep Top1. Compare unchanged OLC33 P1 decisions using precisely the same input dates, labels and scoring convention. Net = log-bp spread minus fixed 20bp if switched; **no claim of executable trading or certified transaction cost**.

## PRIMARY GATE: years 2021–2024; no winner selection using 2025–2026
All of the following are necessary to proceed:
1. **Brier error improvement** for P2 vs P1 AND P0 **separately in EU and USA** on matched eligible Top5 pairs, macro averaged by signal month. 6-month calendar-block bootstrap *paired across markets* (2000 draws; RNG=34001) of monthly (P1 minus P2) Brier improvement: joint 95% lower bound >0. This is descriptive, not data-snooping-adjusted.
2. >=12 executed, evaluable monthly switches **per market** under fixed P2 thresholds; among switches, >=1.5× positive Y+ event frequency of all otherwise unselected challenger pairs in same market/sample.
3. Positive mean **incremental** net log-bp vs Top1 across all evaluable months in each of EU and USA, and positive mean net log-bp *relative to the frozen OLC33 action series* in both.
4. Joint EU/USA 6-month block bootstrap on incremental net log-bp vs Top1 must have 95% lower bound >0, seed=34001.
5. Share of severe negative switches (net <= -300bp) <= severe-loss incidence of otherwise unselected challenger alternatives in each market, and no unresolved data-integrity/causality failure.

If ANY gate fails, STOP: **no threshold fitting, no additional models, no promotion, no strategy NAV or claims of profitable edge**. Record full failures, predictive and economic results and input checks. Do NOT treat reused 2021–2024 or previously inspected 2025–2026 as independent holdout. An actual forward holdout begins only with first new future monthly source-complete signals after protocol, with timestamped/frozen forecasts before outcome.

## Audit
- Verify VIX pinned blob, source/date alignment, calendar closure audit, no duplicate (market, signal_date,ticker), ETF SHA, VIX strict lag and max age.
- Reproduce exact P1 and P0 OLC33 forecasts/decisions on overlapping rows to numeric tolerance 1e-10, and write unmatched cases explicitly.
- Alter outcomes after 2024 cutoff: forecasts through 2024 unchanged; 2025 forecasts may legitimately change.
- Preserve raw source provenance and file hashes; save full prequential forecasts, action records, per-market evaluation, bootstrap draws and summarized gate outcomes in research-only branch `research/olc34-external-vix-20261103`.

**Data limitations:** ETF survivorship, USA observed masks absent, dividends, FX, actual tradability of opening quotes, live intraday timing, VIX vendor revision history, and sample repeatedly explored across OLC01–OLC33. External VIX data is one independently sourced feature set but DOES NOT create fresh independent ETF outcomes.
