# OLC16 — direct contextual ranking, not another gate between near-identical formulas

2 November 2026. User asks to go further after OLC15. Parent frozen at 763387eceee4b7fbf131827f10dee7f608abeb68; CUM_FIT candidate and main remain unchanged. This protocol is committed BEFORE new fits and outputs. Research only, no orders or production merge.

## Why this experiment
OLC15 changed a mixture weight between FIXED and FIT but almost never changed final Top2. We now condition the actual C21/C42/C63 weights on context, and separately test an objective closer to the selection of two opportunities. No forced disagreement or post-result rescue tuning. No claim of optimality, causal regime identification or more independent dates from ticker pairs.

## Frozen inputs and questions
Use authenticated OLC15 checkpoint (SHA256 5f04b1f3cd9573d1122fb2d9f2e950c15fbe5b7a4d8c34f70e218c388a31b50f) and OLC14 results (4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1). No new prices or base ETF fits. z=(C21,C42,C63) are OLC14 mean-three-seed forecasts, NOT future ranks. Native target remains U42, discounted incremental log returns with weights1,sqrt(.5),.5 normalized. All future outcomes used only after the entire query group has matured. Forecast eligibility is never conditioned on future outcomes.

Context is limited, predeclared: trend126, log(vol21/vol126), leadership from OLC15. Local SPY/EXSA.DE context, not a complete cross-asset regime. Efficiency/drawdown remain diagnostics, not additional fitting variables. Missing context is imputed using training-date medians; weighted mean/std are fit per query, each market total weight .5. Clip standardized features to[-3,3]. No USA close supplied to earlier EU decisions.

## Parametric curve
beta(x)=softmax(log(PRIOR)+(a1,a2,0)+(B1*x,B2*x,0)), PRIOR=(.45,.35,.20). Score=z@beta. Alpha is fixed1 here and does not replace the1.5 target exponent of the frozen base models. A static control has B=0; its intercepts are fitted using exactly the same objective/data. All fitted coefficients shared by markets, monthly local context can change beta. Each of two intercepts and six slopes bounded[-5,5]. L2 intercept penalty .05, slope penalty chosen from(.01,.1,1). No requirement that long/short always dominates in a named regime.

## Fixed 2x2 objective/context design
PAIR_STATIC,PAIR_CONTEXT: weighted logistic pairwise ranking as OLC14 (margin multiplier5, top-quintile-involving pairs, economic-gap weights capped3*IQR). Equal query-date weighting within each market.
TOP2_STATIC,TOP2_CONTEXT: maximize differentiable capped-entropic allocation utility. Training-only soft weights w_i>=0,sum(w)=1,w_i<=.5 maximize w@score-T*sum(w log w), T=.05 fixed. At most one cap binds at finite T; others share remaining mass by softmax. This is a smooth surrogate, NOT literal discrete Top2, NOT the live capital allocation. Training utilities are centered by their query median, scaled by IQR and clipped[-3,3]; actual discrete selections are evaluated on unmodified U and returns. Penalization as above. This tests task alignment, not CAGR optimization.

Optimization: L-BFGS-B, analytic gradients checked numerically, three deterministic initializations: intercept(0,0),(.5,-.5),(-.5,.5),slopes0. Select lowest TRAINING objective; all starts logged. No initialization selected using future payoffs. Preserve diagnostics and handle nonconvergence explicitly, no silently accepted failed fit.

## Time contract and selection
Annual fit2021–2026;2019–2020 use PRIOR. Minimum18 fully mature queries per market for outer adaptation. Inner temporal CV last2 eligible calendar years; train needs8 mature queries per market, validation4, all validation outcomes available before outer cutoff. Select slope penalty using mean(EU,USA) Top2-U excess minus.25*abs(EU-USA), tie chooses stronger shrinkage. If no valid inner fold use .1. Static model has no slope penalty search. Fit scalers inside each fold. No cross-market future labels, no random row splits, no adaptive update before outcomes mature.

## Controls and evaluation
Immutable ORIGINAL,CUM_FIXED,CUM_FIT plus the four new variants. Two predeclared delayed-context variants apply PAIR_CONTEXT/TOP2_CONTEXT using previous monthly signal context, no extra fit. New current scores monotonically mapped to the contemporaneous fixed-score distribution, preserving ranks, then unchanged memory40/30/30,power1.1,Return/Hybrid47.5/52.5. Changes in mapping are not hidden alpha.

Native endpoints common to all: actual Top2 U excess/regret, returns21/42/63 and increments21–42/42–63, bottom-quintile selections, ranking to original target only as ancillary. Report CURRENT,SMOOTH,FUSION, decision overlap and distance to Top2 switching boundaries. Main2021–2024 with all63 outcomes mature before2025; separate all48-signals coverage with later outcomes;2025,2026partial,full. No relabeling partially observed dates as failures.

Portfolio: all9variants x2markets x3policies x2costs=108 FULL replays;9x2x2=36 IMMEDIATE lagged-systemic sensitivity. Total144 paths including48 parent controls. Costs .001/.003 retain legacy half-L1 convention. Fixed nominal50/50, unchanged risk/stop/V6 streams and inherited same-open limits. Reconstruct actual selections and ledger, not averages of old NAV curves. Native task first; portfolio benefit can be complementary but does not prove native skill.

Negative controls: for each contextual objective, two seeds1601/1602 permute training contexts across dates WITHIN each market and training cutoff, refit using its selected penalty; predict real chronological test contexts. No outer tuning of null runs. Keep native diagnostics for all null models; no selection among them. This is a finite diagnostic, not calibrated evidence of universal significance.

Inference: paired month-level circular blocks6,4000draws,seed20261102; common calendar, effective query count stated. Zero-containing intervals are not automatic rejection; bootstrap positive fractions are not posterior success probabilities. History repeatedly inspected; no virgin holdout claim. No promotion from only one market or window.

## Implementation and persistence plan
1. Verify parent hashes/manifests; audit forecast/context keys and maturity; run inherited suites in their project roots.
2. Write failing synthetic tests for capped weights, finite-difference gradients, simplex, query weights, cutoff, training-only scaler, missing inputs, and static/context equivalence. Implement small focused modules and run tests.
3. Authenticate48 original paths; save input/schema checkpoint. Train annual models with all CV/start records; save each complete annual model before further work.
4. Evaluate native tasks,144 accounts and null/context-lag diagnostics. Independent metric/accounting recomputation; future-perturbation invariance and reload predictions.
5. Preserve tested sources, concise results and checkpoint hashes on this research branch at concrete milestones. Full binary checkpoint in persistent Library and downloadable artifact; do not imply GitHub asset upload unless performed and verified. Restore in clean directory. Self-review is not independent external review. No background work promise.
