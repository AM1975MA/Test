# Titanium V2 official recovery — 2026-08-17

This directory preserves the recovered frozen Titanium V2 baseline and keeps the August live-retrained implementation explicitly separate.

## Status

- Historical selector parity: **56,500 / 56,500 official basket-date decisions (100%)** when the authentic `TIT_R` panel is used.
- Frozen Titanium V2 `BALANCED`: 12% top-1/top-2 margin threshold, 75/25 fallback, governor `RC0.25_RW0.25_RE0.25_CD3_S1`, D+1 execution.
- Official mean CAGR across 500 baskets: **21.6541%**.
- The August live-retrained producer is **not** score- or selection-identical to the frozen baseline.
- `live_parity_fixed/` is the corrected historical/live-as-of producer: it reuses the official baskets and authenticated `TIT_R`, passes 56,500/56,500 selection decisions and reproduces the official V2 scorecard at 1 July 2026.

Read in this order:

1. `official/RECOVERY_REPORT.md`
2. `audit/LIVE_DISCREPANCY_AUDIT.md`
3. `audit/LIVE_DISCREPANCY_METRICS.json`
4. `ARTIFACTS.md`
5. `live_parity_fixed/README.md`
6. `retrain_only_official_baskets_20260818/RETRAIN_ONLY_RESULT.md`
7. `target_redesign_20260818/TARGET_REDESIGN_REPORT.md`

## Directory policy

- `official/` contains the recovered specification, replay code, official membership and text-form results.
- `live_reference/` preserves the August regenerated live source, manifests, signal and selected audit outputs as a separate reference implementation.
- `audit/` contains the direct frozen-vs-live comparison and a reproducible audit script.
- `live_parity_fixed/` contains the correction, gates and validated text outputs. Canonical binary inputs remain in the complete archive referenced by `ARTIFACTS.md`.
- `retrain_only_official_baskets_20260818/` contains the clean retraining-only experiment with official baskets fixed. It proves the fresh fit is deterministic but not equivalent to authenticated `TIT_R`.
- `target_redesign_20260818/` tests five Compact targets while holding the rest of Titanium fixed. `CONSENSUS_MULTI` is the leading challenger, but remains unpromoted pending perturbation tests.

Never overwrite the frozen baseline with output from `live_reference/`. A future live producer must either pass the parity gates or receive a new version name.
