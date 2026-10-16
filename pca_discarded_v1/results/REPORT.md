# PCA discarded-subspace audit

Actions run 38969790214: SUCCESS. Three frozen downloads, 30 annual model decompositions, 113 mature evaluation dates. No new learner fit; no portfolio replay.

| Score | Top1 realized percentile | Top1 top-decile hit rate | Rank IC |
|---|---:|---:|---:|
| FULL_FROZEN | 51.54% | 32.15% | 0.00309 |
| RETAINED_FROZEN | 50.33% | 28.61% | -0.00504 |
| DISCARDED_FROZEN | 48.18% | 17.11% | 0.02763 |
| PCA95_REFIT | 50.04% | 25.66% | -0.01555 |

Discarded directions carry 87.08% of squared coefficient norm, but this is not information or profit share. Retained directions preserve 95.41% of within-date input variance. Discarded-only frozen scores improve overall Rank IC while worsening Top1 ranking metrics. All 18 reported exploratory 95% block-bootstrap intervals include zero. No statistically established winner.

The discarded coefficients were originally learned jointly with retained coefficients. A discarded-only refit has not been tested. No new CAGR is available from this decomposition.

Decision: retain the full LINEAR research reference; do not promote PCA95 or discarded-only scores on this evidence.

Source: https://github.com/AM1975MA/Test/actions/runs/38969790214
