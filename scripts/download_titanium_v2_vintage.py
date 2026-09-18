#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf
from curl_cffi import requests as curl_requests

START = "2005-01-01"
END_EXCLUSIVE = "2026-08-03"
OUT = Path("data/source_snapshots/titanium_v2_yahoo_20260802")

CATEGORY_TICKERS = {
    "C01_US_BROAD_STYLE": ['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
    "C02_US_SECTOR_THEME": ['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
    "C03_DEVELOPED_GLOBAL": ['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
    "C04_EMERGING": ['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','PIN','ARGT'],
    "C05_BONDS_CASH_CREDIT": ['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
    "C06_REAL_ASSETS": ['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA'],
}
ALL_TICKERS = [t for xs in CATEGORY_TICKERS.values() for t in xs]
TICKER_CATEGORY = {t: c for c, xs in CATEGORY_TICKERS.items() for t in xs}
FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download_batch(batch: list[str]) -> pd.DataFrame:
    last = None
    for attempt in range(6):
        try:
            raw = yf.download(
                batch,
                start=START,
                end=END_EXCLUSIVE,
                auto_adjust=True,
                group_by="column",
                progress=False,
                threads=True,
                timeout=45,
            )
            if raw is None or raw.empty:
                raise RuntimeError("empty yfinance result")
            return raw
        except Exception as exc:
            last = exc
            time.sleep(min(30, 2 ** attempt))
    raise RuntimeError(f"batch failed after retries: {batch}: {last!r}")


def yahoo_chart_fallback(ticker: str) -> pd.DataFrame:
    p1 = int(pd.Timestamp(START, tz="UTC").timestamp())
    p2 = int(pd.Timestamp(END_EXCLUSIVE, tz="UTC").timestamp())
    params = {
        "period1": p1,
        "period2": p2,
        "interval": "1d",
        "events": "div,splits,capitalGains",
        "includeAdjustedClose": "true",
    }
    errors = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{ticker}"
        try:
            r = curl_requests.get(url, params=params, impersonate="chrome", timeout=30)
            if r.status_code != 200:
                errors.append(f"{host}: HTTP {r.status_code}")
                continue
            payload = r.json()["chart"]
            if payload.get("error"):
                errors.append(f"{host}: {payload['error']}")
                continue
            result = payload.get("result") or []
            if not result:
                errors.append(f"{host}: empty result")
                continue
            z = result[0]
            ts = z.get("timestamp") or []
            quote = ((z.get("indicators") or {}).get("quote") or [{}])[0]
            adj_block = ((z.get("indicators") or {}).get("adjclose") or [{}])[0]
            raw_close = pd.Series(quote.get("close") or [], dtype="float64")
            adj_close = pd.Series(adj_block.get("adjclose") or quote.get("close") or [], dtype="float64")
            if len(ts) == 0 or len(raw_close) != len(ts):
                errors.append(f"{host}: malformed result")
                continue
            factor = adj_close.div(raw_close.replace(0, pd.NA))
            idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert(None)
            out = pd.DataFrame(index=idx)
            for src, dst in (("open","Open"),("high","High"),("low","Low")):
                vals = pd.Series(quote.get(src) or [], dtype="float64")
                out[dst] = vals.to_numpy() * factor.to_numpy()
            out["Close"] = adj_close.to_numpy()
            out["Volume"] = pd.to_numeric(pd.Series(quote.get("volume") or []), errors="coerce").to_numpy()
            out = out[~out.index.duplicated(keep="last")].sort_index()
            if out["Close"].notna().sum() >= 252:
                return out
            errors.append(f"{host}: only {int(out['Close'].notna().sum())} closes")
        except Exception as exc:
            errors.append(f"{host}: {exc!r}")
    raise RuntimeError(f"Yahoo chart fallback failed for {ticker}: {errors}")


def field_frame(raw: pd.DataFrame, field: str, batch: list[str]) -> pd.DataFrame:
    if isinstance(raw.columns, pd.MultiIndex):
        if field not in raw.columns.get_level_values(0):
            return pd.DataFrame(index=raw.index)
        x = raw[field].copy()
    else:
        x = raw[[field]].rename(columns={field: batch[0]})
    x.columns = [str(c).upper() for c in x.columns]
    return x


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    frames = {f: [] for f in FIELDS}
    logs: list[dict] = []

    for i in range(0, len(ALL_TICKERS), 25):
        batch = ALL_TICKERS[i:i+25]
        raw = download_batch(batch)
        extracted = {f: field_frame(raw, f, batch) for f in FIELDS}
        for t in batch:
            n = int(extracted["Close"][t].notna().sum()) if t in extracted["Close"] else 0
            source = "yfinance"
            if n < 252:
                fb = yahoo_chart_fallback(t)
                union = extracted["Close"].index.union(fb.index).sort_values()
                for fld in FIELDS:
                    extracted[fld] = extracted[fld].reindex(union)
                    extracted[fld][t] = fb[fld].reindex(union)
                n = int(extracted["Close"][t].notna().sum())
                source = "yahoo_chart_fallback"
            logs.append({"ticker": t, "rows_close": n, "ok": n >= 252, "source": source})
        for f in FIELDS:
            frames[f].append(extracted[f])

    mats = {}
    for f in FIELDS:
        x = pd.concat(frames[f], axis=1)
        x = x.loc[:, ~x.columns.duplicated()].sort_index()
        x.index = pd.to_datetime(x.index).tz_localize(None)
        mats[f] = x.apply(pd.to_numeric, errors="coerce")

    common = sorted(set.intersection(*(set(x.columns) for x in mats.values())))
    if set(common) != set(ALL_TICKERS):
        missing = sorted(set(ALL_TICKERS) - set(common))
        extra = sorted(set(common) - set(ALL_TICKERS))
        raise RuntimeError(f"ticker coverage mismatch missing={missing} extra={extra}")

    for f in FIELDS:
        mats[f] = mats[f].reindex(columns=ALL_TICKERS)

    bad = [r for r in logs if not r["ok"]]
    if bad:
        raise RuntimeError(f"insufficient history for ticker(s): {bad}")

    long_parts = []
    for t in ALL_TICKERS:
        g = pd.DataFrame({
            "date": mats["Close"].index,
            "ticker": t,
            "Open": mats["Open"][t].to_numpy(),
            "High": mats["High"][t].to_numpy(),
            "Low": mats["Low"][t].to_numpy(),
            "Close": mats["Close"][t].to_numpy(),
            "Volume": mats["Volume"][t].to_numpy(),
        })
        g = g.dropna(subset=["Open", "High", "Low", "Close"], how="all")
        g["macro_category"] = TICKER_CATEGORY[t]
        long_parts.append(g)

    long = pd.concat(long_parts, ignore_index=True)
    if long.duplicated(["date", "ticker"]).any():
        raise RuntimeError("duplicate date/ticker rows")

    csv_path = OUT / "DAILY_OHLCV_150ETF.csv"
    zip_path = OUT / "METEOR_TITANIUM_OHLCV_150ETF_20260802.zip"
    log_path = OUT / "DOWNLOAD_LOG.csv"
    universe_path = OUT / "universe.csv"
    manifest_path = OUT / "MANIFEST.json"

    long.to_csv(csv_path, index=False, float_format="%.17g")
    pd.DataFrame(logs).to_csv(log_path, index=False)
    pd.DataFrame(
        [{"ticker": t, "macro_category": TICKER_CATEGORY[t]} for t in ALL_TICKERS]
    ).to_csv(universe_path, index=False)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        z.write(csv_path, arcname=csv_path.name)

    manifest = {
        "provider": "Yahoo Finance through yfinance; direct Yahoo chart fallback when yfinance returns insufficient history",
        "auto_adjust": True,
        "start": START,
        "end_exclusive": END_EXCLUSIVE,
        "intended_last_session": "2026-07-31",
        "universe_tickers": len(ALL_TICKERS),
        "rows": int(len(long)),
        "date_min": str(pd.to_datetime(long["date"]).min().date()),
        "date_max": str(pd.to_datetime(long["date"]).max().date()),
        "archive": zip_path.name,
        "archive_sha256": sha256(zip_path),
        "archive_size_bytes": zip_path.stat().st_size,
        "download_log_sha256": sha256(log_path),
        "universe_sha256": sha256(universe_path),
        "source_code": "scripts/download_titanium_v2_vintage.py",
        "notes": "Redownload of the Titanium V2 Yahoo/yfinance universe at the original fixed vintage; direct Yahoo chart fallback is used only when yfinance returns insufficient history. Vendor historical revisions may differ from previously frozen parquet bytes.",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    csv_path.unlink()
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
