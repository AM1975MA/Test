# OLC108 final V3: what failed, and what OLC109 should test

## Conclusion

The principal failure is exposure to a small number of highly volatile economic themes. The annual leaders and both monthly opportunity variants lost **43.553% from the 28 December 2023 opening NAV to the 19 January 2024 closing NAV**. The entire loss came from two different blockchain equity ETFs: **DAVV −22.335 percentage points and BLCH −21.218 points**, measured against the peak NAV. A positive annual trend or a 200-session moving-average gate would not have protected that episode: both instruments remained above their 200-session averages throughout the event.

The opportunity selector introduces a second failure mode. Short-horizon rebounds frequently replace a persistent sector leader with an instrument whose longer trend is weak. It sometimes succeeds spectacularly, but its historical incremental payoff is uneven and has a negative median. More frequent execution increases turnover substantially and does not establish a better signal. Risk scaling reduces the losses but also removes much of the return that supported the headline CAGR.

The evidence therefore supports separating selection, diversification/allocation, execution timing, and protection. It does **not** support treating more history, an absolute-trend filter, or a mean-reversion overlay as a single remedy for all four failures.

## Scope and reproducibility

This review uses **only final V3** under `/workspace/scratch/23237d81ce2c/olc108/results` and the final ETF source panel. The panel SHA-256 is `14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96`, matching the V3 manifest. No rejected V1 or superseded V2 results were used. No new strategy was simulated or optimized, and no OLC108 file was modified.

`diagnose_v3.py` reconstructs the executed holdings of 13 ETF BASE accounts, decomposes each daily NAV change into instrument overnight price movement, intraday price movement, and trading costs, and reproduces annual returns and sampled drawdowns. The greatest daily P&L reconciliation error is below **€0.000000000022**. Lifetime instrument P&L also reconciles to the published attribution. All detailed calculations, selection-time features, and source qualifications are in `diagnosis_v3.json`.

Contributions below are additive percentages of the relevant year's starting NAV or drawdown peak NAV. They are not stand-alone ETF returns. “Sampled drawdown” uses the recorded opening NAV before that session's fees and closing NAV; it does not measure intraday lows. The sample is **2 March 2020–30 October 2026**: 2020 and 2026 are partial calendar years.

## 1. All calendar years

Returns after the archived €1 ticket and 15-basis-point-per-side costs:

| Year | Passive S&P 500 | Monthly leaders | Monthly Dual63 | Monthly Dual21 | Monthly Dual21 Risk15 | Weekly Dual21 |
|---|---:|---:|---:|---:|---:|---:|
| 2020, partial | 13.14% | −13.45% | 87.38% | 86.22% | 45.09% | 61.68% |
| 2021 | 40.74% | −1.36% | −17.94% | −19.50% | −15.21% | −28.91% |
| 2022 | −14.31% | 49.55% | 20.39% | 3.29% | 3.59% | 25.97% |
| 2023 | 22.47% | 65.79% | 50.12% | 116.63% | 36.45% | 25.17% |
| 2024 | 32.32% | 25.67% | 12.91% | −4.89% | 6.63% | −25.70% |
| 2025 | 4.73% | 1.28% | 10.13% | 46.27% | 25.97% | −10.91% |
| 2026, through 30 October | 16.75% | −8.40% | −0.18% | −17.70% | −8.38% | −14.22% |

The monthly Dual21 CAGR of **22.375%** is supported by very large 2020, 2023, and 2025 gains. Its annual result trails the monthly leaders in **2021, 2022, 2024, and 2026**. Those years must remain visible in OLC109; a full-period winner alone would conceal this pattern.

The gains and losses often come from the same theme. DAVV and BLCH contributed **103.285 percentage points** of Dual21's **116.630%** return in 2023; the same pair caused its worst drawdown the following month. In 2020, VOOL contributed **38.028 points** and clean energy IQQH **31.702 points** of the account's **86.216%** return. Excluding a losing instrument or theme after viewing its losses can also remove a material part of the historical edge.

