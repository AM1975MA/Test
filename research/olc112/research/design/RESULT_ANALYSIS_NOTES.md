# OLC112 — independent result analysis

## Finding

**The primary PRICE_ROTATION policy fails to improve the frozen BASE account.** In the primary following-Close scenario, whole-period CAGR is **15.90% versus 22.57%** for BASE; common post-warmup CAGR is **10.10% versus 20.01%**, with virtually the same sampled MaxDD, **-36.52% versus -36.51%**. Preserving monthly invested rotation does not fix the long cash-reentry behavior. The experiment provides no discovered alpha and no model promotion.

The secondary TERM_ROTATION path has a more favorable historical return/drawdown tradeoff: post-warmup CAGR **18.32%** and sampled MaxDD **-27.11%**, compared with **16.53% / -28.64%** for STATIC_75. This is a useful secondary observation, and it is preserved. TERM_ROTATION still trails BASE in CAGR, OLC111's term-structure forecast evidence remains negative, and selecting TERM after seeing these account results would be another adaptive selection. It is not validation of the options-information hypothesis.

Sources: [`INDEPENDENT_DIAGNOSTICS.json`](../../results/INDEPENDENT_DIAGNOSTICS.json), [`INDEPENDENT_SCORES.csv`](../../results/INDEPENDENT_SCORES.csv), and the predeclared adaptive [`DESIGN_AND_PROTOCOL.md`](../../docs/DESIGN_AND_PROTOCOL.md).

## Scope and matched dates

The audit reads the **12 completed OLC112 accounts** and independently rechecks the **six existing OLC111 BASE/STATIC_75 control ledgers**. It does not generate new financial paths or fit models. All accounts cover 1,699 sessions from 2020-03-02 through 2026-10-30. Learned overrides become eligible at the 2022-07-01 decision Close; common post-warmup returns begin **2022-07-04**, using the actual preceding **2022-07-01 Close NAV**. All 12 new accounts exactly match same-scenario BASE through readiness.

OLC112 changes one mechanism: invested accounts retain their scheduled monthly selector rotation, while an all-cash account still requires learned ENTRY approval. It was designed after viewing OLC111 and therefore is an exploratory mechanism ablation rather than an untouched holdout. Source-data, saved model-fit, source-study freeze and protocol hashes match the experiment freeze.

The Italian four-curve figure shows the post-warmup account growth on a log scale and sampled drawdown, with the preceding Close anchor explicitly named: [`INDEPENDENT_PRIMARY_POSTWARMUP.png`](../../results/INDEPENDENT_PRIMARY_POSTWARMUP.png).

## Primary account results

Primary execution is the following accepted Close, charging EUR1 plus 15 bp per filled order. Cash has zero return. MaxDD samples the pre-fee and closing account marks. Values are rounded here; complete precision is retained in the CSV/JSON.

| Account | Whole-period CAGR | Whole-period MaxDD | Post-warmup CAGR | Post-warmup MaxDD | Post-warmup mean exposure | Full-cash sessions | Actual filled-order costs |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE / MEAN_ROTATION | 22.57% | -36.51% | 20.01% | -36.51% | 99.77% | 0 | EUR4,029.40 |
| STATIC_75 | 18.38% | -30.08% | 16.53% | -28.64% | 75.40% | 0 | EUR2,633.73 |
| PRICE_ROTATION | 15.90% | -36.52% | 10.10% | -36.52% | 80.24% | 215 | EUR3,220.44 |
| VIX_ROTATION | 12.85% | -36.53% | 5.67% | -36.53% | 68.68% | 344 | EUR3,339.00 |
| TERM_ROTATION | 21.44% | -36.10% | 18.32% | -27.11% | 77.81% | 243 | EUR3,358.94 |

Terminal EUR10,000 account equity is EUR38,816.56 for BASE/MEAN_ROTATION, EUR30,780.90 for STATIC_75, EUR26,735.96 for PRICE_ROTATION, EUR22,379.78 for VIX_ROTATION, and EUR36,499.99 for TERM_ROTATION. PRICE_ROTATION finishes at 68.88% of BASE's wealth, with a 9.91 percentage-point lower post-warmup CAGR. TERM_ROTATION finishes at 94.03% of BASE's wealth, with a 1.70-point lower post-warmup CAGR and a 9.41-point smaller sampled drawdown magnitude.

MEAN_ROTATION exactly reproduces BASE across the entire recorded account history in **all three scenarios**. The independent audit also verifies literal equality of every order-ledger column: 225 primary, 226 double-cost, and 226 Open orders. This is the expected neutral control when the saved MEAN models authorize no discretionary actions.

## The cash spells explain an important weakness

