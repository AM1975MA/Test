# Genuine torchsort SoftSpearman TCN — Original149 verified full and pilot, 2026-10-20

## Experimental contract
Research branch research/original149-softspearman-20261020; frozen Original149 149 ETF OHLCV, SHA-256 roster 7bccf1b756bf3652280a254c7486fb43f1e805ebb4cdf10731cecc74007292e6, 125 canonical daily Compact21 features, 30-session TCN(24 channels, dropout .35, 5 epochs max, patience 2, AdamW lr .001 wd .003), annual prior-year holdout and maturity-gated expanding walk-forward, 5-session future next-open to open+5, same anchored 476 weekly OOS 2017–2026, Top5 equal-weight long only and 20bps roundtrip per week. Genuine differentiable torchsort 0.1.10 soft_rank L2 regularization_strength=1.0 (NOT sigmoid ranks), predicted group-standardized scores, Pearson correlation vs realized hard future percentile ranks.

Preregistered objectives:
1. SOFTSPEARMAN: 1−Pearson(soft_rank(prediction), hard_rank(y));
2. SOFTSPEARMAN_RETURN: above +0.30 SmoothL1(prediction, matured, same-date spread-normalized future return);
3. SOFTSPEARMAN_TOP5: 1−truth-top5-weighted Pearson(soft_rank(prediction), hard_rank(y)), weight 5 for the TRUE matured top5, 1 for others. Only during training/validation are future realized true top5 labels known; inference score never sees them. The last objective is NOT standard unweighted Spearman but a differentiable top-targeted weighted extension.

All 6 matrix pilot/full runs and all unit tests (backprop nonzero, finite, full ranking signs, permutation invariance, weighted top5, hybrid target) completed successfully. By necessity matching available binary, these challengers use PyTorch 2.6.0 CPU and precompiled torchsort 0.1.10 pt26cpu; earlier Pointwise used PyTorch 2.7.1, a documented library-version caveat. No baseline retraining on newer library, no parameter tuning using OOS pilot.

## Primary full 2017–2026 OOS 476 weeks

| Variant | CAGR net | MaxDD | Sharpe | mean nominal-return RankIC | actual Top5 overlap |
|---|---:|---:|---:|---:|---:|
| frozen original pointwise TCN | +5.1942% | −48.4929% | +.32852 | +.05609 | 6.26% |
| frozen Ridge125 | +5.1314% | −50.4393% | +.33096 | +.05434 | 6.51% |
| frozen past21 momentum | **+13.4143%** | **−34.9415%** | +.62525 | −.00565 | 13.03% |
| SOFTSPEARMAN | **+3.0702%** | −46.8997% | +.25791 | **+.06269** | 1.55% |
| SOFTSPEARMAN_RETURN | **−2.0807%** | −50.8607% | −.02516 | +.05835 | 1.26% |
| SOFTSPEARMAN_TOP5 | **−6.0355%** | −72.6033% | −.05522 | +.03710 | **17.48%** |

Pure loss raises observed mean RankIC vs Pointwise +.00661 but at cost lower CAGR and Top5 hitrate. Pointwise RankIC advantage is not statistically established independently: matched 5-week block 95% CI [−.00402,+.01732] includes zero. SoftSpearman Top5 improves Top5 raw overlap by +11.2185 percentage points vs Pointwise, 95% paired block [ +9.0756,+13.4044 ] percentage points, but has negative nominal Top5 return advantage. It is NOT a candidate for economic selection despite Top5 hit-rate.

## 2024–25 diagnostic pilot 100 weeks

