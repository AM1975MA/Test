# EU165 — verifiable economic ETF taxonomy and fine-sector predictive ability

**30 October 2026, research-only. No original B0, V2, V3, USA149 or production code changes.**

The research recasts previously frozen source-native European-listed 165 UCITS ticker dataset from 6 broad macro categories into **36 economic groups** based on issuer / index name when verifiable plus explicitly unresolved coarse classifications. Coverage: 41 sectors checked by public issuer/index name, 39 archival metadata, 81 still coarse/unresolved and four sector tickers unverified. Historic index membership/constituent exposures are NOT point-in-time certified, and global US thematic UCITS funds remain included when appropriate.

**Main result, 65 historical monthly Open-to-Open trade intervals per V3 model from 2019–24.** Frozen V3 Pair25/Hybrid24, 5 holdings:
- With six broad macro groups: +0.179pp per interval due to selecting group / +0.459pp from selecting within group, relative to original monthly PIT eligible simple ETF mean.
- With 36 fine groups naively: +0.742pp group / -0.104pp within. **This is biased by singleton groups**, where selecting an ETF equals selecting its group by construction.
- With a preregisterable **anti-singleton diagnostic** (groups with fewer than 2 as-of comparable wrappers folded into their broad category): +0.340pp group / +0.299pp within. Fine-group contribution above original 6 macro +0.160pp per interval, month-block 95% CI [-0.093,+0.435]pp, **NOT statistically conclusive**. Within-group figures are gross before costs, not alpha.
- For V3 Pair127, anti-singleton between +0.356pp, within +0.169pp.
- **62.8%** of V3 Pair25 selected ticker slots have at least one same-group peer in the eligible pool, but this includes still coarse bond, country and factor categories.

**Verified sector leadership forecast**, only groups with ≥2 ETFs and enough comparable eligible groups:
- ≥5 sector groups present: only **30 months** 2019–24, **just ONE month in 2019–20**. V3 Pair25 correct winning-sector hit 33.3% versus MOM252 26.7%, gross group-choice edge +0.802pp vs -0.903pp/interval; paired V3–MOM excess +1.705pp, nominal six-month CI [+0.071,+3.268], **not multiple-test/coverage robust**.
- ≥3 sector groups present sensitivity: **48 months**, only 5 in 2019–20; V3 hit 39.6% vs MOM 35.4% (+4.2pp CI [-8.3,+16.7]); return edge over MOM +1.134pp CI [-0.261,+2.463], **zero included**. Model superiority not established.
- Fine-sector ETF wrapper leave-one-out (exclude chosen ETF from peer benchmark) on 26 covered months: +0.239pp per interval, CI [-0.195,+0.811]; no stable wrapper-alpha confirmation.

**Quality gate**: same two native V3 score arrays and original PIT eligible pool; no fitting or allocation/CAGR optimization; 130 exact additive decompositions, max numerical discrepancy 1.4e-17; all signals before subsequent trade entry; 2025 excluded. Month-level circular 6-month block CIs are exploratory, many prior experiments across 2018–26; no independent untouched holdout.

**Limitations**: 2026-surviving ETFs and retrospective product metadata, some funds/index strategies changed over history; dividends/total-return, FX and actual spreads/quotes not independently audited, trade-window price returns gross not actual NAV contribution, group membership biased by availability, many sector groups have only one eligible ETF. Result should drive *data quality* enhancement, not a new portfolio policy.

Reproducible results ZIP (references frozen earlier EU165 165 OHLCV & original native score files): `ETF_TRADER_EU165_TASSONOMIA_ECONOMICA_LEADERSHIP_20261030.zip`, SHA256 `ad0a397735724f2866a198c9e087dd8f5be5dcc400cd22dac645502e755b4c4f`, 198,769 bytes, 26 files (taxonomy with issuer sources, 4 reproducible scripts, bootstrap scorecards, coverage gates, month-level and wrapper-level tables, plots, Italian report). No production changes.

**Research choice**: complete point-in-time fine-grained country/factor/bond duration and true industry classifications before pursuing a new sector-level learner; preserve V2/V3 as source-native opportunity specialists.
