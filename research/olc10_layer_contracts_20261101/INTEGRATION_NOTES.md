# OLC10 integration decisions — 1 November 2026

The current task evaluates layer outputs, not an economic portfolio sweep. Existing Return, current Hybrid, smoothed Hybrid and fused output are diagnosed separately; no fitted calendar or mixture coefficient is changed.

During source parity checking, a draft composition adapter used the older NaN-propagating three-month smoothing. The authenticated CL01 source in OLC07 phase_state.py already renormalizes the .4/.3/.3 weights over finite past forecasts, while requiring a genuine current forecast. The draft disagreed on 46 European cells. This is an integration-test failure of the new draft, NOT a newly discovered error in the saved strategy. The failed check and regression test are preserved. The adapter was corrected to the actual parent contract. It then reproduces all14850 EU and13410 USA archived combined-score cells exactly, including NaNs. No tolerance change or forecast fallback was introduced.

Two distinct output channels are maintained: the native rank score consumed by the unchanged strategy, and an optional expected-target estimate. The latter estimates .45*rank21^1.5+.35*rank42^1.5+.20*rank63^1.5, NOT a probability of success. An affine calibration never substitutes its numeric scale into the existing ensemble or position-size formula. The STACK2 experiment can change ranking and remains a challenger, not an integrated default.

Complete support is required per monthly ranking evaluation to avoid choosing candidates by future-label availability. This removes additional incomplete outcome months compared with old row-wise MSE summaries; exact dates and counts are retained. Forecasts still exist and remain eligible when their future outcomes are missing. Return's native eligible population and the matched inter-layer population are labeled separately.

No base learner was refitted. The two small calibrators were fitted on six annual prior-OOF histories per market (24 calibration fits total), all using fully matured labels before the year. History has been studied repeatedly, so chronological fitting does not imply a pristine holdout.
