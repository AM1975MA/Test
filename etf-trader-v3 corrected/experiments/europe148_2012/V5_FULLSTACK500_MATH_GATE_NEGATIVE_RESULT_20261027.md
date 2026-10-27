# V5 full original V2 complete 500-basket test of first mathematical physics gate

**27 Oct 2026. SUCCESS: [GitHub Actions run 40473372871](https://github.com/AM1975MA/Test/actions/runs/40473372871). Original source of truth reproduced byte-sha membership and daily NAV; unmodified production.** Main result: hard 25% physical/statistical veto is **REJECTED**, because it destroys alpha when run inside full ORIGINAL V2 Hybrid24. Do not promote.

## Data/provenance correctness

- Exact original canonical **500 baskets of 24 ETF**, six original category quotas 4, basket SHA256 \`36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e\`, regenerated identically.
- Original 149 US-listed ETF daily source snapshot GitHub Actions run **39482809691**; frozen source-generated 114-month original V2 BASE Titanium/ExtraTrees/XGBoost Hybrid Tail scores, exact original equity and turnover PATH, original cluster and annual maturity audits GitHub Actions run **39836842157**.
- **Initial baseline recreated exactly**: across all 500×2366 daily NAV data points, max absolute difference vs frozen original PATH **1.2434497875801753×10^-13**; reference CAGR per basket and worst tail EXACTLY match archived \`RESULT.json\` to 1e−9. Original daily Turnover, original V6 alt indexes, Top2, weights, DD systemic gross all verified against untouched original.
- Original fully active: base .475 and (smoothed ET/XGB) Hybrid24 tail .525, original Top2 margin-dependent continuous allocations, DDfirst, V6 recovery/alternative, HighCAGR24, original intraday execution model with 10bp one-way cost, 500 baskets, NO LM replacement.
- Veto acts only on signals since Jan 2018, rest original 2017 source state unchanged. 101 fully observable future21 signals Jan2018 through May2026. Same calendar window for main economic comparison from Feb2018 to Jul1 2026.
- Mathematical gate scores **causal** (as-of monthly signal closes): \`mu=.50 R21+.30 R63/3+.20 R126/6\`, \`sigma21=std(last21 daily returns)*sqrt(21)\`; \`P(loss<-5%)=Phi((-.05-mu)/sigma21)\`. Per 24 fixed original members, exclude six with highest hazard; original Hybrid24 ranks survivors and selects Top2.
- Comparators: no veto, veto six worst momentum63, and per-month basket random veto six (one seeded control, *not* 2,000 random fullstack economic bootstraps). All variants share original Hybrid24 base/tail/risk/cost.
- Stage-specific previous diagnostic (frozen Ridge125 Top2, NOT full V2) is *different experiment*, [see separate report](V5_CANONICAL500_MATH_BEFORE_US_RIDGE_RESULTS_20261027.md). Never conflate their returns.

## Empirical full V2 500 baskets, 2018-Feb→2026-Jul 1 terminal open mark

| Full ORIGINAL V2 risk stack variant | Mean individual basket CAGR | Mean basket MaxDD | Equal-capital aggregate CAGR | Aggregate MaxDD |
|---|---:|---:|---:|---:|
| **V2 original frozen model** | **+22.0077%** | **−35.1003%** | **+24.7739%** | **−19.8921%** |
| **V2 + math diffusive worst6 veto** | **+15.9449%** | −35.6360% | +17.7244% | −22.5939% |
| V2 + negative-momentum worst6 veto | +15.6615% | −36.6578% | +18.5516% | −23.1310% |
| V2 + one seeded random worst6 veto | +19.3818% | −36.9112% | +22.0424% | −19.3675% |

This veto **reduces** mean basket CAGR by **−6.0628pp**, aggregate CAGR **−7.0495pp** and does NOT improve mean basket or aggregate drawdown. No sensible grounds for production use.

US original most problematic explanatory diagnostic across exact 101 paired signal months:

| Same frozen Hybrid24 Top2 selected in each basket | No veto | Math veto |
|---|---:|---:|
| Observed 21-day future absolute ETF return | +1.6207% | +1.3689% |
| ETF with absolute future 21-day loss ≥5% | **21.3931%** | **18.4267%** |
| Fraction original Hybrid24 basket Top1 removed | 0 | **49.94%** |
| Fraction original Hybrid24 basket Top2 removed | 0 | **45.03%** |

- Paired delta math veto in severe loss rate: **−2.9663pp**, 95% nominal CI **[−4.9832,−0.9297]pp**, circular 6-month 4k bootstrap on 101 months. The gate genuinely detects elevated risk on this explored sample, but loses most of its benefit by excluding high expected return winners.
- Paired delta mean future21 returns **−0.2518pp per month**, CI95 [−0.6287,+0.1346]pp; zero in interval. That doesn't erase measured negative economic performance.
- Independent extra economic check on true equal-capital NAV 101 full months Feb2018–Jun2026: paired log-return difference annualized **−5.7965pp**, circular six-month 16,000 bootstrap draws nominal 95% **[−9.7121,−1.7841]pp**. Not corrected for historical specification search. This measures paired annualized *log-return rate*, not directly difference of geometric CAGR.
- Side-note the source model contains gaps filled according to original legacy V2 processing; corporate-action vintage, historical delisted membership and trade slippage are NOT independently certified. These V2 original assumptions are held the same in both arms for internal parity.

## Why the math veto fails and what to do next

The 25% unconditional diffusion risk selector removes HALF the top predicted winners of Hybrid24. Because the original model often values risk premium / momentum / asymmetric upside, the physical Gaussian loss score is not a replacement for the conditional expected *net return*. Filtering high volatility is not the same as identifying **uncompensated risk**. This is visible in the increase of Top2 score margin paired with lower realized future return. A simple momentum worst-six veto is equally destructive. The negative result is robustly larger than mechanical random exclusion in the single-seed control.

**Engineering recommendation**: retain unchanged original V2 500 stack. Do not hard-reject 25% by unconditional risk score. Next scientific task: train/validate a supervised **conditional FALSE-POSITIVE critic**: estimate \`P(21d severe loss | BASE, ET, XGB, full Hybrid24 score, volatility regime, price dynamics)\` on fully matured source-only walkforward vintages; apply a penalty only when the critic identifies *uncompensated tail risk*, preserving original strong winners. Compare prespecified soft-rank penalty or cash-risk sleeve, **never silently throw away Top1**. Must benchmark zero-gate, single risk critic, existing V6, random-penalty, and no expensive future labels for decisions. 2018–26 is already researched; only prospective later samples can confirm eventual gains.

**Output and replay:** full 500×2366 NAV NPZ; 500×101-month policy selection change audit (153,000 entries); monthly Top2 realized hazard and true returns; paired block bootstrap; exact manifest; [reproducible Python source](v5_fullstack500_pure_math_veto_20261027.py), [Actions workflow](https://github.com/AM1975MA/Test/blob/research/v3-europe148-historical-20261024/.github/workflows/v3-fullstack500-pure-math-before-top2.yml). All files available as \`V3_V2_COMPLETO_500_PANIERI_VETO_MATEMATICO_20261027.zip\` in conversation.
