# OLC65 — Protocollo congelato prima dell'analisi degli errori

**Data 2026-11-07. RESEARCH ONLY.** Scopo: diagnosticare errori upstream di individuazione, ordinamento e tenuta dei leader nella FUSION originale. Nessuna modifica a OLC19, nessun train, nessun nuovo layer/gate, nessuna ottimizzazione su CAGR. L'intero 2019–2026 è stato già esplorato in numerosi test: NON è OOS indipendente.

## Input frozen
- OLC14 Fitting Results: SHA256 4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1.
- OLC16 Input/Code: SHA256 ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7.
- OLC19 engine: SHA256 3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540.
- OLC61 predictions panel: SHA256 a3cf0d3d6755cefaa1962c0dd96d8ad2bd6b92e973ec9d852d536f78fa171659.
- OLC63 reconstruction code: SHA256 df0a6569e937d9389a03e60e70e8c29725f0f88d509fce24312d9034e7a82bd2.

Same original eligible ticker sets, original score, tie treatment, monthly dates, and future fwd_ret_21/fwd_ret_42; no exclusion on the future label for construction of the real Top10/Top2. For evaluation, retain only market-months with complete finite 21/42 forward labels on all original eligible names. MAIN = 2021–2024 (48 monthly signals × EU/USA expected); LATE = 2025 diagnostic only (possibly fewer EU months). For means preserve raw forward arithmetic returns, no synthetic CAGR.

## Predetermined taxonomy
On each monthly market cross-section, original FUSION rank Top10 (include all tied at 10th) and Top2 fractional-tie weights from exact original score; evaluation *oracle* is the two best ETFs in **realized** 21d future Open→Open return (hindsight only, never selection). All outcome labels use rank/return at future horizons solely for evaluation.

1. **DISCOVERY**: an oracle Top2 ETF lies *outside* the original Top10. **ORDERING**: oracle Top2 lies within Top10 but outside Top2; **ALREADY_SELECTED** otherwise. Report event counts and proportions, also by year/market.
2. **Economic opportunity ceiling**, per month: realized equal-weight average return of actual Top2, best possible 2 inside original Top10, best possible 2 in entire eligible universe. Disjoint nonnegative loss components = (Top10 oracle − selected), **ordering gap**; (full oracle − Top10 oracle), **discovery gap**. Report mean 21/42d, annual slices, concentration in worst 3 months, not tradeable returns.
3. **Persistence phenotype** of actual Top2: future 21d leader if top 20% cross-section; durable if also top20% at 42d; **short-lived** if top20% at21d but not42d; **miss** if not top20 at21d. Also calculate if second disjoint 21→42 interval is below same-month peer median, to avoid misinterpreting cumulative 42d as persistence of continuing gains.
4. **Expert visibility**: for missed oracle Top2 outside FUSION Top10, check Top10 membership in original RETURN, ET percentile, XGB percentile, CURRENT and SMOOTH (ranked *at signal time*); any individual component visible means 'fusion suppression', none means 'not flagged by experts'. Also compare rank distributions and pre-signal gaps, never use ex-post oracle to select a trading rule.
5. **Controlled ablations**: original formula with one of Return / ET / XGB / memory neutralized at 0.5, all other original weights fixed; count whether a previously missed future leader enters Top10; diagnose *sensitivity*, not causal responsibility. No tuning/no parameter selection.
6. **Pre-signal diagnostic**: median and quantiles of original score margin between ranks2–3, Top10 cutoff and model disagreement for months with higher economic opportunity gaps; descriptive Spearman with 21/42d oracle gap, paired block bootstrap (6 months, seed 65001). No fitting or policy based on these correlations; note multiple comparisons and missing independence.

## QA / decision
Require exact score and 180/180 OLC19 Top2 decisions; 2021–24 outcomes and support match frozen OLC61/63; counts and nonnegative gap decomposition reconcile independently. No future feature used for ranking. Label any artifact from the result as ex-post *oracle upper bound*. Inference based on months not ETF rows; overlapping 21/42 horizons, survivorship/observed-mask limitations. NO PROMOTION regardless of diagnostic numbers. The next *separate*, preregistered prospective experiment (if warranted) would modify only the upstream representation/target based on errors; do not optimize against these same dates.
