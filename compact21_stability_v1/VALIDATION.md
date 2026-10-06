# Prelaunch validation

2026-10-04 before any real-data COMPACT21_STABILITY_V1 outcome.
Local interpreter Python3.12, NumPy2.3.5, pandas2.2.3, sklearn1.8.0,
XGBoost3.1.3; CI uses Python3.13 (same prior research environment).

- 13 target unit tests PASS: within-date labels, economic ties, fixed grids,
  artificial percentile bin removal, row order, mismatch/invalid rejection,
  strict maturity and known bin-boundary sensitivity.
- 9 quantizer unit tests PASS: all125 canonical features, training-only scale,
  kernel-defined domains, missingness, idempotence, ordering, serialization,
  invalid input and boundary caveats.
- 4 actual-worker integration tests PASS: canonical BASE prediction bytes,
  unchanged Compact63 for Q4/SCALE_ECON1BP, future-row feature/outcome mutation
  leaves eligible training and prior predictions identical, immature reject.
  Only these synthetic tests explicitly override model rounds to2.
- End-to-end benchmark runner smoke for all7 variants on synthetic2017 data
  PASS, including train/test masks, target APIs, isolated3seed fits,
  pairwise-label diagnostics, quality metrics, exact repeated predictions and
  JSON serialization. These smoke cells used2rounds and are not evidence of
  financial robustness. Production benchmark always uses canonical360rounds.
- Canonical productive source hash gate PASS; comparator blob identity PASS.
- Workflow YAML parses; seven benchmark variants, fixed advancement and full
  raw replays wired. GitHub execution and real-data outcomes are tracked by CI.

Independent audit and full-summary tests are recorded in AUDIT.md.
