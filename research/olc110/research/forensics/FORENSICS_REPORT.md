# OLC109 loss and rebound forensics

## Scope and result

This is a descriptive examination of the immutable `DEDUP_DUAL_TREND_OPP` candidate and existing OLC109 controls. It does not fit, simulate, rank, or promote any new protection/reentry strategy. Every new file is inside `olc110/research/forensics`; no OLC109 file is edited.

The evidence supports treating first shock losses, prolonged deterioration, profit giveback, and reentry as different problems. The largest daily losses often arrived while long and short momentum were still positive. In several longer selloffs, faster deterioration was visible well before the existing SMA63 condition. Old controls sometimes avoided further losses, but monthly reentry restrictions also missed large recoveries. Actual portfolio recoveries frequently came from newly selected funds rather than the fund that had just fallen.

The candidate remains a retrospective research result. The calculations below do not establish which prospective rule can improve it.

## 1. Accounting, chronology, and verification

`diagnose_olc109.py` independently replays the saved orders for eight existing accounts: all five candidate scenarios and BASE for `DEDUP_DUAL21`, `DEDUP_DUAL_EXIT63`, and `DEDUP_DUAL_TRAIL15`. It imports no production strategy, account engine, or audit implementation. CSV numbers are read with `float_precision="round_trip"`.

The maximum reconstructed NAV discrepancy is EUR **2.91e-11**. Maximum daily PnL reconciliation error is EUR **2.00e-11**; maximum fund-level discrepancy versus the existing independent attribution is EUR **1.27e-11**. Both accepted-price and raw-turnover file hashes match the frozen stage-two manifest. See `ACCOUNT_RECONSTRUCTION_QA.csv` and `SOURCE_MANIFEST.json`.

Accepted Close observations are forward-filled exactly as in the source account convention. An Open is executable only when the independent accepted Open mask permits it. A missing Open is marked with the prior accepted Close and receives no hypothetical fill. PnL is decomposed as:

\[
\Delta NAV_k = \sum_j q_{k-1,j}(O^*_{k,j}-C_{k-1,j})
 + \sum_j q_{k,j}(C_{k,j}-O^*_{k,j}) - \mathrm{fees}_k.
\]

Here the first quantity is pretrade, the second posttrade, and the Open mark is the valid Open or prior accepted Close. Saved `nav_open` is before that Open's transaction fees. Sampled drawdown uses the ordered chain initial wealth, Open, Close, Open, Close. The initial wealth is EUR10,000. Existing BASE costs are EUR1 plus 15 basis points per order; this work does not change them.

Features have explicit `information_close_idx` and `information_close_date`. One-day loss diagnostics use the **previous** completed Close and actual pretrade holdings. Momentum columns in these diagnostic files are simple returns `C[t]/C[t-h]-1`, not the production logarithmic values; their signs are identical. SMA columns are `C/SMA-1`. Volatility is the sample standard deviation of historical log returns, annualized by square root of 252. No future label is an input to a feature.

Episode peaks, troughs, worst-day selection, and subsequent returns are deliberately retrospective labels. Their use to select an illustration does not make that illustration an out-of-sample signal test.

## 2. Largest drawdowns and time underwater

Elapsed sessions count differences in the frozen common-calendar indices; they do not count endpoints twice. Open/Close phases are retained because a rebound can already occur within the trough day.

| Peak | Trough | Sampled loss | First recovery of prior peak | Decline sessions | Trough-to-recovery sessions |
|---|---|---:|---|---:|---:|
| 2020-03-19 Open | 2020-08-11 Close | -37.9205% | 2022-06-06 Close | 99 | 463 |
| 2026-05-28 Close | 2026-10-16 Close | -35.9955% | Unrecovered at 2026-10-30 | 101 | — |
| 2024-12-05 Open | 2025-04-07 Open | -28.9382% | 2025-07-10 Close | 82 | 65 |
| 2024-07-17 Open | 2024-08-05 Open | -28.7613% | 2024-11-06 Close | 13 | 67 |
| 2025-10-16 Open | 2025-11-21 Close | -28.1777% | 2026-01-29 Open | 26 | 44 |
| 2026-03-02 Open | 2026-03-23 Open | -26.4509% | 2026-05-25 Close | 15 | 42 |
| 2022-06-08 Close | 2023-06-27 Close | -25.3521% | 2023-12-19 Close | 270 | 125 |
| 2023-12-28 Open | 2024-01-19 Close | -23.9141% | 2024-02-15 Open | 15 | 19 |

