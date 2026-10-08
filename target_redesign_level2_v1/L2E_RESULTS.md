# L2-E — dual-ranker, frozen candidate tests — 2026-10-08

**Status:** completed; BOTH candidates **FAILED prespecified simultaneous robustness/predictive gates**. Historical development-only diagnostic. No write to `Etf_trader`. [Protocol frozen BEFORE candidate outcomes](L2E_PREREGISTRATION.md), GitHub commit `d4ff5f5de1898db7fe7b44328539dd2abe0334ef`.

## Methods and integrity

Reused exact fixed L2-C Ridge and L2-D three-seed canonical XGB predictions, 149 ETF x 113 mature 21-session signal dates x 3 Yahoo historical download vintages, equivalent **50,511** matched native rows, +50,511 held-input repeat2 rows. **No new fitting, tuning or future label in live selection rule.** Only same-vintage live predictions are combined. BIL never used as return benchmark, label or eligibility gate. The original ETF universe still contains BIL as an ordinary tradeable security.

Two candidates were predefined: 
1. **RIDGE_ANCHORED_75_25**: cross-sectional percentile score 75% Ridge + 25% XGB.
2. **XGB_TOP_QUARTILE_RIDGE_PICK**: XGB shortlists best 25% (ceil 37.25 = 38 of 149), final pick is highest Ridge rank in shortlist.

Audit **PASS**: exact source baseline replay and baseline vintage stability replicated, keys duplicate-free, 202,044 model/ticker/date/vintage rule-score rows, matched 113*149*3 native and common-input rows. Baseline proxy difference max `5.55e-17`. Source script `l2e_run.py`, SHA256 to be recorded in companion ZIP manifest.

## Forecast quality on 113 date equal weight, vintage equal within date

| model | NDCG@5 | Rank IC | Realized Top5 chosen | Selected ETF next-21-session net return | Realized top1 pct |
|---|---:|---:|---:|---:|---:|
| XGB canonical | 0.554145 | 0.064807 | **19.1740%** | **+2.4605%** | 0.588545 |
| Ridge | 0.561932 | 0.092917 | 7.9646% | +1.7618% | 0.548752 |
| 75/25 rank-score anchored | **0.574388** | **0.096993** | 13.5693% | +2.1931% | 0.560195 |
| XGB top quartile + Ridge pick | 0.569785 | 0.083117 | 10.3245% | +1.6661% | 0.543010 |

## Robustness against three Yahoo vintages

Native Top1 agreement among repeat1-2, repeat1-3, repeat2-3:
- XGB: 45.13%, 56.64%, 46.90%. Native rank MAD ~0.0532–0.0539.
- Ridge: 99.12%, 100%, 99.12%. Native rank MAD ~0.0010–0.00115.
- Rank fusion 75/25: **68.14%, 76.11%, 75.22%**. Native rank MAD **0.01634–0.01662**.
- Quartile vetting: **93.81%, 89.38%, 84.96%**. Native rank MAD **0.03231–0.03451**.

Common repeat2 inference inputs returned approximately the same pattern, so the instability in XGB is predominantly trained-model sensitivity, not a tiny perturbation at one inference call.

Fixed readiness gates were: all vintage pair Top1 agreement>=90%, Top5 hit>=15%, selected return>=Ridge, native rank-MAD<0.01. **Both fail.** Do not tune mixing weights or quartile breadth on this burned universe to force a pass.

## Selection-only monthly Top1 proxy (legacy L2-D fee convention)

| Candidate | Repeat1 CAGR | Repeat2 CAGR | Repeat3 CAGR | Monthly sampled drawdown range |
|---|---:|---:|---:|---:|
| Ridge | 17.09% | 17.12% | 17.09% | -31.66% |
| XGB | 19.56% | 22.14% | 31.88% | -41.88 to -52.68% |
| Rank-score 75/25 | **25.15%** | **22.53%** | **28.08%** | **-23.01 to -33.50%** |
| XGB-quartile/Ridge | 16.36% | 12.81% | 18.57% | -31.56 to -42.77% |

*These are historical top1 replay proxies, not canonical Hybrid24 or validated CAGR estimates. L2-F identified a minor extra terminal fee in this previous proxy; corrected baselines are recomputed there.*

Pairwise moving-block bootstrap 95% *exploratory, unadjusted* CI for 75/25 vs Ridge selected next21 net return difference **+0.004313**, interval **[-0.005884,+0.014274]** (includes 0). Its Top5-hit uplift **+0.05605**, interval **[+0.01475,+0.10324]**, no multiplicity correction. None of this constitutes a new independent holdout.

## Decision

The rank-fusion increases NDCG (0.574 vs 0.562 Ridge, 0.554 XGB) and Top5-hit over Ridge, but does not meet stability or Top5-hit threshold. The quartile veto increases selection stability relative to XGB but destroys most of the Top1 opportunity edge. **Do not promote either.**

Next use portfolio-level position sizing to *bound the XGB model uncertainty* rather than asserting score-fusion solves the root training instability. A separate capital-overlay hypothesis is recorded in [L2F_PREREGISTRATION](L2F_PREREGISTRATION.md) **AFTER L2-E results were seen**, and is therefore exploratory.
