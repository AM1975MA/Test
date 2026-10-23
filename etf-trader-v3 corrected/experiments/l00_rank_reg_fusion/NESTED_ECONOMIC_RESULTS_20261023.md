# ETF Trader V3 Corrected — Causal nested meta-tree, real next-open economic consequence (2026-10-23)

## Reproducibility and independent execution verification

**PASS**: [GitHub Actions 40032693599](https://github.com/AM1975MA/Test/actions/runs/40032693599), source-only next-open self-financing engine and [complete result/decision-log artifact 12535287571](https://github.com/AM1975MA/Test/actions/runs/40032693599/artifacts/12535287571).

Separate chronological model-selection validation **PASS**, [Actions 40032282233](https://github.com/AM1975MA/Test/actions/runs/40032282233), [frozen output 12535227212](https://github.com/AM1975MA/Test/actions/runs/40032282233/artifacts/12535227212).

The economic layer reconstructs **every original and meta-corrected ETF selection in every one of 500 canonical baskets across 101 month-end signals**. It refuses economic evaluation unless its 101 monthly Top1, Top3, nDCG3, regret, selected excess, <=-10% downside share, changed/better/worse decisions exactly equal the already-validated nested selector's output within 1e-11. **All gates passed**. Baseline TOP2 uses original production-matched V2-style source-only allocation engine as cross-check. All variants apply **10bps traded notional one-way**; signals enter at **next open**, self-financing. 149 ETF, 500 overlapping fixed 24-member baskets, 2018-Jan–2026-May signals, 2026-Jun-30 last investment-session evaluation. This is the **CORRECTED125 first-stage ranker**, not the uncorrected V2 baseline. Original source, production strategy and risk layers remain unchanged.

The economic test only changes the within-original-Top3 ordering based on *NESTED_24_TOP1_GUARD*, which chooses one of 36 causal decision-tree hyperparameter configurations each month using only 24 already-matured historical OOS months (minimum 60 calendar day delay) and selects only configurations historically non-degrading on Top1. There is **no CAGR or drawdown-driven model tuning**. TOP1: 100% selected Top1; TOP2: fixed 75%/25% except baseline ranker score Top1-minus-Top2 gap >= .12, in which case 100%/0%; TOP3: frozen weights 50/30/20. No Tail, macro, risk or execution policy changes.

## Net economic results: 2018-02-01 through 2026-06-30

| Fixed policy | Base corrected ranker CAGR | Causal meta-tree CAGR | CAGR difference | Base agg MaxDD | Meta agg MaxDD | mean basket CAGR (base → meta) |
|---|---:|---:|---:|---:|---:|---:|
| TOP1 (100%) | 14.9210% | **16.6587%** | **+1.7377 pp** | -39.7936% | -39.7936% | 11.0661% → 12.8859% |
| TOP2 (75/25 or 100/0 gap) | 14.8170% | **15.6779%** | **+0.8609 pp** | -39.0766% | -39.0766% | 12.1445% → 13.1082% |
| TOP3 (50/30/20) | 13.9710% | **14.2902%** | **+0.3192 pp** | -38.4188% | -38.4188% | 12.4211% → 12.7918% |

Here `aggregate_cagr` means CAGR on the **arithmetic mean of 500 separately compounded basket equity curves**, not equal to mean individual basket CAGR. A single tradable portfolio holding ETF exposures across all overlapping baskets would require a different implementable accounting convention.

## Net matched 2022-02-01 through 2026-06-30

| Fixed policy | Base corrected ranker aggregate CAGR | Nested tree aggregate CAGR | Difference | Base MaxDD | Meta MaxDD | mean basket Sharpe (base → meta) |
|---|---:|---:|---:|---:|---:|---:|
| TOP1 | 21.2145% | **24.6202%** | **+3.4057 pp** | -18.6537% | -18.6087% | .5843 → .6567 |
| TOP2 | 19.8196% | **21.4501%** | **+1.6305 pp** | -19.1692% | -19.1599% | .6338 → .6816 |
| TOP3 | 17.9585% | **18.5401%** | **+0.5816 pp** | -19.4571% | -19.4512% | .6840 → .7066 |

Same **53 rebalance signals, 1105 exchange trading days**, costs included. Some years show negative annual contribution: in 2023, TOP1 original basket-aggregate year return ~8.2% vs meta ~6.8%. 2022 and 2025 support most of the matched improvement.

## Temporal robustness: discard entire 2026 segment (NAV ending 2025-12-31)

From exported daily NAV curves (same start date within each window):
- Full historical since Feb2018: base → meta CAGR TOP1 **14.309% → 15.617%** (+1.307pp), TOP2 13.9996% → 14.6734% (+.674pp), TOP3 13.1129% → 13.3707% (+.258pp).
- Matched since Feb2022: TOP1 **21.006% → 23.6688%** (+2.663pp), TOP2 18.8814% → 20.2250% (+1.344pp), TOP3 16.7228% → 17.2088% (+.486pp).
- The NAV benefits do not depend *only* on 2026, but those dates had already been examined in earlier ETF studies, so this still cannot establish independent predictive alpha.

## Statistical caveats — IMPORTANT

Paired 21-trading-day time-block bootstrap 2,000 samples on daily differences of basket-ensemble log NAV returns, 2,112 original calendar trading sessions (full window) or 1,105 (matched). Annualized **log alpha**, not arithmetic CAGR difference:

| Fixed policy | Full annual log alpha, 95% bootstrap CI | Matched from Feb2022 annual log alpha, 95% bootstrap CI |
|---|---|---|
| TOP1 | +1.6912%, **[-0.0608%, +3.6885%]** | +2.7471%, **[-0.4210%, +6.3769%]** |
| TOP2 | +0.8908%, **[-0.0715%, +1.9883%]** | +1.4917%, **[-0.1873%, +3.4418%]** |
| TOP3 | +0.3399%, **[-0.0230%, +0.7513%]** | +0.5663%, **[-0.0602%, +1.2981%]** |

**Every economic log-alpha interval includes zero.** These CIs furthermore do not adjust for the multiple tree and chronological selector configurations investigated on reused history. Thus we have validated **historical economic improvement**, NOT a confident future alpha or a production-ready replacement. The aggregate maximum drawdown also barely changes; historical Top1 mean individual basket MaxDD is very high (full-window -54.9%, improved from -56.5%). The effects are concentrated in the concentration-first allocation and dilute progressively for Top3.

## Decision

Preserve the causal NESTED_24_TOP1_GUARD as a **research candidate only**. No production merge, no main strategy change. For actual adoption, preregister or stabilize the meta selection rule, lock source/basket universe, and confirm on a truly new chronological period and alternative market regimes. Evaluate 149 ETF source eligibility, score composition, exposure limits, liquidity/slippage and risk/stop layers independently. Do not attempt to optimize Top1/Top2 sizing here by retrospective CAGR. Consider more stringent model-calibration and non-overlapping multi-asset universe cross-checks in a follow-on controlled experiment.

## Source and audit
- `nested_tree_selector.py`: frozen causal configuration selector; controls the actual chosen model each evaluation month.
- `nested_economic.py`: reconstruct every chosen ETF; match exact 101 × 500 monthly decision metrics; run original next-open execution at fees.
- `.github/workflows/v3-meta-nested-tree-validation.yml`, `.github/workflows/v3-nested-tree-economic.yml`: successful source-controllable jobs.
- Archive columns: `ACTUAL_DECISION_LOG.csv`, `DECISION_VALIDATION.csv`, `ECONOMIC_SCORECARD.csv`, `DAILY_ENSEMBLE_NAV.csv`, `YEARLY_ENSEMBLE.csv`, `PAIRED_21DAY_BLOCK.csv`, `ECONOMIC_MANIFEST.json`.
