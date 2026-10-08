# L2-K — Source-of-edge attribution before any further ML research
Frozen 2026-10-08, **before computing L2-K results**. Scope: ONLY `AM1975MA/Test`, branch `research/target-redesign-level2-v1`, no writes to `Etf_trader`. Original149 development is already burned; purely diagnostic attribution, not an out-of-sample validation. No new learner/hyperparameter search. Prefer final **no alpha evidence** to unsupported claims.

## Inputs and provenance
- 2026 Yahoo three-repeated raw archive, use Repeat2 for a single fully aligned market history, GitHub Actions run 37121749852, artifact 11272972639; per-ticker adjusted Open/High/Low/Close/Volume, `universe.csv` and metadata.
- Fixed **source-generated Titanium** schedule `work/original149/titanium/TIT_R_SOURCE_ONLY.csv` from existing `titanium-repeat-2.zip` artifact `11283503395` (GitHub run `37150436612`), containing 114 dates ×149 and **113 contiguous investable next-open entry-to-exit periods** (Jan2017 signal→July2026 exit). This is **Titanium base component**, not itself the full MA3/Hybrid24 operational portfolio.
- Audit raw input and source CSV hashes, coverage, duplicates, date ordering, causal availability, nonpositive prices; explicitly identify missing/tied cases. All corporate-adjusted prices are downloaded in 2026, so back-history is revised, universe survivorship and 2026 categories may introduce bias.

## Fixed diagnostic allocations
At each closed decision window 2017-01-31 through 2026-05-29, choose Titanium Top1 and Top2 by `TIT_R` descending and ticker alphabetic tie break. Apply **existing source logic** `w1=1.0 if (score1-score2)>=0.12 else 0.75`, `w2=1-w1`. Source `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py` uses this in source-only `simulate` (not a confirmed equivalent to final MA3/Hybrid24 allocation; explicitly label proxy). If any selected ETF has no adjusted next-open entry or exit, report and fail closed, no future-dependent replacement.

Use actual next-open / next-open gross returns without stop/governor. Define exact arithmetic attribution each month:
- market component = SPY Open-to-Open return,
- category allocation = weighted equal-weight category ETF Open-to-Open return minus SPY return,
- **within-category selection** = weighted chosen ETF return minus weighted same-category EW return.
Then `r_gross=market + category_alloc + within_category` exactly each month, with no false allocation of compounded CAGR into additive contributions. All categories use only contemporaneously listed positive-price tickers at entry/exit **for retrospective benchmark calculation**; this is not a realizable point-in-time category index due historical availability and 2026 universe selection. Report equal-weight category group size and missingness. Important: category peers selected using exit availability would entail ex-post universe filtering: compute separate causal entry-eligibility and **fail** months with exit missing rather than silently exclude. Fixed 2026 survivor list caveat persists.

Secondary comparator within chosen category: best **past-only** 12-1 momentum (Close[t-21]/Close[t-252]-1), provided pre-signal history, tie break ticker; compare weighted selected ETF returns to same-exposure category momentum ETF. This checks simple factor dominance but a difference cannot be interpreted as a pure risk-adjusted ML alpha.

Risk diagnostics: same-date pre-signal 63d SPY volatility to segment descriptive high/low via prior 36 monthly samples, and tail summary / worst years. Do not tune switch by regime.

## Execution and risk gate
For fixed Titanium picks, trade only at next Open; cost 0.1% per actual bought/sold notional, including true initial trade and terminal liquidation, self-financing valuation/rebalance; compare a tradable matched exposure SPY and category-momentum picks with **identical execution engine**. Report CAGR, monthly sampled MaxDD, turnover and trading fees, and warn not canonical full Hybrid24.
- **Independently audit the risk/governor source code** `period_path`: it detects a first day LOW crossing a 5.5% stop and then assigns a constant `1-0.055-0.001` payoff; quantify selected ETF stop-touch frequency, days where first stop-day OPEN was already worse than threshold (gap risk), and hypothetical stop shortfall if execution only at OPEN for these gaps. These are a stress diagnostic, **not a faithful tick-level stop simulation**; high/low daily bars do not give intraday execution order.
- No claim that the simulated stop or positions are executable until real point-in-time bars/quotes, intraday fill/slippage and handling of gaps are verified.

## Statistical discipline and decision
- Main unit = 113 calendar holding months, not ETF×month rows. Repeat vintages NOT independent markets.
- Report 3-month moving-block bootstrap CI on *monthly additive arithmetic attribution* within-category and category allocation, with fixed seed and 10,000 draws; exploratory descriptive CI, not corrected for hundreds of prior experiments.
- Give year-conditional, period split 2017-2021 / 2022-2026 and year-by-year; attributions can be driven by large shocks.
- **No full Hybrid24 claim without reproducing the actual Hybrid24 execution chain** on the same frozen panels; this experiment is source-of-edge gate B at the Titanium level, and engine issue gate A if relevant. Compare with previously recorded full-strategy metrics but don't use as a fabricated causal contribution.
- Decision is evidence based: if no repeatable within-category selection advantage or a material engine issue appears, STOP ML changes. If a positive within-category differential occurs, still require factor/beta/risk adjustment and truly independent future window.
