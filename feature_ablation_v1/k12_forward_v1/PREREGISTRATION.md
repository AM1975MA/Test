# COMPACT21 K12 conditional forward ablation V1 — preregistration

## Question

The previous frozen benchmark found a clear trade-off:

- **K12** reaches the stability target (Rank-MAD improvement 26.19%) but loses too much realized Top5 overlap.
- **K16** restores realized Top5 overlap to BASE level but gives back too much stability.

K16 differs from K12 by exactly four features:

1. `autocorr1_63` (A)
2. `efficiency21_dev` (E)
3. `skew63_dev` (S)
4. `mom10_dev` (M)

This experiment exhaustively tests every non-empty proper subset of those four additions, plus frozen K12 and K16 controls. No other feature is eligible.

## Frozen candidate matrix

- K12_CONTROL
- K13_A, K13_E, K13_S, K13_M
- K14_AE, K14_AS, K14_AM, K14_ES, K14_EM, K14_SM
- K15_AES, K15_AEM, K15_ASM, K15_ESM
- K16_CONTROL

Feature order is frozen as K12 followed by A, E, S, M in that order when present.

## Model and data

- unchanged canonical Compact21 XGBoost ranker
- unchanged seeds, rounds and hyperparameters
- frozen three `TI_COMPACT.parquet` snapshots from Actions run `37150436612`
- unchanged yearly folds 2017-2026
- unchanged maturity rules, inference alignment and quality metrics
- no strategy CAGR, P&L, Sharpe, MaxDD or execution metric enters candidate selection

## Frozen acceptance gate

A non-control candidate advances only if all conditions hold versus BASE125 from run `37525303093`:

- Rank-MAD improvement >= **25%**
- stability Spearman no worse than BASE
- Top1 disagreement no worse than BASE
- NDCG@5 >= **95%** of BASE
- realized Top5 overlap >= **95%** of BASE
- maturity PASS
- deterministic repeated fit PASS

K12_CONTROL and K16_CONTROL must reproduce the already frozen parent-run metrics within absolute tolerance `1e-12`; otherwise the experiment is invalid.

If more than one candidate advances, the primary candidate is the one with the **lowest Rank-MAD**; ties are broken by higher realized Top5 overlap, then fewer features.

## Interpretation constraint

This is a conditional second-stage experiment motivated by the already observed K12/K16 2017-2026 results. Therefore any winner is a **research candidate, not production adoption**. It must subsequently be confirmed on an independent/future validation slice before changing production or the standing negative feedback.

No gate or candidate list may be changed after candidate results are observed.
