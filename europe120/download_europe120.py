#!/usr/bin/env python3
from __future__ import annotations

import ast, hashlib, json, re, time
from pathlib import Path
import pandas as pd
import yfinance as yf

# Canonical ETF Trader raw window / semantics.
START = "2004-01-01"
END_EXCLUSIVE = "2026-07-02"
LAST_REQUIRED = pd.Timestamp("2026-07-01")
PRE2017_CUTOFF = pd.Timestamp("2017-01-31")
MIN_PRE2017_ROWS = 252
PER_CLUSTER = 20

CLUSTERS = {
    "C01_US_BROAD_STYLE": {
        "label": "EU_BROAD_STYLE",
        "queries": [
            "Europe ETF", "MSCI Europe ETF", "STOXX Europe 600 ETF", "FTSE Europe ETF",
            "Eurozone ETF", "EURO STOXX 50 ETF", "MSCI EMU ETF", "Europe broad market ETF",
            "Europe large cap ETF", "Europe dividend ETF"
        ],
        "must": ["europe", "euro stoxx", "eurozone", "emu"],
        "exclude": ["bond", "bank", "insurance", "technology", "health", "utility", "real estate", "property", "small cap", "mid cap"]
    },
    "C02_US_SECTOR_THEME": {
        "label": "EU_SECTOR_THEME",
        "queries": [
            "Europe banks ETF", "Europe insurance ETF", "Europe technology ETF", "Europe healthcare ETF",
            "Europe industrial ETF", "Europe telecom ETF", "Europe automobiles ETF", "Europe consumer ETF",
            "Europe media ETF", "Europe travel leisure ETF", "EURO STOXX banks ETF", "EURO STOXX technology ETF",
            "EURO STOXX healthcare ETF", "STOXX Europe sector ETF"
        ],
        "must": ["europe", "euro stoxx", "eurozone", "emu"],
        "any": ["bank", "insurance", "technology", "health", "industrial", "telecom", "auto", "consumer", "media", "travel", "leisure", "financial"],
        "exclude": ["bond", "real estate", "property", "utilities", "basic resources", "oil", "gas", "energy", "materials"]
    },
    "C03_DEVELOPED_GLOBAL": {
        "label": "EU_COUNTRY_REGIONAL",
        "queries": [
            "Germany ETF", "France ETF", "Italy ETF", "Spain ETF", "Netherlands ETF", "Belgium ETF",
            "Austria ETF", "Portugal ETF", "Finland ETF", "Ireland ETF", "Greece ETF", "Poland ETF",
            "Sweden ETF", "Denmark ETF", "DAX ETF", "CAC 40 ETF", "FTSE MIB ETF", "IBEX 35 ETF"
        ],
        "must": ["germany", "dax", "france", "cac", "italy", "mib", "spain", "ibex", "netherlands", "aex", "belg", "austria", "portugal", "finland", "ireland", "greece", "poland", "sweden", "denmark"],
        "exclude": ["bond", "2x", "3x", "leveraged", "inverse", "short"]
    },
    "C04_EMERGING": {
        "label": "EU_SMALL_FACTOR",
        "queries": [
            "Europe small cap ETF", "Europe mid cap ETF", "Eurozone small cap ETF", "EMU small cap ETF",
            "Europe value ETF", "Europe momentum ETF", "Europe quality ETF", "Europe minimum volatility ETF",
            "Europe equal weight ETF", "Europe high dividend ETF", "EMU value ETF", "Europe factor ETF"
        ],
        "must": ["europe", "eurozone", "emu", "euro stoxx"],
        "any": ["small", "mid", "value", "momentum", "quality", "minimum", "volatility", "equal", "dividend", "factor"],
        "exclude": ["bond"]
    },
    "C05_BONDS_CASH_CREDIT": {
        "label": "EUR_BONDS_CASH_CREDIT",
        "queries": [
            "Euro government bond ETF", "Euro corporate bond ETF", "Euro aggregate bond ETF", "Euro high yield bond ETF",
            "Euro inflation linked bond ETF", "Euro covered bond ETF", "EUR corporate bond ETF", "EUR government bond ETF",
            "Euro short duration bond ETF", "Euro floating rate bond ETF", "Euro money market ETF", "Euro cash ETF"
        ],
        "must": ["euro", "eur"],
        "any": ["bond", "government", "corporate", "credit", "money market", "cash", "covered", "floating", "aggregate"],
        "exclude": ["usd", "dollar", "sterling", "gbp"]
    },
    "C06_REAL_ASSETS": {
        "label": "EU_REAL_ASSETS_INFRA",
        "queries": [
            "Europe real estate ETF", "European property ETF", "Europe infrastructure ETF", "Europe utilities ETF",
            "Europe basic resources ETF", "Europe materials ETF", "Europe construction ETF", "Europe oil gas ETF",
            "Europe energy ETF", "EURO STOXX real estate ETF", "STOXX Europe utilities ETF", "STOXX Europe basic resources ETF"
        ],
        "must": ["europe", "euro stoxx", "eurozone", "emu"],
        "any": ["real estate", "property", "infrastructure", "utilit", "basic resources", "material", "construction", "oil", "gas", "energy"],
        "exclude": ["bond"]
    },
}


