# ETF Trader V3 Corrected — L10.D1 first analytical-only discriminator

**22 Oct 2026: TEST COMPLETE, STANDALONE RERANKER REJECTED.**
Frozen reference/production V2 unchanged. Historical 2018–2026 repeatedly researched:
NOT a virgin holdout. Research-only; **no execution/CAGR** is claimed or used.

## Source audit (recover, do not reinvent the prior analytic research)

The private original `AM1975MA/Etf_trader` contains recovered source-only
`src/etf_trader/source_only/a4_persistence_opportunity.py`,
`a4_phase.py`, `a4_hazard.py`, `a4_rankers.py`, and
`results/A4_SOURCE_ONLY_CANONICAL_RESULT_20260921.json`.
Recovered A4 consensus is the average of fitted survival and momentum ensemble
percentiles; its incumbent bonus is 0.06 / 0.03 / 0 at high/medium/low
consensus, and the opportunity prior is 0.02*(p-0.5). Original A4 Opportunity
is trained LightGBM LambdaRank, NOT an ML-free analytical signal.
Canonical A4 had mean CAGR **14.7263%** vs its matched A0 **14.3887%**,
but below V2 Golden **21.6541%**, and is not production certified.
These figures belong to the earlier A4 independent experiment,
**not** a comparable L10.D1 backtest. L03's specific RMT expert gate failed
run 39674680942; RMT is not promoted through this analysis.

## First isolated L10.D1 intervention

