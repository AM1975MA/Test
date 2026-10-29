# EU165 — V2/V3 ranker predictive utility for HOLD vs SWITCH

**Date: 29 October 2026. RESEARCH ONLY; no production model/portfolio changes.**

## Explicit research question

Previous source-native 2018–26 EU165 ranker replays found V2/V3 often capture the best future ETF inside Top3 more than simple MOM252, especially pre-2025. Does that superior *ranking* generate an incremental **net return advantage** when deciding to replace an ETF already owned?

This is a **matched basket/month one-shot forecast-outcome diagnostic**, NOT portfolio CAGR, not a new full V2/V3 simulation, and not a new model training.

## Design

- EU165 2026 survivor-defined universe; 101 historical as-of monthly PIT 500×24 **STABLE_HASH_MONTHLY** eligible baskets, 4 instruments per six coarse macro-clusters.
- Real Europe-source-trained annual scores V2 Titanium, V2 Leaves127, V3 Corrected Pair127, V3 Event45, V3 Ridge45, historical Full Hybrid variants; simple MOM252 and MOM63 controls.
- Fixed same **incumbent ETF** across all models: last month's MOM252 Top1 within that exact basket; sensitivity: last month's V2 Titanium Top1. The incumbent must remain in the current basket and all 24 candidates must have finite scores/outcomes. PIT basket timestamp not newer than source score timestamp, including December 2025 adjustment.
- At each month-end score signal, compare HOLD vs TOP1 SWITCH, HOLD_IF_INCUMBENT_RANK_LE_3, and TOP3_EQUAL alternatives. Future **Open-based 21/42/63 session labels** are used ONLY to evaluate outcomes, not to choose trades.
- Switch of whole capital pays **0.10% sold + 0.10% purchased = 0.20%** model cost. Equal Top3 costs exact gross weight turnover.
- Monthly equal-basket means, inference with circular **6-month block bootstrap on months** (500 overlapping baskets **not independent**), Holm correction within compared families.
- Primary pre-2025: **68 matched months for 21/42, 67 for 63**; compared with 75 in prior ranker-only study, since incumbent must exist and survive to be actionable.

## Matched-horizon mean *incremental net advantage over holding* (not CAGR), 2018–24:

| Model TOP1 choice | 21d | 42d | 63d | Fraction switched at 21d |
|---|---:|---:|---:|---:|
| MOM252 | -0.248 pp | -0.651 pp | -0.631 pp | 36.7% |
| V2 Titanium | -0.333 pp | -0.669 pp | -0.593 pp | 87.5% |
| V2 Leaves127 | -0.413 pp | -0.764 pp | -0.691 pp | 89.1% |
| V3 Pair127 | -0.248 pp | -0.712 pp | -0.740 pp | 89.7% |
| V3 Event45 | -0.317 pp | -0.493 pp | -0.451 pp | 86.8% |
| **V3 Ridge45** | **-0.112 pp** | **-0.050 pp** | **+0.164 pp** | 86.2% |

Paired advantage of V3 Ridge45 over MOM252 TOP1: +0.136 pp at 21d, 95% block interval [-0.605,+0.997]; +0.601 pp at 42d [-0.366,+1.585]; +0.795 pp at 63d [-0.983,+2.991]. **None significant after comparison corrections; all intervals include zero.**

Predefined HOLD_IF_RANK3 reduces V3 Ridge45 21d switch frequency to 69.9%; mean net edge relative to holding rises to **+0.031 pp**, 95% block interval [-0.704,+0.767]pp. V3 Event45 rule improves versus its own unconditional TOP1 by +0.220 pp (nominal positive, Holm **p=.132**), not proven.

**TOP3_EQUAL** at 21d from fixed incumbent: MOM252 -0.542 pp, V2 Titanium -0.576 pp, V3 Pair127 -0.428 pp, V3 Ridge45 -0.429 pp. None demonstrates robust improvement vs MOM on matched months.

Sensitivity when incumbent V2 rather than MOM: at 21d V3 Ridge45 -0.06 pp vs HOLD, V3 Pair127 -0.16 pp, V2 Titanium -0.22 pp and MOM -0.31 pp. This illustrates the **dependence of switch utility on the already-held position**.

2025 separate and already mined: MOM252 switches still perform better than V2/V3; cannot use to select/promote a model.

## Interpretation / next experiment

Original V2/V3 source-native forecasting capability remains promising on Top3 hit and coarse macro-group prediction, but **the ranking alone does not establish a net economic reason to sell the current winner**. DO NOT discard their models or rewrite all downstream layers on these results; design and test a **direct pairwise expected 21/42/63d candidate-minus-incumbent reward** with matured-label walk-forward, uncertainty calibration on training only, and an explicit no-trade region.

No full portfolio NAV/CAGR was produced. 42/63 future windows overlap; div/total return and spread/slippage not certified; 2026-curated universe lacks delisted funds and multiple comparisons exhausted 2018–26. Cannot call this independent holdout or deploy.

## Reproducibility

Downloadable conversation ZIP: `ETF_TRADER_EU165_HOLD_SWITCH_ECONOMIC_SKILL_20261029.zip`, SHA256 **e9b30768247244ab8beafa661ea88b78c4ffa523cc7ee5c166394568f6f47e8f**, ~16.82MB; includes monthly scorecards, 6-month block CIs, group attribution, code and minimum input data to independently replay the **economic skill audit** (original native training provenance in the preceding European score study). An independent replay reproduced all **792 scorecard rows to tolerance 1e-12** with exact cost-accounting validation (~2e-16). Original USA149/V2/V3/B0 production unchanged.
