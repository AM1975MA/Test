# L2-D: matched XGBRanker canonical vs Ridge stable — frozen plan

Date 2026-10-08. Source: only frozen Original149 Yahoo x3 artifact 11272972639 and existing L2-C scores. Scope repo `AM1975MA/Test`; **no write to Etf_trader**. Neither benchmark nor candidate is promoted by this burned-data experiment.

## Exactly matched split and features
- Original149 vintage 1/2/3; 125 canonical F2D features, same eligible rows >=30 finite features; 21-session next-open target and full next-open maturity; annual expanding cutoffs 2017-2026 strictly `exit_date_21 < January 1 of fit year`; no use of future labels to filter inference.
- Freeze evaluation: same 113 monthly signals in 2017-02 through 2026-06 that mature by 2026-07-31, equal-weight date means (vintages are repeat acquisitions NOT independent markets).
- **Ridge** uses previously frozen L2-C result: `SimpleImputer(median, keep_empty_features=True),StandardScaler,Ridge(alpha=30)`, target continuous percentile rank. No retraining after seeing XGB result.
- **XGB canonical compact21** uses source-only parameters `objective=rank:pairwise,eval_metric=ndcg@3,360 rounds,max_depth=4,eta=.035,subsample=.85,colsample_bytree=.8,min_child_weight=8,reg_lambda=8,reg_alpha=.1,tree_method=hist`; XGB relevance `round(target_rank_pct*100)`, group sizes per `signal_date`, train sorted by `(signal_date,ticker)`, seeds 101/202/303 and mean their raw ranker scores. Each fit runs in isolated process with nthread=1, following canonical worker; actual environment recorded.
- Exclude BIL from label/eligibility *dependency*: BIL remains a tradeable ticker in the original frozen universe, exactly like other ETFs. No BIL return is required to build the target.

## Evaluation / gates
A. Native common date/ticker keys and same selected ETF outcomes: top1 realized net return, realized percentile, exact winner, Top5 winner hit, realized return regret, NDCG@5, Rank IC (mean vintages then equal-weight dates). Additional per-year/per-vintage.
B. Native input vintage stability, pair 1-2 / 1-3 / 2-3: mean per-date rank-MAD of percentile scores, Top1 agreement, top5 overlap. Refit across vintages and score **repeat2 features unchanged** for primary training-only stability. Do not confuse label invariance with fitted model invariance.
C. Paired moving-block bootstrap on *date-averaged* XGB - Ridge metrics, 3-month blocks, 10k draws; 95% two-sided descriptive intervals, NOT multiplicity-corrected promotion evidence. Same choice-specific outcome on each vintage in each date.
D. Single-name next-open 21-session *proxy* cumulative wealth for each vintage, with fixed 0.1% cost on entry and exit and nonoverlapping monthly date continuity **only if exact evaluation exit and next entry align**. Otherwise report gaps and do not present proxy CAGR as canonical portfolio strategy. Full Hybrid24/MA3/baskets/risk frozen replay requires separate source-only adapter and is NOT part of this matched Compact21 component test.

Primary decision criterion: preserve or improve **prediction quality** and especially Top1 realized economic return while dramatically reducing vintage-related Top1 disagreement; stability alone insufficient. Treat historical samples as burned; no production promotion. If a matched parity or integrity gate fails, mark claims provisional and explain.

Deliverables: source/fit manifests, native and common-input prediction vectors, diagnostics, exact coverage, pairwise uncertainty, clear verdict. No optimization in this phase.