The table compares each primary cash spell with the **actual concurrent BASE account**. The primary comparison starts at BASE's Close immediately before the first recorded full-cash day and ends at the last full-cash Close. It therefore includes the liquidation day. The final column starts at the first full-cash Close and excludes the return into that Close. Both definitions are saved explicitly.

| Account | First full-cash Close | Last full-cash Close | Cash sessions | Next invested Close | BASE return from preceding Close | BASE return from first cash Close |
|---|---|---|---:|---|---:|---:|
| PRICE_ROTATION | 2025-05-29 | 2026-04-01 | 215 | 2026-04-02 | +48.80% | +49.49% |
| TERM_ROTATION | 2024-11-26 | 2025-01-29 | 42 | 2025-01-30 | -7.41% | -5.59% |
| TERM_ROTATION | 2025-06-27 | 2026-04-01 | 194 | 2026-04-02 | +42.48% | +44.93% |
| TERM_ROTATION | 2026-05-29 | 2026-06-08 | 7 | 2026-06-09 | -15.11% | -11.66% |

PRICE_ROTATION stays fully in cash for 308 calendar days between the first cash Close and the next invested Close. TERM_ROTATION's longest spell lasts 279 calendar days by that same convention. The flat cash plateau coincides with a large BASE advance, while TERM's other two primary cash spells coincide with BASE declines. These actual account traces show both the opportunity cost of delayed reentry and episodes in which being out coincides with protection.

**These BASE returns are descriptive comparisons, not causal avoided loss, incremental profit, or additive alpha.** The policies already have different inventory and wealth histories; the preceding-Close convention also includes the sale day. The concurrent BASE path is not a counterfactual that holds every other choice fixed. Do not sum the percentages or convert them into a claimed contribution to the policy CAGR. The audit saves both windows to prevent ambiguity rather than choosing the more favorable one.

VIX_ROTATION has four primary cash spells totaling 344 sessions. Its 194-session late-June-2025 to April-2026 spell is the same long plateau as TERM_ROTATION. Its other spells are 41 sessions in July–September 2023, 42 in November 2023–January 2024, and 67 in November 2024–March 2025. All primary cash spells are fully observed; none is right-censored.

Sources: [`INDEPENDENT_CASH_SPELLS.csv`](../../results/INDEPENDENT_CASH_SPELLS.csv) and the compact parallel-account table [`INDEPENDENT_CASH_CONTEXT.csv`](../../results/INDEPENDENT_CASH_CONTEXT.csv).

## What restoring monthly rotation changed

All comparisons below use the same post-warmup window and compare each arm with its corresponding OLC111 arm.

| Model family | OLC111 post-warmup CAGR | OLC112 post-warmup CAGR | Difference |
|---|---:|---:|---:|
| MEAN | 10.58% | 20.01% | +9.43 percentage points |
| PRICE | 14.02% | 10.10% | -3.92 percentage points |
| VIX | 11.97% | 5.67% | -6.31 percentage points |
| TERM | 10.17% | 18.32% | +8.14 percentage points |

The no-signal MEAN control isolates the baseline-replication mechanism particularly cleanly. Restoring rotation improves TERM materially but worsens PRICE and VIX in this historical sample. There is no general inference that preserving rotation improves the learned policy. The cash-entry rule was deliberately unchanged, and the long delays remain.

Maximum continuous ownership over the full history is 190 sessions for every OLC112 arm, versus 1,104 for OLC111 MEAN, 403 for OLC111 PRICE, and 452 for OLC111 TERM. This is consistent with restored portfolio refresh; it is not proof that actual states perfectly match training support. In the primary traces, the largest absolute standardized FRESH feature is 5.84 for PRICE_ROTATION, 6.18 for VIX_ROTATION, and 5.84 for TERM_ROTATION. These contemporaneous training-scaler diagnostics remain descriptive, not a formal OOD test or a new action threshold.

Sources: the `comparisons`, `held_marks`, and `trace` sections of the independent diagnostics; [`OLC111 result analysis`](../../../olc111/research/design/RESULT_ANALYSIS_NOTES.md).

## Stress results and the secondary TERM tradeoff

Each cell reports **whole-period CAGR / common post-warmup CAGR**. No stress model is refitted.

| Account | Following Close | Following Close, double costs | Following Open sensitivity |
|---|---:|---:|---:|
| BASE / MEAN_ROTATION | 22.57% / 20.01% | 19.71% / 17.26% | 25.75% / 23.23% |
| STATIC_75 | 18.38% / 16.53% | 16.01% / 14.10% | 20.50% / 18.66% |
| PRICE_ROTATION | 15.90% / 10.10% | 13.28% / 7.69% | 18.52% / 12.49% |
| VIX_ROTATION | 12.85% / 5.67% | 10.06% / 3.02% | 15.21% / 7.68% |
| TERM_ROTATION | 21.44% / 18.32% | 18.71% / 15.75% | 23.71% / 20.17% |

