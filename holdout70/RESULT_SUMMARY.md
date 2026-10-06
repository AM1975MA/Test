# Holdout70 transfer test — 2026-10-02

## Purpose

Test whether the severe EU120 degradation is mainly caused by European/cross-market data/domain issues or whether the ETF Trader producer fails to generalize outside the canonical 149 ETFs.

The initially requested holdout60 was found to be incompatible with the unchanged MA3 architecture: MA3 uses 7 dynamic clusters with `MIN_CLUSTER_SIZE=8`, plus a defensive sleeve, so at least 56 dynamic names and 8 defensive names are required. The test was therefore increased to 70 ETFs without changing the model constants.

## Frozen universe

- 70 ETFs, zero overlap with original 149.
- 12 names in each non-defensive canonical macro category; 10 in C05 bonds/cash/credit.
- Selection is coverage/category based only; no performance criterion.
- Minimum 1,260 observations before 2017-01-31.
- Data through 2026-07-31.
- Yahoo Finance adjusted OHLC quality gate and maximum absolute adjusted daily return 25%.
- Frozen data Action run: `36994684932`.
- Frozen artifact: `holdout70-frozen-20260731`, artifact id `11221147818`, sha256 `f9835af66f0906f46bf1904c1b54f45dacd9997e8bfe9ea84dcdb5943d3b00b8`.

## Causal retrain

Full expanding walk-forward retrain Action run: `36994971393`.
Result artifact: `holdout70-causal-retrain-results`, artifact id `11221559642`, sha256 `77a38097f58d95524b14fd2a1f1e6fb4ba876683fc0ed58f334a7af6f01bbb4c`.

Period: 2017-02-01 through 2026-07-01. Target labels are used only after their exit date has matured strictly before the fit cutoff.

| Strategy | CAGR | MaxDD | Sharpe | Terminal equity | Annualized turnover |
|---|---:|---:|---:|---:|---:|
| Annual | 11.2449% | -33.0743% | 0.5543 | 2.7197x | 14.0822 |
| Monthly | 16.0513% | -29.5472% | 0.7374 | 4.0457x | 13.5774 |
| P42 50/50 | 11.3350% | -32.0644% | 0.5641 | 2.7404x | 13.5719 |
| P45 | 12.9543% | -31.6376% | 0.6209 | 3.1383x | 13.4460 |
| Equal-weight buy & hold | 10.6198% | -31.9439% | 0.7496 | 2.5795x | n/a |

For reference, canonical original149 historical research has Annual ~43.15%, Monthly ~37.06%, P42 ~44.75%, P45 ~46.96%. Audited EU120 has Annual ~4.48%, Monthly ~5.07%, P42 ~5.63%, P45 ~5.13%.

## Immediate interpretation

1. EU120 has an additional domain/data/category/calendar problem: holdout70 does not collapse to ~5%.
2. The huge original149 edge does not transfer intact. Passive holdout70 return is ~10.62%, close to the original149 passive universe, yet Annual falls to 11.24%. Therefore passive opportunity alone cannot explain original149's ~43% Annual result.
3. Monthly transfers materially better than Annual: 16.05% vs 11.24%.
4. P45 does not identify this cleanly enough and reduces Monthly from 16.05% to 12.95%.

## Score-level diagnostic

Using the saved prediction panels and frozen adjusted opens, the canonical score was reconstructed and compared cross-sectionally with the next rebalance interval return. This is a diagnostic only; it is not the certified strategy replay.

- Annual mean monthly Spearman rank IC: ~0.095; positive in ~61.8% of evaluated months.
- Monthly mean monthly Spearman rank IC: ~0.098; positive in ~61.8% of evaluated months.
- Approximate simple monthly-rebalanced equal-weight CAGR of the top-2 ranked names:
  - Annual score: ~17.8% (first two warm-up intervals excluded in like-for-like diagnostic).
  - Monthly score: ~21.4%.
- Corresponding equal-weight universe proxy: ~10.2%.
- Bottom-5 ranked names: ~4.8% CAGR proxy.

This means the producer retains real cross-sectional ranking information on the disjoint holdout70. A substantial fraction of that raw ranking edge is lost after the full allocation/risk/stop execution layer.

## P45 router diagnostic

From `ROUTER_TRACE.csv` and `SHADOW_SKILL.csv`:

- Mean P45 monthly weight: ~0.679; median ~0.704.
- P45 assigns >50% to Monthly on ~79.6% of signals.
- Monthly actually beats Annual in ~59.3% of realized monthly intervals.
- Binary router-choice accuracy: ~51.3%.
- Correlation between `w_monthly` and the subsequently realized relative Monthly-vs-Annual skill: ~-0.034 (essentially zero).

If the realized Annual and Monthly interval returns are mixed directly using the same causal P45 weights, the diagnostic CAGR is ~14.15%, versus ~13.79% for a direct 50/50 interval mixture and ~16.00% for Monthly alone. The actual score-level P45 replay is lower at 12.95%, showing an additional nonlinear interaction between score mixing and the allocation/risk overlay.

## Working diagnosis

The new evidence splits the problem into three layers:

1. **EU120-specific degradation** — real and severe: category mismatch, shallow/irregular history and cross-market execution/calendar issues explain why EU120 drops to ~5%.
2. **Original149-specific amplification** — also real: the ~43–47% results do not reproduce on a clean, same-domain, disjoint universe with comparable passive return. This requires a dedicated audit for universe/model research-selection optimism and concentration in original149 winners.
3. **Execution/router attenuation on holdout70** — Monthly score ranking contains materially more raw edge than the final strategy captures. P45 is not predictive of future relative producer skill on this holdout and further dilutes Monthly.

Next diagnostic priority: decompose holdout70 from raw score ranking -> producer allocation -> confidence weighting -> drawdown gross -> V6 stop/alternate logic, and run the same decomposition on original149. That is the shortest route to locating where the original149 ~46.96% is created and where the transferable holdout70 edge is lost.
