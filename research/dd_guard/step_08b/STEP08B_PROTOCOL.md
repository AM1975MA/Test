# STEP08B — persistent diversifying sleeve before stress

Date: 2026-08-31

## Objective
Test whether a small persistent diversifying sleeve can materially reduce the drawdowns of frozen FUSION1 by changing portfolio geometry *before* stress is detected, instead of reallocating only inside rare FUSION1 windows.

## Scientific seal
- Exact Treatment Value HGB 500-basket path and frozen FUSION1 overlay are unchanged.
- Development performance only: 2021-01-01 through 2022-12-31.
- Raw defensive and systemic inputs are truncated at 2022-12-31 before feature construction.
- 2023+ is not read for performance and may be opened only after a preregistered qualifying policy is frozen.
- Return at date t uses defensive/systemic information available through t-1.
- Transaction cost: 5 bp per one-way portfolio turnover, including risky, defensive and cash legs.

## Defensive assets
Primary fixed diversifying trio: `BIL`, `IEF`, `GLD`.
The purpose is structural diversification rather than a searched defensive universe.

A previously frozen STEP08A causal trend sleeve is also tested as a sensitivity: one 63-session momentum winner from liquidity, duration and real/inflation groups, with nonpositive duration/real momentum falling back to the liquidity winner.

## Frozen eligible variants
All variants retain the exact FUSION1 risk/cash mechanics inside the remaining core sleeve.

### P1 — PERSIST_BIL10
10% BIL at all times; 90% allocated to FUSION1.
Sanity control for persistent cash-like ballast.

### P2 — PERSIST_TRIO10
10% fixed equal-weight BIL/IEF/GLD at all times; 90% FUSION1.

### P3 — PERSIST_TRIAD_TREND10
10% causal STEP08A triad-trend diversifier at all times; 90% FUSION1.

### P4 — PERSIST_TRIO10_SYS20
10% fixed equal BIL/IEF/GLD normally; 20% when the frozen six-series `systemic_rankmean_6` observed at t-1 is >= 0.75. The remaining 90%/80% is FUSION1. Threshold and weights are fixed ex ante and not searched.

## Static frontier diagnostic — not promotion eligible
For the fixed equal BIL/IEF/GLD trio only, replay persistent weights `{0%,5%,10%,15%,20%,25%,30%}`. This is an economic ceiling/frontier diagnostic. No point may be promoted or used to retune P1-P4 after development.

## Quality-jump gate
An eligible variant may authorize one-shot holdout only if all are true versus frozen FUSION1 on 2021-2022:
1. mean MaxDD improvement >= +0.50 pp;
2. p10 MaxDD improvement >= +0.50 pp;
3. CAGR delta >= -0.50 pp;
4. annual mean-MaxDD delta is nonnegative in both 2021 and 2022;
5. worst-decile mean MaxDD delta is nonnegative.

A research-Pareto label requires CAGR, mean MaxDD and p10 all improve, with no annual mean-DD sign reversal. It does not authorize tuning.

## Stop rule
If no eligible variant qualifies, do not tune persistent weights, systemic threshold, trio constituents, momentum lookback, or trend sleeve groups. Use the static frontier to decide whether persistent defensive diversification has enough economic ceiling. If the frontier cannot reach the quality gate, close the persistent defensive-sleeve lane and move only to fundamentally different core portfolio construction/risk budgeting.
