# Preregistered hypothesis: differentiable Spearman via exact torchsort soft-rank

Date 2026-10-20. Branch research/original149-softspearman-20261020; baseline frozen branch research/original149-tcn5d-causal-20261020 and listwise experiment untouched. No production changes.

**Frozen experimental setting**: Original149 immutable frozen roster / OHLCV files, canonical 125 Compact21 features, TCN with 30-day lookback 24 channels, 0.35 dropout, 5 epochs maximum, early stopping on prior-year validation only, AdamW lr .001 weight decay .003, identical annual-expanding walk-forward, maturity gate at last train and validation label, 2017–2026 OOS, 5 trading-day next-open to next-open+5 target and rebalance. Score and select 5 ETFs weekly, equal weight, conservative 20bp roundtrip per week, no leverage, no cash and no risk overlay. Exact 476 weekly OOS decision dates. Training grouping by signal date with all as-of eligible ETFs. Input only last 30 bars 125 features at t; no future per-ETF returns used at inference.

**Genuine torchsort.soft_rank** (Blondel et al. projection/sorting on permutahedron): regularization=l2, regularization_strength **1.0**. Normalize *predicted* scores within each date by their standard deviation (using only the predictions, not labels) prior to soft_rank. Hard target rank of historical matured cross-sectional future return percentile y. Main loss 1−Pearson(soft_rank(prediction),rank(y)). This is an approximation to Spearman correlation, optimized differentiably end-to-end through torchsort. For top-weighted variant assign **weight 5× to actual matured top-5** y positions and weight 1× to others in the weighted Pearson correlation. Important: this weighted metric is not literally conventional unweighted Spearman and uses top-5 true outcomes only during training/validation, never during inference.

Three fixed experimental variants:
- SOFTSPEARMAN: pure soft Spearman.
- SOFTSPEARMAN_RETURN: pure soft Spearman + **0.30** SmoothL1(predicted score, (forward_return−median)/max(q90−q10,1e−5) clipped to ±3); training-only matured ret input.
- SOFTSPEARMAN_TOP5: truth-top5-weighted continuous Spearman correlation, weight 5 for true top5 versus all remaining eligible names.

Both pilot 2024–2025 and full primary 2017–2026 run identical predetermined variants irrespective of pilot results. Include genuine autograd tests, monotonicity, input permutation invariance, hybrid relative return data separation, Top5 truth-weight behavior, within-group no mixed timestamps and matured exit. No hyperparam tuning after results.

Compare identical OOS weekly Top5 return, CAGR, MaxDD, Sharpe, RankIC on ALL eligible ETF return ranks, top-5 oracle overlap with actual nominal 5-day returns, decile regret, and mean selected forward return. Control: original registered Pointwise TCN, Ridge125, raw MOM21; compare historical ListNet/ListMLE 3-way results and max-vol controls for context; primary test is whether raw RankIC improves without worsening economic net results. Independent paired-date audit with 5-week circular-block bootstrap, descriptive not prospectively valid due to many prior models.

**Reproducibility caveat**: Use PyTorch **2.6.0 CPU** and matching precompiled torchsort 0.1.10 pt26cpu binary because upstream release does not publish a 2.7.1 CPU wheel, while original Pointwise used torch 2.7.1; numerical-library version mismatch is a controlled reproducibility caveat, not an intentionally tuned model setting. Do not claim exact computational parity with prior model on this point.

**Prior exploratory outcomes not used as tuning selection**: Pointwise original net +5.19% CAGR MaxDD −48.49% RankIC .0561; raw MOM21 +13.41% MaxDD −34.94% despite RankIC near zero; all prior 3 Listwise variants negative 2017–2026. No parameter choice from pilot to full.
