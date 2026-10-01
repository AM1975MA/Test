# EU120 P45 walk-forward retrain

The frozen 120-name European-exposure universe is in `data/eu120/raw_ticker_csv/` in this repository. It is **not** a 120-name EUR-quoted universe: the separately validated EUR-quoted attachment contains 56 names, with only 20 overlapping this frozen EU120 set. The EU120 selection and quality gate used history through 2026-07-01, so historical membership is ex post. The strict point-in-time universe gate therefore **fails**; these results are research diagnostics, not a certified investable backtest.

Run `.github/workflows/eu120-p45-retrain.yml` to fit expanding walk-forward Titanium and MA3 on the 120 names and replay the Annual, Monthly, fixed 50/50, and P45 posterior variants. Fits use labels only after their exit date and strictly before the fit cutoff. The replay uses the next common observed open after each signal, postpones trades and stops on non-common sessions, warms up the risk state with earlier close history, and ingests router outcomes only after their ending open. Missing model scores are ineligible for selection. The 149-name reference supplies the US risk instruments; its labels do not enter the EU120 fit.

Audited local replay, 2017-02-01 to 2026-06-01, 111 intervals, 228 sessions without all observed opens:

| Variant | CAGR | Max drawdown | Sharpe | Terminal equity | Annualized turnover |
| --- | ---: | ---: | ---: | ---: | ---: |
| Annual | 4.48% | -40.37% | 0.337 | 1.520x | 12.58x |
| Monthly | 5.07% | -30.22% | 0.364 | 1.605x | 12.18x |
| Fixed 50/50 | 5.63% | -32.13% | 0.398 | 1.689x | 11.90x |
| P45 posterior | 5.13% | -32.42% | 0.373 | 1.613x | 12.08x |

The original P45 149-ETF result (46.963% CAGR, -27.065% max drawdown, 1.492 Sharpe) belongs to a different universe and execution setup. It must not be interpreted as the expected EU120 performance. See `AUDITED_RESULT.json`, `AUDITED_ANNUAL_COMPARISON.csv`, `AUDITED_ROUTER_TRACE.csv`, and `AUDITED_SHADOW_SKILL.csv` for machine-readable diagnostics. The legacy runner's `RESULT.json` is not an approved performance output; only `replay_audited.py` produces the audited execution comparison.
