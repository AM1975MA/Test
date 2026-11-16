# OLC111 — A bounded experiment in daily cash, hold and fresh-entry decisions

**Design only, 16 November 2026. No new financial returns or model fits were calculated for this memo.**

## Recommendation

Run one nested information experiment, with prediction measured before a portfolio result is interpreted: **PRICE_ONLY, PRICE_PLUS_LEGACY_VIX and PRICE_PLUS_LEGACY_AND_TERM**, using exactly the same small regularized action-advantage model, candidate generator, labels, account engine and decision rule. The legacy block is log VIX level and its21-source-session log change; the new block is only `log(VIX9D / VIX)` and `log(VIX / VIX3M)`. Do not search thresholds or add VVIX/SKEW after observing results. Those downloads can remain archived but unused. These are the root investigator's final implementation rulings; the separately frozen executable protocol is authoritative.

The question is whether these two inputs improve the economic decision to keep the actual account, move it to cash, or buy today's fresh basket from the already frozen selector. This is a falsification experiment with a weak prior probability of success. It is not a forecast that CAGR will reach 30%.

The strongest reason to proceed is a genuinely distinct information block combined with a daily absolute cash decision. The model family itself is deliberately ordinary. If the additional information does not improve forecasts and decisions, changing the learner's name or increasing its complexity would not repair that result.

## What is, and is not, new

Repository history establishes substantial negative prior evidence:

- OLC02/04/23 already tested HOLD versus SWITCH, relative proposed-versus-held features, age/overlap, paths, peers and market features.
- OLC69/70 already included broad-universe momentum breadth. OLC70 took real-account snapshots including units, cash, locks and pending state, then consolidated the selected native branch. Most action-difference forecast errors were worse than a training-only mean.
- OLC74 already tested pairwise Ridge/Logit, broader cross-sectional training, monthly weighting and same-state native action labels.
- OLC99 already tested small-feature economic Ridge reranking and 1,780 native individual counterfactuals. More training rows and replacing simple returns with native utility did not establish incremental skill.
- OLC34 already added prior-session VIX Close and its 21-session log change to a monthly relative-return classifier. It did not establish useful incremental policy value. Its documented inputs did **not** include VIX9D, VIX3M or their term-structure ratios.

Therefore actual-account state, common counterfactual origins, mature labels, breadth, shrinkage, a HOLD action and a VIX level are correctness controls or prior art, not novelty. The narrower new hypothesis is **daily absolute cash/entry value conditional on short-versus-medium option-implied volatility**, tested against the identical model with price features and the already studied VIX level/change block. The experiment does not establish that options information is generally useful, or that a global US options signal must transfer to every EUR-listed ETF exposure.

These are findings from the restored OLC reports, not results transplanted onto the current V3 ETF sample. See `../history/sources/OLC34*.md`, `OLC70.md`, `OLC74_REPORT_IT.md`, `OLC99_REPORT_IT.md`, and the history agent's source manifest.

## Three possible approaches

| Approach | Value | Main limitation | Decision |
|---|---|---|---|
| **Regularized one-step economic advantage with a new options-information block** | Directly compares native net wealth from legal actions; small enough to audit; separates new information from model changes. | A one-step advantage against a frozen continuation is not the value of a fully optimal daily policy. | **Recommended first experiment.** |
| Finite-horizon continuation-value learning, with one or two fitted policy-improvement rounds | Can account explicitly for waiting, later reentry and switching opportunities. Least-squares continuation estimation has a well-established methodological precedent in optimal stopping.[W3] | Few independent paths, maximization bias, policy-dependent state coverage and recursively estimated targets. A good backtest can arise without a reliable value function. | Defer until simple advantages show predictive value. Do not use deep RL here. |
| Separate probability-of-loss and gain/loss-size models | Makes the distinction between frequent losses and economically costly losses explicit. Could distinguish a high crash probability from a still-positive expected payoff. | More parameters, sparse extreme-loss labels and unstable tail-size estimates. Classification accuracy can improve while expected wealth deteriorates. | Useful explanatory diagnostics, not a second optimized strategy family now. |

