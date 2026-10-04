# ETF_TRADER_PERTURBATION_FORENSICS_V1 — consolidated conclusion

Status: **FORENSIC V1 CLOSED ENOUGH FOR REMEDIATION TESTS**

## Primary causal finding

The dominant perturbation amplifier is the **Compact21 XGBoost ranker training stage inside Titanium**.

Measured chain:
- raw close relative perturbation: mean ~1.5e-7;
- simple momentum ranks: essentially unchanged;
- MA3 cluster IDs: ~0.013%–0.029% disagreement;
- Titanium Tail rank: only ~5.8%–6.5% cells differ, very small mean differences;
- Compact21 raw output: mean abs difference ~0.035–0.036;
- Compact21 rank: ~92.3%–93.5% cells differ, mean abs rank difference ~0.053–0.054;
- macro boost: no cross-snapshot difference in the audited period;
- TIT_R: ~91.6%–92.2% cells differ.

Compact21 attribution shows that inference-feature perturbations alone are almost harmless (mean rank difference ~1e-4 and zero Top1 disagreement in sampled years), while perturbations in the **training set** create the large divergence. Training-feature-only and training-label-only ablations both reproduce substantial instability.

The Compact21 target is integerized from percentile rank using round(target_rank_pct * 100), so a tiny fraction (~0.05%–0.07%) of label changes can alter tree/ranking structure materially.

## Downstream layers excluded as primary causes

- Execution ablation: freezing Repeat2 decisions and executing them on Repeat1/2/3 raw reduces CAGR span from 4.9236 pp to ~0.000022 pp. Therefore execution prices, stops, destination risk gross and V6 are not material causes.
- Clustering is highly stable and is not the primary amplifier.
- Tail/Ridge component is orders of magnitude more stable than Compact21.
- Macro boost is identical across snapshots in the Titanium component audit.

## Feature quantization test

Rounding the 125 Compact21 features to **4 decimals (Q4)**:
- raises exact training-feature equality across snapshots from ~44.3% to ~91.6%;
- reduces Compact21 mean rank divergence by ~18.0% in the sampled-year forensic;
- full canonical Q4 replay reduces CAGR span from 4.9236 pp to **2.2450 pp** (**54.4% reduction**);
- mean CAGR falls from 31.758% to **29.013%**;
- mean Top1 disagreement does not improve (31.38% -> 34.09%);
- Top1-or-Top2 disagreement improves slightly (61.65% -> 60.62%).

Q3 was not better than baseline on mean rank divergence. Q4 is therefore a promising stabilizer, but not a complete solution and not yet a promoted production change.

Coarsening Compact21 labels from 100 to 50 bins reduces mean rank divergence by ~14%; Q4 + 50-bin labels reduces it by ~22%, but both worsen sampled Top1 disagreement. This confirms that **both training features and discrete labels contribute**, while direct winner stability remains unresolved.

## Lookahead audit

Static audit: PASS for maturity gating, annual prequential fitting, training-only transforms, cluster timing, risk timing and V6 timing. .bfill() is unsafe style but was not exercised on the controlled Original149 evaluation interval because there were zero missing candidate close cells.

Dynamic future-mutation/truncation audit:
- byte-preserved 2020 test passes exactly;
- an initial 2023 parallel test showed small ET-side differences despite identical historical prefix;
- dedicated single-thread closure produces **exactly identical ET_TAIL, XGB_TAIL and TAIL_HYBRID** under both future mutation and truncation.

Conclusion: **no evidence of operational lookahead in the controlled canonical path**. The earlier dynamic discrepancy is attributable to parallel numerical/ordering sensitivity, not dependence on future values. Research-period tuning / burned development data and universe survivorship remain separate methodology caveats.

## Recommended next remediation line

Do not modify the whole model. Target Compact21 training stability.

Priority candidate:
1. freeze a new preregistered COMPACT21_STABILITY_V1 line;
2. use Q4 feature quantization as the first candidate because it cut CAGR dispersion by 54.4%;
3. preserve baseline model architecture initially;
4. assess convergence metrics before CAGR;
5. separately test a robust treatment of the discrete Compact21 label boundary rather than tuning label-bin count ex post;
6. only after a stable Compact21 exists, return to the deferred causal residual-feedback learner.