The maximum **sampled** drawdown is the 2020 episode, not the July/August 2024 episode. It lasted 562 elapsed trading sessions from peak to recovery. The maximum **Close-only** drawdown is the different, unrecovered 2026 episode. This distinction matters when comparing maximum-drawdown numbers or attributing a single worst event.

The worst 21-session Close return is **-24.1484%**, from 2024-07-16 Close to 2024-08-14 Close. Next are -23.6486% from 2026-05-28 to 2026-06-26 and -21.6779% from 2025-10-15 to 2025-11-13. These are nonoverlapping windows selected retrospectively, without changing any rule.

Sources: `BASE_LARGEST_DRAWDOWNS.csv`, `DRAWDOWN_EPISODES_ALL_SCENARIOS.csv`, `WORST_21_SESSION_WINDOWS_NONOVERLAPPING.csv`.

## 3. Economic sources of losses: concentration and giveback

### The 2020 maximum

The account rose from EUR10,000 to EUR22,124.40 at the March 19 Open, then declined to EUR13,734.72 at the August 11 Close. The trough was still above the starting capital. The VIX futures fund `LU0832435464` contributed **-EUR8,352.87**, or **-37.7541 percentage points of peak wealth**, to the EUR8,389.68 portfolio decline. The entire episode incurred only EUR116.60 in fees. Other holdings partly offset one another.

By the March 19 peak the VIX fund had grown to **77.59%** of wealth, despite the 50/50 target at the last monthly allocation. Its March-to-October holding period nevertheless earned **+EUR3,802.75 net**. A drawdown-control objective therefore differs from merely avoiding positions whose price has fallen below their purchase price.

### Later concentrated tails

The July/August 2024 decline lost EUR9,474.86. Crypto/blockchain `IE00BMDKNW35` contributed -EUR6,816.58, or -20.6920 points of peak wealth; small-cap value contributed -4.3989 points and semiconductors -3.6704 points. Costs were EUR44.23.

The October/November 2025 decline lost EUR18,633.80. Global X Blockchain `IE000XAGSCY5` contributed **-EUR15,807.59**, or **-23.9040 points**. Its entire October 1–December 1 position lost only **EUR648.06 net**, because much of the peak-to-trough decline reversed an earlier gain.

The March 2026 decline lost EUR17,794.68, including -EUR13,023.96 from silver miners and -EUR4,726.36 from Korea. The May–October 2026 decline lost EUR24,596.05 across successive positions: hydrogen -EUR9,351.92, blockchain -EUR5,758.25, Korea -EUR4,604.98, genomics -EUR3,314.76, and gold mining -EUR2,364.86, partly offset by other funds. It is not one uninterrupted losing holding.

These attribution amounts are exact account PnL over the specified portfolio event interval, including each fund's fees. They are not standalone fund returns. The completed position ledger includes all buys, partial rebalances, sales, and costs, and its PnL sums to final wealth less initial wealth.

Sources: `EPISODE_CONTRIBUTIONS.csv`, `EPISODE_GAP_INTRADAY_FEES.csv`, `HELD_POSITION_EPISODES.csv`; immutable reference `olc109/validation/stage2/HOLDINGS_PNL_ATTRIBUTION.csv`.

## 4. What was known before the largest daily shocks?

Among the candidate's 20 worst portfolio days, the following are mean **prior-close invested-weight shares** satisfying each condition:

| Prior-close condition | All days with positions | Worst 20 days |
|---|---:|---:|
| 126-session momentum positive | 92.68% | **100.00%** |
| 252-session momentum positive | 98.23% | **100.00%** |
| Above SMA200 | 96.50% | **97.66%** |
| Above SMA63 | 79.18% | **87.73%** |
| 21-session momentum positive | 71.27% | **82.66%** |
| 5-session momentum positive | 57.08% | **58.94%** |
| Above SMA20 | 64.89% | **71.79%** |
| Volatility21 greater than volatility63 | 45.51% | **62.91%** |

