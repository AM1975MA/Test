# STEP08L causality amendment — before replay

Before any 2021–2022 economic result is inspected, weekly financial-condition series are conservatively delayed by 7 calendar days:
- NFCI
- STLFSI4

This prevents using a weekly observation as if it were known at the observation timestamp. Daily market-close series (VIX, VIX9D, VIX3M, VVIX, SKEW, ETF breadth and HYG/LQD) are allowed through the decision-date close because the frozen action starts two engine sessions later.

All input series are hard-truncated at 2022-12-31 before feature construction. No 2023+ row is read into model features or fitting.
