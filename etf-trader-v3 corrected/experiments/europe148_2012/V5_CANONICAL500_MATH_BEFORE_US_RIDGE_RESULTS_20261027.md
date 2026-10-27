# V5 — primo layer fisico/statistico prima del LM Ridge, 500 panieri V2 autentici (27-10-2026)

**Run SUCCESS, tutti gli esperimenti conclusi**: [GitHub Actions 40463341965](https://github.com/AM1975MA/Test/actions/runs/40463341965). Artifact \`v3-original-500-baskets-math-first-layer-before-us-lm\` ID 12715610306.

## Vincolo: questi sono davvero i 500 panieri, NON EU148 e NON 500 panieri simulati ex novo

Provenienza: [source originale di generazione basket](../../fullstack_legacy/src/etf_trader/source_only/baskets.py), 500 panieri x 24 ETF, 4 ETF per ognuna delle sei macro-categorie, 149 ticker USA originali, seed 20260721. SHA256 membership originale **36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e**, verificato byte per byte; membership anche ricostruita con algoritmo V2 e identità 12000 righe verificata. Un paniere NON può prendere ETF di altri panieri. Non viene creato un finto 500-basket europeo.

Input US OHLCV originali congelati, GitHub Actions snapshot run 39482809691, artifact \`v2-deep-leaf-frozen-raw\`. LM / Ridge congelato: 9 modelli annuali (2018…2026) già addestrati e verificati [run 40394516018](https://github.com/AM1975MA/Test/actions/runs/40394516018), 125 feature, previsioni percentuali signed forward21, senza nuovo fitting. Audits: ciascuna exit63 della formazione annuale precede Jan1 dell'anno test. **101 segnali** mensili, prime esecuzioni US Open 2018-02-01 e mark terminale 2026-07-01; 10 basis points per lato su notional, Top2 due metà capitale, niente costi fittizi, **zero fill mancanti**.

## Variabile isolata

Filtro matematica pura senza ML: trend 21,63,126 giorni e sigma giornaliera stimata su ultime 21 sedute; approssimazione gaussiana di probabilità di \`return21 < -5%\` su drift 21:

\`mu = .50*mom21+.30*mom63/3+.20*mom126/6\`, \`sigma21=stdev(ret_daily_21)*sqrt(21)\`, \`P(loss>5%)=Phi((-.05-mu)/sigma21)\`.

Per ogni mese e per ogni basket, esclude i **sei** peggiori rischi stimati su 24; il modello LM/Ridge già congelato sceglie Top2 dei 18 rimanenti. Ad ogni data vengono anche calcolati pari quantità esclusi secondo 63d momentum negativo e un random veto; medesimi 500 panieri e stessi LM, esecuzione e fee.

**La probabilità gaussiana non è calibrata**, è un proxy d'ordine dei rischi. Nessun rendimento futuro è utilizzato per il veto o le scelte.

## Veri risultati ottenuti, Top2 USD dal 2018 al 2026

| Scenario | **CAGR medio dei 500 panieri** | CAGR portafoglio aggregato equal-capital | MaxDD medio dei 500 | Drawdown aggregato |
|---|---:|---:|---:|---:|
| Frozen LM Ridge 125F, NO veto | +11.840% | **+13.341%** | -45.551% | -39.246% |
| **Fisico-statistico taglio worst6 + frozen LM** | **+12.531%** | +13.114% | **-36.742%** | **-34.817%** |
| Negative momentum veto six + LM | +11.245% | +12.295% | -37.635% | -35.134% |
| Random veto six, single deterministic seed + LM | +11.011% | +12.329% | -42.928% | -38.071% |

Dettagli quantitativi del rischio tra tutti i 500 panieri:
- **P10 dei CAGR**: +2.941% senza veto -> **+7.251%** con fisico/statistico.
- **P10 dei drawdown**: -59.957% -> **-41.466%**.
- **Worst drawdown individual basket**: -78.885% -> **-56.835%**.
- La modifica agisce sul Top2 nel **43,4% delle posizioni** (0.868 sostituzioni medie su due per basket-month).
- Nessun fill mancante in nessuno dei quattro scenari.

## Capacità predittiva: vero risultato principale

| Policy | Percentuale dei Top2 con futura perdita osservata almeno 5% in 21 sedute US | rendimento osservato medio a 21 sedute |
|---|---:|---:|
| Ridge no veto | **17.767%** | +1.4046% |
| Pure Math veto | **14.244%** | +1.3718% |
| Random veto six | 17.444% | +1.3359% |

Differenza pareggiata pure-math vs Ridge senza filtro su **101 mesi**, bootstrap 6-month circular blocks (6000 resamples, unità d'inferenza mesi, non 500 pseudo-soggetti indipendenti):
- **Crashes -3.524pp**, nominal IC95 **[-5.599,-1.508]pp**.
- **Rendimento vero a 21 giorni -0.0328pp**, nominal IC95 **[-0.5063,+0.4944]pp**.
- Aggregate equal-capital monthly NAV log-return spread annualizzato -0.1934pp, bootstrap 12k resamples 6m, nominal 95% **[-6.14,+6.48]pp**. **Nessun guadagno aggregato dimostrato.**

Sources: per-basket original integrity SHA, \`CANONICAL500_TOP2_PICKS.csv\` (500*101*2*4); \`CANONICAL500_LM_VETO_ECONOMICS.csv\`; \`CANONICAL500_PAIRED_TIME_BLOCK_BOOTSTRAP.csv\`; \`CANONICAL500_MONTHLY_PREDICTIVE_SKILL.csv\`; \`CANONICAL500_EQUAL_CAPITAL_DAILY_NAV.csv\`; \`ORIGINAL_TOP2_REPLACEMENT_AUDIT.csv\`; \`FROZEN_ANNUAL_LM_MATURITY_AUDIT.csv\`; \`SOURCE_VINTAGE_21D_LABEL_DIFFERENCE.csv\`; \`MANIFEST.json\`, all GitHub Actions artifacts and delivered chat zip.

## Important limitations: why not compare +12.53% directly with original V2 +22.01%

Original source-only **V2 complete 500** 2018+ [source report run 39834445061](../../reports/FULLSTACK/data_run_39834445061/RESULT.json) mean per-basket CAGR **+22.008%**, includes original Titanium base, Hybrid24 Tail, Top2 dynamic weighting, DD-first, V6 and HighCAGR24, original 2017–2026 calendar. This current test is intentionally **NOT full V2**: it is equal-weight 2 ETF/mese LM on original basket membership. There is **NO justification** to claim replacing productive V2 with physics+LM improves results, given this diagnostic greatly trails full V2 raw performance. Original V2 risk, leverage/exposure and 2017 start differ. The full original risk stack would need a same-period, same-exposure fullstack replay with math gate injected BEFORE selection to establish an incremental effect.

Native annual LM labels were trained for **21 EU-US joint sessions**, but realized crash diagnostics here correctly use 21 **actual US venue** sessions from the V2 raw. Source-vintage/horizon mismatches reach 3.4 percentage points median in some months (April 2020, November 2018), need align feed/calendar for any prospective adoption and NEVER classify original frozen labels as identical to the native execution's targets.

Historical 2018–26 heavily reused for research and filter chosen with knowledge of EU outcomes. Nominal bootstrap intervals are **not a virgin prospective holdout**; fee 10bps does not include impact/slippage. No European canonical 500 baskets exist in original V2; must not invent identical EU comparison.

## Engineering decision

Promising **risk-safety veto**: cuts crash false positives and reduces MDD meaningfully on EXACT immutable V2 500 baskets. It is **not** a model of outsized returns, nor a success against 30% CAGR. Retain as a candidate to insert conditionally in original fullstack with signal as-of filtering and calibrated volatility; preserve original V2 as reference, no production changes until fullstack and unseen forward data validate advantage.

[Reproducible experiment source](v5_canonical500_math_veto_before_frozen_us_lm_20261027.py) and [Actions workflow](https://github.com/AM1975MA/Test/blob/research/v3-europe148-historical-20261024/.github/workflows/v3-canonical500-math-before-frozen-us-lm.yml).