Slow positive trend does not distinguish most of these shocks: it was still present before almost all of them. Neither does a simple negative five-session sign preempt all first shocks. The volatility ratio is more common before these selected bad days, but this descriptive association is not a fitted classifier, a confidence statement, or a demonstrated trading edge.

The average portfolio loss on the selected 20 days was 7.6138%. Summing their arithmetic return contributions, **65.67%** of the loss was in the previous-Close-to-Open component. A rule first observed at the following Close cannot avoid a preceding gap. The full episode decomposition also shows substantial intraday loss across the longer declines; the gap statistic is specifically about the 20 worst single days, not all losses.

### Deterioration during longer selloffs

The following clocks use the actual candidate holding history. They mark when a condition was first observable during an ex-post-selected decline; they do not execute a hypothetical account.

| Held asset and episode | First m5 negative | First below SMA20 | First EXIT63 condition | First TRAIL15 condition |
|---|---|---|---|---|
| VIX, 2020 | Mar 24 | Mar 31 | May 26 | Mar 23 |
| Crypto/blockchain, Jul/Aug 2024 | Jul 23 | Jul 25 | Aug 2 | Jul 30 |
| Blockchain, Oct/Nov 2025 | Oct 17 | Oct 22 | Nov 13 | Oct 22 |
| Silver miners, Mar 2026 | Mar 3 | Mar 5 | Mar 13 | Mar 9 |
| Hydrogen, May/Jun 2026 | May 29 | Jun 4 | Jun 24 | Jun 5 |

`EXIT63` means both below SMA63 and negative m21, exactly as in OLC109. `TRAIL15` means at least 15% below the rolling 63-Close maximum, also exactly as in OLC109.

For example, the July 23, 2024 negative-m5 observation preceded a valid July 24 Open with a further **27.51%** fall to the crypto fund's held Close low. The first EXIT63 signal was August 2, whose next Open on August 5 coincided with the sampled portfolio trough. Weekly evaluation delayed the trailing15 observation from July 30 to August 2. This supports testing a faster observation clock, but it does not quantify false exits during the rest of the sample.

Sources: `DAILY_CAUSAL_DIAGNOSTICS.csv`, `HELD_ASSET_CAUSAL_DIAGNOSTICS.csv`, `WORST_20_PORTFOLIO_DAYS.csv`, `LOSS_FEATURE_DESCRIPTIVE_SUMMARY.csv`, `CAUSAL_FLAG_TIMING_WITHIN_EXPOST_EPISODES.csv`.

## 5. Market coincidence does not imply a universal market alarm

Both previously held funds had negative Close returns on **17 of the 20** worst portfolio days, compared with **27.50%** of all days with holdings. Same-day negative breadth across eligible ETFs averaged **65.20%** on the worst days, versus **46.37%** overall. This is contemporaneous coincidence, not information available before those losses.

Prior-close five-session breadth was much less decisive: an eligible-ETF majority had negative m5 before only **8 of the 20** worst days. The benchmark had negative m5 before **10 of 20**; it actually rose on **6 of those 20** portfolio loss days.

The clearest opposite-direction example is March 24, 2020: the portfolio lost **12.0023%**, while the accepted S&P 500 ETF benchmark gained **8.5509%**. Only 8.85% of eligible funds had a negative daily return, yet the concentrated VIX holding fell heavily. A broad-equity risk alarm cannot be assumed to protect a changing portfolio that includes volatility futures, bonds, miners, country funds, and thematic equity funds.

The breadth universe reproduces OLC109's contemporaneous eligibility and liquidity conventions, but it contains duplicated economic exposures and mixed asset classes. Its percentages are fund-count statistics, not a diversified market index or point-in-time investable market capitalization measure.

Sources: `UNIVERSE_BREADTH.csv`, `WORST_20_PORTFOLIO_DAYS.csv`; benchmark identity in `SOURCE_MANIFEST.json`.

