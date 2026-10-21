from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

FIELDS=("Open","High","Low","Close","Volume")


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()


def load_ticker_csv_folder(folder: str | Path):
    """Load only raw per-ticker CSVs plus universe metadata.

    Required:
      universe.csv with ticker,macro_category
      <TICKER>.csv with date,Open,High,Low,Close,Volume

    No score, gate, selection, path or historical model artifact is accepted.
    """
    folder=Path(folder)
    meta=pd.read_csv(folder/"universe.csv")
    required={"ticker","macro_category"}
    if not required.issubset(meta.columns):
        raise ValueError(f"universe.csv missing {required-set(meta.columns)}")
    meta=meta[list(required)].drop_duplicates().sort_values("ticker")
    if meta.ticker.duplicated().any():
        raise ValueError("duplicate ticker in universe.csv")
    cats=dict(zip(meta.ticker.astype(str).str.upper(),meta.macro_category.astype(str)))
    tables={}
    file_manifest={}
    for ticker in cats:
        path=folder/f"{ticker}.csv"
        if not path.is_file():
            raise FileNotFoundError(path)
        x=pd.read_csv(path,parse_dates=["date"],float_precision="round_trip").sort_values("date")
        if x.date.duplicated().any():
            raise ValueError(f"duplicate dates {ticker}")
        missing=set(FIELDS)-set(x.columns)
        if missing:
            raise ValueError(f"{ticker} missing {missing}")
        x=x.set_index("date")[list(FIELDS)].apply(pd.to_numeric,errors="coerce")
        if not x.index.is_monotonic_increasing or not x.index.is_unique:
            raise ValueError(f"bad calendar {ticker}")
        if not np.isfinite(x.to_numpy(float)).all():
            raise ValueError(f"non-finite raw values {ticker}")
        if (x[["Open","High","Low","Close"]]<=0).any().any() or (x["Volume"]<0).any():
            raise ValueError(f"invalid price/volume {ticker}")
        bad=(x.Low>x[["Open","Close"]].min(axis=1)+1e-8)|(x.High<x[["Open","Close"]].max(axis=1)-1e-8)
        if bad.any():
            raise ValueError(f"OHLC incoherent {ticker}: {int(bad.sum())}")
        tables[ticker]=x
        file_manifest[ticker]={"sha256":sha256(path),"rows":len(x),
                               "start":str(x.index.min().date()),"end":str(x.index.max().date())}
    mats={f:pd.concat({t:x[f] for t,x in tables.items()},axis=1).sort_index() for f in FIELDS}
    return mats,cats,{"tickers":len(cats),"files":file_manifest}


def load_baskets(path: str | Path, valid_tickers):
    m=pd.read_csv(path)
    if not {"basket","ticker"}.issubset(m.columns):
        raise ValueError("basket file requires basket,ticker")
    m["ticker"]=m.ticker.astype(str).str.upper()
    if (~m.ticker.isin(set(valid_tickers))).any():
        bad=sorted(m.loc[~m.ticker.isin(set(valid_tickers)),"ticker"].unique())
        raise ValueError(f"basket contains unavailable ticker(s): {bad[:20]}")
    sizes=m.groupby("basket").size()
    if not sizes.eq(sizes.iloc[0]).all():
        raise ValueError("basket sizes are not constant")
    return [list(g.ticker) for _,g in m.sort_values(["basket","ticker"]).groupby("basket",sort=True)]
