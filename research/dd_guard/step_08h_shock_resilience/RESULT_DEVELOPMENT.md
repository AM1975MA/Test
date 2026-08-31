# STEP08H — Live Shock Resilience Rotation

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022

| policy | delta_cagr_pp | delta_maxdd_pp | delta_p10_pp | delta_worst_decile_pp |
|---|---:|---:|---:|---:|
| ORACLE_FILTERED_FORCE | +1.252981 | +1.276856 | +1.602243 | +0.679077 |
| ORACLE_FILTERED_STAY_ALLOWED | +3.639933 | +2.012834 | +3.121507 | +2.201780 |
| SHOCK_RESILIENCE_EVENT_TIT_R | -1.750944 | -0.479948 | -0.977540 | -2.117335 |

## Annual deltas — deployable H1
- 2021: ΔCAGR **-3.303129 pp**, Δmean MaxDD **-0.754229 pp**, Δp10 **-1.875974 pp**.
- 2022: ΔCAGR **-0.202950 pp**, Δmean MaxDD **+0.058923 pp**, Δp10 **+0.118844 pp**.

## Mechanism
- 1,124 frozen q95 decisions.
- Empty resilient set: 0.00%; mean/median retained candidates: 5.00/5.
- BIL fallback: 0.00%.
- H1 beats exact FUSION1 event utility in 41.46% of events.
- Filtered oracle beats FUSION1 event utility in 60.32% of events.
- Filtered STAY-allowed oracle stays in FUSION1 in 39.68% of events.
- The filter retains about 66.1% of the STEP08E full basket-local oracle mean-MaxDD ceiling and 63.2% of its p10 ceiling.

## Post-mortem
The filtered oracle chooses BIL as best forced action in only 7.47% of events; in 92.53% one of the filtered ETFs is better ex post. Conditional on an ETF being oracle-best, its median resilience rank is 4/5 and median EVENT_TIT_R rank is 2/5. Exact top-1 hit rate is 16.15% for resilience and 43.85% for EVENT_TIT_R.

Interpretation: live shock resilience is useful as a candidate filter, but neither raw resilience nor EVENT_TIT_R identifies the protective destination reliably enough. The remaining problem is the small-set decision among STAY / BIL / roughly five resilient ETFs.

No 2023+ outcome was opened and no post-result retuning was performed.
