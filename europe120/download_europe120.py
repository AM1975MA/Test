#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

START = "2004-01-01"
END_EXCLUSIVE = "2026-08-01"  # freeze to same cutoff as Trader_selector
LAST_REQUIRED = pd.Timestamp("2026-07-31")
PRE2017_CUTOFF = pd.Timestamp("2017-01-31")
MIN_PRE2017_ROWS = 252
PER_CLUSTER = 20
EU_SUFFIXES = (".DE", ".PA", ".MI", ".AS", ".BR", ".L", ".SW")

# The six original P45 macro labels are preserved because P45's frozen macro layer
# knows these labels. Their economic contents are EU analogues, not US exposures.
CLUSTER_SPECS = {
    "C01_US_BROAD_STYLE": {
        "label": "EU_BROAD_STYLE",
        "queries": [
            "EURO STOXX 50 UCITS ETF", "EURO STOXX UCITS ETF", "MSCI EMU UCITS ETF",
            "Eurozone UCITS ETF", "EMU ESG UCITS ETF", "EMU Value UCITS ETF",
            "EMU Quality UCITS ETF", "EMU Momentum UCITS ETF", "EMU Minimum Volatility UCITS ETF",
            "Eurozone Dividend UCITS ETF", "Eurozone ESG UCITS ETF", "Eurozone Climate UCITS ETF",
            "EURO STOXX 50 ESG UCITS ETF", "Eurozone Large Cap UCITS ETF", "Eurozone Mid Cap UCITS ETF",
        ],
        "must_any": ["euro stoxx", "emu", "eurozone", "euro zone"],
        "exclude": ["bond", "banks", "bank ", "insurance", "technology", "health", "utilities", "real estate", "property", "small"],
    },
    "C02_US_SECTOR_THEME": {
        "label": "EU_SECTOR_THEME",
        "queries": [
            "EURO STOXX Banks UCITS ETF", "EURO STOXX Insurance UCITS ETF", "EURO STOXX Technology UCITS ETF",
            "EURO STOXX Healthcare UCITS ETF", "EURO STOXX Industrials UCITS ETF", "EURO STOXX Utilities UCITS ETF",
            "EURO STOXX Telecommunications UCITS ETF", "EURO STOXX Automobiles UCITS ETF", "EURO STOXX Chemicals UCITS ETF",
            "EURO STOXX Construction UCITS ETF", "EURO STOXX Energy UCITS ETF", "EURO STOXX Basic Resources UCITS ETF",
            "EURO STOXX Financial Services UCITS ETF", "EURO STOXX Food Beverage UCITS ETF", "EURO STOXX Media UCITS ETF",
            "EURO STOXX Personal Household Goods UCITS ETF", "EURO STOXX Retail UCITS ETF", "EURO STOXX Travel Leisure UCITS ETF",
            "Eurozone Banks UCITS ETF", "Eurozone Technology UCITS ETF", "Eurozone Healthcare UCITS ETF",
        ],
        "must_any": ["euro stoxx", "eurozone", "emu"],
        "sector_any": ["bank", "insurance", "technology", "health", "industrial", "utilit", "telecom", "auto", "chemical", "construction", "energy", "basic resources", "financial services", "food", "beverage", "media", "retail", "travel", "leisure", "consumer"],
        "exclude": ["bond"],
    },
    "C03_DEVELOPED_GLOBAL": {
        "label": "EU_COUNTRY_REGIONAL",
        "queries": [
            "Germany DAX UCITS ETF", "Germany MSCI UCITS ETF", "France CAC 40 UCITS ETF", "France MSCI UCITS ETF",
            "Italy FTSE MIB UCITS ETF", "Italy MSCI UCITS ETF", "Spain IBEX 35 UCITS ETF", "Spain MSCI UCITS ETF",
            "Netherlands AEX UCITS ETF", "Netherlands MSCI UCITS ETF", "Belgium BEL 20 UCITS ETF",
            "Austria ATX UCITS ETF", "Portugal PSI UCITS ETF", "Finland OMX UCITS ETF", "Ireland MSCI UCITS ETF",
            "Greece MSCI UCITS ETF", "Poland MSCI UCITS ETF", "Poland WIG20 UCITS ETF",
            "Sweden OMX UCITS ETF", "Denmark OMX UCITS ETF",
        ],
        "must_any": ["germany", "dax", "france", "cac", "italy", "mib", "spain", "ibex", "netherlands", "aex", "belg", "austria", "atx", "portugal", "psi", "finland", "ireland", "greece", "poland", "wig", "sweden", "denmark"],
        "exclude": ["bond", "short", "2x", "3x", "leveraged", "inverse"],
    },
    "C04_EMERGING": {
        "label": "EU_SMALL_FACTOR_CONVERGENCE",
        "queries": [
            "MSCI EMU Small Cap UCITS ETF", "EURO STOXX Small UCITS ETF", "Eurozone Small Cap UCITS ETF",
            "MSCI EMU Mid Cap UCITS ETF", "Eurozone Mid Cap UCITS ETF", "EMU Value UCITS ETF",
            "EMU Small Cap Value UCITS ETF", "EMU Momentum UCITS ETF", "EMU Quality UCITS ETF",
            "EMU Minimum Volatility UCITS ETF", "EMU Dividend UCITS ETF", "Eurozone High Dividend UCITS ETF",
            "EMU Equal Weight UCITS ETF", "Eurozone Equal Weight UCITS ETF", "EMU ESG Leaders UCITS ETF",
            "Eurozone ESG Screened UCITS ETF", "EMU Climate UCITS ETF", "Eurozone Low Carbon UCITS ETF",
            "Eurozone Small Mid Cap UCITS ETF", "EMU Size Factor UCITS ETF",
        ],
        "must_any": ["emu", "euro stoxx", "eurozone", "euro zone"],
        "style_any": ["small", "mid", "value", "momentum", "quality", "minimum", "volatility", "dividend", "equal", "esg", "climate", "carbon", "factor"],
        "exclude": ["bond"],
    },
    "C05_BONDS_CASH_CREDIT": {
        "label": "EUR_BONDS_CASH_CREDIT",
        "queries": [
            "Euro Government Bond UCITS ETF", "Euro Aggregate Bond UCITS ETF", "Euro Corporate Bond UCITS ETF",
            "Euro High Yield Bond UCITS ETF", "Euro Inflation Linked Bond UCITS ETF", "Euro Covered Bond UCITS ETF",
            "Euro Short Duration Bond UCITS ETF", "Euro Ultrashort Bond UCITS ETF", "EUR Corporate 1-5 UCITS ETF",
            "EUR Government 1-3 UCITS ETF", "EUR Government 3-5 UCITS ETF", "EUR Government 5-7 UCITS ETF",
            "EUR Government 7-10 UCITS ETF", "EUR Government 10-15 UCITS ETF", "Euro Green Bond UCITS ETF",
            "Euro Floating Rate Bond UCITS ETF", "Euro Money Market UCITS ETF", "Euro Cash UCITS ETF",
            "Euro Investment Grade Corporate UCITS ETF", "Euro Sovereign Bond UCITS ETF",
        ],
        "must_any": ["euro", "eur"],
        "bond_any": ["bond", "treasury", "government", "corporate", "credit", "money market", "cash", "covered", "floating"],
        "exclude": ["usd", "dollar", "sterling", "gbp"],
    },
    "C06_REAL_ASSETS": {
        "label": "EU_REAL_ASSETS_INFRA",
        "queries": [
            "Eurozone Real Estate UCITS ETF", "Eurozone Property UCITS ETF", "EMU Real Estate UCITS ETF",
            "EURO STOXX Real Estate UCITS ETF", "EURO STOXX Utilities UCITS ETF", "EURO STOXX Basic Resources UCITS ETF",
            "EURO STOXX Construction Materials UCITS ETF", "EURO STOXX Oil Gas UCITS ETF", "EURO STOXX Energy UCITS ETF",
            "Eurozone Infrastructure UCITS ETF", "Europe Infrastructure UCITS ETF", "Eurozone Utilities UCITS ETF",
            "Eurozone Materials UCITS ETF", "Eurozone Construction UCITS ETF", "Eurozone Industrial Goods UCITS ETF",
            "European Property UCITS ETF", "Europe Real Estate UCITS ETF", "Europe Utilities UCITS ETF",
            "Europe Basic Resources UCITS ETF", "Europe Construction Materials UCITS ETF",
        ],
        "must_any": ["euro", "emu", "europe"],
        "real_any": ["real estate", "property", "infrastructure", "utilit", "basic resources", "material", "construction", "oil", "gas", "energy", "industrial goods"],
        "exclude": ["bond"],
    },
}


