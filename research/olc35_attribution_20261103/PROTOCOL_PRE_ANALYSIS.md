# OLC35 — Opportunity/selection/execution attribution, preserving the USA reference

**Study design saved 2026-11-03, before running OLC35 attribution calculations.** Historic 2019–2026 data have already been repeatedly inspected; this is **descriptive diagnostic, not a new confirmatory hypothesis, and NOT a deployable strategy**.

## User hard constraint and references

Preserve both historically distinguished U.S. references rather than conflating them:

* OLC17 `TOP2_CONTEXT_REVALUE / ALL_PREOPEN_V6`, legacy fee=0.001, ACTIVE2021_2024 (2021-01-04 to 2024-12-31): USA **52.3006% CAGR**, MaxDD **-19.7902%**. This is a sensitivity of execution; not guaranteed achievable.
* OLC19 `TOP2_CONTEXT_REVALUE / FAST_LOCK3`, legacy fee=0.001, stop_friction=0.001, stress=False, ACTIVE2021_2024: USA **50.7722% CAGR**, MaxDD **-20.2260%**.
* Compare matched European versions of EACH reference, not a cherry-picked EU/USA execution mix. Never claim that the 52.30 and 50.77 represent identical execution.
* No modification of USA engine, allocation, models, weights, data or strategies; no write to main and no order. All actual and proposed USA decisions are kept **bit-for-bit unchanged**. Any future candidate requiring USA deterioration must show separately adjudicated, material, forward-validated EU improvement; OLC35 does not authorize an exception.

## Inputs and provenance

1. OLC32 corrected source `OLC32_RESULTS.zip` SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`, inside `results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz` SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16` (27,191 ETF-month rows with original AUTH FUSION ranks, corrected EU quote labels).
2. OLC17 `OLC17_Validazione_Risultati_20261102.zip` SHA256 `b780ef1e43c756c5649898ca37170ac66391730a13f8649403a1b68426f5c04f` (actual preopen-V6 proposals, scorecards).
3. OLC19 `OLC19_Rischio_Rientro_Risultati_20261102.zip` SHA256 `f574339c8c7ab25e159e83d8fb55fc4be2dc44bdc0ed06a9fbf96e6b24f4a021` (actual FAST_LOCK3 scorecards, orders, stops, fee/exposure summaries).

Data window **48 monthly signal dates per EU/USA during 2021–2024**. Use only rows with `eligible_label==True`, and report invalid coverage without replacing by 0. EU label source=observed and June 2020 fixed; USA prepared but lacks original quote certification. Last 2026 terminal label excluded. The 2021–2024 Top2 from OLC32 MUST match OLC17 actual `TOP2_CONTEXT_REVALUE` proposals **96/96** or stop.

## Predetermined attribution, calculation and interpretation

Calculate for every market-month, using OLC32 `r_o2o_bp` (10,000 log(Open_next/Open_entry)):

* `market_best`: maximum over all eligible ETF labels in that market-month.
* `top5_best`: max among `auth_rank<=5` eligible; `top2_best`: max ranks 1,2; `top2_proxy`: **simple mean of the two individual log returns** — this is NOT actual equal-weight portfolio return, it is a log-score proxy.
* `D_universe = market_best - top5_best`, `D_top5 = top5_best-top2_best`, `D_two_slot = top2_best-top2_proxy`. All are nonnegative, and `D_total = D_universe+D_top5+D_two_slot=market_best-top2_proxy` **exactly per market-month**. This is an **ex post oracle ceiling decomposition**, not achievable alpha or a causal model attribution.
* Per-month percentage of times best market ETF in AUTH Top5 and Top2; median and quantiles of gaps, annual breakdown, concentration (top 5 months accounting for all excess), which ETF creates largest gap; Top5 coverage by year. Marginal *best* is selected with hindsight and is affected by ETF universe choice.
* Optional ceiling: `top5_best - top2_proxy` as potential within-Top5 and `market_best-top5_best` outside signal window, both **hypothetical**. No strategy or retraining on outcome.
* Portfolio scorecards **separate**: OLC17 and OLC19 pairs on same period and matching fee: CAGR, MaxDD, turnover, exposure, stop count, rebalances, `fee_drag_sum`. Do not directly subtract portfolio NAV from oracle labels as a causal contribution. No material attribution of stops to returns without true counterfactual replay holding weights and constraints fixed.
* Control: compare only fixed 2021–2024; no temporal filtering on future label for *prediction*, because no new prediction is made.

## Deliverables and success criteria

Full 96-row month-by-market decomposition; 2-market annual table; CSV of parent scorecards; reconciliation of actual proposals; zero-count missing-quote audit; two matched EU/USA figures of three decomposed headroom contributions, with years/median so outliers are clear; report Italian, code and checksum manifest. Stop and annotate if any source mismatch or near-zero coverage.

No recommendation to change the U.S. baseline or optimize a new regime on the same data. **Next-stage decision rule:** prioritise a *separate EU-only change* if enough opportunity lies in an identifiable bottleneck. Require an independent future holdout and costs/risk comparison before claiming gain; do not present an oracle ceiling as a forecast. Any alternative that sacrifices U.S. CAGR needs separately documented, quantitatively large, out-of-sample EU benefit and explicit approval; it is NOT part of OLC35.
