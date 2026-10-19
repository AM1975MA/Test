# Original149 walk-forward supervised learning stacking F3/H1 — scientific verdict
19 October 2026 | Branch `research/149-walkforward-two-expert-stacking-20261019`

## User hypothesis and test: YES, an actual learning machine was trained and tested
Question: would a cross-sectional walk-forward machine trained on frozen F3 and H1 scores beat merely switching their portfolios monthly? The key distinction from previously failed J2/J3 is that **T149-K learns on each ETF-month (149 ticker observations per matured month)** rather than only one expert winner per month, BUT the macroeconomic effective n remains 51 dates, not 7599 independent scenarios.

Completed GitHub Action (success): https://github.com/AM1975MA/Test/actions/runs/39267915904. First tool attempts no runtime scoring differences; build, scientific assertions, training, baseline parity and SHA-256 commits all passed. Full files in `research_reset/predict149/walkforward_stacking/results/`, with `ALL_9536_PREQUENTIAL_STACKING_FORECASTS.csv`, `ASOF_64_MONTH_MODEL_SELECTIONS.csv`, `PROPER_SCORE_PER_MATURED_TEST_ANCHOR.csv`, `META_TOP5_DIRECTION_RANKING_AFTER_WARMUP.csv`, `EXACT_CASH_FUNDED_DAILY_STACKED_EQUITIES.csv`, `RESULT.json`, and `SHA256_MANIFEST.txt`. Source `run.py`, `test_run.py`; frozen protocol `PREREGISTERED.md`.

## Fixed protocol, genuine past-only metadata
Exactly the original 149 USD-listed survivor ETFs; 64 21-trading-day anchors 2021–2026; **51 test months after 13 warmup months**, 51×149=7599 future-relative event predictions. F3 and H1 were frozen prequential predictions with training only on past matured 2017–21 data; their scores and original H3 reused unchanged.

Inputs to models: 149 within-month percentile F3 forecast rank, H1 forecast rank, their mean/difference, as-of prior 63d volatility rank, as-of H3 predicted quantile spread rank, original 6 one-hot macro classes. At each signal at previous Close, **the just-finished month label ending at the next trading Open is unavailable**; only blocks k−2 and earlier may train. Refit fixed algorithms **every 3 months** on all matured historical meta-labels; first 13 meta months use original 50/50 F3/H1, not an empty-data fitted model. Future-label mutation and complete one-open chronology assertions pass. No hyperparameter search after results.

Predeclared competitors:
- Simple equal cross-sectional mean F3/H1 rank, buy 5, no ML.
- K1 two regularized logistic predictions of *signed* next21 benchmark-relative Y >+3% and Y<−5%, rank score .03*Pup−.05*Pdown and buy 5 ETF.
- K2 shallow HGB regression of winsorized ±20% **signed** forward excess Y, buy the 5 expected highest.
- K3 shallow LightGBM LambdaRank directly grades positive future best 5,15,30, buy 5.
- K4 use K2 average predicted return of *current frozen F3 basket minus current H1 basket* to choose 75/25 or 25/75 if forecast differential is >2% or <−2%, else keep 50/50. K4 chose unchanged 50/50 on all 64 months; should not be interpreted as a successful adaptive predictor.
- Exact original costed self-financed F3, H1, H3 and STATIC F3/H1 50:50, with 10bp buy/sell each and same Open quotes, source SHA `7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6`.
- No EUR-broker real spread, tax, FX, point-in-time listings or delisted ETF history: **not investable validated annual return**.

