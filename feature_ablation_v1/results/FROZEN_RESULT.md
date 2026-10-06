# COMPACT21_ORTHOGONAL_FEATURE_ABLATION_V1 — frozen result

Source GitHub Actions run: `37524219056`  
Artifact: `11441796454`  
Artifact digest: `sha256:c6d6a40ec61feb101a23a35f18c18fb590fc95e1f77735a3e129ae6fd0725547`

The feature-only ablation completed successfully and its fail-closed contract passed. The job-level failure occurred only in the subsequent persistence step because `git pull --rebase` found unstaged checkout files; the result artifact itself was uploaded successfully.

- 125 frozen Compact21 inputs
- 46 semantic feature families
- 17,592 common mature pre-2017 discovery rows per repeat
- 16,986 common 2017-2026 outcome-free stability-audit rows per repeat
- no post-2017 targets or strategy economics used for feature selection
- no production XGB/HGB ranker fitted during feature selection
- strong-evidence subset under the preregistered joint FDR/Boruta/stability gate: **0 features**

## Frozen ladders

- K8: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct
- K12: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct
- K16: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct, autocorr1_63, efficiency21_dev, skew63_dev, mom10_dev
- K24: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct, autocorr1_63, efficiency21_dev, skew63_dev, mom10_dev, drawdown21, breakout_pos252_pct, vol126_dev, mom5_dev, mom42_dev, mom252_ex21_dev, mom21_dev, efficiency63_dev
- K32: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct, autocorr1_63, efficiency21_dev, skew63_dev, mom10_dev, drawdown21, breakout_pos252_pct, vol126_dev, mom5_dev, mom42_dev, mom252_ex21_dev, mom21_dev, efficiency63_dev, beta_mkt63_dev, mom126_ex21_dev, vol_ratio_21_126, corr_mkt63_dev, ma_gap200_pct, max_loss63_pct, vol21_dev, ema_gap20
- K40: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct, autocorr1_63, efficiency21_dev, skew63_dev, mom10_dev, drawdown21, breakout_pos252_pct, vol126_dev, mom5_dev, mom42_dev, mom252_ex21_dev, mom21_dev, efficiency63_dev, beta_mkt63_dev, mom126_ex21_dev, vol_ratio_21_126, corr_mkt63_dev, ma_gap200_pct, max_loss63_pct, vol21_dev, ema_gap20, sign_entropy63, vol63_dev, positive_frac63, ema_gap50, max_gain63_pct, cvar10_63, drawdown63_pct, rsi14
- FAMILY46: mom252_dev, gkvol21_pct, corr_mkt126_dev, acc_mom_21_63_dev, acc_mom_5_21_dev, mom63_dev, log_adv63_pct, volume_surprise21_pct, kurt63_dev, beta_mkt126_dev, efficiency126_dev, mom126_pct, autocorr1_63, efficiency21_dev, skew63_dev, mom10_dev, drawdown21, breakout_pos252_pct, vol126_dev, mom5_dev, mom42_dev, mom252_ex21_dev, mom21_dev, efficiency63_dev, beta_mkt63_dev, mom126_ex21_dev, vol_ratio_21_126, corr_mkt63_dev, ma_gap200_pct, max_loss63_pct, vol21_dev, ema_gap20, sign_entropy63, vol63_dev, positive_frac63, ema_gap50, max_gain63_pct, cvar10_63, drawdown63_pct, rsi14, ma_gap50_pct, breakout_pos126_pct, drawdown126_pct, downvol126_dev, downvol63_pct, downvol21_pct

## Interpretation

The absence of a feature passing the strict joint strong-evidence gate means the ablation has not demonstrated a single individually decisive predictor. The frozen ladders are nevertheless valid candidates for the next mechanistic test because they combine nonlinear relevance, cross-snapshot stability and redundancy control. The next stage must compare them with BASE125 using the unchanged canonical ranker and predictive/stability endpoints before any strategy-economics evaluation.
