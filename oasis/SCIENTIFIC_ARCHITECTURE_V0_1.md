# OASIS — Opportunity-Aware Stochastic Investment Switching
## Scientific architecture V0.1 | 18 October 2026 | DESIGN ONLY, NOT TESTED OR PROVEN

**Branch:** research/opportunity-crisis-switching-20261018
**Research mandate:** independently observe the ETF opportunity surface, distinguish normal breathing from structural change and crisis transition, move capital only when the *relative economic gain* of a switch is probably material after cost and model uncertainty. Avoid using the old Return-Rank and H7 decisions in the new engine. Keep them as frozen comparators. The original EUR60 2017–2026 cohort is *burned exploratory evidence* and lacks point-in-time eligibility; no tuning or deployment claims from it.

This protocol is designed **before** any OASIS EUR60 empirical trading run. No execution has been run as part of this memo. It corrects previous designs that selected monthly Top2 and added risk overlays after the fact without learning the timing or opportunity mechanics of transitions.

### Core philosophical difference

Previous research asked: "Which ETF will be the winning ETF next month?" OASIS asks the *incremental* and *causally observable* decision:

> Given exactly what can be observed at today's trade decision, does there exist an eligible new opportunity that is better than the incumbent, after execution costs, lower-tail risk, model ambiguity, expected opportunity lifespan and the risk of giving up an imminent rebound?

The action state is **hold / increase / reduce / rotate / defend / re-enter**, not simply index Top2. This is a *partially observed semi-Markov impulse-control* problem, with discrete intervention costs and a variable time until a state transition. A high absolute return forecast does not imply a profitable SWITCH if held instrument is nearly as good.

## The 11 specialist mathematical steps

| Step | Question | Lead models | Output | Key rejection test |
|---|---|---|---|---|
| 0. Source veracity | Which ETF funds/listings actually existed and were tradeable in EUR at each historic date? | event-time data engineering; bitemporal/PIT ISIN/venue/underlying; corporate-action reconciliation | as-of eligible unique underlying fund universe plus price provenance and release timestamps | future survivors, split mistakes, duplicate ISINs, quote currency mismatch |
| 1. Price measurement | What portion of a move is expected noise, persistent signal or jump? | dynamic market-factor regression + robust Student-t innovation and multiscale trend filter (2–5d / 10–21d / 63–126d) | robust factor-adjusted drift + innovation z-score by horizon | signal depends on future smoothing; tracking residual assumed mean reverting without evidence |
| 2. Breathing | Is the observed adverse move within the ticker's conditional expected fluctuation? | conditional stochastic volatility with robust state-space/Student-t predictive density; empirical coverage calibration | posterior predictive P(move), one-step log surprise, drift persistence | miscalibrated 50/80/95% intervals, systematic false exits in unchanged regimes |
| 3. Structural rupture | Did return/volatility dynamics change? | Bayesian Online Change Point Detection (BOCPD) on standardized residuals and market breadth; optionally CUSUM as control; real-time filtered probabilities only | P(change in last k days), posterior regime age/run length | can't beat simple EWMA/CUSUM on synthetic breaks + genuine held out events |
| 4. Crisis structure | Is this local dislocation, common systemic shock or early rebound? | downside common factor, robust breadth and cross-sectional dispersion, shrunk covariance eigen-effective-rank and first principal component; state-transition evidence | two axes: systemic stress probability and recovery/continuation probability; *not* a single "high-volatility" flag | adds no crisis/proper-score information beyond market volatility and trend |
| 5. Event probability | When could advantage arrive and how long might it last? | competing-risk survival / hazard model for trend reversal, incumbent deterioration and candidate relative outperformance; event-time calibrated horizons | probabilities of loss of leadership, sustained improvement and opportunity half-life | retrospective fitting to ex-post winners or unstable sparse hazard estimates |
| 6. Opportunity detection | Who has economically meaningful *relative* upside now? | scenario-conditioned Bayesian posterior of excess LOG wealth vs incumbent, factor-neutral relative momentum/strength, posterior ranking probability, tail-loss and costs | credible switch-opportunity table for all eligible ETF candidates | score mostly tracks market beta, winner lucky month or incompatible costs |
| 7. Online watchlist | Are we noticing new opportunities earlier rather than monthly end? | event-driven scanning each completed daily close, independent shadow holdings, threshold-crossing rather than monthly-only | persisted watchlist with price date, opportunity strength, emerging/regressing stage | selected using next opening OHLC, delisted missing data, excessive shadow false discoveries |
| 8. Active switching | Is it time to pay to rotate? | finite-horizon **optimal stopping / impulse control**, no-trade region with Bayesian credible economic gain; dynamic hysteresis | HOLD / BUY / SELL / ROTATE / DEFEND actions with expected NET opportunity uplift | value collapses after turnover/latency or trades on insignificant forecast differences |
| 9. Risk budget | How much capital to deploy and where? | robust risk-aware stochastic control, constrained expected log growth and scenario expected shortfall, drawdown budgets; EUR cash defined | capped weights / exposure, crisis continuation and reentry rules | gains are merely leverage/cash beta, risk ratio denominator manipulation |
| 10. Independent science | Does this truly improve event timing and capital allocation? | embargoed chronological evaluation, paired event studies & forward tests, stationary/block bootstrap, deflated Sharpe/reality check, prequential proper predictive scores | transparent evidence receipt on crisis *transitions*, not only CAGR | no independent PIT holdout, overfitting many thresholds, unmatched daily execution costs |

