# OLC111 runner and daily policy

The runner is implemented in [`src/run_olc111.py`](../../src/run_olc111.py), with synthetic integration tests in [`tests/test_run_olc111.py`](../../tests/test_run_olc111.py). It consumes the frozen design and the independently prepared native comparison bank. No research fit or full research path was executed while implementing this runner.

## Execution contract

```bash
python olc111/src/run_olc111.py --root olc111 --resume
```

The command requires `docs/EXPERIMENT_FREEZE.json`. It verifies `code_hashes`, `input_hashes`, `protocol_sha256`, the exact six arms, the exact three scenarios, and 18 planned paths. Hash paths resolve relative to the OLC111 root, so sibling frozen inputs such as `../olc110/source/src/core.py` resolve correctly. An unchanged freeze is required for resume. A prebuilt bank can be resumed before the first `RUN_MANIFEST.json` exists.

The matrix is `BASE`, `STATIC_75`, `MEAN`, `PRICE`, `VIX`, `TERM`, each under `NEXT_CLOSE`, `DOUBLE_COST`, and `NEXT_OPEN`. All model fits use the primary next-Close normal-cost bank. Stress scenarios reuse those same models and compute features from their own actual accounts. No execution- or cost-specific model refit is performed.

Monthly cutoffs are the first panel session of each calendar month, clipped to `begin-1`, independently of the first available bank row. The learner itself enforces strictly mature outcomes. Fitted artifacts are cached once per cutoff and head; complete transforms, coefficients, bootstrap coefficients, metadata, and per-arm hashes are saved. Their cache provenance includes the experiment-freeze hash.

Initial entry always uses the frozen baseline. Before all three CASH/FRESH/ENTRY heads are ready, the exact monthly baseline continues. After readiness, the account callback can hold at any Close, including month end. A busy account suppresses new discretionary instructions. Missing external data makes VIX/TERM use their matching PRICE models and records the fallback. Missing price/state support cannot authorize an action.

The callback applies the existing 3% fresh-target no-op filter and chooses only predictions whose mean and lower buffer are both positive. Labels are already net of costs; there is no additional predicted-cost hurdle. CASH targets zero weights; FRESH/ENTRY target the unchanged selector basket. Discretionary orders are forced after the no-op filter. HOLD returns `None` and preserves actual quantities.

## Timing and outputs

`FIT_READINESS.json` records each head's first ready decision date and the first date on which all heads are ready. If this occurs at Close `k`, the common post-warmup evaluation begins at session `k+1`, with each path's actual Close-`k` NAV as its denominator. Annual contributions likewise use the actual preceding account NAV.

The prequential forecast ledger and its diagnostics are written before the complete-account paths are interpreted. Each bank-row forecast records the historical fit cutoff, maximum training terminal index, label endpoint, readiness, and model hash. Primary forecast diagnostics use `ALL_HEADS_READY` support; `HEAD_READY` results are retained separately. Scores use equal date weighting and report MSE/bias differences against MEAN, PRICE, and VIX. Prediction bins and positive-buffer realized outcomes are descriptive. Overlapping advantages are not summed into returns. The output explicitly records that the study is exploratory and has no pristine holdout.

| Location under `results/` | Contents |
|---|---|
| `RUN_MANIFEST.json` | Frozen provenance, versions, fixed model options, path completion, exploratory status |
| `FITS/FIT_*.json.gz` | Complete monthly fits for all three heads and four learned arms |
| `FIT_READINESS.json` | Per-head readiness, common decision readiness, first executable post-warmup session |
| `PREQUENTIAL_FORECASTS.csv.gz` | Forecasts and matured realized outcomes by bank row and arm |
| `FORECAST_SCORES.csv`, `FORECAST_BINS.csv`, `FORECAST_GATES.json` | Date-weighted predictive diagnostics; no policy adaptation |
| `SCORES.csv`, `ANNUAL_RETURNS.csv`, `COMMON_POST_WARMUP.csv` | Full-path and common-period performance, actual preceding NAVs, fees, exposure, cash days |
| `DRAWDOWN_EPISODES.csv` | Sampled pre-fee/Close peak, trough, recovery, and ongoing drawdown episodes |
| `{ARM}__{SCENARIO}/DAILY.csv.gz`, `ORDERS.csv.gz`, `INSTRUCTIONS.csv.gz` | Complete native account and execution ledgers |
| `{ARM}__{SCENARIO}/DECISIONS.npz`, `DECISIONS_META.json.gz` | All pre-instruction quantity/weight arrays and decision metadata |
| `{ARM}__{SCENARIO}/POLICY_TRACE.csv.gz`, `METRICS.json` | Daily callback state/actions, models, feature extremity, holding age, and path metrics |

The trace distinguishes actual instruction intent (`CASH`, `FRESH`, `ENTRY`) from baseline `INITIAL`/`SCHEDULED` and `HOLD`. `status` distinguishes warmup, busy accounts, unsupported features, and a failed positive buffer. `fallback_price` and per-head `model_arm` identify option-data fallback. Per-head `max_abs_standardized_price`, actual `gross`, and known holding ages diagnose departures from training support; they do not introduce a new action cutoff. The age fields measure sessions since the latest BUY (`last_buy_idx`); a top-up resets that age. They are not continuous position-duration estimates.

Realized intervention counts require at least one actual order associated with the action's instruction. Twenty-one-session spacing is applied to unique signal dates for the diagnostic episode counts. The twelve-episode indicators and forecast gates are recorded without changing thresholds, features, model settings, or the 18-path matrix.

## Verification

The test file was written first and failed because the runner module was absent. The implementation then passed all 12 initial integration tests; a separate hand-calculated date-weighting/MSE test was added and passed. The complete current OLC111 suite subsequently passed **63 tests**.

The runner tests cover calendar-based fit cutoffs, real-model cache serialization, initial baseline behavior, all-three-head warmup, native positive buffers, pending-order suppression, PRICE fallback, fresh no-op handling, actual-unit scheduled HOLD through an opening gap using real toy fits, prequential exclusion of a row's own future label, preceding-NAV segment returns, frozen sibling-path resolution, and date-balanced TERM-versus-VIX MSE diagnostics. These are synthetic checks only; they do not supply research results.

An independent read-only review found no material defect in cutoff timing, matured fitting, model reuse, warmup, same-account action decisions, HOLD semantics, fallback, post-warmup accounting, or frozen path resolution. Its one reporting comment was the age definition clarified above. The reviewer made no edits and ran no research fits or financial paths.
