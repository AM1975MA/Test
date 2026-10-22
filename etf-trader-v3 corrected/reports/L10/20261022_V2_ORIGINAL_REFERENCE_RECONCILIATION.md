# STOP COMPARATOR CONFUSION — Original ETF Trader V2 full stack vs V3 corrected layer-only tests

**Evidence audit 22 October 2026; not a new backtest and no parameter promotion.** The 15–16% displayed by L10.E3/E4 and 24–25% historically reported for 500 V2 baskets are **different strategy objects, statistics and partially different calendars**. The reported 43% unrestricted universe is another distinct object on an older data vintage.

## Verified source facts

| Reference | Universe / selector / whole stack? | Calendar | Reported estimand | Historical performance |
|---|---|---|---|---|
| V2 Hybrid24 current-raw clean-room full stack | 500 fixed 24-ETF baskets from 149 ETF universe, source-only Titanium + S3B clusters + MA3 hybrid producer + tail smoothing + continuously weighted Top2 + DD-first + V6 REL_B + HighCAGR24; 10bp | **2017-02-01 to 2026-07-01**, 2366 sessions | **Arithmetic mean individual-basket CAGR** | **24.4901650%**; per-basket mean MaxDD −34.2656334%; current-raw holdout 2023–26 mean CAGR 30.5184865% |
| ETF_TRAINER_V2 frozen candidate | Same full stack plus only conditional C4/SEVERE high-conviction risk-sleeve allocation refinement, no gross increase | 2017–26 | **Mean individual-basket CAGR** | **24.897%**, not yet production-promoted; prospective gate pending |
| Historical V2 **full universe**, unrestricted 149 ETFs | A single global Top1/Top2 among all 149, original V2 full-system behavior incl dynamic positioning/risk; **NOT** 500 baskets | **2017-02-01 to 2026-07-01**, 2366 sessions, 113 completed signals | **Single aggregate portfolio CAGR** | **43.1459524%**, MaxDD −25.035765%; recorded as old historical canonical 149 reference in 2 Oct controlled comparison |
| The **same full-universe V2 design**, fresh raw | 149 unrestricted; independently regenerated source-only producer and downstream replay, no historical score/path read; comparisons within workflow | **Same 2017-02-01 to 2026-07-01** | **Single global-portfolio CAGR** | **31.6039946%**, MaxDD −35.770633%, Sharpe 1.11062, on **new RAW vintage**. **−11.541958 pp** vs historical 43.1459524% |
| Frozen *standalone* V2 LEGACY Ranker Top2, **no complete V2 layers** | 500 fixed baskets, original V2 LEGACY predictions, percentile-gap 0.12 else 75/25, no original V2 full macro/DD/MA3/HighCAGR24 stack | 2018-02 through 2026-07 | **Mean individual-basket CAGR / aggregate 500-basket NAV CAGR** | **13.297% mean / 15.941% aggregate**, L07 study; explicit NOT full V2 comparator |
| **V3 CORRECTED** Pairwise127 Top3 frozen L10.E3/E4 tests | 500 fixed baskets, mathematically corrected 125-feature LM ranker, static Top3 weights **50/30/20**; **no original full Titanium+MA3 Hybrid24+DD-first+V6+HighCAGR24** | 2018-02-01 to **2026-06-01** (101 mature monthly signals; end trimmed to avoid using immature last E3/E4 action) | **Aggregate 500-basket NAV CAGR** (separate mean individual-basket metric) | **15.650411% aggregate BASE** (mean basket ~14.025%) vs E4 **15.699662% aggregate** (mean basket ~14.139%); cost 10bp |

### Source links

- Original Hybrid24 authoritative complete source-only specification and exact metrics:
  https://github.com/AM1975MA/Etf_trader/blob/main/docs/HYBRID24_SOURCE_ONLY_20260924.md
- Independently recreated clean-run certification:
  https://github.com/AM1975MA/Etf_trader/blob/main/results/MA3_SOURCE_ONLY_ENSEMBLE_CURRENT_RAW_20260924.json
- Original **ETF_TRAINER_V2** risk-sleeve refinement and its pending acceptance state:
  https://github.com/AM1975MA/Etf_trader/blob/main/docs/ETF_TRAINER_V2.md