def norm_name(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"\b(ucits|etf|acc|dist|distributing|accumulating|eur|gbp|usd|hedged|1c|1d)\b", " ", s)
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def text_ok(spec: dict, name: str) -> bool:
    x = (name or "").lower()
    if spec.get("exclude") and any(k in x for k in spec["exclude"]):
        return False
    if spec.get("must_any") and not any(k in x for k in spec["must_any"]):
        return False
    for key in ("sector_any", "style_any", "bond_any", "real_any"):
        if spec.get(key) and not any(k in x for k in spec[key]):
            return False
    return True


def search_candidates(query: str) -> list[dict]:
    out = []
    try:
        s = yf.Search(query, max_results=50, news_count=0)
        rows = getattr(s, "quotes", None) or []
    except Exception as e:
        print("SEARCH_FAIL", query, type(e).__name__, str(e), flush=True)
        return out
    for r in rows:
        symbol = str(r.get("symbol") or "").upper().strip()
        qtype = str(r.get("quoteType") or "").upper()
        name = str(r.get("longname") or r.get("shortname") or "").strip()
        if not symbol or qtype not in {"ETF", "MUTUALFUND"}:
            continue
        if not symbol.endswith(EU_SUFFIXES):
            continue
        out.append({"symbol": symbol, "name": name, "exchange": r.get("exchange"), "query": query})
    return out


