# ETF Trader V3 Corrected: tree model family and meta learning comparison

All source code and protocols are in `../../`. These experiments are **historical exploratory**, not a new untouched holdout.

## Comparisons
- 9 ordinary tree families including XGBoost, LightGBM, CatBoost, forests, hist boosted trees, and payoff regressions.
- 6 payoff-weighted binary classifiers, with loss magnitude and adverse error penalties.
- 4 ETF-pair invariant 23-feature families (same event = exactly same features).
- 4 14-feature basket-context-preserving families with inverse duplicate-pair weights.
- 3 STRICTLY time-matured nested selection comparators (9 families, 15 families, 23 families), tested against prior frozen V3 meta policy.

All training uses mature labels 60 days older than the first quarterly decision. 101 months; 149 ETF; canonical 500 baskets. Cross-sectional source OOS labels unchanged. Top3 membership invariant.

`archives/` includes all 26 complete successful GitHub artifacts; `tables/` contains directly inspectable summaries, yearly scores, fitting histories, selection audits and paired uncertainty.
`ARCHIVE_MANIFEST.json` stores original run IDs, source paths, byte counts and SHA-256 of every file.
**Do not promote any candidate until truly unseen prospective evidence.**
