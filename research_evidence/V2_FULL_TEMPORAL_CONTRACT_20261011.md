# V2 temporal history retention / ETF eligibility — code-derived gate (2026-10-11)

## Prior-work check
Checked Test PR searches for MA3 as-of, Tail Macro eligibility, retention, temporal audit. PR #68 audits Compact21 *pre-2017 feature coverage*, PR #51 audits data, and PR #40 addresses different EU120 holdout. **No equivalent certified full V2 prefix-truncation parity experiment was found in PR search.** Historical code descriptions and PR search are not proof that no hidden artifact exists.

## Verified code sources (frozen vendored V2)
- `vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py`, functions `build_features` and `fit_predict_all`.
- `vendor/etf_trader_v2/scripts/build_ma3_panel_source_only.py`.
- `vendor/etf_trader_v2/src/etf_trader/ma3/ensemble.py`, `hybrid_producer.py` and `producer.py`.
- `holdout70/v2_canonical_same_source_compare.py` on historical source branch `research/v2-same-source-149-vs-70-20261002`, and PR #68 pre-2017 coverage run 38171032263.

## Subsystem-specific contract
| Subsystem | Observed code-level temporal requirement | Pruning implication |
|---|---|---|
| Compact21 signals | Momentum 252 daily lags; vol etc shorter; numerical valid threshold currently 30/125; feature transforms include cross-sectional ranks/devs. A complete 125/125 panel differs from merely meeting 30/125. | 253 closes can cover some long lookbacks but does **not** replace supervised historical training; ticker-specific as-of inclusion required |
| Titanium/Compact21 annual training | For year Y, training uses `signal_date < Jan1(Y)`, `exit_date_21 < Jan1(Y)` and >=30 usable Compact21 features, minimum 60 distinct signal dates; no maximum rolling cutoff. | Mature pre-2017 training observations from earlier history participate in first 2017 model; cannot drop these without retrain/parity test |
| Titanium Tail | Kernel uses 60 ranked Tail predictors and >=12 non-NA features, year-Y fitted Ridge using labels with `exit_date_63 < Jan1(Y)`. | Needs earlier Tail feature history and 63-session label maturity; one simple global 253-session threshold is not enough to establish model correctness |
| Macro / Opportunity | Kernel fits macro with matured 63-session targets and opportunity with matured 21-session targets; feature computations consume ticker history and cross-sectional groupings. | Truncating source dates can change both feature transforms and training examples, hence predictions and allocation |
| MA3 feature panel | `build_ma3_panel_source_only.py` starts signal dates only after `calendar.min()+365 days`, uses `valid_count = close_cluster.notna().rolling(252,min_periods=1).sum()`; feature families include 200-day moving averages, 126-return windows and 63-session rolling statistics; builds 21/42/63 forward label maturities. | Has both calendar-based entry gate and ticker-level coverage; prefix removal can change panel's nominal first year **even if 252 observations remain** |
| MA3 annual hybrid models | `ma3/hybrid_producer.py` and `producer.py`: fit each year Y on **all** panel rows where `signal_date < Jan1(Y)` and `exit_date_63 < Jan1(Y)`; no fixed training rolling horizon; prediction on current year. | Historical data before 2017 form training corpus, **cannot** be removed and preserve identical fit |
| Stage19 execution | Consumes source-aligned `TIT_R`, MA3 predictions, open/close/low prices, monthly entry/exit schedule and risk/market refs. | Historical execution parity must also be verified before declaring a truncated input usable |

## Current measured boundary and interpretation
Completed [run 38171032263](https://github.com/AM1975MA/Test/actions/runs/38171032263) confirms frozen research Compact21 panels can have first 30-feature-eligible signal on **2004-02-27**. That is NOT a proven raw OHLC truncation start date, NOT a proof of a mature labeled example at that date, and NOT the first useful MA3 example.

**Gate: NO SAFE HISTORY TRUNCATION APPROVED.** The existing frozen V2 research fits use expanding-year historical training, so dropping pre-2017 history without end-to-end matched-data equivalence changes the scientific experiment. The fact that 149/149 tickers had at least one incomplete row reflects past lookback warmup and cannot justify replacing all 149 ETFs. Use per-date per-ticker eligibility only once the specific model's required feature and as-of rules are certified.

## Concrete next engineering step — if a smaller stored window is still desired
1. Keep originals frozen, create derived candidate truncated raw inputs ONLY on Test.
2. Assert exact date, ticker and value parity of all pre-2017 **training rows and mature labels** used by Compact/Tail/MA3/Macro/Opportunity. If candidate drops any participating example, declare it a **changed training policy**, not safe deletion.
3. Assert matching feature panels, cross-sectional ranking universe, train group memberships and per-year fit decisions, followed by identical prediction series and executive replay on the fully frozen pipeline. Required fit checks will cost compute; not performed in this code-only audit.
4. Otherwise keep the existing 2004-start frozen research history intact. To save disk, compress/partition raw archives rather than silently alter V2.

## Decision
Implement no physical deletions, no global ETF substitution based on warmup, no new training and no production changes here. The first 2017 model cannot be certified with `just 253 trading days of history`, since years of mature training outcomes are explicitly used. V2 baseline remains unchanged; quality issues independent of missing warmup remain unresolved.
