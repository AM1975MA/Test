# STEP07D — deterministic normalized-depth protection floor

Date: 2026-08-31

## Purpose
Final admissible controller test after STEP07A–07C. This is not another predictive model. FUSION1 remains the exact frozen protection floor; STEP07D may only reduce gross exposure further. It can never make FUSION1 less defensive.

## Holdout discipline
- Development replay only: 2021-01-01 through 2022-12-31.
- No model fitting and no feature selection.
- 2023+ remains sealed unless the single frozen rule passes the quality-jump gate below.
- No threshold, ladder or recovery parameter may be changed after seeing development results.

## Causal normalized stress state
Use the exact frozen Treatment Value HGB basket path used by the DD-guard research.
For each basket and session calculate trailing 63-session daily return volatility and `s21 = vol63 * sqrt(21)`.

An episode starts when the current path drawdown first crosses below `-1.0 * s21`. At episode start freeze `s0 = s21` so rising realized volatility during a selloff cannot mechanically dilute the measured stress. The episode persists until either:
- path drawdown recovers above `-0.5 * s0`, or
- 126 sessions have elapsed.

Within an active episode define `depth_s0 = drawdown / s0`.

This is basket/path-specific normalization. The monthly frozen leader state is retained only as a diagnostic and is not allowed to tune or veto the policy.

## Single frozen cap ladder
The normalized-depth cap is:
- `depth_s0 > -1.0`: 100% gross;
- `-1.5 < depth_s0 <= -1.0`: 85%;
- `-2.0 < depth_s0 <= -1.5`: 65%;
- `-3.0 < depth_s0 <= -2.0`: 40%;
- `depth_s0 <= -3.0`: 0%.

Signal is observed at close `t`. To avoid look-ahead, the cap first applies to return session `t+1`, matching the causal timing convention of the frozen FUSION1 overlay.

## Composition with FUSION1
Let `G_FUSION1(t)` be exact frozen FUSION1 gross exposure and `C_norm(t)` the normalized-depth cap.

`G_STEP07D(t) = min(G_FUSION1(t), C_norm(t))`.

Therefore STEP07D can only add protection; it can never undo an existing FUSION1 reduction.

Transaction cost is the same frozen 5 bp one-way cost charged on absolute exposure changes.

## Quality-jump gate vs FUSION1, 2021–2022
All conditions must pass:
1. mean MaxDD improvement >= +0.50 pp;
2. p10 MaxDD improvement >= +0.50 pp;
3. CAGR delta >= -0.50 pp;
4. mean MaxDD delta >= 0 separately in 2021 and 2022;
5. worst-decile MaxDD delta >= +0.25 pp;
6. protection is not concentrated in one decision date: leave-one-episode-start-date-out worst mean-MaxDD delta >= 0.

If the rule fails, 2023+ remains sealed and the current DD-controller research lane is closed. No nearby ladder or threshold search is permitted.
