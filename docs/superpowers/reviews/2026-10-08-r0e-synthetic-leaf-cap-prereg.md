# R0-E — Synthetic split/leaf-cap sensitivity preregistration (single-axis; no ETF training)
**2026-10-08 | Test only | Before first model fit**

## Question
Does imposing a *single* maximum-leaf cap suppress topological bifurcations caused by tiny feature changes and rare relevance-label changes in the *same* grouped XGBoost rank:pairwise synthetic training problem, without collapsing synthetic ranking discrimination?

## One preselected contrast
- Base: `max_depth=4, max_leaves=0` (effective hard upper bound 16 leaves by depth).
- Challenger **ONLY**: `max_depth=4, max_leaves=8`, same default `grow_policy=depthwise`, no simultaneous `gamma`, `min_child_weight` or split-method changes.
- Both use frozen canonical-style `rank:pairwise`, eta .035, subsample .85, colsample_bytree .8, min_child_weight 8, reg_lambda 8, reg_alpha .1, hist method, seed 101, 125 features. *Synthetic only* uses **120 trees**, not the canonical 360, for a fast mechanism probe. Do not claim output identical to V2 or improve financial performance.
- Synthetic 36 query groups × 40 candidates = 1440 training samples; 12 hold-inference groups × 40 = 480 inference samples, 125 features. Generated from NumPy RNG seed 20261008 with nonlinear target function and controlled synthetic noise. Within-query 0–100 relevance integer labels.
- Perturbed train X: independent relative scaled Gaussian jitter of amplitude **2.5e−6** on every feature. One preselected randomly indexed relevance label changes by +1 within [0,100], affecting ~0.069% rows. Keep sample keys, groups, evaluation Xte and original seeds fixed.
- Fit base/reference vs perturbed ONCE for each leaf setting. Four XGB rankers total; do not perform a sweep or retune the perturbation size based on output.

## Primary outcome and interpretive limits
- Read XGB JSON tree dumps; canonicalize split feature, threshold, yes/no/missing, identify first differing (tree,node), count split changes and leaf values, compare exact Top1 agreement on 12 held-eval groups and common-input rank-score absolute differences.
- Check effective distribution of leaf counts per tree. Confirm exactly 120 trees in every fit, same source features/groups and single changed relevance label.
- A "better" toy agreement or lower split differences only shows synthetic response, NOT ETF alpha, stability across Yahoo vintages, or ability to preserve 43% Golden CAGR. If tree-cap has no effect or worsens ranking response, mark **NO MECHANISTIC SUPPORT** and do not launch ETF backtests.
- No available original trained XGB trees were found in tracked GitHub; no claim of authentic first diverging Annual V2 split.

## Future finance gate
- Even if toy structural consistency improves, no parameter selection or backtest on already-used Original149/Golden or reuse of prior trials. Require a new dated as-of dataset, prelocked one candidate, full-V2 economic noninferiority per vintage and positive-tail capture, separate user go-ahead. 
