# STEP07A post-mortem and admissible next direction — 2026-08-31

## What STEP07A falsified
The clean low-dimensional architecture “adaptive local scale + next-session competing crash/recovery hazards + monotone exposure map” is development-rejected. The rejection is not driven by costs or poor hazard discrimination.

Primary LOCAL_PLUS_REGIME, 2021–2022 versus frozen FUSION1:
- ΔCAGR -0.4314 pp
- Δmean MaxDD -0.4109 pp
- Δp10 MaxDD -0.4825 pp
- mean gross 99.44%
- crash-next AUC 0.9726
- recovery-next AUC 0.8629

The central lesson is target mismatch: endpoint proximity is highly predictable, yet de-risking on that information destroys economic value. Predicting “crash soon vs recover soon” is not equivalent to predicting the counterfactual value of reducing exposure now.

## What is NOT falsified
Exact ticker-normalized information is not fully falsified. STEP07A used the exact frozen HGB portfolio path as its adaptive scale because held-ticker identity was not embedded in the DD-guard path archive used at preregistration.

After the frozen STEP07A run, a self-contained historical notebook was recovered that embeds the full OHLCV matrices and reconstructs monthly basket leader/satellite identities. The frozen `STATE_PANEL.csv` and `TREATMENT_VALUE_SELECTED_DECISIONS.csv` are also available. This makes a separate exact-ticker audit technically feasible without web data.

This discovery must not be used to retune STEP07A. Any use is a separately preregistered STEP07B.

## Recommended STEP07B if research continues
Do not fit another crash/recovery hazard. Use exact ticker/local-normalized features but learn direct causal action value of each exposure decision.

At each daily stressed state, define a small fixed action set, e.g. gross exposure {100%, 70%, 40%, 0%}, and compute frozen forward counterfactual utility over a fixed horizon from the exact HGB path / component path, pricing both return loss and drawdown avoided. Train a low-capacity model on 2017–2020 and evaluate policy value on 2021–2022 only.

Primary scientific question: does ticker-normalized state explain which exposure level has positive counterfactual value, not whether a normalized barrier will be hit?

A materially strict gate should remain in force; no 2023+ opening for incremental improvements of the STEP06R magnitude.

## Stop rule
If exact-ticker-normalized direct action value also fails to improve FUSION1 by a clearly material amount on development, stop DD-controller research on the current historical information set. At that point, further gains would require a genuinely new source family (structural medium-term breadth, credit/option state, or similar), not controller tuning.
