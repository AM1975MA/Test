# EU165 Native Port V2 vs V3 Pair127 — pilot 2025

**RESEARCH ONLY; no production merge, original B0/USA149/V2/V3 unchanged.**

This branch records an **actual source-derived run** of the original V2 architecture ported to EU165, plus the exact corrected V3 Pair127 model (max_leaves=127, grow_policy=lossguide, 360 rounds, three seeds 101/202/303), integrated with the native Pair25 75%-V2+25%-V3-base design.

- Historical training cutoff 2025-01-01, **one fitted year only**.
- Backtest 2025-02-03 to 2026-02-02, 255 European-market dates, monthly next-open, 10bp one-way.
- EU165, 6 clusters, 500 as-of **STABLE_HASH_MONTHLY** baskets × 24 members (four eligible in each cluster).
- V3 training: 18,433 matured rows, 1,816 2025 predictions. V2 Titanium: 1,816 scores; MA3 panel: 15,075 rows from 101 signal dates.
- Portfolio metric is the **CAGR of the equal-capital aggregate NAV across 500 baskets** (not mean of 500 CAGRs).

| Strategy | CAGR | MaxDD | Sharpe rf=0 |
| --- | ---: | ---: | ---: |
| B0 frozen (indicatively mapped into EU calendar) | 71.08% | -21.10% | 2.351 |
| Passive XMEU | 16.85% | -16.32% | 1.042 |
| Ported source-native V2 Hybrid24 | 13.72% | -17.92% | 0.929 |
| Ported V3 Pair127 25%-base / V2 Hybrid24 downstream | 16.03% | -17.44% | 1.056 |

V3 minus V2 +2.31 pp historical CAGR; **NOT a confirmed independent OOS advantage**. The original V2 equity paths are bitwise-numerically identical when regenerated inside the V3 evaluator (maximum abs difference = 0).

**EU165 adaptations — not a literal US-model replication:** SPY→XMEU.DE, BIL/SHV→LYQ2.DE (EUR 1–3yr government ETF, NOT cash), HYG/IEF spread→EXV1.DE/LYQ2.DE (NOT US high-yield credit), point-in-time stable-hash dynamic baskets instead of fixed 500 baskets; no prelisting backfill. All model settings are original, but economic market-reference changes make this a new research version.

Only 2025 fitted; no 2018–2026 native integral result yet. Historical 2026 survivor cohort, uncertain total-return/distribution methodology, spreads and delistings; ten missing original B0 dates are carried forward to EU calendar for descriptive comparison. V2/V3 entered **zero** new positions at dates with missing raw Open. About 1.1% selected position/day observations use prior-day quoted prices for missing venue days. The 500 overlapping baskets are not independent statistical samples.

Full code, model inputs, as-of baskets, original GitHub source archive, fixed source adapters, score outputs and 500 NAV paths are in conversation artifact `EU165_V2_V3_NATIVE_PAIR127_PILOT_20261029.zip`, SHA256 `78c09a406203646aa681a9ed472840e29b16dd1708aa86184c41a5a710cfe383`. This GitHub branch contains methodology and provenance only, **not** the 36MB archive.

**Next valid gate:** 2018–2026 expanding annual fits on EU165 with exact same sources, validated UCITS cash and credit proxies, dividend/total-return certification, and subsequent untouched post-2026 temporal evaluation. Never promote based on the tested 2025 data.
