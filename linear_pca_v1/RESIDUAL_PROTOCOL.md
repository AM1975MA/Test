# Discarded PCA directions: controlled zero-start refit

Requested after frozen-coefficient decomposition. This is an exploratory, post-PCA follow-up, not an independent confirmation. Only AM1975MA/Test and the original three frozen inputs. No production changes.

For each original annual fold2017-2026 and download, fit the identical training-only PCA95 basis, including whole boundary eigenspaces. Keep its complementary low-variance directions (expected82, not individual original feature columns). Retrain LINEAR from zero in that subspace. Do not whiten/rescale PCs; preserve preprocessing, subtraining/validation split, label maturity, L2=0.001, repaired numerical solver and stopping rule. All other portfolio components, costs and execution unchanged. No hyperparameter search or new historical-window restriction is introduced in this PCA experiment.

Thirty new fits, independent projected-gradient tolerance1e-7, inference/basis/hash audits, three full canonical V2 replays. Original annual LINEAR controls reused byte-for-byte. Original PCA95 results reused as reference, not retrained. Compare CAGR,MaxDD,Sharpe,CAGR dispersion,Top1/orderedTop2 disagreement and all annual returns including2021/2023. Apply existing annual-reference economic and predictive-preservation gates; no promotion based on mean CAGR alone. Opportunity remains excluded from this canonical recipe.

The 87.08% squared coefficient norm in the discarded space is not an information/profit share. A successful decomposition does not predict the result of this independently trained restricted model. Report failed gates and all three downloads. Research only.

## Threshold sensitivity extension

User requested deeper examination after95results. Two additional fixed thresholds90%and99%, selected before new outcomes; original95%andfull125controls reused. Each threshold has30annualfits and3replays, no changes to other recipe parameters. Number of complementary PCs is training-derived per fold; report threshold, count, variance and subspace/selection sensitivity. This is a post-hoc sensitivity study, not a claim of an optimal threshold or independent confirmation.
