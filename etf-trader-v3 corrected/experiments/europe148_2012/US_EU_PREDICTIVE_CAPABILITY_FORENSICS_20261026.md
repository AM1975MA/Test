# Audit forense predittività V3 EU148 vs US149 — 26 ottobre 2026

**Stato:** eseguito; 18 originali modelli annuali V3 125-feature 127 foglie, 101 mesi di test 2018-01/2026-05; 28.374 previsioni originali, USD USA e EUR Europa. **NO training aggiuntivo, NO ricerca di iperparametri.** Le analisi storico-OOS non sono una prova prospectively untouched: stesso storico è già stato usato per orientare le ipotesi. Scopo: diagnosticare modelli esistenti. Modifiche in questo branch di ricerca, NON produzione.

## Riproducibilità
- Riproduzione dal pannello nativo 125F + previsioni annuali: [Actions run 40371581355](https://github.com/AM1975MA/Test/actions/runs/40371581355) **success**, test esatto sui 28.374 forward labels.
- [Source code as-of risk diagnostic](audit_predictive_direction_volatility_20261026.py).
- [Source evaluation of annual 127-leaf ranker](fit_paired_v3_127_annual.py).
- [Source of native same 21 session target](build_paired_v3_panels.py).
- [Source economic evaluation](evaluate_paired_v3_127_economics.py).
- Additional local independent audited predictive reconstruction with paired moving block (6 months), same 18 frozen head artifacts.
- CI artifact name: v3-eu-us-original-125f-predictive-direction-volatility (contains 5 CSV+manifest).
- Price/panel sources: 40226846660, 40227138117, 40227417589, 40218758892 (all before this investigation).

## 1. Actual OOS predictive skill, not portfolio CAGR

| Metric | US149 full | EU148 full | US75 equity | EU equity 89–112 |
|---|---:|---:|---:|---:|
| Spearman IC forward21 | +0.03427 | +0.00362 | +0.01383 | -0.00375 |
| Top5 forward21 excess vs monthly basket mean | +0.8064 pp/month | +0.2054 pp/month | +0.2523 pp/month | **+0.5438 pp/month** |
| Mean forward21 cross ETF std | 4.804% | 2.974% | 3.598% | 2.631% |
| Mean Top5 target rank percentile | 53.15% | 51.32% | 50.81% | 52.96% |
| Positive monthly Spearman of 101 | 53 | 49 | 52 | 50 |

Paired circular moving block 6 months, same 101 signal dates, 10,000 draws: full **US−EU Spearman gap +0.03065**, 95% CI **[-0.03575,+0.09606]**. Equity-only gap +0.01758, CI [-0.03361,+0.06930]. **Differences not statistically established.** Every model's monthly IC CI includes zero. Equity EU Top5 vs its own universe not worse than US equity (and raw fwd21 excess higher), so not a market-wide binary model failure.

Simple *pre-existing* momentum comparator (same labels): EU full MOM252 Spearman +0.0347 vs V3 +0.0036; EU equity MOM252 +0.0542 vs V3 -0.0037. US full MOM21 +0.0358 vs V3 +0.0343; US equity MOM21 +0.0564 vs V3 +0.0138. **No demonstrated V3 superiority over a simple ranking on mean Spearman IC in either geography.**

## 2. Central anomaly: the model ranks volatility rather than signed forecast return

Frozen model score versus **known past volatility** (cross-sectional monthly mean Spearman):
- US149 **+0.7845**; EU148 **+0.3705**.
- Score versus historic downside volatility126: US **+0.7741**, EU **+0.3527**.
- Mean past volatility percentile of 5 highest model picks: US **86.91%**, EU **76.40%**.
- Score vs future **absolute cross-sectional z deviation** (hindsight diagnostic ONLY): US **+0.2874**, EU **+0.2493**.
- Score vs future **signed return**: US **+0.0343**, EU **+0.00362**.
- Score vs risk-adjusted forward 21 return (scaled by past 126d daily vol): US **-0.04290**, EU **+0.00009**.
- Score vs historic mom252: US **+0.1409**, EU **-0.0960**.
- Score vs as-of mean monetary liquidity log ADV63: US **-0.0706**, EU **-0.2053**.

Model Top5 true future **best decile** vs **worst decile** (random roughly 10% each):
- US FULL: **28.32% best / 22.18% worst**.
- EU FULL: **20.40% best / 17.82% worst**.
- EU equity: **27.13% best / 14.85% worst**.
- US equity: **22.38% best / 18.02% worst**.

High probability of **both** outcome extremes: the model retrieves volatile names more reliably than their positive direction. This explains apparently good best-winner Top1/Top3 metrics coexisting with near-zero overall directional IC and severe drawdowns.

## 3. Volatility-only as-of placebo (strictly no future features)

Use highest five original **past vol126** ETF, same universe and signal dates, compare to model Top5. Hindsight realized next-21d values, no cash portfolio simulation:

| Full universe | V3 model mean true future rank % | VOL126-only rank % | V3 excess vs universe (pp/month) | VOL126-only excess |
|---|---:|---:|---:|---:|
| US149 | 53.15 | 46.48 | +0.806 | -0.457 |
| EU148 | 51.32 | 52.51 | +0.205 | +0.404 |

Paired 6-month block CI of **model − volatility placebo**:
- US Top5 mean forward rank advantage **+6.66 percentile points**, CI **[+2.21,+11.03]**; excess forward return +1.26 pp/month, CI [+0.06,+2.49].
- EU Top5 rank advantage **-1.19 percentile points**, CI **[-4.74,+2.32]**; excess forward return -0.20 pp/month, CI [-0.71,+0.32].
- Thus US model partially resolves winners among high-vol opportunities; **EU model does NOT demonstrate incremental directional selection over the naive volatility-only rule.** EU "model worse" descriptive point estimate **not statistically proven** as a stable true difference.

## 4. Data universes strongly non-equivalent

- EU 2018 annual training **5,999 examples** vs US **10,042** (same 70 months), EU **115 eligible candidates** beginning 2018 against US149. EU 2026 **18,525** train vs US24,346.
- 101 OOS-month forward21 asset correlations among instruments present on all dates: EU complete 112 instruments **mean pairwise corr +0.626**; US complete 149 **+0.448**. EU first PCA component **67.0% of standardized future-return variance** vs US **51.3%**; effective dimension ~**2.11** EU, **3.51** USA. Caveat: intentionally *different geographic/sector/asset-class compositions*, not a controlled Europe-vs-US alpha parameter.
- EURO V3 missing feature **volume_surprise21** in **26.3% TRAIN 2012–2017** and **7.07% OOS** versus US **0.27% TRAIN**, **0.01% OOS**. Numeric features volume126/beta barely missing in OOS, so EU volume surprise is standout issue. Historical vendor zero volume is not book-confirmed illiquidity, but obstructs source signal.
- Median cross-sectional return used as EU market proxy vs SPY for US: they are not algorithmically identical. Yet on actual EU dates EU median vs EUR EXSA historical daily returns correlates **+0.9843**; this difference **alone is unlikely root cause**.
- Native label: entry next common exchange session, exit 21 common sessions after entry; matched in both markets. Top1 21-session labeled outcomes correlate around **+0.95** with realized next-month actual account snapshots in **both**, so **no apparent systematic calendar offset**.
- Forward return cross-sectional daily price dispersion much larger in US (includes US sectors, commodities, EM/bonds and global foreign ETF exposures). Comparing direct CAGR also conflates portfolio opportunity set and profitability.
- Ranking labels are **within-month percentile ranks** of raw unadjusted (risk) future returns. The loss is XGB **rank:pairwise**, while overall business objective is positive **net excess return after downside and turnover**. This is objective mismatch; does not constitute source code label sign error.

## 5. Category effect: ex-post diagnostic only (not a tradeable decomposition)

Top5 realized future21 excess returns above the same month's universe mean decompose exactly as
category allocation = selected categories' ex-post equal-weight means minus universe mean,
and selection = chosen ETF's realized return minus its category mean.

| Market, scope | Category component pp/month | Within-category ETF component pp/month | Total |
|---|---:|---:|---:|
| US149 FULL | +0.224 | +0.583 | +0.806 |
| EU148 FULL | -0.053 | +0.259 | +0.205 |
| US75 equity | +0.121 | +0.132 | +0.252 |
| EU equity | +0.008 | **+0.536** | **+0.544** |

These components are future-return explanatory decomposition, NOT causally identifiable signals or separate tradable portfolios. US−EU component differences have broad paired bootstrap CIs overlapping zero. Supports splitting category eligibility/asset allocation from within-category ranking; category-neutral beta/risk additional tests still required.

## 6. Verdict and next experiment

**Not supported**: "The EU model is inherently much worse than the US model." Full IC difference has a wide paired CI spanning zero; EU equity Top5 is comparatively effective by raw forward excess. Equally unsupported: "V3 alpha is validated in the US": its full +13.86% CAGR trails passive SPY (EUR) +15.16%; EU full +3.91% trails EXSA +8.84%, same 10bp economic controls.

**Supported strongest defect**: the V3 model is primarily a **high-volatility selector**; its ranking signal poorly separates positive/negative tails, more clearly so in EU (no advantage over vol-only). It systematically prefers smaller turnover/liquidity at the EU cross-section. EU training has substantially less matured coverage and much higher missingness in volume data. Candidate universe is more correlated and has lower dispersion, further suppressing any absolute euro alpha.

**Recommendation**: STOP leaf count/complexity experiments. Define separate (1) as-of eligible liquid investable universe and category risk budget, (2) signed conditional expected-return model with risk/excess baseline and downside false-positive penalty, (3) out-of-sample directional ranking quality by **within-category and within-volatility decile**, downside-decile precision, Top5 signed excess and turnover/cost capacity, (4) truly independent time/point-in-time market snapshots and US/EU sector/factor matched cohorts. Do not tune thresholds or declare incremental alpha from this already inspected 2018–2026 sample. Keep current branch diagnostic only.
