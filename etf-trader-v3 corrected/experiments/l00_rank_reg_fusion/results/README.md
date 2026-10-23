# V3 Corrected — reproducible L00 ranking/regression decision-tree research

Saved in the real existing V3 project folder. Original V2/V3 execution modules are unchanged.

## Status

- Causal candidate: **NESTED_24_TOP1_GUARD**, exploratory only.
- First-stage: original CORRECTED125 out-of-year ranker.
- Meta: quarterly matured decision tree, monthly 24-month chronological parameter rule, 60-day outcome lag.
- Original 149 ETFs / 500 fixed baskets / 101 matured months.
- No retrospective CAGR selection of meta parameters.
- Functional validation: Actions 40032282233.
- Market-next-open 10bps next-open economic replay: Actions 40032693599.

## Verified matched 2022-02 through 2026-06 aggregate CAGR (baseline -> meta)

| Fixed allocation | Ranker only | Ranker + nested tree |
|---|---:|---:|
| TOP1 100% | 21.21% | 24.62% |
| TOP2 75/25 or 100/0 | 19.82% | 21.45% |
| TOP3 50/30/20 | 17.96% | 18.54% |

**Not independently validated future alpha.** All paired economic alpha confidence intervals contain zero, and the 2018–2026 calendar was already used to develop many settings. The basket aggregate is mean portfolio equity of dependent baskets, not a single investable pooled ETF fund.

## Source and results

- All scripts and protocols reside in the parent directory.
- `tables/`: human-readable summaries, yearly results, confidence intervals, model audit and dated model decisions.
- `archives/`: all **twelve** complete verified experiment artifact bundles; includes original per-ETF OOS signals, 50,500 decisions and daily portfolio NAV series.
- `ARCHIVE_MANIFEST.json`: archive, source run, original filenames, byte counts and individual SHA256 hashes.
- The **frozen original raw OHLCV** remains in Actions run 39482809691 rather than duplicating historical market data.
- Nothing is merged into the original production trading model by this archival task.
