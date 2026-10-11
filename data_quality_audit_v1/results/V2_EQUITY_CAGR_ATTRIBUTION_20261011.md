# Economic session-level CAGR-gap analysis: 6 frozen V2 executed portfolios (2026-10-11)

## Verified experiment, data provenance
Six identical controlled replay jobs produced original `FULL_UNIVERSE_PATH.npz` equity, executed portfolio d1/d2, weights and dates, plus `DAILY_LEADERS.csv` and original `RESULT.json`, in Actions run [38130407167](https://github.com/AM1975MA/Test/actions/runs/38130407167). All **six V2 replay jobs succeeded**. The aggregate analysis step in that run initially failed *only* due to an archive directory naming mismatch; no model failure. The lightweight attribution replay [38130967028](https://github.com/AM1975MA/Test/actions/runs/38130967028) succeeded using the **existing six frozen portfolio artifacts only**, with no retraining. Archive contains `PAIRWISE_EQUITY_LOG_ATTRIBUTION.csv`, `SESSION_EQUITY_LEADER_ASSOCIATION.csv`, `MONTHLY_EQUITY_GAP.csv`, `TOP_100_SESSION_GAPS.csv`, `REPLAY_METRICS_VERIFIED.csv` and `RESULT.json`.

For each pair of vintages and each alpha, strict 2366-date aligned checks and exact reproducible terminal-equity closure verified. Daily economic log-gaps telescope to the entire log terminal-wealth gap. Sessions were marked discordant when either previous or current date leader Top1/Top2 differs across the pair. This grouping is an **association**, not a causal portfolio-swap intervention or a feature-specific/fit-randomness attribution.

## CAGR and exact log-equity-gap partitions

| alpha | vintage pair | CAGR difference (pp, signed i-j) | discordant sessions / 2365 | signed cumulative log-gap on discordant sessions | on agreeing sessions | share of absolute daily log-gap on discordant sessions |
|---|---|---:|---:|---:|---:|---:|
| .05 | 1-2 | +5.566864 | 1466 | +0.426087 | −0.033013 | 92.18% |
| .05 | 1-3 | +4.071212 | 1652 | +0.431888 | −0.147522 | 95.90% |
| .05 | 2-3 | −1.495652 | 1404 | +0.103542 | −0.212250 | 91.22% |
| 1.0 | 1-2 | −2.491488 | 1515 | −0.330963 | +0.158795 | 90.91% |
| 1.0 | 1-3 | −4.880162 | 1614 | −0.403755 | +0.064450 | 92.30% |
| 1.0 | 2-3 | −2.388674 | 1322 | +0.063276 | −0.230413 | 82.28% |

For alpha=1.0, pair 1-3: exact log terminal wealth difference is −0.339306; partition sum (−0.403755) + (+0.064450) = −0.339306. Therefore the 4.8802pp CAGR spread is *economically concentrated* in disagreement-associated sessions, but the net effect of agreeing days offsets part of this. No claim that replacing divergent decisions with a shared leader would recover 4.88pp is supported.

For alpha=.05, largest CAGR spread is pair 1-2 5.566864pp. The net log gap 0.393074 equals 0.426087 on disagreement-associated sessions minus 0.033013 on agreeing sessions.

Caveats: label is based on recorded daily leaders at current or previous session; actual trading, execution cost and alternate selections are included in portfolio equity but may not be fully represented by the Top1/Top2 label. Daily asset returns and risk-control exposures can diverge with identical leaders, reflected in agreeing-day nonzero contributions. Need **controlled counterfactual fixed weights/frozen model and a repeated same-source fitting test** to isolate causal mechanism. Neither alpha can be promoted from this result. No changes to production Etf_trader.

## Decision
Analysis establishes a strong association between **leader disagreement** and **realized portfolio return-path dispersion**, not proof that leader selection alone causes the divergent CAGR. Next step: focus on a few most economically important dates/months (TOP_100_SESSION_GAPS.csv and MONTHLY_EQUITY_GAP.csv), then build fixed-model reproducibility test and isolate data drift vs model fit drift. Do not select alpha based on this post-hoc experiment.