## 6. Why the existing simple exits sometimes failed

The appropriate existing clean comparator for these controls is **DEDUP_DUAL21**, because both protection variants were built on that selector. They were not built on TREND_OPP. Comparing their returns directly with 25.75% conflates the selector change with the protection overlay.

| Existing account | CAGR | Open/Close maximum DD | Mean exposure |
|---|---:|---:|---:|
| DEDUP_DUAL21 | 17.8441% | -37.9205% | 99.78% |
| DEDUP_DUAL_EXIT63 | 9.0158% | -48.7152% | 76.98% |
| DEDUP_DUAL_TRAIL15 | 9.4913% | -50.6951% | 76.17% |

Existing rules combine weekly sell-only reductions, monthly reentry, and monthly entry blocking. Reductions of the other retained fund arising from forced rebalancing are excluded from the full-exit diagnostic.

**Observed missed rebounds:**

- EXIT63 sold crypto/blockchain on **2024-02-05**. Its price rose **30.6404%** by the next monthly Open on March 1, equivalent to EUR2,040.18 on the sold quantity. The protected account's February return was **0.9562%**, versus **14.3644%** for DUAL21.
- Both guards sold the same fund at the **2024-08-05 Open**. It rose **14.8862%** by September 2. The rebound already began within the sale day.
- TRAIL15 blocked silver miners at the **2026-01-30** monthly decision. The omitted fund's subsequent monthly Open-to-Open return was **38.6936%**. The protected account's February return was **-8.3901%**, versus **+6.0079%** for DUAL21.
- TRAIL15 also blocked crypto/blockchain for February 2024, whose omitted monthly Open-to-Open return was **28.4487%**.

**Observed benefits:** TRAIL15's **2025-11-10** blockchain exit was followed by another **23.7490% decline** to the next monthly Open, equivalent to EUR3,156.08 of further decline on the quantity sold. EXIT63's February 10, 2025 crypto exit was followed by another 16.2240% decline to the next monthly Open.

There were 41 full weekly EXIT63 exits, with a median nine sessions to the next monthly Open; the exited asset rose over that interval in 61.0% of cases. TRAIL15 had 25 full weekly exits, median 12 sessions, and positive subsequent asset returns in 36.0%. EXIT63 blocked 19 monthly entries; TRAIL15 blocked 25. These are small, path-dependent, selected samples. A raw asset move after selling is not a complete account counterfactual: it omits financing, changed future holdings, altered position sizes, and all interaction effects.

Sources: `EXISTING_CONTROLS_SUMMARY.csv`, `EXISTING_GUARD_EXITS_AND_LOCKOUT.csv`, `EXISTING_GUARD_MONTHLY_BLOCKED_ENTRIES.csv`, `EXISTING_GUARD_MONTHLY_COMPARISON_VS_DUAL21.csv`; source rules `olc109/docs/STAGE2_PROTOCOL.md` and `olc109/src/cluster_selectors.py`.

## 7. Recovery speed and replacement opportunities

The recovery clock uses each fund's lowest Close **while actually held inside the portfolio decline**. It is not necessarily the eventual low of the fund: a fund can keep falling after the original account has sold it. All subsequent price changes are labels only.

For Global X Blockchain after **2025-11-21**, the fund gained **26.02% in five sessions**, even though no positive SMA63 condition appeared within the next 63 sessions. Positive m5 appeared after three sessions, by which time the Close had risen 15.34%; the next valid Open on November 27 was already 20.80% above the low. One extra session would enter 23.64% above it; two extra sessions 19.43% above it. Delay is not monotonically harmful in every event, because rebounds are volatile.

For silver miners after **2026-03-20**, positive m5 arrived after four sessions and a 2.04% rise; the next valid Open was 3.68% above the low. SMA20 positivity arrived after eight sessions and a 17.58% rise, and SMA63 after 18 sessions and a 24.01% rise. Slow confirmation would have followed much of this particular rebound.

