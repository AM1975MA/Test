# Original149 5D Daily Training + R1/R2 Relational Features — Final 476-Week Audit, 2026-10-20

**Final status**: Complete. All six ablations have actual trained annual models, 476 matched weekly OOS decision results, scored ETF predictions, retained checkpoint/per-year artifacts and net costed performance. Independent six-model 476-week audit **PASSED** (GitHub Actions 39482849326). **No model is promoted to production.** This document is an ex-post retrospective experiment, NOT a claim of prospective alpha.

## Frozen protocol and research hypothesis

- Original149 frozen 149-ETF retrospectively assembled universe, frozen historical adjusted OHLCV and roster checksum, 125 original Compact21 daily features from unchanged vendored kernel. Static six-category taxonomy. Five-trading-session *future next-open to next-open+5* nominal return target, original next-open execution and realized label-maturity embargo.
- Each weekly portfolio holds five selected ETFs equally weighted; 20bp conservative roundtrip cost; original fixed 476 OOS decisions 2017–2026. Fold-specific yearly expanding train / prior-year validation; model/predictions per year archived.
- A original baseline: pointwise TinyTCN with 5-session-spaced training, exactly frozen run 39455244701. Original Ridge125 and historical momentum21 are frozen controls from same run.
- B daily training, original 125 features, identical TinyTCN 30 days×features, 24 channels, dropout .35, original pointwise SmoothL1, maximum five epochs.
- C B +14 causal R1 features: own 5/21/63/126 day momentum relative to SPY and within group, beta63-adjusted SPY momentum, within-group percentile at 21/63. D C +20 causal R2 leave-self-out other-ETF/peer correlation, breadth, volatility/dispersion, dispersion shock and SPY regime.
- E XGB_BASE: pairwise XGBRanker 240 trees, depth4, snapshot original 125 features; E XGB_R1R2 identical with 159 features; E CAT_R1R2 CatBoost QueryRMSE on 159 snapshot features, 240 iterations depth5. For tabular models only a single as-of feature snapshot at signal t was used; TinyTCN sees last 30 daily feature dates. This is an architecture/input representation comparison, NOT equal temporal representation.
- Every new model trained on every eligible daily signal date, training labels are 5-session overlapping, but weekly OOS dates and portfolio policy identical to A.
- Configs were frozen before inspecting 2024–25 pilot; full 2017–26 launched independently of pilot selection.

## Complete original 149 ETF, 2017–2026, precisely 476 matched weekly decisions

| Model | Original features | Training date frequency | Net CAGR | MaxDD | Sharpe | Mean cross-sectional RankIC | Realized nominal Top5 overlap |
|---|---:|---|---:|---:|---:|---:|---:|
| A original TinyTCN, frozen | 125 | Every 5 sessions | +5.1942% | -48.4929% | .3285 | +.05609 | 6.26% |
| original Ridge125, frozen | 125 | Previous original setup | +5.1314% | -50.4393% | .3310 | +.05434 | 6.51% |
| original past21 momentum | Simple rule | No train | **+13.4143%** | **-34.9415%** | .6252 | -.00565 | **13.03%** |
| B_DAILY_BASE | 125 | Every session | +6.1893% | -44.7853% | .3743 | +.05786 | 6.34% |
| C_DAILY_R1 | 139 | Every session | +1.6046% | -46.8024% | .1856 | +.05133 | 6.22% |
| D_DAILY_R1R2 | 159 | Every session | +9.7219% | -44.5230% | .5074 | +.05171 | 6.76% |
| E_XGB_BASE | 125 | Every session | **+15.5726%** | -41.5696% | **.7115** | **+.05910** | 10.67% |
| E_XGB_R1R2 | 159 | Every session | +8.1337% | -45.7692% | .4370 | +.03826 | 9.62% |
| E_CAT_R1R2 | 159 | Every session | +4.4157% | -45.5512% | .3132 | +.05005 | 2.23% |

**Interpretation:**
1. Daily training by itself B vs original A increases point estimate mean RankIC only +.00178 and net CAGR from +5.19% to +6.19%; do not claim robust rank improvement.
2. R1 alone C vs B lowers rank IC from +.05786 to +.05133 and reduces full-net CAGR from +6.19% to +1.60%, the opposite of pilot gain.
3. R1+R2 combination D vs B raises net CAGR from +6.19% to +9.72%, but rank IC drops +.05786 to +.05171, MaxDD remains -44.5%.
4. XGBoost snapshot original 125 features E_XGB_BASE has the highest 476-week net CAGR (+15.57%) and highest full-period new-model RankIC (+.05910) but MAXDD -41.57%, considerably worse than momentum21 -34.94%. In 2024–25 diagnostic pilot, E_XGB_BASE CAGR +18.56% RankIC .06607.
5. Adding all 34 R1/R2 features to the same XGBoost architecture is actively *harmful* over full history: CAGR +15.57% -> +8.13%, RankIC +.05910 -> +.03826 and DD -41.57% -> -45.77%, despite the opposite *pilot* effect (+18.56% -> +26.11% CAGR).
6. CAT feature-rich 2024–25 CAGR +18.71% collapses to full +4.42%, providing a second empirical warning about choosing winners on just 100 weekly dates.
7. None reaches the speculative mean RankIC 0.08 or 0.10 target; there is no substantial independent predictive improvement.

## Independent 476-week full six-variant audit

