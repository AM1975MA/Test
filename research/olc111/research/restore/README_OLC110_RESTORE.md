# OLC110 selective restore

Restored 39 original files (2,847,196 bytes) byte-for-byte under `/workspace/scratch/23237d81ce2c/olc110` from `AM1975MA/Test` commit `5752452e565037b790a4099c9d5f8de9d5788509`, path `research/olc110`.

## Verified identity and scope

The remote commit points to root tree `f23515d0468d1614935ac441da33bc82887b6faf`, whose `research` tree is `88a58c4b6126a6a08e8f035589bba99cbdb27052` and whose `olc110` subtree is `b0eb95446c629bcd46affd8d951817f81bff044b`. Every restored file matches both the Git blob SHA-1 and byte size in that subtree and has file mode 0444 locally. `OLC110_REMOTE_IDENTITY.json` records the selection; `OLC110_RESTORE_RECEIPT.json` records per-file SHA-1, SHA-256 and size checks.

The selection includes all seven `src/*.py` files, `source/src/core.py`, eight tests, the two historical engine references needed by tests, five protocol/documentation files, all five data metadata files, the top-level README/report/archive manifests and reproduction instructions, requirements, and all five aggregate results files. Financial path ledgers, bulk audit tables, figures and large input NPZ files were deliberately excluded from this restore task.

`OLC110_STATIC_RESTORE_QA.json` records successful parsing of 18 Python files, agreement with all seven frozen financial code SHA-256 hashes, agreement with the frozen protocol SHA-256, and exact installed dependency versions. No financial test or simulation was run during this restore.

## Imports

Add `/workspace/scratch/23237d81ce2c/olc110/src` to `sys.path` or `PYTHONPATH` when importing OLC110 modules: the selectors and policy module use bare sibling imports. `run_protection.load_inputs(root)` dynamically loads `root/source/src/core.py` and returns the panel dictionary, turnover array and core module. The runner has a guarded CLI entry point, but its original `run()` executes the frozen OLC110 78-path matrix and is not an OLC111 runner.

The preserved test collection includes imports between test modules. Use the test directory as the discovery start directory when the parent task chooses to run it. `test_guard_engine.py` uses `research/engine/olc108_engine_reference.py`; `test_account_policy_engine.py` uses `research/engine/olc109_engine_reference.py`.

## Binary data supplied separately by parent task

| Relative path | Bytes | SHA-256 |
| --- | ---: | --- |
| `source/data/XETRA_EUR_ETF.npz` | 28682014 | `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96` |
| `data/LIQUIDITY.npz` | 17319970 | `b95fa3d67837fa06c5705aa4aea09807d396464ab44ec1671031d797b57f4485` |
| `source/data/TR29.npz` (test fixture) | 412807 | `6ed7123bfd8122c5b2414f3f31138658a381b5f5b1171a89aac83135decb1346` |

The two full inputs are documented as byte-identical to those in the OLC109 archive. The liquidity NPZ must have `names` and `dates` arrays exactly equal to the panel, and must provide `turnover`. The fixture's Git blob SHA-1 is `2d050d60f4a27573c282717c3e26ebe347cc4a16`.

The original baseline comparator reads sibling `olc109/results_stage2/DEDUP_DUAL_TREND_OPP__{scenario}` for `DAILY.csv.gz`, `ORDERS.csv.gz` and `DECISIONS.npz` and asserts numeric differences below 1e-8. This restore intentionally leaves those OLC109 data/results to the parent task.

## Dependency versions checked

NumPy 2.3.5, pandas 2.2.3, SciPy 1.17.0, threadpoolctl 3.6.0 and matplotlib 3.10.8 exactly match the preserved `requirements.txt` in the current environment.

## Restore method

Only GitHub GET operations were used. Raw text URLs were used for small and medium text files; the 1.52 MB universe CSV was obtained through its Git blob URL after raw-file retrieval hit a size limitation. Text was transported through JSON and encoded as UTF-8 locally, then verified against the original Git blob SHA before writing. No source content was interpolated into shell commands. Intermediate payload files were removed after verification. The generic local writer is retained as `restore_verified_text.py`.
