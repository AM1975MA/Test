# Original149 Tensor 5D — completed 2017–2026 annual walk-forward (2026-10-20)

## Exact frozen test
Source branch: research/original149-tcn-listwise-20261020; code: tensor149_tcn5d. 149 original US-listed ETFs; manifest-checked adjusted OHLCV; canonical 125 feature daily panel; 30-session temporal TCN. Realized target five tradable sessions from D+1 open to D+6 open. Expanding annual refit, preceding year groupwise validation, future-matured targets strictly purged. 476 OOS weekly equal-support decisions over 2017–2026 through July 1 2026 maturity cutoff; costed nominal next-open Top5 long-only equal-weight, conservative 10bps each entry and exit.

Both original prior Simple Pointwise TCN and three new Listwise candidates use same TinyTCN architecture, train-only normalization and frozen seed; objective is the only designed model change. Historical data already mined: these are not independent forward results.

## Verified full annual 2017–2026 results

| Objective | CAGR net | MaxDD | Sharpe | Mean weekly rank IC | true top5 overlap |
|---|---:|---:|---:|---:|---:|
| Past 21d momentum | +13.4143% | −34.9415% | .62525 | −.00565 | 13.03% |
| Frozen TCN SmoothL1 pointwise | +5.1942% | −48.4929% | .32852 | +.05609 | 6.26% |
| Frozen Ridge 125 features | +5.1314% | −50.4393% | .33096 | +.05434 | 6.51% |
| ListNet all-name | **−3.9327%** | −61.9062% | .02137 | +.00367 | 17.02% |
| ListMLE top5 Plackett-Luce | **−5.2037%** | −62.6629% | −.02344 | +.00324 | 18.49% |
| ListNet + normalized return Huber | **−1.5821%** | −62.7551% | .10495 | +.00822 | 17.86% |

Full prospective-style annual chronological fold matrix and all trained checkpoints/every OOS ETF score: https://github.com/AM1975MA/Test/actions/runs/39457504782

Historical full Pointwise frozen comparison: https://github.com/AM1975MA/Test/actions/runs/39455244701

## Verdict
All three registered Listwise 5D losses fail full-window economic screen vs Pointwise and naive past21-momentum; do not promote or merge in production. Their ability to capture realized extreme Top5 names is high even when long-only portfolio net returns are poor, matching the risk-only 21d/63d volatility negative control behavior. RankIC deteriorates substantially relative to Pointwise. Results show that optimizing the realized top5 list does not optimize expected benchmark-relative net reward or downside without explicit risk conditioning. Pilot 2024-2025 remains in RESULTS_PILOT_20261020.md; its favorable 22%–27% CAGR does not generalize to 2017–2026.

## Full risk-only 5D negative controls, same 476 decisions
- High trailing vol21: CAGR −6.4598%, MaxDD −58.7611%, Top5 overlap 19.50%.
- High trailing vol63: CAGR −3.7874%, MaxDD −56.3748%, Top5 overlap 18.40%.
- High trailing downvol21: CAGR +1.5676%, MaxDD −49.8535%, Top5 overlap 15.80%.
Source https://github.com/AM1975MA/Test/actions/runs/39458064851

The relatively good ex-post winner hit rate is consistent with volatility preference. A claim of extra predictive tail alpha would require risk-matched controls, independent forward data and stabilized regime dependence. Original149 has universe survival/selection bias and Yahoo OHLCV adjusted open prices cannot certify live fills. No live deployment recommendation.
