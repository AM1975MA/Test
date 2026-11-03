# OLC36 — EU-only persistent dominant-leader core, preregistered diagnostic

**Protocol publication:** 2026-11-03, *before* running or looking at OLC36 candidate returns or decision outcomes. Parent diagnostic OLC35 commit `833d2a7e0df72c44cdbc08c1f52e7c0a2e971556`. Branch: `research/olc36-eu-dominance-core-20261103`. All historical observations have already been explored repeatedly in OLC01–35; this remains **retrospective exploratory**, never an independent holdout.

## User goal and nonnegotiable guardrail

**Goal:** catch a European ETF entering a *persistent dominant state* earlier and continue holding it while the dominance signal survives, instead of continuously chasing the coming month's single best ETF. **USA149 is strictly frozen and never recomputed or changed**. USA OLC17 `TOP2_CONTEXT_REVALUE / ALL_PREOPEN_V6` 2021–24 fee 0.001 CAGR 52.3006%, MaxDD -19.7902%; OLC19 `TOP2_CONTEXT_REVALUE / FAST_LOCK3` fee 0.001 CAGR 50.7722%, MaxDD -20.2260%. These are two different historical execution contracts, not interchangeable; neither is a guaranteed live performance.

Historical comparisons are not a license to sacrifice the U.S. engine. Nothing is merged to `main`, deployed or used to trade.

## Fixed source and population

- OLC32 EU165 corrected dataset `results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz`, SHA256 `83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16` in `OLC32_RESULTS.zip` SHA256 `aef33c5c1aac60a944f7cf767b7ee637eb4ca254710b431c95b5f13a67fd6b8d`.
- EU signal dates monthly from 2019-01-31 to 2026-06-30. Primary 48 signals 2021-01-01–2024-12-31; secondary 2025–2026 available only as diagnostics, never choose thresholds from those results. Frozen baseline is AUTH FUSION `auth_rank` 1 and 2 as authenticated in OLC35 48/48 EU 2021–24; no model fitting.
- Input features allowed: `ret_21`, `ret_63`, `ret_126`, `ret_252`, `auth_rank`, `ticker`, `feature_available_asof`, `source_date`, `signal_date`. No ticker-specific exclusions or weight tuning, no future label in the decision. Rank denominators use **all as-of feature-complete EU candidates**, not future available labels. Source-date must not exceed signal date.
- Outcome ONLY: EU observed positive next Open-to-Open corrected `r_o2o_bp` when `eligible_label=True`. Missing future observed quotes do not become 0, nor can they be consulted when deciding.

## Exact new rule: *DOM_CORE* (no ML, no blended score)

All percentile ranks are cross-sectional (best return rank=1, tie ticker ascending), at each as-of signal.

**New core qualification** at date t requires simultaneously:
1. ETF feature-valid at t and 63-day, 126-day and 252-day past returns finite and as-of.
2. `rank_126 <= ceil(0.10*n_t)` AND `rank_252 <= ceil(0.10*n_t)`.
3. `rank_63 <= ceil(0.25*n_t)` AND `ret_21 > -0.05`.
4. In the current and two PREVIOUS monthly EU signals, `rank_126 <= ceil(0.10*n_s)` in at least 2 of 3 (missing history = nonqualifying, not zero price).
5. If multiple eligible candidates, choose the one minimizing `rank_126/n_t + rank_252/n_t`, ties: greatest `ret_252`, then alphabetic ticker.

**Core persistence / hysteresis:** if a core was held in the previous month, retain the same ETF while `rank_126 <= ceil(.20*n_t)`, `rank_252 <= ceil(.20*n_t)`, `ret_63 > 0`, `ret_21 > -.05`, and data valid as-of; otherwise release and re-evaluate the stricter new-core qualification above. No ticker identity in the logic; no lookahead; no discretionary extension/early exit.

**Two selection slots:** the first slot is ALWAYS the exact frozen AUTH Top1 on the same signal. The second is the current qualified core **unless it equals Top1**; in that case use frozen AUTH Top2. If no current qualified core, use frozen AUTH Top2. Never duplicate the same ETF. USA untouched. No modification to AUTH ranks, OLC19 V6, stops or costs and no claim to have reimplemented those mechanics in this limited diagnostic.

This **one-slot stateful rule** differs from prior experiments OLC25's continuous 20/40% momentum score blending, OLC26/27's small Ridge/logistic score adjustments and OLC29/30's KAMA re-rankers. If it fails, do not try nearby thresholds, extra lookbacks or new choices.

## Outcome definitions and strict gates

1. Count all changed EU monthly Top2 pairs, early entry and number of subsequent retained months of each chosen core. Evaluable 2021–2024 monthly signals only when both baseline and candidate ETF labels are observed and valid, with the missing label rate separately disclosed; never condition the strategy on future label eligibility.
2. Primary economic diagnostic: an **equal-weight 50/50 monthly Open-to-Open proxy** for each two-ETF pair, calculated as `r_simple(t) = .5*(exp(r1_bp/10000)-1)+.5*(exp(r2_bp/10000)-1)`. Subtract a hypothetical fixed `20 bp * half_turnover` per market/month with half_turnover `0.5*sum_i |target_weight_i(t)-target_weight_i(t-1)|` over the union of tickers; at first month use 100% cash. Compounding the monthly net simple returns gives a monthly NAV **proxy**, NOT an OLC19 strategy NAV or a certified fill (no stops/V6/intraday).
3. A distinct EU *future-dominant proxy* for **evaluation only**: each ticker's sum of its next 6 consecutive eligible monthly corrected Open-to-Open log returns, including the month of signal. For each EU signal with sufficient full 6-month labels, future dominant=top decile of those future sums among eligible ETF paths. Report per-slot Top2 coverage and core retention (prospective prediction never sees this label); future horizon overlaps, so observations are NOT independent.
4. Primary gate on **2021–24 only**: (a) >=12 altered EU monthly selections with complete ex-post label coverage >=95%; (b) average paired monthly net proxy log-return difference DOM_CORE−AUTH >0 bp AND a 6-consecutive-month paired moving-block bootstrap 95% lower confidence bound >0 bp (2000 draws; seed 36001); (c) future six-month top-decile hit rate of BOTH selected ETF slots improves by >=5 percentage points from baseline on matched eligible months; (d) monthly close-to-close proxy max drawdown does not worsen by more than 3 percentage points; (e) all audits pass. **Any failed gate = STOP**. Even all passing = exploratory and requires full unchanged OLC19 risk/V6 replay and a new genuinely prospective sample before promotion.
5. Report 2019–2020 and 2025–2026 separately, using the exact unchanged rule. No tuning and no retrospective ticker-name rules after examining the outcomes.

## Audit and deliverables

- Source SHA256; uniqueness (market,signal_date,ticker); feature `source_date<=signal_date`; full classification before consulting future labels. EU 2020-06-02 correction unchanged, LEEU missing observed remains missing, terminal 2026-06 zero-label forbidden; 48 EU 2021–24 signals and exactly matched baseline ranking.
- Counterfactual label perturbation after any decision cannot modify past rankings/core selection. Deterministic rerun; independently check selection and 50/50 math; future six-month target must use only matured, consecutive eligible months, and must NEVER enter rank or selection.
- Full monthly decision/retention traces, monthly economic proxy performance, future-dominant diagnostics, yearly metrics, bootstrap draws, risk statistics, source and output manifest and a candid Italian report. Keep all prior experiments/USA references untouched.
