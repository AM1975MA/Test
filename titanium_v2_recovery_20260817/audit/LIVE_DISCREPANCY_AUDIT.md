# Titanium live vs frozen — discrepancy audit

Audit date: 17 August 2026  
Verdict: **FAIL — the August live producer is not equivalent to frozen Titanium V2**.

## Executive result

The live package is a legitimate retrained variant, but it does not reproduce the authentic `TIT_R` ranking or the official 500-basket experiment. It must remain versioned separately and must not replace the frozen Titanium V2 baseline.

## Ranking and selection parity

The comparison covers the 113 common signal dates from 31 January 2017 through 29 May 2026.

| Test | Result |
|---|---:|
| Mean monthly score correlation, live vs authentic `TIT_R` | 0.8374 |
| Whole-universe top-1 agreement | 27 / 113 = 23.89% |
| Whole-universe top-2 set agreement | 7 / 113 = 6.19% |
| Basket-level top-1 agreement | 24,545 / 56,500 = 43.44% |
| Basket-level ordered top-1/top-2 agreement | 8,874 / 56,500 = 15.71% |
| Basket-level unordered top-2 agreement | 13,856 / 56,500 = 24.52% |
| 100/0 vs 75/25 concentration-regime agreement | 51,225 / 56,500 = 90.66% |

The high score correlation confirms common lineage, but the low selection agreement proves that the live model is not an exact recovery.

For comparison, authentic `TIT_R` reproduces the official selection matrix on **56,500 / 56,500 decisions**.

## Basket mismatch

The live package regenerated the 500 baskets instead of reusing the frozen membership:

- only 10 of 500 baskets match exactly;
- only 2,317 of 12,000 basket-ticker memberships are shared;
- 9,683 official memberships were replaced by 9,683 different memberships.

This makes the live 500-basket distribution a different experiment even before score differences are considered.

## Universe and data mismatch

The authentic panel contains 149 scored tickers. The live score panel contains 148 on the common dates because `VUG` failed to download. `PIN` also failed, but it was already unavailable in the authentic scored panel.

The official membership CSV and the live membership CSV have different hashes. The frozen path array and the regenerated live path array also have different hashes.

## Performance impact

| Metric | Frozen reference | August live | Difference |
|---|---:|---:|---:|
| Titanium V2 mean CAGR | 21.6541% | 18.7349% live base | -2.9192 pp |
| Opportunity Router mean CAGR | 22.7428% | 18.5998% live router | -4.1430 pp |
| Opportunity Router mean MaxDD | -34.9569% | -41.2872% | -6.3303 pp worse |

The live package's global single-universe CAGR is not comparable to the mean 500-basket CAGR and is not used as a parity claim.

## Signal interpretation

On the last common signal date, 29 May 2026, both panels rank BNO first. The rest of the leading order already differs: authentic `TIT_R` ranks BNO, USL, GSG, EZA, USO; the live panel ranks BNO, HACK, DBO, USL, EZA.

The 31 July 2026 live signal USL/DBO therefore belongs to the retrained producer. There is no authentic frozen `TIT_R` row for that date, so it cannot be labelled a frozen Titanium V2 signal.

## Required production gate

A future live producer may be promoted only if it does one of the following:

1. uses the authentic frozen scoring artifact for the covered historical period and passes the 56,500-decision parity gate; or
2. is explicitly promoted under a new version name after a fresh validation campaign.

Frozen paths, authentic score artifacts and frozen basket membership must never be overwritten by current-data replays.
