# OASIS 150 — preregistered new-universe evaluation (2026-10-18)

**Hypothesis:** Does the frozen OASIS V1 price-only opportunity/crisis model generalize from a retrospectively curated Europe-listed 60-ETF cohort to 150 history-complete US-listed/global/multi-asset ETFs, without changing its parameters?

## Exact source and completeness-only universe
- Two *same-vintage* repositories: `evidence_v1/data/original149` (149 ETFs) and `evidence_v1/data/holdout70` (70 ETFs), both frozen `UNIFORM_YAHOO_FRESH_RAW` with same-row Adj Close/raw Close adjustment to OHLC and raw Volume, collected for 2004-01-01 to 2026-07-31. The two manifests document hashes and original source provenance.
- Do **NOT** merge `data/eu120` (120 European-underlying candidates), because that source has another vintage and its ETF universes were already selected with different inclusion constraints; mixed data vintages can introduce artificial relative opportunity.
- Exact candidate pool = union of those 219 source lists. Fail on duplicate ticker or hash mismatch. ETFs are US-listed ETFs with diverse underlying exposures, not strictly Europe-only. No Argentina or other geography filtered based on whether subsequent returns look good; the task is an *unrestricted 150 ETF completeness* test.
- Frozen quality selection window 2017-02-01 to 2026-07-01 inclusive; require at least 252 valid OHLC sessions at or before 2017-01-31 and an observed valid Open/Close on 2026-07-01 (if missing, fail candidate, no lookahead price interpolation). Valid OHLC = strictly positive finite open/high/low/close with nonnegative finite volume; duplicate dates are rejected. Publish excluded candidate reasons.
- Order survivors by (1) **2017–2026 valid OHLC observation count DESC**; (2) number of positive-Volume rows in same period DESC; (3) pre-2017 valid history count DESC; (4) ticker ascending. Select exactly first **150**, never use log returns, CAGR, drawdown, model scores, sector/alpha performance or the old 60 ETF roster to pick winners. Output full 219-quality census, 150-member roster, source SHA256 receipts. Future data availability is used in *universe curation* only — a retrospective survivor/completeness bias; this is not deployable PIT universe selection.
- If fewer than 150 instruments qualify, do NOT silently reduce N or violate the published rules. Mark BLOCKED with count and reasons; create a separate revised preregistration before any run.

## Frozen OASIS V1 signals and tests
Exactly reuse `oasis/observers.py` and `oasis/daily_backtest.py` with NO changes to ranking/lookbacks, crisis thresholds, Student-t proxy, 5-session cooldown, 95% Bonferroni economic margin, two ETF positions, 50%-cash hypothetical crisis scale, fees 0.10%/side and daily next-open execution semantics.

Only changes to execution wrapper: supply alternate `--universe`, `--source-dir`, fixed start/end and `--min-open-count`; original 60 default unaffected. Use complete common daily-open calendar where at least 120 of selected 150 have valid Open+Close. All seven policies execute on identical sessions; no future Open used in decisions. Mark retained positions using no more than five-session carried last Open; report stale/open-zero-volume trade risks.

Seven *matched on 150* arms:
- P0 monthly simple raw-price score Top2.
- P1 daily greedy score Top2 with no gratuitous unchanged-holding rebalancing.
- P2 daily economic Bayesian-uncertainty-proxy hysteresis.
- P3 P2 + dynamic shock/crisis exposure reduction.
- P4 P0 + same daily crisis exposure reduction.
- P5 daily Top5 hysteresis.
- P6 P2 + BOCPD shock guard.

**No baseline from old EUR60/H7 can be economically compared directly**, because universe, exchange, currency, cohort and path differ. All 150-arm comparisons are internal.

## Acceptance, falsification and statistical contract
Synthetic no-lookahead, stale incumbent, missing opens and numeric equity tests must pass. A 150-ETF quality manifest must exist and be SHA hashed before the backtest. Source file count must be exactly 150; no model old LM predictions or performance-driven universe selection. Report CAGR, daily MaxDD, Sharpe, 5% empirical daily expected shortfall, fees, counts of name switches and blocked orders, crisis-regime counts, 2017–20/2021–23/2024–26 slices and paired 12-month circular block CI. Same 0%-yield cash assumption.

Compare not only winner but **interaction**: P2−P0 incremental opportunity switching, P4−P0 crisis only, P3−P2 crisis on switched assets, P3−P4 active switch after same crisis control. If P3 fails, do not retune the old 150 years to force alpha. Examine per-regime forward relative rank skill and actual 21-day post-switch replacement if feasible; distinguish ex-post audit from a new strategy.

## Limitations
- The supplied frozen source ETFs may be traded in USD, not EUR. No bid-ask, verified adjustments in execution quotes, actual volume liquidity validation or tax/FX cash. Do NOT call the result directly implementable for an Italian investor.
- Selecting by whole-period data completeness excludes failed/delisted funds; may create survivorship bias and is not a prospective holdout, even if no returns entered the selection rule.
- Existing OASIS decisions and market limits were iteratively explored on EUR60, so 150 same-vintage different ETF panel is **out-of-universe transfer evaluation** but NOT a fully independent hypothesis-untouched experiment.
- If action returns no valid results due to source gap issues, repair *data contract* or loader only and document; do not change signal thresholds post-results.

## Persistence
Keep frozen roster/census, source SHA manifest, full daily ledgers, scenario/regime states, results and explanatory report on `research/oasis150-coverage-20261018`. GitHub Actions artifact alone expires; commit meaningful source/results and SHA into isolated research branch, no modification to original OASIS path on its parent branch.
