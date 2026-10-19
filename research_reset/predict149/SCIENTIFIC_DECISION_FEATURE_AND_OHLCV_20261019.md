# ETF149 — Features vs raw, loss functions, and OHLCV: closed predictor research verdict
19 October 2026 | branch `research/149-ohlcv-microstructure-predict-20261019`

## Question answered
The original best-ticker N4 HGB classifier was **NOT trained on raw bars alone**. It used 19 engineered close-price features (5/21/63/126 returns; 21/63/126 volatility; downside volatility; drawdowns; SPY beta; group-relative returns; group momentum; volatility shock; acceleration; within-group return percentile; scaled momentum/risk ratio) and 6 category indicators. **Open, High, Low, Volume** information was mostly omitted. All information still relied on retrospectively adjusted Yahoo 149-U.S.-ETF history.

We tested data representation and mathematical objective, **not** invented P&L tuning:
- T149-D: Actions https://github.com/AM1975MA/Test/actions/runs/39213544830 success. Six arms (original N4 plus five). 64 anchors 2021–26, 9,536 ticker signals, no future training targets, exact old N4 economy parity. Raw63 daily close changes + classes, 25 engineered, 40 engineered plus cross-sectional ranks, supervised LambdaRank directly targeting best future 5/15/30, and signed upside/downside two-head learner. Code `research_reset/predict149/feature_objective/run.py`; all predictions, 64-by-model metrics, costed equity and SHA under `results/`.
- T149-E: Actions https://github.com/AM1975MA/Test/actions/runs/39214487871 success. Four **real OHLCV** challengers plus N4. 21 daily five-field normalized raw OHLCV bars (105 numeric +6 classes), 19+21 explicitly predeclared volume/volatility/gap/intraday engineered with six class controls (46 total), same engineered data with ExtraTrees, and logistic reg. Chronological as-of/no-future mutation tests passed, archived N4 equity matched. Code `research_reset/predict149/ohlcv/run.py`; results and hash in `results/`.

All experiments were **preregistered before execution**, but after seeing heavy use of the **same** 2017–26 original149 survivor universe: no untouched future holdout or independent discovery. Fatal selection bias/multiplicity risk persists. Dataset does not establish EUR investor tradability.

## Headline numbers
All are shadow fully-invested equal dollar top5 21-session rebalances and nominal 10bp each trade side, period 2021–2026. SHARPE etc in raw results. Precision@10 = fraction of predicted top10 that is actually future top15 of 149 after 21 sessions.

| Model | Precision@10 | mean monthly cross-section Spearman | Net shadow CAGR | Daily-open MaxDD |
|---|---:|---:|---:|---:|
| N4 prior HGB 19+6 engineered close-price | 24.53% | −0.0165 | **16.70%** | −34.01% |
| D1 last63 daily raw close returns LightGBM | 23.59% | −0.0119 | 2.38% | −34.63% |
| D2 19+6 engineered LightGBM | 24.22% | −0.0162 | 13.26% | −30.47% |
| D3 engineered +15 cross-sectional ranks LightGBM | 24.84% | −0.0184 | 2.14% | −38.22% |
| D4 graded future winner LambdaRank direct listwise | 23.75% | −0.0128 | 9.42% | −44.92% |
| D5 signed two-tail LightGBM | 16.72% | +0.0224 | 7.88% | −29.17% |
| O1 actual 21 daily OHLCV bars LightGBM | 24.69% | −0.0009 | 6.08% | −35.26% |
| O2 previous 25 + 21 OHLCV engineered LightGBM | **25.63%** | −0.0149 | 1.98% | −42.33% |
| O3 same feature set ExtraTrees | 23.13% | −0.0103 | 5.40% | −53.93% |
| O4 same feature set logit linear | 25.31% | −0.0208 | −1.41% | −47.23% |

All 5 new objective/feature arms D1-D5 and all four true OHLCV arms O1-O4 **FAILED** their preregistered aggregate incremental predictive gates. In O1 the paired Spearman improvement confidence range versus N4 is [+0.00171,+0.02947] yet its absolute mean Spearman remains close to ZERO, selected downside share higher than N4, and 6.08% CAGR worse than passive: **better global correlation does not imply better signed top5 selection**. O2 Precision@10 +1.10 pp over N4 but top5 captures only 12 (vs 19) historical single best winners and cuts historical CAGR to 1.98%. These are not model improvements even if local ranking statistic rises.

## CRITICAL risk-only placebo already evaluated on same original149
Earlier `research_reset/predict149/conditional_validation/results/RESULT.json`:
- N4 HGB future Top15: precision10 **24.53%**, 19/64 next top absolute ETF hits, 16.70% CAGR, −34.01% DD.
- **N7 VOL_ONLY_RANK**: precision10 **29.69%**, **also 19/64 absolute hits**, but only **6.14% CAGR**, −36.36% DD.
- N6 category+volatility calibrated future Top15: precision10 **29.53%**, **also 19/64** hits, 11.10% CAGR, −36.17% DD.
- Both risk-only comparators FAIL their economic superiority gates. N4 Brier .085595, N6 Brier .085789, event prior .090536, but their differences not significant vs one another in 64 anchor block CI.

**Interpretation:** predicting which ETF could have an extreme positive return in an entire set is easily confounded with high volatility, which also produces extreme negative outcomes. Conditional hit-rate is NOT a calibrated forecast of signed future alpha. Cross-sectional mean Spearman of N4 is negative despite top15 Precision10 better than uniform 10.07%. The emphasis needs to shift from classifier type to whether REAL conditional future excess *direction and magnitude* can be predicted after exposure/maturity/transaction costs, while managing rare left-tail outcomes.

## Scientific stop decision and responsible continuation
This is **NOT** a victory by adding more features, and results nowhere near a verifiable 30% CAGR. Repeating dozens more LightGBM/NN parameter trials on this same 2021–26 historical target would be p-hacking. Preserve all failures and simple N4 as baseline only.

Mandatory next research paths, NOT CLAIMED EXECUTED:
1. Independently validate 149 tickers against properly timestamped 2026-07 onward next-Open prices, or acquire separate delisted/PIT ETF historical membership with as-of market/FX and executable bid/ask; older series repeatedly mined must NOT be called an untouched holdout.
2. Source truly different economic information (liquidity/order flow, term curve/credit stress, event timestamps, fund underlying and futures roll) with actual vintage, not inferred from future prices. Past VIX/CBOE feature studies alone showed mixed/inferior skill.
3. Distinguish `E[r_i−benchmark | F_t]`, downside conditional risk, and conditional expected value of **holding vs rotating**. Evaluate 5/21/63 horizons with frozen proper scoring and multiple-testing control, but do not select historical winners by ex-post CAGR.
4. Validate prediction horizon vs market regime separately with no posterior selection, 10bp nominal spread not equal live broker execution. Multi-head classification may improve maxDD historically, but no statistically proven incremental signed edge.
5. Real goal 30%+ net annual CAGR with controlled drawdown is aspirational, extraordinary and **not demonstrated by any current model**. Stop deployment until real prospective evidence.

## Conclusion
Not having enough informative independent covariates is the strongest current limitation. Original engineered features vs raw Close vs actual OHLCV vs factor rankings vs LambdaRank all fail robust incremental predictive gate. *Do not declare "best model" merely by retrospective CAGR or 1pp Precision@10*. The next scientific step is new causal information plus untouched validation, not recursively combining failed forecasters on the same 149.
