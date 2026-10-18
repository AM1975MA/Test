# H7 — orthogonal risk overlay on frozen H5 hysteresis

Frozen 2026-10-18 **after** seeing the first 7 EUR60 arms and score-jitter results, **before** calculating this interaction. This is an explicitly *post-selection exploratory* experiment, not independent validation.

## Rationale
- H5 Top5 hysteresis: 14.0888% historical CAGR / -27.9257% monthly MaxDD; H0 R_H 9.9780% / -26.6441% (frozen run 39089621741).
- H3 50% conditional cash overlay on H0: 9.4147% / -20.7335%; improves drawdown but reduces CAGR. Kalman inverse-uncertainty standalone sizing 9.2527%; entropy flag only 5.8653%; both rejected for this purpose.
- Test if **two economically distinct components** — stable ranking membership + broad-market defensive exposure — combine without losing the selection improvement.
- This step was *inspired by already-seen outcomes*. It is a necessary interaction diagnostic but must be treated as multiple testing and *not as further proof of significance*.

## Arms (no tuning)
1. H0 reference unchanged: R_H Top2 50/50.
2. H5 reference unchanged: lagged Top5 hysteresis Top2 50/50.
3. H3 market filter on H0 unchanged: if prior observed synthetic equally weighted market < its 200-day MA AND 21-day vol > 126-day vol, equity weights scale to 50%; else 100%.
4. **H7 H5 plus the exact H3 market gate**: same H5 picks, exposure 50% when flagged, otherwise 100%; residual earns precisely zero cash.
5. **H8 H5_STATIC_90**: same H5 picks, always 90% equity, 10% non-remunerated cash. This separates a naive permanent defense from a market-timed gate.

Use exact original next-open/open calendar and all frozen portfolio decisions from run 39089621741, not a new fitted return learner. Recompute costs from time-varying weights with the **same half-L1 risky allocation and subsequent cash transfer** formula used in the parent run. Verify H0, H5 and H3 economics against the independently completed parent run to <=1e-12.

Report time-sliced CAGR 2017–2020 / 2021–2023 / 2024–2026, monthly ES5, DD, annual turnover, average exposure, 12-month block-bootstrap paired mean-log return vs both H5 and H0. No grid search in gate thresholds or cash percentage.

A meaningful research signal would be a risk reduction versus H5 without a proportionately large return sacrifice, plus nontrivial improvement versus H8's static defense and stability across time slices. Regardless of results, the old EUR60 survivor cohort prevents prospective promotion.

Do not deploy, merge, or revise production. If H7 fails, reject the gate; do not try new thresholds on the same burned panel to force a positive result.
