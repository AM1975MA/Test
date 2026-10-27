# EU148 Yahoo same-ISIN repairs + seven Europe index ETFs → EU155 — 27 October 2026

**Executed and inspected, research only.** The original 148 legally distinct selected European ISIN are preserved, six existing ISIN have rigorously identified alternative Yahoo **EUR** exchange venues with independently issuer-verified fund identity and substantial reductions in stale/zero-trade-volume Yahoo bars, seven legally distinct Europe-exposed index-tracking ISINs added. **EU155 ≠ USA149, does not include opportunistic global US ETFs.**

## Proof of sources and data repair

Same-ISIN alternative ticker, old → new (% 2018–2026 bars reporting zero trading volume):
- **IE0005042456** FTSE 100: IUSZ.DE → **ISFA.AS**, 1.31% → **0.00%**; Yahoo 2009 original Amsterdam venue vs 2016 Xetra, daily overlapping returns corr 0.98744.
- **FR0010150458** French CAC40 ESG: XEYX.DE → **E40.PA**, 33.05% → **0.60%**; Euronext Paris Yahoo starts 2009 vs Xetra 2021, corr 0.96707 (original Xetra quotes stale).
- **LU1650488494** EUR sovereign 3–5 year: LYQ3.DE → **EM35.MI**, 21.81% → **0.38%**; corr 0.89410; legal share-class from Nov 2017; earlier vendor relabelled bars clipped.
- **LU1650489385** EUR sovereign 10–15 year: LYQ6.DE → **EM1015.MI**, 20.97% → **3.89%**; corr 0.90648; 2017 legal share-class predecessor-vintage bars clipped.
- **LU1834988609** Europe telecom: LTCM.DE → **TELE.PA**, 12.10% → **0.37%**; corr 0.98826.
- **LU1834988864** Europe utilities: LUTI.DE → **UTI.MI**, 7.56% → **0.38%**; corr 0.99100.

Daily median overlapping return gaps below 0.2 percentage points; issuer ISIN identity independently confirmed; lower day-to-day correlation of low-liquidity original quotes is **not** proof that alternate quotes are bad, but still warrants independent exchange EOD/NAV check. Universe-wide **30 most missing-volume ISIN** were searched using exact-ISIN Yahoo search, with **unverified** results kept separately and NEVER substituted as if verified. Source QAs and 155 individual SHA256 snapshots in the delivered ZIP.

**Seven new EUROPE-underlying instruments, dated from actual lawful quote inception:** FR0007052782 CAC.PA (CAC40 France), IE00B1XNH568 IMIB.MI (FTSE MIB Italy), FR0010251744 LYXIB.MC (IBEX35 Dist Spain), FR0010655746 AMES.DE (IBEX35 Acc, active only 2024+), FR0000021842 BEL.BR (Belgium), IE00B9MRHC27 XDN0.DE (MSCI Nordic), DE0005933964 EXI1.DE (Swiss SLI). **LYXIB.MC Yahoo retrofitted 2009 history was removed before the Madrid listing on 2018-09-20**. Duplicate Spain IBEX holdings are disallowed in one TopK. Original basket already contained DAX, FTSE100, AEX, ATX, SMI so none is re-added.

Original 148 identity and all 155 legal ISIN uniqueness and actual OHLC dates verified; Yahoo auto_adjust OHLC for new symbols. No data interpolation or futures used as tradable OHLC. Fetched in [Actions 40564500863](https://github.com/AM1975MA/Test/actions/runs/40564500863) and [second issuer list 40565834430](https://github.com/AM1975MA/Test/actions/runs/40565834430). Source scanning script [eu148_yahoo_alt_venue_indices_20261027.py](eu148_yahoo_alt_venue_indices_20261027.py).

## Rerun 48 economic policies

For **each** of EU148 frozen, EU148 data repaired, EU155 repaired + indices: 2 liquidity rules (all as-of valid prices; 63 past days >=90% reported positive venue volume and median daily turnover >=€50k), 4 models, Top3 and Top5. **101 common monthly signals January 2018–May 2026**, 2076 common-price days from Feb 2018 through July 1 2026, EUR and 10bps one-way fees, exact next trading-session Open. Ridge alpha 250 retrained separately per calendar year 2018–26 from expanding monthly 2012+ **21-day future ETF minus EXSA actual percentage-return targets**, 16 fixed features, strictly matured labels before each Jan1. 9 fits per universe (27 total), no forward feature use, category and ticker labels from original legal catalog. No original V2 500-basket logic in this study.

**Net EUR Top5 CAGR, as-of liquidity filter fixed at €50k:**

| Fixed method | Original EU148 | Same EU148, six venue repairs | EU155 expanded |
|---|---:|---:|---:|
| MOM252 | **8.22%** | 8.06% | **8.79%** |
| MOM63 | 3.69% | **4.15%** | 3.80% |
| Ridge16 signed percentage excess | **4.96%** | 3.16% | 4.79% |
| 50% Ridge16 rank + 50% MOM252 rank | **11.97%** | 11.36% | 10.52% |

No-filter Ridge+momentum Top5: original **8.82%**, repaired **9.11%**, expanded **8.86%**, but many selection execution records report zero venue volume and so cannot be fully certified as realistic fills.

**Ridge out-of-sample Spearman IC (101 monthly sections)** original **+0.05465**, repaired **+0.04961**, EU155 **+0.04390**; enrichment is **not** a demonstrated predictive win. For Ridge+momentum Top5 with as-of liquidity the 101-month paired log-return improvement vs original EU148 is **−1.31 percentage points annualized for EU155**, nominal 6-month-block 95% CI **[−2.87,+0.28]**. Repair-only effect **−0.55pp**, nominal CI **[−1.61,+0.52]**. All comparisons exploratory, 2018–26 history repeatedly mined; unknown survivorship, bid/ask and actual fill prices.

**Decision:** preserve frozen EU148 B0, store separately 148 repaired and EU155; the Yahoo source data quality improvement is real, but **neither prediction nor economic 30% target is met**. Do not replace production strategies based on these results. USA149 remains untouched and is not newly retested here; original USA B0 stays separate. Require as-of exchange bid/ask, corporate action and delisted ISIN verification before claims of true prospective performance.

## Reproducible deliverable

The conversation archive **EU148_EU155_YAHOO_ISIN_QUALITY_AND_48_RETTEST_20261027.zip** contains original untouched complete EU148 frozen ZIP; 155 individual CSV price/volume series; full 155 ISIN catalog and per-file SHA256; original and alternate Yahoo download audit; publisher-verified six source decisions; 7 index additions; full 48-variant EUR daily NAV and as-of Top3/Top5 trade decisions; all 101×3 monthly model forecasts, 27 annual training audits; all paired time-block bootstrap calculations, and four full reproducibility Python scripts. GitHub Actions artifacts separately hold original unfiltered yfinance fetches. **No production code or USA data modified.**
