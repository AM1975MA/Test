# ETF Trader V2 — Causal downside volatility missingness audit

Date 2026-10-21. Source: frozen 149-ETF snapshot [Github Actions run 39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691), same raw artifact `12292840548` as the V2 127-leaf pruning experiments. No future labels used.

The source-only feature formula for `downvol{h}` uses log returns restricted to negative sessions:
`lr.where(lr<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*sqrt(252)`.

This is **not** the same missingness behavior as downside deviation computed from clipped returns. `downvol126` requires >= 63 declining sessions in 126 days, hence many observations have NaN even with fully valid price histories. XGBoost can use missingness as a split condition; changing the formula could alter regime information.

Among tickers with at least 252 consecutive price days, monthly observations averaged over year:

| Year | Downvol21 missing | Downvol63 missing | Downvol126 missing |
| --- | ---: | ---: | ---: |
| 2018 | 39.43% | 57.49% | 74.33% |
| 2020 | 51.23% | 71.98% | 86.97% |
| 2022 | 27.29% | 26.01% | 31.43% |
| 2025 | 50.84% | 69.69% | 78.91% |

A 2012–2025 monthly average across eligible ETFs and years yields approximately 47.3%, 62.9%, 73.4% missing for 21, 63, 126-day definitions respectively. More frequent negative-return days during 2022 reduce missingness. This is a **descriptive regime association**, not prospective evidence that a missing flag improves OOS ranking.

Decision: retain the frozen original formula for all feature-pruning comparisons. Treat `has_downvol`, `fraction_negative_days` and a regular downside-volatility feature calculated with `ret.clip(upper=0)` as **separate predeclared future candidate features**, evaluated incrementally with nested temporal training. Do not overwrite the current production feature semantics.

Code: [regeneration/v2_downvol_missingness_audit.py](https://github.com/AM1975MA/Test/blob/research-v2-feature-confirmation-20261021/regeneration/v2_downvol_missingness_audit.py).

## Regime-proxy correlation (descriptive, same-date)
Across 168 month-ends 2012–2025, the 149-ETF eligible-universe mean `downvol126` missing fraction correlates with SPY's trailing 126-day raw close return at **Pearson +0.673**, Spearman **+0.634**. Correlation with the same-date mean fraction of negative daily ETF returns in the 126-day window is **Pearson -0.959**, as expected from the feature's hard threshold. No look-ahead is needed for these explanatory measures, but these relationships are contemporaneous and do **not** establish future-return predictability. They support separating trend-regime/frequency information from downside deviation in a later controlled experiment.
