# L2-H — smooth nonlinear ranker + consistency + abstention | 2026-10-08

**STATUS: COMPLETED / INDEPENDENT QA PASS / NO GO for both nonlinear candidates.** Scope of GitHub writes: **AM1975MA/Test only**, branch `research/target-redesign-level2-v1`; `Etf_trader` was not changed. [Protocol registered before inspecting results](L2H_PREREGISTRATION.md), commit `c0f457e4c2237f588925f241eef52f1d110fb335`. The common-RNG investigation below is explicitly **POST HOC**, not a preregistered confirmatory result.

## Evidence and design

- Three **frozen repeats of the same historical Yahoo price history**, Source GitHub Actions run [37121749852](https://github.com/AM1975MA/Test/actions/runs/37121749852), artifact `11272972639`; ZIP SHA256 `fcc02918b3a42c3fecde273c4639ca4eed1b5f31e4b8c32aeea4c2a8e4c00f86`.
- Original149 universe, same 125 Compact21 features and same monthly next-Open 21-session return/rank targets as L2-C/D/G. **No BIL benchmark dependency**. Train annual expanding, strictly mature exits before January 1 cutoffs, 2019–2026 inclusive, 3 repeats, 8 years each: **24 separate annual fits** containing both mathematically matched variants, equivalent to 48 fitted coefficient solutions. 90 mature monthly decisions, 149 ETFs, 40,230 date/ticker/vintage mature comparisons and 40,677 total predicted ETF/vintage/date keys per model including 2026-07 nonmature inference not scored.
- `FOURIER_DIRECT`: deterministic RBFSampler 128 nonlinear Fourier features (`gamma=1/250, random_state=47`) + all 125 train-standardized input features divided by sqrt(125), imputer median, L2 alpha=20, unpenalized intercept; direct squared-error minimization to continuous percentile rank.
- `FOURIER_CONSISTENCY`: exactly same feature map, base target and model, plus `lambda=300` PSD penalty enforcing small local score differences under 3 fixed 0.05-standard-deviation perturbations of standardized *training* X. Linear system solved uniquely each year. Original registered experiment generated perturbation RNG with **vintage-dependent seed** `89+100*(vintage_id+1)+year`: a key measurement confound exposed by auditing.
- `ABSTAIN_005`: select Fourier consistency Top1 only if its predicted score exceeds its own predicted score for Ridge's Top1 by >=0.05 continuous rank units, otherwise stay with the Ridge choice. Only past-fit and contemporaneous scores. No refit, switch threshold search, or price-future information. The rule selects Ridge in **76.67%** of original decisions.

## Preregistered experimental results, same 90 signal dates

Date equal weighted after averaging 3 same-market downloads per date. Selected mean 21-session net returns are **not CAGR or verified future returns**.

| Learner | NDCG@5 | Rank IC | Realized Top5 selection hit | Selected mean net return | Repeat2-common-input Top1 agreement |
|---|---:|---:|---:|---:|---:|
| Canonical XGB | 0.555209 | 0.065641 | **21.4815%** | **+2.7002%** | 43.33–60.00% |
| Ridge alpha30 | 0.565574 | 0.106594 | 10.0000% | +2.2410% | **100%** |
| FOURIER_DIRECT | **0.571690** | 0.096918 | 7.7778% | +1.7311% | **98.89–100%** |
| FOURIER_CONSISTENCY | 0.557253 | **0.110135** | 2.9630% | +1.3360% | 94.44–97.78% |
| ABSTAIN_005 | n/a | n/a | 6.6667% | +1.7896% | score rank n/a; native **100% selection agreement** |

The raw vintage pairwise mean rank-MAD for FOURIER_DIRECT is **0.000926–0.001011**, and for registered FOURIER_CONSISTENCY **0.004453–0.004631**. All historical labels and frame keys matched. Interpreting consistency as necessarily harmful to stability **would be premature**, because the seeded training perturbations differed across vintages.

**Prespecified joint gate**: 3 pairwise common-input Top1 agreement >=90%, native rank MAD<0.01, Top5 selection hit>=15%, selected mean return >=Ridge on matched dates. FOURIER_DIRECT and FOURIER_CONSISTENCY **both FAIL, unequivocally**, due to lower Top5 hit and lower selected return. ABSTAIN is not a standalone alternative ranker and also has weaker Top5 and return.

Descriptive date-block bootstrap 10k replications, 3-month blocks:
- FOURIER_DIRECT minus XGB Top5 difference `-0.137037`; unadjusted 95% interval `[-0.222222, -0.051852]`. Return delta `-0.009691`, interval `[-0.032009,+0.012426]`.
- FOURIER_CONSISTENCY minus Ridge Top5 difference `-0.070370`, CI `[-0.125926,-0.018519]`; next21 return delta `-0.009050`, CI `[-0.024002,+0.005935]`.
- FOURIER_CONSISTENCY minus FOURIER_DIRECT Top5 `-0.048148`, CI `[-0.114815,+0.014815]`. Multiple historical experiments and no independent holdout prohibit interpreting any of these as validated future superiority.

## SECONDARY POST-HOC diagnostic: use identical perturbation stream for each vintage's same training year

After studying original outcome, we identified that `rng=89+100*(vintage_id+1)+year` had **introduced extra training variation across vintage experiments**, contrary to the goal of comparing strictly data-driven changes. Ran another full 24-fit diagnostic with **only that seed changed to `89+year`**, keeping **all other penalties and hyperparameters identical**. This second run **cannot be represented as original preregistered candidate validation**.

| Diagnostic outcome for consistency variant | Original vintage-dependent random stream | Same perturbations on all vintages |
|---|---:|---:|
| Held identical Repeat2 input, Top1 agreement | 94.44–97.78% | **98.89–100%** |
| Native max pair rank-MAD | 0.004631 | **0.000634** |
| Realized Top5 membership | 2.96% | 3.33% |
| Mean selected net 21-day return | +1.3360% | +1.5953% |
| NDCG@5 | 0.557253 | 0.558774 |
| Selected monthly proxy CAGR (3 vintages) | 11.99–16.93% | 18.12–19.61% |

This demonstrates that **much of the initial apparent instability was due to the experiment's random perturbations, not market-vintage data**. With the stream controlled, consistency **does** reduce the full ranking's native rank-MAD compared to direct `0.000926–0.001011` to `0.000492–0.000634`. It nevertheless substantially **reduces selection capability** relative to XGB and Ridge. The scientific conclusion is not “regularization can never work,” but **“this fixed regularizer oversmooths useful Top1 signals at tested settings.”** Do not change lambda or noise magnitude on this burned data to seek a better CAGR.

## Execution and risk (89 continuous monthly periods; simple one-ticker Next-Open proxy)

All models matched 2019-02 to 2026-07 using adjusted Open, fixed 0.1% of actual buy/sell notional, no phantom terminal transaction. **NOT** Hybrid24 whole-strategy CAGR, and monthly peak-only drawdown can miss intraperiod worst drawdown.

| Learner | Repeat1 CAGR | Repeat2 CAGR | Repeat3 CAGR | Monthly sampled max drawdown |
|---|---:|---:|---:|---:|
| XGB baseline | 22.28% | 23.31% | 33.91% | −41.9 to −52.7% |
| Ridge baseline | 22.22% | 22.22% | 22.22% | approx −24.65% |
| Fourier DIRECT | 20.88% | 20.88% | 20.58% | approx −22.00% |
| Consistency ORIGINAL | 16.74% | 11.99% | 16.93% | approx −35.47% |
| ABSTAIN original | 18.54% | 18.54% | 18.54% | approx −31.58% |

A stable, smooth model can reduce retrospectively sampled max DD, but can also lose substantial opportunity capture. The stable abstention overlay is **not** economic risk control in itself; Top1 return and DD worse than Ridge on this experiment.

## Econophysics/regime analysis (diagnostic)

SPY 21-session historical realized annualized volatility above/below the prior 36 month-end median, no future inputs, approximately 45 dates per regime:
- FOURIER_DIRECT: net selected next21 +0.878% in low-vol dates, +2.584% high-vol; Top5 hit 4.44% low vs 11.11% high.
- FOURIER_CONSISTENCY: +0.787% low vs +1.885% high; Top5 hit 3.70% low vs 2.22% high.
- XGB: +2.353% low vs +3.048% high.
- Ridge: +1.410% low vs +3.072% high.
These subgroup historical summaries are not calibrated regime-gating rules or evidence of predictable regime conditional edges. Macro-state clustering, long tails and survivor ETF universe constrain generalization.

## Independent audits and reproducibility

Two independent audit executions (`results/INDEPENDENT_AUDIT.json` and `results_common_seed/INDEPENDENT_AUDIT.json`) both **PASS**:
- 24 year/vintage fits, strict historical 21-day maturity, full common keys, no duplicate records.
- All 40,230 matured selection rows; exact sample row agreement.
- PSD regularization with positive penalty trace and nonzero coefficient change.
- All Repeat2 native predictions match common held-input outputs **exactly**.
- Selected ticker and realized return independently rechecked across 270 signal-vintage dates.
- **15** modeled portfolios, **1,335** monthly buy/hold/sell records, continuity and compound equity identity checked.

Exact executed `l2h_fit.py`, `l2h_eval.py`, `l2h_independent_audit.py`, post hoc controlled-seed code, per-ticker native and held-input scores, regime, bootstrap, yearly, full trade ledgers and SHA256 manifest are in conversation file `ETF_Trader_L2H_smooth_ranker.zip` (56 items; ZIP self-test PASS). GitHub hosts this report and preregistration; raw Yahoo acquisition remains in its original GitHub Actions artifact and is not copied into the repository.

**Decision: DO NOT PROMOTE any Fourier candidate.** The next fundamental question is how to retain XGB's Top5 opportunity skill **without fitting fragility**. Another smooth-convex model does not solve it. Test future truly unseen data and/or dedicated robust nonlinear objective (e.g. explicit cross-fit teacher model distribution) only after freezing a fresh independent evaluation protocol. Avoid post hoc parameter search on this repeatedly examined historical sample.