TERM_ROTATION improves on STATIC_75 in the two reported post-warmup return/drawdown summaries for normal Close (**18.32% / -27.11%** versus **16.53% / -28.64%**) and double-cost Close (**15.75% / -27.36%** versus **14.10% / -29.22%**). In the Open sensitivity, TERM has higher post-warmup CAGR but a slightly larger sampled drawdown: **20.17% / -28.76%** versus **18.66% / -28.25%**. This is not uniform dominance across the execution scenarios. Nor is exposure exactly matched: primary post-warmup mean exposure is 77.81% for TERM versus 75.40% for STATIC_75.

The full-history comparison is different because TERM inherits fully invested BASE warmup: whole-period sampled MaxDD is -36.10%, worse than STATIC_75's -30.08%. No account meets the 30% whole-period CAGR objective. The Open convention retains its source-volume/executability limitations.

## Filled actions and drawdown periods

Primary counts below are **filled instructions / completed, separated 21-session episodes**. An instruction may contain several ETF orders. Completion requires a historical endpoint at signal+21; separation is greedy by signal date within each action family.

| Account | CASH | FRESH | ENTRY |
|---|---:|---:|---:|
| MEAN_ROTATION | 0 / 0 | 0 / 0 | 0 / 0 |
| PRICE_ROTATION | 1 / 1 | 8 / 7 | 1 / 1 |
| VIX_ROTATION | 4 / 4 | 16 / 8 | 4 / 4 |
| TERM_ROTATION | 3 / 3 | 3 / 2 | 3 / 3 |

All three primary TERM entries have completed endpoints, unlike OLC111's final October entry. In the Open sensitivity TERM has four filled ENTRY instructions but only three completed separated episodes; its last entry is again at the right boundary. No action family reaches 12 completed separated episodes in any scenario. These are temporal-support counts, not independent statistical validation.

The primary PRICE_ROTATION and VIX_ROTATION worst post-warmup drawdowns share BASE's 2026-05-28 peak and 2026-10-16 trough and remain unrecovered at 2026-10-30. TERM_ROTATION's post-warmup worst episode is the 2024-07-16 peak to 2024-09-06 trough, recovered on 2024-11-07 after 82 panel sessions from the peak. Its worst full-window drawdown remains the common BASE warmup episode. Complete sampled episode details and annual returns are retained in the JSON and [`INDEPENDENT_ANNUAL_RETURNS.csv`](../../results/INDEPENDENT_ANNUAL_RETURNS.csv).

Source: [`INDEPENDENT_INTERVENTIONS.csv`](../../results/INDEPENDENT_INTERVENTIONS.csv).

## Independent validation and limits

All **18 account audits** pass complete-calendar checks, native and score-table whole/post metric parity, holdings/cash reconstruction and accepted-source quote support. Across these account ledgers, 56,258 held-asset closes are inspected. The oldest accepted source mark is five calendar days; there are zero held marks older than five days and no positions lacking any accepted mark. Any such violation would block promotion while leaving recorded NAV unchanged.

Maximum absolute discrepancies are EUR1.0914e-10 in reconstructed cash and EUR1.2369e-10 in reconstructed NAV. The largest difference among independently recomputed and saved financial fields is 3.33e-16. OLC112 frozen source/input/model hashes remain unchanged. The audit source and input hashes are also preserved in the JSON.

The shared OLC111 suite passes **77 tests**, including 14 independent metric/accounting tests; the OLC112 policy suite passes **six tests**. A separate read-only review found no material audit defect and independently verified all MEAN_ROTATION order-ledger equalities. Figure rendering was inspected. Reproduce the result-only audit from the OLC112 directory with:

```bash
python -m unittest discover -s tests -v
python src/analyze_results.py
```

Sources: [`analyze_results.py`](../../src/analyze_results.py), [`INDEPENDENT_TESTS.log`](../../results/INDEPENDENT_TESTS.log), [`shared audit helpers`](../../../olc111/src/analyze_results.py), and [`shared tests`](../../../olc111/results/INDEPENDENT_TESTS.log).

The study remains adaptive and historically inspected. It does not repair OLC111's failed forecast information test, rebuild counterfactual outcomes, remove panel survivorship/catalog/vintage limitations, or certify real execution. The primary policy remains a failure; the secondary TERM tradeoff remains a bounded research observation. Neither justifies a claim of discovered alpha or retrospective tuning.
