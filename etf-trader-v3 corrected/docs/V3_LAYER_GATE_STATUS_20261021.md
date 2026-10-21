# ETF Trader V3 Corrected — Sequential functional gate status

**Date:** 21 October 2026. **All results exploratory** on previously investigated 149 ETF / 500 basket original OHLCV. Production V2 unchanged. **CAGR deliberately excluded from layer tuning**.

| Gate | Mission | Outcome | Functional evidence / decision |
|---|---|---|---|
| L00 | Correct and audit feature formulas, true missingness, source data | **QUALITY_PASS** | 203 fields checked, OHLC source price tolerance met; 125 corrected Compact frozen; exact Tail duplicate groups identified |
| L01 | Find actual next-21D ETF winners | **PAIR127 FROZEN** | Winner Top3 **35.47%** on 101 months; pair63 only **32.24%**, NDCG loss only **17.77%** despite higher rank IC |
| L02 | Detect strongly winning ETFs, independent of risk layer | **ELITE45 SPECIALIST** | Top-tail AP **0.2884** (Ridge45 0.2697), Tail target winner Top3 **39.80%** (Ridge45 35.47%), but 21D false bottom selections rise 25.62%→28.02%. 15 Tail aliases removed with negligible change |
| L03 | Ex ante predict which frozen expert works in a regime | **REJECT market-only gate** | 53 months; AUC **0.470**, Brier **0.254** vs constant prior **0.250**. No demonstrated regime prediction |
| L04 | Exploit complementary model predictions without target lookahead | **NO BLEND PROMOTION** | Tail-only next21D Top3 **42.75%**, 50/50 **41.90%** over 101 months; strict prequential meta model **44.26%** vs Tail **44.27%** on matched 53 later months |
| L05 | Stable diversified budget and limited selection churn | **TOP3 DECAY CANDIDATE** | Tail-driven [50%,30%,20%] lowers monthly target-weight churn 0.474→**0.383** and weight in future bottom 3 28.01%→**26.70%**, while weighted future-rank quality remains ~0.513 |
| L06 | Prevent large losers without missing most winners | **REJECT 85th-percentile veto** | Standalone risk AP **0.290**, AUC **0.755**; hard risk exclusions reduce future bottom-3 weight 26.70%→17.71% but devastate winner Top3 42.75%→**20.64%** and raise churn |
| L07 | Full integrated causal strategy certification | **NOT STARTED** | No single newly approved regime/fusion/risk policy suitable for production. Need further risk-policy research and new untouched evaluation vintage before integration |

## Frozen research interfaces

- **Corrected feature baseline:** 125 Compact, corrected `downvol`/RSI and true-missing semantics; original 149-ETF snapshot.
- **Predictive ranker reference:** XGBRanker pairwise, 127 leaves/360 rounds, 3 seeds; no special risk or regime.
- **Tail expert:** 45 distinct correct Tail inputs, historical annual logistic classifier of matured upper-decile Tail labels; preserves scores separately from Ranker.
- **Regime:** no validated gating model; do not label hindsight winners as observable regimes.
- **Blending:** no confirmed improvement; do not promote arbitrary weights or supervised meta.
- **Allocation candidate:** top three by Tail rank, fixed target weights [0.5,0.3,0.2].
- **Risk:** keep 45-feature bottom-decile classifier as diagnostic; no live/replay hard veto until selection-loss false alarms controlled.
- **Releases:** production remains unchanged; all code, fit audits, OOS month tables, full artifact zips and rejected trials are archived. Full V3 integration remains a **blocked research gate**.

## Provenance and completed Actions

- L00/L01: [39652989033](https://github.com/AM1975MA/Test/actions/runs/39652989033), corrected 125 OOS, source [39482809691](https://github.com/AM1975MA/Test/actions/runs/39482809691).
- L02 elite winner: [39655513813](https://github.com/AM1975MA/Test/actions/runs/39655513813); L02 downside tradeoff: [39657701155](https://github.com/AM1975MA/Test/actions/runs/39657701155).
- L03 market regime: [39659065223](https://github.com/AM1975MA/Test/actions/runs/39659065223).
- L04 frozen score fusion: [39659903643](https://github.com/AM1975MA/Test/actions/runs/39659903643); supervised meta: [39660554536](https://github.com/AM1975MA/Test/actions/runs/39660554536).
- L05 selection quality: [39661273577](https://github.com/AM1975MA/Test/actions/runs/39661273577).
- L06 independent bottom-tail risk veto: [39662062361](https://github.com/AM1975MA/Test/actions/runs/39662062361).

**Research methodology:** Months, not overlapping basket draws, define independent chronological blocks for paired uncertainty; mathematical validity and predictive quality have separate gate outcomes; corrected feature semantics are maintained even when older incorrect signals historically fit better.

## L06.2 — Trial: within-Top3 risk reweighting (21 October 2026)

[Audited result](../reports/L06/20261021_SOFT_RISK_WEIGHT_SKILL.md): same three ETF candidates retained, winner capture exactly **42.7465%**; bad-bottom3 weight 26.6952%→26.3915%, but winner weight 15.2176%→14.9645%, and target-weight churn 0.38336→0.39941. The risk head's conditional AUC among preselected basket candidates is **0.575** vs universe-wide AUC **0.755** (different outcome conditioning). **Decision: inconclusive/NOT PROMOTED.** Next test must improve conditional risk discrimination with the allocation fully frozen, not optimize a risk penalty on these same OOS years.

## L06.3 — Selection-conditional loss classification (21 October 2026)

[Technical report](../reports/L06/20261021_CONDITIONAL_RISK_SKILL.md): New model trained annually from historical OOS Tail-selected ETF candidates to predict basket-relative future worst-three outcome **did not improve** risk identification. On 53 later-year months, AP **0.4227 vs 0.4368** for calibrated frozen global risk, paired 95% CI of delta **[-0.0198,-0.0090]**; AUC about **0.577** either way. **REJECT conditioned3**; preserve Tail Top3 baseline and the frozen risk model as diagnostic. The next isolated L06 check will assess **absolute large-loss event detection** rather than basket-relative losers. No CAGR / allocation changes.

## L06.4 — Genuine absolute >=10% loss risk forecasting

[Source-backed 53-month test](../reports/L06/20261021_ABSOLUTE_LOSS_SKILL.md): On 2,281 distinct Tail-selected ETF-months (162 large next-21D losses), frozen original risk score delivers **ROC-AUC 0.6266 (95% month-block CI 0.543–0.724)**, AP **0.1325 vs 0.0710 prevalence**, and new train-only probability calibration Brier **0.06550 vs constant 0.06640**. **RISK FORECASTING: LIMITED FUNCTIONAL PASS**, with substantial false alarms. No actual policy approved; proceed to single fixed weight-only candidate test, not hard veto. No CAGR.

## L06.5 — Research candidate: calibrated absolute-loss risk soft weights

[Functional test](../reports/L06/20261021_ABSOLUTE_SOFT_POLICY.md): 53 maturity-safe OOS months, same frozen Tail Top3 50/30/20 ETFs, adjusted weight `normalize(original_weight*exp(-3*p_abs_loss10))`. Severe actual next21D loss exposure **9.244%→9.146%** (−0.098 pp), winner weight **15.666%→15.574%** (−0.091 pp), future rank quality **0.505593→0.506417**, regret **0.115445→0.115259**, churn **0.3471→0.3562**. **RESEARCH CANDIDATE; NOT APPROVED for production or L07.** Next independent confirmation and cost-aware evaluation required. No CAGR optimized.
