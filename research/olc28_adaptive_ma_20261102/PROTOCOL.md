# OLC28 — adaptive moving-average information audit (pre-outcome protocol)

2 November 2026. Exploratory after OLC27 negative results; old EU165/USA149 history is repeatedly researched, NOT an untouched validation sample. Parent OLC27 914fc42769be9a173e438279bbe44a112e981e22. No main changes, no orders or trading. Freeze OLC19 archived EU/USA STATE_HALF Close/Open and EU observed mask, canonical OLC27 AUTH FUSION, frozen AUTH Top5.

## Fixed indicators and causality
Use only daily Close at or before the monthly signal date, never current or next entry Open:
- KAMA efficiency ratio ER10 = abs(C[t]-C[t-10])/sum(abs(diff(C)),10), denominator zero -> 0.
- KAMA(10; fast2, slow30) five-session price-normalized signed slope, with squared adaptive smoothing coefficient. Require contiguous valid input; missing history => no signal.
- EMA20 minus EMA50 divided by Close (20/50 crossover is deterministically present in the original ema_gap20/50 inputs).
- HMA20 five-session signed slope divided by Close, HMA= WMA(2*WMA(C,10)-WMA(C,20),round(sqrt20)=4).
EU uses original observed quote mask, USA requires prepared positive finite quotes (original observed mask unavailable); no filling missing market data.

## First-stage incremental-information diagnostics
Check exact algebraic redundancy of EMA crossover with archived ema_gap20/ema_gap50. Compare ER10 with existing efficiency21/63/126 proxies. Compute cross-sectional monthly Spearman information coefficients for all available ETF scores and for AUTH Top5 on the *next execution Open-to-Open* gross return, with 2021–2024 primary; 2019–2020 and 2025–2026 held as separate already-inspected diagnostics.

## Chronological one-step pilot
For each model year 2021..2026, pooled EU+USA, fit weighted ridge alpha=10, standardized on training data only, trained on past Top5 candidates with known next-month Open-to-Open gross outcomes (both entry Opens observed EU; finite positive USA). Each market/month gets equal training total weight. Only events where the actual next entry date is strictly BEFORE Jan 1 of model year may enter training. Baseline FUSION-only ridge, four one-feature variants (ER10, KAMA slope, EMA spread, HMA slope). Exact same rows and training recipe for all models; no threshold, weight, market-specific model or hyperparameter search.

Decision proxy: rank only original AUTH Top5 and take top two predicted returns, equal-weight gross next-month Open-to-Open, with no protections, V6 or trading fees. Compare both against unmodified AUTH Top2 and the FUSION-only ridge. It is a diagnostic upper/middle-layer research proxy, NOT a full backtest or evidence of live alpha.

Only if a prespecified single feature improves both EU and USA against both references in 2021–2024 should a separate preregistered full OLC19 replay with V6, FAST_LOCK3/ALARM and fees .001/.003 be considered. Negative and unchanged results must be preserved. No lucky post-outcome variant selection.

## Limitations
No fresh holdout; share/multiple-test biases, historical ticker survivor bias, missing original US quote masks, imperfect FX/total-return and execution realism remain. "Lag reduced" is not "causal forecast" or necessarily fewer whipsaws. Crossover observations are not orders or automatic vetoes.
