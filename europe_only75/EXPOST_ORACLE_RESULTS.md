# Europe-only EUR60: ex-post perfect-foresight benchmark (17–18 October 2026)

**Verified GitHub Action:** https://github.com/AM1975MA/Test/actions/runs/39084898663 — SUCCESS. Immutable frozen EU60 fresh-refit source from Action https://github.com/AM1975MA/Test/actions/runs/39071370480.

**Universe:** 60 Europe-exposure ETF ticker lines on EUR likely exchanges, extracted from 75 geographic-Europe candidates (45 original mixed-geography candidates excluded and 15 Europe-only non-EUR trading lines held separately), source roster ex-post filtered from the July 2026 frozen original120. Same monthly 113 decision intervals 2017-02-01 to 2026-07-01 and exact EU/US common-open execution calendar. No fit, no new prices. The original source model's registered fixed 50/50 return was exactly reproduced to ≤1e-12. Every hindsight and 50/50 comparator uses the same 10bp *one-way turnover* cost accounting, with 0.5×sum(abs(new target allocations−previous target allocations)) turnover.

| Portfolio | CAGR annualized | Terminal wealth / initial | Terminal from 10,000 EUR indicative |
|---|---:|---:|---:|
| Original R_H risk-managed V2 (separate risk/cost path) | 7.7645% | 2.057866 | 20,579 EUR |
| Original R_H simple Top2 fixed 50/50 monthly | 9.9780% | 2.448863 | 24,489 EUR |
| Predicted Top1 monthly with simple, same cost accounting | 9.0793% | 2.266759 | 22,668 EUR |
| Best ONE fixed ETF over entire test (CSMIB.MI), buy-and-hold indicative | 15.5300% | 3.890073 | 38,901 EUR |
| Perfect-foresight next-month best ticker (tradable 60), Top1 | **130.6541%** | **2617.484476** | **26,174,845 EUR** |
| Perfect-foresight Top2, constant 50/50 next-month | 113.0328% | 1238.429208 | 12,384,292 EUR |
| Perfect-foresight best Top1 limited to ETFs with R_H valid signal at month start | 124.1279% | 1997.573936 | 19,975,739 EUR |
| Perfect-foresight best Top2 restricted to R_H eligibility | 106.8741% | 939.505067 | 9,395,051 EUR |
| Perfect-foresight ex-post best decile, equal weight | 82.9383% | 295.144406 | 2,951,444 EUR |

Predicted R+H Top1 monthly average simple gross forward Open return = +0.9823% versus all-tradable ex-post best +7.4215%; signed ex-post top1 opportunity regret = **6.4392 percentage points per month**, counting all 113 months. Within R+H model-eligible instruments the ex-post top1 opportunity regret is 6.1879pp. Best buy-and-hold fixed ticker CSMIB.MI is identifiable **only ex post** and is not a legitimate ex-ante recommendation.

The >130% historical CAGR *oracle* assumes that on each signal date we can see each ETF's **future realized next-month price** before choosing the winner; this is knowingly impossible lookahead. Compounding this perfect foresight makes capital multiples explosive. Not realistic or statistically predictable, excludes practical constraints including live execution quality, taxes, effects of turnover beyond 10bps, time varying eligible constituents, survivorship, bid-ask spreads, and fund shares/duplicates. Do NOT extrapolate from it to model potential; it measures the extreme opportunity set, not attainable alpha.

The source input EU120 was selected with prices through July 1, 2026 and the EUR trading venue suffixes were not individually provider-verified; the sample is a retrospectively curated geography screen, not valid point-in-time investable universe. The old frozen 120-ticker source and full 75-Europe geography register remain immutable; new code `europe_only75/expost_oracle.py` is versioned in this PR.

**Artifact** `europe-only-eur60-hindsight-oracle` includes RESULT.json, ORACLE_COMPARISON.csv, and MONTHLY_ORACLE_113.csv; retention 90 days in GitHub Actions. No production change.
