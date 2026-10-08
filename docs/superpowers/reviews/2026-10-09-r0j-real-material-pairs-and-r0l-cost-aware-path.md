# R0-J / R0-K / R0-L — REAL DATA result and implementable training direction
**ETF Trader V2 research, 2026-10-09 — DATA × Superpowers.** `AM1975MA/Test` branch `research/v2-xgb-immutable-checkpoints-20261008`. **No ETF training / no full-V2 backtest / no production changes.**

## Executive conclusion

**A genuinely actionable, source-grounded mechanism is now identified:** the canonical `rank:pairwise` target contains a tiny number of **economically indistinguishable** flipped or tied return comparisons when Yahoo revises historical prices. A cost-anchored first-stage definition of *material ranking pairs* (`|forward_return_i - forward_return_j| >= 0.2%` = **20 basis points**, matching the existing modeled 0.1% buy + 0.1% sell *round-trip commission*) preserved **96.21%** of authentic historical 21d comparisons yet eliminated **all strict pair sign inversions** between Yahoo Repeat1 and Repeat3 within the retained pair universe. Even **no high-decile-versus-low-quartile** comparison was removed.

**What this does NOT establish:** a better/stabler **fitted** Compact21, the original XGBoost objective's internal sampled-pair selection, a nondecreasing full-V2 CAGR, or an automatically justified cost threshold for every potential ETF switch. Note the independently proven **training-X-only sensitivity** (~62.5% Top1 disagreements in a limited four-year factorial): label-pair masking can fix at most one possible input-amplification mechanism. Treat as **promising, falsifiable candidate**, NOT model approved.

## 1. Real data, unchanged frozen historical source

