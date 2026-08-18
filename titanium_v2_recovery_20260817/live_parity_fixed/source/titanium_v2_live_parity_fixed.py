#!/usr/bin/env python3
"""Titanium V2 parity-safe historical/as-of runner.

This runner deliberately keeps the recovered official V2 lane separate from the
retrained S3B/Opportunity successor. It never resamples baskets and never
recomputes the authenticated TIT_R ranking for the frozen historical interval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPECTED_SHA256 = {
    "authentic/ORTHOGONAL_SCORE_PANEL.pkl": "57caef7e4b824d0a7c75cea389d7e957b2da23bb0925a15b696ca0bfdaa2af88",
    "authentic/SUPER_GOLD_BASKET_MEMBERSHIP.csv": "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e",
    "frozen_paths/REG_W24_F005_S008_PATHS.npz": "831b426d3a59b7132686555f4591212ddad999e79a1c5c7a118f1bfdd72d166b",
    "frozen_paths/TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz": "7bf8441c66d0256dd3e5897df8f0a2271b00faf0c1d6d5ed9bc2440d614adc54",
}

OFFICIAL_END_DATE = pd.Timestamp("2026-07-01")
OFFICIAL_V2_METRICS = {
    "cagr_mean": 0.2165406437471759,
    "maxdd_mean": -0.339350999208692,
    "sharpe_mean": 0.868077345280489,
}

CATEGORY_TICKERS = {
    "C01_US_BROAD_STYLE": ["DIA", "IJR", "SCHD", "QQQ", "QUAL", "RSP", "DGRO", "IJH", "IWF", "HDV", "MDY", "SCHB", "IWM", "MTUM", "SCHX", "SPY", "IVV", "VTI", "VO", "VB", "VUG", "VTV", "IWD", "IWN", "SPLV"],
    "C02_US_SECTOR_THEME": ["PPA", "SMH", "SOXX", "IGV", "IHI", "KBE", "HACK", "IYT", "KRE", "IBB", "ICLN", "ITA", "FDN", "TAN", "XBI", "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP", "XLU", "XLB", "XRT"],
    "C03_DEVELOPED_GLOBAL": ["ACWI", "EWL", "EWP", "EWA", "EWN", "IEFA", "EFA", "EWH", "EWQ", "EWC", "EWD", "EWJ", "EWG", "EWI", "EWU", "VEA", "VEU", "VGK", "EWK", "EWO", "EIRL", "EIS", "EPOL", "ENZL", "EPP"],
    "C04_EMERGING": ["EWS", "EWY", "FXI", "ASHR", "INDA", "VWO", "EWT", "IEMG", "KWEB", "EEM", "MCHI", "TUR", "AAXJ", "EWZ", "EZA", "EIDO", "EWM", "THD", "EPHE", "SCHE", "DEM", "DGS", "EPI", "PIN", "ARGT"],
    "C05_BONDS_CASH_CREDIT": ["AGG", "BIL", "EMB", "IEF", "IEI", "LQD", "BNDX", "HYG", "MUB", "BND", "JNK", "SCHP", "EDV", "SHY", "TLT", "TIP", "SHV", "VGSH", "VGIT", "VGLT", "VCIT", "VCSH", "MBB", "BKLN", "ANGL"],
    "C06_REAL_ASSETS": ["COMT", "GLD", "SLV", "GSG", "IYR", "PPLT", "CPER", "DBB", "VNQ", "DBC", "GDX", "PALL", "BNO", "DBA", "GDXJ", "IAU", "USO", "UNG", "DBO", "USL", "RWO", "RWX", "WOOD", "CORN", "URA"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def path_metrics(equity: np.ndarray) -> pd.DataFrame:
    returns = np.zeros_like(equity, dtype=float)
    returns[:, 1:] = equity[:, 1:] / equity[:, :-1] - 1.0
    compounded = np.cumprod(1.0 + returns, axis=1)
    cagr = compounded[:, -1] ** (252.0 / returns.shape[1]) - 1.0
    drawdown = compounded / np.maximum.accumulate(compounded, axis=1) - 1.0
    maxdd = drawdown.min(axis=1)
    std = returns.std(axis=1, ddof=1)
    sharpe = np.sqrt(252.0) * returns.mean(axis=1) / np.where(std > 0.0, std, np.nan)
    calmar = cagr / np.maximum(-maxdd, 1e-12)
    return pd.DataFrame({"cagr": cagr, "maxdd": maxdd, "sharpe": sharpe, "calmar": calmar})


def summarize_paths(frozen: np.lib.npyio.NpzFile, final_date: pd.Timestamp) -> pd.DataFrame:
    dates = pd.DatetimeIndex(frozen["dates"])
    mask = np.asarray(dates <= final_date)
    if not mask.any():
        raise ValueError(f"final date {final_date.date()} precedes the frozen path")
    rows = []
    for strategy, key in (("Titanium_V1", "BASE"), ("Titanium_V2", "BALANCED")):
        metric = path_metrics(frozen[key][:, mask])
        rows.append(
            {
                "strategy": strategy,
                "path_start": str(dates[mask].min().date()),
                "path_end": str(dates[mask].max().date()),
                "daily_observations": int(mask.sum()),
                "baskets": int(len(metric)),
                "cagr_mean": float(metric["cagr"].mean()),
                "cagr_median": float(metric["cagr"].median()),
                "maxdd_mean": float(metric["maxdd"].mean()),
                "sharpe_mean": float(metric["sharpe"].mean()),
                "calmar_mean": float(metric["calmar"].mean()),
            }
        )
    return pd.DataFrame(rows)


def basket_structure(membership: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, object]]:
    ticker_category = {ticker: category for category, tickers in CATEGORY_TICKERS.items() for ticker in tickers}
    categorized = membership.assign(category=membership["ticker"].map(ticker_category))
    if categorized["category"].isna().any():
        missing = sorted(categorized.loc[categorized["category"].isna(), "ticker"].unique())
        raise ValueError(f"tickers without static category: {missing}")
    counts = (
        categorized.groupby(["basket", "category"]).size().rename("ticker_count").reset_index()
    )
    matrix = counts.pivot(index="basket", columns="category", values="ticker_count").fillna(0).astype(int)
    expected_columns = sorted(CATEGORY_TICKERS)
    matrix = matrix.reindex(columns=expected_columns, fill_value=0)
    basket_sizes = membership.groupby("basket").size()
    exact = basket_sizes.eq(24) & matrix.eq(4).all(axis=1)
    audit = {
        "basket_count": int(membership["basket"].nunique()),
        "membership_rows": int(len(membership)),
        "unique_tickers": int(membership["ticker"].nunique()),
        "static_categories": expected_columns,
        "required_tickers_per_category": 4,
        "required_tickers_per_basket": 24,
        "baskets_with_exact_4x6_structure": int(exact.sum()),
        "all_baskets_valid": bool(exact.all()),
        "dynamic_s3b_balance_required": False,
    }
    return matrix.reset_index(), audit


def ranked_selections(panel: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    expanded = membership.merge(
        panel[["signal_date", "entry_date", "exit_date", "ticker", "TIT_R"]],
        on="ticker",
        how="inner",
        validate="many_to_many",
    )
    expanded = expanded.sort_values(
        ["signal_date", "basket", "TIT_R", "ticker"],
        ascending=[True, True, False, True],
        kind="mergesort",
    )
    expanded["rank"] = expanded.groupby(["signal_date", "basket"]).cumcount() + 1
    top2 = expanded.loc[expanded["rank"].le(2)].copy()
    wide = top2.pivot(index=["signal_date", "entry_date", "exit_date", "basket"], columns="rank", values=["ticker", "TIT_R"])
    wide.columns = [f"{name}_{int(rank)}" for name, rank in wide.columns]
    wide = wide.reset_index().rename(columns={"ticker_1": "top1", "ticker_2": "top2", "TIT_R_1": "top1_score", "TIT_R_2": "top2_score"})
    wide["margin"] = wide["top1_score"] - wide["top2_score"]
    wide["top1_weight"] = np.where(wide["margin"].ge(0.12), 1.0, 0.75)
    wide["top2_weight"] = 1.0 - wide["top1_weight"]
    return wide.sort_values(["signal_date", "basket"]).reset_index(drop=True)


def selection_parity(panel: pd.DataFrame, selections: pd.DataFrame, reg: np.lib.npyio.NpzFile) -> dict[str, object]:
    dates = pd.DatetimeIndex(sorted(panel["signal_date"].unique()))
    official = reg["BASE_SELECTED"].astype(np.int16)
    if official.shape != (500, len(dates)):
        raise ValueError(f"official selection shape {official.shape} != expected {(500, len(dates))}")
    universe = sorted(set(panel["ticker"]) | {"PIN"})
    if len(universe) != 150:
        raise ValueError(f"expected 150 canonical tickers, found {len(universe)}")
    official_tickers = np.asarray(universe, dtype=object)[official]
    recovered = (
        selections.pivot(index="basket", columns="signal_date", values="top1")
        .reindex(index=range(500), columns=dates)
        .to_numpy(dtype=object)
    )
    equal = official_tickers == recovered
    mismatches = np.argwhere(~equal)
    return {
        "official_selection_shape": [int(v) for v in official.shape],
        "authenticated_signal_dates": int(len(dates)),
        "decision_pairs": int(equal.size),
        "matched_pairs": int(equal.sum()),
        "mismatched_pairs": int((~equal).sum()),
        "agreement": float(equal.mean()),
        "first_mismatch": None if len(mismatches) == 0 else {
            "basket": int(mismatches[0, 0]),
            "signal_date": str(dates[mismatches[0, 1]].date()),
            "official": str(official_tickers[tuple(mismatches[0])]),
            "recovered": str(recovered[tuple(mismatches[0])]),
        },
    }


def unrestricted_signal(panel: pd.DataFrame, signal_date: pd.Timestamp) -> dict[str, object]:
    current = panel.loc[panel["signal_date"].eq(signal_date)].sort_values(
        ["TIT_R", "ticker"], ascending=[False, True], kind="mergesort"
    )
    if len(current) < 2:
        raise ValueError(f"fewer than two authenticated scores on {signal_date.date()}")
    first, second = current.iloc[0], current.iloc[1]
    margin = float(first["TIT_R"] - second["TIT_R"])
    return {
        "mode": "authenticated_historical_asof",
        "signal_date": str(signal_date.date()),
        "entry_date": str(pd.Timestamp(first["entry_date"]).date()),
        "exit_date": str(pd.Timestamp(first["exit_date"]).date()),
        "top1": str(first["ticker"]),
        "top2": str(second["ticker"]),
        "top1_score": float(first["TIT_R"]),
        "top2_score": float(second["TIT_R"]),
        "margin": margin,
        "concentration_threshold": 0.12,
        "top1_weight": 1.0 if margin >= 0.12 else 0.75,
        "top2_weight": 0.0 if margin >= 0.12 else 0.25,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--final-date", default="2026-07-01", help="Frozen path end date, inclusive")
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()

    root = args.package_root.resolve()
    output = (args.output_dir or root / "outputs").resolve()
    output.mkdir(parents=True, exist_ok=True)
    final_date = pd.Timestamp(args.final_date)

    hashes = {relative: sha256(root / relative) for relative in EXPECTED_SHA256}
    hash_ok = {relative: hashes[relative] == expected for relative, expected in EXPECTED_SHA256.items()}
    if not all(hash_ok.values()):
        raise ValueError(f"canonical input hash mismatch: {hash_ok}")

    panel = pd.read_pickle(root / "authentic/ORTHOGONAL_SCORE_PANEL.pkl")
    membership = pd.read_csv(root / "authentic/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    for column in ("signal_date", "entry_date", "exit_date"):
        panel[column] = pd.to_datetime(panel[column], errors="raise")
    panel["ticker"] = panel["ticker"].astype(str).str.upper().str.strip()
    membership["ticker"] = membership["ticker"].astype(str).str.upper().str.strip()
    reg = np.load(root / "frozen_paths/REG_W24_F005_S008_PATHS.npz")
    frozen = np.load(root / "frozen_paths/TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz")
    frozen_dates = pd.DatetimeIndex(frozen["dates"])
    if final_date > frozen_dates.max():
        raise ValueError(
            f"final date {final_date.date()} exceeds authenticated frozen path end "
            f"{frozen_dates.max().date()}; use the successor lane for later dates"
        )

    structure_table, structure_audit = basket_structure(membership)
    if not structure_audit["all_baskets_valid"]:
        raise ValueError("official baskets do not satisfy the required 24 = 6 x 4 structure")
    selections = ranked_selections(panel, membership)
    parity = selection_parity(panel, selections, reg)
    if parity["agreement"] != 1.0:
        raise ValueError(f"selection parity failed: {parity}")

    eligible_signals = panel.loc[panel["exit_date"].le(final_date), "signal_date"]
    if eligible_signals.empty:
        raise ValueError(f"no completed authenticated signal by {final_date.date()}")
    signal_date = pd.Timestamp(eligible_signals.max())
    signal = unrestricted_signal(panel, signal_date)
    scorecard = summarize_paths(frozen, final_date)
    actual_path_end = str(frozen_dates[frozen_dates <= final_date].max().date())
    scorecard_records = scorecard.to_dict(orient="records")
    metric_parity = None
    if final_date == OFFICIAL_END_DATE:
        v2 = scorecard.loc[scorecard["strategy"].eq("Titanium_V2")].iloc[0]
        gaps = {metric: float(v2[metric] - expected) for metric, expected in OFFICIAL_V2_METRICS.items()}
        metric_parity = {
            "reference": OFFICIAL_V2_METRICS,
            "actual": {metric: float(v2[metric]) for metric in OFFICIAL_V2_METRICS},
            "absolute_gaps": {metric: abs(gap) for metric, gap in gaps.items()},
            "tolerance": 1e-12,
            "pass": all(abs(gap) <= 1e-12 for gap in gaps.values()),
        }
        if not metric_parity["pass"]:
            raise ValueError(f"official final metric parity failed: {metric_parity}")

    latest_baskets = selections.loc[selections["signal_date"].eq(signal_date)].copy()
    date_columns = ["signal_date", "entry_date", "exit_date"]
    for column in date_columns:
        latest_baskets[column] = latest_baskets[column].dt.strftime("%Y-%m-%d")
    latest_baskets.to_csv(output / "LATEST_OFFICIAL_BASKET_SIGNALS.csv", index=False)
    structure_table.to_csv(output / "OFFICIAL_BASKET_STATIC_CATEGORY_COUNTS.csv", index=False)
    scorecard.to_csv(output / "OFFICIAL_FROZEN_SCORECARD.csv", index=False)
    (output / "LIVE_SIGNAL_ASOF.json").write_text(json.dumps(signal, indent=2) + "\n", encoding="utf-8")
    (output / "BASKET_STRUCTURE_AUDIT.json").write_text(json.dumps(structure_audit, indent=2) + "\n", encoding="utf-8")

    report = {
        "status": "PASS",
        "parity_final_date_requested": str(final_date.date()),
        "parity_path_end_used": actual_path_end,
        "canonical_inputs_sha256": hashes,
        "canonical_inputs_hash_match": hash_ok,
        "basket_structure": structure_audit,
        "selection_parity": parity,
        "frozen_scorecard": scorecard_records,
        "official_v2_metric_parity": metric_parity,
        "authenticated_panel": {
            "rows": int(len(panel)),
            "tickers": int(panel["ticker"].nunique()),
            "signal_dates": int(panel["signal_date"].nunique()),
            "last_signal_date": str(panel["signal_date"].max().date()),
            "last_exit_date": str(panel["exit_date"].max().date()),
        },
        "latest_unrestricted_signal": signal,
        "policy": {
            "basket_resampling": False,
            "tit_r_retraining_on_frozen_interval": False,
            "dynamic_s3b_used_by_titanium_v2_base": False,
            "successor_s3b_opportunity_lane_is_separate": True,
        },
    }
    (output / "PARITY_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
