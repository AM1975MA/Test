# L2-B — Economic target vintage stability (DIAGNOSTIC)

**Executed 2026-10-08.** Repo: `AM1975MA/Test`, branch `research/target-redesign-level2-v1`. No changes to `Etf_trader` or production strategy. No training, portfolio replay, or optimization.

## Provenance

- Source archive: completed GitHub Actions run [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact ID `11272972639`, `yfinance-repeatability-v1-raw`.
- The three acquisitions were performed in one run with a frozen Yahoo contract, 149 Original149 ETFs, same-row adjusted OHLC, raw volume, 2004-01-01 through 2026-07-31.
- Downloaded artifact ZIP SHA256: `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`.
- All **447/447 ticker files** matched the individual SHA256 stored in their respective raw vintage manifests.
- Vintage manifest SHA256: Repeat1 `e1c6e9b55c652aaf2b5af0e01cd97808470d23800166ef651811e46405883a93`; Repeat2 `9c5906b22a2b871dd5bc5161935fdd32ec4db50d73e1fedb8b4d62f25918fe53`; Repeat3 `210ea5a73e6fc365d53a57ac110b588921e21e0b330b640236d5f12ee171518d`.
- Code: [L2 target generator](targets.py); frozen method: [PREREGISTRATION](PREREGISTRATION.md). Synthetic test suite was separately verified `11/11 PASSED` with `PYTHONPATH=/mnt/data`.
- Analytical script `l2b_analyze.py` and CSV panels are available as reproducible downloadable conversation artifacts accompanying this diagnostic; the committed summary is deliberately compact and does not contain downloaded Yahoo source data.
- Original149 and Holdout70 are already explored development data. All findings here are **diagnostic only**. The three vintages are not independent markets.

## Evaluation

- Month-end signal at close; entry next trading day OPEN; exit at OPEN + 21/42/63 trading sessions.
- The original 149-ticker membership is held fixed across all repeats; no learned eligibility applied.
- Comparisons: signal dates 2017-02-01 through 2026-06-30, only outcomes with exits no later than 2026-07-31.
- Constant assumed cost 0.1% **per leg** for isolated ETF trade labels (a proxy, not the frozen portfolio-turnover cost model).
- BIL cash benchmark and SPY market benchmark on same adjusted OPEN basis. Downside measured by adjusted LOW from entry day through the day prior to exit, also including exit OPEN.
- Also compared 252-day seasoned rows. Every 2017+ observation met this filter, so the `all` and `seasoned252` scopes have identical results.

## Coverage and distributions (Repeat 1, 2017+)

| Horizon | Mature dates | Rows | Mean net return | Median net return | Mean BIL-relative log alpha | Mean adverse excursion |
|---|---:|---:|---:|---:|---:|---:|
| 21 sessions | 113 | 16,837 | +0.6497% | +0.4635% | +0.2716% | 3.8603% |
| 42 sessions | 112 | 16,688 | +1.5164% | +1.0600% | +0.7503% | 5.3697% |
| 63 sessions | 110 | 16,390 | +2.3037% | +1.6646% | +1.1508% | 6.4554% |

These averages are **cross-sectional realized historical labels**, not an investable strategy return, return forecast, excess realized portfolio performance, CAGR, or causal proof of predictive skill.

Historical 21-session example: cash-relative alpha P01 `-0.168942` log units and P99 `+0.160905`; MAE P99 `21.5083%`. The alpha distribution is broad and outcome labels vary materially across years and asset categories.

## Pairwise raw-vintage numerical robustness, 21 sessions

Absolute differences are expressed in basis points of **fractional target values** (multiply raw fraction by 10,000), including log alpha.

| Pair | Max abs diff net return | P99 abs diff net return | Max abs diff BIL log alpha | P99 abs diff BIL log alpha | Max abs diff adverse excursion |
|---|---:|---:|---:|---:|---:|
| Repeat1 vs Repeat2 | 0.015945 bp | 0.007852 bp | 0.023552 bp | 0.013215 bp | 0.016201 bp |
| Repeat1 vs Repeat3 | 0.017415 bp | 0.007558 bp | 0.020851 bp | 0.011998 bp | 0.015737 bp |
| Repeat2 vs Repeat3 | 0.017220 bp | 0.007574 bp | 0.024283 bp | 0.011813 bp | 0.017281 bp |

All 16,837 21-session label rows were pairwise matched, with **zero missingness mismatches**.

## Realized cross-sectional ranking robustness

| Horizon | Monthly dates | Realized Top1 changes per vintage pair | Mean Top5 overlap | Max per-date percentile-rank MAD |
|---|---:|---:|---:|---:|
| 21 | 113 | 0 | 100% | 0.000090086 |
| 42 | 112 | 0 | 100% | 0.000090086 |
| 63 | 110 | 0 | 100% | 0.000090086 |

Minor lower-ranked pair inversions do occur: for 21-session ranking, 8/113, 6/113, and 6/113 dates respectively have nonzero percentile-rank change. This **does not** change realized Top1 or Top5 membership. The pairwise mean rank MAD is roughly `0.0000008`–`0.0000064` across horizons.

Moreover, **within a single vintage and date**, ranking by `gross_ret_h`, `net_ret_h`, `alpha_cash_log_h`, and `alpha_spy_log_h` is exactly identical on fully observed dates. This is a mathematical consequence of fixed fees, monotone logs, and subtracting the same benchmark for every ticker in that date, validated empirically over all 21/42/63 mature dates. Replacing the target is **not** intrinsically a better realized ordering; its potential benefit lies in learning the economic magnitudes instead of discrete relevances.

## Full-history coverage: BIL matters

For all raw monthly pairs mature by 2026-07-31, h=21:

- 40,230 signal/ticker slots; 35,033 valid 21-session ETF gross returns.
- 32,216 valid 21-session BIL-relative alphas (versus 35,033 valid gross returns).
- **2,817 additional missing labels** arise from BIL not existing in early history; none in the 2017+ evaluation.
- For all h, BIL-only historical coverage loss is the same 2,817 rows. A matched-cohort control is mandatory for fair target comparison.

## Regime/category caveat

On Repeat1 the mean 21-session cash-relative log alpha varies by calendar signal year, e.g. 2018 **-0.9086%**, 2020 **+1.3434%**, 2022 **-0.2709%**, and 2023 **-0.8127%**. Mean adverse excursion likewise changes from 1.98% (2017) to 5.97% (2022). These are descriptive **pooled ETF-period** averages, not performance of a selected portfolio and not independent monthly outcomes across ticker rows.

## Conclusion and L2-C gate

**Evidence supports stability of the realized continuous economic labels themselves against the three acquisition vintages. It does NOT demonstrate a trained continuous regression model is stable or more predictive.** The previous explosive model sensitivity needs to be tested at the fitting stage.

Next compare a **fixed identical regularized learner** under three label contracts on strictly identical training/test cohorts:
1. continuous `target_rank_21` control;
2. continuous `net_ret_21` economic regression;
3. continuous `alpha_cash_log_21` economic regression.

Keep all 125 frozen features, annual prequential cutoff and causal label maturity, fit preprocessing on train only, normalize/compare realized prediction outcomes per month, retain all score vectors, and compare matched per-date predictive regret, Rank IC, NDCG@5, native/common-inference vintage stability and selected ETF turnover. Test horizon 21 first. Distinguish improvement in **model prediction** from robustness of the historical labels. No promotion from these burned historical samples.