Sources: `SCORECARD.csv`, `ANNUAL_RETURNS.csv`; JSON `paths.*.annual` and `lifetime_contributors`.

## 2. Drawdowns and the instruments responsible

### The common worst drawdown: blockchain equities, December 2023–January 2024

| Account | Peak | Trough | Sampled drawdown | Recovery of that peak |
|---|---|---|---:|---|
| Monthly leaders | 2023-12-28 open | 2024-01-19 close | −43.553% | 2024-06-14 open |
| Monthly Dual63 | Same | Same | −43.553% | 2024-06-14 open |
| Monthly Dual21 | Same | Same | −43.553% | 2024-11-11 open |

DAVV and BLCH alone explain all three losses. At the 29 December decision they had **74.10% and 77.37% trailing 21-session returns**, **281.66% and 272.44% trailing 252-session returns**, and a **0.9377 trailing 126-session correlation**. Holding two ISINs supplied little protection against their shared economic exposure.

At the 19 January trough DAVV was still **2.05% above its 200-session average** with a **47.73% annual return**; BLCH was **5.92% above** with a **45.75% annual return**. An absolute gate using those two conditions would remain open. At the 31 January decision both also retained positive 63-, 126-, and 252-session returns. Multi-horizon positivity alone is therefore not a sufficient tail-risk rule either.

The annual 2024 drawdown table reports **−41.855%**, rather than −43.553%, because it starts from the 29 December closing NAV. The full-period peak occurred one session earlier at the open. These are different denominators, not a discrepancy.

### Other important drawdown episodes

| Account / year | Peak to trough | Drawdown | Largest negative contributions, percentage points of peak NAV |
|---|---|---:|---|
| Dual21 monthly, 2021 | 2021-01-08 open → 2021-07-20 open | −32.707% | IQQH clean energy −16.593; VOOL VIX futures −6.157; BNXG blockchain −5.243; ETLX gold mining −5.184 |
| Leaders monthly, 2022 | 2022-06-08 close → 2022-07-06 close | −24.881% | IS0D oil/gas −12.382; QDVF energy −11.457; ZPDE energy −1.042 |
| Dual21 monthly, 2022 | 2022-06-08 close → 2022-09-26 open | −26.854% | IS0D −12.255; QDVF −7.151; XBAK Pakistan −3.990; UIC2 China tech −2.876 |
| Leaders monthly, 2026 | 2026-03-02 open → 2026-07-30 open | −40.695% | SLVR silver miners −14.067; G2XJ gold miners −11.546; FLXK Korea −10.564; LKOR Korea −10.445; positive contributions offset part of these losses |
| Dual21 monthly, 2026 | 2026-01-29 open → 2026-10-15 open | −37.954% | ETLX gold miners −13.901; SLVR −8.653; FLXK −7.598; LKOR −7.118; VOOL −4.582; other gains offset part of these losses |

The Risk15 Dual21 account has a different worst episode: **−23.808%**, from **8 January 2021 open to 26 September 2022 open**. VOOL contributes **−12.162 points** and IQQH **−8.936 points** of its peak NAV; several additional detractors and offsetting winners complete the accounting. Protection reduced the 2024 concentration shock enough that a slower cumulative loss became the worst episode.

Weekly Dual21's global **−54.217%** drawdown runs from **19 March 2020 open to 16 August 2024 close**, without recovery by the final date. VOOL alone contributes **−69.755 points of that peak NAV**, or **−€13,758**; other holdings offset part of the loss. This is a persistent repeated-entry problem, not merely one bad weekly transaction.

Sources: per-path `DAILY.csv.gz` and `ORDERS.csv.gz`; JSON `global_drawdown`, `annual[].worst_drawdown`, and `critical_2024_blockchain_event_features`.

## 3. Why Dual21 lagged in the four specified years

### 2021: weak rebounds and clean-energy reversal

