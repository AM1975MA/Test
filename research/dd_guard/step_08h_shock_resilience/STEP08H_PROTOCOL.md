# STEP08H — Live Shock Resilience Rotation

Date: 2026-08-31

## Scientific question
Can the large basket-local protective-rotation oracle ceiling be made more learnable by first restricting destinations to ETFs that are already resisting the *current* shock, then using the frozen STEP08F event-time Titanium score only inside that resilient set?

## Frozen inherited mechanics
- Development only: 2021-01-01 through 2022-12-31.
- 2023+ remains sealed unless the development gate passes.
- Danger trigger: frozen STEP07A/STEP08C q95 schedule.
- Candidate universe: the basket's original 24 ETFs, excluding the current leader and satellite.
- Current holdings/origin reference: latest strictly-prior STATE_PANEL leader/satellite and frozen `legacy_w1`; origin daily return is `legacy_w1*leader + (1-legacy_w1)*satellite`.
- Action window, transaction costs and FUSION1 continuation are unchanged from STEP08C/E/F.
- Destination alpha score: frozen STEP08F event-time distilled Titanium HGB producer and already-generated `EVENT_TIT_R` scores. No re-fit or model change is allowed in STEP08H.
- V2 concentration semantics: 100% top-1 if filtered-set top1-minus-top2 EVENT_TIT_R >= 0.12, otherwise 75/25 top1/top2.
- BIL is the fallback outside option.

## Causal shock-resilience state
All resilience inputs use closes available no later than the decision-date close. For every candidate j and the current origin portfolio i:
- `rel_ret1`, `rel_ret3`, `rel_ret5`, `rel_ret10`: candidate cumulative return minus origin cumulative return over 1/3/5/10 sessions.
- `dd_gap21`: candidate current 21-session drawdown minus origin current 21-session drawdown; higher means the candidate has preserved capital better.
- `downside_gap21`: mean(candidate daily return - origin daily return) on origin-negative sessions in the trailing 21 sessions. At least 3 negative origin sessions are required; otherwise this component is missing.

At each basket/date, each available metric is converted to a cross-sectional percentile rank across the basket alternatives. `resilience_score` is the equal-weight mean of those percentile ranks; no fitted coefficient is used.

## Hard resilience eligibility
A candidate is `shock_resilient` only if at least 2 of these 3 causal conditions are true:
1. `rel_ret5 > 0`;
2. `dd_gap21 > 0`;
3. `downside_gap21 > 0`.

Among eligible candidates, retain at most the top 5 by `resilience_score`. This top-5 size is frozen ex ante to represent the proposed 3–5 destination set and is not tuned.

## H0 — filtered oracle ceiling (diagnostic only)
For each frozen event, evaluate ex post over the already-frozen action window:
- exact FUSION1 continuation (STAY),
- every candidate surviving the causal shock-resilience filter,
- BIL.

Utility is unchanged from STEP08C/E: terminal return + 0.5 * local minimum drawdown, with the same replacement round-trip cost. Report both force-action and STAY-allowed oracles. H0 is never promotable.

## H1 — deployable policy
1. Build the causal resilient top-5 set.
2. If it is empty: 100% BIL.
3. Otherwise rank only that set by frozen STEP08F `EVENT_TIT_R`.
4. If filtered top-1 EVENT_TIT_R is not strictly greater than BIL EVENT_TIT_R: 100% BIL.
5. Otherwise apply the unchanged V2 0.12 / 75-25 concentration rule inside the filtered set.
6. Hold only for the frozen action window, then return to exact FUSION1 continuation.

## Development gate
H1 may open a one-shot 2023+ holdout only if all are true versus FUSION1 over 2021–2022:
- delta CAGR >= -0.50 pp;
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta mean MaxDD >= 0 separately in 2021 and 2022.

No resilience horizon, top-K, hard condition, score weight, trigger, action window, cost, or V2 margin may be changed after observing development results.
