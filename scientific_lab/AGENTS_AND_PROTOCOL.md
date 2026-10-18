# Scientific ETF Lab — multi-agent charter | frozen 2026-10-18

## Mission, scope and answer contract
Design a trading strategy that is *economically executable*, robust to minor data revisions, interpretable under model uncertainty and superior to predeclared controls **in future independently observed results**. Exploration on the 2017–2026 previously mined EUR60 panel cannot certify generalizable alpha. Never equate ex-post winner selection with feasible performance. Use `Test` only; never mutate `etf_trader` or existing prior experiments.

**This is a reproducible multidisciplinary agent organization**: the specialists have distinct responsibilities, gates and evidence artifacts. They are not a claim that eight simultaneous remote LLM agents were actually executed. The executable coordinator enforces their gates and builds a single outcome receipt; human/AI research roles can later run independently.

## Coordinator and team (eight specialist agents)
| Agent ID | Expertise and deliverable | Veto on |
|---|---|---|
| A0 COORDINATOR | experimental director; freeze questions, sequence independent arms, accept/reject with uncertainty; final transparent decision memo | post-hoc choice of global backtest winner |
| A1 PIT_DATA_AUDITOR | provenance, ISIN uniqueness, European underlying/venue EUR, survivorship and timestamp; hash sources; eligibility | data leakage, future membership conditioning in deployability claims |
| A2 CAUSAL_EXECUTION_ENGINEER | signal close -> next common open -> next common open, share weights, cash, 10bp one-way turnover, independent original parity | hidden reinvestment assumptions, incorrect fees, impossible trading prices |
| A3 PREDICTIVE_RANKING_EXPERT | keep and stress frozen R_H ranker; evaluate top1 forward returns, turnover; independent hysteresis selection only | blending model layers before identifying driver |
| A4 STOCHASTIC_STATE_SCIENTIST | Student-t Kalman posterior predictive uncertainty; compare plain historical vol and prediction-interval calibration | using future data, Kalman opacity with no value over volatility |
| A5 COMPLEX_SYSTEMS_SCIENTIST | covariance eigen-entropy, random matrix shrink, filtered shared-market regimes | thermodynamic/chaos analogy mistaken for proof of alpha |
| A6 ROBUST_CONTROL_ENGINEER | causal weight policy, hard caps, simple 0%-yield EUR cash assumption, limit turnover, distinguish sizing and selection | unsupported cash carry, tacit leverage, missing costs |
| A7 ADVERSARIAL_VALIDATOR | synthetic future-mutation tests, economic parity, 12m circular-block paired CI, subperiod stress, risk scoring, dataset caveats | overfit, data-snooping, cherry picking, promotion without untouched holdout |

Each specialist's evaluation corresponds to code-separated functions and independently logged outputs in `scientific_lab/run.py`. The coordinator's output is a **research decision only** and does not make trading recommendations.

## Primary hypotheses (frozen before Action result)
H0: baseline R_H Top2 unchanged, equal 50/50 shares, fixed next-common-open monthly execution.
H1: **risk-only historical inverse volatility** on same Top2, 20–80% weight cap. Simpler yardstick; do not confuse generic risk parity with Kalman edge.
H2: **Kalman posterior predictive uncertainty** as inverse-risk weighting on the **same** R_H Top2 and same cap. If H2 improves H0 but not H1, the Kalman-specific hypothesis fails.
H3: **shared-market observable regime circuit breaker** on H0 Top2, strictly signal-date information. When EW-market proxy below 200-observation mean **and** 21-observation vol above 126-observation vol, hold 50% 0%-yield cash, 50% H0. Fully risk-on otherwise; never leverage. This is a crude crisis guard, not a forecast of peaks.
H4: **eigen-entropy concentration gate** H0 Top2, only after 126-observation shrinkage-correlation data are available; if effective-rank fraction below 0.25 and recent vol above long vol, use 50% zero-yield cash. Otherwise H0.
H5: **hysteresis selector**: retain previously owned R_H Top2 names only while still in current top-5; fill remaining with current leaders; otherwise fixed 50/50. This isolates selection turnover.
H6: **one two-layer interaction** Kalman risk weights H2 combined with independent H3 regime filter, for attribution only, explicitly not a result-selected optimizer.

If any arm fails reproducibility, repair implementation without looking at outcome. Do not tune cap/threshold/frequency to maximize hindsight CAGR. Negative results are accepted. Adding more arms later requires a new protocol and an independent future holdout; historical best-of-7 is not future expected alpha.

## Economics and integrity
- Source: frozen `data/eu120/raw_ticker_csv`, 60 retrospectively selected Europe-labelled tickers; code and prediction artifacts from Actions 39071370480, 39084898663 and 39087987551.
- Time: exactly 113 observed monthly entry/exit open intervals. Derive risk inputs only from closes <= current signal date.
- Revenue: original frozen R_H scores, not refitted new labels; no trading intramonth unless specified.
- Portfolio weight: sum risky ETF allocations <=1; residual is 0%-yield notional EUR cash. This is a **model assumption, not investable product**. Daily/monthly Sharpe comparison is incomplete if cash carry is unknown; never silently use BIL.
- Costs: 10bp one-way on half-L1 turnover, include entering cash as part of turnover. On first month initial previous composition = 100% cash; charge entry cost. Baseline parity check must use old 50/50 reference implementation (which starts with prev empty and charges 0.1% on 0.5 turnover). After initial parity, all arms use identical ledger convention. Changing convention relative to old reference by half fee on first month changes CAGR microscopically, document explicitly.
- Risk: report CAGR, monthly MaxDD, Sharpe, annualized turnover, exposure, worst year, month-level 95% tail loss/ES, paired 12m-block CI vs H0, 2017–2020 / 2021–2023 / 2024–2026 subperiod returns, duration in cash.
- No independent holdout: do not claim statistical validation of alpha. Require future observation or a genuinely independently curated point-in-time dataset.

## Sequential gates
1. Baseline parity (original reference CAGR 9.978039091271884%) and no lookahead synthetic test; report blocking issues.
2. Run standalone H1/H2/H3/H4/H5 and blinded predeclared H6 **without hyperparameter search**. Print all results; compare with H0.
3. Inspect failures separately: if H2 no better than H1, reject Kalman as economic risk observer despite lower historical DD; if entropy concentration offers no incremental risk predictive skill, retain only as diagnostic.
4. Analyze out-of-time slices and paired uncertainty without reconfiguring arms.
5. Coordinator's resolution uses directional evidence plus economic/risk assumptions, NOT “highest old CAGR”.
6. Save source, inputs hashes, signed results, dates, notes and next falsification gate in Git branch; no PR merge.

## Provenance guardrails
EUR60 was curated with knowledge of 2026 historical series. Some securities may be overlapping ISINs or underlying non-Europe despite EUR quote. This lab is development only. The absence of point-in-time ETF births/delistings and independent quote-currency proof prevents honest “live-ready” status, even if CAGR is appealing.

## Referenced foundational theory
- Robust state estimation and Student-t influence, not exact general stochastic volatility.
- Hamilton filtered Markov regimes; using same-date filtered information only.
- Covariance matrix eigen-entropic effective rank and random matrix noise filtering.
- Multiplicative online expert updates reserved, **not tested** in this initial experiment, because its payoffs must be matured before adjustment.
- PnL path risk and cost constraints as in convex stochastic portfolio control.

**Acceptance language**: `PROMISING_RESEARCH_SIGNAL` means survives internal diagnostics yet remains unvalidated for real money. `UNVALIDATED` means no independent forward validation. `FAIL` means an integrity gate failed and results cannot be interpreted.
