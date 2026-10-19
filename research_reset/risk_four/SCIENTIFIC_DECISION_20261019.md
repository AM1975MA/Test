# Scientific decision — Four isolated F3/H1 risk/return ablations
19 October 2026. Retrospective original149 cohort. Completed successful GitHub Action [39293511535](https://github.com/AM1975MA/Test/actions/runs/39293511535). Previous tie-order source bug was corrected BEFORE successful run to preserve the frozen pandas original expert Top5: no strategy parameter or hypothesis altered in response to portfolio outcomes.

## Data and exact audited implementation
All 149 archived original US ETF survivors, 64 non-overlapping 21-session 2021–26 anchors, as-of previous Close and next Open; 1345 daily wealth points. All 8 Yahoo proxy ETFs SPY/TLT/GLD/USO/HYG/UUP/VNQ/XLE downloaded via pinned yfinance 0.2.65, each 2557 daily Close rows 2016–2026; stored under results/YAHOO_FACTOR_CLOSE.csv and YAHOO_FACTOR_MANIFEST.json with SHA256. Yahoo historical prices are retrospectively sourced, not vintage PIT. Original F3/H1 50:50 daily self-funded quote/fee parity **max abs error 1.33226762955e-14**. Exact 10bps fee on traded ETF buy/sell only, zero fee/yield on cash.

## Grossly important fixed treatments
- R1 FACTOR_BALANCE: dynamically assign each already-selected ETF to its highest-absolute prior126 daily correlation among 8 factor proxies (weak <0.25 -> OTHER) and equalize 50% of overall factor group allocation, preserve 100% ETF holdings exactly. Historical mean 2.75 distinct groups/month. Original dominant group mean weight 61.25% -> after policy 52.21%. This is an ex-ante heuristic exposure label, **not a validated factor ontology or true factor beta neutralization**.
- R2 VOL20: target annualized basket sigma 20%, shrink 63d covariance halfway to diagonal, cap invested fraction [40%,100%]. 23/64 blocks below full exposure; average invested 94.75%, minimum 65.15%. Cash has zero interest.
- R3 TREND126: if ex-ante weighted 126-trading-day ETF basket momentum is negative, hold 50% in zero-interest cash until next month. 13/64 blocks at 50%, avg invested 89.84%.
- R4 BUFFER_RANK: each original expert retains some own prior top5 only if current within its top10 and 0.15 current cross-sectional-score-std of rank-5 threshold. F3 changed selections on 12/64 months and H1 on 8/64. Total 26 retained/replaced slot differences versus frozen original. This arm intentionally changes holdings to minimize trading; all other arms preserve original F3 and H1 selected names.

## Verified costed economics
| Method | CAGR | Daily Open MaxDD | daily Sharpe | daily 5% ES | Mean ETF invested |
|---|---:|---:|---:|---:|---:|
| Original F3/H1 50:50 | 23.215% | -24.844% | 0.887 | -3.302% | 100.0% |
| R1 factor balance | 21.988% | -27.132% | .837 | -3.321% | 100.0% |
| R2 volatility 20% | 21.874% | -23.504% | .911 | -3.049% | 94.75% |
| R3 trend126 defensive | 19.292% | -21.990% | .872 | -2.928% | 89.84% |
| R4 rank retention buffer | 23.489% | -25.083% | .895 | -3.310% | 100.0% |

Historical observed trade fee notionals in initial-dollar units: baseline .15156, factor .14689, vol .14247, trend .12784, buffer .14357. Numerically different final capital equity paths reflect returns and fees, not just trading-cost changes.

## Three-anchor block bootstrap of mean per-21-session *net* paired log advantage over static
- R1 factor: -0.00083681; 95% CI [-0.00339345,+0.00156114]; DD is worse by 2.288pp, ES slightly worse. Fails.
- R2 vol20: -0.00091478; CI [-0.00322650,+0.00103144]; DD improves by 1.340pp, ES improves .253pp, but CAGR falls 1.341pp/year. Fails both positive-advantage and strict 3pp-DD condition, early and late both negative.
- R3 trend: -0.00270467; CI [-0.00708630,+0.00067457]; DD improves by 2.854pp, ES improves .375pp, but CAGR falls 3.923pp. Fails all joint return conditions.
- R4 buffer: +0.00018541; CI [-0.00085091,+0.00136305]; CAGR improves .274pp/year but DD worsens .239pp and ES worsens .0077pp. Early monthly mean +.000769 but late -.000519. Fails.

None has positive CI lower bound; **ALL PRECOMMITTED JOINT GO GATES FALSE.** Historical 2021–26 sample has been mined extensively. A single risk-adjusted ratio improvement is NOT evidence of reliable future edge.

## Conclusions and stop/pivot
1. Current crude factor balancing is inferior and should not be promoted. The 8-proxy highest-correlation cluster label can be inaccurate for leveraged, duration, or curve-exposed ETFs; better factor metadata and exposures need genuine timestamped holdings/futures curves before revisiting.
2. Volatility targeting works directionally to reduce risk but here does NOT improve capital growth or the absolute historical 3pp drawdown improvement criterion. It may be a suitable *investor-specific risk budget*, not an alpha source.
3. Simple 126d trend cuts about 2.85pp DD at a large ~3.92pp CAGR cost; **do not adopt** solely because DD improved.
4. Turnover buffer mildly improves annual growth but not materially or reliably and DD worsens. No promotion.
5. Next scientifically sensible step: obtain **new independent PIT universe and price vintages** (including EUR UCITS market), then try genuinely new factor exposure and payoff information; or frame prospective investor drawdown tolerance as an explicit budget for a lower-return portfolio, not claim a historically optimized joint win.
6. Do not try multiple target volatility values, trend lookbacks, signal thresholds or ex-post blends on the same 64 months. This archive is useful for mechanism diagnostics only.

Evidence: source PREREGISTERED.md, script run.py and tests, results/RESULT.json, full daily wealth and original Yahoo factor series, 64 signal states, monthly position weights and SHA256_MANIFEST.txt. Production etf_trader unaffected.
