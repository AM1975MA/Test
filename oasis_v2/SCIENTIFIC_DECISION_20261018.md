# OASIS V2 — scientific verdict and next research design
18 October 2026 | Branch research/oasis-v2-paired-forecast-g1-20261018

## Executive decision
**Partial structural research success; predictive economic-alpha goal NOT MET.** This is a significant change in the *survival mechanics* and a useful science filter against false alpha, NOT a proof of superior investable returns or an answer to future ETF switching opportunities.

All user/project data remain on isolated GitHub research branch of AM1975MA/Test. Old etf_trader production is unchanged.

## Precisely what ran
1. Frozen BEFORE test: oasis_v2/g1/PROTOCOL_FROZEN.md; Action [39136487959](https://github.com/AM1975MA/Test/actions/runs/39136487959), 150 ETF, 64 non-overlapping 21-session prediction anchor dates 2021–2026, **5,120** logged pair predictions. Models null-prior, simple raw trend logistic, group-factor residual logistic, hierarchical regime logistic, Student-t generative. No mature future label training leakage: fitting uses only realized label endpoints strictly before signal close; as-of quote mutation invariants tested.
2. Frozen BEFORE G2 run after G1 failure: oasis_v2/g2/PROTOCOL_FROZEN.md; Action [39137020695](https://github.com/AM1975MA/Test/actions/runs/39137020695), 150 ETF, 2,366 daily next-open wealth samples for seven matched portfolio risk arms, original P0 replay economically reconciled to within 3.6e-15. No G1 failed signal ever fed into investment policies.
3. Post-result passive and era audit Action [39137356154](https://github.com/AM1975MA/Test/actions/runs/39137356154): full 5,120 G1 records, all 7x2,366 G2 daily ledgers and SHA256 manifests retained in oasis_v2/receipts/frozen.
4. Preregistered cross-roster stress AFTER 150 results: oasis_v2/g2/TRANSFER69_PROTOCOL_FROZEN.md, Action [39137733489](https://github.com/AM1975MA/Test/actions/runs/39137733489). **69 other ETFs**, exact original model costs, dates and source-vintage, six broad categories including only two US-sector ETFs. Independent old OASIS P0 reference matches to floating exact zero. The original researcher has already accessed the wider 219 cohort, so 69 is NOT untouched prospective data and full-period survivors remain a bias.
5. Permanent 69 ledger and 150-versus-69 manifest with SHA256 Actions [39137923278](https://github.com/AM1975MA/Test/actions/runs/39137923278), folder oasis_v2/receipts/transfer69.

These are deterministic Python experiments and GitHub Actions jobs, not independent parallel LLM subagent conversations. Previous specialized agents' quantitative audit findings were material for the hypothesis; we did not claim to summon an independent autonomous agent team.

## G1 scientific prediction verdict — FAILED

The target was P(candidate beats already-held ETF by >0.3% in 21-session net log payoff). Chronological after-training-only predictions on *incumbent-challenger task*, 1,024 pairs over 64 sampled anchor dates:

| Method | Brier lower better | Log-loss lower better | AUC |
| --- | ---: | ---: | ---: |
| H0 empirical matured-label prior | **0.247252** | **0.687674** | 0.4044 |
| H1 raw momentum trained 21/63/126d | 0.247980 | 0.689097 | 0.4920 |
| H2 group factor-adjusted logistic | 0.248549 | 0.692533 | **0.5404** |
| H3 hierarchical regime interactions | 0.255549 | 0.707486 | 0.5081 |
| H4 Student-t generative proxy | 0.253443 | 0.700219 | 0.4936 |

- During 2021–2023, H2 did temporarily improve Brier vs null (**0.24449 vs 0.25051**) and AUC reached 0.5833. During 2024–2026, H2 collapsed (**0.25345 vs 0.24332**, AUC 0.4661).
- H2 average anchored Brier reduction vs null **−0.001297** (negative is worse), exploratory 3-anchor 95% bootstrap CI **[−0.01183,+0.00857]**. No scientifically supported alpha.
- Only **one** H2 shadow opportunity exceeded predeclared 0.65 conditional probability, 10-point lead to baseline and positive model mean, and it subsequently won; one success has no statistical relevance. No real P&L portfolio was simulated on the FAILED G1 forecasts.
- **G1 final: STOP predictive promotion.** Do not use these probabilities to control investments, reinterpret discriminative AUC as net utility, tune confidence thresholds or test 100 new hyperparameters on same 2021–26 labels. The next model requires materially better **causal information**, including asset-class relevant macroeconomic factors, term structure for bonds, commodity curves/roll costs, relative fund flows, volatility surfaces or realized breadth/credit liquidity; introduce only if historical as-of availability can be verified. A new dataset and real prospective future months are indispensable.

## G2 independent capital survival: structural improvement vs old concentrated reference

Same frozen **weak** price-only ETF score, no new forecasting gain. USD US-listed adjusted Open next-day opening portfolios, 0.10% commission per trade side, 0%-yield cash proxy:

| Policy | 150 CAGR | 150 daily MaxDD | 150 daily Sharpe | 69 CAGR | 69 daily MaxDD |
| --- | ---: | ---: | ---: | ---: | ---: |
| R0 old two concentrated ETFs | 8.34% | −44.95% | 0.252 | −0.28% | −64.37% |
| R1 top six ETF overall equal | 11.37% | −35.85% | 0.457 | 14.01% | −33.38% |
| **R2 one ETF per macro asset class equal** | **10.70%** | **−28.25%** | **0.639** | **9.02%** | **−28.23%** |
| R3 same six diversified, inverse 63d volatility ≤25%/ETF | 9.54% | −24.25% | 0.678 | 9.75% | −25.51% |
| R4 same R3 at fixed 75% risky, 25% no-interest cash | 7.23% | −18.51% | 0.696 | 7.36% | −19.45% |
| R5 R3 with model Student-t(5) 10%-tail expected-loss budget | 8.54% | −24.06% | 0.625 | 8.64% | −24.72% |
| R6 old Top2 with Student-t ES budget | 7.68% | −27.20% | 0.403 | 0.96% | −41.78% |

- Structural number-of-holdings/class effect robust **directionally** in both previously known universe fragments; R2 reduces sampled maximum DD vs Top2 by ~16.7pp and ~36.1pp respectively.
- R2 and R3 **never satisfy positive alpha forward-validation**: in 150, 12-month-block paired monthly log return bootstrap intervals vs R0 each include zero; in 69, R2 and R3 paired intervals vs R0 also include zero. There are many inherited fund and sector common factors, so not independent 219 years or paths.
- Student-t ES model R5 is NOT an incremental economic breakthrough; it trades on 305 days rather than R3's 114, slightly reduces DD but lowers CAGR materially. R6 traded on 1340 days and damages Top2 strategy. Retain its model-implied ES only as diagnostic until prediction calibration.
- R3 150 CAGR 9.54%, DD −24.25%; 69 CAGR 9.75%, DD −25.51%. Very similar risk profile across the two partitions; this is credible *descriptive structural risk evidence*, not return predictability.
- Both R2 and R3 are fully exposed ~99.8% risky, so improved DD is primarily broad-class risk redistribution, not cash deflation.

### Important passive comparison, no trophy for beating a broken model
Buy-and-hold same-vintage USD-adjusted SPY = **15.25% CAGR / −32.05% daily DD**; static 60% SPY + 40% AGG = **11.39% CAGR / −23.55% daily DD**. The latter has BOTH higher historical CAGR and less severe drawdown than R2 and R3 in 150. The passive proxy does not include exactly matched monthly fees, real spreads, taxes, fixed EUR base FX or broker execution; cannot claim full economic domination as a live Italian-investor strategy, but strongly weakens any strategy "winner" assertion.

Historical era R2 sample annualized returns: **11.03% 2017–2020; 3.18% 2021–2023; 20.00% 2024–2026**. This is regime unstable; no proven alpha despite improvement vs original reference.

## Financial-science revised architecture (not yet validated)
A) **Core first:** six nonduplicated economic risk classes with one ETF/group, capped inverse vol and simple 60/40 passive controls. Keep broad exposure governance independent of any alpha signal. A group is not a safe asset by name; correlated crisis stress required. Current R2/R3 are candidate *controls*, not signed-off trade strategy.

B) **Opportunity module separate, usually OFF:** do not enter directional deviations unless a new, independent information model passes prequential proper-score and paired net-win-when-switch testing against matured-label null AND simple category trend across multiple market regimes. "No informative edge" means no active switch, not "try next ML filter."

C) **Credibility filter and local crisis:** model the trustworthiness of **each ETF's** downside and own prediction residual, not a single equal-weight synthetic overall market regime. Research 21d downside covariance and idiosyncratic change points, conditional expected shortfall and max concentration, but compare against basic fixed cash and conservative equal-risk benchmark to detect valueless sophistication. Must preserve as-of/broker time and calibrate risk scenarios.

D) **Switch only after B succeeded:** probabilistic paired advantage beyond real bid/ask, FX and commission, expected opportunity duration, conservative posterior or proper conformal error *calibrated on matured prequential labels*. Economic hysteresis results from the transaction-cost no-trade region, not an arbitrary Top5 threshold.

E) **G0 data prerequisite:** Entire existing 219 archived US ETF list used full 2017–2026 coverage and excludes funds born during that period. Source stops 2026-07-01, while decision date is 2026-10-18. This corpus cannot evaluate *discovery of genuinely new ETF issues*, survivorship exits, European EUR venue, actual taxes and liquidity. Use new point-in-time ETF launch/delist/ISIN and contemporaneous macro factor dataset, with untouched months. Merely adding the 69 current survivors does not fix this.

## Next minimum test to justify any new trading algorithm
- Build compliant new PIT EU venue/ISIN source and dynamic ETF eligibility that includes new and defunct funds as-of, with EUR cash return, real close/open and bid-ask, deterministic snapshots and hashes.
- Record independent prospective prequential 5-/21d pair log advantage forecasts and economic uncertainty before outcome, per class and regime; independently compare logloss, Brier, false-alarm rate, realized net replacement win rate and block-bootstrap skill.
- Build daily conservative risk overlays versus true exposure-matched diversified and simple SPY/AGG 60/40 controls. If no forecasting skill, actively refrain from switching.
- No claimed net-alpha discovery now. Previous research source, protocols and full outcome receipts persist.

**Key science lesson:** the strongest measured gain came not from a better price predictor but from reducing the degrees of portfolio-level concentration. The real predictor remains unproven. Recognizing this is scientifically preferable to a more impressive retrospective CAGR that fails simple proper scoring and passive benchmarking.