**Source:** `/mnt/data/yfinance-repeatability-v1-raw.zip`, SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`. Yahoo Repeat1 vs Repeat3, 149 Original149 ETFs, 267 mature comparable historical month-end signal dates, 21 trading-session *next-Open to next-Open* returns. Pairwise integer labels computed as source-only `rank(pct=True)×100` rounded. This is a **price-derived training-label component**, not a reconstructed full 125-feature eligible training cohort.

Prior R0-G summary **reconfirmed**: **2,333,613 matched unordered ETF/date comparisons**, exactly **8 strict integer-relevance pair inversions**, **7 tie-to-ordered and 7 ordered-to-tie transitions** across Repeat1→Repeat3. All dates and ticker labels aligned **BY NAME**; includes older dates from 2004 through 2019. No model trained. All 16 changed integer-grade observations occurred before 2020 within the studied acquisition pair. Note pairwise sign reversals reflect real raw-return order only for the eight directly flipped pairs; extra 14 tie-status changes result from percentile label grading shifts and are not extra direct price-order flips.

### Economic size of changed relationships (observed, not assumed)

| Metric | Actual frozen Repeat1/3 Compact21 labels |
|---|---:|
| Strict changed pair orders | **8** |
| Maximum absolute 21d return difference of any strict flipped pair, across either version | **0.0116 bp** (0.000116 percentage points) |
| Relevance percentile range of flipped-pair members | **all below 81.3rd percentile**, none top decile |
| Pair transitions including created/destroyed integer label ties | **22** (8 flips+7+7 ties) |
| Maximum absolute 21d return difference across any of these 22 relationships | **7.6489 bp**, below a *single* 10bp modeled dealing side |
| Top-decile relevance ticker involved in these 22 relations | **0** |

**Important nuance:** 7.6489bp is not a price revision of 7.6489bp: it is the **original return spread between two other tickers** that became tied/untied when an adjacent ETF swapped ranks. The underlying vintage revisions can be orders of magnitude smaller. Do not confuse pair spread, price revision, commission and real selection regret.

Detailed dated 33-row 21d+63d read-only table: `ETF_R0J_pair_details.csv` in the accompanying reproduction ZIP (SHA256 `08886266c72781822bc78ec07b16ab6cc44bda613a6da24d766ea4d0c5e6ad3c`). Code: `etf_r0j_label_pair_detail.py` in package. The 63-session horizon has 5 strict inversions, 3+3 ties, and is **not** covered by the 21d complete-pair result below; 63d must be evaluated independently before any model adoption.

## 2. Cost-anchored 21d ambiguity coverage (one threshold from canonical fees, NOT a CAGR-tuned grid)

The canonical V2 economic replay assumes **0.1% fee on each actual buy/sell notional**. An illustrative **20bp** round-trip cost scale (`0.002` fraction) was used as a *motivated cutoff for comparing returns*, NOT automatically as a mathematically exact marginal switch cost or a fitted threshold. A 10bp one-side fee is displayed as a separate fixed existing economic benchmark, not used to select the best CAGR.

**Across ALL 2,333,613 authenticated Repeat1 eligible 21d pairs:**

| Statistic | 10bp | 20bp |
|---|---:|---:|
| Pairs with forward 21d return gap **below** fee scale | 45,181 (**1.9361%**) | **88,417 (3.7888%)** |
| Pairs **retained** at or above scale | 2,288,432 (**98.0639%**) | **2,245,196 (96.2112%)** |
| Pairs touching >=90th-percentile ETF, masked | 1,140/454,043 (**0.2511%**) | 2,373/454,043 (**0.5226%**) |
| True **top-decile vs bottom-quartile** relevance pairs masked | — | **0 / 118,939** |

The maximum observed 21d gap for ALL 22 changed integer-grade relations, **7.6489bp**, lies below BOTH fee scales; **none** is needed to distinguish clearly different 21d returns by either fixed V2 fee benchmark. However no trading alpha can be inferred from an oracle pair set based on *future* 21d returns: these labels are available only **after** their exit maturity, for causal annual training.

## 3. Robustness of economically material pair orientation across two real price vintages

The independently implemented material-pair sign comparison checks exact **paired same-ticker, same-date, same-exit** numerical return differences across Repeat1 and Repeat3, not just integer label identity:

| Property | At 10bp | At 20bp |
|---|---:|---:|
| Pair signs opposite where material in either vintage | **0** | **0** |
| Pair eligibility `|r_i-r_j| >= threshold` switches vintage-to-vintage | **17** | **14** |
| Pairs material in BOTH vintages | 2,288,421 | **2,245,191** |
| Pairs material in EITHER vintage | 2,288,438 | **2,245,205** |

There is still a very small **boundary set** near the 20bp cutoff (14 status changes), so "all selected training pairs byte-identical" is FALSE. Future loss design must explicitly handle this boundary uncertainty, not simply substitute a cutoff and declare solved. Also original XGBoost uses sampled pairs: 2.33m is a theoretical ALL-pair panel, not the counted internal XGBoost gradient pairs.

## 4. Non-promotable alternate objective check (R0-K)

Native XGBoost **3.1.3** was verified to train `rank:ndcg` with `ndcg_exp_gain=false` on actual **0–100 synthetic relevance labels**, retaining 125 features and nonlinear learning. The linear-gain parameter is **required** because default exponential gain supports labels only up to 31. The input `rank:pairwise` objective does not NDCG-weight gradient magnitude, unlike `rank:ndcg` ([official XGBoost 3.1 ranking manual](https://xgboost.readthedocs.io/en/release_3.1.0/tutorials/learning_to_rank.html)).

[Pre-registered R0-K](2026-10-09-r0k-objective-ndcg-prereg.md) before fitting. **First new independent synthetic world A, 3 seed ensemble, 360 rounds, 36×40 train, 12×40 eval**:

| Indicator | Canonical-like pairwise | Linear-gain NDCG |
|---|---:|---:|
| X-only training perturbation Top1 agreement | 9/12 | **12/12** |
| Y-only one real mid-grade pair swap Top1 agreement | 10/12 | **12/12** |
| Baseline selected top1 ∈ latent top5 | **11/12** | 10/12 |
| Baseline exact latent winner | **7/12** | 5/12 |
| Baseline NDCG@5 | **0.93374** | 0.90224 |

**Decision R0-K: NO GO for promoting native linear `rank:ndcg` as a ready-made solution.** It appears more consistent in world A but worse on **both synthetic top5/exact-winner and NDCG**. World B was only partially fitted (9/18 boosters when command exceeded runtime limit), **no complete World B quality/robustness metrics exist**. Since the preregistered quality guardrail already fails in World A, the remaining B fits were not relaunched or used to search a better parameter setting. This preserves previous failures and avoids cherry-picking. No actual ETF fitting, full V2 replay or CAGR.

## 5. Technical feasibility of a *selective* cost-aware pairwise objective (R0-L)

Implemented an **isolated experimental** full-pair logistic objective compatible with XGBoost 3.1.3 callback `obj(preds,dmatrix)`. It uses mature continuous *future* O2O returns **only in training**, an explicitly supplied group manifest and a 20bp cost-based ambiguity band; it excludes low-gap pairs and preserves larger comparisons, including actual top-tail comparisons. Analytical gradients/hessians are summed per query, with a positive Hessian floor to handle zero-material-pair groups.

**TDD evidence:** new tests were red (module missing) then GREEN **4/4**: masks close pair, retains top-return pair, exact invariance when microscopic ambiguous pair reverses, no effective pairs numerically safe, wrong group/shape errors. `python -m compileall` PASS. **Genuine xgboost 3.1.3 train smoke:** 10 artificial groups ×149 candidates, 125 features, 25 rounds, original depth/eta/reg parameters, returning **nonconstant** finite scores (std **0.665448**) and finished 25 rounds. Not actual ETF training.

**CRITICAL research caveat:** full-pair gradient normalization and XGB native pair-sampler are NOT equivalent; the prototype cannot be substituted into Compact21 without further work on objective semantics, numerical comparability and top-upside economics. This smoke test establishes **implementation feasibility only**, not model-quality or stability. A no-go on linear NDCG reinforces avoiding global top-score smoothing; it does not validate this selective pairwise candidate.

## 6. Recommended one bounded next test — STOP if it fails

**One experimentally motivated line:** `cost-aware confidence masking of ambiguous ranking pairs` in train labels, with **no hard ETF elimination**, **no changes to 125 features**, **no shorter/deeper trees**, **no MA3/risk stop overlays**. Unlike L50 label coarsening or Q4 features, it targets ONLY pairs whose realized 21d difference is below the existing modeled trade friction, with annual as-of label maturity, and lets a clearly superior but rare winner keep its comparisons. Custom gradient is unvalidated until tested on new synthetic groups. The economic improvement cannot be asserted now.

- Gate 1: synthetically validate training-X-only, Y-only and joint perturbations independently (previous X-only Top1 disagreement 62.5% real four-year factorial), under the SAME 360 rounds, 3 seeds, 2 horizons and fixed evaluation inputs, no hyperparameter sweep or posthoc mask band selection. If X-only remains unstable or top-tail ability weakens, **STOP**, or consider a separate X-side numerical split-candidate diagnostic; do not claim label masking solves V2.
- Gate 2: independently verify gradient normalization/sampled-pair bias with exact group-level fixtures and TDD; chronology `exit_date_h < annual_cutoff` and stable point-in-time return-adjustment. Ensure source-native 21/63 group conventions, objective compatibility, model serialization and score parity.
- Gate 3: **only genuine new, point-in-time financial data** and one candidate frozen *before economic labels are inspected*, matched full 2,366-style daily V2 comparison on same new period, annual causal fit, MA3/cluster and all risk/fees unchanged. Report per-vintage CAGR/net daily P&L, risk, exposure-weighted flip/regret, positive-tail selection, worst vintage and turnover. No user authorized financial model modification or production promotion at this stage.

**Do not conflate this with the historical Golden 43.146%**. Earlier vintage Repeat1/2/3 CAGR spread 4.9236pp and model X-only amplification are independent constraints for future validation.

## 7. Reproducibility
All actual executed source code, detailed pair CSV, TDD logs, complete R0-K World A score metrics, original frozen protocol and SHA256 manifest are in the conversation package `ETF_V2_Data_R0J_R0K_R0L_Ricerca_20261009.zip`, SHA256 `e1023db6f69bb31380d679baa41d43800c29ea55eff84066ccb323a99fefd472`; ZIP internal integrity PASS. Supporting generated file checksums: 33-row detailed pair CSV `08886266c72781822bc78ec07b16ab6cc44bda613a6da24d766ea4d0c5e6ad3c`; near-fee-band summary `ce7edd60aeb72a80f1a5b40e58b4eb1e349efd0351d61d8fd68209aabba21ccf`; cross-vintage material-pair summary `f2b14e92ae96b45feb6bc1f0809bd191ad00509317ff2ada953c717794f03fd6`.
