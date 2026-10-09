# Compact21 Top1 margin / economic-gap diagnostic — independently reviewed 2026-10-09

Evidence: [GitHub Actions run 37933141010](https://github.com/AM1975MA/Test/actions/runs/37933141010), **SUCCESS**, artifact `compact21-flip-regret-diagnostic` ID `11616488402`. Preregistered method in [PREREGISTRATION.md](../PREREGISTRATION.md). The run verified frozen source, strict outcome maturity, 10 annual original artifacts, independent original 114-month Top1 disagreement against run 37931212920, and six unit tests.

One common Repeat2 inference panel from the three frozen Original149 Yahoo repeats. Monthly evaluation dates 2017–2026: 114 total; 3 repeat pairs × 114 = 342 source/date pair comparisons for each variant. All quality labels/results must mature by 2026-07-01. Forward returns are 21-session *simple* Open-to-Open changes, NOT portfolio trades/CAGR.

## BASE
- Source-pair Top1 disagreement: **171/342 = 50.00%**; individual pairs 1–2: 62/114=54.39%; 1–3:49/114=42.98%; 2–3:60/114=52.63%.
- Define marginal confidence on each model/date independently: normalized score gap `(score_top1-score_top2)/(scoreQ75-scoreQ25)`. A pair is weak-margin if **at least one** of its two models has score gap <=0.1 IQR. This is an arbitrary preregistered descriptive cutoff, not learned probability/confidence.
- Among all 342 BASE pair/date comparisons, **264 weak-margin** (77.19%), **78 strong-margin** (22.81%). Of weak-margin comparisons 159 flip, so **P(flip|weak)=159/264=60.23%**. Of strong-margin comparisons 12 flip, so **P(flip|strong)=12/78=15.38%**. Conditioning matters: 159/171 = **92.98% of all flips** occur with at least one weak-margin model, but the weak-margin state itself is also common.
- All 171 observed BASE Top1 flip pairs have mature forward returns for both selected tickers on original Repeat2 outcomes. Absolute differences in *their ex-post 21-session simple returns*: median **4.196 percentage points**, 90th percentile **15.872 pp**. **81.87%** differ by more than **1 pp** and **43.86%** by more than **5 pp**. These are abs differences; the stable or low-margin choice is NOT claimed to have better returns.
- Selected Top1 mean realized 21-session forward return on the 339 mature vintage/date choices = **+2.624%**; realized return percentile = **0.583437**. These overlapping/source-dependent observations must NOT be annualized into CAGR or misconstrued as trade returns.

## Earlier source-attribution treatments (not deployable)
| Paired source treatment | Top1 flip count | Weak-margin flips among all flips | Median abs 21-session forward-return gap (pp) | 90th percentile gap (pp) |
|---|---:|---:|---:|---:|
| Original X / original Y (BASE) | 171/342 (50.00%) | 92.98% | 4.196 | 15.872 |
| Native X / common Repeat2 Y | 193/342 (56.43%) | 93.26% | 4.331 | 16.556 |
| Common Repeat2 X / native Y | 195/342 (57.02%) | 92.82% | 4.196 | 15.846 |

The treatments show why the reduction of rank-MAD alone is misleading: both increase chosen-ETF disagreement. The observed 21-session-return gaps can be sizable even with tiny model ranking margins. The margin conditional figures are **descriptive on reused development data**, not causal evidence that imposing a threshold improves returns.

## Next experiment
Single registered hybrid on a distinct research branch: **0.75 original XGB percentile ranks +0.25 Ridge percentile ranks**. The Ridge is an existing frozen historical stability comparator; unlike the cross-vintage controls this treatment can be trained entirely on one snapshot. It must pass both prior stability and selected-Top1 quality gates before any full-strategy CAGR replay is attempted. Keep all negative results, old source unchanged, and production untouched.