Cost-aware dynamic trading research makes existing holdings and trading frictions part of the decision problem.[W2] That is motivation for the accounting contract, not empirical evidence that this ETF overlay will work. The option literature also distinguishes expected variance from the variance premium; a high VIX is not, by itself, a negative expected-return signal.[W4] Hence no predefined “high volatility means sell” sign restriction is justified here.

## Exact action and label contract

### State and candidate

At every eligible European decision close `t`, **including monthly dates**, snapshot actual cash, holdings/units, NAV, scheduled targets, pending orders, account restrictions and native execution state. The learned policy is fully daily after readiness: HOLD can preserve incumbent units at a monthly date, and STAY_CASH can keep cash beyond that date. Initialization and pre-readiness fallback still use the frozen baseline. This is the root investigator's final pre-results revision, replacing the earlier forced-monthly design. Snapshot price data and every feature dependency as of that timestamp. Create one fresh target with the **unchanged** `DEDUP_DUAL_TREND_OPP` rule on available data. Do not let the learned model rerank all 2,096 funds or choose among a new Top10 menu.

If native orders are pending or queued, do not make another discretionary decision. Let the existing order state resolve under its frozen rules. The state is never inferred from the intended target or last selected ticker.

The legal action menu is:

- `HOLD`: submit no new trade at t, including skipping a scheduled monthly buy/rebalance at the same timestamp; keep actual units/cash. For its counterfactual label only, continue the frozen baseline monthly schedule at strictly later events.
- `CASH`: sell the actual invested inventory under the native order contract. In counterfactual labels, retain proceeds until subsequent frozen baseline continuation events; in the actual learned replay, cash can remain until the learned entry gate passes. This action is absent in an all-cash state.
- `FRESH`: submit the frozen fresh target using actual available cash and actual net orders. In an invested state this is a switch; in an all-cash state it is an entry. Identical/no-op targets are deduplicated.

All branches start from the same snapshot. HOLD skips any same-t monthly instruction (`issue_initial=False`); CASH/FRESH apply their initial intervention. After t, all label branches use the **same frozen baseline continuation at events j > t**, without further learned interventions, through common terminal session `T = t + 21 exchange sessions`. This is a one-step policy-improvement target. Labeling a branch with future actions selected by a model fitted on later outcomes is prohibited.

Let `W_a(T)` be native account NAV after all fills, fees and scheduled continuation effects. For each legal intervention:

`y_net(s,a) = log(W_a(T) / W_HOLD(T))`.

The three fitted heads are `CASH_MINUS_HOLD` and `FRESH_MINUS_HOLD` in invested states, and `ENTRY_MINUS_STAY_CASH` in cash states. HOLD has exact advantage zero. This is a payoff comparison, not a label for whether the ETF's raw return was positive.

Do not add a fictional liquidation at T unless the common native account contract already does so. The target is continuation NAV, not a fabricated round trip. The omission of effects after T is an explicit horizon limitation.

### Execution and costs

Use EUR1 plus 15bp per executed order and the actual native number of net orders. A switch is not one order by definition; overlapping existing holdings can also reduce the required orders. The signal is known at t; the fill is at the next accepted execution event. Do not backfill a missed trade at the signal close.

Prefer NEXT_CLOSE as the primary execution proxy when the alternative Open availability is retrospectively gated by final full-day volume. Keep the existing next-Open contract as a sensitivity and disclose that full-day volume does not establish opening-auction executability. Next-Close still remains a daily-bar execution proxy, not certified auction access.

Fit the native **net** target directly. The action hurdle is zero net advantage, followed by the conservative uncertainty buffer below. All executed fees are already in the target; **do not subtract the commission again**. The root investigator explicitly excluded a separate estimated cost-offset layer from this first implementation. Record actual NAV and order costs to detect whether a changing EUR1 fee burden impairs transfer across account sizes.

