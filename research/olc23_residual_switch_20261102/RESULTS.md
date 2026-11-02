# OLC23 — differential residual-value switch model: negative result

2 November 2026. Exploratory historical block registered at commit 790e7ccd9e6c4f7a6ee8b69e68ecd7b1453ad766. AUTH ranking/risk contracts remained frozen.

## Verification
- Six chronological annual ridge models fitted under the registered lambda grid.
- All model training rows have both signal and 21-day label availability strictly before the annual cutoff.
- Local suite: 3/3 tests pass.
- AUTH_CONTROL portfolio arrays reproduce OLC20 AUTH exactly.
- Candidate-specific V6 is rebuilt and checked for primary overlap.

## Decisions
The recursive residual-veto policy differs from AUTH on 32 of 90 EU signals and 28 of 90 USA signals. It materially lowers turnover but often retains the wrong outgoing ticker.

Causal out-of-sample edge diagnostics for 2021–2024:
- EU: 66 matched replacement edges; predicted keep rate 69.7%, observed positive residual rate 39.4%, sign accuracy 39.4%, prediction/outcome correlation -0.100.
- USA: 76 edges; predicted keep rate 63.2%, observed positive residual rate 40.8%, sign accuracy 51.3%, correlation -0.044.

The model therefore has no useful common calibration in the primary period.

## Economics — 2021–2024, fee .001

| Contract | EU AUTH | EU DIFF_RIDGE | USA AUTH | USA DIFF_RIDGE |
|---|---:|---:|---:|---:|
| ALARM | 22.087% | 15.820% | 45.507% | 4.834% |
| FAST_LOCK3 | 23.200% | 16.853% | 50.772% | 5.898% |

FAST_LOCK3 MaxDD changes EU -28.61% to -33.25% and USA -20.23% to -47.11%. Annual turnover falls EU 12.41 to 9.01 and USA 23.32 to 14.65, but saved turnover is overwhelmed by selection loss.

Fee .003 remains strongly adverse:
- FAST_LOCK3 EU 19.884% -> 14.366%
- FAST_LOCK3 USA 42.733% -> 2.260%

Full 2019–July2026 remains adverse:
- ALARM .001 EU 18.573% -> 15.519%; USA 39.554% -> 16.921%
- FAST_LOCK3 .001 EU 19.764% -> 16.666%; USA 39.484% -> 15.269%

## Diagnosis and decision
The fixed 21-trading-day forward-return target is not sufficiently aligned with the portfolio's actual monthly Open-to-Open replacement interval. The veto also compounds recursively after an early keep decision, increasing path drift.

OLC23 is rejected; no threshold is retuned after observing this failure. A separate preregistered follow-up may test an execution-aligned Open-to-Open differential label and explicitly compare pooled versus market-stratified fits using the same small model architecture. This is a new exploratory hypothesis, not a repair claimed inside OLC23.
