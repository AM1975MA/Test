# Canonical binary artifacts

The complete verified recovery archive is retained at:

- ChatGPT Library: `/Meteor/METEOR_TITANIUM_V2_RECOVERED_OFFICIAL_20260817.zip`
- Size: 54,863,017 bytes
- SHA-256: `c42591a16e5538af204081be5832caa54fc44b0a15607a72ae9055708d62fe7f`

The inspected August live package is retained at:

- ChatGPT Library: `/Meteor/METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE(1).zip`
- Size: 89,912,144 bytes
- SHA-256: `ffa94ba5518e556aaff16eface66687a5a64b417a01972412ea2e6a86553b128`

The corrected parity-safe live/as-of package is retained at:

- ChatGPT Library: `/METEOR_TITANIUM_V2_LIVE_PARITY_FIXED_20260818.zip`
- Size: 54,562,479 bytes
- SHA-256: `fd575a0f06f68b59273fc426083c592bdaa2e52df04273e1101b4143b15ef06f`
- Validation: 500/500 baskets with 24 = 6×4 structure; 56,500/56,500 selections; official V2 metric gate PASS.

## Frozen sources of truth

| Artifact | SHA-256 | Role |
|---|---|---|
| `ORTHOGONAL_SCORE_PANEL.pkl` | `57caef7e4b824d0a7c75cea389d7e957b2da23bb0925a15b696ca0bfdaa2af88` | Authentic `TIT_R` score panel |
| `SUPER_GOLD_BASKET_MEMBERSHIP.csv` | `36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e` | Official 500-basket membership |
| `REG_W24_F005_S008_PATHS.npz` | `831b426d3a59b7132686555f4591212ddad999e79a1c5c7a118f1bfdd72d166b` | Official selection matrix |
| `TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz` | `7bf8441c66d0256dd3e5897df8f0a2271b00faf0c1d6d5ed9bc2440d614adc54` | Frozen V1/V2 500-basket paths |

The binary files are intentionally referenced by immutable hashes. GitHub text sources and reports must not be interpreted as replacements for these canonical bytes.
