# STEP09A3 — Reserve-Balance Funding Topology Audit
Date: 2026-09-01

## Scientific question
Does a genuinely orthogonal funding/liquidity variable improve the frozen STEP09A2 robust three-state separation (STAY / ROTATE / BIL) without changing the target, geometry features, model, or validation design?

## Frozen base
- Reuse `ROBUST_ESCAPE_EVENT_PANEL_2018_2022.csv` from STEP09A2 unchanged.
- Robust target unchanged: ROTATE iff escape_fraction >= 0.25; else BIL iff BIL full-episode utility > STAY; else STAY.
- Geometry feature set unchanged from STEP09A/09A2.
- Model unchanged: median imputation -> StandardScaler -> multinomial LogisticRegression(C=0.1, max_iter=3000).
- Date weights unchanged; 2018-2020 train with LOO-year robustness; 2021-2022 forward development.
- 2023+ sealed.

## New orthogonal information: Federal Reserve reserve balances
Series: FRED `WRESBAL` (Reserve Balances with Federal Reserve Banks), archived at immutable public GitHub commit `Garrincha077/NUEVO@199250186dc6621e92673f17e7f7aef34039a1de`, raw archive SHA-256 `b10e207ffbe19ae510fb4e8a7606710f8f417fe619ca7151752dc628f348d523` per source manifest.

To be conservative about H.4.1 publication timing, each event at date t may use only a WRESBAL observation dated <= t-7 calendar days.

Frozen funding features (no alternatives searched):
1. `wresbal_log_level` = log(WRESBAL).
2. `wresbal_chg4w` = 4-observation log change.
3. `wresbal_chg13w` = 13-observation log change.
4. `wresbal_accel4v13` = chg4w - (4/13)*chg13w.
5. `wresbal_pct52` = causal percentile of the current level within the previous 52 available weekly observations, including current lagged observation.

No feature selection and no threshold search.

## Mandatory parity check
Before judging funding, refit GEOMETRY-only from the frozen STEP09A2 panel and reproduce the published STEP09A2 forward scorecard within numerical tolerance. If parity fails, STOP.

## Primary comparison
`GEOMETRY_PLUS_WRESBAL` versus frozen `GEOMETRY` using the same logistic model.

The augmented model qualifies STEP09B only if it satisfies every original STEP09A2 information gate:
- forward 2021-2022 balanced accuracy >= 0.45;
- forward macro OVR AUC >= 0.60;
- ROTATE AUC >= 0.60;
- BIL AUC >= 0.60 when present;
- 2021 balanced accuracy >= 0.40;
- median valid pre-2021 LOO macro AUC >= 0.58;
- no predicted class >95% of forward date weight;
and additionally
- forward macro AUC is not below the frozen geometry-only macro AUC by more than 0.01.

No gate relaxation and no post-result tuning. If it fails, do not try alternative WRESBAL windows; move to genuinely orthogonal positioning/flow information.
