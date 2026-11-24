"""Load the frozen market panels and archived cluster assignments."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd

MARKETS = ("EU", "USA", "TR")
BENCHMARK = dict(EU="SXR8.DE", USA="SPY", TR="IE00B5BMR087")
MARKET_ARCHIVE = "PERSEO_UNIFICATO_RICONCILIAZIONE_20261121.zip"
TR_ARCHIVE = "PERSEO_U19_DATI_COMPLETI.zip"
LEGACY_ARCHIVE = "OLC07_Calendario_Risultati_20261101.zip"


def locate(root, name):
    hits = list(root.rglob(name))
    if len(hits) != 1:
        raise FileNotFoundError(f"Expected one {name} under {root}, found {hits}")
    return hits[0]


def stored_arrays(archive, suffix):
    with ZipFile(archive) as zf:
        member, = [name for name in zf.namelist() if name.endswith(suffix)]
        with np.load(BytesIO(zf.read(member))) as data:
            return {key: data[key] for key in data.files}


def stored_csv(archive, suffix):
    with ZipFile(archive) as zf:
        member, = [name for name in zf.namelist() if name.endswith(suffix)]
        with zf.open(member) as content:
            return pd.read_csv(content)


@dataclass
class MarketPanel:
    name: str
    dates: pd.DatetimeIndex
    tickers: np.ndarray
    close: np.ndarray
    opening: np.ndarray
    observed: np.ndarray
    open_observed: np.ndarray
    volume: np.ndarray | None
    eligible: np.ndarray
    benchmark: int
    open_mark: np.ndarray
    observation_source: str
    history_usable: np.ndarray | None = None


def make_market(name, arrays, universe=None):
    dates = pd.DatetimeIndex(arrays["dates"])
    tickers = arrays.get("tickers", arrays.get("names"))
    assert dates.is_unique and dates.is_monotonic_increasing
    assert len(set(tickers)) == len(tickers)
    close, opening = arrays["C"], arrays["O"]
    positive_close = np.isfinite(close) & (close > 0)
    positive_open = np.isfinite(opening) & (opening > 0)
    observed = arrays.get("low_observed", arrays.get("observed", positive_close)) & positive_close
    open_observed = arrays.get("open_observed", arrays.get("observed", positive_open)) & positive_open
    open_mark = pd.DataFrame(opening).where(open_observed).combine_first(
        pd.DataFrame(close).where(observed).ffill().shift(1)
    ).ffill().to_numpy()
    eligible = np.array(["CASH_" not in ticker and (universe is None or ticker in universe)
                         for ticker in tickers])
    label = "ARCHIVED_MASKS" if "observed" in arrays else "FINITE_POSITIVE_FROZEN_PRICE"
    return MarketPanel(name, dates, tickers, close, opening, observed, open_observed, arrays.get("V"),
                       eligible, list(tickers).index(BENCHMARK[name]), open_mark, label)


def archived_members(csv, market):
    csv = csv.copy()
    csv["signal_date"] = pd.to_datetime(csv["signal_date"])
    lookup = {ticker: index for index, ticker in enumerate(market.tickers)}
    matched = csv[csv.ticker.isin(lookup)].copy()
    assert not matched.duplicated(["signal_date", "ticker"]).any()
    matched["index"] = matched.ticker.map(lookup)
    snapshots = {dt: g.groupby("cluster_id")["index"].agg(list).to_dict()
                 for dt, g in matched.groupby("signal_date", sort=True)}
    return pd.DatetimeIndex(snapshots), snapshots


def load_inputs(root):
    old = locate(root, MARKET_ARCHIVE)
    tr = locate(root, TR_ARCHIVE)
    past = locate(root, LEGACY_ARCHIVE)
    taxonomy_path = locate(root, "EU165_ECONOMIC_TAXONOMY.csv")
    allowed = stored_csv(tr, "data/TR1846_CLASSIFICATION.csv")
    allowed = set(allowed.loc[allowed.tradable.eq(True), "isin"])
    marts = {}
    for market, suffix in (("EU", "EU165_ORIGINAL_STATE.npz"), ("USA", "USA149_ORIGINAL_STATE.npz")):
        marts[market] = make_market(market, stored_arrays(old, suffix))
    marts["TR"] = make_market("TR", stored_arrays(tr, "data/TR1846_OHLCV.npz"), allowed)
    members = {
        market: archived_members(stored_csv(past, f"P0/results/calendar/{market}_CLUSTERS.csv"), marts[market])
        for market in ("EU", "USA")
    }
    tr_csv = stored_csv(tr, "data/TR_CLUSTERS.csv")
    sources = stored_csv(tr, "data/TR_CLUSTER_AUDIT.csv")
    sources["signal_date"] = pd.to_datetime(sources["signal_date"])
    for col in ("anchor_date", "last_input"):
        assert (pd.to_datetime(sources[col]) <= sources.signal_date).all()
    assert set(pd.to_datetime(tr_csv.signal_date)).issubset(sources.signal_date)
    members["TR"] = archived_members(tr_csv, marts["TR"])
    taxonomy = pd.read_csv(taxonomy_path)
    assert not taxonomy.ticker.duplicated().any()
    econ_groups = {}
    for group, rows in taxonomy.groupby("economic_group"):
        econ_groups[group] = np.flatnonzero(np.isin(marts["EU"].tickers, rows.ticker))
    return marts, members, econ_groups, (old, tr, past, taxonomy_path)
