# Daily-training + causal R1/R2 Original149 ETF experiment — pilot results (2026-10-20)

Branch research/original149-r1r2-daily-20261020. Production etf_trader_v2 untouched. Original Original149 149 ETF roster and SHA untouched. One signal per 5 sessions, weekly next-open to next-open+5 target; 100 paired OOS decision dates 2024–2025; equal weight 5 ETF holdings, full conservative 20bp roundtrip weekly. Full 476-date 2017–26 runs were preregistered and launched BEFORE review of pilot and are separate primary test.

## Diagnostic 2024–2025 results, 100 paired dates

| Model | Feature count | Net CAGR | MaxDD | Sharpe | Mean cross-sectional RankIC | Top5 raw oracle overlap |
|---|---:|---:|---:|---:|---:|---:|
| Frozen A old weekly-trained TCN | 125 | +10.0677% | −27.5291% | 0.5561 | +0.05879 | 5.2% |
| Frozen original mom21 (no fitting) | N/A | +10.4242% | −24.8602% | 0.5026 | −0.03721 | 15.2% |
| B_DAILY_BASE original TCN + daily training | 125 | +8.4921% | −29.7883% | 0.4950 | +0.05362 | 5.4% |
| C_DAILY_R1 TCN +14 residual and group momentum | 139 | +12.7978% | −30.9536% | 0.6777 | +0.05772 | 7.8% |
| D_DAILY_R1R2 TCN +14 R1+20 R2 | 159 | +15.6807% | −32.9588% | 0.7914 | +0.05857 | 7.6% |
| E_XGB_BASE XGBRanker pairwise | 125 | +18.5608% | −26.6410% | 0.8642 | **+0.06607** | 7.6% |
| E_XGB_R1R2 XGBRanker pairwise | 159 | **+26.1072%** | −26.7537% | **1.1101** | +0.05916 | 8.2% |
| E_CAT_R1R2 CatBoost QueryRMSE | 159 | +18.7116% | −25.3038% | 0.8858 | +0.04959 | 4.0% |

These are DIAGNOSTIC pilot figures and should not be treated as an independent out-of-sample test: previous Listwise Top5 and torchsort Top5 variants posted similarly impressive pilot returns before failing the full 2017–26 run. Preliminary direction: daily training alone worsens Pointwise; relational features R1 and R2 incrementally boost the neural model's pilot nominal selection return and net CAGR, but worsen drawdown. XGB original 125 features yields the highest pilot full-universe RankIC, but extra R1+R2 features substantially boost XGB pilot economic result while slightly lowering mean RankIC. Confirm only against full period before any promotion.

## Reproducibility and fixed settings

R1: 14 features = four 5/21/63/126 day momentum residual families against SPY market, historical beta63-adjusted SPY and leave-self-out same-group peer medians; own same-group percentile at 21/63.
R2: 20 features = rolling peer and universe leave-self-out correlation 21/63; 21 minus 63 correlation shifts; peer and universe positive-return breadth 1/5/21; broad and same-category momentum dispersion 5/21; dispersion shocks normalized by prior trailing median; SPY momentum and vol regime.
All features causal and exact prefix invariant under synthetic truncation; original 125 feature QA and ETF eligibility mask retained. Daily training predictions use matured t+6 next-open labels; previous-year weekly validation for early stop and hyperparameters, unchanged 5-session rebalance. CatBoost QueryRMSE objective; XGBoost objective rank:pairwise with validation RMSE because its default NDCG metric rejects the original continuous percentile target in XGBoost 3.1.3; no target or loss changes during bug fix.

Initial pilot run 39477779302 failed on pandas broadcast; corrected feature mask, QA passed 39478363028. Next 6way pilot attempt 39478626210 yielded valid TCN and CatBoost results; XGB component failed solely because default relevance evaluation demanded nonnegative integer labels, repaired without altering model loss or target; XGB pilot completed 39479747137. All failed diagnostic runs retained as history, excluded from experimental findings.

## Links

- Verified synthetic causal/Compact source QA https://github.com/AM1975MA/Test/actions/runs/39478363028
- Pilot TCN B/C/D and CatBoost E, full checkpoint/score evidence https://github.com/AM1975MA/Test/actions/runs/39478626210
- Corrected XGBoost pilot archives https://github.com/AM1975MA/Test/actions/runs/39479747137
- Independent matched 100-date analysis workflow https://github.com/AM1975MA/Test/actions/workflows/tensor149-daily-r1r2-compare-pilot.yml
- Full primary annual 2017–2026 run https://github.com/AM1975MA/Test/actions/runs/39478752782
- Corrected XGBoost full workflow https://github.com/AM1975MA/Test/actions/runs/39479754815
- Frozen baseline A https://github.com/AM1975MA/Test/actions/runs/39455195643

Interpretation strictly subject to mined retrospective roster and Yahoo adjusted prices.
