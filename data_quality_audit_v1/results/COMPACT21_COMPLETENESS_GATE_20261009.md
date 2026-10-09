# Original149 Compact21 completeness gate — confirmed 2026-10-09

Scope: all **125 canonical** Compact21 numeric feature columns, **40230 ticker×signal-date rows per acquisition**, all three independently frozen Yahoo sources; no ML retraining and no strategy economics. CI run [37953044061](https://github.com/AM1975MA/Test/actions/runs/37953044061) has original and previously independently cleaned experimental downvol (9 features) jobs both SUCCESS.

| Eligibility rule | Original Repeat1/2/3 (same count each) | Experimental cleaned-downvol Repeat1/2/3 | Source |
|---|---:|---:|---|
| >=30 /125 features valid | 34876 | 34876 | canonical existing inference cohort |
| all 125 features finite | **5465** | **31827** | controlled complete-case gate |
| all 116 non-downvol features finite | 31827 | 31827 | independent source-vs-semidev comparison |
| all-125 excluded within >=30 cohort | 29411 | 3049 | subtraction |
| all-125 retained among >=30 cohort | **15.67%** | **91.26%** | computed ratios, not a backtest |
| all-125 retained out of all stored rows | **13.58%** | **79.11%** | snapshot warmup and history included |

The three acquisitions have **identical eligibility sets for each rule**, including all 125 cleaned feature values and the original 125. Pairwise eligibility flips **zero**. This does NOT establish that their *values* or model decisions are equal, and does not generalize to Tail or MA3.

**Important**: the 5465 original complete rows / 31827 after downvol repair are ALL available 2004–2026 in source panel, not just 2017–2026 live backtest rows. The frozen 30/125 inference availability contract is unchanged. The experimental clean-downvol construction still was NOT accepted as a production fix due to failed cross-download model stability/economic criteria.

Remaining feature missingness is nontrivial even after downvol work. The worst surviving feature families include `mom252`, `mom252_ex21` and derived pct/dev; `breakout_pos252`; `ma_gap200`; and cross-sectional `_dev` features such as `drawdown21_dev`, for which some missingness may come from zero-MAD or structural cross-sectional dispersion. **Do not assume all residual NA derives from short history.** Audit each formula, raw lookback and ticker/date first.

Decision: a strict 125/125 complete-case **can technically be enforced** but loses 3049 otherwise eligible rows per acquisition even after the experimental downvol fix (8.74% of 34876) and should not yet be deployed. First classify feature-wise remaining NaNs, calendar coverage and the bias toward older instruments. Do not fill with zeros. The next stage should enforce deterministic data contracts, explicit source-availability/warm-up and an eventual as-of feature gate for each submodel after finance-valid definitions are certified. No learning, model retuning or CAGR performed by this study.

Data-only scripts: data_quality_audit_v1/completeness_gate.py; stored per-year cohort coverage, per-feature NA counts, pairwise cohort changes and per-row valid feature counts in successful CI artifacts.
