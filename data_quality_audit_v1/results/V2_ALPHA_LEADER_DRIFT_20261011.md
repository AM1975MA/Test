# V2 Alpha Repeatability — ETF Top1/Top2 divergence, 2026-10-11

Status: **CONFIRMED** by GitHub Actions [38129805814](https://github.com/AM1975MA/Test/actions/runs/38129805814) (successful). Re-used six immutable `DAILY_LEADERS.csv` outputs from fully fitted historical V2 replay run [38094477390](https://github.com/AM1975MA/Test/actions/runs/38094477390), for alpha=.05 and 1.0 on all three frozen Yahoo Original149 downloads. No retraining, input change, production edit, or financial revaluation in this run. Validated 2366 exactly aligned unique decision dates in each vintage and each alpha.

| Outcome | alpha=.05 | alpha=1.0 |
|---|---:|---:|
| Dates evaluated | 2366 | 2366 |
| Any Top1 disagreement among the three source vintages | 1183 (50.00%) | 1066 (45.05%) |
| All Top1 selections equal | 1183 | 1300 |
| Any Top2 disagreement among the three source vintages | 1819 (76.88%) | 1777 (75.11%) |
| Difference in Top1 disagreement dates, alpha=1 vs .05 | -117 | |
| Difference in Top2 disagreement dates, alpha=1 vs .05 | -42 | |

The replay CAGR results: alpha=.05 33.9966%, 28.4298%, 29.9254% across three downloads (span 5.5669 percentage points); alpha=1 30.5329%, 33.0244%, 35.4131% (span 4.8802 pp), against baseline original V2 CAGR span 4.9236 pp. Improving Top1 agreement by 117 of 2366 dates has yielded **only a marginal** historical CAGR span improvement over original. The proportion of disagreement is too high to call prediction choices reproducible.

This action also exports precisely keyed `JOINED_LEADERS_ALPHA_*.csv`, `DISAGREEMENT_DATES_ALPHA_*.csv`, `LEADER_DISAGREEMENT_COMPACT_ALPHA_*.csv` and `PAIRWISE_ALPHA_*.csv` for follow-up.

**Caveats:** daily leader disagreement itself is not economic attribution, and daily top1 and top2 columns do not establish executed weights, trade dates or contributions to CAGR. A difference on two consecutive daily observations may or may not represent separate portfolio decisions. No causality assertion (input drift versus model training randomness) follows solely from top1 disagreement. To identify economic sources, join executed position histories and portfolio log return contributions to frozen source/feature changes at the proper as-of timestamps. Need per-feature and held-fixed-model controlled counterfactuals; do not suggest these source discrepancies are solely responsible for CAGR.

Recommendation: **do not promote alpha=1.0 to production**. Follow up on position-level P&L attribution, leader disagreement concentration by month and near-tie margins, and repeated-fitting randomness with fixed source snapshot. No Etf_trader production edits.
