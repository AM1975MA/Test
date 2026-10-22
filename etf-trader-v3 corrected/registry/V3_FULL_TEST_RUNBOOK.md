# ETF Trader V3 Corrected — frozen configuration and full-test runbook

**Date:** 21 October 2026. **Status:** All documented L00–L06 research-gate follow-up tests executed and archived. **L07 integrated execution backtest completed in successful run 39683840686; historical diagnostic only, not production approved.** V2 production untouched.

## Source of truth (machine readable)

- [Complete experiment ledger](./V3_EXPERIMENT_REGISTRY.json): baseline, success/failure/rejection status, GitHub Actions run IDs and artifact IDs.
- [Integration freeze](./V3_INTEGRATION_FREEZE.json): exact configuration, model settings, trusted source data, allowed policy alternatives.
- [L07 preflight](../reports/L07/20261021_INTEGRATION_PREFLIGHT.md): numeric parity checks and mature labels over all required OOS sources, successful run **39676155405**, artifact **12381996439**.
- 149-ETF frozen raw snapshot from run **39482809691**; original 500 baskets of 24, fixed hash in the registry. **No independently unused out-of-time period has been established**.

## Frozen default / allowed alternative for L07

| Layer | Default V3 diagnostic stack | Test status |
|---|---|---|
| L00 | Corrected 125-feature source, 203-field contract | Quality passed |
| L01 | XGBRanker rank:pairwise, 127 leaves, 360 rounds, 3 seeds (101,202,303), reg_lambda=8 | Frozen; 63 leaves, NDCG objective and lambda16 not promoted |
| L02 | 45 distinct Tail input features; logistic top-decile of mature 21/42/63D rankmix, C=.2 with balanced class weight | Frozen specialist; unweighted variant not promoted |
| L03 | Static experts; no market or RMT expert switching | Two supervised regime gates rejected |
| L04 | Preserve separated ranker and Tail scores, no active blending | 50/50, 25/75, OR, RRF and trained meta-ranker not demonstrated superior |
| L05 | ETF selection: Top3 by Tail score, fixed weights 50/30/20 | Fixed candidate reference; volatility modification not promoted |
| L06 | No hard risk veto, no automatic ETF replacement | Default |
| L06 optional variant | Same ETF Top3 names, risk soft weights normalized from original base weights × exp(−3 × causal P(ETF loss >=10% at next 21D)) | Research-only, 53 matched months; NOT promoted |
| L07 | Compare frozen default and optional risk version in full cost-aware trading replay; preserve original V2 as separate control | Preflight only; final backtest not run |

## Complete-test execution protocol — no hyperparameter search

1. **Pin inputs:** use the frozen original 149-ETF universe and historical membership, immutable SHA of 500 baskets, checked vendor corporate-action adjustments. Do not change symbols or ETF start dates silently. If extending the price snapshot beyond July 2026, document the retrieval timestamp and recheck all adjusted OHLCV semantics.
2. **Check maturity:** train each underlying model only on labels with realized exits strictly earlier than each annual training cutoff. Apply the same historical cutoff to all alternatives. Verify by exact `signal_date,ticker,exit_date` match.
3. **Reproduce baseline:** verify archived pairwise Ranker and Tail prediction streams numerically identical to original results. No accidental use of L03 market/RMT gate or L04 score blend.
4. **Replay decisions:** for each signal month and each basket select Tail top-3, weights 50/30/20. For the L06 alternative keep exactly the same three tickers and use solely the train-only calibrated absolute-loss probability; do not replace holdings with ex-post "safe" names. Record positions at each next-open.
5. **Execution:** same next-open convention, adjusted prices and identical trading calendars. Charge consistent real turnover fees (e.g., 10 bps base and separate 20/50 bps sensitivity); make spread/slippage assumptions explicit. Calculate actual realized portfolio turnover including price drift rather than treating target-weight churn as trading cost.
6. **Functional acceptance:** confirm no winner-capture differences due to unchanged membership; compare severe-loss exposure, eventual winner weight, conditional regret, true execution turnover, false alarms and the distribution of out-of-year losses. Evaluate by year and across 500 overlapping baskets using **calendar-block**, not basket-level, uncertainty.
7. **Economic reporting only after freeze:** calculate CAGR, MaxDD, Sharpe, volatility, fees, exposures and stress-test outcomes as consequences of the approved frozen configuration — never feed them back into layer/hyperparameter selection on the same period.
8. **Independent validation:** the 2018–May2026 period was repeatedly inspected. A new later OOS vintage (and ideally independently specified universe or rolling vintages) is required before claiming generalization. A historical integrated backtest can be reported as *diagnostic reproduction*, not statistically untouched confirmation.
9. **Release controls:** L07 release requires all source/contract tests green, frozen scorer hash/version, documented fee assumptions, absent look-ahead/survivorship, and explicit approval. The historical production V2 remains unchanged until then.

