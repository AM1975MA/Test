# T149-F — Predict SIGNED economic value, not absolute extremes (preregistered)
19 October 2026. Research-only branch `research/149-signed-value-predictor-20261019`. EXACT frozen original 149 US ETFs, immutable source manifest. Previous repeated experiments contaminate the 2017–26 corpus, so this is **exploratory falsification**, not prospective or production alpha. Stop choosing/adjusting model on realized CAGR.

## Central hypothesis
The best 21-session future ETF is NOT necessarily the one most likely to have an extreme absolute move. To identify positive economically relevant movements, explicitly model the **signed future benchmark-relative log return** `Y_i,t=log(Open_i[t+21]/Open_i[t])−log(.6*SPY_open_ratio+.4*AGG_open_ratio)`, and its conditional distribution. Large future winners with high simultaneous downside risk are NOT rewarded by directionally symmetric ranker. The benchmark is a USD shadow proxy, not EUR investable 60/40.

Frozen 112 blocks of 21 sessions, first 48 for initial training and last **64 evaluation anchors (2021–2026)**. Every as-of feature uses only previous Close before next Open; each learned label from prior anchor becomes trainable only when `maturity OPEN < current signal Close`; quarterly refits only. Precisely 149 per anchor, 9,536 test ticker rows. Same original 19 engineered as-of price features + six static category one-hots. No retuning; OHLCV expansion just failed tests and is intentionally excluded, so experiments isolate the **prediction target** and distributional model instead of changing features+target simultaneously.

## Frozen predictive families
- B0_N4_TOP15: frozen archive N4 original future-top15 historical HGB scores; all economics must match its previous CAGR 16.69597% to machine precision.
- B1_PAST63: past63 close log-price momentum; sign/risk-null reference, not fit.
- F1_SIGNED_MEAN_LGBM: predict *clipped* future benchmark-relative log excess `clip(Y,-.20,+.20)` using LightGBM squared regression (robust to giant leveraged extreme cases via ex-ante ±20 log percentage point truncation). Realized target used for fitting only; evaluation uses TRUE untruncated outcomes.
- F2_HURDLE_2PART: LightGBM classifier `P(Y>0)`, two distinct LightGBM L1 regressors for positive `min(Y,.20)` and for negative magnitude `min(-Y,.20)`; score = `Ppos*E[pos|Y>0] - (1−Ppos)*E[absneg|Y<=0]`, all 3 fitted on matured data, explicitly positive and negative directional components. This is a *pseudo-expected* winsorized directional value; external regression models use no future labels.
- F3_QUANTILE_DISTRIBUTION: 3 LightGBM quantile models `q=.10,.50,.90` on clipped signed excess; score = (q10+2*q50+q90)/4 and report predicted 10th quantile as downside confidence. Do NOT claim a complete calibrated density from three quantiles.
- F4_SIGNED_TAIL_EVENTS: independent LightGBM binary heads `P(Y > +.03)` and `P(Y < -.05)` with fixed economic event thresholds, score `0.03*Pup−0.05*Pdown` (an *event score*, not mathematical true E[Y]). Report both Brier/logloss against historical-matured null and raw event rate; primary check signed precision, not right-tail-only hit rate.
- F5_RISK_ADJUSTED_MEAN: exact F1 expected clipped excess divided by preceding 63-session daily volatility times sqrt(21), with fixed .01 floor; risk efficiency diagnostic only, not a newly fitted learner.

Fixed base params for all new LightGBM regressors/classifiers: `n_estimators=80,learning_rate=.04,num_leaves=9,max_depth=4,min_child_samples=100,reg_lambda=25,random_state=20261019,n_jobs=1,verbosity=-1`. Loss for conditional magnitudes = `regression_l1`; quantile loss LightGBM with alpha .10,.50,.90 (no tuning). No train-vintage transformations from future dates. F2 conditional models trained on separate *matured positive vs negative* observations. Future benchmark ratio used ONLY for target, never for as-of features.

## Scientific score (NOT optimized on CAGR)
Primary: mean cross-sectional per-anchor Spearman vs future signed excess, plus 3-month-block CI difference vs B0; mean per-anchor top5 true signed *benchmark-relative* log excess and share with `Y>0`; mean top5 *actual* worst15 membership; negative signed-return fraction; top5 event P(Y>+.03) realized hit fraction and spread vs risk-only null. Predictive skill gate: paired block-bootstrap Spearman improvement over B0 entirely >0, PLUS top5 true mean excess > B0 in **BOTH** 2021–23 and 2024–26, PLUS realized bottom15 among top5 no worse than B0; stringent, may fail. Report actual expected average of top5 vs a fixed volatility-only control to rule out just selecting volatile instruments.

Proper scoring:
- F2 sign head: Brier/logloss on `Y>0` vs matured historical global probability; report by era.
- F4 two events: Brier/logloss vs online matured category-conditional event prior, by era (all 149 forecasts after prediction; no test labels in priors).
- F1 squared error vs prior mean `Y` and F3 q10/q50/q90 pinball losses vs unconditional historical quantile baselines fitted only matured labels. Winsorized target distribution cannot prove future untruncated alpha.
- All 5 nontrivial models also run unchanged **five equal-share ETF Next Open** costed simulation with 10 bp fee per buy and sale, daily MaxDD, ES5, turnover and CAGR, vs frozen N4 and prior SPY/AGG passive. These are exploratory and not used to change parameters.

## Hard scientific cautions
Fixed U.S. survivor 149 universe hindsight bias; repeated same 2021–26 evaluation; neither the bootstrap of 64 anchors nor a new branch constitutes independent data; likely leveraged or futures-ETF implementation unavailable through European brokers. No independent point-in-time delistings, bid/ask, tax, EUR FX or true fund factor vintages. No guarantee of ~30% CAGR. Success would require future untouched dates and economic risk-matched baselines before implementation. Never touch `etf_trader`.

Archive frozen source, per-ticker probabilities and scores (9,536×), all anchor rank losses, untruncated true Y and outcomes, daily costed shares, paired CI, and a decisive FAIL/PASS vs predefined prediction test.
