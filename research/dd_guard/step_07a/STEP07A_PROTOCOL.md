# STEP07A — adaptive local-scale + daily competing-hazard controller

Date: 2026-08-31

## Research question
Can a genuinely earlier, ticker/basket-local normalized state plus daily competing crash/recovery hazards produce a visibly better DD frontier than the frozen FUSION1/STEP06K family, rather than another incremental q30 refinement?

## Scientific boundary
- 2023+ remains sealed during development.
- No GitHub Actions.
- Inputs are frozen Treatment Value HGB paths (500 baskets, 2366 daily observations), the frozen transition panel, and frozen systemic raw series.
- The exact ticker identity is not embedded in the DD-guard path archive. Therefore the primary normalization is **basket/local-strategy adaptive**, which automatically follows the volatility scale of the currently held HGB path. This is the closest exact reproducible test of the per-ticker-scale hypothesis available from frozen inputs. If this fails strongly, exact ticker identity is unlikely to rescue the architecture; if it passes, exact ticker-level normalization becomes a follow-up audit, not a prerequisite.

## Adaptive stress state
For basket b and date t:
- `sigma63`: trailing 63-session stdev of HGB daily returns, min 42 observations.
- `S21 = sigma63 * sqrt(21)`.
- `zdd = current HGB drawdown / S21`.

A stress episode starts causally when `zdd <= -1.0` after the prior session was above -1.0. At episode start t0 freeze `S0 = S21[t0]`.
The competing endpoints are fixed in local-risk units for that episode:
- RECOVERY when HGB drawdown >= `-0.5 * S0`.
- CRASH when HGB drawdown <= `-3.0 * S0`.
- censor after 63 sessions if neither endpoint occurs.

Thus no universal raw -3/-5/-7.5% threshold defines the regime.

## Daily hazard rows
Every active episode contributes one causal state row per session until the first endpoint/censoring. Two cause-specific next-session logistic hazards are estimated:
- `h_crash(t) = P(CRASH endpoint occurs on t+1 | still active at t)`
- `h_recovery(t) = P(RECOVERY endpoint occurs on t+1 | still active at t)`

Primary risk score: `logit(h_crash) - logit(h_recovery)`.

## Frozen feature families
LOCAL_ONLY:
1. `zdd`
2. 1-session return / `sigma63`
3. 3-session return / (`sigma63*sqrt(3)`)
4. 5-session return / (`sigma63*sqrt(5)`)
5. 10-session return / (`sigma63*sqrt(10)`)
6. `vol10 / vol63`
7. fraction negative returns over last 5 sessions
8. 5-session drawdown change / `S21`

LOCAL_PLUS_REGIME (primary) adds only three already-frozen causal state summaries:
9. `sync_rankmean`
10. `accel_rankmean`
11. `systemic_rankmean_6`

No feature search is allowed inside STEP07A.

## Model
For each cause separately:
- `SimpleImputer(median)`
- `StandardScaler`
- `LogisticRegression(C=0.25, max_iter=2000)`
- no class weighting

Training window: 2017-02-01 through 2020-12-31 only.
Validation/replay window: 2021-01-01 through 2022-12-31 only.
No refit on 2021-2022.

Sample weights are constructed so each market date has total weight 1; within a date, rows are initially downweighted by inverse episode length and then renormalized. This prevents basket multiplicity and long episodes from masquerading as independent evidence.

## Causal score calibration
The risk score is transformed to a weighted empirical percentile. The ECDF is seeded with training scores only. During 2021-2022, scores from a date enter calibration history only after decisions for that date are complete; no validation labels enter calibration.

## Frozen exposure map
Outside an active adaptive stress episode: 100% HGB.
Inside an active episode, today's score controls tomorrow's gross exposure:
- percentile <= 0.50: 100%
- (0.50, 0.70]: 85%
- (0.70, 0.85]: 65%
- (0.85, 0.95]: 40%
- > 0.95: 0%

On recovery/censoring the episode ends; the next decision state is normal unless a new adaptive episode is triggered. Exposure changes pay 5 bp per one-way gross change. There is no threshold search or sizing grid.

## Benchmarks
Exact frozen 2021-2022 replays will be reconstructed for:
- HGB
- FUSION1
- STEP06K

## Net-jump development gate
The primary LOCAL_PLUS_REGIME candidate qualifies for a one-shot 2023+ holdout only if all are true on 2021-2022:
1. mean MaxDD improvement vs FUSION1 >= +0.50 pp;
2. p10 MaxDD improvement vs FUSION1 >= +0.50 pp;
3. CAGR vs FUSION1 >= -0.50 pp concession;
4. mean gross exposure >= 85%;
5. mean MaxDD improvement vs FUSION1 is non-negative separately in both 2021 and 2022;
6. LOCAL_ONLY has non-negative mean MaxDD improvement vs FUSION1 (architecture-direction support).

This intentionally demands a materially larger move than STEP06R's incremental improvements. If the gate fails, 2023+ is not opened and the adaptive-hazard route is considered development-rejected in its clean low-dimensional form.

## Holdout rule if gate passes
Freeze model objects, training-score ECDF, features, episode definition, and exposure map before opening 2023+. One-shot 2023-07/2026 replay only; no post-holdout retuning.
