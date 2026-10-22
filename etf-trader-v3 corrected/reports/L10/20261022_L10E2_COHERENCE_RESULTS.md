# ETF Trader V3 Corrected — L10.E2 conditional coherence of selected ETF trajectories

**22 Oct 2026 — completed, research-only, NOT PROMOTED.**
One preregistered extra gate on E1, executed [39743730941](https://github.com/AM1975MA/Test/actions/runs/39743730941), artifact **12410790359**, 101 maturity-complete out-of-sample monthly signals, frozen 149 ETF / 500 overlapping baskets of 24 each. Successful atomic data-archival run [39744027534](https://github.com/AM1975MA/Test/actions/runs/39744027534). One failed **archive-only** run 39743951395 lacked pandas, corrected without changing model, data or analysis outputs. The canonical E1 experiment is 39742108852.

## Research objective

**Respect the intended architecture: original XGBoost CORRECTED rank FIRST, causal mathematical audit of the actually selected ETFs SECOND, then optional replacement from the *same original ML rank*.** Never analytically re-rank the entire basket and never force Top5 into the policy. All unflagged incumbent Top3 slots remain untouched; weights [0.5,0.3,0.2] fixed. Ex-ante data restricted to adjusted historical closes through t, prospective 21D labels only for subsequent evaluation. No refit, no cost tuning or CAGR optimization.

E1 flagged any original Top3 position whose 21-session log momentum is negative and whose drawdown from the trailing 63-session high is <=−10%. E1 on 2018–2026 had removed many genuine future winners. To isolate a possible structural downtrend from a rebound-capable correction, **E2 adds exactly ONE new condition**:

\`efficiency21 = abs(log(C_t/C_{t-21})) / sum_{s=t-20}^t abs(log(C_s/C_{s-1}))\`.

Only if E1 flag *and* \`efficiency21 >=0.45\` do we replace the selected ETF by the next original ML ranked **unflagged** ticker from rank 4+, retaining the original slot/weight. A choppy or partly retracing price decline is intentionally not an automatic veto. Missing efficiency -> do not veto. The 0.45 threshold and rule were committed in the [pre-result protocol](./20261022_L10E2_TRAJECTORY_COHERENCE_PREREG.md) before outcome inspection; this period is NOT a new or untouched holdout.

The run computes BASE, original E1 and E2 on **identical baskets, ETF-months, and forward labels**, reproducing BASE and E1 archived reference metrics numerically. Original certified source run 39482809691, frozen original CORRECTED OOS run 39700865721, basket SHA256 \`36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e\`; causal perturbation of future prices PASS; all 149×101 signal windows fully available. Output contains complete timestamped as-of 21D momentum, 63D drawdown, efficiency, flag, future audit-only realized outcome and actual individual substitutions.

## Matched Top3 diagnostic

| Metric (mean across 101 monthly aggregates) | Frozen ML BASE | Aggressive E1 | Coherence-gated E2 |
|---|---:|---:|---:|
| Selected basket winner appears in Top3 | **35.4713%** | 29.2713% | 34.8317% |
| Realized weight allocated to basket-best ETF | **12.5818%** | 10.1826% | 12.3822% |
| Weight on next21D losers <=−10% | 8.4861% | **6.7834%** | 8.2986% |
| Future-weighted percentile rank | **0.524852** | 0.516791 | 0.524261 |
| Weighted forward21D return | 1.3560% | 1.2964% | 1.3753% |
| Weighted 21D oracle regret | 0.105470 | 0.106066 | 0.105277 |
| Bottom-three allocated weight | **22.1313%** | 19.9531% | 22.1552% |
| Percent baskets modified | 0% | 56.6119% | **9.1168%** |
| Original Top3 capital changed | 0% | 31.9228% | **3.8147%** |
| Replacement events across 500×101 basket-months | 0 | 45,684 | **5,297** |

*Why the apparent return improvement is NOT established*: E2-BASE weighted 21D return difference +0.000193 (+0.0193 percentage points), with wide paired CI95 [−0.000712,+0.001223]. These are arithmetic 21D forward proxy returns, **not an execution backtest**.

## Paired calendar-month six-month-block bootstrap, 6000 draws

| Contrast | Mean delta | Descriptive CI95 |
|---|---:|---:|
| E2−BASE future basket winner in Top3 | **−0.6396 pp** | [−1.8158,+0.2357] pp |
| E2−BASE winner invested weight | **−0.1996 pp** | [−0.6059,+0.0941] pp |
| E2−BASE loss10 invested weight | **−0.1875 pp** | [−0.6058,+0.1721] pp |
| E2−BASE weighted future rank | −0.000591 | [−0.004142,+0.002872] |
| E2−BASE 21D weighted forward return | +0.000193 | [−0.000712,+0.001223] |
| E2−BASE weighted regret | −0.000193 | [−0.001223,+0.000712] |
| E2−E1 future basket winner in Top3 | **+5.5604 pp** | [+3.1068,+8.2595] pp |
| E2−E1 invested weight on basket winner | **+2.1996 pp** | [+1.2490,+3.2491] pp |
| E2−E1 loss10 weight | +1.5152 pp | [−0.0066,+2.9450] pp |

The 500 baskets **overlap heavily** and are aggregated within calendar month before resampling. Tested periods 2018–2026 have repeatedly influenced research; bootstrap CIs are exploratory, not independent confirmatory evidence. Several correlated endpoints are evaluated.

## Analysis of the mathematical rule, not only its policy

- E1 initially flagged **31.9556%** of baseline invested capital; E2 flags only **3.8147%**. That preserves most ML choices by construction.
- E2 replaces **0.10489 holdings per basket/month** on average, versus **0.90463** for E1.
- E2-flagged original invested weight that will subsequently lose >=10% is **0.6901%**, while replacement weight that will subsequently lose >=10% is **0.5026%**, net benefit just **0.1875 pp**.
- E2 removes **0.4693%** invested original weight on actual future basket winners and replaces it with **0.2697%** on actual winners: net **0.1996 pp** winner-weight harm remains.
- It also removes **1.6014%** original invested capital from ETF positions with *positive* future 21D return. Negative coherent past trajectories can recover too.
- Among **unique initially selected ETF-months**, the E2 warning precision for future <=−10% losses is roughly **10.82%** on only 39 months with warnings, and unflagged loss rate **7.17%** across 101 months. The original E1 warning precision average 11.08% is over 99 different months, so raw comparison does NOT establish enrichment or loss of skill; month selection and sparse events prevent naïve significance interpretation. Separate conditional matched cohort analysis would be necessary for a stronger claim.
- In only 69 months were future loss10 events present among selected names, and the E2 flag recalled an average **3.71%** of such loss events (on those months): too little coverage for a reliable veto.

## Decision and next mathematical objective

**E2 did not pass the post-selection predictive/functional promotion gate.** It avoided most false vetoes of E1, but also abandoned nearly all of E1's downside protection. No meaningful improvement over keeping frozen ML alone in the matched prospective metric suite; neither economic benefit nor robust risk protection is established. Do not retrospectively adjust the 0.45 threshold based on this OOS evaluation, and do not promote. Preserve both negative/neutral E1 and E2 experiments and their source.

This is a useful failure diagnostic: the critical missing piece is not a stricter minimum on price-path coherence, but a **conditional estimate of whether the incumbent's expected future utility is genuinely worse than its *specific* available replacement**. An E3 research hypothesis could model an explicit pairwise *review and substitution* signal trained only on matured prior-year labels, including as-of trajectory shape, local rebound markers, relative peer context and their calibration, with primary penalty for falsely vetoing true winners. Such a model would **not** replace the original general ranker; it would issue an optional reasoned veto and must be tested as one frozen intervention before any execution or 10bp costs. Do not train/select from reused 2018–2026 and then claim independent evidence; retain untouched newer vintages.

## Durable sources

- Frozen [preregistered L10.E2 protocol](./20261022_L10E2_TRAJECTORY_COHERENCE_PREREG.md).
- Audited [E2 source, deterministic E1 rerun, monthly block bootstrap](../../experiments/l10_postrank_trajectory/evaluate_e2.py).
- [Complete immutable output data](./data_run_39743730941/): summary, yearly, monthly, 15,049 ETF-date as-of audits, **5,297** individual replacement records, paired bootstrap and manifest.
- Main workflow source \`.github/workflows/v3-l10e2-trajectory-coherence.yml\`.
- Eval Actions run [39743730941](https://github.com/AM1975MA/Test/actions/runs/39743730941) success, artifact **12410790359**.
- First archive-only run **39743951395** failed because pandas was not installed in the audit step, retry **39744027534** success, with no change to E2 outcomes.
- Original production V2, all frozen V3 reference models and prior experiment outputs unchanged.
