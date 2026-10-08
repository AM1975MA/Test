# L2-J — Block-bootstrap XGBoost stabilization: preregistration (2026-10-08)

*Source-only development experiment. NO modifications to Etf_trader; write only in AM1975MA/Test branch research/target-redesign-level2-v1. Original149 extensively used in previous stages; outcome **diagnostic only**, not unseen validation.*

## Hypothesis

Training-XGB decision instability is a property of fit amplification. Aggregating rankers trained on overlapping but **temporally block-bootstrapped past signal months** may reduce dependence on individual, near-tied splits in the original 3-seed full-data ranker without losing its unusually high realized Top5 opportunity-capture rate.

## Fixed design before new outcome inspection

- Frozen Original149 full adjusted Yahoo OHLCV acquisition vintages `_repeat1/_repeat2/_repeat3`, 149 ETFs, same source artifact GitHub Actions 37121749852 ID 11272972639. 125 canonical Compact21 features, same 21-trading-day next-Open labels, same year/ETF eligibility threshold >=30 features as previous L2-D. No BIL benchmark label.
- **Test years 2021 through 2026**, strictly matured training rows at Jan1 cutoff of each year, annual expanding, evaluate next-Open outcomes with 21-session expiry on 2021-01 through 2026-06 inclusive, last end Jul31 2026. No future prices in features, no future matured labels in training.
- Three separate model replicas **per vintage/year**, each using **temporal moving-block bootstrap** of training signal-month groups, block length = 6 consecutive signal months, sample with replacement to 100% of training month count. For comparability across vintage, use exactly same month-index draws for each year/member across vintages; all training group members within each sampled date included together. Duplicate date samples are distinct XGB query groups. Deterministic RNG `rng_seed=20261008 + 1000*year + 101*member`, independent of Yahoo vintage.
- **XGB model** matches canonical XGB Compact21 rank objective/params and 360 boosting rounds, except train group resampling and members. One fixed seed per member `[101,202,303]`, nthread=1. Baseline original XGB has the same 3 seeds and full training dataset, with its frozen outputs from L2-D. This compares the specific intervention of resampled groups; no other learner/target/feature changes.
- After fit, score members on own vintage native features and also **same Repeat2 fixed inference feature panel** (training-vintage-stability check). Per-member within-date rank percentile; mean the three ranks to select ETF `BOOTSTRAP3`. No future outcome or cross-vintage information in prediction. Original XGB score baseline and Ridge control are already frozen L2-D.
- Preexisting 3-source-vintage XGB consensus (L2-I) is not a causal-live comparator, since those 2026 files would not historically be known; only a contextual risk diagnostic.

## Metrics and gates

- Whole signal date equal weight, after averaging vintage outcomes for 2021-2026, not treating vintage repeats as separate markets. Quality: realized Top5 winner membership, Top1 net 21-day return, NDCG@5, rank IC, realized percentile, regret.
- 3 pairwise native and common-repeat2-input stability: Top1 agreement, Top5 overlap, percentile rank MAD; inspect distribution of member-level disagreement, model diversity and bootstrap coverage.
- 2021–2026 regime and annual diagnosis: pre-existing SPY volatility (21-session annualized log-vol vs trailing 36 prior month-end median, shifted), no future data; no regime-based switching.
- Next-open single-name monthly executed proxy with 0.1% each actual buy/sell, no phantom terminal trade; compare on same dates to exact existing L2-D controls; *never call it Hybrid24 CAGR*. Long-only.
- Paired date-block bootstrap length three contiguous calendar months with 10k resamples, deterministic seed; descriptive CIs not multiplicity-corrected. Three vintage repeats NOT independent.
- Diagnostic advancement gate: all pairwise common-input Top1 agreement >=85%, native rank MAD <0.02, actual Top5 hit >=15%, and selected mean return >= Ridge on matched months. If ANY fail, **NO GO** without adjusting block length, members, seeds, model params or risk thresholds.
- Independent QA: train_exit<Jan1 strictly, train group month draws same vintage, complete native/common keys and target parity, no duplicate `(vintage,date,ticker)` in final outputs, prediction finite, backward matched realized returns, input/file SHA256, exact next-open fee accounting, two independent metric implementations where practicable.

Note 2021-2026 diagnostic sample is narrower than the original benchmark 2017-2026. Source dates start 2004; all vintage data are 2026-downloaded revised histories. Must show annual fragility, selection concentration, uncertainty; historical results cannot validate future edge or authorize production.