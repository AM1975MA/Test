# R0-O — PRE-TRAINING frozen native pair-sampling confirmation protocol
**2026-10-09 | Superpowers × Data | isolated synthetic validation only | no ETF fitting/backtest**

## Hypothesis
A single native XGBoost parameter `lambdarank_num_pair_per_sample=5` can reduce sensitivity of annual-style `rank:pairwise` training to small training X and one rank-changing Y perturbation, without materially reducing the broader ranking quality or extreme-positive winner capture. This is motivated by exploratory R0-N and **tests a hard new synthetic instance**, rather than retuning a value after seeing R0-N data.

## Locked experiment BEFORE inspecting results

- **New world** `B` (hard/noisy nonlinear R0-M mathematical fixture), new RNG **20261213**, unseen in R0-M/N. Exactly 32 monthly-like groups ×32 training candidates, 125 features.
- **Independent held-eval**: concatenate independent held-out eval sets from `generate_world(20261213,'B')`, `generate_world(20261214,'B')`, `generate_world(20261215,'B')`; 3×20=**60 groups ×32 candidates**. No ETF data or markets in test.
- Same exact training X, y/groups, feature order and eval X for both policies. Training scenarios: `baseline`, `X_only` (same 2.5×10^-6 feature-scale jitter as R0-N, fixed RNG seed worldseed xor 0xABCDEF) and `Y_only` (same rank-reversing middle pair constructor, exactly 2 grade rows change, one strict pair inversion, true return gap below 20bp). No second loss/regularizer.
- Native `rank:pairwise`, 360 boosting rounds, tree_method hist, max_depth4, eta=.035, subsample=.85, colsample_bytree=.8, min_child_weight=8, lambda8, alpha.1, XGB 3.1.3, seeds **101,202,303**; nthread=1, exactly **2 policies ×3 scenarios ×3 seeds =18 new synthetic fits**.
- **ONLY difference in model parameters**: `lambdarank_num_pair_per_sample` default vs 5, `lambdarank_pair_method='topk'` otherwise unchanged. Verify actual serialized training config.
- Persist all 18 prediction arrays, source dataset hash and manifest SHA256, and independent per-group synthetic "truth", so independent Data can audit without retraining.

## Prespecified success/stop gate — no post-hoc tuning

Report per policy, with three-seed-mean scores: baseline Top1-in-latent-realized Top5 hits out of 60, exact winner hits, NDCG@5 across 60 held groups, mean selected artificial outcome and oracle regret; stability Top1 agreement / Top5 overlap / rank-MAD for X-only and Y-only; number of changed selected candidates and per-changed-group payoff impact. Use paired **group** bootstrap 5,000 samples seed 20261009, report uncertainty and no inferential market claims.

A narrowly defined **continue-to-research gate** requires ALL:
1. `topk5` Top1-in-true-Top5 hit count **≥ default**;
2. mean synthetic selected return **≥ default**;
3. stability agreement `X_only` and `Y_only` both **≥ default**;
4. full-ranking mean NDCG@5 **≥ default −0.01**.
If any fail => **NO GO for this single topk5 candidate**; do NOT sweep 2,3,10 or choose a new training round/leaf structure from these data. The NDCG margin is an engineering diagnostic guard only, not a statistically validated financial loss budget.

No full-V2 performance claims even if all gates pass; next steps would still require novel point-in-time ETF data, source model/MA3 artifacts, a fixed future cutoff and an approved prospective full engine comparison. This test is independent **synthetic** only, not independent market validation. Do not alter `Etf_trader` or `Trader_selector`.

## Evidence provenance
R0-M and R0-N local bundles were supplied in this conversation, SHA-verified independently; R0-N 36 per-seed predictions across 2 worlds/2 policies/3 scenarios/3 seeds. R0-N showed topk5 recovered 2/20 Top5 hits in world B but degraded NDCG@5 ~0.025; hence this **new** 60-group B fixture is deliberately an adversarial confirmation with the above complete gate defined now.
