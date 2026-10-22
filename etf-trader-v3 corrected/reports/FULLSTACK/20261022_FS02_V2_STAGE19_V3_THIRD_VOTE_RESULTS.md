# Full-stack V3 FS02: ETF_TRAINER_V2 original risk conviction versus extra V3 model confirmation

**Executed 22 October 2026; exploratory, no V3 policy promotion.** Original V2 full-stack from frozen RAW, full source-only Titanium/S3B/Hybrid24 training, original continuous dynamic Top2, DD-first, V6 REL_B, HighCAGR24, exact original daily intraday engine at 10bp. All original upstream source SHA locks and maturity audits passed.

Successful [FS02 run 39836842157](https://github.com/AM1975MA/Test/actions/runs/39836842157), artifact **12451018561**, includes complete RESULT.json, 114-month source-only Hybrid24 as-of predictions and 500×2366 daily NAV paths. Previous exact Hybrid24-only run **39834445061** reproduced fully identical original mean CAGR to 1e-10. No ranker retraining, no future outcome as signals, frozen original 149 OOS Pair127 score stream run 39700865721.

## Isolated conditions

1. **V2 Hybrid24**: source-only full 149 OHLCV, original 500 baskets, all risk/position layers, base Top2 dynamic weights and 10bp fees.
2. **ETF_TRAINER_V2**: same original selected Top2; in risk-off C4/SEVERE only, score margin >=0.03, AND original Hybrid24 ET and XGB components both prefer original top1 to top2, concentrate risky sleeve to 100% Top1. No change to gross, V6 alt, candidates or fees.
3. **V3 three-model confirmation**: same ETF_TRAINER_V2 action allowed only if the original frozen V3 CORRECTED Pairwise127 ALSO prefers that exact selected Top1 to Top2. Missing 2017 V3 OOS falls back to V2. This is a VETO of original risk-sleeve concentration, not a new universe rank.

All 500 baskets from original canonical SHA 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e and identical raw CSV aggregate SHA 0ee4be0cb24bc550194b7f1fb0aefc244b8df575c0c7bbd683a5203f2a74576d.

## Source-only results — arithmetic mean individual-basket statistics

| Period / metric | Original complete Hybrid24 | ETF_TRAINER_V2 original risk sleeve | Additional V3 third-vote |
|---|---:|---:|---:|
| 2017–2026 mean CAGR | 22.1772% | **22.4593%** | 22.2563% |
| Mean maximum drawdown | **−35.2972%** | −35.3786% | −35.3749% |
| Mean Sharpe | 0.86963 | **0.87402** | 0.86952 |
| 10th percentile CAGR | 10.8041% | **10.8948%** | 10.6224% |
| Worst single-basket MaxDD | −64.997% | **−63.205%** | −64.590% |
| 2017–2022 development CAGR | 17.9112% | **18.3242%** | 18.0294% |
| 2023–2026 later CAGR | 30.5149% | **30.5594%** | 30.5288% |
| 2022+ CAGR | 25.1255% | **25.4122%** | 25.2628% |

Original ETF_TRAINER_V2 risk agreement improves over original full Hybrid24 by **+0.2821 percentage points** mean-basket full CAGR and better Sharpe, p10 and worst basket DD in this vintage. V3 third-model vote throws away **0.2030 percentage points** of that gain. This confirms that the old V2 model-consensus sleeve is important and should be preserved, while V3 Pair127 must NOT be used as a blanket third veto.

The historical ~24.897% V2 candidate and 24.490% Hybrid24 both used the older Sept clean snapshot and **must not be compared across raw vintages**. Current matched source-only V2 candidate is 22.4593%, old raw older V2 24.897%. 2023+ results remain approximately 30.56% in the later period. No historical 2017–26 is a virgin holdout.

Risk action diagnostic: 74,792 500-basket×trading-day risk-off eligible exposures; ET+XGB consensus approved 41,965 of these, stricter V3 third-vote only 22,680. These correlated basket×day counts are NOT independent trades. Exact real trade notional is in artifact PATH.npz.

Decision: restore documented ETF_TRAINER_V2 risk agreement as a **research available downstream policy**, keep full original V2 as same-raw comparator. Reject V3 third-model requirement; no production change or assertion V3 beat best V2. Next research FS03 predeclares a different V3 contribution as optional 2-of-3 majority vote only in the same C4/SEVERE riskoff states, an explicit *new* exploratory hypothesis.

Reproducibility: original copied source under fullstack_legacy/src/etf_trader, tested variant runner fullstack_legacy/scripts/run_v3_fullstack_risk_agreement.py, .github/workflows/v3-fullstack-model-agreement.yml, pre-result protocol 20261022_RISK_AGREEMENT_PREREG.md, completed run 39836842157.