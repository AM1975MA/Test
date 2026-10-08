# L2-G — Causal teacher–student nonlinear stabilization: frozen protocol

Frozen 2026-10-08, before evaluating any L2-G candidate outcome; research writes ONLY to `AM1975MA/Test`; no writes to `Etf_trader` or `Trader_selector`. **Original149 burned**; results diagnostic, no live promotion. This phase attempts **training-time smoothing** of the noisy nonlinear XGB teacher and controls its incremental value over a direct nonlinear student.

## Hypothesis

XGBRanker's annual re-fits amplify tiny Yahoo historical vintage deltas (L2-D: 45–57% Top1 agreement). Its *out-of-fold* ranking scores might encode useful nonlinear structure. Train a **capacity-limited student** using only **past** teacher OOS signals plus economically mature historical ranks, thereby regularizing the fitted mapping directly, rather than posthoc score blending. Crucial: compare a matched direct student of identical architecture, because smoother behavior might come from model capacity alone.

## Exactly two candidates (no tuning)

- `HGB_DIRECT`: `HistGradientBoostingRegressor` with target **continuous 21-session realized percentile rank**; `SimpleImputer(strategy='median', keep_empty_features=True)` fitted on train only; fixed `max_iter=120, learning_rate=0.05, max_leaf_nodes=7, max_depth=3, min_samples_leaf=100, l2_regularization=10, max_bins=127, early_stopping=False, random_state=42`.
- `HGB_TEACHER50`: **same learner, fit, features and cohort**, but train target **0.50*realized_rank_pct_21 + 0.50*past_XGB_teacher_OOF_prediction_percentile**. Teacher percentile recalculated from each vintage's true source-only, annual out-of-sample XGB scores, cross-sectionally within signal date; never use teachers from the future or fitted on the same target date. 50:50 is fixed *ex ante* in this phase.

A theoretically useful teacher signal must stabilize across vintages despite noisy XGB fits, **without sacrificing top5 capture**. Otherwise conclude distillation failed.

## Matched cohorts / temporal logic

- Frozen 3 Yahoo acquisitions, original149 149 tickers, canonical 125 Compact21 features (L2-C formulation), same signal date/ticker in vintage-specific panels. Only rows with >=30 observed features.
- Annual fit at Jan1 **2019–2026**, with historical teacher OOF predictions from 2017 onwards. Use only signal_date<cutoff and exit_date21<cutoff, teacher from an earlier-year training fit itself strictly matured before its own prediction. Require >=12 past distinct months; otherwise no training.
- Evaluate identical signal dates **2019-01 through 2026-06** with 21-day exits <=2026-07-31. No adjustment for lookback when computing quality stats; samples identical for XGB, Ridge, student.
- All fitted preprocessing on training folds only. Never include ticker identity in the student features; same original 125 fields. Strict no teacher output at prediction time; student predicts from ETF features alone. Teacher data is one historical target transform.
- Keep 100% Ridge and XGB source-only predictions frozen as benchmark. No production strategy, portfolio optimizer, or look-ahead.
- For *same input* stability, use Repeat2 inference feature panels with the three independently vintage-trained students. Recompute predictions from each fitted student on that common input **before** inspecting the outcomes. Native predictions also retained.

## Fixed success gate for diagnostic continuation (ALL must pass)

1. 3 pairwise same-input student Top1 agreement >=90% (strong training robustness);
2. native rank MAD <0.01 (3 pairwise average);
3. selected ETF realized Top5 membership >= 15% of held-out monthly decisions (don't lose too much of XGB's ~19%);
4. selected realized 21d return mean >= that of Ridge on exactly matched dates.
5. No chronological leakage, duplicate keys, missing predictions, or unexplained rowset changes.

If fails, **do not alter model parameters, mix or thresholds**. Also compare `HGB_TEACHER50` to `HGB_DIRECT` as causal diagnostic for teacher contribution, still developmental.

## Metrics and inference

Date-weighted realized Top1 21d net return, Top5 hit, exact realized winner, selected percentile, regret, NDCG@5, rank IC; 3-vintage-mean per date (vintages NOT three independent market tests). Pairwise vintage Top1/rank MAD/Top5 overlap native+common. Paired calendar-date **3-month moving-block bootstrap** (10k deterministic draws) for Top1 return, Top5 and NDCG between each candidate and both controls; CIs descriptive and not multiple-comparison adjusted. Annual performance breakdown.

Econophysics check: regime state based **only on past SPY 21d rolling volatility** at each month-end, with threshold the **past 36 available month-end SPY vol21 median, shifted one date**; minimum 12 months available. Report hit and realized return, and vintage stability conditional on high/low past-volatility regimes. This diagnostic is fixed in advance; no regime gate alters the strategy or fits. Also report kurtosis / downside tail of selected realized monthly labels where sample supports (small-sample caution).

Risk validation: standalone Top1 next-open monthly proxy with exact entry/exit costs and no phantom terminal switch, monthly-sampled max DD clearly labeled, **not Hybrid24 CAGR**.

## Roles / analytical discipline

- ML: supervised teacher-student and truly OOF teacher, deterministic regularization and exact train cohorts.
- Economophysics: volatility clustering and shock regimes, nonlinear rank switching, regime conditional instability, heavy tails.
- Statistics: paired within-month vintage design, 3-month block bootstrap, 2019+ matched cohorts, uncertainty and no p-hacking.
- Risk and execution: next-open trade chronology, costs, annualized proxy vs full Hybrid24, downside tail & drawdown.
- QA: output hash, train cutoff audit, exact keys, independent baseline and transaction reconciliation.

Results in `L2G_RESULTS.md`, scripts+raw predictions in companion reproducibility package. **No promotion without new untouched prospective data.**