## Real historic economics, Feb 2021–June 2026
| Method | Net simulated CAGR | Daily Open maxDD | Daily annualized log Sharpe | Daily worst5% return ES |
|---|---:|---:|---:|---:|
| Frozen F3 | 20.020% | −29.737% | .693 | −3.702% |
| Frozen H1 | 24.625% | −33.774% | .793 | −4.112% |
| Frozen H3 | 23.526% | −28.783% | .759 | −4.137% |
| **Frozen real ETF 50:50 F3/H1** | **23.215%** | **−24.844%** | **.887** | −3.302% |
| Equal F3/H1 score rank Top5 without learning | 14.657% | −24.603% | .527 | −3.732% |
| K1 signed up/down logistic Top5 | 13.060% | −25.975% | .568 | −3.191% |
| K2 HGB clipped signed return Top5 | 12.894% | −32.325% | .494 | −3.620% |
| K3 direct graded LambdaRank Top5 | 19.854% | −34.714% | .627 | −4.250% |
| K4 model-predicted basket gate | **23.215%** | −24.844% | .887 | −3.302% (same static) |

Bootstrapped 64-anchor paired *monthly net log returns vs original 50:50*:
- K1 mean −0.007190/month (95% 3-anchor block CI **[−0.013640,−0.001081]**): **worse**.
- K2 mean −0.007312/month (CI **[−0.014787,−0.000215]**): **worse**.
- K3 mean −0.002312/month (CI [−0.013604,+0.008122]): includes zero, with worse DD.
- K4 mean 0 because no changes.
All four **precommitted joint skill/risk/economic gates FAIL**.

## KEY POSITIVE FINDING — learned tail probabilities have *some* proper-score skill
On **51 genuinely chronological post-warmup anchor months** (date-level bootstrap with circular 3-anchor blocks), both K1 classification heads lower Brier and log-loss relative to the **mean event rates calculated only on matured earlier ETF data**:
- Positive relative return >+3%: mean **Brier gain +.00581176** (lower Brier than prior), date-block CI **[+.00217045,+.00929380]**; Log-loss gain +.01823 (CI [+.00547,+.03005]).
- Negative relative return <−5%: mean **Brier gain +.00530311**, CI **[+.00300547,+.00777660]**; Log-loss gain +.02482 (CI [+.01462,+.03547]).
- K2 point forecast winsorized return squared error **.002382874** vs naive matured historical mean **.002384599**; improvement +.000001726, CI **[−.00003688,+.00004273]**: indistinguishable from noise.
- K1 event probability might be informative about **marginal tail frequency** but **DOES NOT** imply superiority in selecting signed high-return ETF leaders: its selection CAGR fell to 13.06% even though lower daily ES than 50:50; the general Brier skill may derive from broad asset risk/class exposure and common market states. Especially no claim it can identify the correct F3-vs-H1 month (that separate T149-J trial failed).

## Consequences and decision
1. **Do not discard F3 or H1 rankings in favor of the stacked model**. Pooling scores directly was worse than holding both baskets separately: original portfolio diversification beats top5 fused ranking in this sample. Do not optimize another Top5 threshold / 40–60 split on same historical 64 anchors.
2. A narrower candidate scientific question is now justified: Can we use K1's forecast probability of **left-tail negative excess** for stocks already picked by F3/H1 to quantify *portfolio conditional risk/ES*, without using K1 to choose different high-upside names? Such a risk-only overlay would require a frozen future test; the current experiment did **NOT** verify that tail probabilities can improve a portfolio without harmful de-risk timing. Include actual portfolio exposures, intra-month correlation and futures roll risks.
3. The 51 mature dates are too few to generalize, even with 7,599 ETF rows. Use historical grouped uncertainty and no p-hacking; report that all methods were inspired by already-mined data. To establish a usable predictor of expert leader, need **new genuinely available pre-signal data** and a separate test period with final code committed BEFORE outcomes and execution quotes. Never infer 30% forward CAGR.
4. H3 remains an interesting single portfolio candidate, but F3/H1 50:50 has highest empirical risk-adjusted Sharpe and better drawdown in this historical comparison. No backtested alpha in U.S. survivor-list is an investment recommendation.

**Verdict:** actually-trained walk-forward cross-sectional learning is scientifically worthwhile and can improve **directional event probability** estimates, but **does not improve** F3/H1 fully costed returns or their economic timing on this sample. Next development should target risk calibration using honest new period, or independent factors and PIT data, not algorithm shopping on same price history. No production `etf_trader` file changed.
