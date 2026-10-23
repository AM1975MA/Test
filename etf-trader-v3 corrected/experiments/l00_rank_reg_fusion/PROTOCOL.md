# ETF Trader V3 — L00/L01 ranking, volatility and complementary regression trial

Research protocol frozen before any new outcome, 2026-10-23. This branch is independent of original V2 production and frozen V3 source. All 2018–2026 years were heavily researched previously: results are **exploratory, not pristine generalization proof**.

## Immutable reference
- Exact 149 OHLCV snapshot from GitHub Actions 39482809691, original 500 baskets x 24 ETF, SHA `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e`.
- CORRECTED125 source and independent annual OOS scores, run 39515716383.
- Same eligibility from original 125 features >=30 finite fields; same 21-trading-day next-open outcome; no non-matured labels at annual cutoff; expanding annual 2018..2026 fits, 360 trees, 127 leaves, seeds 101/202/303. All date/ticker labels and basket members must exactly match oracle, or run fails.
- No model changes downstream to execution, Top2 policy, Tail, weights, stops, risk, V2 Hybrid24, production.

## Frozen arms

| Arm | Features | Hypothesis |
|---|---|---|
| CORRECTED | 125 | original control, no retraining |
| CS_ADD250_MINMAX | original 125 + all 125 same-day minmax | preserve absolute features while also supplying complete cross-sectional views |
| CS_ADD250_ROBUST | original 125 + 125 same-day median/MAD standardized clipped channels | robust additional relative channels, no future dates |
| VOL_TREND_RESID | original 125 + 3 RMS log-price residuals from rolling OLS time trend 21/63/126 | residual fluctuation around evolving historical price trend |
| VOL_MARKET_RESID | original 125 + 3 annualized OLS SPY-return residual volatilities 21/63/126 | market-neutral fluctuation independent of systematic daily factor |
| REG_REL125 | original 125 | reproduction of prior L09 median-centered relative clipped log 21D return target |
| REG_REL101 | original 125 minus 24 vol/downvol/vol_ratio/GK channel features | direct test of removing volatility information from relative return regression |
| REG_ABS125 | original 125 | clipped *absolute* next-open 21D log return |
| REG_ABS101 | same 101 | absolute return without volatility channels |
| REG_HUBER125 | original 125 | pseudo-Huber relative return training loss for outlier robustness |

Every model is separately refit. CS_ADD250 variants do not replace the 125 originals. Regression is not simply substituted for ranking: after frozen out-of-year scores are generated, each basket is tested with separate postranking transformations:

- F1_TOP5_REL125: original top5 within basket, reorder ONLY these candidates by expected relative return, remaining candidates retain their base order;
- F2_GATE_REL125: replace the base first candidate with relative-regression best within the original top5 only if the original candidate's regression score is below the median of that top5;
- F3_BLEND_REL125: fixed 75% of same-date global percentile ranker score + 25% percentile regression relative score;
- F3_BLEND_REL101: same with volatility-free relative regression;
- F3_BLEND_ABS125: same with absolute regression;
- F4_CAUSAL_BLEND_REL125: blend rank weight in [0,.25,.5,.75,1] chosen using last 36 strictly earlier OOS monthly selected-excess outcomes, with >=60 calendar day maturity lag and >=24 prior OOS months; until available, fixed 0.75.

## Evaluation gates
Primary metrics basket future winner Top3, Top1, rank nDCG3 and regret; secondary selected forward excess and universe rank IC for direct models. Record how often fusion substitutions correct or worsen original Top1 choices, instead of reporting standalone CAGR. All 500 overlapping baskets are aggregated within each calendar month before any six-month circular-block paired bootstrap; all compared arms have exactly matched calendar/ETF/label membership. Report year-by-year differences. Inference on reused research history is exploratory and multiplicity is not controlled to confirm a winner.

If a fused score improves the model selection skill and uncertainty is not adverse, the next study may hold ranking constant and evaluate **next-open executable** Top2/Top3 with costs and drawdown, never mix into this feature-stage causal attribution. Reject a change when its observed Top3 increases but nDCG, regret, or realized selected quality become materially worse. No production promotion without genuinely unexamined validation.

Workflow: `.github/workflows/v3-l00-rank-reg-fusion.yml`; analysis: `experiments/l00_rank_reg_fusion/evaluate.py`; aggregation `aggregate.py`. Results from the workflow artifacts are not present until the run completes.
