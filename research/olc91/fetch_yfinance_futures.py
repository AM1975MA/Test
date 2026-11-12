#!/usr/bin/env python3
"""OLC91: download di futures Yahoo Finance per i cluster ETF (solo ricerca).

NON usare queste serie continue per simulare il roll dei fondi o come archivio PIT.
I CSV vengono salvati come artifact di GitHub Actions, MAI committati.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import yfinance as yf


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def symbols_from_catalog(path: Path) -> tuple[list[str], dict[str, list[str]]]:
    by_symbol: dict[str, set[str]] = {}
    with path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            for symbol in (row.get("yahoo_tickers") or "").split(";"):
                symbol = symbol.strip()
                if symbol:
                    by_symbol.setdefault(symbol, set()).add(row.get("cluster", "").strip())
    if not by_symbol:
        raise ValueError("Il catalogo non contiene futures Yahoo validi")
    return sorted(by_symbol), {s: sorted(clusters) for s, clusters in by_symbol.items()}


def normalize_prices(history: pd.DataFrame, start: str, end: str):
    if isinstance(history.columns, pd.MultiIndex):
        history = history.copy()
        history.columns = [str(c[0]) for c in history.columns]
    if not isinstance(history.index, pd.DatetimeIndex):
        raise ValueError("Il risultato Yahoo non ha un indice temporale")
    # Conserva il giorno locale della borsa; NON convertire a UTC prima di estrarre date.
    dates = pd.to_datetime(history.index.tz_localize(None)).date
    data = pd.DataFrame({"date": [str(d) for d in dates]})
    for name, source in (
        ("open", "Open"), ("high", "High"), ("low", "Low"),
        ("close", "Close"), ("adj_close", "Adj Close"), ("volume", "Volume")
    ):
        data[name] = pd.to_numeric(history[source], errors="coerce").to_numpy() if source in history else float("nan")
    data = data[(data["date"] >= start) & (data["date"] < end)]
    data = data.sort_values("date")
    duplicates = int(data["date"].duplicated().sum())
    if duplicates:
        data = data.drop_duplicates("date", keep="last")
    data = data.reset_index(drop=True)
    if len(data) and data["date"].isna().any():
        raise ValueError("Date non valide")
    return data, duplicates


def download_one(symbol: str, start: str, end: str, tries: int = 3):
    error = None
    for attempt in range(1, tries + 1):
        try:
            frame = yf.Ticker(symbol).history(
                start=start, end=end, interval="1d",
                auto_adjust=False, actions=False, repair=False
            )
            if frame is None or frame.empty:
                raise ValueError("Yahoo ha restituito uno storico vuoto")
            result, duplicates = normalize_prices(frame, start, end)
            if result.empty or result["close"].notna().sum() == 0:
                raise ValueError("Nessun prezzo di chiusura valido")
            return result, duplicates
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            print(f"{symbol}: tentativo {attempt}/{tries} fallito: {error}", flush=True)
            if attempt < tries:
                time.sleep(4 * attempt)
    raise RuntimeError(error)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", default="research/olc91/cluster_catalog.csv")
    parser.add_argument("--out", default="research/olc91/output")
    parser.add_argument("--start", default="2018-01-01")
    parser.add_argument("--end-exclusive", default=None)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    end = args.end_exclusive or (utc_now().date() + timedelta(days=1)).isoformat()
    start = args.start
    if not start < end:
        parser.error("--start deve precedere --end-exclusive")
    symbols, clusters = symbols_from_catalog(Path(args.catalog))
    if args.check_only:
        print(json.dumps({"status": "CHECK_ONLY", "symbols": symbols, "start": start, "end_exclusive": end}, indent=2))
        return 0

    out = Path(args.out)
    raw = out / "daily"
    raw.mkdir(parents=True, exist_ok=True)
    info = {
        "schema_version": 1,
        "created_utc": utc_now().isoformat(),
        "provider": "Yahoo Finance via yfinance",
        "yfinance_version": getattr(yf, "__version__", "unknown"),
        "pandas_version": pd.__version__,
        "start": start,
        "end_exclusive": end,
        "symbols_requested": symbols,
        "warnings": [
            "Le serie continue futures cambiano ai roll e possono essere riscritte dal provider",
            "Le date dei CSV non certificano la disponibilita' point-in-time storica",
            "Questi prezzi non rappresentano i rendimenti degli ETF o le regole di roll dei fondi",
            "Il WTI ha avuto prezzi futures negativi: non rimuoverli automaticamente",
            "Prima del backtest controllare buchi, roll discontinuities e disponibilita' al segnale",
        ],
        "records": [],
    }
    (out / "cluster_catalog.csv").write_bytes(Path(args.catalog).read_bytes())
    for symbol in symbols:
        record = {"ticker": symbol, "clusters": clusters[symbol]}
        try:
            data, dup = download_one(symbol, start, end)
            filename = re.sub(r"[^A-Za-z0-9_-]", "_", symbol) + ".csv"
            path = raw / filename
            data.to_csv(path, index=False, float_format="%.17g")
            yearly = data.groupby(data["date"].str[:4]).size().to_dict()
            non_null = data["close"].dropna()
            record.update(
                status="DOWNLOADED_NOT_PIT_VERIFIED",
                first_date=data["date"].iloc[0],
                last_date=data["date"].iloc[-1],
                n_rows=int(len(data)),
                year_counts={str(k): int(v) for k, v in yearly.items()},
                duplicates_removed=dup,
                missing_close=int(data["close"].isna().sum()),
                negative_close=int((non_null < 0).sum()),
                zero_close=int((non_null == 0).sum()),
                file=f"daily/{filename}",
                sha256=sha256(path),
            )
        except Exception as exc:
            record.update(status="ERROR", error=f"{type(exc).__name__}: {exc}")
        info["records"].append(record)
        print(f"{symbol:8s}: {record['status']} {record.get('n_rows', 0)} righe", flush=True)

    success = sum(r["status"].startswith("DOWNLOADED") for r in info["records"])
    info["status"] = "COMPLETE" if success == len(symbols) else ("PARTIAL" if success else "FAILED")
    info["n_downloaded"] = success
    info["n_failed"] = len(symbols) - success
    (out / "manifest.json").write_text(
        json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (out / "coverage.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ("ticker", "status", "first_date", "last_date", "n_rows",
                  "missing_close", "negative_close", "duplicates_removed", "sha256", "file", "error")
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(info["records"])
    checksums = [f"{r['sha256']}  {r['file']}" for r in info["records"] if "sha256" in r]
    (out / "SHA256SUMS.txt").write_text("\n".join(checksums) + "\n", encoding="utf-8")
    print(f"ESITO OLC91: {info['status']} ({success}/{len(symbols)} ticker); artifact in {out}", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
