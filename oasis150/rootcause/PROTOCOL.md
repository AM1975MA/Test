# OASIS 150: forensic root-cause review, frozen audit protocol 2026-10-18

This is a **diagnostic investigation**, not optimization. Source: complete seven-arm daily Open ledgers, frozen 150 fund price-coverage set and raw Yahoo-adjusted price CSVs at `oasis150/results/frozen/`, Action 39132785483. Source OASIS parameters will not change and NO performance-ranked winner strategy will be promoted. Analyze WHY the 150 run fails investor-relevant risk criteria.

Independent role partitions with separate machine-executed GitHub Action audit jobs:
- **DATA_AGENT**: verify 150/219 provenance, common history bias, actual ETF classes, FX/venue, dubious daily adjusted jumps and misleading observation quality.
- **SIGNAL_AGENT**: test whether as-of OASIS rank predicts cross-sectional *forward* 5/21 sessions log payoff, conditioned on broad-market stress; also measure realized incremental profit after switches and rank error against inactive no-switch. All forward returns only used in POST-RESULT diagnostic, not model.
- **RISK_AGENT**: quantify wealth drawdowns and recovery, concentration, crash state detection frequency through actual declining equity, false crisis/recovery exposure, exact loss event peak/trough.
- **EXECUTION_AGENT**: audit trading cadence, turnover, commissions, cash, holdings, stale prices and execution fairness; estimate where net advantage comes from rather than claim prediction.
Coordinator independently aggregates role-specific JSON findings into decision gates, including failures. Profiles in `.github/agents` are specifications; Actions run deterministic specialist audit scripts, **not eight separate independent AI model conversations**.

Explicit scientific hypotheses to falsify:
1. 63/126d **factor-adjusted trend** has little true 21-day cross-sectional predictive correlation; null H0 Spearman ≤0 averaged over non-overlapping month-end timestamps. If null not rejected, rank/switch policy has no business justification.
2. The pseudo-95% uncertainty adjusted relative opportunity difference is NOT calibrated: volatility of paired returns is aleatoric, not epistemic uncertainty of forecast; treating it as valid credible lower bound is unjustified.
3. The single composite market proxy spans 21 bonds/credit, 22 commodities/real assets, equities, etc.; beta can be economically meaningless across asset classes and panics. Examine cross-group and within-group signals and downside covariance, and loss by holding asset class.
4. 2 ETFs at ~100% equity, no position-level tail-risk/stops or per-ETF deterioration observer, 50% cash on only 142/2366 days. Crisis guard operates on *market-wide two-dimensional momentum + breadth*, not on individual portfolio losses. Its ~−59% peak-to-trough may primarily reflect unmonitored held risk not systemic aggregate market crisis.
5. Hysteresis may freeze stale positions even as relative forecast worsens because fixed Bonferroni simultaneous test on 150 reduces switching without forecasting improved probabilities; compare crisis transition reallocation to benchmark and switch ex-post relative returns.
6. Attractive relative performance is conditional on early 2017–20 history (+25% pa P3), while 2021–23 is negative and 2024–26 weak; must report per-period stability. P3 vs P4 similar ~10% CAGR yet much higher DD, cannot be recommended based on a 0.12pp CAGR difference.
7. Full-sample coverage and same-vintage adjusted Yahoo Open no-spread fills are hindsight-survivor filtered, never PIT / true EUR investable guarantee.

Freeze **no new winning thresholds** in this audit. Negative results must remain. Any future science iteration must first beat naive physical/mathematical controls on proper *prequential* predictive scores and conditional opportunity economics on a truly independent PIT dataset, BEFORE portfolio knobs.

Diagnostic code and results on `research/oasis150-root-cause-20261018`. Nothing in production is changed.
