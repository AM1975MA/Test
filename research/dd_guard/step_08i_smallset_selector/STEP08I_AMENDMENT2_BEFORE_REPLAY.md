# STEP08I amendment 2 — training-state coverage

Date: 2026-08-31

No STEP08I 2021-2022 economic replay result had been computed or observed when this amendment was written.

The frozen `STATE_PANEL.csv` begins on 2020-01-31. STEP08I requires the last strictly-prior leader/satellite state to build the exact STEP08H resilience filter, so 2019 episode rows cannot be used without inventing historical holdings.

Therefore the effective training sample is frozen to all usable states from 2020-02-03 through 2020-12-15 that satisfy the original maturity rule. This yields 2,210 basket-state events and more than 12,000 candidate-action examples. No synthetic 2019 origin state is reconstructed.

All model parameters, features after Amendment 1, target, zero threshold, validation schedule, gate, and 2023+ seal remain unchanged.
