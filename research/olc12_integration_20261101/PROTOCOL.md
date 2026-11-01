# OLC-12 — classifier integration without confusing native skill and portfolio growth

1 November 2026. User authorizes continued integration of OLC11's XGB upper-quintile classifier into the entire strategy. All tests paired USA149/EU165. No main changes or live orders. This protocol precedes new candidate metrics and portfolio outcomes.

## Frozen sources
OLC11 branch tip 9180a6d7b0ffefbdac351d0a30d5eb688ecae476. OLC11 complete checkpoint SHA256 6802adb5ee54db9142c49b1ea13511c354b200ee84e3cdf3cae8bbd491275eeb; OLC10 checkpoint 33b454c843421a8154818c746966ff371226ca7722004b555ac9abe4b0e05783; OLC06 checkpoint 7e3a23176e27813b324a4fed275965b6644b4dd97ae8f33a31061c0b518319aa. Verify parent manifests before consuming serialized data. This lot reuses authentic annual out-of-time forecasts; zero new base learner fits planned.

OLC11 regressors/classifiers use the same full-mature-group training rows. Matched mean-of-three-seed regressors are the PRIMARY integration comparator; archived seed101/old training is a distinct historical control. Return125 RSI-corrected remains frozen. Its original cross-sectional-label maturity is not newly certified; OLC11's maturity correction covers Hybrid only. No fresh market-data download.

## Questions and layer gates
1. Does the classifier retain native Top2 skill through a monotone mapping? 2. Is the loss caused by mixing with ET, by temporal averaging, or by final fusion? 3. Can a separate specialist channel or a predeclared shortlist reranking improve the selected ideas? 4. Does that result survive persistent holdings, risk, costs and execution?

Primary direct diagnostics: NDCG@2, target top-quintile precision, bottom-quintile errors, target regret; static Top2 excess payoff21/42/63 on common eligible support and complete outcomes. No CAGR-based choice of model weights. Probability, percentile and expected target are explicitly separate fields. A classifier's probability is of a relative target-quintile event, not of positive monetary return. No probability-to-position/Kelly mapping.

## Prespecified candidate set
Let r=Return percentile, e=ET_REG percentile, x=XGB_REG percentile, c=XGB_CLASS percentile, p=the classifier probability. Mean raw predictions across seeds101/211/307 before percentile transformation. S(a) is the original causal weighted lag(.4,.3,.3), renormalized only over available past observations, masked when current is missing; P(a)=clip(a,0,1)^1.1. All transformations use only their own signal date and past.

MATCHED_REG = .475r+.525P(S(.6e+.4x)); NAIVE_CLASS = .475r+.525P(S(.6e+.4c)); MIX_CLASS_CURRENT removes only that temporal average. SOLO_CLASS_CURRENT = .475r+.525P(c); SOLO_CLASS_MEMORY = .475r+.525P(S(c)). Paired controls SOLO_REG_CURRENT and SOLO_REG_MEMORY use x instead of c. CLASS_NATIVE = p, direct specialist-only diagnostic.

PROB_MEMORY = .475r+.525P(rank_same_date(S(p))); contrasts smoothing probabilities before ranking against smoothing ranks. No direct summation of probability with a differently scaled score.

SPECIALIST20_CURRENT = .8 MATCHED_REG+.2c. SPECIALIST20_MEMORY = .8 MATCHED_REG+.2P(S(c)). The 20% is a fixed research intervention, not a calibrated optimal weight. Regressors remain separate native outputs.

RERANK5 = choose top2 classifier probabilities among top5 MATCHED_REG, using observed score/ticker deterministic ties only. Candidate pool boundary includes all tied scores, so eligibility is not ticker-name dependent. It cannot buy outside the parent shortlist and has no learned veto/cash alternative. Size5 is fixed, not optimized. Forecast/label-missing future rows remain live candidates.

ARCHIVE_S101 retains the original RSI-corrected single-seed archived composition as an additional historical anchor. No in-sample optimum is silently renamed the baseline.

## Whole strategy
Primary candidates above: HALF target; policies IMMEDIATE, DELAY3, PHASE5; legacy fee .001/.003; both markets. Same observed execution quotes and fixed daily risk/V6 streams as OLC06. Candidate-specific scored names change only d1,d2 and selected weights; preserve ticker/calendar alignment and holding state, no spliced curves. Known same-Open risk knowledge/fill assumptions remain: not certified live executability. V6 targets remain frozen to isolate the main selector; this can interact with changed selections and is disclosed.

Run original OLC06 q targets as12 immutable engine controls before changing names. Reproduce archived OLC11 layer outputs exactly for MATCHED_REG and NAIVE_CLASS. Recompute all economic summaries on actual next-Open valuation dates, exclude final flat row. Primary2021-2024; fullFeb2019-July1 2026;2020crash;late2021-2023;2025;2026partial separately. Strategy entries exist regardless of availability of future evaluation labels. No forward-filled quote is treated as an executable quote.

For the five fixed structures MATCHED_REG,NAIVE_CLASS,SOLO_CLASS_CURRENT,SPECIALIST20_CURRENT,RERANK5 additionally compare one-session-lag gap/breadth inputs at IMMEDIATE and both fees/markets. This is a conservative sensitivity, not a full live execution model and not selected after returns.

## Uncertainty and decision
For pre2025 native metrics use fully mature groups; pair USA/EU by month, maintain missing-month grid. For portfolios use net monthly log differences. Circular paired bootstrap blocks3/6,6000 draws,seed20261101; same resampled calendar blocks in both markets. Keep all candidates and family-sensitivity intervals; no CI-zero automatic veto and no bootstrap fraction called posterior probability. Reused history is not virgin validation. No choosing different candidate per market. A better native component can remain a specialist even when a fusion fails. No new parameters will be chosen from this lot's CAGR.

## Tests and persistence
Failing-before-passing tests: scale separation, original smoothing parity, current-missing handling, no cross-date ranks, future-prefix invariance, shortlist containment/ties, observed execution eligibility, exact baseline NAV and ledger identity. Independently reconstruct NAV from units/cash/next Open, re-evaluate metrics, and check label-based metrics independently. Persist source/input manifest and integrated scores before portfolio replay; persist all outcomes and failures after. Save complete new sources and compact results to this research branch; binaries to verified persistent storage with honest location. No assumption of background local jobs. Self-review, not an independent reviewer.
