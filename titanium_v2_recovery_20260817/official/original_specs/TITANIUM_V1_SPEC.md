# TITANIUM_V1 — Frozen Research Baseline

Frozen on 2026-07-26.

## Architecture

1. Alpha engine: concentrated top-1 selector.
2. Core score: 70% Compact + 30% Ridge TailMix.
3. Macro conditional filter: frozen development-selected conditional macro overlay.
4. Risk governor: stable top-1 governor configuration `RC0.25_RW0.25_RE0.25_CD3_S1`.
5. Point-in-time operation with D+1 execution and frozen data package.

## Mean results across 500 baskets

| Period | CAGR | MaxDD | Sharpe | Calmar |
|---|---:|---:|---:|---:|
| Development 2017-2022 | 18.8419% | -35.5601% | 0.7330 | 0.6112 |
| Holdout 2023-Jul 2026 | 29.4573% | -32.9424% | 0.9230 | 1.0012 |
| Full 2017-Jul 2026 | 22.3140% | -39.7522% | 0.8078 | 0.6332 |

## Relative to prior Meteor Governor

Full-period mean CAGR improvement: +6.5286 percentage points.
Full-period mean MaxDD deterioration: -10.7953 percentage points.

Titanium_V1 is frozen as the new operational research frontier. It is not a claim that every component independently passes full multiple-testing correction. TailMix and the macro conditional filter remain promising components whose standalone White Reality Check / CSCV evidence is not yet definitive.

## Immutability rule

Any future modification must use a new version name (Titanium_V2, Titanium_V1.1, etc.). Titanium_V1 files, parameters and scorecards must not be overwritten.
