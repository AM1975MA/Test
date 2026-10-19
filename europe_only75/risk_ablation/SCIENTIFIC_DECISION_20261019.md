# Europe-only EUR60 risk ablations: final verified scientific decision
19 October 2026. Verified GitHub Action [39294988228](https://github.com/AM1975MA/Test/actions/runs/39294988228) **success**, all research source, first protocol, 5 unit tests, Europe geography unit tests, frozen annual EU-only models and originals match, evidence + checksum committed under results. No production modifications.

## Attribution: do NOT conflate American F3/H1 and European R_H
This experiment is on the **60 candidate EUR listings with strictly European-underlying ETF exposure**, subset of 75 qualifying European funds (other 15 trade non-EUR) conservatively filtered from 120 mixed original. Original 45 excluded for geography/legal vehicle or insufficient issuer-geography evidence. The price/source universe is retrospectively curated based on coverage in July 2026 and NOT point-in-time. Currency and ISIN deduplication not fully verified.

Annual walk-forward EUROPE-trained models: source Action [39071370480](https://github.com/AM1975MA/Test/actions/runs/39071370480), 10 folds, source score COMPACT_REFITTED and HYBRID_REFITTED, strictly matured training observations before each fold. No American F3/H1 signal or American 149 instrument enters the ranked European portfolios. Europe reference is R_H: 47.5% return-aware rank +52.5% Hybrid Tail from European models, top TWO eligible ETFs monthly, equal 50/50. Same 113 monthly 2017–26 completed periods, 2277 common joint OPEN marks and previous Close state. Original legacy EUR60 approx cost 50/50 reference replicated **2.448863449071206 vs archive 2.448863449071208**, abs error 2.22e-15, CAGR 9.9780%; BUT the original legacy study used simplified 0.5*target-weight turnover fee instead of capital-conserving shares. Do not compare that 9.978% to newly audited real share 9.0467% as if strategy changed; fees and drift accounting differ. Every new trial shares the SAME new 10bps each ETF buy/sell (zero-interest, zero transaction fee cash) and exact monthly self-financing engine.

## Policy results
| European strategy | Net CAGR | Open MaxDD | Sharpe daily log | Worst 5% Open return ES | Avg ETF fraction | Cash months |
|---|---:|---:|---:|---:|---:|---:|
| B0 R_H Top2 | 9.0467% | -44.0176% | 0.3969 | -3.3369% |100%|0|
| E1 Same-category 20% cash | 7.2012% | -37.8103% | 0.3816 | -2.8161% |86.37%|77|
| E2 Covariance vol20 | 7.9757% | -43.6737% | 0.3991 | -2.8877% |94.03%|30|
| E3 Prior 126-close trend | 4.5998% | -28.5006% | 0.3204 | -2.2288% |72.57%|62|
| E4 Top2 score buffer | 10.4167% | -44.0176% | 0.4511 | -3.3655% |100%|0|

E1 avoids double European macro category: 77/113 signals matched category. E2 cut investment in 30/113 months, E3 in 62/113, E4 changed ETF holdings in 15/113 decisions. The 20%-cash macro-category heuristic is NOT a validated exposure-beta hedge, and volatility/negative trend cannot remove future gap loss.

## Grouped statistical tests vs same cost-model European B0
98.75% two-sided Bonferroni-adjusted 3-consecutive-month circular-bootstrap CI, mean paired monthly **net log advantage**:
- E1 category: -0.00142135, CI [-0.00322419,+0.00049617]; DD improves **6.21 pp** but CAGR -1.8455 pp/y; negative paired mean in EACH era.
- E2 vol20: -0.00082185, CI [-0.00269592,+0.00059278]; DD improves **0.344 pp** but CAGR -1.071 pp/y.
- E3 trend126: -0.00346709, CI [-0.00828128,+0.00091062]; DD improves **15.52 pp** but CAGR -4.447 pp/y, negative relative mean in each era.
- E4 buffer: +0.00103976, CI [-0.00056813,+0.00304738]; DD is EXACTLY the same as B0 on historical sample, daily ES **worse by 0.0285 pp**; early era 2017-20 negative, 2021-23 and 2024-26 positive. CAGR +1.37 pp/y is descriptive, NOT significant.

**ALL FOUR PRECOMMITTED JOINT ACCEPTANCE GATES FAIL.** No policy demonstrates both increased CAGR and reduced DD with familywise-controlled paired evidence on this archive. New European evidence substantiates a structural risk-return tradeoff: cash-based risk protection meaningfully reduces historical maximum loss but sacrifices returns; turnover buffer increases retrospective CAGR without risk protection. No strategy is appropriate to deploy.

## Next validation priority
A fair longer term strategy should revisit **European ranking portfolio concentration** before risk filters: Top2 ETF always 50/50 leads to significant -44% observed daily-common-Open drawdown. Test separately more European holdings (e.g. Top5/Top6) ONLY under independently preregistered controls and genuine future validation, or derive a distinct Europe-only multi-expert combination using untouched predictions. Benchmark passive Europe equity/Euro sovereign, tax, EUR brokers and volatility at equal budget. Do not optimize TopN after seeing the old 2017-26 returns and label any retrospective winner a scientific discovery.

Requires live ISIN, exchange FX, UCITS, historical membership/delistings and point-in-time provider prices. Existing data EUR60 still contains duplicated fund listing risks and has already been mined. Source yahoo prices originally downloaded/frozen, not new current vintage. No actual order book spreads or taxes. Treat this as a historical diagnostic not financial advice.

Full source and checkable SHA256: results/RESULT.json, results/EXACT_EUROPE_COMMON_CALENDAR.csv, results/MONTHLY_EUROPE_ONLY_WEIGHTS.csv, results/EXACT_COSTED_MONTHLY_PNL.csv, results/DAILY_COMMON_OPEN_COSTED_NAV.csv, results/ASOF_MONTHLY_STATES.csv.
