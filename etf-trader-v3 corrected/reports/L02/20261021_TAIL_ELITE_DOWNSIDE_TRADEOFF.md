# V3 L02/03 — Independent bottom-decile risk head alongside frozen Tail winner classifier

**Completed:** 21 October 2026. **Decision:** reject unconditional `winner − risk` ranking fusion. **Preserve the risk head separately for L06 diagnostics** and lock the elite logistic Tail as the L02 upper-winner specialist.

## Evidence

- [Successful Actions run 39657701155](https://github.com/AM1975MA/Test/actions/runs/39657701155), complete artifact **12370754300**, 3 training shards and fully matched OOS scores.
- Source frozen 149-ETF OHLCV run 39482809691; 500 canonical overlapping 24-member baskets, 2018–2026 historical data **previously interrogated** (not a new unseen holdout).
- Elite/winner model **not retrained**: exact `TAIL_EVENT_LOGIT45` scores from successful run 39655513813 (98 months of fully mature 63-trading-day Tail labels).
- Added **one** bottom-event model, `LogisticRegression(C=.2,class_weight=None)`, with the same 45 Tail inputs and 63D maturity cutoff. Target: future bottom 10% on cross-sectional 21-trading-day ETF returns.
- The only ranking addition, registered *before* examining OOS results: `score = same_date_pct_rank(p_elite) − 0.25 × same_date_pct_rank(p_bad)`. No parameter search, CAGR, compact refit, macro, allocation, or global risk overlay.

## Functional accuracy: Tail recognition vs safety

| Metric | Frozen elite model | Elite−0.25×bottom risk | Delta |
|---|---:|---:|---:|
| Top-decile Tail Average Precision | **0.288357** | 0.265920 | −0.022436, 95% CI [−0.032593,−0.012666] |
| Top-decile Tail ROC AUC | **0.744162** | 0.726754 | −0.017408, CI [−0.022078,−0.013009] |
| Elite recall in Top-15 ETF scores | **26.939%** | 25.034% | −1.905 pp, CI [−3.061,−0.884] pp |
| Basket best-Tail winner Top-3 capture | **39.798%** | 35.871% | −3.927 pp, CI [−4.953,−2.924] pp |
| Bottom-decile ETF false selections | 28.020% | **24.622%** | **−3.398 pp**, CI [−4.973,−1.775] pp |
| Tail rank target regret | **0.475278** | 0.492925 | +0.017648, CI [+0.006115,+0.030139] |

Risk head independently, evaluated on 101 months with matured 21D outcome:
- `P(bottom10%)` out-of-sample Average Precision **0.289746** vs **0.093960** base rate;
- ROC AUC **0.755226**;
- Brier **0.079972**; a Brier value by itself is NOT enough to claim calibration.

These results support **two different tasks** with distinct error trade-offs rather than indiscriminate subtraction of one score from the other.

## Layer decisions

1. L02 winner specialist candidate: **LOCK `TAIL_EVENT_LOGIT45`** for independent next-layer diagnostics. It is better than original Ridge on upper-event AP, recall and Top-3. Note it selects more short-term losers if left unchecked.
2. L02 risk subtraction: **REJECT `TAIL_ELITE_BAD25`** as the upper-tail ranking solution. It sacrifices almost all of the demonstrated winner Top-3 uplift to lower bad picks.
3. Store the independent `P(bottom decile)` head as **research-only L06 risk signal**, not an automatic additive correction of L02. On L06 use risk-event PR-AUC, calibrated risk by train-only correction, false-positive rate, true loss recall, downside/CVaR (NOT a CAGR optimization).
4. L01 remains **CORRECTED125 + pairwise 127 leaves**, frozen. All research continues on the same 149 ETFs and 500 baskets; no V2 production switch.
5. The follow-on L03 regime should show whether it predicts **relative expert skill** with only known-at-signal market variables and matured expert outcomes, not by reading which expert won a future year.

## Statistical scope

98 matched mature Tail months; 6-month paired circular block bootstrap, 6,000 draws. Because the 500 baskets heavily overlap, they are first averaged by calendar month, not counted as 500 independent experiments. Significant paired changes in a repeatedly examined historical period are **exploratory**, not independent post-selection validation.
