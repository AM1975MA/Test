# OLC20 checkpoint04 — final economic replay verified

2 November 2026. Completion of the already preregistered OLC20 validation block; no new ETF predictor or strategy parameter search.

## Completion
- 58 score procedures reconstructed from the persisted 342 annual models; CONTEXT_LAG plus ORIGINAL/CUM_FIT controls give 60 portfolio procedures.
- 480 economic accounts completed; 6240 metric rows across full/subperiod/year slices.
- 32 AUTH/STATIC/ORIGINAL/CUM_FIT account arrays are bit-exact to OLC19.
- Saved interval-return CSV reconstruction maximum absolute error: 9.996e-17.
- 15/15 OLC20 tests pass after score reconstruction.

## Primary 2021–2024, fee .001

Values are CAGR / MaxDD, percent.

### ALARM

| Trial | EU CAGR | USA CAGR | EU MaxDD | USA MaxDD |
|---|---:|---:|---:|---:|
| AUTH | 22.087% | 45.507% | -24.040% | -20.615% |
| STATIC | 20.491% | 40.892% | -24.461% | -20.615% |
| CONTEXT_LAG | 25.592% | 35.529% | -23.084% | -20.615% |
| PENALTY_HALF | 22.906% | 42.934% | -26.800% | -20.615% |
| PENALTY_DOUBLE | 20.090% | 33.779% | -26.120% | -20.624% |
| OMIT_TREND | 21.427% | 34.851% | -25.400% | -20.615% |
| OMIT_VOL | 15.906% | 25.319% | -34.368% | -21.099% |
| OMIT_LEADERSHIP | 18.511% | 29.611% | -27.877% | -23.315% |
| ORIGINAL | 22.216% | 40.868% | -21.458% | -23.530% |
| CUM_FIT | 21.115% | 41.946% | -29.352% | -18.671% |

### FAST_LOCK3

| Trial | EU CAGR | USA CAGR | EU MaxDD | USA MaxDD |
|---|---:|---:|---:|---:|
| AUTH | 23.200% | 50.772% | -28.608% | -20.226% |
| STATIC | 22.478% | 37.068% | -24.764% | -20.362% |
| CONTEXT_LAG | 23.293% | 36.129% | -27.444% | -23.855% |
| PENALTY_HALF | 24.163% | 44.258% | -30.950% | -20.226% |
| PENALTY_DOUBLE | 21.185% | 39.638% | -30.749% | -21.195% |
| OMIT_TREND | 22.361% | 39.530% | -29.629% | -22.025% |
| OMIT_VOL | 17.481% | 29.835% | -37.782% | -21.706% |
| OMIT_LEADERSHIP | 19.132% | 29.756% | -32.693% | -20.327% |
| ORIGINAL | 20.800% | 43.309% | -22.808% | -24.716% |
| CUM_FIT | 23.817% | 30.882% | -28.534% | -22.021% |

## Negative-control counts

| Contract | Fee | EU >= AUTH | USA >= AUTH | both >= AUTH |
|---|---:|---:|---:|---:|
| ALARM | 0.001 | 17/50 | 2/50 | 1/50 |
| ALARM | 0.003 | 17/50 | 2/50 | 1/50 |
| FAST_LOCK3 | 0.001 | 17/50 | 1/50 | 0/50 |
| FAST_LOCK3 | 0.003 | 16/50 | 1/50 | 0/50 |

Counts are descriptive structured negative-control frequencies, not posterior probabilities or search-adjusted p-values. NULL replicas are not candidate strategies.

## Decision
No predeclared robustness variant dominates AUTH in both universes. CONTEXT_LAG and PENALTY_HALF improve Europe in some accounts but materially reduce USA performance. OLC20 therefore closes as validation/diagnostic evidence, not a new promotion. A subsequent exploratory block must be separately registered if it tests score shrinkage/blending inspired by these outcomes.
