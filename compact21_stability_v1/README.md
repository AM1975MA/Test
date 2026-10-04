# COMPACT21_STABILITY_V1

Research branch `research/compact21-stability-v1` in `AM1975MA/Test`.
The exact hypotheses, inputs, variants and advancement rules are fixed in
[PREREGISTRATION.md](PREREGISTRATION.md). See [AUDIT.md](AUDIT.md) for evidence,
known boundaries and independent review.

GitHub Actions workflow `COMPACT21_STABILITY_V1` runs seven variants on all
2017-2026 annual folds, three frozen Yahoo snapshots, and all snapshot pairs.
It persists `results/BENCHMARK.json`, then performs raw-only full replays for
BASE, Q4, Q4_LEGACY and every eligible challenger; the complete economic and
decision assessment is persisted to `results/FULL_REPLAY.json`.

The baseline/control producer uses single-thread execution throughout to
exclude ExtraTrees scheduling nondeterminism. Feature/target settings, XGBoost
hyperparameters, seeds, blending, allocation, risk and execution are frozen.
Historical Q4 results remain diagnostic references, not the new gate baseline.

## Local validation
From repository root with pinned numerical dependencies:

```bash
export PYTHONPATH="$PWD/vendor/etf_trader_v2/src:$PWD"
python -m unittest discover -s compact21_stability_v1/tests -v
python -m unittest discover -s tests -p test_quantization.py -v
python compact21_stability_v1/source_gate.py
```

`source_gate.py` permits only the historical final-newline normalization on
two canonical files for source hash parity. No semantic canonical edits.

## Reproduce diagnostic benchmark
Download the three artifacts from run37150436612 into `_ti/r1`, `_ti/r2`,
`_ti/r3`, then:

```bash
python compact21_stability_v1/run_benchmark.py --variant SCALE_ECON1BP \
  --r1 _ti/r1 --r2 _ti/r2 --r3 _ti/r3 --out _benchmark/SCALE_ECON1BP.json
```

## Reproduce full raw replay
Download raw snapshots from run37121749852; use a fresh output directory:

```bash
python compact21_stability_v1/run_full_pipeline.py \
  --raw _raw/_repeat1 --variant SCALE_ECON1BP --out _full \
  --compare-script holdout70/v2_canonical_same_source_compare.py
```

Only run challengers eligible under the frozen benchmark gate when reproducing
the staged experiment. Scores/features/models from historical artifacts are
never full-replay inputs. Negative feedback remains unchanged. Three repeated
snapshots on the burned Original149 universe cannot justify production adoption.