Dual21 returned **−19.495%** versus leaders **−1.360%**. Its largest annual detractors were VOOL **−14.454 points**, IQQH **−7.185**, and ETLX **−5.813**; gains elsewhere offset part of those losses. The extra selector did not escape the clean-energy reversal and added VIX-futures and gold-miner losses.

The existing matched-state test isolates the substitution decision without comparing different wealth paths. Among the **10** 2021 opportunity-used monthly intervals, Dual21's mean increment versus leaders is **−172.8 basis points**, median **−274.0 bps**, with **40%** wins. Selecting ETLX on 31 May rather than retaining the second leader costs **871.3 bps** over the next interval; the 30 November VOOL substitution costs **814.0 bps**.

### 2022: diversification away from the winning energy exposure

Leaders returned **49.549%**, supported by **46.977 points** from oil/gas equity ETFs and **87.70% mean close exposure** to that group. Dual21 returned **3.293%**, with **15.778 points** from energy and **54.89% mean close exposure**. It repeatedly replaced the second energy leader with weaker clean-energy, VIX, China-technology, Pakistan, or gold-mining exposures.

The matched-state mean increment is **−442.9 bps** across **9** opportunity-used intervals, with **33.3%** wins. The substitutions at 31 March (QCLN), 29 April (VOOL), 30 June (UIC2), and 30 September (M9SD) cost approximately **933, 916, 974, and 1,144 bps**, respectively, against the same-starting-state leaders control. Several challengers had positive recent returns but negative annual returns; this is a concrete rationale for testing an absolute filter on challengers.

The same energy concentration that created much of the 2022 profit also generated a **24.881%** leaders drawdown in June–July. Diversification cannot be judged only by whether it preserves all of that concentrated upside.

### 2024: identical January crash, then slower recovery and harmful substitutions

Dual21 and leaders lose the same **32.55%** in the matched January interval. Their full-year difference is therefore largely about what follows the crash. Dual21's full-year return is **−4.892%** versus leaders **25.673%**.

On 31 January, Dual21 replaces BLCH with Turkey ETF LTUR and loses **1,626.3 bps** versus the matched leaders portfolio during February. The retained BLCH would rebound strongly. On 31 May, its HYCN hydrogen substitution costs another **1,961.0 bps** versus the matched control. HYCN contributes **−9.233 points** to Dual21's annual return. Other substitutions help, but across **10** opportunity-used intervals the mean increment is **−324.6 bps**, median **−391.3 bps**, and win fraction **40%**.

This year contains both a strong example of short-term reversal after a crash and a strong example of continued weakness after a short rebound. A broad claim that “mean reversion predicts the next month” is not established by either observation alone.

### 2026: mining reversals, hydrogen, and correlated Korea exposure

Dual21 returned **−17.702%** versus leaders **−8.401%** through 30 October. Its largest annual negative contributions include FLXK **−9.039 points**, LKOR **−8.381**, VOOL **−5.953**, KWBE China internet **−5.276**, and HYCN **−5.178**. BLCH contributes **+11.328 points** and SLVR **+5.505**, illustrating why the annual attribution differs from peak-to-trough attribution.

The 30 June leaders pair FLXK/LKOR has **0.9910** trailing correlation, rising to **0.9952** at 30 September. This is near-duplicate country exposure even though the funds track different named indices. Dual21 avoids the pair for part of the summer, but re-enters it in September. Its mean matched increment across **8** opportunity-used intervals is **−109.4 bps**, with **37.5%** wins. The 31 July KWBE substitution costs **1,080.8 bps** versus matched leaders.

Sources: `SAME_STATE_INTERVALS.csv`, `SAME_STATE_ANNUAL.csv`, `TARGET_PAIR_CORRELATIONS.csv.gz`; JSON annual contributors and selections. Matched intervals are assigned by their ending year and are not annual compounded returns; cross-year intervals remain identified in the source.

## 4. Two positions frequently mean one economic exposure

The classification below uses provider instrument names, not constituent-level holdings. It is a transparent proxy and should not be presented as verified portfolio overlap.

