# Titanium V2 — fresh retraining with official baskets fixed

Experiment date: 18 August 2026  
Final evaluation date: 1 July 2026  
Verdict: **the fresh retraining is deterministic, but it does not reproduce authenticated Titanium V2**.

## What was held fixed

- the official 500 baskets and all 12,000 basket/ticker memberships;
- 24 ETFs per basket, 4 from each of the 6 static macro categories;
- common 113 signal dates from 31 January 2017 through 29 May 2026;
- the published Compact/TailMix/macro architecture and seeds;
- annual expanding walk-forward refits;
- the 12% concentration threshold and 75/25 fallback;
- final daily path date of 1 July 2026.

No baskets were resampled for this experiment.

## Fresh retraining reproducibility

The models were fitted again from source with three XGBRanker seeds and 360 trees per annual refit. The resulting 17,020-row score panel is exactly equal to the score panel already packaged in the August live version:

| Field | Maximum absolute difference |
|---|---:|
| Compact rank | 0.0 |
| Tail rank | 0.0 |
| Macro bonus | 0.0 |
| Final Titanium score | 0.0 |

This proves that the live retraining is deterministic. It does not prove equivalence with the authenticated frozen model state.

## Selection comparison on official baskets

| Test | Fresh retraining vs authenticated `TIT_R` |
|---|---:|
| Mean monthly score correlation | 0.8374 |
| Unrestricted top-1 | 27 / 113 = 23.89% |
| Basket top-1 | 24,545 / 56,500 = 43.44% |
| Basket ordered top-2 | 8,874 / 56,500 = 15.71% |
| Basket unordered top-2 | 13,856 / 56,500 = 24.52% |
| Concentration regime | 51,225 / 56,500 = 90.66% |

## Daily scorecard at the same final date

| Metric | Official frozen V2 | Fresh retraining, official baskets | Difference |
|---|---:|---:|---:|
| Mean CAGR | 21.6541% | 18.8389% | -2.8151 pp |
| Mean MaxDD | -33.9351% | -41.2835% | -7.3484 pp |
| Mean Sharpe | 0.8681 | 0.7489 | -0.1191 |

The previous live run with regenerated baskets produced 18.7349% mean base CAGR. Reusing official baskets raises that to 18.8389%, only about +0.1040 percentage points. Therefore basket resampling was a real methodological error, but it explains little of the mean performance gap; the retrained ranking/model state is the dominant source.

The fresh path uses the current OHLC snapshot while the reference uses canonical frozen path bytes. For that reason the exact daily performance gap contains a smaller data-snapshot component. The 56,500-decision comparison and the authenticated-label monthly replay isolate the score/retraining effect more directly.

## Authenticated-label attribution check

Using the same official baskets, the same `fwd_ret_21` labels and identical monthly cost logic for both score panels:

| Metric | Authenticated `TIT_R` | Fresh retraining |
|---|---:|---:|
| Mean CAGR | 19.7150% | 14.4035% |
| Mean MaxDD | -36.2273% | -44.1362% |
| Mean Sharpe | 0.8062 | 0.6134 |

This is an attribution diagnostic, not a substitute for the official daily governor scorecard.

## Conclusion

Simply retraining the published architecture does **not** recover the original Titanium V2 result. The fresh run exactly reproduces the August live-retrained model, but not the authenticated `TIT_R` model state. The parity-safe live producer must therefore continue to use the authenticated score panel through 1 July 2026, while any subsequent retrained producer remains a separately versioned successor.