### Model of breathing, fragility, transition

For ETF i, its as-of return is decomposed into an observable factor part and latent idiosyncratic state:

r(i,t) = beta(i,t)·F(t) + a(i,t) + sigma(i,t)*epsilon(i,t) + J(i,t).

- beta·F: common market/sector/style movements, calibrated using only as-of factors and same-venue/currency adjusted prices.
- a: latent idiosyncratic *conditional* drift / relative efficiency.
- sigma: time-varying volatility and asymmetry; epsilon may be heavy-tailed Student-t, not necessarily Normal.
- J: sporadic shock/jump. With daily OHLCV, a daily large return is an anomaly candidate, but **do not interpret intraday bipower-variation jump estimators as available from daily closes**.
- Detect a "normal breathing" event when standardized residual is statistically plausible under the calibrated predictive law **and** posterior changepoint hazard remains low. The ticker falling 5% is neither normal nor abnormal without its conditional market factor, volatility, skew, liquidity and current uncertainty.
- A persistent deterioration is not a price decline alone: posterior a(i,t) shifts down, residual innovations remain biased, or the market's factor/network risk abruptly changes.
- Trend-filtering or wavelets may identify slow vs fast behavior, but must use **causal** one-sided filters; centered wavelet smoothing would peek at future observations.

Critical: price levels often resemble integrated processes; **do not automatically assume prices revert to a fixed equilibrium**. A mean-reverting residual or oversold displacement must be tested empirically for the *specific factor-hedged spread and regime*. Failure rejects contrarian signal.

### Four crisis-transition mechanisms, not a binary risk-on/off HMM

Use as-of posterior state probabilities, not retrospective labeling:
1. BREATHING: no material evidence of a new data-generating process, dynamic downside within expected tails, small differences in ETF opportunity scores. Enlarge no-trade region; avoid chasing near ties.
2. SHOCK/CONTAGION: abrupt shift in conditional variance, downside breadth and factor concentration; markets can gap before the next possible trade. Accelerate re-assessment; permit **immediate protective risk override** if holding's projected downside becomes unacceptable. Do not buy simply because an ETF has fallen.
3. CRISIS CONTINUATION/DISPERSION: separate **systemic loss** from individual resilient winners using factor-adjusted relative strength and downside covariance. Rotation into truly different underlying exposures or a *verified EUR cash/defensive UCITS sleeve* may be needed; 60 equity ETFs cannot universally hedge equity selloffs. Exit old exposure only on causal evidence of better alternatives.
4. RECOVERY: declining probability of further market downside, improving cross-sectional breadth, reduced negative co-jumps and positive *factor-adjusted* relative return acceleration. Watch for abrupt winner-to-loser rank reversal / momentum crash; compare incumbent versus rebound candidates using a short state-conditioned opportunity horizon, not a retrospective bottom signal.

