# R0-M — Fixed 20bp pair-band controlled synthetic test: preregistration
**2026-10-09, committed BEFORE R0-M model fitting.** `AM1975MA/Test`, branch `research/v2-xgb-immutable-checkpoints-20261008`.

## Scientific question
Can masking only training pairs whose forward return gaps are below a *fixed externally motivated* 20bp economic indifference band prevent rank-flip sensitivity while retaining extreme winner capture? The previous read-only R0-J audit: 8 native grade-pair reversals, all in minuscule return gaps, 0 reversals outside 20bp, exclusion of ~3.79% total theoretical pairs, but 14 threshold-eligibility flips; not proof of model fitness. R0-L verifies custom XGB Python callback but it uses FULL group pairs and DIAGONAL Hessian unlike native `rank:pairwise`.

## Essential three-arm experimental design
1. **Native reference:** `rank:pairwise` trained on native rounded within-query percentile label `round(100*rank(pct=True))`.
2. **Custom same algorithm, NO mask control:** same existing R0-L logistic full-pair objective and diagonal Hessian with `fee_band=0.0`, continuous future synthetic returns as target.
3. **Custom identical algorithm, MASKED:** exactly the same full-pair logistic objective, scoring, Hessian and training size with **`fee_band=0.002`**, no other changes.

**The causal contrast for the 20bp mask is (3) minus (2), NOT (3) minus (1).** Any differences of (2) vs (1) could be explained by loss target, pair sampler, Hessian and scale. Even if (3) outperforms (2), it does not prove compatibility/performance parity with native XGB.

## Frozen fixture and perturbation
- Two new synthetic worlds seeds `20261031` and `20261101`, world A stronger nonlinear signal, B weaker/noisier. **32 training groups ×32 ETFs =1024 training rows**, **20 held eval groups ×32=640 rows** per world, 125 float32 feature columns. Use XGB 3.1.3 canonical-like tree params depth4/eta .035/subsample .85/cols .8/min_child8/L2 8/L1 .1/hist with **360 rounds**. One predeclared XGB seed 101 for this mechanism audit (NOT evidence of seed robustness); other original seeds 202/303 not tested at this stage.
- Synthetic continuous 21-day forward returns are nonlinear functions of contemporaneous features + additive noise, standardized *within group* to approximately 2.5% cross-sectional SD. Generate all labels and test realized returns from frozen mathematical function; note the economic units are artificial, not adjusted Yahoo.
- **Original**, **X_only** (train X jitter std 2.5e-6, same y and same continuous returns), **Y_only**: pre-identify a pair in the **middle** 50% of one 32-row query and set its original return grades to *within ±0.000005* of their mean while preserving its placement between neighboring ranks (must assert exactly one pair ordinal inversion). Swap the close original continuous returns to create strictly inverted ordinal rank in that query and recompute the two integer-grade labels; only the two selected returns change. Verify original/altered return gaps are below 20bp, changed native label signs >0, no other pair ranks change. The original return near-tie is constructed identically before *all* scenario training, not optimized after seeing evaluation.
- Same synthetic evaluation X and true future returns in all variants and methods. **2 worlds×3 algorithms×3 scenarios×1 seed =18 independent 360-round fits** total; no hyperparameter sweeps, other objective experiments or actual ETF fitting.
- Fully source-consistent native query grouping `QuantileDMatrix(...).set_group(...)` and reference test DMatrix; explicit group pointer check in custom objective. No XGB training with future eval labels.

## Prespecified metrics and interpretation
- Pair-mask fraction in ORIGINAL and Y-only per world, number of eligible-state flips; rule must remove swapped tiny pair but preserve >20bp potential-gain pairs. Gradient/Hessian invariance on swapped near-tie as a **unit**, not assumed to imply learned tree invariance (because trees also change with X).
- For each world & arm & scenario: held group predicted Top1 in realized Top5, exact winner, NDCG@5 using continuous latent ranking; compare baseline and perturbation matched Top1 disagreement, Top5 Jaccard, rank-MAD and return regret relative to ex-post winner (illustrative oracle, not P&L). **Do not rely on NDCG alone**.
- No change to number of rounds, leaf count or feature table. No separate unregistered training iterations. Do not select alternate band, objective weights or XGB params by outcomes.
- Stage conclusion criteria: (i) matched custom mask improves label-perturbation stability in BOTH worlds without worsening high-upside Top5, (ii) robust X-only behavior separately disclosed, (iii) the custom full-pair control itself must retain native-like tail competence; otherwise `NO GO` even with higher Top1 agreement. This is a qualitative pre-set joint test, **not a market release gate**.
- If test fails, stop and retain canonical V2. If passes, label `SYNTHETIC_ONLY_CANDIDATE`, require a different, point-in-time as-of market cohort and full V2 matched economic validation before any code changes.
- Reproducibility deliverables: Python source, TDD test(s), JSON/CSV, environment versions and logs in new dedicated `target_redesign_level2_v1/r0m_cost_pairwise/` under Test; no change to `vendor`, `Etf_trader`, `Trader_selector`, legacy branch.
