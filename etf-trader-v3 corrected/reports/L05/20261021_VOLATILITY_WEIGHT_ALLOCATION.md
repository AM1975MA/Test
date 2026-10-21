# V3 L05.2 — ex-ante bounded past volatility for same Top3 holdings

**21 October 2026: completed, NOT PROMOTED.** Frozen Tail expert and 50/30/20 Top3 selection. No ETF replacements or first-stage model changes, no CAGR.

[Successful Actions run 39674584732](https://github.com/AM1975MA/Test/actions/runs/39674584732), artifact **12382150250**.

One predeclared intervention: previous-63-day `Close` log-return volatility (21 valid minimum, zero lookahead), weights `w'_i = normalize(w_i × clip((median(selected_vol)/vol_i)^0.5, 0.8,1.2))`, preserving the same three ETF symbols and positive weights. 149 original ETFs, 500 overlapping baskets, 101 signal months 2018–2026. No missing vol in eligible period. Control must numerically reproduce archived L05 50/30/20 score exactly.

| Functional metric | Frozen Top3 50/30/20 | Bounded vol-aware |
|---|---:|---:|
| Mean realized percentile rank weighted | 0.512941 | 0.513762 |
| Future bottom-three weight | 26.695% | **26.312%** |
| Weight on future winning ETF | **15.218%** | 14.934% |
| Future actual absolute >10% loss weight | 10.076% | **9.778%** |
| Mean next21D weighted regret | 0.107137 | 0.106906 |
| Target-weight churn (not live turnover) | **0.383364** | 0.401237 |
| Mean max position | 50.00% | **48.33%** |

Paired six-month block delta vol minus original: bottom-three weight **−0.384 pp**, 95% CI [−0.553,−0.216] pp; future severe loss weight **−0.298 pp**, CI [−0.424,−0.171] pp; future winner weight **−0.284 pp**, CI [−0.399,−0.160] pp; target-weight churn **+0.017873**, CI [+0.016496,+0.019193]. Mean selected rank quality +0.000822, CI [−0.000755,+0.002538], not established.

No free improvement: exposure to losing ETFs falls but so does weight on eventual winners; churn increases. **Keep 50/30/20 as L05 reference and do not promote vol-weight intervention.**
