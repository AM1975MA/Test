# L10.E — Post-rank trajectory quality gate (CORRECTION of L10.D interpretation)
**Preregistered before L10.E numeric outcomes; 22 October 2026. Research branch `research-v3-l10e-postrank-trajectory-20261022`.**

## User-intended architecture, different from L10.D1

Preserve **the complete frozen ML rank**, XGB CORRECTED Pairwise127 (125 corrected features, 127 leaves, 360 boosting rounds, three seeds), as first and only general ordinal expert. Analytic mathematics is a **post-selection trajectory auditor**, not a new score for the whole ETF universe, not a separate global ranker and not a replacement of the ML rank. Its task is to flag *selected* trajectories that may have deteriorated and then conditionally replace only flagged positions with the highest original ML-ranked unflagged alternative. Unflagged chosen ETFs and their existing relative positions remain unchanged; weight policy stays Top3 [0.5, 0.3, 0.2]. If no eligible alternative exists, leave original position unchanged and record failure to replace. Top-5 is frozen as an optional candidate generator for later separate experiments, **NOT** silently blended in L10.E1.

L10.D1 (run 39738471945) instead analytically reordered the entire expanded pool; that was not the user's intended mechanism, and its rejected results remain archived for scientific provenance but are **not** evidence against post-rank trajectory auditing.

## One predeclared transparent flag (E1 proof of protocol)

Ex-ante signal date t daily adjusted close history; fixed, deliberately simple conservative initial indicator:

- 21-session trailing log return `momentum21_i,t = log(C_i,t/C_i,t-21)`.
- 63-session rolling-high current drawdown `drawdown63_i,t = C_i,t/max(C_i,t-62,...,C_i,t)-1`.
- **Trajectory deteriorating** when *both* `momentum21 < 0` and `drawdown63 <= -0.10`.
- Compute from close data available on signal date only, i.e. executed *no earlier than next-open*. No labels, outcomes, past cross-sectional re-optimization, RMT or ML addition to this first flag. No alternate thresholds or horizon sweeps in this evaluation.

This rule is not claimed optimal or adequate; it is a **single frozen falsifiable first contrast**, not a production rule.

## Exact functional test design

Fixed 149 original ETF raw adjusted OHLCV run 39482809691; original 500 canonical baskets x24 SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`; 101 fully mature next-open plus 21-session OOS evaluation months; scores from frozen run 39700865721 (`CORRECTED`) and same ticker/date/future targets. Benchmark **B0** unchanged CORRECTED Top3, weights [0.5,0.3,0.2]. Candidate **E1** preserves ordering unless a selected candidate is flagged by the above past-only trajectory rule; scan original CORRECTED ranks 4–24 for first *unflagged, previously unselected* ETF and place it in that original slot (no global analytical re-ranking and no hindsight). If no unflagged alternative, preserve original ETF and log no safe replacement. Multiple flagged selected slots are processed in original slot order. No cash, other head, or allocation weights changed.

Check both **signal skill before portfolio effects** and effect of one flag-policy change:
- 100% or explicit coverage of as-of signal and synthetic prefix invariance;
- conditional *unique ETF-month* severe future21D losses <= -10% and captured-winner false-alarm rates among exactly the initially selected ETF-months (the same ETF repeated in multiple overlapping baskets is unique for skill);
- how much selected weight was flagged/removed and what fraction of genuine future winners was removed (veto harm);
- Top3 true basket winner selection, actual weight on winner, future weighted percentile rank, severe absolute-loss investment weight, weight among bottom-three and weighted 21D oracle regret, all as 101 matched per-calendar-month aggregates;
- count actual substitutions and no-alternative cases, yearly breakdown, trading-target turnover increase estimate (not actual execution costs);
- paired circular 6-calendar-month bootstrap (6000 draws) over monthly *differences*. The 500 overlapping baskets are not independent.

## Acceptance guard

No promotion from risk-weight reduction alone. Demand evidence of positive conditional precision *and* reduced future loss weight, without meaningful loss of winners or rank quality/regret deterioration. If E1 has weak coverage/precision or removes too many winners, reject and archive it. Do not tune the fixed 10% threshold after seeing results from these 2018–2026 heavily reused months; any other flag is a separately preregistered test and needs truly newer independent years before live approval. Evaluate economic consequences only AFTER a candidate passes its specific trajectory-filter predictive/functional gate, at identical L07–L10 next-open 10 bps per traded dollar. Original V2 production and frozen V3 reference remain untouched.
