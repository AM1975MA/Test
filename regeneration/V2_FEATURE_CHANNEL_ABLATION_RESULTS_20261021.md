# ETF Trader V2 — feature representation and economic-family ablation (21 Oct 2026)

## Completed matched experiment
- [Successful GitHub Actions run 39510844931](https://github.com/AM1975MA/Test/actions/runs/39510844931).
- Complete results artifact `12305572884` (`v2-feature-channel-complete`), three source-only yearly artifacts for 2018, 2022 and 2025.
- Same frozen 149-ETF raw snapshot from run `39482809691`, same official canonical 500 baskets of 24, same 36 mature forward 21-day months, same XGBRanker 127-leaf 360-round three-seed annually refitted ensemble.
- Exact eligibility, observation dates and targets match on all variants; no Tail, macro, allocation, risk-layer.
- NO_DEV: remove all 33 `*_dev` features (keep 92 raw/pct).
- NO_PCT: remove all 46 `*_pct` features (keep 79 raw/dev).
- NO_RAW: remove all 46 plain features (keep 79 pct/dev).
- NO_MARKET: remove 12 features with prefixes `beta_mkt` and `corr_mkt` (keep 113).
- NO_MOMENTUM: remove 49 momentum/trend/moving-average/RSI/positive-day features (keep 76).
- NO_VOLRISK: remove 61 volatility/downsiderisk/drawdown/efficiency-related features (keep 64).
- NO_LIQUIDITY: remove 6 features in `volume_*` and `log_adv*` families (keep 119).
  
## Full matched OOS results (2018, 2022, 2025)
| Arm | n | Universe IC | Basket Top-1 | Basket Top-3 | Basket regret per 21D |
| --- | ---: | ---: | ---: | ---: | ---: |
| BASE125 | 125 | 0.076193 | 18.078% | 37.839% | 9.597% |
| NO_DEV | 92 | 0.076481 | 18.300% | 38.944% | 9.758% |
| NO_MARKET | 113 | 0.082619 | 17.533% | 39.339% | 9.799% |
| NO_LIQUIDITY | 119 | 0.073789 | 17.594% | 37.478% | 9.527% |
| NO_PCT | 79 | 0.072957 | 16.089% | 35.044% | 10.013% |
| NO_RAW | 79 | 0.060304 | 14.783% | 33.717% | 10.059% |
| NO_VOLRISK | 64 | **0.095507** | 14.367% | 34.961% | 10.196% |
| NO_MOMENTUM | 76 | 0.057564 | 13.828% | 31.478% | 10.214% |

## Year-by-year basket Top-3
| Year | BASE125 | NO_DEV | NO_MARKET |
| --- | ---: | ---: | ---: |
| 2018 | 30.55% | 31.98% | 35.00% |
| 2022 | 45.03% | 44.95% | 46.80% |
| 2025 | 37.93% | 39.90% | 36.22% |

## Paired conditional bootstrap sensitivity (corrected for disconnected years)

Use 5000 resamples, within each of the exact three years sample two circular 6-month blocks, with year weights held equal. This estimates uncertainty **conditional on these selected years**, not across possible untested market histories.

| Drop-one arm | Basket Top3 delta versus BASE | Fixed-year bootstrap 95% interval | Basket regret delta |
| --- | ---: | ---: | ---: |
| NO_DEV | +1.106 pp | [+0.061,+2.161] pp | +0.161 pp |
| NO_MARKET | +1.500 pp | [-0.650,+3.617] pp | +0.202 pp |
| NO_LIQUIDITY | -0.361 pp | [-1.833,+1.072] pp | -0.070 pp |
| NO_PCT | -2.794 pp | [-5.050,-0.633] pp | +0.416 pp |
| NO_RAW | -4.122 pp | [-6.433,-1.838] pp | +0.462 pp |
| NO_VOLRISK | -2.878 pp | [-5.145,-0.622] pp | +0.599 pp |
| NO_MOMENTUM | -6.361 pp | [-8.044,-4.733] pp | +0.617 pp |

## Interpretation
- `NO_DEV` is a **tentative lower-complexity candidate**, not a proven better production configuration: 33 features fewer, nearly identical universe IC, basket Top3 slightly higher, but basket regret slightly worse and universe Top1 decreased. The nominal fixed-year bootstrap excludes zero marginally yet **does not adjust for the tested arms and the thousands of prior research decisions**.
- `NO_MARKET` improves average basket Top3 and overall IC but **underperforms baseline in 2025**, and its bootstrap interval includes zero. Neither Top1 nor regret improves.
- Removing raw feature magnitudes has a visible Top1/Top3 cost. Removing pct features also hurts. Removing all momentum/trend families produces the worst Top3 drop.
- **Ranking IC and Top3 can move in opposite directions**: NO_VOLRISK raised universe IC by 0.0193 but decreased basket Top3 by 2.878 pp. Optimization solely on IC would be insufficient.
- **Next step**: compare BASE125, NO_DEV, NO_MARKET on each year 2018–2026 using the same snapshot. This is an extension/robustness check of already-explored history, *not* a virgin holdout. Keep production unchanged.

Do not promote `NO_DEV` or `NO_MARKET` without independent confirmation and a multi-objective criterion (Top3, regret, IC, economic return). Do not treat 500 overlapping baskets as statistically independent.
