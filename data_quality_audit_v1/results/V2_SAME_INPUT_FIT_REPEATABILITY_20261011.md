# Three fully independent V2 fits on byte-identical Original149 input — 2026-10-11

**Verified success:** GitHub Actions [38132305441](https://github.com/AM1975MA/Test/actions/runs/38132305441), 3/3 canonical ETF Trader V2 fits + summary success. All repeated runs consumed the exact frozen Yahoo Original149 `_repeat1` source from run 37121749852, research-only common global downvol correction and robust normalization α=1.0, same environment, runner and hyperparameters. No production edits. Each job trained anew: no cached fit or stored historical model scores.

| Metric | Independent fitting #1 | Independent fitting #2 | Independent fitting #3 |
|---|---:|---:|---:|
| CAGR | 0.30532892009742985 | 0.30532892009742985 | 0.30532892009742985 |
| Max DD | -0.27701037400899275 | -0.27701037400899275 | -0.27701037400899275 |
| Sharpe | 1.0681711776600111 | 1.0681711776600111 | 1.0681711776600114 |
| Final capital | 12.203428122516222 | 12.203428122516222 | 12.203428122516222 |
| Annual turnover | 13.150337841825086 | 13.150337841825086 | 13.150337841825086 |

CAGR max-minus-min **0.0 percentage points**. Daily Top1 disagreements **0**, Top2 disagreements **0** across 2366 session decisions. Source-only `predictions_sha256` **b6d160d502c284f5b52265ed4ad065661e4e44ba8e9cd4532fe4f19a2ee997e1** identical in all 3. Titanium full/candidate hashes identical all 3.

**Important nuance:** MA3 panel raw pickle SHA256 differs in run 3 (`eaaf6ba79eab...`) from runs 1/2 (`7ec2d839c151...`), despite predictions, rankings, economics and other source outputs matching. A bytewise artifact discrepancy by itself could arise from serialization and is **not** a validated numerical feature-value discrepancy; independently inspect semantic equality of MA3 panels before asserting *all* intermediate files are deterministic.

## Interpretation

At fixed original snapshot the observed pipeline fitting+simulation is economically reproducible. This rules out **observed** rerun random variability for this configuration/snapshot/runner, not all sources of training numerical instability across alternative hardware/seeds or other variants. Across *different* downloads original149, α=1.0 CAGR ranged 30.5329–35.4131% (spread 4.8802pp) and Top1 disagreement on 1066 of 2366 dates; this is consistent with source sensitivity but cannot attribute the mechanism solely to raw price changes until fixed-model cross-input replay distinguishes feature drift from retraining response.

## Next investigation
Compare exact price/feature differences at economically significant decision dates, hold model weights fixed when switching source panels, quantify thresholds and near-tie ranking instability. Also test semantic MA3 panel equality irrespective of its pickle hash. No production promotion.
