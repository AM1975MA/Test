# Strict causal Cboe feature loader

Implemented in `olc111/src/cboe_features.py`; behavioral tests are in `olc111/tests/test_cboe_features.py`. This task changed only those two new files and this note. It did not modify OLC110, raw CSVs or the acquisition manifest, and did not fit any model or simulate a financial account.

## Public API

```python
from cboe_features import load_cboe_features

cboe = load_cboe_features(raw_dir, decision_dates)
```

`raw_dir` must contain `VIX9D_History.csv`, `VIX_History.csv` and `VIX3M_History.csv`, with `DATE` in Cboe's `%m/%d/%Y` format and a `CLOSE` column. Other columns are ignored. VVIX and SKEW are not used. `decision_dates` is an array-like collection accepted by pandas `DatetimeIndex`; dates must be valid and timezone-naive. Intraday times normalize to the same calendar date, and input ordering is preserved.

| Result key | Shape / type | Meaning |
| --- | --- | --- |
| `dates` | `(n,)`, `datetime64[D]` | Normalized decision calendar dates |
| `available` | `(n,)`, Boolean | Common valid sample for both Cboe blocks |
| `source_dates` | `(n, 3)`, `datetime64[D]` | Latest strictly prior source dates, ordered VIX9D, VIX, VIX3M; missing sources are `NaT` |
| `source_age_days` | `(n, 3)`, float | Calendar-day ages; absent sources are `NaN` |
| `term` | `(n, 2)`, float | `log(VIX9D / VIX)`, `log(VIX / VIX3M)` |
| `legacy` | `(n, 2)`, float | `log(VIX)`, `log(VIX / VIX_21_source_sessions_ago)` |
| `metadata` | dictionary | Source order, feature names, timing settings, official URLs, actual raw-file SHA-256, bytes and row counts |

Metadata uses actual input bytes and remains separate from model features. The loader records provenance but does not fit, scale, normalize across observations, enforce an external expected hash or persist outputs. The source manifest was read during implementation, and the actual CSV hashes, byte sizes and URLs were separately verified against `data/CBOE_SOURCE_MANIFEST.json`.

## Causality and rejection rules

For each index, choose the latest source row satisfying `source_date < decision_calendar_date`. Equality is always excluded, even if the decision input carries an intraday time. The implementation uses a left-sided source-date search, never future fill.

After the independent lookups, all three latest source dates must be identical. Different dates invalidate the entire feature row; the loader never silently backdates any index to fabricate a matching term structure. Every selected source must be 1–7 calendar days old inclusive and have a finite, strictly positive close.

Legacy maturity requires a finite, positive VIX close exactly 21 source rows before the selected current VIX row, so at least 22 VIX observations are required. The lag is based on rows in the preserved source series, not on European decision dates, elapsed calendar days or a manufactured business-day calendar. Invalid closes remain in their original session positions and are not dropped. An invalid current close or lag endpoint invalidates the common mask. Duplicate, unsorted or invalid source dates raise `ValueError` because their ordering is ambiguous.

When any requirement fails, `available=False` and **both entire feature blocks are NaN** for that row. The selected source dates and ages remain available for diagnosis. Natural-log differences implement the requested log ratios without creating unnecessary ratio overflow.

## Expected experiment integration

Construct the requested feature blocks as PRICE, PRICE plus `legacy`, and PRICE plus `legacy` plus `term`. Use the shared `available` mask, together with any existing PRICE/label validity rules, consistently for their paired comparison. There is no `X_price_extra` alias: named arrays make the two additions explicit. Model fitting and financial execution remain outside this loader.

## Test-first verification

The first run was performed before creating the loader and failed as intended because the public implementation was absent: 13 test methods, 24 assertion failures including invalid-value subtests. After the implementation, both the targeted command and the full OLC111 discovery command passed:

```text
python -m unittest discover -s tests -p test_cboe_features.py -v
Ran 13 tests in 0.257s
OK

python -m unittest discover -s tests -v
Ran 13 tests in 0.242s
OK
```

The full discovery result reflects the OLC111 test files present at that verification time. The tests exercise real temporary CSVs, without mocked source data readers. They cover:

- Same-day US-close exclusion, including an intraday decision timestamp.
- Weekend and US holiday carry-forward from the preceding observed source session.
- Seven-day acceptance and eight-day rejection.
- No source before the decision, with no future backfill.
- Common-mask maturity at 21 versus 22 observed VIX closes.
- Hand-checked ratios and the exact 21-source-session VIX change across holidays.
- Future close mutation leaving all earlier output arrays unchanged while provenance hashes change.
- Different latest source dates causing rejection without backdating.
- Zero, negative, NaN and infinite latest closes across all three indices, without fallback to a previous close.
- Invalid VIX lag endpoints.
- Duplicate and unsorted source dates.
- Empty decision arrays retaining their public shapes.

## Read-only check against acquired CSVs

An illustrative weekday grid from 2020-03-02 through 2026-10-30 contains 1,740 dates. It is a calendar-business-day check, not the ETF exchange calendar or an experiment sample definition. The loader returned 1,707 available rows and 33 unavailable rows, with a maximum accepted source age of four calendar days. Every available source date was strictly earlier than its decision date and identical across the three indices; all accepted features were finite and all rejected feature rows were NaN.

All 33 exclusions on that illustrative grid were differences among latest source dates; none were absent/stale source rows. For example, at decision date 2022-05-31 the latest source dates were VIX9D=2022-05-27, VIX=2022-05-30, VIX3M=2022-05-27, so the common mask correctly rejected the row. This documents the consequence of the explicitly requested same-source-date rule rather than changing the source observations.

| Source | Bytes | SHA-256 matched to acquisition manifest |
| --- | ---: | --- |
| VIX9D | 202682 | `c29cb0795e2ab676e5d1fdc42cb3f53d8e66c3daf36a492ec0192f033e690874` |
| VIX | 474859 | `d4e2b1199951501b7757814b6e1c2356394922a7ea8ef16d85c3a4596e6e2c2d` |
| VIX3M | 220141 | `6fa2ba5f8b85bf62a98ba14acf5e03c712298dffe534d3c73998e21db1248a4b` |

Implementation SHA-256: `094c278adb6363136a2ffc2528d56c765b9508b2fe593893748fcf66c90db62c`.

Test-file SHA-256: `a403c6a1649cf73a65283637c1c274ef7d36b9edfae49e353efb85c7e1bd9b4b`.
