# L08 — Causal ranker-score versus selection-policy decomposition

**Completed: 22 October 2026. Status: EXPLORATORY RESEARCH DIAGNOSTIC, NO PRODUCTION CHANGE.**

[Successful GitHub Actions 39685852459](https://github.com/AM1975MA/Test/actions/runs/39685852459); original numeric artifacts **12386252130**, `v3-l08-frozen-expert-policy-factorial-results`. Initial workflow 39685692589 failed from an omitted Python argument and was superseded with no model/policy changes.

## Hypothesis and predeclared design

The previous L07 V3 Tail45 Top3 replay underperformed historical source-only LEGACY Top2. Test independently whether this arises from **forecast channel** (which ETFs are scored highly) or from **allocation/sparsity** (Top1 vs old Top2 vs Top3 weights).

Four entirely frozen input score channels, no model refitting:
- `LEGACY`: original source-only V2 Ranker OOS from [run 39515716383](https://github.com/AM1975MA/Test/actions/runs/39515716383);
- `PAIR127`: corrected125 feature, 127-leaf/360-round pairwise ranker OOS from [run 39652989033](https://github.com/AM1975MA/Test/actions/runs/39652989033);
- `TAIL45`: 45-feature upper-elite Tail logistic OOS from [run 39655513813](https://github.com/AM1975MA/Test/actions/runs/39655513813);
- `RRF10`: preregistered combined reciprocal ranks `1/(10+rank_PAIR127)+1/(10+rank_TAIL45)`, no new trained model.

For each score channel cross with **three fixed** policies: `TOP1` (100%), `TOP2` original V2-like (75/25 unless normalized cross-universe score gap >=0.12, then 100% Top1), and `TOP3` (50/30/20). **12 arms, no ex-post weight fitting**. This is a complete factorial, not a hyperparameter search.

Same 149 ETF original OHLCV, original 500 baskets × 24 ETF, identical 102 score dates, identical mature next-21D targets; 101 months evaluable for intrinsic selection (one final score month is forward-immature). **Next market session adjusted Open execution**, monthly close signal available at order time, actual held quantities and NAV price drift, one-way 10bps fee on actual traded dollars. Same reference independent V2 source-only replay matching daily NAV and turnover to **absolute 1e−10** for both calendar windows.

## Functionality: 101 months, future-winner recall versus actual quality of invested assets

All numbers below use identical `TOP3 50/30/20` to isolate predictive channel:

| Expert | Future winner in Top3 | Weighted realized 21D rank quality (0 worst,1 best) | Ex-post weighted 21D regret |
|---|---:|---:|---:|
| LEGACY source-only ranker | 35.7446% | **0.529142** | **0.104820** |
| Corrected PAIR127 | 35.4713% | 0.524852 | 0.105470 |
| RRF10 two-score fusion | 42.5604% | 0.521655 | 0.105716 |
| TAIL45 elite classifier | **42.7465%** | 0.512941 | 0.107137 |

**Crucial finding:** higher probability of catching ONE basket's actual best ETF in the selected three is not evidence of better *average weighted invested ETF quality*. LEGACY has lower best-ETF recall but superior mean realized rank quality and lower regret.

## Historical, execution-fee-aware economics, same full 500 basket universe

Fee 10 bps per actually traded notional; each ETF/rank signal generated OOS before its following open. **Aggregate CAGR is equal-initial-capital basket capital, not median/mean individual basket CAGR.**

| Score and portfolio policy | CAGR aggregate, 2022–2026 matched | CAGR aggregate, 2018–2026 long | Aggregate MaxDD, matched | Mean Sharpe, matched |
|---|---:|---:|---:|---:|
| LEGACY TOP1 | **25.22%** | **17.02%** | −18.00% | 0.663 |
| LEGACY TOP2 original | 23.16% | 15.94% | −17.83% | **0.718** |
| LEGACY TOP3 | 20.02% | 14.11% | −17.99% | **0.745** |
| PAIR127 TOP1 | 21.03% | 14.84% | −18.65% | 0.580 |
| PAIR127 TOP2 original policy | 19.63% | 14.73% | −19.17% | 0.629 |
| PAIR127 TOP3 | 17.78% | 13.88% | −19.46% | 0.679 |
| RRF10 TOP2 | 16.87% | 14.25% | −20.67% | 0.549 |
| RRF10 TOP3 | 16.77% | 13.64% | **−16.17%** | 0.635 |
| TAIL45 TOP2 original policy | 12.68% | 11.06% | −28.92% | 0.444 |
| TAIL45 TOP3 | 13.86% | 11.56% | −22.87% | 0.549 |

Even **under the identical original V2 Top2 policy**, changing LEGACY score to TAIL45 changes matched aggregate CAGR 23.16%→12.68%. Model scoring is therefore a major explanatory factor, not simply changing Top2 to Top3. Switching Tail-only Top2→Top3 slightly improves its economics 12.68→13.86%, whereas LEGACY Top2→Top3 reduces CAGR 23.16→20.02%. **Portfolio concentration policy interacts with the score/model**.

LEGACY Top1 has higher historical aggregate CAGR in both windows (25.22%,17.02%), but lower *mean individual basket* Sharpe than Top2 in the recent window (0.663 vs 0.718). LEGACY Top3 has even higher mean basket Sharpe (0.745) but lower aggregate CAGR (20.02%). A simple declaration that Top1 is best would wrongly optimize retrospectively on examined years and suppress risk-preference trade-offs.

RRF10 Top3 has a more favorable recent aggregate max drawdown than Tail Top3 (−16.17% vs −22.87%), with intermediate CAGR. None proves superiority versus frozen LEGACY under independent future data.

## Dependent-sample uncertainty

Calendar time, **not basket count**, is the unit for paired uncertainty. Average the 500 overlapping basket daily log return differences first; circular bootstrap of 21 **trading-date** blocks, 1500 replicates. All intervals below are exploratory as 2018–2026 were used repeatedly by our research process.

| Recent matched 2022–26 contrast (annualized log return) | Delta | 95% block interval |
|---|---:|---|
| PAIR127 Top2 − LEGACY Top2 | −0.0300 | [−0.0646,+0.0016] |
| PAIR127 Top3 − PAIR127 Top2 | +0.0008 | [−0.0266,+0.0297] |
| TAIL45 Top2 − LEGACY Top2 | −0.0897 | [−0.2115,+0.0193] |
| TAIL45 Top3 − TAIL45 Top2 | +0.0272 | [−0.0077,+0.0604] |
| PAIR127 Top3 − TAIL45 Top3 | +0.0333 | [−0.0481,+0.1233] |
| RRF10 Top3 − TAIL45 Top3 | +0.0247 | [−0.0165,+0.0660] |

No one contrast supplies adequate independent evidence to promote a tuned policy. These are *log-alpha* differences, NOT the pointwise percentage-point difference of annual CAGR.

## Yearly diagnostic, matched period aggregate NAV returns

| Year | LEGACY Top2 | PAIR127 Top3 | RRF10 Top3 | TAIL45 Top3 |
|---|---:|---:|---:|---:|
| 2022 (from February) | +11.42% | +4.10% | +2.26% | −3.88% |
| 2023 | +5.39% | +9.37% | +4.87% | +2.15% |
| 2024 | +21.34% | +15.34% | +12.46% | +6.24% |
| 2025 | +51.60% | +39.11% | +52.24% | **+56.85%** |
| 2026 (partial through July 1) | +15.50% | +12.25% | +7.53% | +8.02% |

Tail specializes in payoff tails and excels in 2025 but lags in several other realized regimes. That pattern is consistent with an objective mismatch, NOT proof of a workable ex-ante regime gate (prior L03 and causal RMT gate explicitly failed).

## Decision and work forward

**No L08 arm promoted.** Keep production V2 unchanged and V3 research stack frozen. The fixed factorial identifies **upper-winner event classification vs full-capital portfolio utility mismatch** as a priority failure mode. Reject using Top3 extreme winner recall alone as the objective for any further optimization.

Next distinct research step, only with a *predeclared chronological retraining protocol* and no ex-post policy hunt:
- Evaluate a learning target that explicitly predicts **next-position holding-period expected utility / risk-adjusted rank and regret** (versus the current Tail's elite-tailmix event), using corrected feature data and training-only variable selection.
- Preserve LEGACY Top2 as the source-only execution sanity baseline, not falsely claim it reconstructs the full production V2.
- Use genuinely new untouched data or source vintage as final confirmation before production promotion.

**No CAGR-based hyperparameter selection, no post-hoc "winning" arm promoted, no independent virgin holdout claim.**
