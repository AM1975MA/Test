# STEP08I amendment — frozen before development replay

Date: 2026-08-31

No STEP08I 2021-2022 economic replay result had been computed or observed when this amendment was written.

## Reason
The frozen STEP08F event-time TIT_R producer can be regenerated exactly for 2021-2022 from already persisted scores, but generating the same producer feature on all ~500 2019-2020 STEP08I training dates requires a full historical OHLCV feature-snapshot rebuild that exceeds the practical runtime of this execution environment. Substituting a stale monthly TIT_R in training and a fresh event-time TIT_R in validation would create a train/deployment domain mismatch; using an approximate producer would falsely claim historical identity.

## Frozen amendment
Remove `event_tit_r` and `event_tit_r_rank_set` from the STEP08I selector feature vector for both training and validation. All other protocol elements remain unchanged:
- exact STEP08H top-5 causal resilience filter;
- STAY / BIL / filtered ETF action set;
- 2019-2020 training only;
- HGB hyperparameters unchanged from STEP08G;
- target = candidate utility - exact FUSION1 STAY utility;
- zero decision threshold;
- exact q95 validation schedule and gate unchanged.

This amendment makes STEP08I a clean test of whether the **small causal resilient set itself is learnable**. The saved STEP08F event-time Titanium alpha challenger remains separate and may be combined with a successful protective selector only in a new preregistered experiment.
