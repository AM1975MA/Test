# Evidence V2 — Macro Context v1 credit-series availability fix

Status: **DATA-AVAILABILITY AMENDMENT BEFORE ANY MODEL TEST**

The preregistered FRED series `BAMLH0A0HYM2` cannot provide the required 2005-2026 history through FRED in 2026 because FRED now exposes only the most recent three years for this licensed ICE BofA series. The second freeze attempt failed the preregistered >=97% coverage gate with only ~11.6% coverage for the transformed credit feature. No model was fit and no performance metric was observed.

To preserve the preregistered economic role of the feature (US credit-spread stress) while restoring full historical coverage, `BAMLH0A0HYM2` is replaced once, before model execution, by FRED series `BAA10Y` (Moody's Seasoned Baa Corporate Bond Yield Relative to the 10-Year Treasury Constant Maturity), a daily credit-spread series with long historical coverage.

Consequent rename:
- `hy_oas_z252` -> `baa10y_z252`.

The transformation remains exactly a 252-business-day rolling z-score with minimum 126 observations. All other series, transformations, model settings, causal alignment, evaluation dates and decision gates remain unchanged.

This amendment is a source-availability correction, not a performance-driven feature substitution.