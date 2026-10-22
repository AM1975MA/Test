# L11.S3 — original V2 monthly downtrend veto with next-ranked same-basket fallback

**22 October 2026: completed exact replay on ONLY five preregistered baskets; negative; NOT promoted.** The user approved testing an original-V2 next-ranked eligible ETF instead of simply holding idle BIL/SHV after excluding selected names in persistent decline. [Pre-outcome frozen protocol on research branch](https://github.com/AM1975MA/Test/blob/research-v3-l11s3-causal-rank-fallback-20261022/etf-trader-v3%20corrected/reports/FULLSTACK/20261022_L11S3_FROZEN_RANK_FALLBACK_PREREG.md). This report, original Python source and CSV/NAV files were generated from local exact-source experiment and are available as exported study ZIP; numerical original references remain in GitHub FS02, FS03.

## Source lineage and hard controls

- Original 149 OHLCV RAW artifact Actions **39482809691**, FS02 fully source-rebuilt historical V2 Titanium+S3B+MA3 Hybrid24 original scores/predictions and original canonical 500×24 membership Actions **39836842157** artifact 12451018561; FS03 original Stage19 daily NAV Actions **39838818618**. Original basket membership SHA256 **36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e**.
- Original producer rank score reconstructed exactly: 0.475×Titanium BASE +0.525×[(0.40 current +0.30 lag-1 +0.30 lag-2) of original 60% ExtraTrees+40% XGBoost Hybrid24 Tail]**1.10; unchanged predictions and no new XGBoost fitting. Pre-economic **every single one of 500×114 = 57,000 original monthly Top-2 pairs reconstructed with perfect equality** to the original V2 PATH ticker IDs. No original 500 basket NEW-policy economic trial.
- Original Stage19 V2 DD-first, HighCAGR24 gross/weight, original ET&XGB risk-off consensus, V6 3-day cooldown/conditional 5.5% intraday stop, V6 alternative and 10bps traded-notional cost kept; original Stage19 5-basket daily NAV EXACT reproduction max absolute difference **6.0396e−14** over 2,366 trading sessions 2017-Feb to 2026-July.
- Five original representative basket IDs from V2 10/30/50/70/90 percentiles, **227, 69, 327, 301, 220**; calendar 2017-02-01..2026-07-01, no virgin OOS.

## Frozen proposed action

At every ORIGINAL month-end selection, an ETF selected Top-2 becomes ineligible only when all three prior-close causal conditions hold: >=5 negative days of 7, prior 10-day log return <=−0.8×√10×(1.4826×median absolute daily log returns in previous 21), and last completed close < completed SMA10. If vetoed, look down the **unchanged V2 rank** in the SAME original 24 names and choose highest ranked healthy alternative only if score >= weaker ORIGINAL Top2 original score−0.13 (same original V2 weight/margin saturation scale; no sweep). Recompute original continuous two-name weight and original riskoff ET/XGB Stage19 concentration for new pair. If unable to fill both accepted slots, keep remaining original target capital portion in original BIL/SHV safe parking. Do not allocate all risk to the surviving ETF; no leverage or global/macro exposure increase. New trading decisions only on next market OPEN after signal, not using that session's close.

Controls: original V2 no-veto, veto→safe BIL/SHV, veto→rank3+ healthy candidate within .13 then safe for remaining unfilled. Prior L11.S1/S2 sigma stop **NOT** bundled, since it failed separately; no hindsight optimization.

## Fee-aware results (arithmetic mean of the FIVE individual panieri)

| Strategy | Mean CAGR | Mean maxDD | Mean annualized traded notional | Change CAGR vs V2 | Change maxDD vs V2 |
|---|---:|---:|---:|---:|---:|
| Original ETF_TRAINER_V2 Stage19 | **22.4470%** | −33.7606% | 11.501× | baseline | baseline |
| Downtrend veto, otherwise safe BIL/SHV | 19.0878% | **−32.7051%** | 10.837× | −3.3592pp | +1.0555pp |
| Downtrend veto, original same-basket next-ranked V2 fallback | 19.7579% | −34.0208% | 11.211× | −2.6891pp | **−0.2601pp** |

## Per-basket original V2 vs same-basket rank fallback

| Basket | Original CAGR | Fallback CAGR | Delta CAGR | Original MaxDD | Fallback MaxDD | Improvement in maxDD |
|---|---:|---:|---:|---:|---:|---:|
| 227 (V2 p10) | 10.8966% | **15.9829%** | **+5.0863pp** | −29.5874% | −22.4992% | **+7.0882pp** |
| 69 (p30) | **17.5997%** | 14.6102% | −2.9895pp | **−49.9061%** | −51.4907% | −1.5846pp |
| 327 (p50) | **22.2882%** | 13.5697% | **−8.7186pp** | **−29.9407%** | −37.8954% | **−7.9546pp** |
| 301 (p70) | **27.5251%** | 20.9579% | −6.5672pp | **−27.9121%** | −30.3959% | −2.4838pp |
| 220 (p90) | **33.9252%** | 33.6687% | −0.2564pp | −31.4569% | **−27.8228%** | **+3.6341pp** |

Original V2 full 500 reference generated 57,000 correct rank decisions. Within five portfolios, over 114 months each the filter intervened on **140 distinct basket-months** (some involved both Top1 and Top2). FALLBACK found **154 replacement slots** and failed to find two sufficiently good candidates on **16 monthly position slots**; safe-veto had **170 parked slots** (these are correlated basket-month counts, not independent trades). The strongest beneficiary was basket 227, but basket 327 catastrophically lost ~8.72pp CAGR and ~7.95pp more worst DD; other baskets had inferior results.

Examples: basket 327 June 2024 original MCHI/CPER both vetoed, replaced by TAN/ARGT; July 2024 original EDV/TAN changed to EDV/CPER. Basket 69 Feb 2021 original KRE/ITA vetoed, replaced by KWEB/IBB; a downtrend exclusion does not imply the replacement shares low economic-factor or commodity downside exposure. No lookahead future outcomes were used to choose the rank3 candidate.

## Reproducibility, execution caveats and decision

The source was a standalone local research experiment `l11_s3_fallback_eval.py` with 149 OHLCV raw, source-only frozen V2 predictions, exact original V2 replayer; complete script, CSV intervention audits, original+candidate daily NAV arrays, manifest and charts are packaged in `ETF_V3_L11S3_fallback_5_panieri.zip` in the ChatGPT artifacts. The control reproduces Stage19 NAV to 6.04e−14. New risky names reapply source Top2 dynamic score weight and stage19 original model-consensus rules. Original V6 alternate ticker state is unchanged *except disabling a collision* with a newly selected risk name. An eventual full 500 integration would also have to regenerate the original V6 alternative state for changed holdings and verify turnover/stop fill parity; these new 5-policy results are not a production certification.

Crucially, **the criterion for extending to 500 was NOT MET**: required >=4/5 DD better, >=3pp mean DD improvement, <=0.5pp mean CAGR loss, no one basket DD deterioration >3pp. Actual only 2 of 5 DD improved, mean DD worsened 0.26pp and CAGR lost 2.69pp, basket 327 DD worsened 7.95pp. **Do not test/favor/tune this same hypothesis across 500 on already examined dates. Original full V2 and frozen V3 unchanged.** A more promising independent hypothesis must explicitly model conditional risk-adjusted advantage of the alternative, beyond a binary negative-momentum veto, and must use historically matured labels only, tight causality and a truly new validation period to avoid accumulating another backtest-optimized gate.