# EU120 frozen 2×2×2 allocation ablation, separately for Hybrid-only and ReturnRank+Hybrid
Preregistered 2026-10-17, before viewing any outputs. Research-only; **no production change**; no model fitting or parameter search.

## Question
After EU120 refitting (GitHub run 39064123941) and pair/weight crossover (run 39065982541), is historical efficacy attributable to (i) rank-margin to initial first-ETF weight mapping, (ii) original margin threshold allowing an override to weight1=1, or (iii) agreement between ExtraTrees and XGB Tail when market gross risk < 1?

Exactly two **unchanged selected ETF pair** policies H=Hybrid Tail alone and R=Return-NDCG+Hybrid, with fixed original frozen 2017–2026 EU120 120-ticker monthly scores, 112 common-open completed signals, 2432 same daily sessions. Original refs SPY HYG IEF BIL SHV solely contextual. 80 original annual EU120 fits are frozen and **not** refitted.

## Factorial
For each of H and R, eight combinations of:
1. `weight_mode`: `D` original continuous producer first-ETF base weight `0.60+0.40 min(margin/0.13,1)^2`; or `F` strictly 0.50. In all arms the same pair d1/d2 from the corresponding frozen policy.
2. `margin_gate`: `1` original TOP1_MARGIN from selected score; or `0` replace margin by zero **after** initial producer weight calculation. This only disables confidence boost (does not reset original dynamic first weight if weight_mode D).
3. `agreement`: `1` original ET/XGB ordering agreement for chosen ETF pair; or `0` report original agreement but supply false to original `conf_weights`. This specifically disables risk-off boost, not the risk-on margin override.

Names: `H_D_M1_A1` canonical Hybrid-only, `R_D_M1_A1` canonical R+Hybrid; other 14 explanatory arms. `F_M0_A1` fixed first-weight no margin must reproduce prior published six-arm `H_HALF` / `R_HALF` arrays exactly. `F_M0_A0` must produce same output as `F_M0_A1`; `D_M0_A0` same as `D_M0_A1`, because without a margin gate the agreement vote cannot promote first-ETF weight. These are preregistered negative-control equalities.

Original downstream **unaltered** EU120 common-open audited execution `replay_audited.replay`: original market `risk_transform`, score-to-ETF pair, model agreement as-of score, `conf_weights`, V6 (built from modified *raw* base first weight), 10bp fee, actual observed common-open trading, stop/cash rules, no mix of vintage periods. Scoped method wrappers must always restore original functions. Output daily post-confidence first weights and pre-confidence weight/margin, sampled agreement and trigger counts; no future returns used for score or intervention.

## Fail-closed gates and metrics
- Frozen 120 EU120 names match exact manifest; original training hashes and maturity audited for 2017–2026; score dates exact 112×120; all 16 same 2432 execution sessions.
- Original `H_D_M1_A1` and `R_D_M1_A1` compare `dates`, `equity`, `turnover` arrays against run 39064123941 exact 1e-12; independently recompute original strategy CAGR, max drawdown, Sharpe and terminal equity from saved daily equity path. Compare `F_M0_A1` against prior 6-arm H_HALF and R_HALF from run 39065982541.
- Same d1/d2 within H and within R for all eight gate arms, and from source score; same daily calendar among all 16. Verify 0 marginal effect of agreement in M0 arms. Report trigger frequencies separately for risk-on (unconditional margin) and risk-off (margin and agreement required), and **count actual post-risk weights**.
- Eight-way factorial per selector for mean market history CAGR, maxDD, Sharpe, turnover and per-year returns; report paired M/A/W effects *conditional on other fixed gates*, do not claim individual causal contribution where the V6 risk policy also reacts to raw weight1. Report source 2026 as a partial year.
- These are interventions to explain already examined historical outcomes, not independent prospective evidence. Original EU120 universe was chosen ex post using data through July 2026; no production promotion.
