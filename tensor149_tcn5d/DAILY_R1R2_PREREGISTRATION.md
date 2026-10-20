# Preregistration: daily training + R1 relative strength + R2 cross-ETF structure (2026-10-20)

Original149 frozen dataset and six static macro categories. Branch research/original149-r1r2-daily-20261020. No production changes.

**Constant across runs**: Original149 frozen 149 ticker manifest, existing 125 exact Compact21 daily features, unchanged original ETF eligibility, future 5-session open(t+1) to open(t+6) percentile [-1,1] label, annual expanding walk-forward with train label exits strictly before year-1 Jan 1 and validation label exits strictly before test-year Jan 1; same 476 test weekly dates 2017–2026 and last exit 2026-07-01. All strategies top5 long only, full rebalance, 20bp roundtrip, daily NAV path, no cash.

Baseline A: original untouched weekly-date-trained TCN, Ridge125 and MOM21 archived run 39455244701. Do not re-fit A after observing pilots.

B_DAILY_BASE: Same 125 features and exact same TCN as frozen A (30-day input, 24 channels, dropout .35, AdamW .001 wd .003, 5 epochs maximum, early-stop patience2 previous-year validation), same tail-weighted SmoothL1(beta .2), BUT train every daily signal (1-day stride). Previous-year validation remains original weekly anchors. Predict and trade on the original weekly 476 dates. Daily labels overlap 5-session horizons and are NOT independent.
C_DAILY_R1: B + 14 causal R1 features: at horizons 5/21/63/126, excess momentum vs SPY, rolling beta63 adjusted vs SPY and own minus other-peer sector group median, plus own within-category momentum percentile at 21 and 63 (group excludes own from peer median).
D_DAILY_R1R2: C + 20 causal R2 features: rolling (21/63) correlations to leave-self-out universe and group benchmarks, 21 minus 63 correlation changes, leave-self-out category breadth and broad-market breadth 1/5/21, group/universe dispersion 5/21, dispersion shock vs 63-day prior median, and as-of SPY 21-day momentum/volatility regime.
E_XGB_BASE: XGBRanker rank:pairwise, original 125 daily snapshot features, 240 trees, depth4, learning rate .035, subsample .85, colsample .8, min child weight8, L2 8, L1 .1, grouped by signal date, daily train weekly previous-year validation.
E_XGB_R1R2: Same XGBRanker, 159 features.
E_CAT_R1R2: CatBoostRanker QueryRMSE, 240 trees depth5 learning .035 L2 8, group_id signal date; same 159 features daily train and weekly previous-year validation.
Keep tree scores vs TCN scores on identical weekly investable universe. Tree models are point-in-time single date input, whereas TCN has last 30 temporal feature bars: interpret as model and representation comparison rather than identical temporal architecture.
All model parameters set BEFORE pilot and full execution. Both 2024–25 diagnostic pilot (100 weeks) and full 2017–26 (476 weeks) run fixed configurations and same cost model.

**Hard QA gates**: all new features strictly prefix-invariant under truncation of future prices, labels maturity, six static groups, strict roster manifest, no future prices in normalization. New TCN scaler uses only features dated before prior validation cutoff; tree models handle NaNs without future fitting. Same eligibility as frozen A. Test R1 dimension14, R2 dimension20, total 159. Retain yearly models, weekly predictions, per-ticker scored OOS, daily net NAV and per-year validation evidence.

**Report metrics**: mean per-date cross-sectional Spearman RankIC, bootstrap paired improvement vs A and MOM21, Top5 raw-return oracle overlap, mean nominal 5-session basket return, net CAGR, MaxDD, Sharpe, yearly stability and factor/volatility bias. 5-week circular moving-block bootstrap is descriptive; historic 2017–26 data mined many times. A real independent future or disjoint ETF sample remains required.

**Cautions**: 149 ETF roster is retrospectively surviving selection with taxonomy fixed in present, no new source or macro publications, adjusted Yahoo OHLCV not necessarily executable, daily overlapping target labels inflate raw sample counts, in-sample parameter search prohibited, daily training 5x data rows does not equal 5x independent data.
