# Additional diagnosis after the first OLC-01 replay

The initial72path summaries have now been inspected. Direct economic ranking and lifecycle actions built from it underperform CL01 markedly. No hyperparameter, target weight, risk threshold or transaction convention is changed to rescue those results.

Run one additional, explicitly post-result diagnostic on BOTH markets and both costs: retain the CL01 Top2 as the only replacement proposal, and let the already fitted21-only or3-head value model choose between that proposal, actual HOLD and cash. The comparator is the identical CL01 half-weight account. Compare to the existing model-generated-proposal GATE under identical execution. Both fixed learners (Ridge and HGB) are included. Sixteen additional paths are expected:2learners x2horizon contracts x2markets x2costs.

This separates deterioration caused by replacing the opportunity generator from deterioration caused by accepting/rejecting actual incumbent changes. It is not an independent holdout or a newly tuned strategy. Preserve all initial negative paths. No promotion merely because a filter reduces turnover. Label post-selection and report missed opportunity cost as well as avoided changes. The same72saved annual head models are reused, with no refit.
