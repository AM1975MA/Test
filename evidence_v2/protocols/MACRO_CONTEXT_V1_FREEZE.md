# Evidence V2 — Macro Context v1 data freeze

Status: **FROZEN BEFORE MODEL TEST**

Purpose: create an immutable macro-context dataset before any Evidence V2 model is fitted or evaluated.

## Source series

Exactly these FRED IDs are permitted after the documented pre-model availability correction:
- `VIXCLS`
- `DGS2`
- `DGS10`
- `BAA10Y`
- `DTWEXBGS`

`BAA10Y` replaces the initially specified `BAMLH0A0HYM2`, which became unusable for long-history retrieval because FRED exposes only the latest three years of that licensed ICE series in 2026. The substitution is documented separately and occurred before any model fit or performance observation.

Freeze interval: `2005-01-01` through `2026-06-30` inclusive.

## Fixed transformations

Exactly six model-context features are produced:
1. `vix_z252`: rolling z-score of log VIX, 252 business days, min 126;
2. `dgs2_delta21`: 21-business-day change in 2Y yield;
3. `dgs10_delta21`: 21-business-day change in 10Y yield;
4. `curve_10y2y_z252`: rolling z-score of 10Y-2Y curve, 252 business days, min 126;
5. `baa10y_z252`: rolling z-score of BAA10Y credit spread, 252 business days, min 126;
6. `usd_ret21`: 21-business-day log return of broad USD index.

Missing daily observations may only be forward-filled for at most 5 business days. No interpolation or future fill is permitted.

## Temporal rule

Any model using this dataset must perform an as-of join with `macro_date < signal_date`. Exact-date observations are deliberately excluded to eliminate same-day publication timing ambiguity.

## Quality gate

- no observations after `2026-06-30`;
- every transformed feature has >=97% non-null coverage from `2007-01-01` onward;
- all non-null transformed values are finite;
- raw downloaded bytes and transformed CSV are persisted with SHA256 hashes;
- no model output is computed in this workflow.

## Limitation recorded in advance

This freezes FRED current historical market series as retrieved and is not an ALFRED vintage reconstruction. These are market/rate series with comparatively low revision risk, but any later promotion test should independently review point-in-time provenance.