| Monthly account | Decisions with two selected assets | Same classified theme | Trailing 126-session correlation above 0.90 | Median pair correlation |
|---|---:|---:|---:|---:|
| Leaders | 80 | 29 (36.25%) | 31 (38.75%) | 0.5633 |
| Dual63 | 80 | 21 (26.25%) | 23 (28.75%) | 0.3457 |
| Dual21 | 80 | 12 (15.00%) | 12 (15.00%) | 0.1972 |

Examples include energy QDVF/ZPDE at approximately **0.999** correlation in June–August 2022; blockchain DAVV/BLCH at **0.938–0.980** at several monthly decisions; and Korea FLXK/LKOR at **0.991–0.995** in June–September 2026. These are different securities with strongly redundant observed exposure. This review does not establish that their full underlying constituent lists are identical.

Dual21 improves the average diversification statistics substantially and still retains the entire worst drawdown. An allocation rule must constrain the exposure at the dangerous decisions, not just improve its average correlation. Increasing the number of instruments without controlling shared themes can preserve the same problem.

## 5. Maturity and prior turnover: useful controls, incomplete explanation

The existing eligibility already requires at least **253 observed closes**. Earliest first selections in monthly Dual21 have **254 observations**. Low observation counts can reflect the source panel's February 2019 start, so they must not be confused with a new fund listing: VOOL has 268 observed records at its first selection but was listed in December 2012.

First selections in the monthly Dual21 account:

| ETF | First selected | Observed records by signal | Days since current Xetra listing | Prior 63-session average daily turnover | Approx. half-NAV / prior turnover |
|---|---|---:|---:|---:|---:|
| VOOL, VIX futures | 2020-02-28 | 268 | 2,629 | €345,748 | 1.45% |
| ETLX, gold miners | 2021-05-31 | 280 | 406 | €81,840 | 9.50% |
| QCLN, clean energy | 2022-03-31 | 274 | 405 | €60,810 | 14.41% |
| DAVV, crypto/blockchain equities | 2022-07-29 | 317 | 449 | €92,249 | 7.93% |
| HYCN, hydrogen | 2023-07-31 | 368 | 537 | €26,895 | 32.43% |
| BLCH, blockchain equities | 2023-11-30 | 405 | 674 | €49,695 | 19.64% |
| JEDI, space equities | 2024-07-31 | 499 | 763 | €14,346 | 91.60% |
| FLXK, Korea | 2026-06-30 | 1,624 | 2,582 | €5,889,285 | 0.43% |
| KWBE, China internet | 2026-07-31 | 635 | 1,025 | €472,325 | 4.88% |
| LKOR, Korea | 2026-09-30 | 1,744 | 2,777 | €3,130,564 | 0.73% |

Turnover is raw daily volume × raw close on this listing, with missing/invalid final-V3 observations contributing zero to the fixed-session mean. The lookback ends at the signal close. The half-NAV ratio is a proposed position-size diagnostic, **not actual order participation**, and daily turnover does not establish opening liquidity, spreads, or market-maker capacity.

A prior-turnover admission rule is justified as an execution-feasibility control for some early selections. It does not explain the liquid, mature Korea losses. Requiring 504 observations would suppress some young-theme exposure but also remove BLCH's late-2023 entry, which contributed **45.163 points** of that year's Dual21 return. Moreover, the damaging HYCN selection in May 2024 already has **576 observations**, so a 504-day gate would not remove it. A maturity rule is not a substitute for allocation and protection.

## 6. What the hypotheses do and do not address

