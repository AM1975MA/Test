# Predeclared EU120 selector × weights cross-replay — 2026-10-17

**Question:** Does the advantage of EUR-exposure 120 ETF `R_H` (Return-Rank-NDCG + Hybrid Tail) over `H_ONLY` (Hybrid Tail alone) in original common-open audited V2 come from ETF pair selection or from the allocation weight/margin and confidence transitions?

## Immutable model/data contract

Five-variant EU120 fully **refitted** annual OOS predictions (`COMPACT_REFITTED.parquet`, `HYBRID_REFITTED.parquet`, `TRAINING_AUDIT.csv`, `RESULT.json`, reference `H_ONLY_EQUITY.npz`, `R_H_EQUITY.npz`) are from certified Actions run **39064123941**, artifact `eu120-compact-return-tail-refit-full`. Original 120 ticker candidate snapshot and manifest `data/eu120` unchanged, frozen original149 run 36551650325 used **only** for market references SPY HYG IEF BIL SHV; zero fit/retraining, no new Yahoo calls, no user production change. 112 completed EU120 common-open signals, 2432 daily V2 sessions, 120 ETFs, and all 5 previous strategies' scores/weights unchanged.

## Registered counterfactual arms (exact original audited V2)

For **selection** S and **weight schedule** W computed from preexisting original `producer.allocations_from_score` on the full identical 120 ETF signal matrix:
- `H_H`: S=Hybrid-only, W=Hybrid-only, canonical original control;
- `R_R`: S=Return-Rank+Hybrid, W=Return-Rank+Hybrid, canonical original control;
- `H_R`: ETF pair from H, `base.weight1` and `base.margin` from R;
- `R_H`: ETF pair from R, `base.weight1` and `base.margin` from H;
- `H_HALF`: ETF pair from H, .5/.5 first/second and zero margin, retains the rest of V2;
- `R_HALF`: ETF pair from R, .5/.5 first/second and zero margin, retains the rest of V2.

These are diagnostic interventions. Original risk transforms `g`, per-selected-pair ExtraTrees+XGB agreement, subsequent `m.conf_weights`, V6 alternate construction, source open/low/close, no-common-open trade deferral, turnover and .001 transaction cost are **recomputed without editing** their original functions. A borrowed score's `margin` and `weight1` are not production deployable without a corresponding signal; interpretation cannot claim exact pure causal effect of a single rule.

## Fail-closed checks
1. Verify frozen EU120 provenance manifest, immutable prediction files hash, training fold maturity strictly before cutoff for all 10 years, 120 unique candidate names, zero overlap Original149.
2. Exact identical dates/equity/turnover arrays for H_H versus frozen H_ONLY and R_R versus frozen R_H, tolerance absolute ≤1e-12. Published H_ONLY (CAGR 7.6299738727%, MaxDD −30.0263068552%, Sharpe .51005441) and R_H (CAGR 12.0350274048%, MaxDD −34.2686626362%, Sharpe .7018142452) MUST reproduce, else reject all outcomes.
3. All arms identical tradeable days/calendar of 2432 sessions; 112 monthly signals. Daily selection IDs must stay unchanged between H_H, H_R, H_HALF and independently R_R, R_H, R_HALF. Constant-weight controls must always assign 0.5 weight1 except where no position active. `H_H`/`R_R` archived parity before any claims.
4. Write per-arm equities and trade/selection/weight/margin diagnostics, per-year returns and aggregate economic table, year-by-year paired deltas, # dates differing in top1/top2, weight change summary, and 2017–2026 consistent calendar. Compare cost and maximum drawdown as well as CAGR/Sharpe. Source study's independent top2 monthly 50/50 (H_ONLY 8.88% vs R_H 8.68%) stays separate and isn't silently treated as the canonical V2 strategy.
5. No fitting/tuning, fixed six arms, no change to user production, **PR draft**. If any source or parity gate fails, end the Action with failure.

**Research limitation:** EU120 universe members were selected ex post with information through July 1, 2026, so this is a historical mechanism diagnostic, not future-investability or an independent time-point holdout. The 120 ETFs are European-exposure rather than guaranteed EUR-quoted, and the source is one Yahoo data vintage. No forward profitability claims.
