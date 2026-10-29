# B0 EU155 — independent market-risk and sector-rotation experiments

**Date:** 2026-10-29. **STATUS: Exploratory; no production changes.** Frozen B0 / USA149 / V2 / V3 unchanged.

This research has six 101-signal, 2,076-market-date monthly-next-open EUR portfolio replays on original EU155 LIQ50 MOM252 Top5, fixed transaction cost 10bp each traded side. **Original B0 frozen source archive SHA256**: `8c0028d66fd66b8b5c73438980aac759c6e2b4b37729276db2adfd23b77138a8`.

## Source-backed results

| Policy | CAGR | Max DD | Sharpe rf0 |
|---|---:|---:|---:|
| B0 source-derived replay | 8.80% | −35.35% | 0.532 |
| MARKET_HALF_MA200 | 8.60% | −26.81% | 0.573 |
| MARKET_CASH_MA200 | 8.11% | −26.97% | 0.566 |
| PORTFOLIO_VOL15 | 6.98% | −31.24% | 0.490 |
| ROTATION_MARGIN_5PP | 8.55% | −34.27% | 0.503 |
| ROTATION_5PP_MARKET_HALF | 8.00% | −29.51% | 0.527 |

MA200 is the EUROPE BROAD benchmark DE0002635307, prior signal Close, 200 session SMA; exposure is 0.5 if benchmark <200DMA, otherwise 1.0. Zero cash yield, no leverage. The vol15 signal uses trailing 63 daily **frozen B0 NAV** changes available by signal, leverage capped at 1x with 0.25x floor. The rotation rule retains formerly held ETFs when mom252 is no more than five percentage points below the contemporaneous rank-5 threshold, subject to eligibility, and otherwise refills by ranking.

## New decomposition of what worked in 2025

Monthly Top5 selected next-Open return minus all eligible ETFs equal-weighted next-Open return is decomposed EXACTLY into (a) effect of **choosing group exposures** and (b) selection **within groups**, using historical eligible universe, no future outcomes for signals. For diagnostic attribution only, the 6 original categories are expanded to 7 by splitting five clearly labeled bank-sector ETF wrappers from other sector ETFs.

| Window | Mean group allocation effect pp/month | Within-group effect pp/month | Total gross selection excess pp/month |
|---|---:|---:|---:|
| 2018–2024 | −0.016 | −0.004 | −0.020 |
| 2025 | +3.224 | +0.140 | +3.365 |
| 2026 Jan–May | −1.296 | −1.508 | −2.804 |
| All 101 signals | +0.305 | −0.061 | +0.244 |

Thus **sector allocation into bank ETFs drove virtually all of 2025 cross-sectional advantage**, not a demonstrably superior choice among banking ETF wrappers. The bank subgroup is an *ex post explanatory label* and not a traded or point-in-time index.

## Inference / decision

MARKET_HALF_MA200 minus B0 paired annualized log-return difference **−0.184 pp/year**, 6-month circular bootstrap nominal 95% CI **[−2.65,+2.47] pp**. It reduces historical max DD by 8.5 percentage points but this was not evaluated on untouched data; do not promote. Rotation margin reduces turnover (60.84x to 36.07x cumulative) but lowers CAGR. Keep B0 ranker unchanged, test market-risk overlay on future independent data, and acquire historical fund holdings for richer hierarchical sector decomposition.

## Integrity / limitations

- Replayed B0 differs from the original archived frozen NAV by **0.002351 units maximum absolute**, **0.000930 at final date**, so no exact parity assertion.
- 1 traded line with recorded volume zero; 2 held-position day events use last available mark; no new position entered on missing Open.
- 2026-survivor curated ETF population, repeated use of 2018–26 for model research, historical dividend treatment and executable bid-ask unverified; block bootstrap is nominal after multiple testing.
- `B0_EU155_RISK_VS_ROTATION_RESEARCH_20261029.zip`, SHA256 `d1819ac87d5325db22729bf690862ba213d27cff3f6283f93ad2c8bde6e9b331` includes **complete Python executable source, verification tests, per-signal attribution and risk policy, daily NAV, transaction ledger, bootstrap, report and the original unchanged input archive**. Full data/source are in conversation ZIP; GitHub stores this summary and compact scorecards.

B0/V2/V3 main branches and all controls stay untouched.