## Completed incremental L01–L05 follow-up tests

| Layer | Follow-up run | Result |
|---|---:|---|
| L01 lambda16 | [39675577723](https://github.com/AM1975MA/Test/actions/runs/39675577723) | Top3 35.471% → 34.388%; no improvement |
| L02 unbalanced logistic | [39675781293](https://github.com/AM1975MA/Test/actions/runs/39675781293) | Tail elite Top3 39.798% → 39.649%, AP falls; no promotion |
| L03 63-day RMT | [39674680942](https://github.com/AM1975MA/Test/actions/runs/39674680942) | Expert prediction Brier 0.25395 → 0.27249; rejected |
| L04 OR/RRF | [39674361027](https://github.com/AM1975MA/Test/actions/runs/39674361027) | RRF Top3 42.560% vs frozen Tail 42.747%; no demonstrated improvement |
| L05 bounded 63D volatility weights | [39674584732](https://github.com/AM1975MA/Test/actions/runs/39674584732) | Loss exposure down, winner weight down, churn up; not promoted |
| L07 preflight | [39676155405](https://github.com/AM1975MA/Test/actions/runs/39676155405) | Exact frozen score parity, mature-label controls and risk-candidate matching pass |

**Data risk:** all those test years have substantial post-selection research reuse. Multiple sequential candidate proposals on the same history can create selection bias even when each local bootstrap interval excludes zero. Do not use these intervals as independent statistical proof of a deployable strategy.

## L08 — score-vs-policy factorial diagnostic (22 October 2026)

[Successful run 39685852459](https://github.com/AM1975MA/Test/actions/runs/39685852459), artifact **12386252130**, code `experiments/l08_score_policy_factorial/evaluate.py`. Matched fee-aware 10bps execution of **four fixed genuinely OOS score channels × three predeclared portfolio policies** over full 2018–2026 and common 2022–2026 periods, all 500 canonical baskets. The LEGACY Top2 independent original V2 replay matches exactly (NAV/turnover within 1e-10), 149-ETF labels are identical. Historical exploratory, **NOT a virgin holdout**.

The most important identified mismatch is **forecast objective vs portfolio value**. Although Tail45 Top3 finds the future best basket ETF in 42.75% of baskets vs LEGACY 35.74%, Tail's weighted average future rank is only 0.5129 vs LEGACY 0.5291 (both Top3 50/30/20). Equal-weighted 500-basket aggregate CAGR over 2022–26 at 10bps: LEGACY Top1 25.22%, LEGACY Top2 23.16%, corrected PAIR127 Top2 19.63%, corrected PAIR127 Top3 17.78%, frozen RRF10 Top3 16.77%, frozen Tail45 Top3 13.86%. The V3 relative drag is primarily MODEL/OBJECTIVE, not only portfolio weights. Extreme-winner capture is not synonymous with wealth generation or average rank. Multiple models and policies have been compared ex post; no winning configuration is promoted as new production strategy. Keep LEGACY reference and frozen research stack unchanged. Independent, predeclared newer data required for performance confirmation.


## L10.C — retrieval complementarity (22 October 2026)

Original L10 run **39700865721** and economic run **39701813167** succeeded. Both Top5-alone new rankers remain rejected as final buy-order models. New fixed-size candidate comparison **39703702242** (artifact **12394450375**, permanently archived via run **39705218877**) compares baseline Corrected Top3 against the union with distinct Top5 Top3 candidates, with matched extra CORRECTED rank-4+ candidates as the control. Union adds 1.19293 names per basket; future-best coverage **50.60%** versus capacity-matched **45.3782%** (baseline **35.4713%**): paired six-month-block delta **+5.2218 pp**, descriptive CI **[+3.2712,+7.1447] pp**. However the added names are severe 10% losers **10.4828%** versus **7.1751%** for matched corrected names, with descriptive delta CI [+2.1302,+4.5527] pp. **No investment promotion** or refit. Raw monthly CSV, year table, bootstrap, manifest permanently committed under [L10 data archive](../reports/L10/data_run_39703702242/) and full [L10.C report](../reports/L10/20261022_CANDIDATE_UNION_DIAGNOSTIC.md). The old 2018–2026 years are repeatedly explored, not independently unused. A later fit-only-on-past second-stage selector requires its own frozen preregistration.


## L10.D — analytical mathematics is an independent ranking evidence channel (planned, no tests yet)

The L10.C result establishes **incremental candidate retrieval** by the Top5 expert (+5.22 pp winner coverage against a same-capacity Corrected-only pool) but also extra 10% losers. The next stage MUST NOT be framed as only a new ML classifier: preserve an **independent causal analytical/econophysical discriminator** for relative-alpha residuals, opportunity/persistence, left-tail/crash resilience, RMT state information and rank confidence, with separate functional skill measurement before any fusion.

Read the [pre-registered research outline](../reports/L10/20261022_ANALYTICAL_DISCRIMINATOR_RESEARCH_PLAN.md) and central pending entry `l10-independent-analytical-discriminator`. First recover and audit earlier analytical A0/A4, OASIS, F3/H1/H3 and RMT source lineage; do not silently reproduce abandoned approaches. Remember L03's particular RMT expert-switching model failed; this does not validate an RMT feature or invalidate all analytical research. Freeze the 149 ETFs, 500 baskets, unchanged Corrected ranker, unchanged Top5 candidate scores. Test analytics-only candidate quality and severe-loss skill before any supervised reranking or top-policy change, then compare separate analytical/ML sources one change at a time. All forward outcomes must mature before any fitted cutoff; historical 2018–2026 is reused, not virgin OOS. **Status: NOT EXECUTED, NOT PROMOTED**. No V2 changes.


## L10.D1 — independent residual/downside analytical signal (22 October 2026, completed)

Original authentic A4 Persistence+Opportunity, A4 Phase and A4 Hazard source recovered in private AM1975MA/Etf_trader. The A4 mechanism is partly supervised: do not pass the whole A4 as an analytic-only benchmark. Canonical A4 source-only mean CAGR 14.7263% vs paired A0 14.3887% and V2 Golden 21.6541%, not a confirmed V3 ranker replacement.

First frozen mathematically defined diagnostic (no ML fit, same 149 ETF/500 baskets/101 mature OOS months) succeeded **39738471945**, artifact **12408381310**. The standalone signal is 63-session cumulative market-residual log return divided by downside L2 norm of daily residuals, with shifted preceding 126-session beta to fixed 50/50 SPY/VTI daily benchmark. All 101 months and 500 baskets have 100% indicator coverage; causal-prefix invariance passed. A synthetic test failure due to SPY self-benchmark produced NO outcome results in prior failed run 39738202561, then was fixed and recorded before target examination.

UNION (frozen CORRECTED Top3 + novel Top5 Top3 additions), and MATCHED (same-size CORRECTED next-ranked additions) each re-ordered solely by the new analytic indicator, with unchanged diagnostic 50/30/20 weights. Top3 best-basket ETF capture BASE 35.4713%, UNION 38.1465%, MATCHED 34.8832%. **However** analytic universe RankIC **−0.010615** vs CORRECTED **+0.038536**; UNION weighted loss10 exposure **8.5057%** vs MATCHED **7.4947%**, paired bootstrap delta +1.0111 pp CI95 [+0.5388,+1.4919] pp. Unique UNION ETF-month 21D loss10 AUC analytic 0.5451 on only 71 event-informative months; independent 6-calendar-month paired bootstrap against random 0.5 interval for uplift **[−0.02515,+0.11144]**, so neither reliable risk classification nor superior general ranking is demonstrated. No investment backtest performed for this rejected selector.

**Decision: D1 completed, do not promote/merge.** Mathematical independent evidence channel stays available, but this specific analytic-only residual momentum/downside formula is not a satisfactory two-stage selector. Source, 101-month full signal stream, bootstrap and notes persisted on [L10.D1](../reports/L10/20261022_L10D1_ANALYTICAL_RESULTS.md) and [archived raw files](../reports/L10/data_run_39738471945/). Final durable archive success [39739293349](https://github.com/AM1975MA/Test/actions/runs/39739293349); earlier archive attempts 39738974565 and 39739113883 failed without loss of source/artifact. Continue distinct analytic family (A4 phase/hazard downside state) only under one-change predeclared gates and no retrospective CAGR tuning. The 2018–2026 evaluation remains heavily researched, not a virgin holdout.


## L10.E — corrected research direction: ML rank first, post-selection mathematical trajectory quality audit

**Interpretation correction from user (22 Oct 2026):** DO NOT build an analytical global ranker or replace CORRECTED's full ranking by an analytical score. Keep the original model's ETF order frozen. Apply an independent mathematical check *only to already-selected ETF trajectories*. A title is retained by default; flag and possibly replace only if ex-ante trajectory evidence shows convincing deterioration. The next-ranked frozen ML candidate is the original replacement ordering; Top5 proposals may later be introduced separately. An unflagged title never gets displaced, and the existing Top3 slot weights remain as before.

First one-rule test [L10.E1 report](../reports/L10/20261022_L10E_POSTRANK_TRAJECTORY_RESULTS.md) and [protocol](../reports/L10/20261022_L10E_POSTRANK_TRAJECTORY_PROTOCOL.md), workflow [39742108852](https://github.com/AM1975MA/Test/actions/runs/39742108852) SUCCESS, artifact 12409995955, entire 101x149 trajectory and >45k individual substitution data durably archived to main in [data_run_39742108852](../reports/L10/data_run_39742108852/), successful archive [39742298365](https://github.com/AM1975MA/Test/actions/runs/39742298365). Rule: prior 21-session log price return <0 AND close at least 10% below past 63-session max. Only flagged Top3 names replaced by next unflagged original CORRECTED rank4+; no ML retraining, analytical full-universe reorder, changed weights or CAGR tuning. 149 original ETFs, fixed 500x24 overlapping baskets, 101 mature months, 100% as-of trajectory coverage, synthetic prefix invariance PASS.

**Numerical result:** 56.61% of baskets changed, ~31.92% original capital displaced. Future-best ETF captured in Top3 deteriorated **35.47% -> 29.27%** (bootstrap delta -6.20 pp, CI [-9.05,-3.59]). Future-best weight **12.58% -> 10.18%** (-2.40 pp, CI [-3.56,-1.37]); loss >=10% capital **8.49% -> 6.78%** (-1.70 pp, CI [-3.34,-0.06]). 17.36% baseline invested capital allocated to originally positive-forward-return ETFs was erroneously removed. **E1 rejected** despite risk reduction; a crude drawdown signal erases too many valid ML reversal/recovery selections. No backtest economic performance produced for a failed functional candidate, no V2 reference change.

Next L10.E2 should audit distinct true deterioration vs a *healthy rebound setup* **conditional on originally selected ML candidates**, considering trajectory shape/slope, acceleration, coherence, lower-tail risk and peer context as *separate ex-ante diagnostics*. Before testing any rule, predeclare a single discriminator and threshold mechanism with chronology; primary cost-of-error: wrongly vetoing future winners, then weighted severe-loss reduced vs rank/regret/turnover. New tests on repeatedly inspected years remain exploratory, not virgin confirmation.
