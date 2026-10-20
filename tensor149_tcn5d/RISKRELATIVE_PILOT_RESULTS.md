# Original149 5-session risk-relative target pilot — 2026-10-20

Research only, branch research/original149-tcn-riskrelative-20261020; full preregistration: tensor149_tcn5d/RISKRELATIVE_PREREGISTRATION.md. No production changes or original source data edits.

## 2024–25, exactly 100 chronological weekly predictions; 149 frozen ETFs; long Top5 equal weight, next open to next open+5, 20bps per roundtrip
| Model | Net CAGR | MaxDD | Sharpe | Mean all-ETF RankIC | Raw realized top5 overlap | Mean selected vol63 | Mean beta63 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original frozen TCN Pointwise | +10.0677% | −27.5291% | .5561 | +.05879 | 5.2% | - | - |
| Raw-excess ListNet target vs SPY | +9.5765% | −28.0247% | .4728 | +.02363 | 19.6% | 42.51% | .657 |
| Risk-relative ListNet (excess / asof vol63) | −7.0934% | −24.0978% | −.3460 | −.02577 | 6.4% | 20.22% | .259 |
| Beta- and risk-relative ListNet ((excess beta residual)/asof vol63) | +0.5990% | −23.4558% | .1296 | +.00736 | 10.2% | 24.64% | .200 |
| As-of original momentum21 | +10.4242% | −24.8602% | .5026 | −.03721 | 15.2% | 29.92% | .767 |
| As-of mom21 risk-scaled | +1.8491% | −25.5224% | .1944 | −.03682 | 9.6% | 20.99% | .607 |
| As-of mom21 beta- and risk-scaled | +3.9401% | −25.8246% | .2898 | −.03444 | 8.2% | 20.06% | .445 |
| Highest vol63 | +13.7786% | −22.7474% | .6073 | +.05378 | 18.8% | 45.75% | not recorded |
| Lowest vol63 | −5.0395% | −10.0672% | −3.4440 | −.05378 | 0.8% | 7.10% | not recorded |

Risk-relative targets all train against softmax of the 5-day benchmark-relative matured next-open outcome distribution after subtracting median and dividing by q90−q10 date-by-date; only as-of vol63 and beta_mkt63 are features used in risk normalizer. They are NOT market-neutral portfolios. Portfolio economic assumptions identical to frozen baseline.

The independent audit confirms matched 100 signal dates, identical ETF roster, and that all momentum/vol controls select identically regardless of target training. Paired RAW_EXCESS_DIST vs MOM21 difference in mean 5-day Top5 return −0.000115; exploratory 95% five-week moving-block interval [−0.00492,+0.00478]. No evidence of net uplift relative to momentum on pilot. Compared to Pointwise, RAW_EXCESS_DIST true Top5 overlap improves by +14.4pp, but its costed CAGR is slightly below Pointwise.

Primary 3×2yr pilot action: https://github.com/AM1975MA/Test/actions/runs/39471026485
Independent 100-week audit: https://github.com/AM1975MA/Test/actions/runs/39471702489

Full 2017–2026 expanding OOS remains the preregistered primary screen. No changes to losses or selections after pilot.