Why crisis transitions deserve special experiments: Daniel & Moskowitz (2016), Momentum Crashes, https://doi.org/10.1016/j.jfineco.2015.12.002 report momentum drawdowns associated with rebounds after panics. Extreme downside dependencies differ from unconditional correlations; Longin & Solnik (2001), https://doi.org/10.1111/0022-1082.00340. **Neither proves that entering crises early will make money for our ETF set.**

### Economically meaningful opportunity, NOT Sharpe-by-ticker

For current held portfolio h and candidate replacement i, conditional on data available at t, define for horizon H:

G(i←h,t,H) =
  E_t[ log(wealth_i(t,t+H)) - log(wealth_h(t,t+H)) ]
  - expected incremental execution/FX/spread cost(i←h,t)
  - lambda * max(0, ES_loss(i,t,H) - ES_loss(h,t,H))
  - gamma * ambiguity(i←h,t,H)
  - opportunity-duration penalty.

Use the **posterior predictive distribution of relative log payoff**, not only mean G.
A candidate is "economically significant" only if:
- expected net relative benefit is positive under predeclared transaction costs,
- a calibrated one-sided lower predictive/epistemic bound on G exceeds the no-trade hurdle, unless a separately defined severe-risk override is active,
- its edge persists across more than one clock scale / survives tiny source-version price perturbations,
- enough *independent* underlying ETF holdings exist and available volume/spread can execute in an as-of valid EUR market,
- the predicted advantage duration is long enough to repay current and anticipated next exit costs.

Do NOT use an exact prediction of the next month winner as training label: use **relative, trade-conditioned log-utility realized at actual feasible timestamps**. Labels of hypothetical switches may overlap and should be embargoed, costs counted, information set bounded.

### Dynamic hysteresis as optimal switching region (the central novelty)

Static Top5 history offered 14.09% retrospective EUR60 CAGR but strong sensitivity to recent 2024–26 and a wide paired bootstrap CI. Retain its principle, NOT its arbitrary Top5 threshold.

At each t consider net continuation value Q_hold and net switch value Q_switch under model uncertainty. The controller uses an **inaction region**, for instance:

SWITCH only if LB_95%(Q_switch - Q_hold) > actual_crossover_cost
and P_t(candidate superior for intended holding horizon) > calibrated_threshold.

The threshold should come from constrained decision costs / acceptable false-switch rate, **not** maximize burned EUR60 CAGR. The condition is an illustrative design, not yet a selected operational calibration.

**Critical exception:** in an acute loss scenario a separate downside-risk budget can require protective de-risking even if the next ETF's mean expected return is statistically tied. This separates *alpha switching* from *survival control*.

In normal breathing with small predictive return differences, posterior uncertainty and frictions keep the position stable. In a well-evidenced structural rupture, the posterior can move strongly enough to cross the no-trade region despite elevated volatility. In an unconfirmed high-volatility crisis the no-trade region for speculative rotation widens, whereas the protective risk override may trigger. This resolves the apparent contradiction "be active during crisis, but don't overtrade in noise".

Interpretation via physics: *metastable state plus an energy barrier* is an analogy for transaction-cost-induced inaction. Here the barrier is measurable money + uncertainty + foregone opportunity, **not physical thermodynamic energy**. There are mathematical results showing that proportional costs induce no-trade regions in optimal control: Holden et al., Optimal rebalancing of portfolios with transaction costs, https://doi.org/10.1080/17442508.2011.651219.

