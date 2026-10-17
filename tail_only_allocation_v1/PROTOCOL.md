# Frozen Tail-only and position/risk mediation study — 2026-10-17
Research branch `research/tail-only-and-allocation-ablation-20261017`, AM1975MA/Test; **DO NOT MERGE; 0 new model fits**.

## Main question
Does the MA3 Tail Hybrid score, without either original Compact21 BASE or RETURN_RANK_NDCG and without Titanium Ridge Tail, perform well? Is the previously observed RETURN_RANK_NDCG + MA3 Hybrid (Titanium Ridge Tail OFF) 39.33% retrospective mean CAGR attributable to ETF selection rather than position sizing or path-dependent risk?

## Original immutable inputs and outcomes
Source original149 frozen market input 3 correlated Yahoo revisions, 114 monthly signals (113 mature 21-session), 2366 daily replay observations, Oct 2026 historical replay end. Original unchanged models from certified run 39031200131 and 8-arm original results run 39058118631. Exact original full daily score/portfolio all-on control and `R_T0_H1` source paths are read from certified archive; no scoring model retraining and no input reconstruction. Exact model columns ET_TAIL, XGB_TAIL and Titanium are from original annual OOS canonical forecasts. Verify original SHA and all source calibration input parity, historical dates, source keys and immutable baseline in any simulation.

## Registered isolated scoring arms
For Tail-only (no Compact BASE or Return-Rank and no Titanium Ridge Tail) take frozen monthly cross-sectional 149-ETF ET_TAIL and XGB_TAIL ranks and form:
- `H_ONLY`: H(t)=.6 ET_TAIL(t)+.4 XGB_TAIL(t), smooth .4 H(t)+.3 H(t−1)+.3 H(t−2), score=clip(smooth,0,1)^1.10; NO .475 Titanium component and NO Compact forecast channel. Keep all portfolio risk and existing model-agreement vote active (MA3 remains enabled).
- `ET_ONLY` and `XGB_ONLY`: same .4/.3/.3 lag smoothing and ^1.10 transformation, using only ET_TAIL or only XGB_TAIL respectively; model-agreement vote is **disabled** as a pairwise ET/XGB agreement does not exist when only one learner is active (package ablation). This is extra diagnostic, not a weight sweep.
- `RIDGE_TAIL_ONLY`: score = within-date rank of original annual trained Titanium Ridge Tail `tail` column (no Compact21 and no Macro bonus), no MA3 model agreement vote. The Ridge Tail historical OOS scores are sourced from the frozen annual evidence, not trained anew.
- Reference `R_T0_H1` = 47.5% Return-Rank-only Titanium percentile + 52.5% MA3 Hybrid, all original V2 risk unchanged. Full same-source replay MUST reproduce the archived source paths from run 39058118631 bit-identically up to 1e-12 before any conclusions. No new weights tuned. References `B_T0_H1`, `R_T1_H1`, `B_T1_H1` from prior 8-arm audit stay unchanged.

## Selection/weight counterfactuals
Use two original score-generating policies `H_ONLY` and `R_T0_H1`. For each vintage compute both sets of *daily* allocations from the same canonical `producer.allocations_from_score`, including top1/top2, base `weight1` and `margin`. Four **hybrid replay policies**:
- S=H, W=H (original H_ONLY)
- S=R, W=R (original R_T0_H1)
- S=H, W=R (Tail-only selected ETF pair, Return-Rank+Hybrid weight1 and margin schedule)
- S=R, W=H (Return-Rank+Hybrid selected ETF pair, Tail-only weight1 and margin schedule)

Apply paired S/W arrays to original **unchanged daily canonical V2 simulator** (via scoped allocation interception), recompute V6 alternative state from combined S and W at that date, recompute ET/XGB agreement using selected pair, keep all raw prices, risk caps, stop, costs, slippage, cash, calendar identical. To isolate dynamic weights further, for each S policy also run W=0.5 constant with margin=0, keeping original gross risk controller/stop/V6, total 2 more policies. This is a **counterfactual intervention on allocation fields**, not a causal statement about the origin of alpha; W borrowed from the other signal is not a learned independently optimal policy and margin/confidence are bundled. The complete 2×2 plus fixed 50/50 controls must reproduce exact S=H/W=H and S=R/W=R paths of the corresponding standalone original canonical replays.

Also run independent **risk-neutral 50/50 monthly top-two** comparator (source open-to-open with ten basis points turnover fee) for H_ONLY and R_T0_H1: no V2 risk overlays. It is a separate benchmark and must not be described as exact V2 PnL.

## Evaluation, no tuning
Per vintage and aggregate: CAGR, MaxDD, Sharpe, terminal equity, mean turnover, cross-source CAGR span, original daily Top1 agreement, daily Top2 switches, absolute weight deltas, years 2021/2023/2024/2025; pure monthly Top1 21-session realized return, regret vs top decile, actual top5 hit, Top5 overlap; source and model attribution; fixed 50/50 comparator. Independent equity path recalc to 1e-12; all support 149 tickers ×114 signals × 2366 sessions; all archived R_T0_H1 full replay arrays must pass parity. If any inconsistency or missing signal, fail closed.

The same 2017–2026 markets have been heavily researched. Three Yahoo vintages are correlated and do not constitute independent validation. This is a mechanism audit; keep PR draft and no production promotion.
