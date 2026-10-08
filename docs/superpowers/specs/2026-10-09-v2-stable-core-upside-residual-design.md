# ETF Trader V2 — Data / Superpowers: Stable Core + Upside Residual Expert
**9 October 2026 — ARCHITECTURAL DESIGN AND READ-ONLY COMPLEMENTARITY AUDIT, NOT AN INVESTMENT-GRADE TEST**

**Repo:** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`. No source-only production change, no additional model fitting or historical portfolio backtest. Earlier two-stage LTR cascades, Top10 rerankers, fixed 75%/25% capital split and paired XGB/Ridge score fusions are **already tested**; do not repeat.

## 1. User's central idea

**Split the objectives:** a robust core seeks consistently useful cross-sectional assessment with low training-data-vintage variance; a second opportunity specialist seeks rare, nonlinear positive-tail upside missing from the core. They should **both score the complete as-of eligible ETF universe**, not make a destructive Stage1 TopK shortlist. A third small portfolio decision gate mediates residual alpha/risk only on genuinely validated incremental benefit. This is **not** equivalent to (a) hard 149→38→1 cascade, (b) constant 75% Ridge /25% XGB capital split, or (c) arbitrary weighted average of native rank scores.

**Why a regularization-only ranker is insufficient:** existing L2-D on native matched Compact21 horizon21: XGB 19.1740% of decisions selected an ETF in the ex-post true Top5, versus Ridge 7.9646%, whereas under matched input Ridge Top1 is 100% cross-vintage stable and XGB only 45.13–56.64%; a stable ranker alone can erase extreme-winner capture. These are **component-level hit rates**, not full V2 CAGR.

## 2. Fresh read-only audit of EXISTING frozen native L2-D scores (data evidence)

Inputs were already obtained and trained in L2-C/D:
- `etf_l2d_xgb_vs_ridge_results.zip:l2d_delivery/l2c_reference/PREDICTIONS.csv.gz`: OOS Ridge `pred_rank_pct_21`, outcome `net_ret_21`, `exit_date_21`, per-ticker date vintage.
- `etf_l2d_xgb_vs_ridge_results.zip:l2d_delivery/l2d_results/XGB_NATIVE_PREDICTIONS.csv.gz`: the matching XGB `pred`.
- Exact inner-join keys: `signal_date,ticker,vintage`. Filter `2017-02-01 ≤ signal_date ≤ 2026-06-30`, `exit_date_21 ≤ 2026-07-31`. Date-grouped lexicographic tie-break `np.lexsort((ticker,-score))` identical to L2-D original evaluation script; truth is Top5 by realized 21-session `net_ret_21`. 149 ETF candidates per decision.
- **50,511** joined ticker predictions; **113 months × 3 Yahoo acquisition vintages = 339 decision-vintage groups**. These 339 are **not 339 independent financial months**; only 113 unique market dates.

| Measure | Count / 339 | Percent |
|---|---:|---:|
| Ridge Top1 in ex-post Top5 | 27 | 7.9646% |
| XGB Top1 in ex-post Top5 | 65 | 19.1740% |
| **At least one of Ridge Top1 or XGB Top1 in ex-post Top5** | **84** | **24.7788%** |
| Both Top1 candidates in Top5 | 8 | 2.3599% |
| XGB Top1 in Top5 but Ridge Top1 not | 57 | 16.8142% |
| Ridge Top1 in Top5 but XGB Top1 not | 19 | 5.6047% |
| Same Top1 selected by both | 25 | 7.3746% |
| Both candidates miss Top5 | 255 | 75.2212% |

Breakout, **each vintage only 113 decisions**:

| Vintage | Ridge Top5 hits | XGB Top5 hits | Union candidate hits | XGB-only hits | Ridge-only hits |
|---|---:|---:|---:|---:|---:|
| Repeat1 | 9 | 19 | 27 | 18 | 8 |
| Repeat2 | 9 | 22 | 27 | 18 | 5 |
| Repeat3 | 9 | 24 | 30 | 21 | 6 |

Control: Ridge hit `27/339` and XGB hit `65/339` exactly match original L2-D `SUMMARY.json` reported 0.0796460 and 0.1917404. Mean native selected next-21d net-return difference XGB minus Ridge over 339 groups +0.699 percentage points (identical to L2-D means 2.4605% vs 1.7618%). Do not multiply this by twelve or call it Annual V2 growth. This is paired read-only remeasurement of already-researched predictions, **not an independent holdout**.

**Correct interpretation:** Two candidate names **contain** a realized Top5 winner more often than either selected name alone. **This is an oracle opportunity ceiling**, since we do not know prospectively which candidate is better. It does not establish that some gating model could realize the 24.78%, or even outperform XGB alone. 255/339 have both candidates *outside* the best five. More than one candidate/turnover may increase costs and risk. It supports further architecture analysis of complementarity, not promotion.

## 3. Three roles — not a hard cascade

**Layer A: stable base, full-universe.**
- A causal annual low-variance model on all eligible ETFs, trained only on mature rows and point-in-time membership, targeting broad expected rank/return (Ridge is a proven *diagnostic reference*, not an automatically accepted final core).
- Its purpose is stability of **assessment, concentration and baseline opportunity**. Score all ETF rows, do **not** permanently discard 75% at Stage1.
- Lock feature schema and normalization. Ridge lost too much top-tail hit rate to be used as the sole investable Core without a separate joint economics gate.

**Layer B: positive-upside/residual expert, full-universe.**
- Predict **incremental conditional positive-tail reward**, not simply today's absolute best ticker or imitation of the canonical XGB outputs.
- Candidate training targets: payoff-above-core after costs with matured prices, or probability and magnitude of being an exceptional top-quantile winner conditional on stable-core score. Use temporally **OOF/prequential** core predictions for all training rows, not in-sample residuals, with source-year and label-exit purging. The core predicted score must be economically calibrated before subtracting returns—never subtract raw XGB ranking scores from actual returns and call them residuals.
- Start research with nonlinear source-compatible XGB specialist *only if* its independent training-X and training-y noise can be characterized; otherwise consider a small explicitly regularized Dense or another nonlinear specialist. Avoid generic standalone top10 classifiers, HGB smoothing, and copying unstable teacher scores.
- Specialist sees **all 149** as-of ETFs, so it can recover candidates that a narrower Ridge list would have deleted. It must retain/highlight high-upside captures without relying on ex-post perfect foresight.
 
**Decision layer: locked capital/residual gate (part of strategy policy, NOT a new ranking proof).**
- Compare prospectively calibrated expected **incremental net value**, expected uncertainty and turnover/costs, with strict no-lookahead as-of features. If no independently validated net uplift, core fallback; if evidence supports the specialist, limited additive/conditional alpha exposure is possible.
- Exactly **one** predeclared gating policy; avoid tuning `lambda(t)`, shortlist size or top-tail quantiles against Golden/Repeat1/2/3 market P&L. The previously tried Ridge75/XGB25 and rank-score 75/25 fusions are negative/insufficient precedents, **not this proposed residual-learner experiment**.
- Crucial: allocation gating contains some economic consequences of an unstable specialist **but does not make its raw predictions intrinsically stable**. The full-V2 drawdown exposure and MA3/governor remain independent constraints. If core-only is weaker than incumbent, a frequent fallback can reduce CAGR.

## 4. Why we must not just repeat 75/25 or Top38

- Existing L2-F stable capital sleeve 75% Ridge/25% XGB, monthly selection-only proxy CAGR Repeat1/2/3 **19.50/19.93/22.37%**, compared with pure XGB **19.58/22.17/31.91%** (same proxy, not full V2). Lower monthly-sampled DD and less vintage spread, but pronounced loss of XGB upside especially Repeat3, **not adopted**.
- Previous cascades with frozen Top5/Top10 rejected. Prior frozen **different retriever LTR** kept future best within Top38 97/114 but missed 17/114; ex-ante trailing dispersion miss-AUC 0.515/0.531, unsuitable gate. A new alpha expert cannot operate solely on a prefiltered set without forfeiting opportunity.

## 5. Revised sequential test plan (do NOT train now)

**Gate 0 — empirical opportunity complementarity, DONE:** This audit proves there exists some candidate complementarity among two already-trained OOS outputs. **Not** a return or model improvement proof.

**Gate 1 — formal problem/target design, no financial fit:** specify annual stable core and OOF target production, as-of universe/year/version and maturity, distinct incremental tail reward; count *effective independent months* rather than treating 149×113 highly correlated ticker/month samples as independent. Compare against already-failed L2-F and HGB/Fourier/reranker designs; do not duplicate.

**Gate 2 — one synthetic risk demonstration:** before training, preregister **one** residual target/architecture and one conditional gate, independent new synthetic grouped fixtures with artificially rare high-tail winners and noise in X-only/Y-only/joint; four essential checks: (1) causal OOF core, (2) material tail capture not worse, (3) cross-training vintage economic decision stability, (4) confusion/turnover and false growth activations. Reject if stable core + specialist collapses to Ridge-only returns or adds unstable trades with no valid uplift.

**Gate 3 — first fresh point-in-time financial trial only with proper new evidence and explicit release approval:** same ETF membership/as-of sources, compare **original FULL V2** versus proposed A+B+gate on exact same dates/fees/MA3/Stage19 risk, plus core-only, alpha-only *as diagnostics*, not candidates to optimize. Metrics: paired net **daily** compounded portfolio outcomes, per-vintage net CAGR *if sample long enough*, MaxDD, trading fees, annual turnover, concentration/tail events, economic regret, true top-decile capture, dollar-exposure rank divergence. **No choosing best gate on reused 2017–2026 Original149 outcomes**.

**Gate 4 — decision:** keep canonical V2 unless prospective same-universe full V2 non-inferiority and robustness preconditions are jointly met; all models/feature/MA3 states versioned and repeatable, new annual or new ETF universe causal `REFIT` allowed.

### Single biggest open question

Can the opportunity specialist learn a **genuinely forecastable conditional uplift** over the stable core, or does it simply transfer the unstable XGB tail speculation to a separate box? Existing combined *oracle* Top5 candidate coverage cannot answer that. That is the highest-value next falsifiable scientific question; if new independent real data are not available, stop at preregistered synthetic/no-financial study rather than hunting parameters on the old market tape.

**No new fit or backtest performed in this design revision. No production repo touched.**
