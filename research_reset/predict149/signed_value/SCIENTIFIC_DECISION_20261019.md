# Original149 — Signed-value prediction and after-discovery falsification
Date 2026-10-19 | `research/149-signed-value-predictor-20261019`

## Decision
**Strong experimental improvement in representing direction and left-tail risk, but no robust edge proven relative to correctly matched risk/sector placebo, so NO model production deployment.** In particular, F3 three-quantile signed excess model is now a high-priority **frozen hypothesis**, not a 30%-CAGR winning strategy. Do not retune it on 2021–2026.

Both original149 GitHub Actions completed **successfully**:
- Signed distribution model search: https://github.com/AM1975MA/Test/actions/runs/39218769031
- After-result adversarial stress: https://github.com/AM1975MA/Test/actions/runs/39219460024
- Sources and prediction tables: `research_reset/predict149/signed_value/results/` and `stress/results/`, SHA-256 manifests.
- No change to `etf_trader`, data are 149 original fixed survivor U.S.-listed ETFs, NOT EUR investable PIT universe, horizons 64 × 21 sessions 2021–26, 9,536 ETF-month forecasts, historical data repeatedly tested, 10 bps each side conditional share-level reconstructions.

## Targets and mathematical change
Old N4 learned P(ticker in top15 absolute returns). This over-rewards variance, not expected signed return. T149-F froze five alternative **bench-relative signed** targets from previous-close available 19 close-derived features plus category:
1. F1 LightGBM predict winsorized signed log excess Y in [-.2,+.2].
2. F2 hurdle: conditional P(Y>0), expected winning magnitude, expected losing magnitude, combined as pseudo-expected signed payoff.
3. F3 independent LightGBM conditional Y quantiles .10/.50/.90, score=(q10+2q50+q90)/4; a three-quantile proxy for expected value, not true fully calibrated density.
4. F4 P(Y>+3%) minus P(Y<-5%) with economic-sign thresholds fixed pretest.
5. F5 risk-scaled F1 mean.
Historical N4, as-of 63d momentum and as-of volatility-only are direct comparators. Trained on fully **matured** observations only, quarterly refits.

## Observed 149 portfolio results (2021–2026 retrospective exploratory)
| Policy | Net CAGR | Daily-open MaxDD | Daily log Sharpe | Avg signed 21d excess vs static 60/40 | Actual bottom15 membership of selected 5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| N4 old max future Top15 classifier | 16.70% | -34.01% | 0.499 | +0.003230 | 28.13% |
| F1 clipped signed expected mean | 1.00% | -51.45% | 0.038 | -0.006655 | 21.56% |
| F2 hurdle conditional sign + magnitudes | 13.63% | -28.28% | 0.505 | +0.003558 | 16.25% |
| **F3 three-quantile signed returns** | **20.02%** | **-29.74%** | **0.693** | **+0.007949** | **17.81%** |
| F4 signed 3%/5% event probability | 13.37% | -29.50% | 0.542 | +0.003769 | **14.06%** |
| F5 mean divided by as-of vol | 4.40% | -42.59% | 0.176 | -0.002764 | 18.44% |
| Risk-only 63d realized volatility | 6.14% | -36.36% | 0.197 | -0.006486 | 34.06% |

F3 Spearman future benchmark relative cross-sectional +0.07319 vs N4 -0.01654; 3-anchor bootstrap paired F3-N4 Spearman lift CI **[+.03241,+.14564]**, but entire-period ranking result contrasts with the strict per-era economic gate:
- 2021–23 F3 selected future excess +0.005310 vs N4 -0.013047.
- 2024–26 F3 +0.011134 vs N4 +0.022874. F3 **underperforms N4** in later period.
- F3 56.25% of chosen holdings actually outperform USD 60/40, vs N4 49.69%; N4 absolute best ETF in selected 5 in 19/64, F3 only 10/64, demonstrating signed-vs-highest-volatility distinction.
- Original preregistered stringent economic era-dominance gate **FAILED** for ALL tested methods; do not change gate after looking at F3.

## Proper-score / probabilistic evidence, not backtest return
- P(Y>0): Brier F2 sign **.248494**, online prior **.249914** — modest improvement.
- P(Y>+3%): Brier event model **.154521**, online category prior **.154500** — no real gain.
- P(Y<-5%): Brier downside model **.093178**, online category prior **.096002** — better.
- Direct F1 winsorized return MSE **.00248787**, online train-mean MSE **.00246458** — worse.
- F2 implied expected clipped return MSE **.00246436**, online mean **.00246458** — nearly equal, NOT strong.
- **Conditional lower-tail quantile 10% pinball** F3 .007985 vs online unconditional quantile .008916, upper 90% .008527 vs .009383; median quantile .017461 vs null .017446 — tail information relatively stronger than center. Strongly suggest that conditional tail asymmetry is more learnable here than an exact mean value.

## After-result adversarial matched test (explicitly POSTHOC)
F3 not retrained, thresholds/weights identical. 250 randomized five-name portfolios matched on the same coarse six classes and identity retention, and 250 further matched by as-of 63d volatility. Same actual 149, same 64 anchor dates, exact self-funding 10bp share trades:
- F3 20.02% historical CAGR; 250 **class-only** placebo median 9.62%, 95th percentile 16.10%; F3 exceeds 99.6% class-only placebo CAGR outcomes.
- But 250 **class-and-volatility matched** placebo median **15.34%**, 95th percentile **23.03%**; F3 at **86th percentile** (below placebo 95th percentile), not an exceptional result once risk adjusted by observable volatility. F3 DD −29.74% vs matched median −27.86% (worse); F3 actual realized signed mean excess +.007949 vs matched median +.004987, a weaker conditional benefit.
- Paired F3 minus N4 mean signed excess **+.004719 log per month**, circular block 95% CI **[-.01132,+.02165]** includes zero. F3 minus N4 costed monthly log growth +.002348, CI **[-.01312,+.01853]** includes zero.
- Paired F3 minus per-anchor volatility+class placebo signed mean **+.002716**, 95% block CI **[-.00504,+.01091]** includes zero.
- Strict preregistered F3 adversarial transfer gate = **FAIL**. Thus no statistical demonstration that the exceptional-looking 20.02% survives controlled factor/volatility comparisons or hypothetical new samples.

## Deep learning decision
- Conditional **negative tail, event probability and quantiles** are an intellectually legitimate improvement in *what to forecast*; they reduce symmetric tail chasing and can improve global ranking of signed outcomes. **This is not equivalent to a trained profitable forecaster of 30% CAGR.**
- Exact benchmark-relative *mean* value still barely forecastable: direct mean regressor loses to online null MSE, hurdle barely beats it; F3 more informative extreme quantile predictions can approximate useful asymmetric opportunity but is exposed to volatility composition and sample selection.
- Further parameter tuning on same 149 would amplify overfitting and model-family shopping. F3 fixed source code and hyperparameters should become a frozen **challenger for newly available dates after 2026-07-01**, with transparent source acquisition and as-of investible roster; avoid calling those months a large independent statistical sample.
- Better research requires new independent PIT data (fund underlyings/sector exposures, credit/timeline, futures roll), and a controlled sample of newly matured ETF and market periods. No trusted 149 original list can cover delisted new vintages or truly investable EU ETF universe.
- Until true out-of-sample behavior is measured, choose paper-only forecast recording, no trading action, no edits to ETF production repo.

**Verdict:** main problem direction-vs-volatility is partially addressed mathematically, but not *solved*. The best research candidate is F3 (signed quantiles), not because of its CAGR alone but improved tail scoring and rank correlation; confidence in a 30% CAGR strategy remains absent.
