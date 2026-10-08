# R0-D Results — Ex-ante dispersion DOES NOT predict Top38 false negatives
**ETF Trader V2 research · 2026-10-08 · READ-ONLY diagnostic (no training, no full-V2 backtest).**

**Branch:** `AM1975MA/Test@research/v2-xgb-immutable-checkpoints-20261008`. **Pre-registered BEFORE the diagnostic** at [R0-D protocol](2026-10-08-r0d-exante-dispersion-prereg.md), commit `4ab72abd61cf96c8360d9f8f974c9ddd08064c18`. No retuning, no training, no change to the canonical V2 or production repositories.

## Decision (read this first)

**NO GO for an adaptive Top38 exclusion rule based solely on observable 21d/63d trailing cross-sectional return dispersion.** The proposed regime signal successfully predicts **some** future *return dispersion*, but has essentially **no discrimination of which months lose the actual winner**. It is not worth fitting/tuning an adaptive cutoff on these exhausted 2017–2026 data.

**Do not confuse this with invalidation of the separate ideas** of a capacity-controlled canonical XGBoost (`max_leaves / split` diagnostics), a regularized Dense ranking network, or a future broader/reversible funnel trained and checked on genuinely new, independent point-in-time data. The findings specifically reject **this** volatility-proxy-driven adaptive screen on this already-used LTR retriever.

## Data and exact as-of boundaries

- Repeat2 `titanium-repeat-2.zip` containing 149 adjusted OHLC CSVs; **Close[t]/Close[t−N trading sessions]−1** on historical **signal date**, N=21 and N=63, using SPY reference trading calendar; sample cross-sectional standard deviation over 149 tickers. The decision occurs at the next month's first open; the signal feature does NOT use future data.
- Existing `/mnt/data/OOS149_return_dispersion_monthly_repeat2.csv`, 114 ex-post 21-session open-to-open cross-sectional return dispersions and exact best return/winner; generated *before* this diagnostic and previously validated 114/114 against frozen Evidence V1 global winners.
- `evidence_v1/checkpoints/retriever_ltr_v1/OOS_PREDICTIONS.csv` frozen OOS ranked 149 tickers, Git blob `1745a6d12b6957bc629998c7ac3417550ac9bceb`, `evidence_v1/results/cascade_v1_ltr_top5_hybrid24/MONTHLY.csv` Git blob `85ce4db4600efdb701b045d87d89cd099310459a`.
- Fixed retrospective cohorts: 2017–2022 (72 signal months); 2023–2026 June (42). This period split was proposed by the user after seeing prior results and is **not** an independent hypothesis test.
- All **114/114 dates have complete 149/149 trailing 21d AND trailing 63d histories**; no altered universe, date dropped, missing historical close or imputation.
- Frozen Top38 OOS LTR retained actual future best ETF in 97/114; miss on 17/114. LTR retriever is NOT full V2 Compact21 nor its trading engine.

## Observed statistical results

| Metric | Trailing 21d cross-sectional SD | Trailing 63d cross-sectional SD |
|---|---:|---:|
| Spearman rho with **future** 21-session cross-sectional SD | **0.484579** | **0.494980** |
| Calendar-year-block bootstrap 95% interval, 2,000 draws | [0.157,0.683] | [0.143,0.674] |
| Spearman rho with Top38 **winner miss** | **−0.018334** | **−0.037791** |
| AUROC of *low* trailing dispersion flagging a Top38 **winner miss** | **0.514857** | **0.530625** |
| Year-block 95% AUROC intervals | [0.432,0.629] | [0.424,0.766] |

**Interpretation:** historical dispersion contains a moderate monotonic association with future dispersion, but AUROC near **0.50** is essentially random classification of the months that actually lose the best ETF. Wide intervals encompass chance. No classifier was fitted; AUC uses rank ordering of the raw predictor itself, with *lower* dispersion predicting a miss. Do not cherry-pick 63d as 'better' after seeing these results. Bootstrapped calendar years account for within-year clustering only crudely and are not independent market evidence.

Regime descriptive means:

| Metric | 2017–2022 (72m,16 misses) | 2023–2026 (42m,1 miss) |
|---|---:|---:|
| Trailing 21d cross-sectional SD | 4.3413% | 4.6225% |
| Trailing 63d cross-sectional SD | 7.6383% | 8.6899% |
| Forward 21d cross-sectional SD | 4.5237% | 4.7518% |
| Among **missed** months, trailing 21d SD | 4.4778% | 3.9261% (n=1) |
| Among **retained** months, trailing 21d SD | 4.3023% | 4.6395% |

Early-period correlation between trailing and forward SD is stronger (Spearman **0.5863/0.5962** at 21/63), but early-period AUROC for **miss** is **0.4598/0.4554**—not useful. Later-period AUROC estimates ~0.76/0.78 reflect **a single miss**, so have no meaningful classification reliability. Improved Top38 capture after 2023 may relate to more training data, different market regimes, earlier ranking quality or the true exceptional-winner signal, not merely trailing SD.

