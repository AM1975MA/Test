# Compact21 robust deviation (_dev) missingness: complete diagnosis — 2026-10-10

## Exact reproducible source checks
- Run [38093280854](https://github.com/AM1975MA/Test/actions/runs/38093280854) SUCCESS: all 33 cross-sectional robust `_dev` features in each of three independently downvol-cleaned original Original149 panels; matched canonical missing masks exactly. Each source: 14916 missing `_dev` feature cells **within currently 30-of-125 eligible rows**, of which **13155** coincide with missing raw/base input feature, **1761** have available base feature but zero cross-sectional median absolute deviation (MAD), **0** missing-MAD other than zero, **0** unexplained. Identical counts across 3 source snapshots.
- `drawdown21_dev`: 1411 missing, **all** because MAD=0, across 10 signal dates. `drawdown126_dev`: 844 missing, of which 734 source feature missing and 110 because MAD=0 (1 signal date).
- Run [38093343608](https://github.com/AM1975MA/Test/actions/runs/38093343608) SUCCESS: independently classified the zero-MAD observations **1761** into **1029** with base input exactly equal to cross-sectional median, and **732** with base input distinct from median. These counts exactly match in all three acquisitions.
- For a zero-MAD cross-section, setting every standardized deviation to zero is NOT meaning-preserving: 732 off-median cells encode actual difference from the median despite MAD zero. Distinguish ties-at-median from outliers. No universal `fillna(0)`, mean/median replacement or artificial history.
- Counts refer to 33 `_dev` columns and may have dependencies/repeated ticker-date instances; **not** a claim of independent defects in 1761 unique ticker-dates. Data original and other pipeline components unchanged, no training, no new CAGR.

## Approved interpretation, not yet production correction
For source-missing base features, preserve availability mask until sufficient actual historical data, as diagnosed in prior raw-window run [38083480515](https://github.com/AM1975MA/Test/actions/runs/38083480515). For zero MAD, current formula (value minus median)/(1.4826*MAD) is mathematically undefined. An alternate robust scale (e.g. nonzero IQR or a well-specified fallback standard deviation) is a **new definition**, not an innocuous missing-value correction; must independently verify informativeness, causality, stability, and per-date behavior before implementation. A simpler deterministic option is to mark specific cross-sections unavailable and exclude affected rows via complete-case gate, with quantified coverage and survivorship impacts. Neither change has been approved or tested yet.

## Next strict data-only gate
1. Quantify per date/feature zero MAD and fallback IQR, standard deviation and fraction of ties, across three source snapshots; verify whether fallback is nonzero and stable under tiny Yahoo data revisions, without training models.
2. Implement and test an explicit `_dev` policy with no undefined output on otherwise valid input (or explicit ineligibility), preserving an audit reason for every difference.
3. Recompute all input-column completeness and denominator-aware numerical invariance, including original 30/125 vs 125/125 admission impact. Only then resume frozen three-repeat V2 learning and portfolio replay.

No changes to Etf_trader production.