### A different timing clock: state-aware, not monthly-only

Scanner updates on each **completed session close** (as-of). It checks known market-wide and holding-local alarms at daily frequency and produces hypothetical action at the *next actually feasible exchange open*. A stable regime with weak opportunities can go 1–3 months without switches. A crisis can generate 2–5-day *checks* and potentially multiple real switches if truly justified after costs, but not an unconditional frenzy of trades.

Define distinct update clocks (daily event observations vs weekly/monthly expert refit) so each label reaches full maturity before learning. Data availability includes holidays, partial closures, non-common exchange openings, bid/ask and intraday execution assumptions. A monthly open/open benchmark and daily intervention strategy must both be simulated on the SAME continuous portfolio wealth timeline to be comparable. A new daily backtester is mandatory; prior 113 monthly open/open results cannot validate emergency transitions.

### Mathematical method choices and explicit rivals

1. Per-ticker signal: robust Student-t factor-adjusted state-space **vs** EWMA-trend and plain residual trend. Reject Kalman unless proper predictive score and economically useful risk-normalized signal improve.
2. Breathing vs new regime: multivariate robust BOCPD **vs** one-step anomaly score and CUSUM/EWMA. BOCPD's hazard/run length can identify a new state before a large fixed-window moving average, but may be too sensitive to jumps.
3. Market crisis classification: downside breadth + shrunk eigen concentration + posterior change risk **vs** market index volatility alone. Test false alarms, time-to-detection and missed recoveries.
4. Relative opportunity: credible **paired incumbent-to-candidate** advantage **vs** cross-sectional average-return ranking and simple time-series momentum. Strong predictor quality is insufficient if switch after costs not valuable.
5. Switching: economic uncertainty-aware optimal stopping **vs** unconditioned Top2 monthly, Top5 hysteresis monthly, fixed Δrank gating and pure "switch if score higher" rules.
6. Portfolio: risk-limited two/five positions + defensives vs equal weight and naive inverse vol. Bound concentration, tail correlation and cash exposure; compare on matched beta and exposure.
7. Continuous validation: one-variable-at-a-time ablations, causal **prequential predictive log score, quantile coverage, conditional Brier score, net relative log growth**, crisis conditional regret, delay cost, trade-change budget and net drawdown. Tests must expose observed status when inputs cannot support estimates.

Avoid automatic entropy-gated trading: prior H4 5.87% CAGR vs H0 9.98% on mined EUR60. Entropy can measure crowding / market breadth but must beat simpler concentration measures before it earns a trade-control role. Avoid indiscriminate expert mixing: previous online Hedge (5.30% CAGR) diluted strong D1 standalone (9.19%). Don't introduce an ensemble without evidence of complementary conditional skill.

### A concrete completely hypothetical scenario (NOT EUR60 backtest)
- Current ETF A expected factor-adjusted excess log return over next 10 sessions +0.5%, ETF B +0.8%; model uncertainty on B−A is ±1.0%, round-trip cost 0.25%. A and B are practically tied. **HOLD A** because an estimated 0.3% gross advantage does not justify the costs and uncertainty.
- After a downside market shock, B becomes a genuine defensive relative leader. The paired posterior expected B−A advantage is +3.0% over the next 10 sessions, with calibrated one-sided lower bound +0.9% and gross execution hurdle 0.3%, holding-specific tail protection improves. **ROTATE A→B** if risk budget and universe permit.
- Panic stabilizes. An ETF C rebounds 6% in one day, but uncertainty and negative market breadth remain high: **WATCH C**, no automatic "buy the dip".
- After a sustained breadth reversal, the posterior lower bound for C's net conditional advantage over B clears hurdle and trend-reversal confidence improves. **REENTER C** (at next tradable open). If a margin vanishes the next day, hysteresis prevents a reflexive return to B.

