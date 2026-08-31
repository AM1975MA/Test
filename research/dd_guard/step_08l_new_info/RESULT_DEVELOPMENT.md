# STEP08L — New Information BIL/STAY Gate

**Verdict: REJECT_BEFORE_2023_HOLDOUT.** 2023+ remains sealed.

## Development 2021–2022 vs FUSION1

| Policy | ΔCAGR pp | Δmean MaxDD pp | Δp10 pp | Δworst-decile pp |
|---|---:|---:|---:|---:|
| VOL_FINCOND_ONLY | -2.866637 | -0.540504 | -1.144687 | -1.683753 |
| BREADTH_ONLY | -0.624593 | -0.202503 | -0.419022 | -0.447500 |
| CREDIT_ONLY | -2.328193 | -0.680196 | -0.744819 | -1.177229 |
| ALL_NEW_INFO | -3.212960 | -1.093623 | -1.756185 | -2.000403 |

Primary `ALL_NEW_INFO` fails every promotion requirement. The attribution policies are descriptive only and were not used to select a post-hoc winner.

## Key mechanism
- VOL_FINCOND_ONLY BIL rate: 67.26%; in 2021: 99.46%.
- CREDIT_ONLY BIL rate: 32.92%; in 2021: 62.01%.
- BREADTH_ONLY BIL rate: 9.88%; 2021 stays almost identical to FUSION1 but 2022 worsens.
- ALL_NEW_INFO BIL rate: 50.00%; oracle hit only 32.74%.

Weekly NFCI/STLFSI4 were delayed by 7 calendar days before feature use. All raw inputs were hard-truncated at 2022-12-31 before feature construction. No 2023+ outcome was opened and no post-result tuning was performed.
