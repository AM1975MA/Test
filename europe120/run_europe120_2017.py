#!/usr/bin/env python3
import download_europe120 as d

# Expand only discovery breadth. Eligibility, dates and price semantics remain
# those of download_europe120.py and therefore match the canonical ETF Trader raw feed.
EXTRA = {
    "C01_US_BROAD_STYLE": [
        "iShares Europe ETF", "Vanguard Europe ETF", "SPDR Europe ETF", "Xtrackers Europe ETF",
        "Amundi Europe ETF", "WisdomTree Europe ETF", "First Trust Europe ETF", "Europe hedged equity ETF",
        "Europe value ETF", "Europe minimum volatility ETF", "Europe dividend ETF", "Eurozone equity ETF",
        "WisdomTree Europe Hedged Equity Fund", "First Trust Europe AlphaDEX Fund",
        "First Trust STOXX European Select Dividend Index Fund"
    ],
    "C02_US_SECTOR_THEME": [
        "iShares Europe sector ETF", "SPDR Europe sector ETF", "Xtrackers Europe sector ETF",
        "Amundi Europe sector ETF", "Lyxor Europe sector ETF", "Europe financials ETF",
        "Europe consumer ETF", "Europe industrials ETF", "Europe healthcare ETF", "Europe technology ETF"
    ],
    "C03_DEVELOPED_GLOBAL": [
        "iShares Germany ETF", "iShares France ETF", "iShares Italy ETF", "iShares Spain ETF",
        "iShares Netherlands ETF", "iShares Belgium ETF", "iShares Austria ETF", "iShares Ireland ETF",
        "iShares Poland ETF", "iShares Sweden ETF", "iShares Denmark ETF", "iShares Greece ETF"
    ],
    "C04_EMERGING": [
        "iShares Europe small cap ETF", "SPDR Europe small cap ETF", "Xtrackers Europe small cap ETF",
        "Europe size factor ETF", "Europe value factor ETF", "Europe momentum factor ETF",
        "Europe quality factor ETF", "Europe low volatility ETF", "Europe equal weight ETF", "Europe dividend factor ETF"
    ],
    "C05_BONDS_CASH_CREDIT": [
        "iShares Euro government bond ETF", "iShares Euro corporate bond ETF", "Xtrackers Euro bond ETF",
        "Amundi Euro bond ETF", "SPDR Euro bond ETF", "Vanguard Euro bond ETF",
        "Euro investment grade ETF", "Euro high yield ETF", "Euro inflation bond ETF", "Euro short term bond ETF"
    ],
    "C06_REAL_ASSETS": [
        "iShares Europe property ETF", "SPDR Europe real estate ETF", "Xtrackers Europe real estate ETF",
        "Europe infrastructure ETF", "Europe utilities ETF", "Europe resources ETF", "Europe materials ETF",
        "Europe oil gas ETF", "Europe construction ETF", "Eurozone real estate ETF"
    ],
}

for cat, qs in EXTRA.items():
    d.CLUSTERS[cat]["queries"] = list(dict.fromkeys(d.CLUSTERS[cat]["queries"] + qs))

raise SystemExit(d.main())
