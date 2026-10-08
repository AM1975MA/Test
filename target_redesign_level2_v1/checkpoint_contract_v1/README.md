# Checkpoint Contract V1 — ETF Trader research-only

8 October 2026. This is **isolated source code**, NOT connected to the full ETF Trader V2 execution/training pipeline. It changes no production decisions, risk parameters, ETF selections, or trained models. All tests are synthetic. No Original149 backtest or previous experiment was repeated.

## Deliverables

- `checkpoint.py`: creates a new immutable versioned archive directory containing an original `.ubj` model, exact byte copies of supplied sources and a SHA256 manifest. `verify_checkpoint` validates all saved bytes; optional `expected_sources` and `expected_metadata` reject silent stale-cache reuse after inputs/params change.
- `test_checkpoint.py`: eight unit tests created before implementation, including stale data, corrupted model/manifest, parameter drift, unsafe paths and refuse overwrite.
- `xgb_refresh_probe.py`, `test_xgb_compat.py`: synthetic XGBoost 3.1.3 verification of `rank:pairwise`, unchanged split topology on leaf refresh, UBJ round-trip and compatibility with `DMatrix`; this is NOT a signal-quality result.

## What was discovered

1. Existing source-only `_xgb_worker.py` saves prediction `.npy` and does not call `save_model`. `models.py` accepts an annual predictions cache if its audit file merely exists, without a source/data hash comparison in that cache-hit branch. This is an engineering risk, NOT proof of corruption in previous backtests.
2. A caller-produced XGBoost `.ubj` file can be preserved and reloaded without changing predictions. Additional training state (seeds, version, feature order, original data, eligible training rows and maturity) needs separate immutable evidence; `.ubj` itself is not a complete experimental contract.
3. `process_type=update, updater=refresh, refresh_leaf=1` on the canonical-style `QuantileDMatrix` fails in XGBoost 3.1.3 with `Not implemented for QuantileDMatrix`. Rebuilding the *refresh input only* as a normal `DMatrix` succeeds for synthetic grouped `rank:pairwise` data: 12/12 trees retain identical split topology, 87 leaf values differ, model reload prediction delta=0, update prediction delta~0.5498. This probe does not demonstrate safe economic behavior for 360-tree canonical annual ranking.

## Correct limits

- Freezing existing model/data gives snapshot-level reproducibility; it does **not** establish robust fresh training, restore the 43.145952% historical Golden CAGR for another vintage or guarantee future alpha.
- The contract does not cryptographically authenticate the author of a checkpoint, protect against an attacker able to change the manifest and its checksum, enforce a disk quota, or provide a cross-process distributed lock. Those belong to production integration.
- `training_exit_before_cutoff` is a required caller attestation. Production integration MUST verify each data row has a mature exit date before cutoff; the flag itself does not prove that condition.
- For production, freeze all 3 Compact21 models per horizon/year, full MA3 ExtraTrees/XGB models, PCA/KMeans state and training bytes; adapt caching only after the complete state fingerprint and all model-loading parity checks are independently verified.
- Data providers may legitimately correct errors and corporate-action factors. Preserve each as-of snapshot with a provenance ID rather than pretending corrected and previous adjusted bars are identical.

## Commands

```bash
python -m unittest discover -s . -p 'test_*.py' -v
python xgb_refresh_probe.py
```

## Gate to actual V2 implementation

Do not merge into the source-only worker until (1) the exact immutable training-source bytes, label matrix and year/seed group index are hashed, (2) the `save_model` / `load_model` prediction identity is proven for all three seeds and both horizons, (3) the existing source-only cache hit path validates source identity and rejects changed training inputs, (4) the full unchanged V2 preserves prior accounting, then (5) **a separate** prospectively preregistered leaf-refresh intervention is considered. No parameter sweep on Original149.
