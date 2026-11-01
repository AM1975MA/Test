# OLC12-B — task-trained fusion, disclosed post-observation extension

Added after the fixed OLC12 integration metrics and 188 paths were observed and saved in CHECKPOINT_02, before any meta-model fit or output. It is not independent confirmation and does not rewrite the first protocol.

Question: does the classifier supply useful incremental information to a small learned integrator, rather than requiring an arbitrary blend coefficient? No new base features or base-learner refits.

Compare META2 and META3. META2 inputs: current Return percentile and matched regressor's original smoothed/powered Hybrid signal. META3 adds the logit of current XGB_CLASS event probability (clip only for logit to [1e-6,1-1e-6]). Both train to recognize the top quintile of the true Hybrid multi-horizon target, on identical past OOF predictions and fully mature complete monthly target groups. No portfolio outcomes enter fitting.

Every January 2021–2026, require at least18 complete past signal months, all group exit63 dates strictly before January1. Standardize using only weighted training data; each month carries total weight1. Target top-quintile uses average-rank tie handling. Logistic loss, intercept unpenalized, L2 coefficient .01 on standardized slopes; all slopes constrained nonnegative. Intercept initialized to training event-frequency logit and slopes zero. SciPy L-BFGS-B, maxiter1000, ftol1e-12. Same structure and hyperparameters in both universes. No search over penalty, feature set, sign or training length. Return and regressor native outputs remain available separately.

24 planned small calibration/combination fits (2specs*6years*2markets), not24 new underlying ETF predictors. Before sufficient history, use MATCHED_REG rankings and mark probability unavailable; do not pretend a baseline rank is a probability. Each output chooses Top2 with HALF weights; no cash alternative, leverage or probability-scaled capital.

Evaluate native task discrimination, probabilistic loss and static opportunity outcomes before full-portfolio results. Replay META2/META3 with each of IMMEDIATE/DELAY3/PHASE5, legacy .001/.003 and both markets:24additional paths. Compare META3 against META2 to isolate classifier input; against MATCHED_REG to measure complete integration. Preserve all adverse periods. No candidate promoted from a single CAGR, and no CI-zero veto.

Tests: every training group fully mature; no current/future labels; future label perturbation leaves earlier coefficients unchanged; coefficient constraints; equal monthly weighting; uniform feature degeneracy; insufficient-history fallback; native probability distinct from final capital. Retain optimizer diagnostics, training keys, scaling parameters and model coefficients. These are exploratory tests after fixed-integration results, explicitly counted in selection risk.
