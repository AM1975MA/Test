# ETF Trader EU165 — self-financing specialist allocator V1 (2026-10-29)

**EXPLORATORY RESEARCH ONLY — original B0/V2/V3/USA149 production unchanged.**

**Question:** Can original native EU165 V2 Titanium / V3 Corrected Pair127 / V3 Tail Ridge45 Top3 opportunity specialists, combined with a 21/42/63-day incremental-return forecaster, risk veto, and endogenously persistent position-level HOLD/FULL/PARTIAL SWITCH, beat the source-native V3 Pair127 Top3 allocator?

**Answer from 2021–2024 (pre-2025) backtest: no.** Native V3 Pair127 Top3 equal weight CAGR **+8.174%**, MaxDD **−25.775%**, annual gross turnover **14.810×**; specialist HOLD/SWITCH without veto **+7.684% / −30.083% / 3.666×**; with independent loss-risk veto **+7.222% / −29.182% / 3.006×**; with partial switch (max 5 holdings) **+6.505% / −28.976% / 1.950×**; V3 with veto only **+6.181% / −25.284% / 11.369×**. Relative to V3, 6-month month-block bootstrap specialist HOLD/SWITCH annualized log return diff **−0.47pp**, 95% CI **[−10.77,+10.88]pp**; the new method **does not demonstrate positive alpha**. 500 baskets share underlying ETFs and are NOT 500 independent samples.

**Out-of-sample source-native model fits:** 18 annual mature-label fit pairs from 2021–26 (3 horizons × six years). Base model scores were independently source-trained 2018–26 in prior EU165 native archive. Same fixed 500 historical STABLE_HASH_MONTHLY 24-instrument baskets, four each from six original coarse macro-clusters; 165 ETF OHLCV histories; raw next-session Open is required for every buy/sale, 10 basis points per side, self-financing cash/share ledger and daily Close NAV for 1,429 master sessions. 65 monthly decisions Jan2021–May2026; three December (2021, 2024, 2025) have source scores for only five–seven ETFs → **no rebalance; hold positions**. Other missing MOM21/63 score entries are imputed using historical-only training median instead of dropping the full rebalance, which fixes the initial failed replay; core native V2/V3 scores and real Open still required. 2021–24 primary; 2025 heavily mined, reported only as illustrative stress.

**Read-only score and ensemble design:** 8 causal input features including V2/V3/MOM historical ranks; predict each ETF's 21,42,63-day return using Ridge + LightGBM and risk of an absolute -5% return using independent LightGBM classifiers. Expected candidate-minus-incumbent utility is the difference between their estimated ETF returns; no new portfolio-specific future labels are used at decision time. Shortlist = union of native V2/V3/Tail top3, at most nine candidates. No-trade threshold 0.20% full round trip + an exploratory risk/disagreement penalty. Loss veto thresholds P(loss5 over 21d)≤20%, P(loss5 over 42d)≤25%; these probabilities are NOT well calibrated: 2021–24 mean Brier model/baseline 21d .0886/.0909, 42d .1153/.1084, 63d .1381/.1268. Do not deploy. Risk/uncertainty tuning NOT independently validated.

**2021–24 detailed CAGR / MaxDD / turnover yearly:** 
- V3 Pair127 Top3 **8.174% / −25.775% / 14.810×**
- No-risk specialist **7.684% / −30.083% / 3.666×**
- Risk-veto specialist **7.222% / −29.182% / 3.006×**
- Partial risk-veto specialist **6.505% / −28.976% / 1.950×**
- MOM252 Top3 **4.930% / −26.328% / 8.455×**
- V2 Titanium Top3 **3.864% / −36.400% / 15.308×**
- Initial V3 Top3 buy-and-hold **9.737% / −22.833% / 0.538×**, but NOT comparable as a continually eligible dynamic basket strategy; positions can leave the new baskets and selection depends on Jan2021 starting set.

**2025 stress** original MOM252 Top3 32.87% CAGR, V3 Pair127 Top3 26.14%, no-risk HOLD/SWITCH 22.73%, risk-veto HOLD/SWITCH 20.75%. This is not new data.

**Fundamental data limitations:** 2026 survivor-defined universe; no properly point-in-time delisted ETF coverage; dividends and adjusted total returns **uncertified**; synthetic ffill for missing valuation Close (raw Open required for trades), no spreads, slippage or exchange-fee validation; all 2018–26 researched many times; macro-clusters not real industry taxonomy; means over 500 overlapping portfolios; yearly score re-training uses annual mature-label cutoff but hyperparameters already explored. The experimental V2/V3 ranker-only portfolios are NOT exact original V2/V3 full-risk-pipeline strategies. No deployment or production changes.

**Self-contained original research ZIP** `ETF_TRADER_EU165_SPECIALISTS_SELF_FINANCING_PILOT_20261029.zip`, SHA256 `ef15b8c734d79a580cca29d3a05814951929814d2e334131c917162ebb2006dd`, **39,932,527 bytes**, **188 entries**. Contains all 165 unmodified daily files, 500×24 historical PIT basket archive, original source-native European ETF forecasts and price labels, full replay Python code, all 254,793 logged trade entries, daily NAV, 18-fit maturity audit, raw OOS 21/42/63 forecasts, paired bootstrap, risk metrics and Italian detailed report. ZIP CRC tested clean.

**Next go/no-go:** do not promote old or new allocator. Need (1) data execution/total-return/PIT cleanup; (2) proper calibrated conditional pairwise forecast of candidate-minus-**endogenous incumbent** value; (3) out-of-time comparisons on unseen data; (4) rolling risk calibration to replace arbitrary fixed veto. A strong ranking hit-rate is not proof that frequent reallocation increases net utility.