| Hypothesis | Evidence-supported purpose | Limitation and bounded experiment recommendation |
|---|---|---|
| Absolute trend | Reject positive short rebounds inside weak long trends. VOOL in several later entries, HYCN in May 2024, and KWBE in July 2026 supply concrete examples. | Run one fixed, predeclared gate, e.g. positive 252-session return and price above the 200-session average, with a fixed fallback. Do not claim this protects the blockchain crash: both conditions remain satisfied at its trough. |
| Multiple momentum horizons | Reduce dependence on a single annual rank and expose disagreements between a recent bounce and the longer path. | Compare one fixed equal-weight combination of 63/126/252-session ranks with one fixed version excluding the latest 21 sessions. Do not optimize weights or window grids. Positive multi-horizon momentum alone still admits the worst crypto pair. |
| Short-term mean reversion | Potentially avoid chasing an extreme recent rally, or retain an otherwise strong leader through a short reversal. | Treat as a separate, lower-priority timing hypothesis with one frozen specification. At 30 November 2023 BLCH already had +27.04% trailing21 momentum and then gained roughly72% in December; suppressing all strong recent winners could destroy major gains. On the selected monthly Dual21 sample, positive 21-session momentum has mean next-interval price return 3.06%, versus 0.27% for nonpositive 21-session momentum; these dependent retrospective observations do not support a generic contrarian rule. |
| More positions / exposure diversity | Directly reduce the top2 single-theme concentration that causes the largest drawdown. | Test one economic-group/correlation constraint at the existing two-position count, then one fixed four-position allocation with the same constraint. Count independent exposures, cap individual positions, and leave unavailable slots in cash under a frozen rule. Do not promise that adding positions preserves concentrated 2022/2023 gains. |
| Maturity and prior liquidity | Make newly tradable histories and the assumed position sizes more credible. | Use point-in-time rules and record exclusions; treat them as data/execution controls. Do not choose a minimum history or turnover threshold by deleting the named losing ETFs. Report the profitable exclusions too. |
| Protection | Address fast losses that remain inside a positive long trend and cap risk separately from selection. | Compare one predeclared daily protection module against the same selection/allocation with it disabled. Retain Risk15 as a known reference. Do not tune a volatility target until sample MaxDD just falls below 25%; its existing 12.095% CAGR shows that de-risking alone does not reach the return goal. |

This is a bounded research sequence: retain existing anchors; isolate absolute trend; isolate a fixed multi-horizon selector and one skip-month alternative; isolate the diversity constraint; then test four positions; finally test one protection module on a frozen selection/allocation. It avoids a large factorial sweep and makes each result attributable to a specific module. Only if there is budget and a predeclared mechanism should a separate mean-reversion timing case be added. All seven calendar years, lag stress, doubled costs, and exact target failures should remain visible. No 2020–2026 segment is an untouched holdout after this diagnosis.

## 7. Why simply trading faster or reducing fees is insufficient

Monthly Dual21 makes **15.19×** two-sided annual turnover; weekly Dual21 makes **45.05×**. The weekly CAGR is **0.429%** versus **22.375%** monthly. Removing every modeled trading cost raises weekly CAGR only to **8.307%**, with a **49.142%** sampled drawdown. Monthly zero-cost CAGR is **25.362%**, still below 30%, with the same 43.553% drawdown.

The existing monthly opportunity-used matched comparison has **61** intervals: mean increment **+83.36 bps**, median **−29.26 bps**, and **49.18%** wins. The weekly comparison has **283** intervals: mean **−19.65 bps**, median **−33.53 bps**, and **43.82%** wins. Those distributions do not support using a faster schedule as protection.

Monthly Dual21 is also sensitive to execution timing: one extra session of delay reduces CAGR to **12.951%** and two to **7.830%**, while sampled drawdowns worsen to **46.944%** and **51.338%**. Any OLC109 result that requires the exact first next-open fill needs to show this sensitivity explicitly.

## Material limits

The reconstructed accounting is exact within floating-point precision, but these data cannot prove a tradable future edge. The universe is built from the current catalogue and available provider histories, not a complete historical survivorship-free listing inventory. Final V3 also uses a retrospective positive-daily-volume convention for source-bar validity. Adjusted prices are provider economic units; this is not proof of available executable opening quotes. The classifications here use names and observed correlations, without constituent-level overlap or complete derivative exposure verification. Prior daily turnover is a venue-specific proxy. The signal/outcome groups are dependent and inspected after seeing the results. None of the proposed changes has been backtested in this task, and no new performance estimate or success probability is asserted.
