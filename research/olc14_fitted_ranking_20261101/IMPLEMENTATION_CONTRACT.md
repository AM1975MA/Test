# OLC14 score-scale clarification

Declared while elementary horizon training is running, before any fitted weights, score comparisons or new economic outcomes are computed.

The learned curvature alpha acts on available horizon forecasts. It can change the marginal numerical scale without changing ordinal quality. Passing that scale directly to the old .475/.525 fusion would silently change its effective influence.

For CUM_FIT and INC_FIT only, map each date's learned score monotonically to the contemporaneous empirical distribution of its matching FIXED score before temporal memory and fusion. A strict ordering receives the same sorted anchor values; tied learned scores receive the mean anchor values at their occupied ranks. The mapping uses no outcomes, is nondecreasing, and preserves ordering except unavoidable ties already present. Store raw and mapped scores. Native rank/payoff metrics are unchanged by the mapping. ORIGINAL and fixed anchors are untouched; TARGET_SELECT retains the original OLC13 component-score scale.

This is a representation control, not calibration of predicted returns or event probabilities. It makes fitted-versus-fixed integration less confounded by level/scale. Tests must prove invariance to strictly increasing recodings of the learned score, identical marginal anchor values without ties, and tie handling. Protocol objectives, alpha/lambda candidates, model inputs and training populations remain unchanged.
