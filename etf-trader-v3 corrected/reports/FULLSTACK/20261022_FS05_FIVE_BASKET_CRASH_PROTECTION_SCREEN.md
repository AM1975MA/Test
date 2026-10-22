# FS05 — crash and idiosyncratic tail-risk review of five representative 500-basket cases

**2026-10-22; negative screening result; DO NOT PROMOTE / DO NOT LAUNCH all 500 until a future preregistered gate passes.** The five canonical baskets were selected before the risk evaluation from original ETF_TRAINER_V2 CAGR quantiles 10%,30%,50%,70%,90%, not by future risk guard profits. IDs zero-based **227,69,327,301,220**.

## Sources and exact reference

- Same fully source-only original V2 Titanium/S3B/Hybrid24 500-basket full risk pipeline, Stage19 original ET/XGB riskoff conviction, no V3 ranker replacement. Source RAW 149 original adjusted OHLCV artifact 12292840548, GitHub Actions 39482809691; FS02 full original source build GitHub run **39836842157** artifact **12451018561**. 500×24 original canonical baskets SHA256 36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e.
- Original V2 Stage19 and V3 majority 2-of-3 paths from full exact source replay **FS03 GitHub Actions 39838818618**, artifact **12452641034** original daily 500×2,366 net-NAV paths.
- Input 149 original OHLCV CSV checked independently. CPER **2025-07-29 Close 35.00, 2025-07-30 Open 34.71, Low 28.19, Close 28.24**. Its -19.31% close-on-close event is actual copper market move, not clear split/import mistake: 2025-07-30 COMEX futures dropped ~20–22% upon tariff scope change. S&P Global confirmation: https://www.spglobal.com/market-intelligence/en/news-insights/research/prices-decline-as-us-50-tariff-excludes-refined-copper ; original White House July 30 proclamation: https://www.whitehouse.gov/presidential-actions/2025/07/adjusting-imports-of-copper-into-the-united-states/

## Largest peak-to-trough event per V2 500-basket sample

| Basket | V2 CAGR | Peak → trough | MaxDD | mean original DD-first systemic macro G cap | fraction of descent with global macro G=1 | model exposures heavily represented |
|---|---:|---|---:|---:|---:|---|
| 227 (V2 p10) | 10.897% | 2020-01-03 → 2020-04-24 | −29.587% | 0.8907 | 49% | EPHE, WOOD, BNO |
| 69 (p30) | 17.600% | 2021-02-24 → 2022-10-21 | **−49.906%** | 0.9479 | 71% | KRE, KWEB, DBO, EPOL |
| 327 (p50) | 22.288% | 2024-10-04 → 2025-10-01 | −29.941% | 0.9913 | 95% | TAN, ARGT, MCHI, CPER |
| 301 (p70) | 27.525% | 2024-05-20 → 2025-04-08 | −27.912% | 0.9967 | 99% | TAN, IWF, FXI, GDX |
| 220 (p90) | 33.925% | 2024-05-20 → 2025-04-17 | −31.457% | 0.9926 | 96% | SMH, URA, EWT, GDX |

**Important:** DD-first G is an upper-bound risk-budget, NOT actual intraday invested capital. V6 may separately reduce the actual holding or trigger existing stop after price gaps. All five *maximum drawdown magnitudes* are **identical for the V2 and V3 voting policy**. No protective action from V3 FS03 covered the severe episodes.

## A. First broad 5-only diagnostic screen (indicative cash-sleeve proxy, NOT exact full-stack execution)

Signals computed using ONLY underlying V2 observed portfolio/149-ETF closes before each session and exact past raw ETF series. Carry unused fraction in BIL open-to-open as a proxy and add 10bps per one-way exposure change; always-fully-invested reference reproduces original daily V2 NAV. This simplified sleeve is only a **screen**; it does not claim to replicate full source V6 intraday cash/alternative effects when changing risky capital.

Audited fixed mechanism families: trailing 21/63-session realized-volatility caps (20%–35% targets, floor ~40%–50%), 63-session portfolio drawdown thresholds 10/15% with BIL sleeve, 21-day momentum and 5-day rebound reentry, selected ETF 21-day volatility cap, global breadth fraction above 63-session average, and combined drawdown/breadth. No 500-basket returns inspected or backfit, only original V2 five selected paths.

Original five mean per-basket CAGR **22.4470%**, mean maxDD **−33.7606%**. Most protective tested DD+breadth filter mean maxDD **−29.80%** (+3.96pp protection) but mean CAGR falls to **16.72%** (−5.73pp): unacceptable capital efficiency. Milder 21-day 35%-annual-vol cap with 50% risk-sleeve floor mean CAGR **20.93%** and mean maxDD **−33.04%**, giving away ~1.52pp CAGR for ~0.72pp mean drawdown. None was an attractive robust improvement.

## B. Exact original daily V6 source execution, no approximations

Reimplemented original V2 V6 stock selection, original intraday next-open stop/slippage/fees, DD-first, V6 BIL/SHV alternative and 3-day cooldown. **Validated exact daily NAV for all five baskets against both archived FS02 V2 Hybrid24 source and archived FS03 full ETF_TRAINER_V2 Stage19: maximum absolute error 7.46e−14 and 6.04e−14 respectively**. 2,366 sessions, costs 10bps on traded notional, original stop threshold 5.5% from preceding close and stop-fill slip 0.1%. No model retraining, changes solely to intraday conditional stop gate.

