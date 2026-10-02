# Evidence V3

## Status

**DIAGNOSTIC PHASE — Dev72 is burned development data. Frozen LTR broad retrieval transferred strongly, but both global concentration and the preregistered category-balanced decision layer failed economic gates. No nearby allocation/model variants are permitted.**

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

Thus the broad retrieval phenomenon transfers strongly.

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

## V3.1 — category-balanced LTR6 — REJECT / LINEA CHIUSA

Protocol: `evidence_v3/protocols/CATEGORY_BALANCED_LTR6_PREREG.md`.

Exact architecture:
- no model refit;
- one highest frozen OOS LTR-score ETF from each of the six frozen Dev72 macro categories;
- exactly six positions, equal-weight 1/6;
- no category omission, score weighting, volatility weighting, cash or regime rule.

Valid run: `37074538540`.

Result commit: `56bbdd0` (`Record Evidence V3 category-balanced LTR6 result`).

Artifact:
- id `11256014074`;
- SHA256 `c5892b4a4bbee8d7407759803cdf4293167e5f6571339a44c058516111ca431a`.

Full 114-period result:

| Portfolio proxy | CAGR | Ann. vol | Sharpe rf0 | Max DD |
|---|---:|---:|---:|---:|
| Global LTR Top1 | -7.57% | 31.83% | -0.090 | -72.78% |
| Global LTR Top5-EW | 3.42% | 24.63% | 0.262 | -40.55% |
| Category-balanced LTR6 | **7.40%** | 18.03% | 0.487 | -25.49% |
| Dev72 Universe-EW | **8.52%** | 13.86% | 0.661 | -20.14% |

Category-balanced LTR6 materially repairs the catastrophic global concentration, but still trails Universe-EW by **1.12 percentage points CAGR** over the full period.

Subperiods:
- 2017-2022: LTR6 **4.91%** vs Universe-EW **8.02%** — FAIL;
- 2023-2026: LTR6 **11.81%** vs Universe-EW **9.39%** — PASS.

Primary gate required LTR6 to beat Universe-EW full-window and in both broad subperiods. Gate result:
- full-window: FAIL;
- 2017-2022: FAIL;
- 2023-2026: PASS.

**Binding verdict: DEVELOPMENT_REJECTED.**

The recent-period outperformance is diagnostic only and may not be converted into a regime rule. The category-balanced line is closed: no category weights, category omissions, Top2-per-category, alternate K, score weighting, volatility weighting or nearby allocation variants may be tested on Dev72.

## Current scientific diagnosis

Three facts now coexist on a genuinely disjoint universe:
1. LTR Top5/Top10 winner retrieval is far above chance;
2. global score concentration has very poor economic performance;
3. deterministic category diversification removes much of the damage but still does not beat passive Universe-EW robustly across time.

Before any new architecture is allowed, V3 may perform a **non-advancement diagnostic only** on the already frozen OOS predictions to determine whether high LTR scores preferentially identify positive winners, negative losers, or both return tails. This diagnostic may describe the failure mode but may not tune or select a trading rule on Dev72.

If that diagnostic motivates a materially new direction/sign architecture, that architecture must be preregistered and tested on a **new disjoint development universe**, not selected by further performance trials on Dev72.

## Data status

- Original149: closed/burned development.
- Holdout70: burned diagnostic only.
- EU110/EU120: previously tested, not clean V3 data.
- Dev72: closed/burned development for model/allocation selection; diagnostic use only.
- No Holdout-B has been opened.

## Repository rule

Every test and diagnostic must commit source/protocol, workflow, provenance and durable results. Scientific source/protocol must be frozen before the corresponding run.