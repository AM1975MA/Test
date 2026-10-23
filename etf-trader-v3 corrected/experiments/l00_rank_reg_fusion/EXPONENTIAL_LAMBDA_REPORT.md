# V3 meta research: exponential lambda and confidence gates (frozen run)

Validated success: [Actions 40031144599](https://github.com/AM1975MA/Test/actions/runs/40031144599), exponential job, [artifact 12534457757](https://github.com/AM1975MA/Test/actions/runs/40031144599/artifacts/12534457757). Original raw inputs 149 ETF, canonical 500x24 baskets, 101 months, 2018-01 to 2026-05; original OOS first-stage heads from run 40016809498. Exploratory backtest, **not pristine holdout**; none of the 46 arms is promoted to production.

For any ETF i, let R and G be same-date global percentile scores from baseline ranker and relative-return REG_REL125. The robust positive multiplier is **R * exp(lambda * (2G-1))**. Lambda grid is 0.05, .10, .20, .35, .50, .75, 1, 1.5, 2, 3, 4. TOP3 variant reorders only original three highest-ranked ETFs; ALL variant reorders the entire basket. Gate restricts TOP3 changes to ranker margin first-vs-second <= {.02,.05,.10}, regression edge candidate-vs-first >= {.05,.15}, lambda {.2,.5,1,2}. These are **fixed grids**, chosen before outcomes. Gating and lambda values require further fully independent validation before selection.

| Variant | Top1 hit rate | Top3 hit rate | Selected forward 21D excess | Remark |
|---|---:|---:|---:|---|
| CORRECTED | 14.5525% | 35.4713% | +0.7122% | immutable control |
| EXP_TOP3_REL125_0.05 | 13.9129% | 35.4713% | +0.8150% | retains candidates |
| EXP_TOP3_REL125_0.2 | 13.0733% | 35.4713% | +0.8445% | Top1 hit rate lower |
| EXP_TOP3_REL125_4 | 12.3406% | 35.4713% | +0.7425% | extreme lambda does not help |
| EXP_ALL_REL125_4 | 10.7010% | 22.0218% | +0.5644% | strong lambda devastates Top3 |
| GATE_TOP3_REL125_0.2_G0.02_E0.15 | 14.3129% | 35.4713% | +0.7496% | intervention only 9.6% of baskets |
| GATE_TOP3_REL125_0.2_G0.1_E0.15 | 13.2891% | 35.4713% | +0.8662% | highest observed excess, Top1 materially worse |

Bootstrap: 2,000 paired circular six-month blocks, 101 month-level observations; overlapping baskets are **not independent**. For EXP_TOP3_0.2, mean Top1 change -1.4792pp (95% [-2.6755,-0.1661]pp), selected excess +0.1323pp (95% [-0.1897,+0.4938]pp). For EXP_TOP3_4, Top1 changes -2.2119pp ([-3.8992,-0.4949]pp). EXP_ALL_4 Top3 drops -13.4495pp ([-16.3253,-10.3008]pp). Confidence gate margin .02, regression edge .15: Top1 -0.2396pp ([-0.5901,+0.1110]pp), selected excess +0.0374pp ([-0.0467,+0.1216]pp). Confidence gate gap .10, regression edge .15: Top1 -1.2634pp ([-2.2653,-0.1386]pp), excess +0.1540pp ([-0.1514,+0.5071]pp). No confidence interval for increased selected excess excludes zero.

**Conclusion:** higher lambda is not an escape from loss of Top1. Confidence gates reduce intervention frequency and harm, but no robust advantage validated. Do not confuse arithmetic selected-forward-excess with executable strategy CAGR. The parallel supervised DecisionTree meta-layer is a separate experiment.
