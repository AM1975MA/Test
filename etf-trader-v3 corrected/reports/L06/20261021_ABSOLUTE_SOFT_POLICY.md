# V3 L06.5 — Controlled probability-of-absolute-loss soft position weights

**21 October 2026 — COMPLETE. STATUS: RESEARCH CANDIDATE, NOT PRODUCTION APPROVED.**

Source-backed [successful GitHub Actions 39672320747](https://github.com/AM1975MA/Test/actions/runs/39672320747); full artifact **12380905630** `v3-l06-calibrated-absolute-soft-policy-results`.

## Exactly one risk-policy change

- Same 149 ETFs, canonical 500 baskets of 24; **53 mature monthly signals 2022–May2026**. Frozen original Tail45 expert and exact same three selected instruments per basket. No change to L00–L05, Tail, regime, weight selection universe or labels.
- Baseline `TOP3_DECAY` = three fixed target weights `[0.5,0.3,0.2]`. Numerically checked against original independently completed L05 OOS portfolio selection metrics.
- The new risk input is a single train-only, annual chronological OOS prediction `p_abs_loss` of a realized **<=−10% absolute ETF next-21D loss** among Tail-selected ETF candidates. Calibration provenance: [successful 39671493979](https://github.com/AM1975MA/Test/actions/runs/39671493979), no target leakage.
- One predefined **non-veto** new weight formula: `w'_i = normalize(w_i × exp(-3 × p_abs_loss_i))`. Coefficient `3` is declared before evaluating this experiment and is NOT optimized on the 53 test months.
- The original ETF names and selection ranks remain entirely untouched. All weights remain strictly positive and sum to one, without selling the entire risky asset or substituting a different ETF.
- Metrics concern the **functional task of an allocation risk policy**: severe absolute-loss exposure, winner exposure, rank quality, regret, target-weight churn and concentration. **No CAGR/long-term total equity PnL was computed or used to select the policy.**

## Matched results

| Metric | Frozen Top3 50/30/20 | Absolute-loss soft weights | Paired delta (new minus frozen) |
|---|---:|---:|---:|
| Winner in selected Top-3 | 44.2679% | 44.2679% | 0 exactly |
| Weight on future basket best ETF | **15.6657%** | 15.5743% | −0.0914 pp; 95% CI [−0.1495,−0.0389] |
| Weight on ETFs suffering actual absolute >=10% next21D loss | 9.2442% | **9.1462%** | −0.0979 pp; CI [−0.1628,−0.0345] |
| Weight on eventual bottom-3 of 24 | 28.2928% | **28.0772%** | −0.2157 pp; CI [−0.2734,−0.1555] |
| Mean quality of realized selected ETF ranks | 0.505593 | **0.506417** | +0.000825; CI [+0.000125,+0.001476] |
| Basket oracle regret over next21D (fractional return) | 0.115445 | **0.115259** | −0.000185; CI [−0.000333,−0.000026] |
| Target weight churn per month | **0.347135** | 0.356240 | +0.009105; CI [+0.008006,+0.010270] |
| Mean maximum position weight | 50.000% | **49.369%** | −0.631 pp |
| Effective number of positions | 2.63158 | 2.65317 | +0.02159 |

The absolute severe-loss exposure reduction is real in this sample but small: **−0.0979 percentage points of portfolio weight**. The risk policy also slightly lowers future winner weight **−0.0914 pp** and increases target-weight churn by **2.62%** vs control. Within this narrow policy family, the signs of rank quality and opportunity regret are positive, but their *magnitudes* are extremely small.

These are exploratory calendar-month paired 6-month circular block bootstrap CIs, **6,000 resamples**, on 53 already repeatedly examined OOS monthly dates. The same 500 baskets are highly overlapping and were averaged by month first. They do not provide 500 independent confirmations.

## Decision and continuation gate

**Keep `TOP3_ABSLOSS_EXP3` as an isolated research candidate ONLY; do not merge into ETF Trader's live production policy**. It is a safer structural idea than the rejected 85th-percentile hard exclusion, but it has no established net benefit after genuine trading costs and untouched future independent validation. The risk signal does not yet have enough discrimination (absolute-loss ROC AUC ~0.627) to support an aggressive veto.

Further L06 improvements should avoid choosing larger or smaller exponent factors by inspecting this same OOS period. A future genuinely untouched data vintage or nested train-only risk policy calibration should test risk calibration drift and the opportunity cost of false positives. The L07 integrated whole-strategy certification remains open and blocked.

## Complete trace

L06.2 generic percentile soft weight test: [39669570005](https://github.com/AM1975MA/Test/actions/runs/39669570005) (weak benefit, not promoted).
L06.3 selected-conditional relative loser classification: [39670543932](https://github.com/AM1975MA/Test/actions/runs/39670543932) (did not improve AP, rejected).
L06.4 absolute-loss detection and yearly calibration: [39671493979](https://github.com/AM1975MA/Test/actions/runs/39671493979) (limited functional PASS).
L06.5 calibrated absolute-loss soft weights: [39672320747](https://github.com/AM1975MA/Test/actions/runs/39672320747) (candidate only).