[Predeclared D1 protocol, plus prereg engineering correction](./20261022_L10D1_RESIDUAL_PERSISTENCE_PROTOCOL.md),
[source](../../experiments/l10_analytic_discriminator/evaluate.py),
successful [GitHub Actions 39738471945](https://github.com/AM1975MA/Test/actions/runs/39738471945),
artifact **12408381310**. Original failed engineering run 39738202561
stopped during the synthetic causal-prefix test BEFORE any prediction outcome:
SPY self-benchmark gives a mathematically exact zero residual and 0/0.
Fix recorded pre-outcome: fixed equal-weight SPY/VTI log-return benchmark.
Preceding-shifted 126d market beta; analytic score is residual 63d
cumulative log return divided by trailing 63d residual downside L2 norm.
No fitted ML or future inputs.

Original 149 ETFs and fixed 500x24 baskets SHA
`36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`;
101 mature OOS months, original frozen CORRECTED/Top5 scores from 39700865721,
original certified adjusted daily Close 39482809691. No data rewrite,
no hyperparameter sweep, no lookahead and no transaction-cost optimization.
Synthetic prefix invariance **PASS**, 149 ETF analytic signal coverage
**100.00%** on every tested month, 500/500 basket coverage **100.00%**.

## Independent predictive skill

| Property | Analytic | Frozen CORRECTED comparator | Interpretation |
|---|---:|---:|---|
| Universe monthly Spearman rank IC | **−0.010615** | **+0.038536** | Analytic fails general alpha ordering |
| Within UNION pooled basket candidate Spearman | +0.025192 | +0.034301 | No established improvement |
| Unique UNION ETF-month absolute loss10 ROC-AUC (71 months with both classes) | **0.545084** | **0.397101** | Analytic better *relative to comparator*, but not demonstrably above random |
| Observed unique UNION ETFs per month | 53.505 | same | Avoid treating overlapping 500 baskets as independent |
| Unique severe-loss events per month | 3.723 | same | 30 months have no defined binary AUC |

The initial bootstrap implementation correctly refused to show the
71-event-month ROC-AUC as if all 101 months were informative. Separate
`audit_auc_bootstrap.py` then recomputed resamples over all **101
consecutive calendar months**, retaining months without both risk classes
as missing and using 6-month circular blocks (10,000 draws). This is
post-hoc uncertainty QA only, **NOT a new model or parameter selection**.

- Analytic AUC minus random 0.5: **+0.045084**, CI95
  **[−0.025149,+0.111441]**; not established above chance.
- Analytic minus CORRECTED loss AUC: **+0.147983**, CI95
  **[+0.033963,+0.260158]**; specific restricted UNION population.
- CORRECTED loss AUC minus random 0.5: **−0.102899**, CI95
  **[−0.159509,−0.043207]**. This describes its severe-loss *direction*
  on the selected union, NOT the standalone marketwide risk skill.

## Exact fixed 50/30/20 functional diagnostic (101 months)

`BASE` = frozen CORRECTED Top3;
`UNION_ANALYTIC` = analytic score sorts Corrected Top3 +
distinct Top5 Top3 additions;
`MATCHED_ANALYTIC` = same analytic sorter of Corrected Top3 +
same number of next-ranked CORRECTED candidates.
Union and matched pools have identical member counts each basket/date;
mean extra ETF slots = **1.192931**.

| Outcome | BASE | UNION_ANALYTIC | MATCHED_ANALYTIC |
|---|---:|---:|---:|
| Future winner selected Top3 | **35.4713%** | **38.1465%** | 34.8832% |
| Weight on actual winner | 12.5818% | 13.0505% | 11.9026% |
| Weighted future rank quality | **0.524852** | 0.521726 | 0.525371 |
| Absolute loss >=10% weight | 8.4861% | 8.5057% | **7.4947%** |
| Bottom-three invested weight | 22.1313% | 23.1923% | **20.9770%** |
| Weighted 21D oracle regret | 0.105470 | 0.105262 | **0.104892** |

Calendar-month, paired six-calendar-month circular block bootstrap
6,000 draws, 500 overlapping baskets aggregated *within each month*:
- UNION vs MATCHED Top3 winner capture: **+3.2634 pp**,
  CI95 **[+1.9624,+4.4911]** pp, but this is *relative
  retrieval benefit*, not a proof the analytic head is good.
- UNION vs BASE Top3: **+2.6752 pp**, CI [+0.2195,+5.1525] pp.
- UNION vs MATCHED severe-loss invested weight: **+1.0111 pp**,
  CI **[+0.5388,+1.4919] pp**, a material adverse difference.
- UNION vs MATCHED bottom-three weight: **+2.2152 pp**,
  CI [+1.4036,+3.0387] pp.
- UNION vs MATCHED future-weighted regret: +0.000370,
  CI [−0.000850,+0.001555], no demonstrated improvement.
- UNION vs BASE winner-weight delta: +0.4687 pp,
  CI [−0.6794,+1.6158] pp, uncertain.

### Regime/year instability (descriptive)

Analytic universe IC 2019 **−0.110**, 2020 **+0.120**,
2024 **−0.125**, 2026 Jan-May **+0.041**.
Conditional analytic UNION Top3 hit rate varies:
2020 **30.13%**, 2022 **48.77%**, 2024 **27.65%**, 2025 **47.10%**.
The samples are NOT new independent periods. Very high 2025 performance
must not be used to tune or justify a rule.

## Decision

**REJECT L10.D1 as autonomous full-UNION Top3 reranker or universal
alpha model.** Its general RankIC is negative, unique-risk AUC
does not establish skill above chance, and relative to a matched
capacity/reranker control it raises severe-loss exposure. Retain
its versioned analytic series and full statistics for scientific
audit only, not as a live veto/bonus. L10C remains the valid
candidate-retrieval finding, not proof of investable alpha.

Next single-variable research should retain the whole stack
(CORRECTED general rank, L10 Top5 candidates), audit
original A4 phase/hazard and analytic family separately, and
test a **predeclared pure downside/resilience indicator** for
its own binary risk task before any joint reranking.
Do not optimize the choice across already-inspected 2018–2026
outcomes or claim any independent untouched confirmation.
Only after causal out-of-sample skill is credible should we
try a separately frozen Top3 ranking change or next-open 10 bps replay.

## Complete immutable outputs and provenance

- [Monthly, annual, complete 101x149 ETF-month signal+future-label audit,
  bootstrap, coverage and manifest](./data_run_39738471945/)
- [Sparse-event, paired calendar-block AUC bootstrap](./data_run_39738471945/ANALYTIC_RISK_AUC_BOOTSTRAP.csv).
- [Reproducible sparse-event AUC QA code](../../experiments/l10_analytic_discriminator/audit_auc_bootstrap.py).
- Dataset run **39482809691**, frozen L10 scores **39700865721**.
- Successful D1 model-free test **39738471945**, artifact **12408381310**.
- Failed code-test **39738202561** (self-benchmark, zero outcomes; repaired).
- Archive failures **39738974565** (token placeholder),
  **39739113883** (large file exceeded Linux command argv); both preserved.
  Final successful atomic Git archive **39739293349**.
- Unmodified production V2 and frozen V3 models.
