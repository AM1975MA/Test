# Original149 point-in-time ETF warmup audit 2017–2026 (2026-10-11)

Prior work checked: PR #19 basket membership, PR #52/#64–#67 historical feature nulls and PR #68/#69 full temporal retention contract. The missing step was a 2017–2026 per-ticker, per-signal-date raw warmup vs actual eligibility census. No models fitted, no datasets modified, and no production edits.

Completed [GitHub Actions run 38173382353](https://github.com/AM1975MA/Test/actions/runs/38173382353) **SUCCESS**. Three immutable Yahoo Original149 acquisitions from 37121749852 and three α=1.0 Compact21 panels from 38094232042. 114 monthly operative signal dates, 149 ETF symbols, 16,986 ETF/signal pairs **per vintage**.

**Per each of three vintages**:
- Missing 253 consecutive finite positive recorded daily Close observations at operative signal: **0**.
- Failed existing Compact21 >=30/125 finite input eligibility: **0**.
- Failed combined raw 253-bar plus Compact21 current eligibility: **0**.
- Missing at least one input of stricter all-125/125 Compact21 gate: **2** ETF/date pairs; 16,984 strict complete cases.
- On all 114 signal dates, **all 149** ETF candidates satisfy 253 recorded valid close observations and the original 30-feature eligibility requirement; minimum and median daily eligible universe = **149**.

**Implication:** No substitution/deletion of Original149 instruments based solely on insufficient historical Close warmup for operative monthly signals. Most earlier 1,665 incomplete eligible rows were historically before 2017. Adding the 253-valid-bar check to 2017–2026 frozen monthly Original149 has **zero universe effect**, though it is not yet wired into production strategy or shown by a full strategy prediction-parity replay.

**Limitations:** 253 positive Close rows and >=30 Compact21 features do not certify complete MA3/Tail/Macro/Opportunity feature availability, same-session Volume, corporate-action history, point-in-time listing membership/universe survivorship, or arbitrary daily as opposed to monthly signal calendars. Historical Yahoo 149 ETF membership is retrospective and these are preselected survivors. Source calendar recorded rows need not all be independently exchange-verified trading sessions; observed zero-volume events are not price-quality certified. The stricter 125-feature gate changes two observations and must not be silently adopted in lieu of the original validated model contract.

**Decision:** Do not replace ETF tickers or delete older raw history. Preserve baseline; if adopting explicit eligibility, lock exact source-specific checks and validate full end-to-end V2 equivalence before promotion. Data-quality and predictive stability gaps remain distinct.