def download_one(symbol: str) -> tuple[pd.DataFrame | None, str | None]:
    try:
        d = yf.download(symbol, start=START, end=END_EXCLUSIVE, auto_adjust=False, actions=False, progress=False, threads=False)
    except Exception as e:
        return None, f"download_error:{type(e).__name__}:{e}"
    if d is None or d.empty:
        return None, "empty"
    if isinstance(d.columns, pd.MultiIndex):
        d.columns = d.columns.get_level_values(0)
    d = d.reset_index()
    need = ["Date", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
    if any(c not in d.columns for c in need):
        return None, "missing_columns"
    raw_close = pd.to_numeric(d["Close"], errors="coerce")
    adj = pd.to_numeric(d["Adj Close"], errors="coerce")
    f = adj / raw_close.replace(0, np.nan)
    q = pd.DataFrame({
        "date": pd.to_datetime(d["Date"]),
        "Open": pd.to_numeric(d["Open"], errors="coerce") * f,
        "High": pd.to_numeric(d["High"], errors="coerce") * f,
        "Low": pd.to_numeric(d["Low"], errors="coerce") * f,
        "Close": adj,
        "Volume": pd.to_numeric(d["Volume"], errors="coerce"),
    }).dropna().sort_values("date").drop_duplicates("date", keep="last")
    if q.empty:
        return None, "no_valid_rows"
    bad = (q["Low"] > q[["Open", "Close"]].min(axis=1) + 1e-8) | (q["High"] < q[["Open", "Close"]].max(axis=1) - 1e-8)
    if bad.any():
        return None, f"ohlc_incoherent:{int(bad.sum())}"
    pre = q[q["date"] <= PRE2017_CUTOFF]
    if len(pre) < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{len(pre)}"
    if q["date"].max() < LAST_REQUIRED:
        return None, f"ends_early:{q['date'].max().date()}"
    q = q[q["date"] <= LAST_REQUIRED].copy()
    return q, None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    out = Path("europe120/output")
    raw = out / "raw_ticker_csv"
    raw.mkdir(parents=True, exist_ok=True)

    selected = []
    rejected = []
    data = {}
    used_symbols = set()
    used_names = set()

    for cat, spec in CLUSTER_SPECS.items():
        pool = []
        seen = set()
        for query in spec["queries"]:
            for r in search_candidates(query):
                key = r["symbol"]
                if key in seen:
                    continue
                seen.add(key)
                if not text_ok(spec, r["name"]):
                    continue
                pool.append(r)
            time.sleep(0.25)
        # deterministic selection independent of returns: query order, then symbol.
        qrank = {q: i for i, q in enumerate(spec["queries"])}
        pool.sort(key=lambda r: (qrank.get(r["query"], 999), r["symbol"]))
        print("POOL", cat, len(pool), flush=True)

        chosen = 0
        for r in pool:
            if chosen >= PER_CLUSTER:
                break
            sym = r["symbol"]
            nkey = norm_name(r["name"])
            if sym in used_symbols or (nkey and nkey in used_names):
                continue
            q, reason = download_one(sym)
            if q is None:
                rejected.append({**r, "macro_category": cat, "reason": reason})
                print("REJECT", cat, sym, reason, r["name"], flush=True)
                continue
            rec = {
                "ticker": sym,
                "macro_category": cat,
                "eu_cluster": spec["label"],
                "name": r["name"],
                "search_query": r["query"],
                "rows": int(len(q)),
                "first": str(q.date.min().date()),
                "last": str(q.date.max().date()),
                "pre2017_rows": int((q.date <= PRE2017_CUTOFF).sum()),
            }
            selected.append(rec)
            data[sym] = q
            used_symbols.add(sym)
            if nkey:
                used_names.add(nkey)
            chosen += 1
            print("SELECT", cat, chosen, "/", PER_CLUSTER, sym, r["name"], flush=True)
        if chosen != PER_CLUSTER:
            pd.DataFrame(selected).to_csv(out / "partial_selected.csv", index=False)
            pd.DataFrame(rejected).to_csv(out / "partial_rejected.csv", index=False)
            raise RuntimeError(f"quota not met for {cat}: {chosen}/{PER_CLUSTER}; candidate pool={len(pool)}")

    if len(selected) != 120:
        raise RuntimeError(f"expected 120, got {len(selected)}")

    file_hashes = {}
    for rec in selected:
        t = rec["ticker"]
        q = data[t].copy()
        q["date"] = q["date"].dt.strftime("%Y-%m-%d")
        p = raw / f"{t.replace('/', '_')}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        file_hashes[t] = sha256(p)

    pd.DataFrame(selected)[["ticker", "macro_category", "eu_cluster", "name"]].to_csv(raw / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)

    for fld in ["Open", "High", "Low", "Close", "Volume"]:
        mat = pd.concat([data[t].set_index("date")[[fld]].rename(columns={fld: t}) for t in data], axis=1).sort_index()
        mat.to_parquet(out / f"{fld.upper()}.parquet")

    manifest = {
        "status": "EUROPE120_DOWNLOADED",
        "economic_scope": "EU/euro-area economy; European-listed UCITS ETFs; six EU analogues of P45 macro clusters",
        "selection_rule": "frozen Yahoo search-query order plus symbol order; economic-name filter; first 20 distinct funds per cluster with >=252 pre-2017 rows and coverage through 2026-07-31; no return/performance criterion",
        "provider": "Yahoo Finance via yfinance",
        "selected_count": len(selected),
        "per_cluster": PER_CLUSTER,
        "cutoff": str(LAST_REQUIRED.date()),
        "performance_used_for_selection": False,
        "selected": selected,
        "file_sha256": file_hashes,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in manifest.items() if k not in {"selected", "file_sha256"}}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
