# Compact21 MAD-zero fallback diagnostic — 2026-10-11

GitHub Actions [38093523739](https://github.com/AM1975MA/Test/actions/runs/38093523739), successful, three Original149 independently cleaned-downvol vintages, all 33 robust deviation features; no training and no changes to canonical source or original input panels.

| Data-only result per vintage | Median+IQR/1.349 fallback | Median+population standard deviation fallback |
|---|---:|---:|
| Eligible _dev source-valid zero-MAD input cells | 1761 | 1761 |
| Fallback scale positive | **1761** | **1761** |
| Unresolved (neither candidate denominator positive) | 0 | 0 |
| Cases off the median | 732 | 732 |
| Worst cross-vintage absolute normalized-value difference across the original 3 pair comparisons | 0.004231893077522031 | **0.00022091198582696592** |
| Differences >0.1 between any acquisition pair | 0 | 0 |

The original 1029 tied-at-median and 732 nonmedian values per vintage are both correctly treated as available under either denominator, without fabricating prices or time series. Candidate values clipped to ±8 as current robust deviation definition. Using MAD normally and fallback standard deviation only at exact MAD=0 is an **explicit change to feature semantics**, not proof of improvement in predictive quality. A different fallback can introduce a discontinuity near MAD=0: **audit near-zero MAD and sign/near-tie perturbations before final acceptance**. For all 1761 observed zero-MAD cells standard deviation has much lower maximal between-snapshot variation than scaled IQR, but that is a *local comparison*, not overall-model stability evidence.

Residual input history NaNs (e.g. mom252, ma_gap200) remain legitimate cold-start exclusions; no blanket 125/125 gate or imputation. Follow-up: implement a pure, unit-tested function and apply to strictly frozen feature panels **without training**, compare standard-deviation fallback vs original cross-section semantics and prospective inference completeness; include original source exact mask/other-feature parity and preserve three-vintage independence. Only after a complete data quality gate should model replay resume.

No code changed in productive Etf_trader.