One important originally observed weakness: existing V6 protective stop is activated only when the selected ETF's preceding price trend signals are weak or when systemic overnight gap/breadth stress is present; an otherwise healthy price can experience a large idiosyncratic same-day gap or intraday collapse without V6 stop activation. Testing **unconditionally** using the same stop 5.5%, same 3-session cooldown, and same trading fee did NOT work.

| Basket | Original V2 CAGR | Unconditional individual 5.5% stop CAGR | Original maxDD | New maxDD |
|---|---:|---:|---:|---:|
| 227 | 10.897% | 9.841% | −29.587% | −29.008% |
| 69 | 17.600% | 14.480% | −49.906% | −49.307% |
| 327 | 22.288% | 21.844% | −29.941% | **−24.130%** |
| 301 | 27.525% | 22.720% | −27.912% | −30.483% |
| 220 | 33.925% | 27.092% | −31.457% | −33.380% |

Five-portfolio means: V2 **22.447% CAGR / −33.761% mean maxDD / 11.501× annual gross turnover**; indiscriminate 5.5% stop **19.195% CAGR / −33.262% maxDD / 15.040× turnover**. Despite clear tail protection in basket 327, the rule loses **3.252 percentage points of annual CAGR** and makes 301 and 220 drawdowns worse. This is a massive stop-and-reenter whipsaw failure, not evidence of an alpha opportunity. Protecting the unpredictable July2025 copper break after it begins does not imply forecasting it or profiting from it.

## C. Targeted exact-source V6 stopping and underlying ETF risk tilts, only five diagnostic baskets

Compared exact-source versions: allow individual 5.5% stop only if selected ticker trailing 21-day return negative, ticker's own 21-day volatility >45% annual, preceding close below 63-session price moving average, selected ticker 63-session drawdown >15%, AND/or original systemic DD-first gross was fully risk-on; also tested per-month inverse 21-day selected-ETF volatility weights while preserving actual original ticker identities and Stage19 riskoff decisions. All risk feature inputs read only closes before current date; any model-specific thresholds are explanatory prototypes, NOT optimized or promoted.

- The closest-to-CAGR-preserving prototype, **stop when ETF below prior 63d average AND macro DD-first is gross=100%**, has mean CAGR −0.052pp relative to V2 but **mean maxDD worsens by ~1.251pp**, so no protective utility.
- Monthly inverse-selected-ETF-vol risk allocation reduces mean CAGR by 0.387pp AND worsens mean maxDD by 0.825pp.
- Always conditional ticker 63-day drawdown >15% stop reduces mean CAGR by 0.452pp and worsens mean maxDD by 1.127pp.
- Targeting only selected ticker 21-day vol>45% also materially degrades CAGR and the mean maxDD.
- **No exact source-supported candidate on these five simultaneously improves CAGR and mean maxDD by a material margin.** Candidate performance is heterogeneous; individual basket gains are not proof of generalization.

## Gate / follow-up decision

**DO NOT run the requested 500-basket confirmatory evaluation yet.** The user's explicit gate was a distinctly promising joint result on the five, ideally converting loss events into positive convex opportunity. Neither historical drawdown/cash budget throttles nor unconditional/conditional stops nor inverse-vol selected weights showed that. Running all 500 and choosing hindsight winners after this negative five-case screening would add multiple-testing bias.

Diagnosis: (i) **underdiversified 2-ETF positions** with exposures to same thematic, country and commodity high-beta risks; (ii) global market risk cap ignores concentrated **idiosyncratic**, sector and commodity shock hazards during otherwise healthy regimes (94–99% risk-on across 2024–25 worst descents); (iii) original V6 stops are conditionally gated and frequently reenter the same original top-ranked ETF after short cooldown, causing whipsaw; (iv) the July 2025 CPER copper discontinuity is real, not a software-missing-split artifact; it is unforecastable by a simple trailing-vol policy.

Proper next **pre-registered new research line** if desired: build source-only basket-level conditional ex-ante risk utility after real full V2 producer selection, using lower-tail expected shortfall/downside volatility, ETF pair correlations / economic factor overlap, liquidity and event-gap proxies, ETF-specific worsening regime features and diversified safe alternatives. Model causal exposure reduction AND recovery timing together on prior fully matured years with veto-error penalty: focus on avoiding disaster WITHOUT discarding high-upside V2 trend followers. Candidate should be evaluated as a **single frozen decision policy** on chronology not consulted in development; demand a meaningful cost-matched uplift and no change to frozen V2/V3 production. A historical 500 basket study could be exploratory, but would not substitute for never-used future market vintages.

Raw study deliverables currently produced in ChatGPT working runtime: five_screen_full.csv (indicative sleeve), stop_selective_five.csv (exact original V6 selective stop/vol tilt), five_exact_unconditional_stop55.npz, ETF_5_panieri_audit_drawdown.png, ETF_5_panieri_massimi_drawdown.csv. Keep original V2/V3 source and freeze unchanged.