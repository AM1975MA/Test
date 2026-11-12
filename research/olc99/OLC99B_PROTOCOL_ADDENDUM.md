# OLC99B — Global-universe economic training before Top10 application

**Follow-up protocol added after seeing OLC99A results, before executing OLC99B. Research only. Not an independent discovery holdout.**

OLC99A's economically oriented Top10-only Ridge worsened both markets. One specific explanation to test is training-set selection and sample scarcity: after just 24 mature months only about 240 individual training examples exist, many highly correlated.

- Train **one** additional economic Ridge per market at each signal on *all eligible tickers* in prior monthly universes, using same 12 ex-ante features, feature transforms, alpha=100, clipped log Open→Open returns relative to that month's eligible universe median, date grouping weights 1/N, and strict t-2 maturity. Require 24 mature groups. No ticker identity.
- Apply predictor **only to the ten ETF candidates selected by the original FUSION**, rank them by predicted economic excess and mix 80% native contextual Top10 rank and 20% learned economic rank. No feature selection, parameter search, gating, per-market tuning, or changes to Top2-context selection outside these ten candidates.
- Compare full-universe-trained variant B1 against OLC99A E1 and original E0 on the very same 2019–Jul2026 source, matched timing (IMMEDIATE and DELAY3), fee 0.001 and 0.003, FAST_LOCK3, Top2 50/50. Recompute period metrics from original daily OLC19 native engine; annual and uncertainty at six-month blocks.
- Only if independent and stable improvement on genuinely new data is later observed would B1 be eligible to replace the original selection. No new allocation optimization using OLC99B outcomes; the matched-state allocation is already fully tested in OLC99A.