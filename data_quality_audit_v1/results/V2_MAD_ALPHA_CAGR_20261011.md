# Six independent V2 Canonical Original149 replay fits, 3 Yahoo downloads × two MAD stabilization alphas — 2026-10-11

Run [38094477390](https://github.com/AM1975MA/Test/actions/runs/38094477390) **SUCCESS**: 6/6 end-to-end annual ETF Trader V2 replay jobs and summarizer passed. This is not merely precomputed Compact21 panels: full canonical source-only Titanium and MA3 pipeline rebuilt from each original frozen Yahoo input, using research-only patched shared `rolling_downvol` (full-window annualized downside RMS) and `cs_robust_dev` with denominator max(1.4826×MAD, alpha×cross-sectional population-STD), alpha=.05 or 1.0. For fully tied dates, deviation=0 only if numerator=0. Exact baseline kernel source hash and canonical replay runner hash gated. Same environment / history / split. No production modification.

## Confirmed V2 economic results
| Configuration | Repeat1 CAGR | Repeat2 CAGR | Repeat3 CAGR | Mean CAGR | CAGR max-min spread pp |
|---|---:|---:|---:|---:|---:|
| Original canonical V2 historical baseline | 29.75344775% | 30.84370493% | 34.67707907% | 31.75807725% | 4.92363133 |
| Earlier shared downvol correction only | 36.98139201% | 32.70476300% | 27.96877377% | 32.55164292% | 9.01261824 |
| Downvol cleanup + MAD floor α=.05 | 33.99664188% | 28.42977794% | 29.92542989% | 30.78394990% | 5.56686393 |
| Downvol cleanup + MAD floor α=1.0 | 30.53289201% | 33.02437955% | 35.41305357% | 32.99010838% | 4.88016156 |

For alpha=.05: maxDD [-30.6825%, -35.9985%, -26.5301%], Sharpe [1.17965,1.05459,1.08385], turnover [12.9413,13.3694,13.5008].
For alpha=1.0: maxDD [-27.7010%, -29.5717%, -29.2414%], Sharpe [1.06817,1.13963,1.19312], turnover [13.1503,13.7215,13.0768].

## Interpretation

α=1.0 improves CAGR spread by only **0.04346976 percentage points**, ~0.88% relative versus ORIGINAL V2. Relative to the earlier downvol-only 9.0126 pp this is large, but **not** a meaningful cure versus original V2 (4.9236 pp). α=.05 worsens dispersion to 5.5669 pp while mean CAGR decreases to 30.78%. α=1.0 has higher arithmetic mean CAGR 32.99% but alters more than 1,000,000 historically finite compact _dev cells per vintage (observed in prior stage); this is not an approved production change.

IMPORTANT:
- This experiment **changes the shared downvol and shared cs_robust_dev definitions across source-only model uses**, including any Tail/macro consumers. It does **not** merely read/replace the six specific precomputed TI_COMPACT parquet files. Their controlled representation was an exploratory precursor; direct equality of internally rebuilt panels to the Parquet artifacts is not asserted.
- CAGR dispersion does not directly measure prediction selection agreement; analysis of per-date winner overlap, ranking agreement and label coverage is still needed, as is full input data gate (1,665 otherwise-eligible incomplete Compact21 rows after STD floor and unverified other model inputs).
- Baseline original differs in both downvol and MAD semantics, so differences cannot be attributed to alpha only versus that baseline; isolated alpha comparisons hold downvol correction fixed.
- Backtests are historical hypothetical with potential survivorship, transaction model and evaluation caveats. No external live validity concluded.

## Decision
**Do NOT promote either alpha to production.** The improvement of alpha=1.0 is too marginal, and significant conceptual & feature representation changes remain. Freeze run and move to causal per-date ETF selection instability analysis, as-of completeness, label leakage and full Tail/MA3 source diagnostics. No new tuning for CAGR until input contract certified.

Artifacts: six separate `v2-alpha-<alpha>-repeat-<n>` jobs including RESULT.json, ENSEMBLE_FIT_AUDIT.csv, DAILY_LEADERS.csv, and summary `v2-three-source-alpha-cagr-summary`.
