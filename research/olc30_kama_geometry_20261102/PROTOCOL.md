# OLC30 – KAMA geometry inside a chronological ranker (frozen protocol)
Date 2026-11-02. Exploratory historical research following OLC29. Parent OLC29 commit 5054f5aaa9b91e697778b8484cdb2e6f9c2acfc4, anchor AUTH OLC20 and exact OLC19 risk/V6 accounting. No change to main or live trading. Past 2019–2026 data have been repeatedly researched; NOT independent validation.

## User's hypothesis
KAMA should be a ranker *feature*, not a buy/sell crossover and not an externally imposed switch rule. Integrate the SIGNED price-vs-KAMA area and its slope/distance dynamics to characterize persistent/overextended leadership. The best historical ETF (EU QDVE.DE, USA ARGT 2021–24 and SMH full) must remain a pure retrospective diagnostic; never used to design coefficients or rules.

## Fixed causal features (KAMA only)
KAMA(ER10, fast2, slow30) calculated on contiguous strictly observed positive Close histories, as in OLC29 (EU original observed mask, USA finite-positive prepared quotes; missing USA original mask is a material limit).
All features available by signal Close, no entry Open or later prices:
- AREA21 = mean(log(C[t-j]/KAMA[t-j]), j=0..20), a signed 21-session discrete price/KAMA integral; requires all 21 ratios finite.
- SLOPE21 = (log(KAMA[t]) - log(KAMA[t-21]))/21, signed per-session KAMA slope; requires both finite.
- GAP_SPEED5 = (log(C[t]/KAMA[t]) - log(C[t-5]/KAMA[t-5]))/5; price's divergence from KAMA expanding/shrinking.
No binary cross or trend veto, EMA/Hull or additional indicators. No lookahead or missing repair.

## Ranker
ANNual cutoff 1 January 2021..2026, expanding training. Label is percentile rank in [0,1] of realized **next entry Open to next entry Open** return within each monthly market universe, only across tickers with both entry prices genuinely observed EU or finite positive USA. Label maturity is the actual next execution Open; every training row requires maturity STRICTLY earlier than cutoff. The label is never an inference feature or used to exclude an inference ETF.

Four frozen ridge recipes, one alpha=10.0, StandardScaler fitted on historical training, pooled EU/USA with 50/50 market balance and equal month weighting:
- FUSION_ONLY: AUTH FUSION baseline.
- FUSION_AREA: FUSION, AREA21.
- FUSION_SLOPE: FUSION, SLOPE21.
- FUSION_GEOMETRY: FUSION, AREA21, SLOPE21, GAP_SPEED5.
Training cohort must have complete FUSION and all three KAMA features for ALL four recipes (identical support); fallback to unchanged AUTH if no established eligible training history or missing inference feature.

For every inference month, each ranker's predicted percentile is itself transformed to cross-sectional ranks among valid ETFs. Output fused score = 0.80 * canonical AUTH FUSION + 0.20 * predicted percentile. Missing KAMA feature: use AUTH value unchanged; keep all candidate tickers. Same 0.80/0.20 for both markets/years. No retrospective optimizer, ticker-specific rule or model/alpha tuning.

## Primary (not merely CAGR)
- Matched benchmark gap (daily cumulative log NAV strategy minus fixed ex-post best ETF NAV) 2021–2024 and full, both markets; gap may improve while absolute CAGR does not, and is not ex-ante alpha.
- First entry, months selected and actual average nominal & realized exposure to best hindsight ticker (QDVE.DE/ARGT/SMH), plus missed positive benchmark months and false positive selection months.
- Top2 future126 top-decile hit rate (same opportunity cohort for AUTH and candidate), not conditioned on future availability during selection.
- Next-month gross Open-to-Open rank/Top2 opportunity capture, and change attribution vs frozen AUTH.

Secondary economic/risk guards: FULL OLC19 ALARM / FAST_LOCK3 replay with candidate-specific V6 and costs legacy .001/.003, yearly breakdowns 2020/crash, MaxDD, turnover and bootstrap descriptive uncertainty. Exact 8 AUTH parent account arrays required before acceptance. A result improving ONLY hindsight benchmark selection cannot justify strategy promotion.

## Validation
- no feature derived from quotes later than signal, missingness preserved;
- true cutoff after maturity, no split/random training or feature leakage;
- numerically identical AUTH accounts and independent saved NAV reconstruction;
- both candidate and control trained on identical rows;
- distinguish area and slope ablations from full geometry;
- full source, metrics and adverse outcomes persisted. No new model promotion or claim of prospective validation.
