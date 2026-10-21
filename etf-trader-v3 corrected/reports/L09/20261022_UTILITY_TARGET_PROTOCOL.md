# V3 L09 — 21-trading-day forward utility alignment (preregistered experiment)

**Date 22 October 2026.** Research branch `research-v3-l09-21d-utility-target-20261022`. **The evaluation period 2018–2026 has been extensively examined, so all resulting tests are exploratory and not virgin out-of-time confirmation.** Original source-only V2 remains untouched. No layer promotion until fully audited.

## Question isolated after completed L08
Is the economic deficit of Tail-based Top3 driven by training for rare extreme-ETF winner capture rather than selecting assets with high *expected next holding-period utility*?

Change *only the training objective/label*, keep:
- 149 original ETFs, 500 original 24-ETF baskets (membership SHA256 `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`), corrected 125 Compact features and missingness rules unchanged.
- Historical 2012+ annual expanding train and 2018–2026 genuinely out-of-year test, only training signals whose next-open to +21-trading-day return has matured before Jan1 refit cutoff.
- XGBoost same fixed 127 leaves, 360 rounds, three seeds [101,202,303], base reg_lambda 8, same tree feature preprocessing. Use reg:squarederror for both new regression heads. Both labels computed from adjusted next-open 21D ETF return. No learned risk gating, blending, tail model retuning or volatility allocation.
- Existing original historical LEGACY ranker and corrected 125-feature PAIR127 scores remain independently frozen reference streams.

## Exactly two predeclared, not grid-searched labels

Let `r_it` denote the full mature next-open to 21 trading-session ahead ETF return and `l_it = log(1+max(r_it,-.95))`; `m_t` is the median `l_it` cross-universe on the training month (never observed at inference).

1. `L09_EXCESS21`: 100 × `clip(l_it - m_t, -.25,.25)`. Predicts 21D forward relative log return, with robust tail clipping.
2. `L09_DOWNSIDE21`: 100 × [`clip(l_it-m_t,-.25,.25) - .5 × clip(log(.90)-l_it,0,.20)`]. Adds an asymmetric penalty only when the realized absolute next21D return is **worse than -10%**. Coefficient .5 and all clips fixed ex ante.

These targets include future information **only as matured training labels** and retrospective evaluation outcomes. Test-year features contain no future returns. Cross-sectional median of the future training returns is **never an input feature**.

## Gate metrics
Primary: paired original 500 baskets future 21D weighted selected-rank quality and oracle regret; secondary: winner Top1/Top3 and basket nDCG@3; monthly rank IC. Handle overlapping baskets by aggregating to month before 6-month block resampling (and compare two new arms under multiple-hypothesis correction).

Only when numerical predictions are frozen: compare same next-open executable portfolios at **10bps per traded dollar**: LEGACY and CORRECTED PAIR127 vs each new L09 score, each held to two **predefined** strategies: original Top2 rule (75/25 unless first-second cross-universe percentile gap>=.12), and Top3 weights [50/30/20]. Use same cost/execution engine as L07/L08, daily mark-to-adjusted-open, same original 500 baskets, same calendar dates; compare annual contributions, CAGR, Sharpe, MaxDD and true turnover only as consequences — never search objective coefficient/policy by CAGR.

## Decision discipline
- Treat claims of better selected-rank skill and lower realized regret separately from portfolio profit or single-year gains.
- At most record L09 a *candidate* if robust out-of-year skill improves against original corrected PAIR127 under identical controls; no production promotion without independent new vintage.
- Do not represent historical LEGACY ranker + Top2 as the entire V2 production layer chain.
- All run IDs, source revisions and artifacts must be added to the central registry, including failed or superseded test runs.
