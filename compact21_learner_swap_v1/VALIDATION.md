# Implementation validation before financial outcomes

The five implementation/review workstreams completed before the first run of
COMPACT21_LEARNER_SWAP_V1. Forty-five standard-library tests pass: nine learner
and benchmark tests, four actual-worker full-hook integration tests, twelve
semantic-integrity tests and twenty summary/evidence/gate tests.

- BASE predictions equal canonical XGB worker output byte for byte.
- Compact63 predictions remain exact for every learner replacement.
- Extreme appended future features/outcomes do not alter eligible past fitted
  state or predictions; strict exit maturity is tested.
- Ridge/LightGBM recipes and targets are frozen; imputation/scaling are fitted
  exclusively on training rows. Same-input fits are independently repeated.
- Schema, index/ordered keys, dtypes, missing masks and each finite float bit
  are tested. Different pickle block layouts can be semantically equal, while
  even a one-ULP value change fails. Signed zero remains distinct.
- Aggregators reject missing folds/pairs, forged means, nonfinite/duplicate
  JSON, altered coverage, inconsistent contracts, modified retained values,
  immature Tail labels and a failed benchmark concealed by good CAGR.
- The actual benchmark runner completed all three learners and ten annual
  folds on synthetic data, then passed the strict summary interface. Synthetic
  tests use two boosting rounds only; research runs retain 360 frozen rounds.
- The untouched canonical MA3 builder was independently run twice on local
  original149 raw as a construction smoke test: 31,375 rows by 242 columns,
  with exact semantic panel and membership equality. This is not a new frozen
  snapshot economic result and does not resolve missing prior MA3 panels.

Python syntax and workflow YAML parsing pass. Canonical productive sources
have no semantic edits. The source gate permits the previously documented
final-newline normalization for hash parity in two historical source files.

Local numerical checks use Python3.12; GitHub pins Python3.13 and re-runs the
complete validation before financial benchmarks or raw replays. A pre-existing
truncated local XGBoost binary was replaced atomically with the pinned 3.1.3
wheel before the passing checks; no model configuration was changed.

These checks validate implementation and causal boundaries. They do not
establish strategy quality, population robustness or investment performance.

Execution-profile amendment: all 46 tests pass locally under the uniform
AVX2/Haswell settings, including a new test that a blocking environment
comparison preserves actual/expected fields before raising. The canonical
MA3 double rebuild also passes exact panel and membership equality under
that profile. Its values differ from the automatic CPU profile in 43 columns
(maximum absolute difference 1.7339907287805545e-11); all experimental arms
are therefore regenerated, and initial-attempt results remain separate.
