# ETF Trader V2 — Research evidence ledger and non-duplication gate (2026-10-11)

## Scope and method
Source: GitHub repository `AM1975MA/Test`, all pull requests #1–#61, with detailed classification #39–#61 and referenced GitHub Actions artifacts/reports already verified in this research session. **This is a versioned meta-review, not another model experiment or a proof that every historical artifact was re-read.** PR summaries establish *what was attempted*, but numerical claims are recorded as **confirmed** only when a completed run/report was previously retrieved. Several PR descriptions are stale and cannot serve as execution status evidence. The search for a prior complete retrospective by terms `synthesis`, `consolidat`, `research retrospective`, `lessons learned`, `audit summary` did not locate an equivalent PR; file-level existence across every historical branch is **not excluded**. No training and no production edit.

### Evidence confidence notation
- **VERIFIED RUN:** run succeeded, numerical results checked in output/research report.
- **PR-DOCUMENTED:** historical PR documents a designed/completed experiment, but results not independently re-extracted by this audit.
- **PENDING GATE:** rigorous causal, independent-source or point-in-time certification still missing.
- **SUPERSEDED:** prior execution-only, abandoned or superseded research path; should not be counted as a new model finding.

## Complete thematic coverage of PR history

| PR interval | Historical subject | Ledger state | Why it matters |
|---|---|---|---|
| [#1–#8](https://github.com/AM1975MA/Test/pulls?q=is%3Apr+sort%3Acreated-asc) | Initial Titanium live tests, reconstruction and downside formulas | PR-DOCUMENTED; #3 explicitly withdraws invalid previous performance, #6 closed wrong downside hypothesis, #7/#8 successful package verifications | Never treat early ad-hoc CAGR as comparable certified results |
| #9–#15 | Canonical Titanium package re-generation, 150 ETF repair and VUG/PIN history | PR-DOCUMENTED; #9 superseded, many execution-only | Source and universe parity matters |
| #16–#28 | XGBoost version parity, model maturity/targets/regularization, frozen source/basket reconstruction, parameter archaeology | PR-DOCUMENTED; notably [#28](https://github.com/AM1975MA/Test/pull/28) summarizes **21** Compact parameter artifacts already tested | Hyperparameter/regularization archaeology has already been attempted; no blind tuning |
| #29–#38 | Yahoo adjusted-data audit, cluster membership, 21/42/63-day supervised targets, seed aggregation, scoring transforms, official frozen-vs-live recovery | PR-DOCUMENTED; [#38](https://github.com/AM1975MA/Test/pull/38) reports only **43.44%** live-vs-frozen top1 basket match and **15.71%** ordered top1/top2 matches | Explicit prior evidence that model/source regeneration changes selections |
| #39–#40 | EU120 frozen P45 external-universe evaluation | PR-DOCUMENTED; #40 reports annual CAGR 4.48%, monthly 5.07%, fixed 50/50 5.63%, P45 posterior 5.13%; hindsight universe gate FAILED | External holdout is **not** a comparable Original149 stability certification |
| [#41](https://github.com/AM1975MA/Test/pull/41)–[#42](https://github.com/AM1975MA/Test/pull/42) | Compact21 orthogonal feature ablation | PR-DOCUMENTED; #42 is execution-only | Orthogonal feature selection is **already tried** |
| [#43](https://github.com/AM1975MA/Test/pull/43)–[#44](https://github.com/AM1975MA/Test/pull/44) | K12→K16 conditional forward ablation (singles/pairs/triples) | PR-DOCUMENTED; #44 execution-only | Compact subset/forward feature selection is **already tried** |
| [#45](https://github.com/AM1975MA/Test/pull/45) | 2×2 feature/label historical training-source factorial, 10 annual fits, frozen inference | **VERIFIED RUN** 37916159772 exists; detailed effect numbers need re-extraction | Training response to feature and label perturbations **already tested** |
| [#46](https://github.com/AM1975MA/Test/pull/46) | Near-tie Top1 margin vs realized 21-day forward returns, 114 months | PR-DOCUMENTED | Ranking margin/economic near-tie idea **already examined** |
| [#47](https://github.com/AM1975MA/Test/pull/47) | XGB75/Ridge25 blended ranker with independent predictive and stability gates | PR-DOCUMENTED; result thresholds not re-extracted | Mixed Ridge/XGB is **already tested**, do not propose it as novel |
| [#48](https://github.com/AM1975MA/Test/pull/48) | Frozen full-strategy 3×3 BASE/RIDGE/LGBM LambdaRank replays recovered from earlier successful fits | PR-DOCUMENTED: original 37195399755; recovery 37934815636. Specific CAGR matrix not independently re-extracted in this inventory | BASE vs Ridge vs LambdaRank full replay **already executed**, inspect outcome before model suggestion |
| [#49](https://github.com/AM1975MA/Test/pull/49)–[#50](https://github.com/AM1975MA/Test/pull/50) | Source-only downside RMS correction / 3 original consecutive Yahoo snapshots | PR-DOCUMENTED and run-linked | Previous missingness cleanup impacted model quality/stability |
| [#51](https://github.com/AM1975MA/Test/pull/51) | Full source OHLCV/Compact/Tail/Macro/Extra audit | PR-DOCUMENTED; **gate explicitly NOT CERTIFIED**, 178 changing numerical inputs and 14 downvol null-mask-changing derivatives, 123 large price events and 1,905 zero-volume bars still need triage | Existing pipeline data acceptance blocked |
| [#52](https://github.com/AM1975MA/Test/pull/52)–[#55](https://github.com/AM1975MA/Test/pull/55) | Missingness, MAD exact-zero and near-zero continuity | VERIFIED RUNS 38083355019, 38083480515, 38093280854, 38093523739, 38093812635 | 51,814 missing cells among 34,876 eligible; 1,761 zero-MAD _dev cells; floor sensitivity already analyzed |
| [#56](https://github.com/AM1975MA/Test/pull/56)–[#57](https://github.com/AM1975MA/Test/pull/57) | Five MAD/STD alpha floors and exact 6-panel materializations | VERIFIED RUNS 38093992533, 38094232042 | 31,827→33,211 complete 125/125 rows; **1,665 eligible incomplete remain** across each vintage; α=1 changes 1,007,355 formerly finite _dev cells |
| [#58](https://github.com/AM1975MA/Test/pull/58) | Six full canonical V2 replay fits with α=.05/1.0 and corrected downvol | **VERIFIED RUN** 38094477390 | α=.05 CAGR 33.9966/28.4298/29.9254%, spread 5.5669 pp; α=1 CAGR 30.5329/33.0244/35.4131%, spread 4.8802 pp; original V2 span 4.9236 pp |
| [#59](https://github.com/AM1975MA/Test/pull/59) | Three-source portfolio leaders Top1/Top2 disagreement | **VERIFIED RUN** 38129805814 | α=1 has 1066/2366 (45.05%) Top1 disagreement dates and 1777/2366 (75.11%) Top2 |
| [#60](https://github.com/AM1975MA/Test/pull/60) | Rebuilt six actual equity paths and economic association with leader discordance | **VERIFIED RUN** 38130967028 on six successful fits from 38130407167; **note** parent workflow overall failed because first aggregation path was invalid, but all six replay jobs succeeded and corrected independent attribution succeeded | α=1 vintage 1-vs-3 CAGR gap 4.8802 pp, 92.3% of absolute daily log return gap occurred on session-current/preceding leader discordance; association not causation |
| [#61](https://github.com/AM1975MA/Test/pull/61) | Triple identical-raw retraining V2 α=1 | **VERIFIED RUN** 38132305441 | Identical CAGR 30.5328920097%, zero daily top1/top2 disagreement, identical prediction SHA256; different MA3 raw pickle SHA in one trial is unclassified serialization vs numerical difference |

## Cross-experiment verdicts, without re-running work
1. **Numerically deterministic fitting for tested fixed data**: 3/3 fully independent original149 repeat1 XGB fits economically and prediction-hash identical (PR #61). This does not imply that small data revisions are harmless.
2. **Small data variations, large downstream portfolio choice variation**: α=1.0 reduces selection disagreement modestly but still has 45% days any Top1 disagreement and 75% any Top2 disagreement (PR #59), with return-gap concentration on discordant sessions (PR #60).
3. **Source data and feature contract are NOT certified**: PR #51 and #52 explicitly flag Yahoo corporate actions/extreme returns/zero-volume anomalies, lookback completeness, as-of timing and Tail/MA3/Macro/Extra. Do not obscure these with XGB hyperparameters.
4. **MAD flooring not solution**: α=1.0 reduces CAGR spread compared to original V2 by just 0.04347 percentage points while changing >1m previously finite _dev feature values (PR #58).
5. **No validated production improvement**: The prior ablation, hybrid Ridge/LGBM and label factorial experiments exist but their actual outcome matrices must be re-extracted before selecting any architecture; historical development Original149 and non-point-in-time EU120 cannot certify live edge.
6. **Causal mechanism not proven by frozen model/factorials alone**: Historical feature-vs-label results apply to frozen Compact21 experiments; full strategy includes Tail/MA3/Macro/risk and execution. The exact full V2 graph is not isolated by the recent tests.

## Already attempted — Do not propose again without citing a missing control
- Fixed-data repeatability: #61 (and independent determinism checks in #45).
- Feature selection/reduction, orthogonal ablation, K12: #41–#44.
- Feature-vs-label perturbation, frozen inference: #45.
- Top1 score margins and realized outcomes: #46.
- Ridge blends, LightGBM LambdaRank, complete-strategy CAGR comparisons: #47–#48.
- XGBoost versions, hyperparameters, number of trees, seed aggregation, supervised maturity and target horizons: #16, #27–#28, #32–#36.
- Yahoo raw-vs-adjusted and missingness/MAD/downside feature changes: #29, #49–#58.
- Leader disagreement and session-wise CAGR gap association: #59–#60.

## Genuine unclosed prerequisites, ranked

**Priority 0: Recover factual decisions from already existing artifacts** (no fitting). Retrieve the exact per-model full-strategy CAGR, pairwise stability and acceptance gate tables from #41–#48, especially #47 and #48, without assuming its PR description is a numerical result. Reconcile source versions (Original149 corrected downvol vs earlier raw) and prevent invalid cross-era CAGR comparison. Archive a complete source-of-truth outcome matrix, marking missing unmaterialized outputs as not verified. This is *the* appropriate immediate continuation and is intentionally NOT a new experiment.

**Priority 1: Close source quality gate** for 123 >20% price-event observations, 1905 zero-volume bars, corporate-action truth, 1665 remaining eligible incomplete Compact21 rows, and full source-only Tail/MA3/Macro/Extra features, with as-of timing. Distinguish valid source change from recoverable feed error. No synthetic prices, no fillna(0), no future observations.

**Priority 2: Only after Priority 0 and 1**, decide on genuinely untested learning architecture or explicitly declare the present universe/data feeds insufficient for reliable live deployment. Any suggested trial must include a novel falsifiable hypothesis, a counterfactual control missing from historical work, temporal holdout, preregistered predictive stability/quality gates and economic test last—not next-alpha grid search.

## Research workflow guardrail
For any proposed experiment, first search PR titles/bodies, relevant source branches and completed Actions including artifacts; cite the closest historical comparator and explain precisely what it did **not** test. Mark `DUPLICATE` unless a substantive missing control is demonstrably different. Do not order another training job without (1) input-source acceptance, (2) a registered success/failure metric, (3) no overlooked prior result, and (4) authorization to perform the novel test. Production repository `Etf_trader` remains immutable.

### Traceability
GitHub PR index: https://github.com/AM1975MA/Test/pulls?q=is%3Apr
Fully executed recent pipeline action runs: https://github.com/AM1975MA/Test/actions/runs/38094477390 ; https://github.com/AM1975MA/Test/actions/runs/38129805814 ; https://github.com/AM1975MA/Test/actions/runs/38130967028 ; https://github.com/AM1975MA/Test/actions/runs/38132305441 .
