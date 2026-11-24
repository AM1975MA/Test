"""Freeze just the historical ticker and cluster forecasts needed for the test."""

import argparse
from hashlib import file_digest
import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

HERE = Path(__file__).resolve().parent
TICKER_COL = "TOP2_CONTEXT_REVALUE_FUSION"
SOURCES = ("OLC104_CAMPAGNA_COMPLETA_20261114.zip", "OLC07_Calendario_Risultati_20261101.zip")


def locate(base, name):
    paths = list(base.rglob(name))
    if len(paths) != 1:
        raise FileNotFoundError(f"Expected one {name}, found {paths}")
    return paths[0]


def from_archive(archive, suffix, columns, dates):
    with ZipFile(archive) as source:
        member, = [name for name in source.namelist() if name.endswith(suffix)]
        with source.open(member) as content:
            return pd.read_csv(content, usecols=columns, parse_dates=dates,
                               compression="gzip" if suffix.endswith(".gz") else None,
                               float_precision="round_trip")


def digest(path):
    with path.open("rb") as stream:
        return file_digest(stream, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--archives", required=True, type=Path)
    p.add_argument("--cluster-results", type=Path, default=HERE.parent / "cluster_only" / "results")
    p.add_argument("--output", type=Path, default=HERE / "inputs")
    args = p.parse_args()
    args.output.mkdir(exist_ok=True, parents=True)
    ticker_source, membership_source = [locate(args.archives, name) for name in SOURCES]
    source_paths = [ticker_source, membership_source]
    tickers = from_archive(ticker_source, "USA149_ORIGINAL_SCORES.csv.gz",
                           ["signal_date", "ticker", TICKER_COL], ["signal_date"])
    members = from_archive(membership_source, "P0/results/calendar/USA_CLUSTERS.csv",
                           ["signal_date", "ticker", "cluster_id"], ["signal_date"])
    tickers = tickers.rename(columns={TICKER_COL: "native_score"}).dropna(subset=["native_score"])
    assert not tickers.duplicated(["signal_date", "ticker"]).any()
    assert not members.duplicated(["signal_date", "ticker"]).any()
    variants = []
    for label, folder in (("RESTORED", args.cluster_results / "outage_sensitivity"),
                          ("ORIGINAL", args.cluster_results)):
        forecast_file = folder / "SCORED_CLUSTERS.csv.gz"
        fit_file = folder / "FIT_CUTOFFS.csv"
        source_paths.extend([forecast_file, fit_file])
        panel = pd.read_csv(forecast_file, usecols=["family", "market", "day", "close_cutoff",
                                                   "member_cutoff", "cluster", "RIDGE", "MOM21"])
        fits = pd.read_csv(fit_file, usecols=["family", "day", "latest_label"])
        usa = panel.query("family == 'LEGACY' and market == 'USA'").copy()
        fit_legacy = fits.query("family == 'LEGACY'").drop(columns="family")
        usa = usa.merge(fit_legacy, on="day", validate="many_to_one")
        assert (usa.groupby("day").cluster.nunique() == 8).all() and usa.day.nunique() == 57
        assert (usa.member_cutoff <= usa.close_cutoff).all()
        assert (usa.close_cutoff < usa.day).all() and (usa.latest_label < usa.day).all()
        variants.append(usa.drop(columns=["family", "market"]).assign(source=label))
    predictions = pd.concat(variants, ignore_index=True)
    needed = set(pd.to_datetime(predictions.member_cutoff))
    tickers = tickers[tickers.signal_date.isin(set(pd.to_datetime(predictions.close_cutoff)))]
    members = members[members.signal_date.isin(needed)]
    assert len(needed) == members.signal_date.nunique() == tickers.signal_date.nunique() == 57
    for name, frame in (("TICKER_SCORES", tickers), ("GROUP_MEMBERS", members),
                        ("GROUP_PREDICTIONS", predictions)):
        frame.to_csv(args.output / f"{name}.csv", index=False)
    manifest = {str(f.relative_to(args.cluster_results)) if f.is_relative_to(args.cluster_results)
                else f.name: digest(f) for f in source_paths}
    (args.output / "SOURCE_HASHES.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("FROZEN_INPUTS", len(tickers), len(members), len(predictions), flush=True)


if __name__ == "__main__":
    main()
