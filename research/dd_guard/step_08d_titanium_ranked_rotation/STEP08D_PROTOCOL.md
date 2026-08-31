# STEP08D — Titanium-ranked protective rotation

Date: 2026-08-31

## Objective
Test whether the large STEP08C destination oracle ceiling can be monetized by reusing the already-authenticated causal Titanium V2 `TIT_R` ranking rather than training a new destination model.

## Scientific seal
- Development only: 2021-01-01 through 2022-12-31.
- 2023+ remains sealed and is not read for model selection or replay.
- Trigger schedule is frozen from STEP08C: first STEP07A high-risk state with `risk_pct > 0.95` per episode, then the same non-overlapping 10-session action windows.
- No trigger threshold, horizon, transaction cost, ranking field, score margin, or portfolio weights are optimized in STEP08D.
- Authentic source of truth: recovered historical `ORTHOGONAL_SCORE_PANEL.pkl`; only `signal_date`, `ticker`, and `TIT_R` are used. Forward-return columns are forbidden for policy construction.
- At decision close d, use the latest authentic score row with `signal_date <= d`; execution remains the already-frozen STEP08C `action_start` two sessions later.
- Exclude the current monthly leader and satellite used by the frozen HGB/FUSION1 state. No outcome-based candidate filter is permitted.
- An ETF must have a finite `TIT_R` and a valid price at the decision date. Future price availability is not an eligibility criterion.
- 10 bp one-way temporary-rotation cost is inherited from STEP08C: entry and exit on the full rotated sleeve.

## Frozen policies
### D1 — TIT_R_TOP1
Rotate 100% to the highest eligible authentic `TIT_R` ETF.

### D2 — TIT_R_V2_BALANCED (primary)
Sort eligible ETFs by authentic `TIT_R` descending.
- If `TIT_R(top1) - TIT_R(top2) >= 0.12`: 100% top1.
- Otherwise: 75% top1 + 25% top2.

The 0.12 margin and 75/25 concentration are inherited from the recovered official Titanium V2 definition; they are not selected in STEP08D.

BIL is treated as an ordinary scored destination. There is no special cash override or post-hoc health gate.

## Replay
Each selected destination replaces the exact FUSION1 path only over the frozen STEP08C 10-session action window. For D2 the initial 75/25 weights are buy-and-hold within the temporary window (no daily rebalancing). Entry and exit costs apply to the full temporary sleeve.

## Primary promotion gate
D2 must satisfy all of:
1. delta mean MaxDD vs FUSION1 >= +0.50 pp;
2. delta p10 MaxDD >= +0.50 pp;
3. delta worst-decile MaxDD >= 0;
4. delta CAGR >= -0.50 pp;
5. delta mean MaxDD >= 0 in both 2021 and 2022.

D1 is a structural diagnostic and does not replace D2 as the primary policy after seeing outcomes. If D2 fails, STEP08D is rejected before 2023+ holdout; no margin/horizon/top-k tuning is allowed inside STEP08D.