Successful run: https://github.com/AM1975MA/Test/actions/runs/39482849326 . This checks original Original149 dataset manifest SHA, exactly the same 476 weekly dates, model identity, original baseline scores, and per-year costed weekly replay, computes the *paired differences* in cross-sectional RankIC, Top5 oracle overlap and nominal 5-day Top5 basket returns. Original 5-week circular moving-block bootstrap, 1600 draws, with descriptive 95% intervals, not prospective or multiple-testing corrected.

| Variant vs original A Pointwise TinyTCN | RankIC mean delta and 5-week block 95% CI | Top5 overlap mean delta and 95% CI (percentage points) | Mean five-session basket return delta and 95% CI (percentage points) |
|---|---|---|---|
| B daily 125 | +.00178 [−.01081,+.01440] | +.084 [−1.345,+1.471] | +.0126 [−.1576,+.1850] |
| C R1 | −.00476 [−.02056,+.01095] | −.042 [−1.639,+1.471] | −.0762 [−.2837,+.1227] |
| D R1+R2 | −.00438 [−.02098,+.01237] | +.504 [−1.050,+2.059] | +.0799 [−.1162,+.2639] |
| E XGB125 | +.00301 [−.01139,+.01815] | **+4.412 [+2.731,+6.009]** | +.1910 [−.0490,+.4275] |
| E XGB159 | −.01783 [−.03798,+.00408] | +3.361 [+1.596,+5.000] | +.0522 [−.2098,+.3101] |
| E CAT159 | −.00603 [−.02542,+.01111] | **−4.034 [−5.546,−2.689]** | −.0299 [−.2767,+.1904] |

**Most important falsification:** E XGB125 nominal mean five-day selected basket return vs simple MOM21 +.0401 percentage point per five sessions, descriptive paired 95% interval [−.2852,+.3411] percentage points includes zero. Despite better retrospective CAGR (+15.57% vs +13.41%), there is no convincing weekly paired nominal-return superiority and the drawdown is worse. E XGB125 vs A mean RankIC +.00301 CI crossing zero; no established breakthrough in global RankIC.

Archive for 2017–26 per-year economics and all pairwise comparisons: full independent audit GitHub Action artifact **original149-r1r2-full-paired476-audit** (REPORT.json, PERFORMANCE.csv, ANNUAL_BY_MODEL.csv). Historical block bootstrap statistics exploratory due to sample mining.

## 2024–25 diagnostic pilot, precisely 100 matched OOS decisions

| New model | net CAGR | Mean RankIC |
|---|---:|---:|
| B daily | +8.49% | .05362 |
| C daily+R1 | +12.80% | .05772 |
| D daily+R1+R2 | +15.68% | .05857 |
| XGB125 | +18.56% | .06607 |
| XGB159 | **+26.11%** | .05916 |
| CAT159 | +18.71% | .04959 |

The pilot grossly overrated expanded XGB, R1-only TinyTCN and CatBoost, whereas the full archive reverses their apparent rankings. Do not promote pilot winner or treat pilot as clean holdout since adjacent historical Original149 already extensively mined.

## Provenance and reproducibility

- Baseline A original immutable 2017–26 model: https://github.com/AM1975MA/Test/actions/runs/39455244701 .
- B,C,D,Cat full 476-week trained models and saved per-fold state: https://github.com/AM1975MA/Test/actions/runs/39478752782 . Workflow overall status **failure** solely because its original two XGBoost jobs failed in an evaluation metric that demanded nonnegative integer relevance labels. **The four cited B/C/D/Cat individual matrix jobs succeeded**. The failures are not treated as valid model results.
- Corrected XGBoost 3.1 rank:pairwise float-label default validation metric by setting eval_metric=rmse; objective, labels and estimators unchanged; reran BOTH pilot and full XGB: https://github.com/AM1975MA/Test/actions/runs/39479754815 (full SUCCESS).
- Exact same dataset and 476 weeks matched original in independent partial audit for first 3: https://github.com/AM1975MA/Test/actions/runs/39482481414, then exact full 6-model independent audit https://github.com/AM1975MA/Test/actions/runs/39482849326 (SUCCESS).
- Synthetic causal/prefix tests passed: https://github.com/AM1975MA/Test/actions/runs/39478363028.
- Pre-register: tensor149_tcn5d/DAILY_R1R2_PREREGISTRATION.md; pilot: tensor149_tcn5d/DAILY_R1R2_PILOT_RESULTS_20261020.md; source: tensor149_tcn5d/relational_features.py and daily_ablation.py, independent paired audit: compare_daily_r1r2.py.

## Decision / next research

**Reject hypothesis that these 14 R1 and 20 R2 features produce a substantial global RankIC gain**. DO NOT promote complex full-feature models. Keep E_XGB_BASE (Original125 features, daily learning-to-rank, consistent Top5 overlap improvement vs baseline A) as *research challenger*; it is not better on MaxDD than simple momentum and no full-period paired return advantage vs momentum is established.

Prioritize ONE independent clean validation regime before further feature mining. If continuing exploration on the mined Original149, test parsimonious *feature selection*, constrained R1-only vs R2-only ablation, factor/volatility-controlled rank diagnostics, and a separately evaluated downside-risk portfolio filter in temporally nested walk-forward, with at most pre-registered configs. Economic value and drawdown must be evaluated separately from RankIC; avoiding overfitting matters more than another marginal 0.003 rank gain.

**Limitations**: Survivor selection and static 149 ETF taxonomy, repeatedly mined same 2017–26 OOS periods, Yahoo adjusted price assumptions not necessarily executable intraday at adjusted open, fixed costs not comprehensive live slippage/market impact, no independent history until future untouched data or disjoint instrument universe is reserved. Annual model comparisons on same sample should not be stated as proven live alpha.