### Training state coverage and selection bias

Construct a trigger-independent anchor bank on every eligible date: (1) the frozen baseline account snapshot and (2) an all-cash state at the same NAV. The all-cash record is a hypothetical admissible state, not a claim that cash was reached without paying a previous sale fee. Comparisons stay within each state, never across their starting histories. Both branches have identical starting wealth within each comparison.

Make labels for all legal actions at these states, including dates when no historical stop fired. Do not train an exit model only on stop-triggered dates, and do not train reentry only after the newly learned policy happened to exit. Those samples would answer a policy-selected question and can omit the states most important to a new policy.

Actual learned-policy states can be logged for later diagnostics. Do not silently add them to the initial training bank after inspecting their results. Any later policy-improvement round must be a separately frozen experiment.

With price-taking assumptions and the same deterministic simulator, all legal action outcomes can be computed at each state. This is not a conventional bandit dataset with only one observed treatment outcome. Inverse-propensity or doubly robust policy-learning machinery is unnecessary for these fully simulated actions; the serious limitations are execution realism, missing prices and support of account states. Athey and Wager's observational policy-learning setting clarifies the distinction.[W5]

### Censoring and maturity

Every row stores signal timestamp, first accepted fill(s), terminal session, last required observation timestamp, state ID, action ID, support flags and raw dependency IDs. A row is mature only when **every required outcome was observable strictly before the fit cutoff**. Use actual dependency maturity, not `signal_date + 21` as an unconditional shortcut.

If a terminal price or account valuation cannot be supported, censor the whole matched comparison group and count it explicitly. Do not drop the losing action while retaining the winning counterfactual, fill an unobserved return with zero, or call the resulting complete-case estimate unbiased. Native nonfills that are genuinely known by T remain an economic outcome and must be reported. Right-edge outcomes are excluded from training and scored separately as pending. Suspended/delisted tails need a separate adverse valuation bound; censoring can itself hide downside.

## Features and model

Use trailing basket returns constructed from the **currently known positions and weights**, including cash as zero return. These are descriptive histories of today's exposures, not a claim that this exact portfolio was historically funded. Define `NM_L = log_return_L / (daily_vol63 * sqrt(L))`. Use training-only scaling and explicit small volatility floors.

| Head | Price/state features |
|---|---|
| CASH−HOLD | Held NM21; held NM63; held log(vol21/vol63); deduplicated-universe positive-m63 breadth; sessions to next monthly baseline event strictly after t divided by21; actual invested gross fraction. |
| FRESH−HOLD | Fresh-minus-held NM21; fresh-minus-held NM63; log(vol63fresh/vol63held); fresh/held correlation63; sessions to next monthly baseline event strictly after t divided by21; actual invested gross fraction. |
| ENTRY−STAY_CASH | Fresh NM21; fresh NM63; fresh log(vol21/vol63); deduplicated-universe positive-m63 breadth; sessions to next monthly baseline event strictly after t divided by21. |

Gross exposure is necessary because normalized return/volatility features alone can erase the economic scale of a partial account. Compute breadth with the existing deduplication/groups, so many wrappers do not count as many independent market votes.

PRICE_PLUS_LEGACY_VIX adds log VIX level and its21-source-session log change. PRICE_PLUS_LEGACY_AND_TERM then adds exactly two new features: `log(VIX9D/VIX)` and `log(VIX/VIX3M)`. Require a source date strictly earlier than the European decision date, and no more than seven calendar days old. Use one common source date for the three values. Do not use same-date final US Close at European Close. Cboe describes these indices as different maturity points on SPX implied volatility.[W6,W7]

At each fit, residualize the two new TERM columns on the price/state columns, the two LEGACY VIX columns and an intercept using training-only weighted least squares; standardize the residuals using training statistics. This makes the incremental linear information question clear. It does not prove economic independence, causal exogeneity or out-of-sample orthogonality.