def original_149() -> set[str]:
    src = Path("regeneration/etf_trader_raw.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    cats = None
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "CATS":
                    cats = ast.literal_eval(node.value)
    if cats is None:
        raise RuntimeError("cannot recover canonical CATS from regeneration/etf_trader_raw.py")
    return {str(t).upper() for xs in cats.values() for t in xs}


def text_ok(spec: dict, name: str) -> bool:
    x = (name or "").lower()
    if spec.get("exclude") and any(k in x for k in spec["exclude"]):
        return False
    if spec.get("must") and not any(k in x for k in spec["must"]):
        return False
    if spec.get("any") and not any(k in x for k in spec["any"]):
        return False
    return True


def search_candidates(query: str) -> list[dict]:
    try:
        rows = getattr(yf.Search(query, max_results=50, news_count=0), "quotes", None) or []
    except Exception as e:
        print("SEARCH_FAIL", query, type(e).__name__, str(e), flush=True)
        return []
    out = []
    for r in rows:
        sym = str(r.get("symbol") or "").upper().strip()
        typ = str(r.get("quoteType") or "").upper()
        name = str(r.get("longname") or r.get("shortname") or "").strip()
        if sym and typ == "ETF":
            out.append({"symbol": sym, "name": name, "exchange": r.get("exchange"), "query": query})
    return out


def download_one(symbol: str):
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
    f = pd.to_numeric(d["Adj Close"], errors="coerce") / pd.to_numeric(d["Close"], errors="coerce").replace(0, pd.NA)
    q = pd.DataFrame({
        "date": pd.to_datetime(d["Date"]),
        "Open": pd.to_numeric(d["Open"], errors="coerce") * f,
        "High": pd.to_numeric(d["High"], errors="coerce") * f,
        "Low": pd.to_numeric(d["Low"], errors="coerce") * f,
        "Close": pd.to_numeric(d["Adj Close"], errors="coerce"),
        "Volume": pd.to_numeric(d["Volume"], errors="coerce"),
    }).dropna().sort_values("date").drop_duplicates("date", keep="last")
    pre_rows = len(q[q["date"] <= PRE2017_CUTOFF])
    if pre_rows < MIN_PRE2017_ROWS:
        return None, f"insufficient_pre2017_rows:{pre_rows}"
    if q.empty or q["date"].max() < LAST_REQUIRED:
        return None, "ends_before_2026-07-01"
    return q[q["date"] <= LAST_REQUIRED].copy(), None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    out = Path("europe120/output")
    raw = out / "raw_ticker_csv"
    raw.mkdir(parents=True, exist_ok=True)
    selected, rejected, data = [], [], {}
    used_symbols = set()
    original = original_149()

    for cat, spec in CLUSTERS.items():
        pool, seen = [], set()
        qrank = {q: i for i, q in enumerate(spec["queries"])}
        for query in spec["queries"]:
            for r in search_candidates(query):
                if r["symbol"] in seen:
                    continue
                seen.add(r["symbol"])
                if r["symbol"] in original:
                    rejected.append({**r, "macro_category": cat, "reason": "overlap_original149"})
                    continue
                if text_ok(spec, r["name"]):
                    pool.append(r)
            time.sleep(0.15)
        pool.sort(key=lambda r: (qrank.get(r["query"], 999), r["symbol"]))
        print("POOL", cat, len(pool), flush=True)
        chosen = 0
        for r in pool:
            if chosen >= PER_CLUSTER:
                break
            sym = r["symbol"]
            if sym in used_symbols or sym in original:
                continue
            q, reason = download_one(sym)
            if q is None:
                rejected.append({**r, "macro_category": cat, "reason": reason})
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
            chosen += 1
            print("SELECT", cat, chosen, "/", PER_CLUSTER, sym, r["name"], flush=True)
        if chosen != PER_CLUSTER:
            pd.DataFrame(selected).to_csv(out / "partial_selected.csv", index=False)
            pd.DataFrame(rejected).to_csv(out / "partial_rejected.csv", index=False)
            raise RuntimeError(f"quota not met for {cat}: {chosen}/{PER_CLUSTER}; pool={len(pool)}")

    if len(selected) != 120:
        raise RuntimeError(f"expected 120, got {len(selected)}")
    overlap = sorted(set(used_symbols) & original)
    if overlap:
        raise RuntimeError(f"EU120 overlaps original149: {overlap}")

    hashes = {}
    for rec in selected:
        t = rec["ticker"]
        q = data[t].copy()
        q["date"] = q["date"].dt.strftime("%Y-%m-%d")
        p = raw / f"{re.sub(r'[^A-Za-z0-9._-]', '_', t)}.csv"
        q.to_csv(p, index=False, float_format="%.17g")
        hashes[t] = sha256(p)

    pd.DataFrame(selected)[["ticker", "macro_category", "eu_cluster", "name"]].to_csv(raw / "universe.csv", index=False)
    pd.DataFrame(selected).to_csv(out / "coverage.csv", index=False)
    pd.DataFrame(rejected).to_csv(out / "rejected.csv", index=False)
    for fld in ["Open", "High", "Low", "Close", "Volume"]:
        pd.concat([data[t].set_index("date")[[fld]].rename(columns={fld: t}) for t in data], axis=1).sort_index().to_parquet(out / f"{fld.upper()}.parquet")

    manifest = {
        "status": "EUROPE120_DOWNLOADED",
        "provider": "Yahoo Finance via yfinance",
        "requested_start": START,
        "last_included": str(LAST_REQUIRED.date()),
        "price_semantics": "same-row Adj Close/raw Close adjustment for OHLC; raw Volume",
        "evaluation_start": "2017-02-01",
        "selection_rule": "first 20 coverage-valid European-economy ETF tickers, disjoint from original149, in frozen query/symbol order per cluster; no performance criterion",
        "selected_count": 120,
        "per_cluster": 20,
        "intersection_with_original149": overlap,
        "performance_used_for_selection": False,
        "selected": selected,
        "file_sha256": hashes,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: v for k, v in manifest.items() if k not in {"selected", "file_sha256"}}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
