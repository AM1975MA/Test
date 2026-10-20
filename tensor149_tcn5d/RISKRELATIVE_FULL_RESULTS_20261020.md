# Original149 Risk-relative outcome distribution, audited full walk-forward — 2026-10-20

Scope: 149 frozen Yahoo-adjusted OHLCV ETF histories (SHA unchanged), exact canonical daily 125 Compact21 features, 30-session TinyTCN, weekly next-open to next-open +5, equal-weight top5, full conservative 20bp roundtrip. Registered yearly chronological 2017–2026 annual refit with mature train / validation labels. Exactly 476 matched decisions; 2024–25 pilot 100 matched decisions. Only training target changed among three models. No production repo modified.

Protocol: RISKRELATIVE_PREREGISTRATION.md.
- As-of beta_mkt63(t), annualized historical vol63(t) and vol-scaled sigma5_i(t)=max(0.01,vol63_i(t)*sqrt(5/252)).
- Future label first set to next-open 5-session relative r_i − r_SPY (raw), or /sigma5 (vol only), or (r_i−beta_i(t)*r_SPY)/sigma5 (beta+vol).
- Same-date target robust scale median and q90−q10, bound ±3, create distribution softmax(3.5 z) for cross-sectional ListNet. Future r_SPY only in matured labels; scores at inference use only causal features. Same annual scaler and neural architecture / hyperparams as preceding Listwise tests.

## Primary full 2017–2026 results, 476 weeks

| Strategy | Net CAGR | MaxDD | Sharpe | Mean true top5 overlap | Mean rank IC | As-of vol63 chosen | Mean beta63 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Previous Pointwise TCN | +5.1942% | −48.4929% | .3285 | 6.26% | +.05609 | not recorded | not recorded |
| Previous Ridge125 | +5.1314% | −50.4393% | .3310 | 6.51% | +.05434 | not recorded | not recorded |
| Original MOM21 | **+13.4143%** | **−34.9415%** | **.62525** | 13.03% | −.00565 | 30.54% | .7803 |
| RAW_EXCESS_DIST | **−9.0516%** | −73.0577% | −.16935 | 18.99% | −.00053 | 44.09% | .6844 |
| VOL_EXCESS_DIST | **−3.6146%** | −55.1821% | −.13847 | 6.85% | −.03940 | 18.89% | .3041 |
| BETA_VOL_RESID_DIST | **−2.2198%** | −56.1648% | −.02288 | 8.91% | −.02189 | 21.89% | .2169 |
| MOM21_RISK as-of simple | +1.7365% | −49.2219% | .18602 | 7.73% | −.01234 | 20.43% | .6220 |
| BETA_MOM21_RISK as-of simple | +1.6712% | −53.4133% | .18274 | 7.52% | −.00905 | 20.37% | .4585 |
| Choose HIGHEST VOL63 | −3.7874% | −56.3748% | .02020 | 18.40% | +.04132 | 47.48% | .8877 |
| Choose LOWEST VOL63 | −7.6054% | −52.8775% | −4.87781 | 1.01% | −.04132 | 7.10% | .0009 |

Net CAGR and max drawdown use same daily equity function from original registered Pointwise experiment, entry fee and exit fee charged on every five-day holding. Original pointwise metrics come from archived immutable 2026-10-20 run.

## Independent 476-date same-roster negative controls with paired moving block (block = 5 weeks)

All 476 week-anchor dates and 149-member frozen roster matched **exactly** original Pointwise. The five momentum / volatility controls select the exact same tickers and return sequences in every risk target run, so labels cannot contaminate their as-of predictions. 5-week circular moving-block bootstrap, exploratory 95% intervals for per-week Top5 nominal future return difference:

| New model minus original MOM21 | mean weekly Top5 future return delta | 95% moving-block interval |
|---|---:|---|
| RAW_EXCESS_DIST | −0.4172 percentage points per 5 sessions | [−0.7188, −0.1288] pp |
| VOL_EXCESS_DIST | −0.3571 percentage points per 5 sessions | [−0.6014, −0.1016] pp |
| BETA_VOL_RESID_DIST | −0.3199 percentage points per 5 sessions | [−0.5633, −0.0847] pp |

Differences reflect paired nominal realized Top5 basket holding returns, before identical 20bp roundtrip cost; matched costs cancel. Negative intervals exclude zero under the stated DESCRIPTIVE bootstrap but cannot be treated as independent significance due to historically mined Original149 and multiple attempted models.

Pairwise improvement relative to simple *risk-adjusted* momentum is NOT statistically supported: e.g. BETA_VOL_RESID_DIST minus BETA_MOM21_RISK mean weekly return −0.0776 pp, exploratory CI [−0.3178, +0.1529] pp. Thus the neural model's improvement over a purely as-of risk-adjusted rule is unproven.

The paired audit also generates ANNUAL_WEEKLY_REPLAY.csv with 2017–2026 weekly compounding and year-specific, costed post-hold drawdown, and METRICS.csv, COMPARISON.json, PAIRED.json.

## Diagnostic 2024–25 pilot, 100 weeks

| Strategy | Net CAGR | MaxDD |
|---|---:|---:|
| Original MOM21 | +10.4242% | −24.8602% |
| Raw relative distribution | +9.5765% | −28.0247% |
| Relative / as-of vol | −7.0934% | −24.0978% |
| Beta-normalized relative / as-of vol | +0.5990% | −23.4558% |
| MOM21 / volatility | +1.8491% | −25.5224% |
| MOM21 beta residual / volatility | +3.9401% | −25.8246% |
| Highest vol63 | +13.7786% | −22.7474% |

## Verdict

The risk-corrected probabilistic cross-section target was tested with no leakage under 149 ETF original data, preserving benchmark, annual training and weekly trading rules. It does NOT improve full 2017–26 results over original Pointwise or simple 21d momentum; its nominal forward Top5 return selection is materially inferior to momentum in paired-date bootstrap. Beta-normalization reduces selected 63d beta from MOM21 0.7803 to 0.2169, but does not translate into lower portfolio drawdown (−56.16% vs −34.94%). Selection loss and economic risk were still uncoupled: less beta is not automatically less downside risk or high expected excess return. The mean beta-relative *training-label residual* (future realized proxy) for beta risk target is +0.1518 percentage points per 5 sessions, but raw market benchmark excess selected −0.1185 percentage points, and net CAGR remains negative. Market beta residual is not a tradable hedged return without a SPY hedge and costs.

Do not promote any of the tested targets. Future hypotheses should consider (a) separate expected nominal return and tail-risk estimators, (b) a risk-aware portfolio-level decision rule with explicit nominal-return threshold or cash option, (c) market-regime/turnover-sensitive hedging, and (d) independent forward data rather than further mining Original149.

Evidence:
- Full risk-target 3-way matrix: https://github.com/AM1975MA/Test/actions/runs/39471099231
- Independently matched 476-date audit (including ANNUAL_WEEKLY_REPLAY.csv): https://github.com/AM1975MA/Test/actions/runs/39472535984
- Pilot: https://github.com/AM1975MA/Test/actions/runs/39471026485
- Independent pilot audit: https://github.com/AM1975MA/Test/actions/runs/39471702489
- Frozen Pointwise full: https://github.com/AM1975MA/Test/actions/runs/39455244701

Limitations: Survivorship and retrospective universe selection, extensively mined time period, Yahoo adjusted open not live executable, fixed nominal costs but no slippage or market impact, incomplete inference from moving-block CIs under multiplicity.