Fit one Ridge per head. Minimize **mean date-weighted squared loss plus `1.0 * sum(beta^2)`**, with an unpenalized intercept. Standardize inputs using only the mature training sample. Each date has total weight one per head; split that weight across its valid state records. ETF rows, synthetic cash states and overlapping events do not increase the number of independent market episodes. Do not clip future loss labels to make training look stable.

Start only after at least504 distinct mature dates and at least24 nonoverlapping21-session outcome blocks. Refit monthly on an expanding window. Earlier decisions follow the frozen baseline exactly. Fit all three models on the same complete-label/source-date support. If an external block is unavailable at prediction time, use the corresponding valid nested lower-information model and record the fallback; do not manufacture a current options observation. This warmup means the learner cannot improve the2020 crash. Report both the full window with identical baseline warmup and a prominently displayed, same-date post-warmup comparison. Do not synthetically backdate fitted models.

For a conservative decision buffer, resample **whole 63-session date blocks**, keeping all state/action rows on each selected date together and using paired resamples across all three models. Use100 fixed-seed resamples. For an action to override HOLD/STAY_CASH, its predicted net advantage must be positive and the 10th percentile of its resampled conditional-mean predictions must also exceed zero. Choose the largest such lower bound; ties retain HOLD, then use a stable action ID if needed. This is a conservative heuristic, **not a calibrated 90% probability or valid discovery confidence interval**. Never use the distribution of individual future returns as if it were uncertainty in the conditional mean.

## Prediction gate, small portfolio matrix and stopping rule

Before interpreting account CAGR, write a prequential ledger of each forecast, training cutoff, model hash, support, forecast difference and subsequently matured outcome. Compare every head with (a) a training-only historical mean, (b) PRICE_ONLY and (c) the nested PRICE_PLUS_LEGACY_VIX control. Report date-weighted MSE, mean forecast bias, a few fixed forecast bins, actual selected-action net advantage, action counts, independent episodes and year/regime contributions. An improvement in raw positive-return hit rate does not satisfy the economic question.

The gate is not “the full sample CAGR exceeded30%.” Require improvement beyond the historical-mean and lower-information nested forecasts, plus positive incremental common-state decision value after costs. Inspect exit, switch and entry separately so positive equity risk exposure cannot disguise unhelpful exits. A family with fewer than12 separated, completed intervention episodes has insufficient evidence for action-specific reliability. Empty action sets are a legitimate failure to find a useful decision rule, not a reason to lower the confidence buffer.

Run the following18 complete account paths as diagnostics even if the prediction evidence is weak: the one-step/actual-policy mismatch itself needs measurement. If the forecasts or account evidence do not support incremental value, stop further search: no expanded threshold grid, no feature mining, and no promoted strategy. Freeze only these account policies:

| Policy | Role |
|---|---|
| Original frozen selector | Existing invested control. |
| STATIC_75 | Existing exposure-reduction control. |
| ADV_MEAN | Same machinery, mature training-only mean forecasts and identical uncertainty buffer. |
| ADV_PRICE | Same machinery and price/state inputs. |
| ADV_LEGACY_VIX | Identical learner plus the previously studied VIX level/change information. |
| ADV_LEGACY_AND_TERM | Primary proposed policy with the two incremental term-structure inputs. |

Run only three declared execution/cost scenarios: primary NEXT_CLOSE at normal costs; NEXT_CLOSE at double proportional costs; existing NEXT_OPEN at normal costs. This is18 paths, not a horizon/penalty/threshold search. The historical-mean arm is both a mandatory forecast benchmark and an executable policy comparator. Use identical supported evaluation dates and report the warmup separately. Do not select a winning scenario or head after seeing the results.

Report native CAGR, MaxDD, annual returns, exposure, turnover/order counts, out-of-market days, delayed/unfilled orders, action-specific outcomes and rebound capture. A lower drawdown caused mainly by lower exposure must be compared with STATIC_75 and described accordingly. Common-state21-session advantages overlap: their average cannot be annualized and called an account CAGR.

