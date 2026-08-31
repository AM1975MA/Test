# STEP08A — structural defensive restructuring during FUSION1 stress

Date: 2026-08-31

## Objective
Test whether the portfolio can materially reduce drawdown without the large CAGR sacrifice of cash de-risking by changing **what is held** during FUSION1 stress rather than attempting another crash-timing controller.

The exact Treatment Value HGB 500-basket path remains the risky sleeve. FUSION1 remains frozen and determines the maximum risky weight. The structural overlay invests the residual weight in causal defensive ETFs instead of cash. One fixed stronger restructuring variant additionally transfers 15 percentage points from the risky sleeve to the same defensive sleeve while FUSION1 is active.

## Frozen data and causality
- Exact 500-basket Treatment Value HGB daily equity paths from `TREATMENT_VALUE_SELECTED_PATHS.npz`, `candidate` array.
- Exact frozen FUSION1 alerts and execution engine from STEP06J.
- Frozen 150-ETF OHLCV payload. Only observations through 2022-12-31 may enter development features or performance. 2023+ performance is not read or evaluated before a qualifying freeze.
- Defensive allocation applied to close-to-close return at date t is computed using information available through t-1.
- Outer overlay turnover cost: 5 bp per one-way turnover, identical convention to FUSION1 outer overlay.
- No parameter search after seeing development results. All variants below are fixed before execution.

## Fixed defensive universe
`BIL, SHV, SHY, VGSH, IEF, IEI, VGIT, TLT, EDV, VGLT, TIP, SCHP, AGG, LQD, GLD, IAU, COMT, DBC`.

No HYG/JNK/equity-like risk assets are admitted to the defensive sleeve.

## Fixed variants
### S0 — FUSION1
Frozen benchmark. Risk weight `G_f`; residual is cash.

### S1 — BIL_FILL
Risk weight = frozen `G_f`. Residual `1-G_f` is invested in BIL.

### S2 — TRIAD_TREND
Risk weight = frozen `G_f`. The residual is split equally across three fixed sleeves, with one causal 63-session momentum winner per sleeve:
1. liquidity: `BIL, SHV, SHY, VGSH`;
2. duration: `IEF, IEI, VGIT, TLT, EDV, VGLT`;
3. real/inflation: `GLD, IAU, COMT, DBC, TIP, SCHP`.

The winner is determined from data through t-1. If the duration or real/inflation winner has non-positive 63-session return, that third falls back to the liquidity winner. No optimization of lookback or number of sleeves is permitted.

### S3 — LOWCORR_TOP3
Risk weight = frozen `G_f`. Residual is allocated to the top three members of the fixed defensive universe by a causal cross-sectional score computed at t-1:
- 50% rank of 63-session return / 63-session annualized volatility;
- 30% rank of negative 63-session correlation to the exact basket HGB daily return;
- 20% rank of negative 63-session volatility.

Candidates require non-negative 63-session return; if fewer than three qualify, remaining defensive weight goes to BIL. Selected assets are inverse-volatility weighted.

### S4 — LOWCORR_TOP3_SHIFT15
Same defensive sleeve as S3. During an active FUSION1 state, risky weight is `max(G_f - 0.15, 0)` and defensive weight is the remainder. Outside FUSION1 stress the exact HGB path remains untouched. The 15 pp transfer is fixed ex ante and is not a grid point selected from development.

## Development window
Exact replay: 2021-01-01 through 2022-12-31. Historical lookbacks may use earlier frozen observations. 2023+ remains sealed.

## Quality-jump gate
A variant qualifies for a future one-shot holdout only if all are true versus frozen FUSION1 on 2021–2022:
1. mean MaxDD improvement >= +0.50 pp;
2. p10 MaxDD improvement >= +0.50 pp;
3. CAGR delta >= -0.50 pp;
4. annual mean-MaxDD delta is non-negative in both 2021 and 2022;
5. worst-decile mean MaxDD delta is non-negative.

A weaker research-Pareto label is allowed only if CAGR, mean MaxDD and p10 all improve (>0) with no annual mean-DD sign reversal. It does not authorize promotion or parameter tuning.

## Stop rule
If no structural variant reaches the quality-jump gate, do not tune lookbacks, sleeve constituents, score coefficients, top-k, or SHIFT15. Diagnose the frontier and decide whether the next research lane requires a fundamentally different portfolio construction or new information.