These are pedagogic values, **not estimates from live or backtested financial data**.

### Experimental package and phases, strict reproducibility
**Phase A: validate observations** (no trading).
- Build PIT eligible EU fund universe and conservative venue/FX/ISIN filters; compare historical data vintages as perturbations, not independent holdouts.
- Fit only as-of state models; evaluate proper prediction density, 50/80/95% coverage and shock/rank fragility. Plot normal breathing vs documented shock dates **only for diagnostics**, never event-guided re-tuning.

**Phase B: quantify genuine relative alpha** (shadow only).
- Daily log every opportunity candidate in all eligible names, paired vs incumbent, 5/10/21-day horizons, expected gross/cost/upside/tail and uncertainty.
- Verify whether opportunity LB or superiority probability predicts an economically positive net *alternative* vs no-action, and calibration survives 2017–2020, 2021–2023, 2024–2026 as internal historical stability checks only. No claims of prospective validity from a cohort studied repeatedly.

**Phase C: transition experiment** (new daily engine and matched path).
- Freeze predictions & thresholds before testing. Compare:
  A) static monthly rank,
  B) monthly rank + fixed Top5 historical inertia,
  C) dynamic opportunity economic gate,
  D) C + protective regime-based de-risking,
  E) D + recovery early reentry.
- Preserve an explicit *crisis-alarm ablation*: C vs D vs E isolates tail defense versus new opportunities.
- Split *crisis onset*, *drawdown continuation*, *recovery* and *normal breathing* with as-of labels and also measure realized event outcomes without classifying with future data.
- Capture missed opportunities, false switches, annualized turnover, 1/5/21-day post-event regret, net log growth, maximum daily DD, time underwater, tail loss, concentration and missed rebound returns.
- Secondary controls: random event-matched switches, no-trade agent, daily always-rank-top2, passive liquid Europe UCITS index proxy, realistic cash.
- Cash must be a realistic EUR fund/deposit with as-of actual yield and costs, otherwise declare 0%-yield hypothetical and do not claim practical safety.

**Phase D: scientific promotion**
- Reserve truly untouched forward months and independent PIT ETF roster; use rolling retraining with explicit embargoes and version hashes. Multiplicity-adjust confidence, do not select winning variants on final holdout. If no PIT universe/fresh observations exist, STOP at research prototype.

### Research source anchors
- Adams & MacKay, Bayesian Online Changepoint Detection, 2007: https://arxiv.org/abs/0710.3742
- Holden et al., Optimal rebalancing portfolios with transaction costs: https://doi.org/10.1080/17442508.2011.651219
- Daniel & Moskowitz, Momentum Crashes (2016): https://doi.org/10.1016/j.jfineco.2015.12.002
- Barroso & Santa-Clara, Momentum Has Its Moments (2015): https://doi.org/10.1016/j.jfineco.2014.11.010
- Longin & Solnik, Extreme Correlation of International Equity Markets (2001): https://doi.org/10.1111/0022-1082.00340
- Gneiting et al., Probabilistic forecasts, calibration and sharpness (2007): https://doi.org/10.1111/j.1467-9868.2007.00587.x
- Gibbs & Candès, Adaptive Conformal Inference Under Distribution Shift (2021): https://arxiv.org/abs/2106.00170
- Barndorff-Nielsen & Shephard, Testing jumps using bipower variation (2006): https://doi.org/10.1093/jjfinec/nbi022 . NOTE: primarily high-frequency realized-volatility methods; NOT directly an OHLC-daily jump test.

## Decision
This is the design of a potentially stronger *decision system*, NOT evidence of stronger realized alpha. The priority is to implement and verify the *as-of opportunity label* + *economic switching hysteresis* + *transition-aware daily backtester* **before** adding more mathematical sophistication. Crisis/reentry control should be a separately falsifiable layer, not fitted as one end-to-end reward learner on the contaminated 113-month history.
