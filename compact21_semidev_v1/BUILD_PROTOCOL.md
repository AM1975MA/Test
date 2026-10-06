# BASE_SEMIDEV portable construction and execution contract

The scientific gates are registered separately in PREREGISTRATION.md. This
build protocol changes no recipe, threshold, seed or target. Only nine
Compact21 downvol21/63/126 raw/pct/dev columns change to the second-moment
downside deviation: sqrt(mean(min(log_return,0)^2))*sqrt252 with rolling
finite-coverage min_periods=max(10,h//2). No epsilon or synthetic noise rule.
NaN and either infinity remain missing BEFORE clipping and never count as a
zero finite observation. Frozen raw inputs have no infinite prices/returns.

The original raw loader/calendar and full149-member universe.csv population
are used. Additional infrastructure CSVs outside universe.csv are excluded.
Require TI/raw population equality; do not intersect or invent memberships.
Normalize monthly matrices with canonical cs_pct/cs_robust_dev before aligning
TI keys. Preserve all116 other features and metadata/labels exactly.
Training and inference receive the identical new semantics. No canonical
source, Compact63/Tail, feedback or strategy output changes.

Select mature native training and native/common inference from ORIGINAL TI,
then transfer only the nine registered columns. Never recalculate cohorts from
the new view. Require exact original coverage and label/key fingerprints.
Training signal/exit are strictly before Jan1; inference ends2026-06-30 and
quality outcome maturity is2026-07-01. Common donor is the new Repeat2 view
on the original common inference keys; native donors are their own vintages.

Each cloud job executes ONE year2017..2026 and three vintages. BASE recipe is
unchanged: canonical XGB worker, params/seeds101/202/303,360rounds,threads1,
no model search or early stopping. Numerical gate is identical to V2.

Before ANY candidate fit, refit original BASE on all three ORIGINAL native
training sets and original common/native inference. Require byte-exact
predictions and exact metadata against retained COMPLETE BASE V2 parquets,
matching per-year matrix/label/group/prediction hashes and original coverage.
Any mismatch blocks the job before candidate fitting. Independently refit
the candidate in every year/vintage and require exact prediction bytes and
complete learned-audit equality. Retain both control and candidate vectors.

Frozen TI file identities are hardcoded and checked; all453 raw CSV hashes
must match original full-BASE contracts (151 per vintage). Source fingerprints
of used canonical BASE files must match retained V2. The runner records new
source, scientific/build protocol, reference and numeric identities before
fitting, and cannot overwrite a nonempty output directory.
The original nine downvol columns are rebuilt from canonical raw first:
missingness must match exactly, percentiles must be byte-exact, finite raw
downvol values must agree within absolute1e-12, and normalized `_dev` values
within absolute1e-10. There is no bit-parity claim for raw/dev reconstruction.
This tolerance never applies to the score/control
or unchanged-column comparisons, which remain bit-exact. Actual normalized
numeric-contract equality to BASE V2 is checked before any control fit.

Prefit integrity correction, 2026-10-05: the initially proposed common1e-12
reconstruction tolerance was unnecessarily strict for dimensionless `_dev`
reconstruction across Windows/Python3.12 and Linux/Python3.13. A complete
27-column source-only diagnostic, before any BASE_SEMIDEV fit, found masks
exact27/27, percentiles bit-exact9/9, max raw difference3.2287e-14 and max dev
difference2.5064e-12 on its bounded[-8,8] scale. Freeze raw1e-12/pct0/dev1e-10
as separate reconstruction bounds. No recipe, scientific gate, score/control
byte-parity requirement, numeric contract or unchanged-column requirement
is relaxed. Failed reconstructions still block candidate fitting.

Example:

    python compact21_semidev_v1/run.py --year 2017 --r1 _ti/r1 --r2 _ti/r2 --r3 _ti/r3 --raw-root _raw --contracts-root _contracts --reference _reference --out _semidev/2017

_contracts/rN/INPUT_CONTRACT.json are the retained original full-BASE contracts;
_reference contains the COMPLETE BASE V2 RESULT.json and native/common parquets.
The runner outputs annual RESULT.json, INPUT_CONTRACT.json, CONTROL_GATE.json,
NATIVE_PREDICTIONS.parquet, COMMON_PREDICTIONS.parquet and corresponding
CONTROL_* parquets. Summary must require all10 annual jobs and all3 vintages,
all pair cells, controls, refits and matching contracts. No failed/incomplete
job becomes a successful predictive result. No automatic adoption.
