# L00 — Data/feature layer: preregistered experiment and acceptance gates

Date: 2026-10-21. State: **L00 remains open**. This document is written **before** examining the new challenger outcomes.

## Current evidence

The original 125-feature model `LEGACY` and corrected 125-feature model `CORRECTED` have previously been fully refitted annually with a 127-leaf XGBRanker. The old score is numerically identical to an earlier independent archived oracle across **15,198 ETF-months**.

On 101 matured out-of-sample months in 2018–2026, the original model had basket Top-3 35.745% and mean basket CAGR 13.297%; mathematically corrected model had basket Top-3 35.471% and CAGR 12.057%. Corrected-plus-negative-frequency 128-feature model yielded basket Top-3 35.071% and CAGR 10.688%, so **continuous frequency ratios alone are not a successful solution**.

All the above years are already examined research history, NOT a pristine untouched holdout.

## Mechanistic hypothesis

The incorrect legacy `downvol{21,63,126}` did two things:
1. A continuous measure of standard deviation **conditional on negative daily log returns** (not standard downside deviation).
2. A structural NaN routing signal: at least `max(10,h//2)` negative days existed within the window.

The repaired `downvol` is a different well-defined lower partial moment. We must not silently revert its mathematical meaning. Instead we isolate the old information under **new, explicit, correctly named features** and test incremental value, freezing everything else.

## Predeclared variants and exact one-layer control

| Arm | Features | Added information | Training status |
|---|---:|---|---|
| LEGACY | 125 | Original misspecified `downvol` | Previously frozen, independently certified OOS scores |
| CORRECTED | 125 | True zero-benchmark downside deviation | Previously frozen, independently certified OOS scores |
| V3_GATE128 | 128 | Corrected 125 plus three binary `legacy_downvol_valid{21,63,126}` | New 127-leaf annual fit |
| V3_CONDSTD128 | 128 | Corrected 125 plus three conditionally negative-only stds `negative_only_std{21,63,126}` | New 127-leaf annual fit |

Missing price returns remain missing. The gate uses a complete `h`-return window and is one **only** when the original negative-only conditional std is available. The std is explicitly identified as `negative_only_std`, not a risk measure.

**No simultaneous optimization** of leaf count, objective, horizon, tails, experts, macro/RMT, regime selector, allocation, stops or risk overlay.

## Training and measurement rules

- Exactly the same frozen adjusted 149-ETF OHLCV snapshot from run 39482809691, same 500 canonical 24-member baskets, same official seed and basket SHA.
- Train 2018–2026 with January 1 expanding annual train cutoff; only matured labels `exit_date_21 < cutoff`; use the same 21-day forward returns for all variants.
- Source eligibility is always computed **from original LEGACY 125 features** (at least 30 observed). All other variants evaluate the exact same ETF-months; no post-hoc pruning of hard markets.
- Objective `rank:pairwise`, `max_leaves=127`, `n_estimators=360`, seeds `101,202,303`, same calibrated original params.
- OOS measure IC, full-universe Top-1/3, basket Top-1/3, regret, selected excess, year-wise differences. Bootstrap calendar months in shared 6-month blocks, not 500 basket rows. Two new contenders warrant multiplicity adjustment.
- If feature controls fail the sanity check, the entire experiment fails rather than fabricating results.
- Execution replay uses same next-open adjusted prices, Top-2 75/25 weights (or 100% Top-1 if rank gap >=0.12), 10 bps traded cost, no risk, calendar 2018-02 through 2026-07.

## Decision gate

Primary predictive target: **basket Top-3**, requiring both a positive mean uplift over CORRECTED and an uncertainty interval that clears zero **after considering multiple arms**. Secondary checks: rank IC, basket Top-1, regret and instability across years. Economic non-degradation in annual log portfolio returns after cost and maximum drawdown required before promotion.

No variant will be promoted based on one cherry-picked year or post-hoc optimized annual mix. If neither challenger satisfies gates, **L00 remains CORRECTED AS RESEARCH BASELINE with no ranking superiority claim**, not an invented champion. Refine the *next preregistered single-family* experiment only after archiving this result.

This stage is intentionally **exploratory in a researched calendar**; production V3 promotion additionally requires a new unexamined raw vintage or a genuinely untouched future holdout.

## Provenance

- Source-only corrected V3 copy: `src/etf_trader_v3/source_only`.
- Original V2 source oracle for training label/eligibility: `/regeneration/campaign/etf_trader/source_only` (main).
- Controls: [frozen original-vs-corrected 9-year refit](https://github.com/AM1975MA/Test/actions/runs/39515716383).
- [Documented prior frequency failure](https://github.com/AM1975MA/Test/blob/research-v2-negative-frequency-20261021/regeneration/V2_NEGATIVE_FREQUENCY_RESULTS_20261021.md).
- Results will be deposited under `reports/L00/` only after Actions OOS and replay jobs both succeed.
