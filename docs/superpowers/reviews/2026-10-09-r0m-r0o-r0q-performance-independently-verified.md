# ETF Trader V2 — Data independent performance audit of attempted 20bp pairwise loss
**Date 2026-10-09 · Research branch `research/v2-xgb-immutable-checkpoints-20261008` · No ETF/full-V2 retraining in this audit**

## Decision
**R0-M 20bp hard-band pairwise masked custom objective = NO GO on the pre-registered joint quality+stability criterion.** It stabilizes *deliberately excluded* near-tie Y changes on tiny artificial panels, but the matched unmasked objective retains better exact-winner identification, NDCG@5 and synthetic selected-return mean. **No actual ETF/portfolio CAGR has been measured for this candidate.** Do not advertise a hypothetical annual return or infer full V2 improvement. Keep original rank:pairwise, 360 rounds, 3 seeds, 2 horizons and original MA3 unchanged.

The read-only reviewer independently re-executed *tests and audit on preserved model-output artifacts*, NOT the already completed 18 R0-M model fits.

## Performance table — 40 held artificial test queries (two independent worlds ×20)
| Metric | Native `rank:pairwise` | Custom full-pairs, 0bp band | Custom full-pairs, 20bp mask |
|---|---:|---:|---:|
| Baseline Top1 in latent true best-5 | 32/40 | 33/40 | 33/40 |
| Exact latent best Top1 | **13/40** | **13/40** | 12/40 |
| Mean NDCG@5 (2 equal-weight worlds) | **0.922946** | 0.917695 | 0.915921 |
| X-only training perturbation Top1 agreement | 35/40 | **40/40** | 39/40 |
| Y-only one near-pair reversal Top1 agreement | 36/40 | 38/40 | **40/40** |
| Mean *synthetic* selected future return | **+4.0852%** | +4.0492% | +3.9421% |

**Matched causal comparison is 20bp vs 0bp CUSTOM, not vs native XGBoost**, because the two custom arms use full within-group logistic pairs with an approximate diagonal Hessian. The native rank:pairwise objective differs in pair sampling and gradient/Hessian. Thus of the 20bp mask **relative to 0bp custom**, Y agreement improves 38/40→40/40, X agreement declines 40/40→39/40, NDCG −0.001774, exact winner declines 13/40→12/40, mean selected artificial return declines 4.0492→3.9421%, i.e. **−0.10715 pp per artificial decision, not CAGR**.

**World-by-world** (20 test queries each):
- World A native/custom0/custom20: Top5 16/17/18; exact winner 9/9/9; X agree 18/20,20/20,20/20; Y agree 19/20,19/20,20/20. Masked selection latent return is −0.000576 versus custom0.
- World B native/custom0/custom20: Top5 **16/16/15**, exact **4/4/3**, X agree 17/20,20/20,19/20; Y agree 17/20,19/20,20/20. Masked selection latent return **−0.001567** versus custom0.
- R0-M purposely reverses one synthetic ordinal pair of near-identical returns; it falls within the 20bp mask before and after reversal. The perfect Y stability of that arm is therefore *partly structurally guaranteed by how the perturbation was designed*, not evidence of immunity to broad vendor-vintage revisions.

**Independent revalidation 2026-10-09**:
- `pytest` on original R0M four tests and original R0L eight tests: **12 PASSED**; R0M `data_audit.py` reports **`DATA_AUDIT_PASS`**, **18 archived models**, two worlds and all three training scenarios. No model training performed by QA.
- Additionally audited related closer-to-native R0-O `rank:pairwise` topk5 vs default, full canonical three XGB seeds and 360 iterations: in 60 artificial test groups top5 hits **43→37**, exact winners **13→15**, NDCG@5 **0.871001→0.867030**, artificial return **3.27199%→3.17076%**, X-only Top1 agreement **56→58**, Y-only **46→53**. Four targeted tests PASS; archived `data_audit.py` recomputation returned `guards_all_pass=false`. This distinct native-topk5 objective also **fails joint release gate** and should not be tuned against old Original149.
- **No full V2 trading engine/canonical MA3 predictions were generated for either intervention**, so **financial CAGR and daily drawdown are unknown**, not zero.

## Data-led further direction — real feature instability, do not conflate with investment return

The independently checked R0-Q real-Yahoo-data audit identifies a distinct stronger *engineering* mechanism upstream of learner fitting: hard missingness threshold inside `source_only/kernel.py::rolling_downvol` with `r.where(r<0)` and `min_periods` measured in negative days instead of all trading days. Very small adjusted price changes can flip a return across zero and discontinuously alter the input validity/sample STD, then cross-sectional median/MAD feature scaling.

A continuous negative-part second moment `sqrt(mean(min(r,0)^2)) * sqrt(252)` reduces variation on the **exact matched 4-way nonmissing cells** of Repeat1/3:
- h21: 18,412 identical cells, mean absolute cross-vintage delta lower **23.20×**, `>0.1` normalized feature-diff events **44→0**.
- h63: 12,724 identical cells, mean absolute delta lower **43.96×**, events **16→0**.
- h126: 8,676 identical cells, mean absolute delta lower **24.25×**, events **4→0**.

Independent audit re-run: **6 unit tests PASS**, all matched-support checks PASS. This is **real measured input-feature stability**, not ETF model prediction or full portfolio performance. **Major caveat:** the new formula changes the semantics and missing-value support of the feature and may modify the training cohort/features; it **must not** be dropped into a previously fitted Booster or production V2 unchanged.

## Practical next validation gate

1. To obtain **actual economic performance of the 20bp loss**, need a canonical-source-compatible **annual** fit on a genuinely novel point-in-time ETF as-of universe, identical X/y/groups/trading engine and matched V2 baseline, plus full 3-seed×2-horizon/MA3/risk daily ledger, costs/turnover/DD/tail upside. None of those exist in the archived R0-M files. The history 2017–2026 is a **burned development set**, not an independent holdout, and even a new backtest there would not prove future performance.
2. Because this precise 20bp hard mask **failed its preregistered synthetic gate**, **do not consume such full-V2 compute on this candidate** merely to produce a headline CAGR. Keep its proof-of-concept separate.
3. Priority instead: isolate R0-Q feature-input continuity effect on a source-compatible valid/mature panel and test actual Compact21 **X-only** stability with one preregistered feature-representation candidate, checking top-tail skill; if successful, extend to matched full V2 on *fresh* as-of data.
4. No `Etf_trader` or `Trader_selector` modifications; files reside exclusively on `Test` isolated branch. No independent external agents were dispatched in this review.

**Source artifacts already present in the conversation runtime**: `/mnt/data/ETF_Trader_V2_R0M_Data_20261009.zip`, `/mnt/data/ETF_Trader_V2_R0O_Data_20261009.zip`, `/mnt/data/ETF_Trader_V2_R0Q_Continuous_Downside_Data.zip`. Re-run **QA only**, do not repeat expensive model fits.