There is also false-start evidence. Hydrogen's lowest held Close in the 2026 decline was June 29. It rose 5.53% by the first positive-m5 observation four sessions later, but its price was **24.24% below** that June 29 Close after 21 sessions. An early short-window improvement is not sufficient evidence that the original decline has ended.

Actual portfolio recovery often used different opportunities. Net PnL from fund identities **not held at the trough** accounted for:

| Recovery episode | PnL from funds absent at trough | Total recovery PnL | Identity-based share |
|---|---:|---:|---:|
| Aug 2020 to Jun 2022 | EUR7,900.51 | EUR8,537.06 | 92.5% |
| Nov 2025 to Jan 2026 | EUR16,002.51 | EUR19,724.28 | 81.1% |
| Mar 2026 to May 2026 | EUR12,637.35 | EUR17,873.82 | 70.7% |

Energy and clean energy helped the first recovery; gold mining and commodities the second; hydrogen, AI, and uranium the third. Conversely, the August–November 2024 recovery largely came from the already-held crypto fund, which contributed EUR7,319.33 of EUR9,961.42 total recovery PnL.

This identity partition is descriptive. A fund counted as held at the trough may later be sold and repurchased; it does not attribute a causal benefit to a particular reentry rule. It does show why any frozen research design should distinguish reopening a previously held asset from admitting a newly qualified asset.

Sources: `ASSET_REBOUND_TIMING.csv`, `RECOVERY_CONTRIBUTIONS.csv`.

## 8. Execution-delay sensitivity is already material

| Frozen scenario | CAGR | Final equity | Sampled maximum DD |
|---|---:|---:|---:|
| BASE | 25.7526% | EUR46,045.58 | -37.9205% |
| ZERO_COST | 28.8205% | EUR54,068.74 | -37.4300% |
| DOUBLE_COST | 22.6914% | EUR39,071.83 | -38.4065% |
| LAG1 | 18.6490% | EUR31,253.61 | -40.7282% |
| LAG2 | 13.1942% | EUR22,839.51 | -45.6796% |

The extra lag means extra common-calendar sessions before the next accepted Open; it is not execution at the signal Close. Monthly return attribution locates large LAG1 gaps in December 2023, March 2025, and October 2024. Together those three months contribute -0.20591 to the total -0.38750 log-wealth gap versus BASE. This is localization of the existing result, not an assertion that all delay cost comes from reentry or that selecting a fast signal can recover it.

Sources: `CANDIDATE_FIVE_SCENARIOS.csv`, `CANDIDATE_SCENARIO_MONTHLY_RETURN_GAPS.csv`.

## 9. Limits and implications for the next frozen experiment

The observations justify a small research design that separately examines faster loss recognition, an explicit path back from cash, and eligibility for new opportunities. They do not identify a winning threshold. Long-trend positivity alone did not warn of most first shocks; late SMA63 exits and monthly lockouts can miss large rebounds; rapid m5 recovery can also be a false start. Gaps, concentrated winners, and the giveback of large unrealized gains remain important even when entry-price losses look modest.

The original source limitations remain intact:

- The current catalog does not certify reconstruction of closed/delisted historical funds or freedom from survivorship bias.
- Positive completed-day volume retrospectively filters some Open availability, although that volume is not known at the Open. Historical vintage of adjustment factors is uncertified.
- Adjusted Open/Close proxies and fractional economic units do not certify executable physical share fills, spreads, opening auction depth, or capacity. Taxes are excluded; cash earns no interest.
- Open/Close sampled drawdown can miss a deeper intraday low.
- All 2020–2026 observations have already been inspected, and the existing stages were adaptive. This analysis creates no pristine holdout or independent validation sample.
- Fund-count breadth is not an independent market signal; correlated fund copies and mixed economic exposures remain in it.
- Highest-loss-day and episode-conditioned statistics are intentionally selected after observing outcomes. They must not be interpreted as unconditional predictive hit rates or used to choose new thresholds without declaring the additional adaptation.

The relevant immutable source discussion is `olc109/RAPPORTO_OLC109_IT.md`, sections 9–10. Reproduce this diagnostic from the workspace root with `python olc110/research/forensics/diagnose_olc109.py`. The source manifest records every read input and the diagnostic script hash.
