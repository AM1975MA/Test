# V5 — layer fisico-statistico per escludere i peggiori, **prima** di LM/Ridge

**27 ottobre 2026 — test davvero eseguito localmente, 101 mesi, ricostruzione EUR NEXT Open, research ONLY.** Il modello operativo e i 500 panieri originali non sono stati modificati/testati. Tutti i CSV, i sorgenti Python e gli audit sono consegnati nell'archivio della conversazione \`V3_MATH_STAT_FIRST_LAYER_BEFORE_LM_20261027.zip\`.

## Ipotesi sperimentale

Layer 1 matematico **senza alcun ML**. Solo grandezze disponibili alla chiusura del mese: momentum percentuali su 21, 63, 126 e 252 sedute, drawdown precedente, volatilità storica 21 e 126 sedute, percentuale di sedute positive. Stima euristica della probabilità di perdita totale >5% a 21 sedute:

\`\`\`
mu21 = 0.50 * trailing_return_21 + 0.30 * trailing_return_63/3 + 0.20 * trailing_return_126/6
sigma21 = rolling_daily_sigma_21 * sqrt(21)
approx_p_loss5 = Phi((-0.05 - mu21)/sigma21)
\`\`\`

È una **approssimazione gaussiana di drift/diffusione**, non una legge di moto finanziaria e non una probabilità calibrata. Esclude il quartile più a rischio di ogni mese, **senza guardare Ridge o i futuri rendimenti**. Layer 2: **Ridge16 già congelato**, senza riaddestrarlo, che ordina soltanto i sopravvissuti. Policy di rimpiazzo: se un precedente Top3 è filtrato, si prende il prossimo migliore già idoneo, mai future winners.

Controlli *separati e dichiarati*: punteggio di deterioramento composto (quartile peggiore e peggiori 40%); momentum 12–1 peggiore quartile; volatility alta quartile; flag severi con soglie assolute; **random exclusion 25%** come placebo. Non selezionare retrospettivamente il migliore in base al CAGR.

## Risultati economici, Top3, 101 segnali 2018–2026 EUR e commissioni 10bps per lato

| Policy | EU148 CAGR | EU148 maxDD | EU158 CAGR | EU158 maxDD |
|---|---:|---:|---:|---:|
| Ridge16 senza filtro | **+6.13%** | -29.17% | **+10.15%** | -30.23% |
| Layer fisico-statistico coda-5% + Ridge | **+10.25%** | -29.34% | **+10.81%** | -31.21% |
| Exclude worst 25% momentum + Ridge | +10.31% | -29.17% | +12.34% | -30.23% |
| Exclude worst 25% high vol + Ridge | +8.75% | -29.05% | +10.52% | -29.15% |
| Punteggio deterioramento 25% + Ridge | +8.95% | -29.11% | +8.84% | -34.10% |
| Punteggio deterioramento 40% + Ridge | +9.34% | -29.11% | +11.13% | -35.85% |
| Severe absolute flags + Ridge | +6.03% | -29.11% | +9.50% | -30.97% |
| ONE randomized exclusion 25% + Ridge | +4.92% | -29.73% | +11.55% | -30.23% |

**The 25% random CAGR is only a single draw and not a meaningful statistical economic null.** Additional **2,000 independent random 25% exclusion seeds** were evaluated on *predictive* outcomes, not through full economic simulator.

## Better signal: reducing worst losses (same 101 months, held-out annual predictions)

| Top3 fraction experiencing future ETF -5% or worse over next 21 sessions | EU148 | EU158 |
|---|---:|---:|
| Ridge16 unfiltered | **14.52%** | **17.49%** |
| Randomly drop same 25%: mean of 2000 null replications | **13.47%** | **16.54%** |
| **Pure math-tail veto THEN Ridge16** | **7.26%** | **10.56%** |

None of the 2,000 independent random vetoes achieved such a low Top3 crash rate. Paired 6-month circular 12k bootstrap reduction compared with unfiltered: EU148 **-7.26 percentage points [95% CI -11.22;-3.63]**; EU158 **-6.93 percentage points [-10.23;-3.63]**.

In terms of returns, Top3 true EXSA excess mean improved by **+0.343pp** EU148 and **+0.094pp** EU158 per month, but **both paired CIs include zero**. This is more convincing as a **false-positive/tail-risk gate** than as an outright return forecast.

Relative to 25% random vetoes in 2000 tests, EU148 physics Top3 future excess **+0.4325%** vs random mean **+0.1518%** (exceeds 99.05% of null distributions); EU158 **+0.4402%** vs random mean **+0.3380%** (exceeds ~79.9%). Do not conflate these descriptive comparisons with prospective alpha.

Annualized paired **full-month log-return improvement** of physics vs no filter: EU148 +3.84pp log-rate, bootstrap 95% [-0.95;+8.49]; EU158 +0.61pp, [-5.86;+6.81]. Not a demonstrated economic gain. Even the volatility hedge may lower upside, reducing signal vs raw CAGR.

## Time-window stability and strict caveats

The old EU148 physic-tail Top3 approximately +8.1% CAGR 2018–21 and +12.1% 2022–26, against unfiltered ~+4.7% and +7.3%. EU158 physics +7.4% and +13.9%, versus Ridge base +6.6% and +13.1%. The absolute percentages and subperiod figures are descriptive.

This is NOT a test of original 500 baskets, and the 2018–26 period was extensively explored before this policy. EU158 uses **ten 2026-listed surviving global UCITS chosen retrospectively** and cannot verify prospective absence of survivorship bias. No slippage spreads or order-book depth. Gaussian statistical tails may underestimate jumps; historical signal can change when macro regime shifts. Nominal CIs are not corrected for repeated research comparisons.

## Decision

- Keep the **mathematical safety veto**, fixed parameters, as a **candidate** for the new first layer; the strongest experimentally backed quality is fewer severe false-positive selected ETFs.
- Do NOT promote any filter on CAGR or claim the 30% performance objective. The current test reached only 10–12% annual historical CAGR.
- Next **necessary scientific check**: frozen 500 original historical baskets using vintage/as-of composition, compare before/after gate matched selected count, adverse-event prediction out of distribution, paired confidence and properly risk-/factor-matched buy-and-hold; then genuinely new live paper signals. Recalibrate actual tail probabilities on train-only if probability forecasts are needed.
- Source ZIP delivered contains exact original \`nav_sim\` copied by AST from the previous EU research implementation, original input dates/candidates, portfolio replay, all pre-signal risk scores, 2000 random matched veto seeds, monthly precision/recall, portfolio NAV, real trades, and bootstrap.

**Reproducibility source files:** \`v3_analytic_first_layer_test_20261027.py\`, \`v3_math_first_layer_random_null_20261027.py\`, \`v3_math_first_layer_final_checks_20261027.py\`. Inputs are archived in conversation \`V3_PREDICTIVE_ENGINE_V4_20261027_AUDIT.zip\`, \`EU_GLOBAL_UCITS_BREAKTHROUGH_20261026.zip\`, \`eu148_final_corrected_ohlcv.zip\` and \`EU_GLOBAL_UCITS_20261026_SOURCE_RESULT.zip\`.
