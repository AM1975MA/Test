# Meteor Titanium V2 + Opportunity V3 — regeneration checkpoint

Checkpoint date: 2026-08-11

Repository: `AM1975MA/Test`
Branch: `titanium-live-package-regeneration-20260804`
PR: #6 (draft, temporary; do not merge into main)
Latest sensitivity run inspected: `30892989208`
Latest job: `91939207212`

## Verified source hashes
- `titanium_retrained_current_data_audit.py`: `76b5da95c865a069d967189d61b1c8df3338eacc5a0e8941e8ee7025c42caf60`
- `titanium_reconstruction_v5.py` before runtime numba-cache patch: `ba99f9ce08d96e6b56567d44bf18b5caa7a76ccf13a7d44546e6d1416d79d65a`

## Input OHLCV
Artifact id: `8839840705`.
Contains `OPEN.parquet`, `HIGH.parquet`, `LOW.parquet`, `CLOSE.parquet`, `VOLUME.parquet`.
Current reconstruction scores 148 tickers over 113 OOS months.

## Current parity gates
Passing: all Compact features present, all Tail features present, all 54 macro aggregates present, all Opportunity features present, S3B sizes balanced, no impossible daily jumps, OOS starts at first entry.
Median S3B ARI: `0.7187250026499582`.
Unresolved: `macro_gate_non_degenerate=false`, `known_signal_matches_frozen=false`. Macro bonus occurs in 3 months in the fast runs.

## Downvol sensitivity — fast 20-basket results
All four variants completed successfully. Run 30892989208 failed only in the `Summarize` step because `Path.glob('SENS_*')` also matched `SENS_*.zip`.

### original
Basket mean CAGR: Base 18.9402%, Direct 19.1833%, Router 19.0255%. Router median 20.1200%; P05/P95 6.7343%/29.2406%; median MaxDD -35.8639%. Global CAGR: Base 16.2772%, Direct 17.5758%, Router 16.8021%.

### zero_std
Basket mean CAGR: Base 20.7404%, Direct 20.7469%, Router 20.8687%. Router median 17.3372%; P05/P95 11.0749%/36.7049%; median MaxDD -37.8239%. Global CAGR: Base 15.7104%, Direct 16.2518%, Router 16.2224%.

### downside_rms
Basket mean CAGR: Base 19.9032%, Direct 20.0840%, Router 20.0322%. Router median 18.0718%; P05/P95 7.3123%/40.1495%; median MaxDD -34.6625%. Global CAGR: Base 15.8876%, Direct 16.5386%, Router 16.5636%.

### negative_std_full
Basket mean CAGR: Base 20.6818%, Direct 20.7858%, Router 20.8521%. Router median 20.6748%; P05/P95 8.8072%/34.1163%; median MaxDD -34.5633%. Global CAGR: Base 17.0998%, Direct 20.3882%, Router 19.7976%.

## Resume point
1. Fix summary glob to directories only.
2. Re-run sensitivity and archive all four outputs and missingness summary.
3. Select downvol definition by semantics, missingness and stability — not CAGR alone.
4. Run full 360-tree / 3-seed / 500-basket reconstruction.
5. Generate `METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE.zip` containing source, model/panel outputs, basket membership, clusters, governor state, 500-basket results, unrestricted-universe results, manifests and SHA256.
