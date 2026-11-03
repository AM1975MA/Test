# OLC32 — dati di esecuzione corretti e previsione diretta del vantaggio economico Open→Open

**Congelato prima degli esiti del nuovo learner, 3 novembre 2026.** Parent OLC31: `b0eb7b6a4e257b64ec3a13fc068f5f4c3b91ccbe`. Nessun intervento su main, sui predittori originali, sul sistema operativo o trading. EUR165 ed USA149 insieme. Storico già molto esplorato: i risultati sono retrospettivi, NON un nuovo holdout.

## Sorgenti e verifica
- OLC08_01 panel verificato SHA256 945faa5816aa627c398244d1b2a599fc2ba31f35fa6d789379264b0912d0be02, inclusi EU_HYBRID/USA_HYBRID originali.
- OLC08_03 raw score SHA256 0dbcb8ee93cd0acaefd7505a202fbf30c9fda8df1804d90a0dd1578abd704f4b.
- OLC19 checkpoint SHA256 3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540; Contains state O/H/L/C, EU observed quote masks, inherited signal/entry/exit calendar.
- OLC20 final model/replay SHA256 a81be0fad1da73b48ba0af0080985657ee33e18a10f278db2318f9da06738a9c; frozen AUTH FUSION scores.
- Official Deutsche Börse trading calendar 2020 https://www.deutsche-boerse.com/resource/blob/1665534/112856375187d3e93671aa3d731d09d3/data/xetra-trading-calendar-2020.pdf : no Xetra/Börse Frankfurt trading on **2020-06-01**.

## Data repair rules frozen
**Never fabricate prices. Never overwrite archived raw arrays.**
1. EU monthly calendar anomaly: both the 2020-04-30 signal EXIT and 2020-05-29 signal ENTRY shift from 2020-06-01 to common 2020-06-02, first observed common German market session; this fixes the two adjacent MONTHLY LABEL BOUNDARIES. Historical portfolio NAV/backtest remains frozen, not declared retrospectively corrected.
2. At all endpoints, EU O must be finite positive and **observed=true**; additionally source-date 2020-06-01 forbidden as a German ETF executable boundary. For the rare non-German listings, same common corrected schedule is imposed as a **uniform basket-level execution convention**, which may delay available foreign quotes by one day. Report this limitation.
3. EU LEEU.DE on 2024-05-02 is not observed (archived stale 2024-04-30 Open); DO NOT backfill as a 2024-05-02 real execution. Mark its May-boundary label invalid; preserve previous/next verified price only as diagnostic; do not silently move this ticker alone to a different entry date.
4. USA has no original observed quote mask. Accept only positive finite PREPARED Open, label `not_original_quote_certified`; never call these verified quotes.
5. Terminal 2026-07-01 entry==exit is not a future label; exclude. Retain missing features/labels as NaN. Keep both ORIGINAL and CORRECTED calendars + changed-row audit, full month-level counts, SHA256 files.

## Prediction target and scope
At monthly signal t, for eligible ETF i, with corrected entry Open O0 and corrected next Open O1:
`r_i = 10_000*log(O1_i/O0_i)` in **basis points**.
Define *economic advantage* `a_i = r_i - median_j(r_j)` per market/signal month among VALID observed/finite pair labels. The median uses future returns **ONLY to construct mature training labels**, never to decide forecast eligibility or as input to prediction. For any two ETFs i,j, the fitted advantage difference `a_hat_i-a_hat_j` is the predicted economically sized Open→Open spread, not merely a percentile.
Label available at corrected exit_date; strict `exit_date < Jan 1 of fit year`; no random split, no 21-day proxy. Do not train on months with fewer than 70% source-observed/finite valid label rows; keep all in quality audit.

## Frozen input feature set
Use the EU/USA OLC08 causal HYBRID panel (contemporaneous signal features, no future label) plus canonical OLC20 AUTH FUSION:
`FUSION,ret_21,ret_63,ret_126,ret_252,mom_126_21,acc_5_21,acc_21_63,eff_21,eff_63,dd_21,dd_63,sma_ratio_50,sma_ratio_200,vol_21,vol_63,skew_63`.
Exactly 17 features. Validity requires finite complete-case features at BOTH candidate and reference evaluation; missing scores fall back to AUTH and are never dropped from live-style selection. Model fitting and evaluation use matched feature support for all candidate models.

## Annual walk-forward models and fixed hyperparameters
Train one **pooled EU+USA model** per year 2021..2026, from all prior fully mature months only. Market mass 50/50, months within market equal weight, ETF equal within month. Fit only if at least 12 valid distinct mature signal months in EACH market. No EU/USA-specific hyperparameters, ticker IDs or future-data predictors.

- B1: StandardScaler + Ridge(alpha=10) on FUSION alone, under matched complete-feature support.
- E1: StandardScaler + Ridge(alpha=100) on all 17 features, fitted directly on economic `a_i`.
- E2: HistGradientBoostingRegressor(loss='squared_error',max_iter=100,learning_rate=0.04,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=50,early_stopping=False,random_state=32001), same 17 features, direct `a_i`. No tuning, early stopping or retrospective winner choice. Sample weighting identical.
- B0: no-information prediction 0 bp economic advantage (secondary).

For each OOF signal, generate direct advantage forecasts, and pairwise predicted spreads for all 10 AUTH Top5 unordered pairs. No future availability condition in forecast score output. All models on same OOF dates/tickers.

## Test gates and endpoint metrics
Primary main 2021–2024 **both markets**:
(A) Within market-month mean MSE and MAE of economic-advantage prediction (bp² / bp), baseline B1 vs E1/E2 on matched rows.
(B) Within AUTH Top5: pairwise spread MAE and directional accuracy for economically material **|true gap| >=100bp**, spread calibration deciles/quantiles, denominator explicit; Top2 candidate errors.
(C) Description of missed opportunities and dynamic best-retrospective-ticker capture; not an ex-ante optimization criterion.
(D) 6-month block bootstrap paired by calendar month, joint EU/USA ranges, not posterior probabilities or search-adjusted statistical proof.
(E) 2019–2020 corrected labels only eligible as known training once matured; 2025 and 2026 partial separately, no choice on those windows.

Only if a fixed candidate beats B1 in **both** markets in month-mean MSE AND improves Top5 material-spread accuracy or MAE in both may a separate preregistered full OLC19/V6 risk/fee replay be considered. Otherwise stop at predictive gate. **Never train on true future labels missing from decisions**; never automatically deploy. Do not reoptimize model/hyperparameters on failed results.

## Collaudo and reversibility
- Source SHA256, duplicate (market,signal_date,ticker), exact parent AUTH forecast/controls, feature as-of and mask audit.
- Test official 2020-06-01 closure and both revised event boundaries, continuity exit==next entry, positive observed German quotes 2020-06-02; LEEU 2024-05-02 remains unobserved; last terminal label absent.
- Two independent derivations of corrected O2O labels/median from Open matrices; compare checksum and reconstruction. Outcome perturbation after cutoff leaves older models/predictions unchanged; no label-dependent candidate universe.
- StandardScaler training only; exact EU/USA and month balances; deterministic rerun and saved model reload; source errors fail closed.
- Persist both successful and unsuccessful results, 2020 correction audit, annual fitted models, OOF predictions and manifest. No claim of repaired real historical trading accounts without fresh independent replay and data audit.

## Limits
Original USA observed mask missing; survivorship, total-return/dividend/FX, original same-Open order conditions, intraday availability and real bid-ask/lot size not certified. The corrected 2020 date is an exchange-level calendar fix for new training labels, not a claim of recovered missing historical prices.
