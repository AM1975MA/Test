# STEP08E — basket-local Titanium protective rotation

Date: 2026-08-31

## Scientific question
STEP08D used the authentic TIT_R rank across the full 150-ETF universe and improved the aggregate 2021-2022 CAGR/MaxDD frontier, but failed temporal replication because 2021 was negative. It also applied the original Titanium V2 12% concentration rule outside its native 24-ETF basket domain.

STEP08E tests the same idea in the exact native domain: when the already-frozen STEP08C/STEP07A q95 risk trigger fires, choose the destination only from the basket's original 24 ETFs, with the currently held leader/satellite excluded. BIL is the safe outside option.

## Frozen inputs
- STEP08C q95 decision schedule and 10-session action windows are unchanged.
- Exact FUSION1 development path/replay is unchanged.
- Authentic historical `TIT_R` panel from `METEOR_TITANIUM_V2_RECOVERED_OFFICIAL_20260817.zip`.
- Frozen `SUPER_GOLD_BASKET_MEMBERSHIP.csv`: exactly 24 ETFs per each of 500 baskets.
- Frozen OHLCV close history from the 150-ETF package.
- Development only: 2021-01-01 through 2022-12-31. 2023+ remains sealed.

## C0 — basket-local oracle ceiling
For each frozen q95 decision, evaluate ex post over the already-frozen action window:
1. exact FUSION1 continuation (`STAY`),
2. every eligible ETF in that basket except the current leader/satellite,
3. BIL.

Utility is unchanged from STEP08C:
`U = terminal_return + 0.5 * local_min_drawdown`, including the same 10 bp round-trip replacement cost used in STEP08C.

C0 is diagnostic only. It may authorize C1 but can never be promoted.

## C1 — causal basket-local TIT_R policy
At decision date d:
1. use the most recent authentic TIT_R signal date <= d;
2. restrict candidates to the basket's frozen 24 ETFs;
3. exclude current leader and satellite;
4. rank remaining candidates by authentic TIT_R;
5. compare the basket top-1 TIT_R with BIL TIT_R on the same authentic score date:
   - if no basket candidate has TIT_R strictly greater than BIL, allocate 100% to BIL;
   - otherwise BIL is not used and the original V2 concentration rule is applied to basket top-1/top-2: 100% top-1 when `TIT_R(top1)-TIT_R(top2) >= 0.12`, otherwise 75%/25%.
6. hold the replacement only for the frozen STEP08C action window, then return to the exact FUSION1 path.

No threshold, horizon, cost, trigger, candidate universe, margin, or sizing may be tuned after seeing results.

## Development gate
C1 qualifies for a future one-shot 2023+ holdout only if all are true versus FUSION1 over 2021-2022:
- delta CAGR >= -0.50 pp;
- delta mean MaxDD >= +0.50 pp;
- delta p10 MaxDD >= +0.50 pp;
- delta worst-decile MaxDD >= 0;
- delta mean MaxDD >= 0 separately in 2021 and 2022.

If the gate fails, STEP08E is rejected before holdout and no post-hoc tuning is allowed.
