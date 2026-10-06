# Hybrid24 top-tail diagnostic — 2026-10-02

## Provenance

Canonical Hybrid24 source is unchanged. Source gate passed against the productive ETF_trader V2 blobs before analysis.

Primary diagnostic Action:
- run: `37035270407`
- artifact: `11240321050`
- artifact SHA256: `deb4127a221ed5c8ef62f27508e01b4f50ada3256bae54940b4edaf5af7e590a`
- raw vintage: the same frozen fresh Yahoo/yfinance vintage already used for the controlled 149-vs-70 comparison
- no historical score/path consumed

The Holdout70 is already burned and is used here only for diagnosis. No result in this document is a prospective validation of a new strategy.

## Canonical Hybrid24 top-tail diagnostic

### Original149 fresh

- 114 complete 21-day signal periods
- mean Spearman IC(score, forward 21d return): `+0.06900`
- median IC: `+0.08414`
- positive-IC periods: `59.65%`
- predicted top1 realized rank: mean `71.14 / 149`, median `55`
- actual best ETF predicted rank: mean `32.30`, median `23`
- actual 21d winner inside predicted top5: `19.30%` (random baseline `3.36%`)
- actual 21d winner inside predicted top10: `28.07%` (random baseline `6.71%`)
- P(predicted top1 beats predicted top2): `49.12%`
- Spearman correlation between score margin (top1-top2) and subsequent return difference (R1-R2): `+0.13062`
- top1 21d compounded monthly CAGR proxy: `15.66%`
- top2 proxy: `33.87%`
- equal top1/top2 proxy: `26.38%`
- current fixed margin-weighted proxy: `24.35%`

### Holdout70 fresh

- 114 complete 21-day signal periods
- mean Spearman IC: `+0.08357`
- median IC: `+0.08979`
- positive-IC periods: `62.28%`
- predicted top1 realized rank: mean `32.46 / 70`, median `29.5`
- actual best ETF predicted rank: mean `24.11`, median `18`
- actual winner inside predicted top5: `17.54%` (random baseline `7.14%`)
- actual winner inside predicted top10: `32.46%` (random baseline `14.29%`)
- P(predicted top1 beats predicted top2): `50.88%`
- Spearman margin vs subsequent R1-R2: `+0.01589`
- top1 21d compounded monthly CAGR proxy: `19.17%`
- top2 proxy: `8.46%`
- equal top1/top2 proxy: `14.52%`
- current margin-weighted proxy: `15.80%`

## Causal walk-forward top1-vs-top2 meta diagnostic

A small regularized logistic model was trained only with labels whose 21-day exit date was already mature before each current signal. Inputs were current observable score/margin/component-difference features. This is a diagnostic, not a promoted strategy.

### Original149 self walk-forward
- n = 89
- accuracy: `51.69%`
- probability vs subsequent R1-R2 Spearman: `+0.0393`
- hard router proxy: `28.42%`
- soft probability mix proxy: `29.26%`
- equal mix on same window: `29.40%`

No meaningful improvement versus equal mixing.

### Holdout70 self walk-forward (burned diagnostic)
- n = 89
- accuracy: `52.81%`
- probability vs R1-R2 Spearman: `+0.1052`
- hard router proxy: `20.97%`
- top1 on same window: `22.22%`

No improvement versus top1.

### Train on Original149, apply to Holdout70

No Holdout70 outcome was consumed by the fitted model in this lane, although the diagnostic feature set itself was designed after Holdout70 had already been inspected, so this is not a pristine holdout validation.

- n = 89
- accuracy: `60.67%`
- probability vs R1-R2 Spearman: `+0.1084`
- hard router proxy: `24.92%`
- soft mix proxy: `20.98%`
- top1 same window: `22.22%`
- top2: `13.91%`
- equal mix: `18.96%`

This is evidence that some transferable information about top1-vs-top2 choice may exist, but it is not sufficient for promotion.

## Additional exploratory decomposition from the same frozen checkpoints

The following figures were computed after the Action from the exact saved prediction panels and are explicitly **ex-post diagnostics**.

### Effect of the 40/30/30 tail smoothing

Holdout70:
- unsmoothed final BASE+TAIL score top1 proxy: about `24.09%`
- canonical smoothed final score: `19.17%`
- mean IC rises from about `0.0734` to `0.0836`

Thus on Holdout70 the smoothing improves broad cross-sectional IC while worsening the economic extreme that is actually traded.

Original149:
- unsmoothed TAIL_HYBRID alone: about `24.31%`
- smoothed tail alone: about `13.80%`
- however final unsmoothed BASE+TAIL score: only about `7.90%`
- final canonical smoothed score: `15.66%`

The interaction of BASE and TAIL therefore changes materially by universe. A single fixed smoothing/blend rule is not universe-invariant.

### Component complementarity

On Holdout70, BASE has relatively high recall of the actual winner in its predicted top5 (~27%), whereas ET is a stronger top candidate scorer than its broad IC alone suggests. Ex-post two-stage filter/rerank tests can materially outperform the canonical linear blend, but the best rules differ sharply between Original149 and Holdout70. They must not be treated as validated strategies.

A fixed rule `SCORE top5 -> choose max BASE` improves the full-period top1 proxy in both universes, but fails subperiod robustness on Original149 (strong 2017-2022, weak 2023-2026). This is evidence for component complementarity, not evidence for promotion of that rule.

### Learning-to-rank exploratory probe

A walk-forward XGBoost `rank:ndcg` top-tail objective was tested only as a diagnostic. It strongly improves **retrieval** of the true winner into a shortlist but does not order the shortlist well enough to use its top1 directly.

Holdout70 diagnostic:
- canonical score: actual winner in predicted top5 `17.5%`
- LTR shortlist: actual winner in top5 about `44.7%`
- LTR top1 itself: poor (~10% CAGR proxy)

Original149 diagnostic:
- canonical: actual winner in top5 `19.3%`
- LTR: actual winner in top5 about `32.5%`
- LTR top1 itself: poor

This supports a two-stage architecture: high-recall candidate retrieval followed by a separate causal reranker, rather than a single global score.

## Main diagnosis

The evidence points to an objective/decision mismatch:

1. Hybrid24 has genuine broad cross-sectional signal (positive IC in both universes).
2. The strategy monetizes only the extreme top1/top2 tail, where the ordering is much less reliable.
3. The current top1-top2 margin is not a calibrated confidence measure, especially on Holdout70.
4. Smoothing and linear BASE/TAIL blending can raise global ranking quality while destroying top-tail quality.
5. Static blend/smoothing/sizing choices are materially universe-dependent.
6. A simple ML router on the existing top1/top2 meta-features is not enough.
7. Learning-to-rank appears more useful as a high-recall shortlist generator than as the final selector.

## Next controlled experiment

Do not optimize another static blend on Holdout70. It is burned.

The next challenger should be preregistered as a causal two-stage producer:

1. **Retriever:** annual/expanding maturity-safe Learning-to-Rank optimized explicitly for top-k retrieval (e.g. NDCG@5/10), producing an OOS shortlist.
2. **Reranker:** trained only on earlier matured OOS shortlist predictions, using pairwise candidate comparisons; no in-sample producer predictions.
3. **Sizer:** only after reranking, estimate top1-vs-top2 relative skill/probability from OOS history; do not use raw score margin as confidence without calibration.
4. **Universe normalization:** separately test a stable reference universe for cross-sectional ranks/clusters, decoupled from the investable candidate universe.
5. **Validation:** freeze a new disjoint Holdout-B before any performance is inspected. Holdout70 may be used for diagnosis but not final promotion.
