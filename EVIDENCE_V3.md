# Evidence V3 — CLOSED

## Purpose

Evidence V3 started from a new development universe after Evidence V1/V2 exhausted Original149. The goal was to determine whether the frozen LTR retrieval phenomenon transferred to genuinely disjoint data and, if so, why its broad winner recall did not translate into portfolio economics.

## Phase A — Dev72 freeze — PASS

Dev72 was frozen before any V3 performance result using only identity/category/data availability/coverage/OHLC quality.

Freeze run: `37073560840`.

Frozen dataset commit: `f6a30ab`.

Artifact:
- id `11255428127`;
- SHA256 `4581530cb8092379468a1c63c80fcbe053b348f500162aba38474ad04a13c7c7`.

Frozen identities:
- manifest SHA256 `2856f629c06a5e66d6229756cdc721858b30c0e35b8ed78cc90a45872fe63b3c`;
- universe SHA256 `412e577eab42cf9978fe57d6e42c62f9959aa0e46667ee5070aa3a788b9b5778`;
- candidate-spec SHA256 `5ca1e5fda66b05862c25e52769428f2cb13a39e7f44a979b7134e8b8af45e690`.

Dev72 contains exactly 72 ETFs, 12 per six macro categories, with zero intersection with the 328-name burned/tested union of Original149, Holdout70 and EU110. Selection used no performance statistic.

## Phase B — exact frozen LTR transfer — BROAD RETRIEVAL PASS / ECONOMIC FAIL

Protocol: `evidence_v3/protocols/LTR_BASELINE_TRANSFER_DEV72_PREREG.md`.

Valid run: `37074030427`.

Result commit: `36a5962`.

Artifact:
- id `11255267634`;
- SHA256 `5ba62d677a0547578df89a50e8e1c72c6820c395175da7e0950b22a34478dcad`.

Evaluation: 114 monthly signal dates, 2017-01-31 through 2026-06-30, 72 candidates each month.

| Metric | Observed | Random expectation | Enrichment |
|---|---:|---:|---:|
| Top1 winner | 8 | 1.58 | 5.05x |
| Top5 winner | 33 | 7.92 | 4.17x |
| Top10 winner | 60 | 15.83 | 3.79x |

Economics:

| Portfolio | CAGR proxy |
|---|---:|
| LTR Top1 | -7.57% |
| LTR Top5-EW | +3.42% |
| Dev72 Universe-EW | +8.52% |

Thus the frozen LTR architecture transfers strongly as a **broad retriever**, but global score concentration fails economically.

## V3.1 — category-balanced LTR6 — REJECT / LINE CLOSED

Protocol: `evidence_v3/protocols/CATEGORY_BALANCED_LTR6_PREREG.md`.

Valid run: `37074538540`.

Result commit: `56bbdd0`.

Artifact:
- id `11256014074`;
- SHA256 `c5892b4a4bbee8d7407759803cdf4293167e5f6571339a44c058516111ca431a`.

Exact rule: one highest frozen OOS LTR-score ETF per each of the six frozen categories, equal weight 1/6, no model refit.

| Portfolio | CAGR | Ann. vol | Sharpe rf0 | Max DD |
|---|---:|---:|---:|---:|
| Global LTR Top1 | -7.57% | 31.83% | -0.090 | -72.78% |
| Global LTR Top5-EW | 3.42% | 24.63% | 0.262 | -40.55% |
| Category-balanced LTR6 | 7.40% | 18.03% | 0.487 | -25.49% |
| Dev72 Universe-EW | 8.52% | 13.86% | 0.661 | -20.14% |

Subperiods:
- 2017-2022: LTR6 4.91% vs Universe-EW 8.02% — FAIL;
- 2023-2026: LTR6 11.81% vs Universe-EW 9.39% — PASS.

Binding verdict: **REJECT**. The recent subperiod advantage cannot be converted into an ex-post regime rule. No category-weight/count, TopN-per-category, score-weight, volatility-weight or nearby allocation variant is permitted on Dev72.

## Tail-symmetry diagnostic — KEY RESULT

Protocol: `evidence_v3/protocols/LTR_TAIL_SYMMETRY_DIAGNOSTIC_PREREG.md`.

Diagnostic-only run: `37074805101`.

Result commit: `6a7474b`.

Artifact:
- id `11256224273`;
- SHA256 `5717ed351a7c377009ed5192ef0f265a45cd1924c1a5b3f54694506fcd2a5779`.

No model refit and no trading rule was tested.

### Extreme capture is nearly symmetric

| Tail event | Top1 hits | Top5 hits | Top10 hits |
|---|---:|---:|---:|
| Global 21d winner | 8 | 33 | 60 |
| Global 21d loser | 8 | 30 | 53 |

Random expectations are 1.58 / 7.92 / 15.83 respectively. Therefore LTR enriches both positive and negative extremes by roughly 3–5x.

In 20/114 months the score Top10 contains **both** the global winner and global loser.

### Score predicts magnitude, not sign

- mean monthly Spearman `LTR_SCORE` vs `fwd_ret_21`: **-0.0184**;
- positive sign-correlation months: **42.1%**;
- mean monthly Spearman `LTR_SCORE` vs `abs(fwd_ret_21)`: **+0.3328**;
- positive magnitude-correlation months: **94.7%**.

Absolute-return concentration:
- universe mean `|r21|`: **4.15%**;
- score Top1: **7.22%** = 1.74x universe;
- score Top5: **7.03%** = 1.69x;
- score Top10: **7.05%** = 1.70x.

Within score Top10, the mean overlap is 2.64 names with the realized positive Top10 and 2.90 names with the realized negative Bottom10. Months with more negative-tail than positive-tail names: 57; more positive-tail: 49; equal: 8.

### Rank-bucket shape

Fixed six-name score buckets confirm that magnitude is concentrated at the top:
- ranks 1–6 mean `|r21|` **7.13%**;
- ranks 7–12 **6.77%**;
- ranks 13–18 **5.76%**;
- ranks 19–24 **4.53%**;
- lower half stabilizes around ~3%.

The highest-score bucket simultaneously has elevated extreme gains (>=+10% in 14.62% of names) and extreme losses (<=-10% in 10.53% of names).

## Scientific conclusion

The contradiction observed across V1–V3 is resolved:

**the LTR score is behaving primarily as a forward-return-magnitude / tail-opportunity detector, not as a reliable directional return ranker.**

This explains why:
- Top5/Top10 winner recall is far above random;
- the same score also captures losers far above random;
- global Top1 concentration can have poor or negative CAGR;
- diversification repairs risk but cannot manufacture direction information.

No further model, threshold, K, bucket or allocation test is permitted on Dev72. Dev72 is permanently burned for architecture selection.

## Next scientific line

A materially new hypothesis is now justified but must be tested on **new disjoint development data**:

`Stage 1: frozen LTR-style magnitude/tail retrieval -> Stage 2: separately trained causal 21-day direction/sign head`.

The direction head must predict sign rather than best-in-shortlist identity. Its architecture, target, maturity rule, shortlist K and decision rule must be frozen before performance is observed on the new universe.

This is not allowed to be back-tested for selection on Dev72 because the hypothesis was derived from the V3 diagnostic.

## Data status

- Original149: closed/burned development.
- Holdout70: burned diagnostic only.
- EU110/EU120: previously tested.
- Dev72: closed/burned development; no further model/allocation selection.
- No Holdout-B opened.
- Evidence V3: **CLOSED**.