# OLC34 — Reproducible offline research bundle

Research experiment on the *incremental* ex-ante predictive value of CBOE VIX, reusing frozen OLC32 ETF labels and OLC33 classifier. No trading orders.

- Original preregistered experiment protocol commit: `320d11c9c29180f669f54dd45f92bb01b4d4e043`.
- Data source problem found *after* first outcome replay: index quotes on non-session dates; transparent addendum commit `84520a5a976fbca38b7baaa9e5d6b1bbfc461021`.
- Corrected data audit and re-run (`exchange_calendars` XNYS-session screen) are **post-audit sensitivity**, not independent first-pass confirmation.
- Snapshot SHA1 Git blob: initial VIX `762fe8cd591b45cae78a869e8b1541e14fc87188`; filtered `28c334adcf0f8f43477c8df99ae311a12b44d441`.
- Cboe VIX source mirrored through https://github.com/datasets/finance-vix/tree/main/data, blob `c05e0d9c28ddf3b98d0531017ef5b5180df05ae1`.
- Full tested features, thresholds and gates unchanged. No optimization on 2021-2024 results.

## Re-run (relative to this directory)

Install Python 3.11+, numpy, pandas, scikit-learn, exchange-calendars.

```sh
python src/olc34_vix_context_exchange_filtered.py \
    --input input/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz \
    --vix results/OLC34_VIX_ASOF_SIGNAL_EXCHANGE_FILTERED.csv \
    --baseline-src src/olc33_tail_condition.py \
    --out temp_rerun
python src/verify_olc34.py
```

Compare `temp_rerun/OLC34_RESULTS.json` to frozen `filtered/OLC34_RESULTS.json`. `verify_olc34.py` validates frozen persisted results and has a temporal label-perturbation test. Earlier OLC33 prediction artifacts are included in `olc33_reference/` for parity.

## Files

- `REPORT_OLC34_IT.md`: methodological and results explanation.
- `input/`: 27,191-row (non-raw) frozen OLC32 corrected data source (completely copied), not newly sourced prices.
- `src/`: OLC33 baseline and OLC34 original / calendar-screened replica and verifier.
- `results/`: initial and corrected external VIX snapshots.
- `filtered/`: complete OOF probability table (720 rows), model coefficients, action decisions, month/market performance, block bootstrap draws, verification JSON and outcome summary.
- `figures/`: error chart and EU/USA comparative cumulative *spread vs Top1*, **not NAV**.

**Limitations:** source mirror can contain pseudo-quote dates, XNYS regular-session screening is a proxy rather than original CBOE observed mask; USA original observed ETF quote mask missing; dividends/taxes/FX/transaction prices and actual bid-ask not certified; historical 2021–2024 heavily explored in earlier iterations.