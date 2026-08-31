# Saved alpha challenger — STEP08F Event-Time Titanium

Date: 2026-08-31
Status: **SAVED FOR FUTURE TITANIUM ALPHA RESEARCH — NOT A DD PROMOTION**

## Why this is preserved
STEP08F failed the DD-promotion gate because tail drawdown metrics worsened, but it produced a clean and temporally replicated CAGR improvement when the stale monthly Titanium destination score was refreshed at each q95 event.

## Frozen result versus FUSION1, development 2021–2022
- Delta CAGR: **+0.632483 pp**
- Delta mean MaxDD: **+0.050503 pp**
- Delta Sharpe: **+0.016452**
- 2021 delta CAGR: **+0.314126 pp**
- 2022 delta CAGR: **+0.987675 pp**

## Producer identity
Event-time score producer: HGB distillation of authentic historical `TIT_R`.
Pre-development 2019–2020 parity audit:
- mean same-date Spearman: **0.864606**
- median same-date Spearman: **0.903810**
- mean basket Top-3 overlap: **0.536917**

No economic 2021–2022 outcome was used to select the producer.

## Interpretation
The result is evidence that **refreshing Titanium cross-sectional information at event time contains alpha**. It is not evidence of a better DD controller: overall p10 MaxDD worsened by -0.865013 pp and p5 by -1.974486 pp.

Future Titanium work should treat this as a separate alpha challenger and investigate how to incorporate event-time score refresh without inheriting the adverse tail-risk behavior of the STEP08F protective-rotation implementation.

## Source
Full reproducible package: `STEP08F_EVENTTIME_TITANIUM_DEVELOPMENT_REPRO_20260831.zip`.
2023+ was not opened for STEP08F.
