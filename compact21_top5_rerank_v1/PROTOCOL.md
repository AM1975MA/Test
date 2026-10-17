# Compact21 Top-5 constrained economic rerank — fixed research protocol

Registered 2026-10-17 **before viewing any outcome from this variant**. Research-only branch `research/compact21-top5-economic-rerank-20261017`, repository `AM1975MA/Test`; no production merges or tuning.

## Question

Does **restricting the previously trained out-of-sample Ridge economic layer to the best five ETF picks selected by the original Compact21 BASE** prevent the large degradation of standalone Top1 observed for the unconstrained `ECON_LAYER_OOS30`, while retaining any independent economic benefit in the unchanged V2 portfolio replay?

The starting `BASE` is unchanged native XGBoost 125-feature annual `rank:pairwise` model, with 3 seeds, hash-verified original annual **OOS** scores `predictive-BASE` from run 37229180477. The economic scorer is the **already frozen, trained and out-of-sample** `ECON_LAYER_OOS30` from successful run 39039845251, not refitted and never retrained on current evaluation outcomes. The raw source snapshots, underlying 149 ETF population, forecast dates and full V2 simulator are unchanged. The 3 Yahoo input revisions are correlated historical observations, not independent markets.

## One fixed variant: `ECON_TOP5_RERANK`

For each month and vintage, deterministically select the **five** (or all if fewer) highest original BASE raw scores, with ascending ticker as tie-breaker. Within this unchanged set of five tickers, sort by already generated `ECON_LAYER_OOS30` score descending (ticker asc on ties); **permute the original BASE raw five scores** to those ETF names in that new order. For all ETFs **outside BASE Top5**, preserve the **exact original BASE score**, original rank, and ticker assignment; do not permit promotion into the Top5. The set of per-date scores is identical to BASE's multiset; their numeric distribution, expected subsequent percentile score normalization and all non-Top5 selections remain exactly unchanged. BASE fallback months where prior economic layer had insufficient OOS data must remain exactly BASE. Underlying Ridge model is not modified: original 0.70 BASE / 0.30 economic blend is used only as within-Top5 ordering comparator, with no new tunable weights. No new features. For a score tie, stable sort by ticker asc; order ties at the BASE top5 boundary deterministically. Verify the preserved Top5 membership, outside scores bitwise, and per-date sorted raw score multiset; report the actual per-vintage/month Top1 changes. The layer is **postprocessing**, not a new training experiment (0 fits).

## Inputs, cutoffs and source lineage

- `predictive-BASE`, original run 37229180477; `compact21-oos-economic-layer-predictive`, original run 39039845251.
- Original OOS 2017–2026, 114 monthly decision dates; predictive quality restricted to 113 mature outcome dates with exit no later than 2026-07-01, checked without filtering forecast decisions.
- Verify original hashes of result manifests, candidate and BASE native/common Parquet predictions against declared SHA256, status, per-year maturity and exact forecast keys and outcomes. Record each input SHA.
- Check original layer trained using only older mature annual BASE OOS predictions: its declared `layer_trainings=24`, `base_fallbacks=6`, per-year source-audit and training fingerprints retained without recomputation; early fallback preserved exactly.
- Preserve complete per-year training fingerprints from original `ECON_LAYER_OOS30` in the new candidate's output manifest for unchanged raw-to-score independent V2 linkage audit.
- Do not use any realized target to form the reranking; future 21-day returns are only for evaluation.

## Predeclared predictive decision gates

Primary: signed 21-session regret vs top-decile future-return mean (lower = better, base-relative), by equally weighted mature signal dates, after vintage mean per date. Secondary: regret vs exact ex-post max, return of selected ETF, exact top1 hit, top5 hit, top-decile hit, top5 prediction/realized overlap, NDCG5 and RankIC. Paired exploratory 3/6/12 calendar-month block bootstrap (1000 draws, seed 20261017), cannot be interpreted as prospectively unbiased due to many earlier historical searches. The predictor qualifies only if primary regret is strictly better than BASE with exploratory 3-month-block 95% upper difference <0; top5-hit no more than 1 percentage point below BASE; NDCG5 not below BASE by more than 0.01; each correlated vintage regret no worse than BASE. Report all negative and positive values, even if no gate passes. Source-level monthly Top1 disagreement, Top5 equality and fraction Top1 changed also reported.

## Predeclared economic diagnostics

Unconditionally run exactly **three unchanged canonical full original149 V2 replays**, one per frozen source revision, from original raw and verified baseline cashflow/MA3 parity; 2366 daily sessions, unchanged execution, costs, risk, other Compact63/Tail/Macro/MA3 signals and allocation. Independently reconstruct all six BASE/candidate equity paths: CAGR, maximum drawdown, Sharpe, year returns, source CAGR spread and daily portfolio Top1 leader disagreements. Economic screen requires mean CAGR >= 95% BASE, mean MaxDD no worse than BASE by over 2 percentage points, mean Sharpe >=95% BASE, and source portfolio Top1 disagreement no higher than BASE; report jointly with predictive screen. No automatic promotion regardless of success. No change to parameters based on test results.

**Limitation:** This is retrospective development research on 2017–2026 outcomes already investigated in earlier runs. Any advancement to real investing requires a separately locked prospective validation.
