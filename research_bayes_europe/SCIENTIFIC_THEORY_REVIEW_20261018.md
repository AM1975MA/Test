# SCIENTIFIC MODEL DESIGN — physics, information, games, stochastic control
**2026-10-18 / exploratory research decision, NO NEW PERFORMANCE CLAIM.**
Parent: [HYPOTHESIS_KALMAN_RISK_OBSERVER.md](../HYPOTHESIS_KALMAN_RISK_OBSERVER.md). Historical observation source: [RESULT.json](../results/RESULT.json), certified [Action 39087987551](https://github.com/AM1975MA/Test/actions/runs/39087987551). Original \`etf_trader\` and existing data unchanged.

## 0. Problem formulation and physical analogies
The problem is **not** "find a magical formula for tomorrow's price." It is a **partially observed, time-varying stochastic control problem with adaptive interacting agents**.
- Hidden state: transient expected asset excess returns, latent volatility, broad factor exposure/correlation structure, regime-switch probability, data/revision reliability.
- Observation: historical as-of OHLCV and publication-timestamp-valid external data. Missing/stale prices and corporate actions add measurement noise.
- Action: choose eligible European-UCITS ETFs and weights at next common **open**, then hold/rebalance per an executable rule.
- Cost: turnover, fees, FX, spreads, trading calendar, tail loss and concentration.
- Control goal: robust prospective utility and drawdown under uncertain parameters, **not** hindsight Top1 oracle CAGR.
- Agents adapt: market is nonstationary, not an autonomous deterministic machine. Return labels on a repeated 2017–2026 retrospective universe are not an independent scientific validation.

**Physical analogy: spacecraft navigation.** The predictor ("trajectory plan") is not the observer (Kalman-like estimate of position/uncertainty), which is not the controller (portfolio trade constrained by safety envelope). Combining all three into one black-box score hides causal errors. An uncertain posterior should change how aggressively the controller acts, not automatically reverse the destination.

## 1. Falsifiable theory map — prioritize predictive utility, not novelty

| Theory and analogy | Operationally measurable component | Plausible added value | Main trap | Priority |
|---|---|---|---|---|
| Bayesian state-space / robust Kalman: noisy sensor estimates hidden drift | one-step predictive mean, variance and Student-t tails; sequential log score | stable uncertainty estimates; outlier resistance | posterior approximation misspecification, autocorrelated errors, weak directional alpha | HIGH |
| Hidden Markov states / Bayesian online changepoints: changing weather system | filtered, **not smoothed** p(high-vol regime); hazard of change | nonstationarity, time-varying volatility and correlations | with 113 monthly decisions, many states/parameters overfit | HIGH, start one two-state **shared-market** model, not per-ETF HMM |
| Statistical mechanics / entropy of correlation eigenmodes: hidden concentration of energy in one mode | as-of eigenvalue Shannon effective rank of shrinkage covariance \`N_eff=exp(-sum p_j log p_j)\` | measure whether 60 nominal ETFs effectively track few independent shocks | "financial entropy" is not thermodynamic entropy; arbitrary entropy of return signs can be useless | HIGH as **risk**, NOT alpha, predictor |
| Random matrix theory: noisy high-dimensional sensors | shrink eigenvalues; track largest market eigenmode and effective rank | reduce covariance inversion noise, flag common-shock concentration | 252 daily points/60 ETFs still dependent; duplicate ISINs bias dimension | HIGH |
| Robust stochastic optimal control / MPC: autopilot minimizing flight risk | optimizer penalizing variance/ES, turnover, model ambiguity and departure from equal weights | clear separation selection vs sizing, cost-aware actions | unconstrained estimated-mean optimization maximizes estimation error | HIGH |
| Online expert learning / repeated game: expert players adapt to changing market | Hedge/exponential weights between **frozen** R_H, Kalman-risk, inverse-vol policies; update only after realized payoff maturity | gradual adaptation with bounded regret to fixed expert under assumptions | extra hyperparameter; transaction costs, regret guarantee NOT future alpha | MEDIUM; after isolated selection-vs-sizing tests |
| Information theory: ask whether the sensor adds genuinely new information | prequential change in log predictive density, interval coverage, Brier/proper scores | distinguish real incremental risk information from a metric coincidence | entropy is not automatically causal information; MI/transfer entropy tiny samples misleading | HIGH as validation |
| EVT / heavy-tail physics: high-impact rare storms | Student-t forecast, predeclared stress scenarios, exceedance rate and expected shortfall | calibrated loss limits | 113 monthly periods give ~6 observations in 5% tail; cannot fit rich EVT safely | MEDIUM on longer *daily* data, diagnostic |
| Adaptive market/minority games: many strategic agents compete for limited opportunities | expert score persistence, crowding proxies only if actual flows/order book/positioning are available | hypothesis that edge decays as strategies crowd | OHLCV alone cannot identify strategic payoffs, participants, equilibria | LOW for direct implementation |
| Deterministic chaos / Lyapunov/fractals: butterfly effect | data-perturbation sensitivity, rank switches, divergence of decisions under revised prices | excellent **stress test of pipeline instability** | no proof chaotic deterministic law in markets; short noisy series yields spurious exponents | HIGH as quality diagnostic; LOW as forecast model |
| Thermodynamic temperature, free energy, criticality | conditional volatility proxy ("temperature") and KL-regularized optimization ("free energy") | helpful metaphor for volatility and regularization | temperature and free energy are **not literal physical observables**; no conservation law | MEDIUM as design metaphor, LOW as claim of market physics |
| Reinforcement learning/deep end-to-end controller | trial-dependent multi-step policy | potentially state/action interaction | finite independent months and reused evaluation make policy search overfit easily | LOW now |

### A concrete example of entropy's useful interpretation
Let \(\Sigma\) be the covariance or correlation matrix on the *as-of eligible, distinct underlying ETF exposure set*, preferably shrunk, with nonnegative eigenvalues \(\lambda_k\). Define \(p_k=\lambda_k/\sum_j\lambda_j\), \(H=-\sum_k p_k\log p_k\), and \(N_{\rm eff}=\exp H\). With a **synthetic** 60x60 equicorrelation matrix:
- \(\rho=0\): \(N_{\rm eff}=60.000\);
- \(\rho=0.5\): \(N_{\rm eff}\approx14.847\);
- \(\rho=0.8\): \(N_{\rm eff}\approx3.661\);
- \(\rho=0.95\): \(N_{\rm eff}\approx1.487\).

In the \(\rho=0.8\) example, 60 legal products still offer only ~3.7 **entropy-effective statistical covariance modes**, NOT precisely 3.7 independent securities or future returns. These are analytical illustrations, **not empirical results on the user ETF universe**. Normalize for changing N and compare simple \(\bar\rho\), first eigenvalue share and realized variance before claiming added information.

An ETF-specific *Shannon entropy of returns* does not automatically measure market uncertainty or predict next month's winner. Transfer entropy may detect asymmetric dependence but estimation is fragile at 113 observations and hidden common drivers make causality claims invalid.

### What chaos theory actually suggests
Small changes in data caused large historical winner/weight changes in Test. That establishes **sensitivity of a trained decision pipeline**; it does **not** establish a positive Lyapunov exponent or deterministic chaotic market dynamics. The scientifically valid use of the analogy is a **perturbation amplification audit** (small noisy Yahoo revisions -> score gaps -> Top2 membership changes -> risky weight changes -> PnL difference). The cure can be posterior uncertainty, hold/no-trade hysteresis, confidence thresholds and constraints; it is NOT fitting Lorenz attractors to noisy ETF quotes.

### What game theory actually suggests
Many independent strategies compete, and profitability can erode. Rather than simulate invisible participants, choose a tiny fixed set of *observed* experts. A causal Hedge update can be written
\(q_{j,t+1}\propto q_{j,t}\exp(\eta\,g_{j,t})\),
where \(g_{j,t}\) is the **matured realized** net log growth of an already specified shadow strategy; cap exposure to any single expert and charge trade costs. This is online learning with regret notions, **not a zero-sum model that predicts prices**. Before adding Hedge, establish that each expert carries independent out-of-time information: a controller cannot create alpha by mixing two invalid forecasts. Use strictly past realized outcomes; no hard router based on future winner or ex-post fitted threshold.

### Robust control in actionable terms
At each monthly signal date, do not optimize the historical winner. Keep R_H's predeclared Top2 and choose \(w\) using only previous data, calibrated uncertainties and constraints. One **illustrative** control functional, NOT already backtested:
\[
\min_{w\in\mathcal W}
\underbrace{-\hat\mu^\top w}_{\text{forecast opportunity}}
+\lambda\underbrace{w^\top\hat\Sigma w}_{\text{portfolio risk}}
+\gamma\underbrace{\|w-w_{t^-}\|_1}_{\text{turnover}}
+\tau\underbrace{D_{\mathrm{KL}}(w\parallel w_{\mathrm{prior}})}_{\text{regularization}}
+\kappa\underbrace{\mathrm{ES}_{95\%,t}(w)}_{\text{tail stress}}.
\]
Here \(\mathcal W\) is an investable simplex with nonnegative bounded weights and a declared defensive asset/cash contract; posterior mean errors may dominate, so first benchmark **zero mean input** (risk-only) against full formula. The KL term borrows language from "free energy" but imposes **algorithmic** stability, not thermodynamic physics. A complex ES + variance + entropy objective has several tuning degrees of freedom; test simple risk-only and equal-weight controls first, rather than a 5-penalty sweep.

In this strict Europe-only study, BIL/SHV are US market **reference** series, not a legitimate European investable cash sleeve. A real EUR cash/deposit/UCITS money-market proxy or explicitly unremunerated 0% cash must be separately specified *as of date* before measuring full dynamic risk-off benefits. Without an escape asset and with 100% capital in two European equity ETFs, widespread market drawdowns cannot be hedged away by posterior reweighting alone.

## 2. Recommended minimal architecture — scientific priority

\`\`\`
PIT Europe UCITS/ISIN/currency + QA of corporate actions, splits, calendars
             |
        AS-OF DAILY RETURNS
             |
     +-------+--------------------------------+
     |                                        |
 R_H frozen selection                  RISK OBSERVER
 (rank Top2 at t)                       |
     |                           robust Kalman + Student-t
     |                           simple shared 2-state
     |                           high/low vol filter
     |                           shrunk covariance
     |                           eigen entropy N_eff
     |                                        |
     +----------------------+-----------------+
                            |
               CONTROL / ALLOCATION POLICY
            start: SAME Top2, explicit weights
             50/50 vs inverse vol vs uncertainty
             model risk, turnover, no trade band
                            |
                next common tradable open
                            |
                 EX-POST FORECAST SCORING
        log score, calibration, ES, turnover, PnL
\`\`\`

Do **not** start with all observer modules simultaneously; the diagram shows the final hypothesis space, not an authorization to merge layer effects in one experiment. Stage 1: Kalman uncertainty alone vs plain inverse historical volatility **with frozen identical R_H Top2**. Stage 2: only if Stage 1 forecasts uncertainty better, one shared-market regime filter. Stage 3: entropy-based correlation concentration as a **risk gate** tested with frozen previous stages. Stage 4: online game/experts if incremental information survives; all model changes separately frozen beforehand. Stage 5: consider stress-tail control when an investable EUR cash sleeve exists.

## 3. Measurement plan, null hypotheses, controlled gates

**First gate: data quality, not return.** Point-in-time eligible fund universe (no future survivor conditioning), European underlying geography, official ISIN per fund, EUR venue currency, no same-ISIN duplicate lines, exchange calendar and source adjusted prices. Original EUR60 remains permanently *burned development data*. No independent forward edge inference from running it again.

**Step A — observational diagnostics (no trading optimization):**
- Test Kalman one-step log score and 50/80/95% predictive interval coverage on months/daily risk horizon against rolling historical volatility and unconditional Student-t variance.
- At each signal compute first eigenvalue share, mean correlation, \`N_eff\`, risk forecast and realized subsequent variance. Show whether entropy improves risk forecast *conditional on volatility and on turnover*, not merely whether it correlates with crisis retrospectively.
- Test regime/filter state classification using strictly filtered probabilities at t, never smoothed probabilities \(P(z_t \mid y_{1:T})\) or future-label optimum.
- Test forecast residual autocorrelation, PIT calibration, outlier/missing handling and sensitivity to tiny OHLC revisions.

**Step B — one-variable-at-a-time economic factorial:**
- freeze R_H Top2 membership and execution. Base 50/50.
- compare one candidate at a time: historical inverse-vol, Kalman posterior uncertainty weights, posterior mean+variance separately. Fixed constraints, no hidden allocation target rescaling, no share of future fitted equity used.
- assign paired differences in net monthly log return, monthly/daily max drawdown, ES95, volatility, holding concentration, turnover and worst-year return; no result chosen by max CAGR on this burned panel.
- **selection-vs-weight attribution** must compare identical selection with different weights and identical weights with different selection, not infer cause from one path.

**Step C — genuine scientific test:**
- new forward untouched observations acquired after model and code freeze, or distinct genuinely PIT constructed cohort untouched by any model choice; no retrospective EU60 "holdout" after many rounds of research.
- stress via dependent multiple raw-data vintages is a reliability test, NOT independent statistical samples.
- calendar/block bootstrap/Reality Check for multiple trials; performance claim must account for model search. A missing promotion gate is a negative result, not a tuning invitation.

**Decision rule:** Prefer the smallest observer that improves *proper risk-forecast skill* and subsequently out-of-sample *net expected utility* without lower-tail deterioration relative to equal weight and historical inverse-vol. Do not require improved historical Top1 hit rate from risk observer. If none clears all gates, freeze R_H ranking, retain only diagnostics and reject additional trading layers.

## 4. Empirical falsifiers and things to avoid
1. Risk posterior not better calibrated than lagged realized volatility: Kalman complexity is unwarranted.
2. Entropy signal not incremental after vol/correlation level/market trend: do not append it to the trader.
3. HMM regime probabilities collapse to uninformative constants or leak future via smoothing: reject.
4. Expert-mix gains vanish after turnover and mature-payoff lag or under perturbation: reject Hedge.
5. Any return improvement occurs exclusively in 2017–2026 already inspected, unverified ETF geography/ISIN/currency or a hand-picked vintage: **do not promote**.
6. More than one module alters both ranking and allocation in a "single" experiment: reject causal attribution.
7. Inverting a high-dimensional unshrunk 60x60 covariance, maximum Sharpe optimizing noisy mean, or fit of 7-parameter critical-crash LPPL to selected crash windows: avoid.

## 5. Scientific anchors (not performance guarantees)
- Rama Cont, *Empirical Properties of Asset Returns*, Quantitative Finance 1, 2001. https://doi.org/10.1080/713665670
- J. D. Hamilton, *A New Approach ... Nonstationary Time Series*, Econometrica 1989. https://ideas.repec.org/a/ecm/emetrp/v57y1989i2p357-84.html
- R. P. Adams, D. MacKay, *Bayesian Online Changepoint Detection*, 2007. https://arxiv.org/abs/0710.3742
- Laurent Laloux et al., *Noise Dressing of Financial Correlation Matrices*, Phys. Rev. Lett., 1999. https://doi.org/10.1103/PhysRevLett.83.1467
- Thomas Schreiber, *Measuring Information Transfer*, Phys. Rev. Lett. 2000. https://doi.org/10.1103/PhysRevLett.85.461
- Andrew W. Lo & Ruixun Zhang, *The Adaptive Markets Hypothesis*, 2024. https://doi.org/10.1093/oso/9780199681143.001.0001
- Challet, Marsili, Zhang, *Modeling Market Mechanism with Minority Game*, 2000. https://doi.org/10.1016/S0378-4371(99)00446-X
- J. L. Kelly, *A New Interpretation of Information Rate*, 1956. https://doi.org/10.1002/j.1538-7305.1956.tb03809.x
- Thomas Cover, *Universal Portfolios*, 1991. https://doi.org/10.1111/j.1467-9965.1991.tb00002.x
- Helmbold, Schapire, Singer, Warmuth, *On-Line Portfolio Selection Using Multiplicative Updates*, 1998. https://doi.org/10.1111/1467-9965.00058
- Boyd et al., *Multi-Period Trading via Convex Optimization*, 2017. https://web.stanford.edu/~boyd/papers/cvx_portfolio.html
- R. Michaud, *The Markowitz Optimization Enigma*, 1989. https://rpc.cfainstitute.org/research/financial-analysts-journal/1989/the-markowitz-optimization-enigma-is-optimized-optimal
- *Random walk or chaos: a formal test on the Lyapunov exponent*, J. Econometrics, 2012. https://doi.org/10.1016/j.jeconom.2012.01.012

## Implementation status
**Analysis and preregistered hypothesis only. No new physics/HMM/entropy game-theory trading backtest was run or claimed.** All cited old 2017–2026 results remain exploratory for promotion purposes.