## Investment/portfolio risk read-through: irrecoverable opportunity cost

For each of the 17 actual miss months, the previously frozen LTR **Top38 members** were used *without refit* to calculate the **best forward O2O 21-session return theoretically available inside the retained 38** and compared with the single global best among all 149. The difference is a **perfect-foresight ORACLE opportunity gap**, never the realized return of any proposed ETF strategy.

- 97/114 months gap **zero**, as true best ETF is in the Top38.
- On 17 miss months, **mean opportunity gap +4.0066 percentage points per 21-session period**.
- Across all 114 months, mean gap **+0.5975 pp/period**, which CANNOT be annualized as an expected CAGR loss.
- **Six missed winners** create an oracle gap exceeding **5 percentage points** in that month.
- Worst: **2021-07-30, ARGT** returned **+18.3031%** over the future 21 sessions; the strongest Top38 survivor **UNG** returned **+6.8003%**; irretrievable gap **+11.5029 pp**.
- Other large miss examples: 2020-11-30 URA ~8.96pp; 2021-03-31 CORN ~7.27pp; 2020-05-29 KWEB ~7.12pp.

This is an informative downside for **hard exclusion of winners**, but it is *not* an executable return spread (requires perfect future foresight), full V2 regret, exposure-weighted P&L, transaction-fee impact, or proof that V2 holdings would differ in these months. Therefore no 'lost CAGR' should be inferred from 0.5975pp.

## Technical reviewer cross-checks

- Cross-sectional 149/149 coverage for both ex-ante horizons on every date.
- Original historical data are never refitted, and current source `rank:pairwise` / MA3 / risk rules untouched.
- Weekday/date alignment: signal date close **precedes** next-open entry; future 21 sessions use previously validated O2O21 open-price convention; no future return enters a predictive feature.
- AUC computed from raw trailing dispersion, without trained weights and without choosing a decision threshold.
- Yearblock intervals use fixed 20261008 RNG seed, 2,000 resampled sequences of complete calendar years. Correlation and AUC reported for both pre-fixed horizons, not best-of-two.
- Separate verification reported 114 rows, all 149 histories present, 17 misses; read-only audit finds the 2017–2022 miss case in fact has *slightly higher*, not lower, mean trailing 21d dispersion than retained cases.
- No actual XGB boosters were found in tracked GitHub Test tree or available accompanying research archives: original split structure cannot be reconstructed from OOS scores.
- Results are **development-grade** because the same Original149 history has been researched extensively. The 2023 regime split was noticed after looking at outcomes; statistical CIs do not cure this selection bias.

## Updated plan and stop conditions

1. **STOP** further fitting, moving-cutoff tuning or CAGR optimization of a Top38 screen conditioned only on trailing 21d/63d cross-sectional SD on Original149.
2. **KEEP** the top38 frozen recall observation 97/114, but require genuine as-of canonical Compact21 predictions and exposure-weighted full V2 outcomes before evaluating a cascade in a new period. Recall is not a performance outcome.
3. **PRIORITIZE structural XGBoost diagnosis** (tree split/gain sensitivity); actual authentic boosters may not be archived, so design a new **synthetic-only** split-node falsifier instead of rerunning historic ETF training.
4. **SECONDARY analytical feasibility** of regularized compact Dense neural `rank:pairwise`/listwise models, focusing on effective independent time observations, loss/labels, capacity and chance of erasing positive-tail alpha. No model fit has occurred.
5. Before any **new financial experiment**, lock one intervention, model lifecycle IDs, as-of data, same-universe matched full V2 evaluation, yearly/signal maturity, daily MaxDD, costs, turnover and **per-period tail opportunity capture**, with genuine future snapshots rather than selecting winner from historical vintages.

## Reproducibility and local support artifacts

`r0d_exante_dispersion.py` SHA256 `7715a834c96189e78a7efb4d098a7e5c0c6144a433f7d9ce779bb9be19923a8a` (10,529 bytes).
`r0d_exante_dispersion_results.json` SHA256 `252e4e31bdb8484d01cfe376968458804ed048df65c47ecb8f75cbca3f2211df`.
`r0d_exante_dispersion_monthly.csv` SHA256 `407df79bf446ee35a81590823490fed738ed0039ca0662fcef6e190cee6456c5`.
The helper embeds **only the 17 Top38 membership lists for missed months** from the original frozen LTR GitHub blob. It does not generate or fit ranking predictions. It is distributed in the linked conversation ZIP artifact, not silently claimed committed into GitHub Test.

**STATUS: diagnostic complete, branch research updated; no model or V2 performance improvement demonstrated.**
