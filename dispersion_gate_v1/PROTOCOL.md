# Causal dispersion switch - fixed before first replay

Hypothesis: full LINEAR is preferable when cross-ETF return dispersion is high; independently retrained PCA95-discarded LINEAR is preferable when dispersion is low. Exploratory test motivated by previously exposed results, not independent confirmation.

Only AM1975MA/Test,149Original149,three original frozen Yahoo downloads. Never access production or refresh prices. Reuse completed annual full LINEAR and discarded95models/predictions exactly, zero new learner fits. OtherV2layers/costs/risk/execution unchanged; Opportunity excluded.

DispersionD at monthly signal close is the sample standard deviation (ddof1) across eligible Original149 ETF simple returns Close(t)/Close(t-21sessions)-1. Ignore raw observations before2011-01-01 for dispersion. No forward filling, no future labels or forward returns used for membership. Both price endpoints finite and positive; at least100eligible ETF returns required, otherwise fail closed. Log eligible count and regime input for all dates.

Annual January1 threshold is the median of monthly signal dispersions from2012-01-01 through strictly before that January1. Monthly signals thereafter: D>=threshold selects full LINEAR; D<threshold selects discarded95. Threshold fixed for entire year. Unsupervised threshold needs only already-observed inputs; labels need not have matured for threshold calibration, but reused source learners preserve their original maturity contracts. Single21session horizon and single median rule, no threshold/window grid and no yearly best-model selection.

Evaluation2017-2026 on canonical exact prediction keys and original portfolio dates. Two fixed source portfolios reused;3new switch replays only. ReportCAGR,MaxDD,Sharpe,turnover,CAGRspan/SD,Top1/orderedTop2 disagreement,all annual returns and regime disagreement between download vintages. No promotion for meanCAGR alone; original annual-reference preservation gates retained.

Mechanism diagnosis: evaluate both fixed source prediction sets within the same ex-ante low/high query groups. Report date-weighted Top1 percentile,NDCG5,RankIC and realized21session Top1return; combine vintage revisions by date rather than claiming independent observations. Labels entered only after regime assignment, quality exits<=2026-07-01. These are descriptive conditional diagnostics, not significance evidence. Small realized return dispersion may reflect weak signal as well as subtle opportunities. PCA input variance and return dispersion are distinct quantities.

Verify pinned sourceRESULT/prediction hashes, raw byte identity against originalBASEcontracts, original source training fingerprints and exact switched prediction reconstruction. Preserve source models and metadata; candidate has zero fits and explicit prediction-source identity. A passing switch does not prove causal economic regimes, and the inverted conditional pattern would count against the stated hypothesis.
