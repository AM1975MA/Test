# ETF >20% daily-price events — first external source adjudication (2026-10-09)

## Scope and immutable evidence
Original149, three consecutive Yahoo snapshots. Automated run [37943793896](https://github.com/AM1975MA/Test/actions/runs/37943793896), artifact [11622932331](https://github.com/AM1975MA/Test/actions/runs/37943793896/artifacts/11622932331): 123 >20%-magnitude observations, but **41 distinct ticker × date events**, all in all 3 original Yahoo copies, 25 distinct tickers. Outlier counts over three vintages must not be interpreted as 123 independently erroneous stock-market events. No data replacement is yet justified by a magnitude-only rule.

## External event verification evidence
| Event | Yahoo frozen change | Independent source | Classification | Approved historical price change |
|---|---:|---|---|---|
| KWEB 2022-03-16 | +39.72% | contemporaneous Zacks March 17 report says KWEB up 39.7%; https://www.zacks.com/stock/news/1883306/china-stocks-jump-most-since-2008-etfs-up-at-least-20; The Edge Malaysia March 30 cites 39.72% https://theedgemalaysia.com/node/612764 | genuine market event corroborated | NONE |
| SLV 2026-01-30 | -28.54% | contemporary ETF.com January 30 reports intraday collapse >34%; Benzinga January 30 reports SLV roughly -28% https://www.etf.com/sections/features/gold-silver-etfs-suffer-historic-collapse-trump-fed-pick ; independent historical largest one-day move ~-28.5% https://marketchameleon.com/Overview/SLV/Stock-Price-Action/Largest-Historical-Down-Moves | genuine market event corroborated | NONE |
| CPER 2014-12-04 | -33.15%; reported volume 0 | paired rebound +49.89% on 2014-12-05; no date-specific externally corroborated closing-price/NAV and event verified yet | **SUSPECT** missing trading / bad print / stale-price or adjust | NOT APPROVED (quarantine for investigation) |
| CPER 2014-12-05 | +49.89%; reported volume 200 | reversal of preceding zero-volume -33.15% | SUSPECT linked predecessor; requires NAV/trade data | NOT APPROVED |
| CPER 2015-02-02 | -28.66%; reported volume 0 | next trading day +45.71%; no certified external daily close | **SUSPECT** missing trading / bad print / stale-price or adjust | NOT APPROVED (quarantine for investigation) |
| CPER 2015-02-03 | +45.71%; reported volume 1000 | rebound from zero-volume day | SUSPECT linked predecessor; requires NAV/trade data | NOT APPROVED |

CPER issuer is a copper-futures-based exchange traded commodity fund: SEC 2015 prospectus https://www.sec.gov/Archives/edgar/data/1479247/000119312515165380/d882709d424b3.htm ; its objective is tracking SummerHaven Copper Index Total Return via daily NAV, making these extreme 1-day movements worth independent NAV checking. Broad 2014-2015 monthly historical price references (e.g. https://www.digrin.com/stocks/detail/CPER/price ) are insufficient to certify the *exact daily* replacement. No raw OHLC should be overwritten using a month-end price or interpolation.

## Policy for any approved correction
Do not conflate an adjusted historical close with an unadjusted exchange close. Require an independent daily timestamped price/NAV record with matching adjustment semantics, a documented split/dividend factor and time availability, deterministic method for reconstructing adjusted O/H/L/C, and checks on volume/cross-vintage identity. If only NAV is available and a valid trade close was missing, prefer an explicit **non-tradable observation mask** and separately track NAV for marking-to-market; never claim a fabricated open-to-open execution price. If evidence is insufficient, freeze a SUSPECT flag with exact sources and disable auto-correction; do not zero returns or forward-fill.

### Tool-based price repair is only a *candidate*
yfinance's own price-repair document: https://github.com/ranaroussi/yfinance/blob/main/doc/source/advanced/price_repair.rst acknowledges missing data, dividend adjustments and split errors; documentation also warns false positives. Running repair=True is a diagnostic candidate **not** an independent price oracle or permission to overwrite the frozen Original149 source.

## Decision
No blanket correction of the 123 flags. Two externally corroborated real events retained. Four anomalous CPER events segregated for official/exchange confirmation. Other 35 unique events await exact event-level independent assessment; no false claim that all 41 are resolved. Source snapshots unchanged, model training prohibited, no CAGR computed.
