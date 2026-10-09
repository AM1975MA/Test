# COMPACT21_LEARNER_SWAP_V1 — independently recovered complete 9-way economic audit (2026-10-09)

## Provenance and verification
This is the recovery of the original October 4 full replays, NOT a new backtest fitted after inspecting outcomes. The original [run 37195399755](https://github.com/AM1975MA/Test/actions/runs/37195399755) completed 3 benchmark jobs, 3 independent MA3 reference jobs, and all **nine** BASE/RIDGE/LGBM_LAMBDARANK × repeat1/2/3 full raw Original149 runs. The original GitHub workflow failed while committing the benchmark summary (git pull/rebase), so its final summary was skipped. The existing preregistered `summarize.py` and `summarize_full.py` were rerun from immutable original workflow artifacts **without retraining**, in [recovery run 37934815636](https://github.com/AM1975MA/Test/actions/runs/37934815636), which succeeded and persisted `BENCHMARK.json` and `FULL_REPLAY.json` (artifact ID **11617647076**, `learner-original9-full-recovery`).

The independent full summary records `status=COMPACT21_LEARNER_SWAP_V1_FULL_SUMMARY_COMPLETE`, `benchmark_matrix_checked=true`, and `ALL_EVIDENCE_PASS=true` for all three models. Same-repetition canonical MA3 semantic checks, raw-source identity, 2017–2026 label maturity, complete 2,366-day replay coverage, unchanged negative feedback and canonical nonintervened components were verified within that original full-summary pipeline. The three acquisition datasets are sequential snapshots of the *same historical market*, not three independent trials; Original149 has been repeatedly used for research.

## Whole strategy economic replay: 2017-02-01 through 2026-07-01

| Learner replacing Compact21 | Repeat 1 CAGR | Repeat 2 CAGR | Repeat 3 CAGR | Mean CAGR | Max–min CAGR span | Mean MaxDD | Mean daily Top1 pair disagreement |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE XGB canonical | 29.7534% | 30.8437% | 34.6771% | **31.7581%** | **4.9236 pp** | -32.2164% | 31.3750% |
| RIDGE (train-only median impute + standard scale, alpha=30) | 28.2666% | 26.8492% | 23.3595% | **26.1584%** | **4.9071 pp** | -31.7102% | 16.3990% |
| LGBM_LAMBDARANK (frozen params) | 41.0339% | 38.0339% | 31.8263% | **36.9647%** | **9.2076 pp** | -25.1875% | 25.5142% |

LGBM improves the historical average CAGR over the fresh BASE by **+5.2066 percentage points**, the average maximum drawdown is substantially less deep, and the mean daily Top1 disagreement improves from 31.3750% to 25.5142%. However LGBM's CAGR span across vintage copies is **9.2076 pp** versus BASE **4.9236 pp** (approximately **+87% larger**). The preregistered *economic* screen requires a candidate span <=75% of BASE = **3.6927 pp**. LGBM therefore fails the critical stability requirement. Historical mean CAGR cannot compensate for an explicitly failed span gate.

## Locked qualification results (no post-hoc threshold relaxation)

**BASE:** control reference; complete original evidence.

**RIDGE:** complete original evidence, much more stable fitted rankings and daily leaders, but mean CAGR 26.1584% fails the old >=95% of BASE floor (required >=30.1702%), and the 4.9071 pp span fails <=3.6927 pp. Its benchmark quality gate also fails. `RESEARCH_CANDIDATE_PASS=false`.

**LGBM_LAMBDARANK:** benchmark quality/stability passes, including **27.7172%** less diagnostic mean rank-MAD than BASE; `BENCHMARK_GATE_PASS=true`. The full economic screen passes mean CAGR, daily leader stability, mean MaxDD, turnover, and integrity, but fails the sole economic `span_le75pct_base` condition. Thus `ECONOMIC_ROBUSTNESS_GATE_PASS=false`, `RESEARCH_CANDIDATE_PASS=false`, and `production_adoption=false`.

The source/full artifacts and original gate thresholds are decisive; the original workflow failure concerned Git checkpoint persistence and was fixed only by independent read-only recovery. Do not imply that earlier full replays were already qualified; the complete final evidence has now been reconstructed.

## Recent independent experiments, distinct from these whole-strategy replay models
- Frozen training feature/label source attribution [run 37931212920](https://github.com/AM1975MA/Test/actions/runs/37931212920): stabilizing mean rank-MAD via cross-vintage source controls worsened monthly Top1 disagreement; not deployable.
- Native single-vintage 75% XGB / 25% Ridge **rank-percentile** hybrid [run 37933994472](https://github.com/AM1975MA/Test/actions/runs/37933994472): monthly Top1 disagreement 50.00%→40.64%, realized Top1 mean percentile 0.58344→0.59862, but rank-MAD reduction only 10.84%, precision@5 worsens, and its noninferiority confidence bound fails. `STABILITY_PILOT_PASS=false` and `QUALITY_CONSERVATION_PASS=false`; **hybrid CAGR was not computed** and cannot be inferred from these three other models.
- Near-tie diagnostic [run 37933141010](https://github.com/AM1975MA/Test/actions/runs/37933141010): 159/171 BASE monthly Top1 flips occur when at least one model has a weak first–second margin. Ex-post selected ETFs can still have a 4.196 pp median absolute 21-session simple-return difference, which is **not a portfolio CAGR**.

## Research decision and next step
**NO CANDIDATE ADOPTED, production `Etf_trader` UNCHANGED.** The historical LGBM challenger is the most promising *economic* result but its same-history replay spread is worse, which is precisely the instability this project must address. Do not optimize mixtures or adjacent hyperparameters using these already-examined Original149 results. Next scientifically defensible step is an independent fresh-acquisition/source-revision audit and a genuinely disjoint ETF universe and forward-date validation of the frozen learners, with the prior CAGR-span and selected Top1 quality gates unchanged. The previously prepared `holdout100` workflow is not by itself evidence of validated predictive performance. All findings are historical backtests and carry source, selection, survivorship, and multiple-testing limitations.
