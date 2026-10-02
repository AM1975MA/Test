# Evidence V3

## Status

**OPEN — Dev72 is now burned development data after the preregistered baseline-transfer test. One deterministic decision-layer hypothesis is being preregistered; no model tuning is allowed.**

## Why V3 exists

Evidence V1 and V2 established that the frozen LTR architecture can retrieve plausible candidates but that repeated attempts to improve the extreme Top1 choice on Original149 did not survive preregistered gates. Original149 is closed/burned development data and Holdout70 is burned diagnostic data. EU120/EU110 was subsequently used in P45 transfer/retrain work and is therefore not treated as a clean new development universe.

Evidence V3 therefore started from a new development universe before any V3 performance result was observed.

## Phase A — Dev72 freeze — PASS

Dev72 was defined by `evidence_v3/protocols/DEV72_FREEZE_PREREG.md` and produced only by `evidence_v3/src/freeze_dev72.py`.

Freeze run: `37073560840`.

Frozen dataset commit: `f6a30ab` (`Freeze Evidence V3 Dev72 universe`).

Artifact:
- id `11255428127`;
- SHA256 `4581530cb8092379468a1c63c80fcbe053b348f500162aba38474ad04a13c7c7`.

Frozen identities:
- manifest SHA256 `2856f629c06a5e66d6229756cdc721858b30c0e35b8ed78cc90a45872fe63b3c`;
- universe SHA256 `412e577eab42cf9978fe57d6e42c62f9959aa0e46667ee5070aa3a788b9b5778`;
- candidate-spec SHA256 `5ca1e5fda66b05862c25e52769428f2cb13a39e7f44a979b7134e8b8af45e690`;
- coverage SHA256 `6d6ffdaa54c4aa6f291a95c8ecc9731ef1fbc7633f278b9880cb9e008172ae20`.

Properties:
- exactly 72 ETFs, 12 per six macro categories;
- requested data start 2004-01-01, frozen end 2026-07-31;
- at least 252 valid observations before 2017-01-31 for every selected ETF;
- zero intersection with the 328-name union of Original149, Holdout70 and the tested EU110 exclusion reference;
- selection used only identity/category/data availability/coverage/OHLC quality;
- `performance_used_for_selection = false`;
- no performance test was executed in the freeze workflow.

## Phase B — exact frozen LTR transfer — FAIL ON ECONOMICS

Protocol: `evidence_v3/protocols/LTR_BASELINE_TRANSFER_DEV72_PREREG.md`.

Valid run: `37074030427`.

Result commit: `36a5962` (`Record Evidence V3 LTR baseline transfer Dev72`).

Artifact:
- id `11255267634`;
- SHA256 `5ba62d677a0547578df89a50e8e1c72c6820c395175da7e0950b22a34478dcad`.

The exact Evidence V1 LTR architecture was retrained causally on Dev72 with unchanged `FEATURES_42`, target, hyperparameters, annual expanding schedule and 63-day maturity gate. No network, Original149, Holdout70 or EU110/EU120 data were used during the model test.

Evaluation: 114 monthly signal dates, 2017-01-31 through 2026-06-30, exactly 72 eligible candidates each month.

### Retrieval

| Metric | Observed | Random expectation | Enrichment |
|---|---:|---:|---:|
| Top1 winner | 8 | 1.58 | 5.05x |
| Top5 winner | 33 | 7.92 | 4.17x |
| Top10 winner | 60 | 15.83 | 3.79x |

Additional diagnostics:
- winner rank median `10`;
- winner rank normalized mean `0.171`;
- mean IC21 `-0.0184`.

Thus the retrieval phenomenon transfers very strongly in a broad-recall sense.

### Economics

| Portfolio proxy | CAGR |
|---|---:|
| LTR Top1 | **-7.57%** |
| LTR Top5 equal-weight | **+3.42%** |
| Dev72 universe equal-weight | **+8.52%** |

Primary gate:
- Top5 enrichment >=2x: PASS;
- Top10 enrichment >=1.5x: PASS;
- Top1 CAGR > Universe-EW: FAIL;
- Top5-EW CAGR > Universe-EW: FAIL.

**Binding verdict: DEVELOPMENT_TRANSFER_FAIL.**

The key scientific result is not that LTR fails to find the future extreme: it finds it far above chance. The failure is that global score ordering/concentration does not convert that broad retrieval into economic value. Therefore no LTR target, hyperparameter, feature-set or K tuning is allowed on Dev72.

## V3.1 — next and only current hypothesis

Before any further run, V3 will preregister one deterministic decision layer with **no model refit**:

`category-balanced LTR6 = equal weight of the highest frozen OOS LTR-score ETF in each of the six frozen Dev72 macro categories`.

Rationale is structural rather than performance-selected: Dev72 was frozen at exactly 12 ETFs per each of six categories. Category balancing removes cross-category score calibration/concentration as a source of portfolio dominance while retaining the already-produced causal OOS LTR rankings within each category.

No category may be omitted, overweighted or selected according to realized performance. No K sweep is involved: six positions arise mechanically from the six preregistered universe categories.

If V3.1 fails its preregistered economic gate, this deterministic use of the frozen LTR scores will be closed on Dev72; no nearby category weighting or number-of-category variation will be tested.

## Data status

- Original149: closed/burned development.
- Holdout70: burned diagnostic only.
- EU110/EU120: previously tested, not clean V3 data.
- Dev72: **now burned development** after Phase B.
- No Holdout-B has been opened.

## Repository rule

Every V3 test must commit source, preregistration, workflow, provenance and durable results. Scientific source/preregistration must be frozen before the corresponding run.