## Material failure modes

1. **Independent sample size:** roughly six-and-a-half years of21-session targets provide only on the order of80 nonoverlapping horizon blocks before training warmup, regardless of millions of ETF rows. Correlation and regime dependence can reduce effective information further.
2. **Research reuse:** the entire historical period and many architecture choices have been observed. Chronological training prevents some look-ahead; it does not create a pristine holdout or erase search over prior studies.[W8]
3. **Continuation mismatch:** repeated daily interventions, monthly HOLD vetoes and cash held across month ends generate states and future decisions different from the frozen baseline continuation used in the labels. Anchor-bank incumbents usually turn over monthly; learned incumbents can become much older. Report holding ages and feature-support/extrapolation diagnostics explicitly. The complete account replay is essential; a positive one-step diagnostic is not sufficient.
4. **Risk-premium confusion:** a high risk forecast, or a high crash probability, can coexist with positive expected returns. Entry success versus cash can be ordinary risk exposure rather than selective alpha.[W1,W4]
5. **Execution and missing tails:** Open availability gated by final daily volume, survivor-biased current catalog membership, adjusted-price assumptions and censored losers remain data limitations. A model cannot cure them.
6. **Geographic/exposure mismatch:** US SPX implied volatility may not predict a portfolio dominated by gold, bonds, commodities, Europe or emerging markets. The small design intentionally does not add enough interactions to fit every exposure separately.
7. **Bootstrap instability:** few independent blocks make parameter uncertainty noisy. Resampling is a cautious action buffer and descriptive sensitivity, not an inferential repair for the reused sample.

## Primary sources

- **[W1]** Campbell and Thompson (2008), *Predicting Excess Stock Returns Out of Sample: Can Anything Beat the Historical Average?* [Harvard author repository](https://dash.harvard.edu/entities/publication/73120378-7dd1-6bd4-e053-0100007fdf3b). Supports using a historical-average forecast as a serious benchmark; its US aggregate-return findings do not validate this ETF model.
- **[W2]** Gârleanu and Pedersen (2013), *Dynamic Trading with Predictable Returns and Transaction Costs*. [NBER working paper and published-version record](https://www.nber.org/papers/w15205). Methodological motivation for state- and cost-aware decisions.
- **[W3]** Longstaff and Schwartz (2001), *Valuing American Options by Simulation: A Simple Least-Squares Approach*. [University of California repository](https://escholarship.org/uc/item/43n1k4jb). Continuation-value estimation precedent; option valuation is not proof of stock-return predictability.
- **[W4]** Bekaert and Hoerova (2014), *The VIX, the Variance Premium and Stock Market Volatility*. [NBER working paper and published-version record](https://www.nber.org/papers/w18995). Distinguishes conditional variance from the variance premium.
- **[W5]** Athey and Wager (2021), *Policy Learning with Observational Data*. [Authors' manuscript](https://arxiv.org/abs/1702.02896). Used to delimit, not claim, the need for observational treatment-effect machinery.
- **[W6]** Cboe, [VIX historical data](https://www.cboe.com/tradable_products/vix/vix_historical_data). Official historical-series source.
- **[W7]** Cboe, [Term Structure Data and Charts](https://www.cboe.com/tradable_products/vix/term_structure), and [VIX methodology](https://cdn.cboe.com/resources/vix/VIX_Methodology.pdf). Official definitions and US dissemination timing.
- **[W8]** Bailey, Borwein, López de Prado and Zhu (2017), *The Probability of Backtest Overfitting*. [University of California repository](https://escholarship.org/uc/item/4w1110bb). Motivation for treating reused-sample performance as descriptive, not an untouched validation.

All source consultation occurred on16 November2026. Sources motivate specific design choices; no paper's published performance has been transferred to the ETF account.
