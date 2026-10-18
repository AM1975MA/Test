# OASIS V1 failed: four-agent scientific root cause, and OASIS V2 research direction
Date: 2026-10-18. Branch: \`research/oasis150-root-cause-20261018\`. Status **STOP V1 TRADING RESEARCH / REBUILD CORE SIGNAL & RISK**.

## Traceable reviews actually run
Four independently executed deterministic quantitative audit jobs (DATA_AGENT, SIGNAL_AGENT, RISK_AGENT, EXECUTION_AGENT), followed by the coordinator's gate verdict. GitHub Actions [39133850072](https://github.com/AM1975MA/Test/actions/runs/39133850072). Each archived \`oasis150/rootcause/results/{DATA,SIGNAL,RISK,EXECUTION}_AUDIT.json\` and \`SCIENTIFIC_COORDINATOR_DECISION.json\`, with hashes. The GitHub \`.github/agents\` profiles were **consulted as review responsibilities**, but NO parallel independent LLM agent conversations were instantiated. Do not misrepresent executed Python auditors as LLM experts.

The seven OASIS trade arms themselves are immutable, full 2366-day ledgers archived under \`oasis150/results/frozen\`, successful originating [39132785483](https://github.com/AM1975MA/Test/actions/runs/39132785483). No model parameter tuned after seeing performance. All tests are retrospective and cannot establish deployable performance.

## Severity 1: Information failure, BEFORE decision layer
- Original signal \`oasis/observers.py\` computes fixed one-sided 21/63/126d factor-adjusted trailing momentum with historical realized-volatility penalty. This is a score **heuristic**, not a calibrated forecast of relative expected NET gains.
- Mean cross-sectional Spearman (as-of score vs subsequent 21-session executable next-Open/next-Open gross log payoff), taking every 21st day to limit overlapping forward labels:
  - BREATHING **+0.01424** across **96** nonoverlapping sampled dates.
  - SHOCK **+0.1198** across **7** dates — too few for a stable finding.
  - CONTINUATION **−0.1716** across **2** dates — too few.
  - RECOVERY **−0.2620** across **7** dates — too few.
- For 96 BREATHING points, the score's Top2 mean gross next-21d log return was **−0.00292** (−0.292 percentage log points) **relative to contemporaneous cross-sectional median**. This is directional evidence against exploitable long-only excess payoffs on the easiest subset, not a statistical proof of negative alpha.
- The score does NOT generalize obviously within asset classes either; small held-out group sample + correlated ETFs make naive Spearman unreliable. Report group details in SIGNAL_AUDIT.
- **Economic switch quality (direct decision diagnostic):** 49 one-for-one switches in BREATHING with 21-day realized NEW-minus-SOLD log gain **−0.00335** on average; just **42.9%** positive. 2 SHOCK switches **−0.2021** average log disadvantage; 5 RECOVERY switches **−0.0448** average, each tiny subset. Gross, **before** switch transaction costs. Both “noisy score” and “switch as if forecast credible” are failures.
- A z-score from historical paired *return variance* is not a valid standard error for the model's forecast. Existing code's Bonferroni-adjusted "credible lower bound" is not credible in the statistical sense until residual out-of-sample calibration validates it. More mathematics on an uninformative \`score\` cannot manufacture net alpha.

**ROOT CAUSE:** no proven point-in-time conditional ranking skill, calibrated *paired* utility distribution or ability to distinguish transient bounce from durable relative growth. OASIS attempted optimal decisions without a trustworthy information layer.

## Severity 1: Risk engine detects the wrong target
- \`P3_OASIS_CRISIS_ACTIVE\` max daily sampled DD **−59.06%**, from 2022-08-26 peak to 2025-04-07 trough = **654 trading sessions**.
- Within this episode, system recognized market systemic crisis on only **11 sessions**. Its mean portfolio risky exposure stayed **98.96%**, and risky exposure was materially reduced on **1.68% of the drawdown window**. Trough held \`EWO;FXI\`.
- **None of P3's ten worst daily portfolio log returns were classified as market crisis**. Major one-day losses occurred when holdings included GDX/SLV, SMH/REZ, SMH/DXJ, UNG/TAN, even though the aggregate market proxy was labeled \`BREATHING\`.
- Current risk gate uses aggregate breadth, common proxy's 21d momentum and a coarse volatility HMM. It does **not** estimate conditional expected-shortfall of ACTUAL held positions, concentration, idiosyncratic deteriorations, adverse price jumps or synchronized downside correlation. All portfolio risk is allowed in ostensibly ordinary markets. Two ETF weights ~50% each, fully risky almost always.

**ROOT CAUSE:** conflation of systemic stress detection with the actual portfolio survival budget. A stock/bond/commodity equal-weight proxy may classify a commodity-specific crash as noncrisis; a two-ETF book can then suffer enormous losses at maximum allocation.

## Severity 2: Economic decision layer does not add meaningful value
- Exact same data/cost/calendar OASIS P3 vs *monthly selector with same crisis overlay* P4:
  P3 CAGR **10.1663%**, daily MaxDD **−59.0585%**;
  P4 CAGR **10.0502%**, daily MaxDD **−46.0872%**.
  P3 gains only **0.116 percentage points CAGR**, while sampled MaxDD worsens by **12.97 pp**.
- P3−P4 log-wealth gain over complete period: **+0.009925**, too small to declare meaningful alpha after selection/test multiplicity.
- P3 makes 57 name switches; P4 monthly 101; turnover not sufficient justification for worse holding-specific risk. Relative-hysteresis vs monthly-only without risk overlay P2−P0 gains historical CAGR just ~0.16pp at much worse DD.
- Frozen wide paired 12-month block bootstrap of P3−P0 monthly log gains **includes zero**. No statistically established novel alpha.
- Decision frequency and hysteresis are downstream knobs. Replacing Top5 with fancy “optimal switching” is not itself alpha. A calibrated distribution of the **incumbent vs candidate** net opportunity must come FIRST.
- Shock/continuation/recovery regime blocks may show gains but have few genuinely independent crisis episodes. Their effect should be evaluated at event level not with daily overlapping labels.

## Severity 2: Data and evaluation are insufficient for intended discovery
- 150/219 chosen by WHOLE-SAMPLE 2017–2026 price availability. All 150 had 2366 observed Open/Close sessions and positive observed Volume. This **deliberately excludes every ETF born after 2017**, eliminating exactly the new fund opportunities the user wants to monitor.
- The universe includes 24 US broad, 35 US sector/theme, 28 developed global, 20 emerging, 21 bonds/cash/credit and 22 real assets. A single “synthetic market index” blending their returns has no stable portfolio hedge identity. Treating it as a factor in every ETF is economically questionable.
- Same-vintage adjusted OHLC is internally consistent, but does NOT prove past executable bid/ask, historical fund eligibility, unique underlying ISINs, regulatory status, EUR cash returns or FX conversion to a Euro investor.
- 7 daily adjusted Close-to-Close log changes exceed 25% in absolute value (SLV, USO, UNG, REM, EWZ, GDX); review for genuine gaps/adjustment errors, do not uncritically remove large valid crashes. No claims of the price source being corrupted until verified.
- This already-mined 2017–2026 panel has no hypothesis-untouched prospective sample. Even the 150-ETF transfer test is not independent of prior design exploration on EUR60.

## Decision: kill the wrong science, not just the wrong hyperparameters
**DO NOT** sweep Top5/Top10, 50%-cash fraction, 21 vs 63 day momentum, HMM parameters or asset weights on the burned historical 150 until a new info generation gate is passed. The V1 implementation should be kept for regression and negative controls, **not** promoted to production.

### New architecture OASIS V2: scientific gates, not a layer cake

**G0: Data fidelity and dynamic ETF opportunity universe (prerequisite, FAIL as of now).**
- Make a point-in-time register of ETF ID/ISIN, actual market symbol, underlying geographic/style and asset category, quote currency, inception/listing/delisting, true tradable OHLC bid/ask or conservative slippage and dividends/adjustments.
- At each date only ETFs that already existed and had observed data may be candidates. ETF births are allowed; dead/de-listed funds retained historically. Separate actual EUR-listed investable universe from a USD/global comparative lab. Do not use today's surviving ETF membership to choose past trading universe.
- Exact executable trade timeline, align exchange calendars and FX daily closes, verified cash alternative. Reconcile 7 extreme moves before model testing.

**G1: Information and signal validity FIRST (no portfolio backtest before passing).**
- Predict **paired net relative log growth** for candidate i versus currently held j over predeclared 5 / 21 session horizons, conditional on actual group factor and state; NOT next absolute winning ETF and not a single 150-wide momentum sort.
- Represent paired forecast as calibrated predictive distribution:
  \`P_t(Delta log W_ij(h) > spread+fees+FX)\`,
  \`E_t[Delta log W_ij(h) - costs]\`, conditional tail quantile and uncertainty.
- Start with three falsifiable models: (a) zero-alpha / shrinkage-no-change, (b) simple conditional residual trend 21/63 days, (c) robust hierarchical Student-t latent drift and state-space *conditional model*; add complexity only after prequential proper log score, event Brier score, empirical interval coverage and realized economic paired switch advantage beat plain controls. Asset group-specific common factors; no single equity/bond/oil beta.
- Hierarchical shrinkage across assets/market states to prevent fitting separate rich models on 2 independent continuation crises. Event alerts based on sequential innovation calibrated on training data; data-adaptive FDR/e-process optional ONLY after proper calibration.
- Economic opportunity duration is modeled via survival/competing risks once there are sufficient events, not guessed from momentum slope.

**G2: Portfolio-specific survival and risk budget (separate from alpha).**
- Daily as-of conditional covariance and downside joint tail scenarios of **current holdings**, e.g. shrinkage + Student-t heavy tails, conservative stress/factor shocks. Evaluate conditional portfolio expected shortfall, worst case per asset and posterior regime change, plus time underwater.
- Research policy benchmark should not concentrate 100% in two high-tail ETFs. Compare precommitted 4–8 positions with *per-ETF cap* (e.g. 20–25% before any backtest) versus existing Top2; a robust risk budget reduces position/exposure when predicted tail loss breaches preset risk tolerance regardless of systemic market label.
- Defensive option requires actual verified currency and execution; 0% hypothetical cash cannot prove implementable EUR defense.
- Compare matched exposure and realistic turnover so “protection” is not just under-investment.

**G3: Active crisis exploitation = distinguish mechanisms, not naive panic-buy.**
- Parallel independent filtered observers: (i) broad systemic regime, (ii) asset-specific deterioration/volatility shock, (iii) *relative* cross-sectional resilience and recovery hazard vs appropriate peer group.
- Shock: decrease exposure when held portfolio's conditional tail risk exceeds budget; do not automatically rotate into an arbitrary new “winner”.
- Continuation: look for validated resilience/durable outperformance relative to the incumbent; if no credible alternative, prefer risk-reserve rather than forced activity.
- Recovery: seek early improving residual drift and widening participating market breadth, but require *prequential* evidence that this signal beats a simple 21d reversal/momentum baseline.
- Regular observation can be daily; trades only at feasible next market open when economic gain clears rigorously tested decision hurdle. Event-level evaluation around shocks/recoveries, not multiple overlapping label rows.

**G4: Impulse control / dynamic hysteresis LAST.**
- With accepted calibrated \`Delta Q_{i,j}(h)\`, solve sequential accept/hold/reduce/rotate decision with crossing cost (commission+bid-ask+tax if relevant), expected survival of opportunity, epistemic uncertainty penalty and position-specific ES budget.
- Mathematical analogy: metastability/no-trade region from optimal switching with transaction costs is appropriate; thermodynamic entropy is *only* a proxy for correlation concentration, not market “temperature”.
- Do not set thresholds by V1 CAGR. Set them by predeclared acceptable false-switch incidence and cost recovery in training, and validate on fresh data.

**G5: Independent validation before deployment.**
- Immutable chronological as-of predictions (persist every daily score before knowing next 5/21 sessions), embargo overlapping labels, rolling retraining, no retrospective strategy selection, multiplicity correction.
- Report realized NEW−HELD relative net log payoff, calibration/Brier/log score, crisis-event conditional skill, fraction of economically significant opportunities captured, delay/regret, fees, daily ES/maxDD, concentration, worst-day controls and survivorship.
- Compare against a risk-matched mix of passive broad index/cash, a naive daily 21/63d trend, a conservative monthly selector and never-trade comparator; avoid directly comparing EUR60 and USD150 backtests with differing sources/execution.
- For live promotion require a genuinely untouched future/instrument cohort with verified PIT fields and realistic spreads; stop if calibration or tail-loss gates fail.

### Resource allocation (no premature complex agents)
Lead numerical QA (G0), probabilistic forecasting (G1), risk physics (G2), regime/event scientist (G3), causal execution & falsifier (G5), with scientific coordinator veto. Only activate dynamic switching optimization G4 **after** G1 AND G2 produce evidence. This is a research program, not a promise that data contain exploitable alpha.

## One-line lesson
**An elaborate switcher cannot create an advantage its predictor cannot see. A market crisis flag cannot protect a portfolio whose own risk it does not measure.**