- **Historical V2 unrestricted 43.1459524% vs fresh 149 unrestricted 31.6039946% evidence** in successful GitHub Actions [37020787738](https://github.com/AM1975MA/Test/actions/runs/37020787738), artifact **11233440300**, source artifact `COMPARISON.json` fields `historical_canonical149_reference`, `original149.v2_full_universe`, `fresh149_minus_historical_reference`, `original149.source_only`.
  Old reported Titanium SHA256 `8ec29dd155583b3721fd760fcec9bfbbe43cf96f79e79dd6fd034d478e411dcc`; regenerated fresh 149 Titanium SHA256 `9fdc99dd750653b34ecb5b29dfb5989c71e4ae010483f6e8431e923c9c320f6f`. Old predictions SHA256 `5caf2d1047234e854ff484d5794e421fe1dd6b5283ccde202907a3f0769ab238`, fresh predictions `0aaad6bc99466e5bfa2bac48287bbd127dc45a9aaa393ec68998840803aab02b`. Unlike the older 43% record, the new 31.604% has a repeatable same-source raw-only campaign artifact.
- Original Test V3 L07 full economic study **already explicitly called its legacy V2 ranker comparator NOT the full V2 system**:
  https://github.com/AM1975MA/Test/blob/main/etf-trader-v3%20corrected/reports/L07/20261021_FULL_INTEGRATED_ECONOMIC_REPLAY.md
- E4 source-faithful 10bp fee matched standalone CORRECTED Top3 comparison:
  https://github.com/AM1975MA/Test/blob/main/etf-trader-v3%20corrected/reports/L10/20261022_L10E4_CHRONO_CALIBRATION_RESULTS_AND_CAGR.md

## Root causes of misleading comparison

1. **Wrong strategy**: stripping original producer hybrid, regime/risk and full portfolio-positioning/weight layers, changing the original dynamic Top2 to static Top3 and changing old LEGACY and/or MA3 ensemble to corrected125 Pairwise127. Do not call these "V2" results.
2. **Wrong statistic**: original 24.49% and 24.897% are **arithmetic mean of the 500 individual basket CAGRs**; recent 15.65% was **CAGR of an equal-weight aggregate NAV across baskets**. Even on identical assets, arithmetic mean of per-basket CAGRs and CAGR of aggregate NAV generally differ. The recent Top3 mean individual basket CAGR is ~14.025%, not 15.65%.
3. **Nonmatching calendar**: original full 2017-Feb through 2026-July, new 2018-Feb through 2026-June (label maturity restrictions).
4. **Not identical raw-vintage**: 43.146% unrestricted historical Golden versus later 31.604% unrestricted fresh source-only on the same 2017–26 calendar is **11.542pp difference**, with immutable distinct Titanium/prediction hashes. Source freshness and annual-model refit can change rankings materially; cannot attribute the full 11.542pp to the subsequent V3 adjustments.
5. **Basket constraint**: 43% unrestricted allows choosing from all 149 on each month, whereas a 500-basket test lets each individual portfolio trade only its 24 names. These are not competing estimates for the same universe/decision.
6. **Research target drift**: L10.E1–E4 audited an optional replacement gate on the stripped-down corrected125 static Top3, not on the original profitable full-stack V2 choices, while the user actually sought to **keep the productive ranking and optimize only the final trajectory veto**.

## Hard correction to V3 research protocol

**Preserve all past tests as isolated scientific diagnostics but do NOT use 15.65% to conclude original full ETF Trader V2 alpha has collapsed.** Prior to any new post-rank reviewer training, establish both unmodified reference controls on the EXACT SAME source/raw snapshot, date range, group membership and executor:

A. **Original complete 500-basket Hybrid24 / ETF_TRAINER_V2**: same model annual fits and source-only DAG, DD-first, V6, HighCAGR24, continuous Top2, fee=10bp. Report mean basket CAGR, aggregate NAV CAGR, mean/p10 DD, turnover. Candidate post-rank mathematical veto must be applied **after the real full-stack V2 selection** (and risk budget/gross), and compare original V2 + one optional veto with identical otherwise untouched actions.

B. **Original complete 149-unrestricted global V2**: same full-stack producer/selection/risk/execution, raw vintage and calendar. Anchor **fresh-raw 31.6039946%** from artifact 11233440300 where those inputs are used; historical 43.1459524% must be separately reported as a different data vintage, not silently used as matched control. For 149-global, compare only global-versus-global and report exact original source SHA / raw SHA / signal-date maturity.

C. **Chronological 101-month reduced V3 ranker-only diagnostic** remains a separate lane whose own matched BASE/E1/E2/E3/E4 comparisons are valid only within that restricted lane; do not mix A/B/ C.

Attribution sequence should change ONE variable at a time on an identical vintage: (1) identical original full-stack V2 SOURCE+executor reconstructed baseline, (2) freeze full-stack actual incumbent actions, (3) diagnostics/math trajectory E1–E4 on selected incumbents WITHOUT replacing productive ML or original risk stack, (4) only if functional incremental edge add fee-aware CAGR. No threshold retro-optimization on heavily inspected 2017–26, no production promotion without truly untouched newer data. 

**This is a baseline-lineage audit, NOT a newly executed full-stack V2/V3 matched backtest**. No evidence that the original 24.49/24.897 or historical 43.14595 results were erased; the most recent work simply tested different strategies, and separate data vintage experiments explain much of the old-vs-new 149 global result.
