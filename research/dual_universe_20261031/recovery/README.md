# DUAL-01 recovery: completed paired experiment

Read `RESULTS_IT.md` and `results/STATUS.json` first. Results are historical and conditional on a 70-month common signal calendar; no production promotion. The current training/replay batch is complete. No local process is claimed to continue after this session.

## Evidence delivered in the conversation

| File | Bytes | SHA-256 |
|---|---:|---|
| DUAL01_Risultati_Verificati_20261031.zip | 45678527 | 9600a0f4efd4928dd3860c235096638a4d44b29443d54807ad1ef4148b68ffba |
| DUAL01_Checkpoint_Completo_20261031.zip | 344899033 | 34f6b34d3783875fa3964a80a38524eea8c4c35533c6e92a748813a5950403bf |

The smaller archive contains all result tables, all 3,360 NAV curves, router outputs, source code, checks and the detailed Italian report. It excludes full fitting inputs and most full execution ledgers. The complete archive contains the exact source input ZIPs, corrected kernel, prepared feature/market panels, all 112 annual prediction checkpoints with hashes, result tables, full NAV/ledger files and executable source. CRC checks passed for both archives; the smaller archive's 78 included manifest files were independently hash-verified. Do not confuse the full continuation archive with the earlier log-only status archive.

Binary datasets/checkpoints are delivered as conversation artifacts, not all uploaded to this Git branch. To retrieve them after a runtime reset, locate the exact named artifacts in the conversation/Library and materialize them; do not assume old container paths or training processes still exist. The large archive has all 112 prediction CSV checkpoints, not the binary fitted model objects. Hyperparameters, seeds, input/output/model hashes and source permit refitting.

## Restoration

Extract the complete ZIP under `/mnt/data/`. It restores `dual_market_research/recovery/`, `dual_market_research/code/`, `dual_market_research/inputs/`, `yfinance-repeatability-v1-raw.zip`, and `compact21-tail-factorial-full.zip`. Verify archive hashes first. Pickle files must only be loaded from trusted, hash-verified inputs.

From `/mnt/data/dual_market_research/recovery`:

```bash
PYTHONPATH=src python -m pytest -q
python src/modeling.py
python src/replay.py
python src/analysis.py
python src/router.py
python src/verify_outputs.py
python src/matched_target_diagnostic.py
```

`modeling.py` reuses a checkpoint only when its signature/output digest match. The prepared panels avoid needless feature recomputation. To rebuild from raw data, run `python src/prepare.py` first; changed data/code/environment may change pickle signatures and require a new experiment version rather than bypassing the integrity check.

For a repository checkout, the matching corrected kernel is already versioned at `etf-trader-v3 corrected/src/etf_trader_v3/source_only/kernel.py`. Copy it without alteration to `research/dual_universe_20261031/code/frozen_kernel.py` before preparation. Required SHA-256: `3e024b3cf169f19ed30747cb8c41d4078d8eee6107455c860668d4bd7180a65a`. The source archives/prepared/checkpoint folders must also be restored from the full delivery; a source checkout alone does not include those binaries.

## Environment actually used

Python3.13.5; numpy2.3.5; pandas2.2.3; scipy1.17.0; scikit-learn1.8.0; xgboost3.1.3; numba0.65.1; pytest9.0.2; matplotlib3.10.8. Exact pip requirements and environment text are in the archives.

The router was changed to decompress NAV arrays once rather than thousands of times. Election logic was unchanged; the 29-test suite was rerun and the full router completed after this performance-only adjustment.

## Interpretation

The new common BASE is not the old Stage19. The common-market features and causal simulation contract differ. Missing European score support leaves 18 months without a new scheduled rebalance in both markets, while holdings/risk rules continue. This coverage limitation must be addressed and retested symmetrically before any general monthly-strategy promotion.

A target improvement is measured against the exact same mature-label training sample before comparing the integrated strategy. Conditional posterior probabilities are not future win probabilities or a correction for all historical selection. The entire repository's 293 prior branch tips were not fully retrained by this campaign. Main and operational trading remain unchanged.