| Variant | net CAGR | MaxDD | Sharpe | RankIC | nominal oracle Top5 overlap |
|---|---:|---:|---:|---:|---:|
| frozen pointwise TCN | +10.0677% | −27.5291% | .5561 | +.05879 | 5.2% |
| frozen mom21 | +10.4242% | −24.8602% | .5026 | −.03721 | 15.2% |
| pure SOFTSPEARMAN | +4.0455% | −19.3039% | .3260 | +.04865 | 0.8% |
| SOFTSPEARMAN_RETURN | −4.8778% | −25.7999% | −.1819 | +.04836 | 2.4% |
| SOFTSPEARMAN_TOP5 | **+24.2102%** | **−19.0824%** | **.9511** | +.05503 | 19.8% |

Pilot Top5 performance is NOT stable across 2017–2026; this is yet another demonstrated dangerous two-year selection / data snooping trap, similar to previously tested ListNet hybrid.

## Independent 476-week matched OOS audit and exploratory 5-week circular-block CIs

Original Pointwise exact 476 dated signal support and original149 roster SHA validated for all challengers. Separate replay archived as YEAR_BY_YEAR_COSTED.csv, includes yearly realized 5-session net Top5 returns and exit max drawdown. Return deltas are **nominal portfolio 5-session average next-open returns**, per-week, matched by date, and identical cost 20bp cancels out in differences. Confidence intervals descriptive only due to overmined historical set.

| Challenger vs frozen MOM21 | mean Top5 nominal 5d return difference (pp) | 95% circular 5-week block interval (pp) |
|---|---:|---|
| SOFTSPEARMAN | −0.2142 | [−0.4980,+0.0752] |
| SOFTSPEARMAN_RETURN | −0.3194 | [−0.6213,−0.0377] |
| SOFTSPEARMAN_TOP5 | **−0.3536** | **[−0.7102,−0.0237]** |

| Challenger vs frozen Pointwise | mean RankIC difference | 95% circular 5-week block interval |
|---|---:|---|
| SOFTSPEARMAN | +.00661 | [−.00402,+.01732] |
| SOFTSPEARMAN_RETURN | +.00227 | [−.00955,+.01444] |
| SOFTSPEARMAN_TOP5 | −.01899 | [−.03897,+.00154] |

This means measured rank improvement for pure soft Spearman is statistically uncertain in an autocorrelated block bootstrap, while return underperformance of Top5 against momentum has exploratory negative 95% interval. Top5 oracle hit-rate is not synonymous with significant tradable positive average Top5 returns due to extreme variance, volatility selection and downside outcomes.

## Evidence and files

- Full three models + all yearly fold checkpoints, all per-ETF OOS predictions, per-week selections and daily net NAV: https://github.com/AM1975MA/Test/actions/runs/39473844113
- Pilot complete and checkpoints: https://github.com/AM1975MA/Test/actions/runs/39473836762
- Independent full 476 exact-date matched audit, raw return and IC paired bootstrap, YEAR_BY_YEAR_COSTED.csv: https://github.com/AM1975MA/Test/actions/runs/39474701442
- Independent pilot exact date audit: https://github.com/AM1975MA/Test/actions/runs/39474308419
- Frozen original Pointwise full: https://github.com/AM1975MA/Test/actions/runs/39455244701
- Code: tensor149_tcn5d/softspearman_losses.py, softspearman_run.py, test_softspearman.py, compare_softspearman.py.
- Pre-registered plan: tensor149_tcn5d/SOFTSPEARMAN_PREREGISTRATION.md

## Decision

No promotion of any variant to live/production. Genuine soft Spearman is feasible and trains end-to-end on daily Original149. It marginally improves *point estimate* raw-return RankIC on long sample but does not produce costed long-only alpha or beat simple momentum. Top5-targeted weighted Spearman massively improves ex-post extreme winner overlap but destroys long-horizon wealth. Another training objective alone is not adequate; prioritize independent inference-compatible expected nominal top-five forward returns and a separate portfolio tail-risk/position-sizing rule, with holdout different universe or future untouched data.

Limitations: 149-name retrospective survivor list, extensively mined OOS interval, price adjusted open not guaranteed executable, constant slippage/cost assumptions, no changes in investor constraints, descriptive CIs do not adjust for multiple model trials.
