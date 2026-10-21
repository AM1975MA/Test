# V3 L03.2 — causal RMT spectral features for regime gate

**21 October 2026, completed. Rejected.** Frozen previously trained experts, no CAGR. Original 149 ETFs/500 baskets, 53 test months 2022–May 2026.

[Successful GitHub Actions 39674680942](https://github.com/AM1975MA/Test/actions/runs/39674680942), artifact **12380838434**. Earlier run 39674156188 was invalid due Python source import path and superseded; preserve as failed history.

One predeclared feature-family intervention: baseline market-only seven ex-ante features vs same L2 logistic model C=0.1 with additional spectral state of past 63-daily-return ETF correlation: leading eigenvalue fraction, top-three eigenvalue share, normalized spectral effective rank. Test RMT-only as diagnostic and train-only prevalence constant as reference. At each signal the features use **only past ETF closes**, never the next-21D expert win label. Annual training uses mature expert-relative Top-3 outcomes before year cutoff.

| Variant | ROC-AUC | Brier (lower better) | Log loss | Expert-chosen Top-3 |
|---|---:|---:|---:|---:|
| Train-only constant prevalence | N/A | **0.250041** | **0.695026** | 44.268% |
| Seven market features | 0.470238 | 0.253953 | 0.718008 | 44.830% |
| Market + RMT | 0.366071 | 0.272494 | 0.769800 | 44.830% |
| Three RMT features only | 0.226190 | 0.276856 | 0.766431 | 44.268% |

Market+RMT minus market-only Brier **+0.018541**, paired 6-month block 95% CI **[+0.001988,+0.042982]**; log-loss delta +0.05179, CI [+0.002989,+0.126568]. Higher loss and inferior AUC; no selection benefit. **Reject RMT as expert selector in this parameterization.**

This does not disprove RMT as *input features* to a future separately controlled ranker experiment. No feature engineering is promoted here. Prior historical period examined repeatedly, hence no untouched holdout.
