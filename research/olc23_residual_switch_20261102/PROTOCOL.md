# OLC23 — chronological differential residual-value switch model

2 November 2026. Registered after OLC22 showed that unconditional target hysteresis is harmful. Exploratory reused-history block, not an independent holdout. Parent OLC22 31630be990982847940c2863a32f3275c5376006. AUTH ranking, predictors, context, 50/50 sizing, V6, stop barrier, cooldown and risk contracts remain frozen.

## Objective
Do not keep a prior target merely because it was held. When AUTH wants to replace a previous proposed target, estimate whether keeping that outgoing ticker for the next 21-day horizon has positive residual economic value versus the incoming AUTH candidate. The model can veto a replacement; it cannot introduce a ticker outside the union of previous targets and current AUTH Top2.

This still uses the previous proposed pair, not the exact post-stop holdings. It is a controlled residual-target experiment, not full order-state optimization.

## Event construction
For each market and signal transition under frozen AUTH:
- previous pair P, current AUTH Top2 B;
- outgoing O=P\B and incoming I=B\P;
- when |O|=|I|=1, one comparison;
- when both slots change, train on all O×I comparisons with per-event weights so a two-by-two event does not receive four times the total weight.
The observed structure contains approximately 122 outgoing EU slots and 137 USA slots over 89 transitions; these counts are label-blind.

A training comparison is admissible only when both tickers have finite fwd_ret_21 and both exit_date_21 values are strictly earlier than the annual training cutoff.

## Fixed target
For a pair (outgoing o, incoming i):
Y = log(1+r21_o) - log(1+r21_i) + 0.0005.
The +0.0005 is the approximate saved base-fee cost of not swapping one 50% slot under fee .001 (half-L1 turnover convention). The decision model is trained once per year and is unchanged under the .003 cost-stress replay.

## Fixed features available at the signal
All differences are incoming minus outgoing unless stated:
1. AUTH FUSION gap;
2. RETURN gap;
3. C21 gap;
4. C42 gap;
5. C63 gap;
6. I42 gap;
7. I63 gap;
8. outgoing AUTH FUSION level;
9. incoming AUTH FUSION level;
10. outgoing target age in monthly signals.

No future return, exit status, stop outcome, market-specific dummy or realized portfolio metric is a feature.

## Model and chronology
One pooled EU/USA weighted ridge regression per calendar year 2021..2026. Standardization is fitted on training rows only. Each market receives total regression weight 0.5, and each replacement event has equal weight within market.

Ridge lambda grid is fixed at {0.1,1,10}. Select lambda using chronological validation on at most the last two eligible calendar years: train on earlier admissible events, validate on that year, minimize the mean of EU and USA weighted MSE. Tie-break toward larger lambda. If no valid fold exists, lambda=1. Refit on all admissible events before the cutoff.

For each two-slot replacement, evaluate the two possible outgoing↔incoming matchings and use the matching with largest summed predicted keep advantage. Keep each outgoing only when its matched predicted Y > 0; otherwise accept the AUTH incoming ticker. No threshold optimization.

## Portfolio replay
Candidate-specific V6. Same OLC20/OLC19 ALARM and FAST_LOCK3, fees .001/.003, stop friction .001 and accounting. Margin0/AUTH is the exact control.

Primary: ACTIVE2021_2024 fee .001. A common improvement requires higher CAGR than AUTH in BOTH EU and USA under the same risk contract. Rank by the smaller CAGR delta. Secondary: fee .003, FULL history, yearly results, MaxDD, CVaR, turnover, number of vetoed replacements and realized ex-post keep-vs-switch differential.

## Verification
- annual training rows all mature strictly before cutoff;
- future-outcome perturbation cannot alter earlier model/decision;
- balanced market/event weights sum as specified;
- lambda selection uses only prior chronological folds;
- zero predicted advantage never keeps by tie;
- no candidate outside previous pair/current AUTH Top2;
- exact AUTH parity when model veto is disabled;
- V6 non-overlap and independent return reconstruction.

## Limits
The model is deliberately small but is still selected after extensive prior research. Historical improvement would be a challenger, not prospective proof. r21 labels, prices, quote masks and actual fills retain upstream limitations.
