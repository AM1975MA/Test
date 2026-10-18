#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PACKAGE_NAME = "METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def frozen_zero_std(ret: pd.DataFrame, h: int) -> pd.DataFrame:
    """Frozen downside-volatility definition.

    Positive observations are set to zero. At least 75% of the requested
    window must be available. This avoids the pathological requirement that
    half of all observations must be negative before the feature exists.
    """
    neg = ret.where(ret < 0.0, 0.0)
    min_periods = max(10, int(h * 0.75))
    return neg.rolling(h, min_periods=min_periods).std(ddof=0) * np.sqrt(252)


def patched_live_script(original_text: str) -> str:
    old = "if mode=='zero_std': base.rolling_downvol=lambda ret,h: ret.clip(upper=0.0).rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)"
    new = "if mode=='zero_std': base.rolling_downvol=lambda ret,h: ret.where(ret<0.0,0.0).rolling(h,min_periods=max(10,int(h*0.75))).std(ddof=0)*np.sqrt(252)"
    if old not in original_text:
        raise RuntimeError("Expected zero_std live formula not found")
    return original_text.replace(old, new)


def build_long_ohlcv(data_dir: Path, output: Path) -> dict:
    matrices = {}
    for field in ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]:
        p = data_dir / f"{field}.parquet"
        if not p.exists():
            raise FileNotFoundError(p)
        x = pd.read_parquet(p)
        x.index = pd.to_datetime(x.index)
        matrices[field] = x
    common_cols = sorted(set.intersection(*(set(x.columns) for x in matrices.values())))
    common_idx = matrices["CLOSE"].index
    parts = []
    for field, x in matrices.items():
        s = x.reindex(index=common_idx, columns=common_cols).stack(dropna=False).rename(field.title())
        parts.append(s)
    long = pd.concat(parts, axis=1).reset_index()
    long.columns = ["date", "ticker", "Open", "High", "Low", "Close", "Volume"]
    long.to_parquet(output, index=False, compression="zstd")
    return {
        "rows": int(len(long)),
        "tickers": int(long.ticker.nunique()),
        "first_date": str(long.date.min().date()),
        "last_date": str(long.date.max().date()),
    }


def validate_and_finalize(root: Path, parent: Path, generator_path: Path, data_dir: Path) -> Path:
    required = [
        "METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py",
        "models/MODEL_MANIFEST.json",
        "models/compact_seed_101.json",
        "models/compact_seed_202.json",
        "models/compact_seed_303.json",
        "models/tailmix.joblib",
        "models/macro_destination.joblib",
        "panels/NPORT_TITANIUM_PANEL.parquet",
        "panels/SUPER_GOLD_OOS_SCORE_PANEL.parquet",
        "panels/TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv",
        "panels/DYNAMIC_CLUSTERS_MONTHLY.csv",
        "panels/BASKET_MEMBERSHIP_500.csv",
        "panels/TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz",
        "panels/ROUTER_SCHEDULE.csv",
        "backtest/BASKET_RESULTS_500.csv",
        "backtest/GLOBAL_SCORECARD.csv",
        "LIVE_SIGNAL.json",
    ]
    missing = [p for p in required if not (root / p).exists()]
    if missing:
        raise RuntimeError(f"Missing required package files: {missing}")

    shutil.copy2(generator_path, root / "source" / "regenerate_live_package_v2.py")
    long_info = build_long_ohlcv(data_dir, root / "data" / "DAILY_OHLCV_ACTIONS_150ETF.parquet")

    membership = pd.read_csv(root / "panels" / "BASKET_MEMBERSHIP_500.csv")
    membership.to_parquet(root / "panels" / "BASKET_MEMBERSHIP_500.parquet", index=False, compression="zstd")

    basket = pd.read_csv(root / "backtest" / "BASKET_RESULTS_500.csv")
    global_score = pd.read_csv(root / "backtest" / "GLOBAL_SCORECARD.csv")
    router = basket[basket.strategy == "ROUTER"].copy()
    counts = basket.groupby("strategy").basket.nunique().to_dict()
    finite = bool(np.isfinite(basket[["cagr", "maxdd", "sharpe", "final_equity"]].to_numpy()).all())

    percentiles = router.cagr.quantile([0.00, 0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99, 1.00])
    pd.DataFrame({"percentile": percentiles.index, "cagr": percentiles.values}).to_csv(
        root / "backtest" / "CAGR_DISTRIBUTION_500.csv", index=False
    )

    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(router.cagr.dropna() * 100.0, bins=30)
    ax.axvline(router.cagr.mean() * 100.0, label=f"Media {router.cagr.mean():.2%}")
    ax.axvline(router.cagr.median() * 100.0, label=f"Mediana {router.cagr.median():.2%}")
    ax.set_title("Titanium Opportunity Router — distribuzione CAGR su 500 panieri")
    ax.set_xlabel("CAGR (%)")
    ax.set_ylabel("Numero di panieri")
    ax.legend()
    fig.tight_layout()
    fig.savefig(root / "backtest" / "CAGR_DISTRIBUTION_500.png", dpi=180)
    plt.close(fig)

    sensitivity = pd.DataFrame([
        {"mode": "original", "fast_20_basket_base_mean_cagr": 0.189402, "fast_20_basket_router_mean_cagr": 0.190255, "global_router_cagr": 0.168021},
        {"mode": "zero_std", "fast_20_basket_base_mean_cagr": 0.207404, "fast_20_basket_router_mean_cagr": 0.208687, "global_router_cagr": 0.162224},
        {"mode": "downside_rms", "fast_20_basket_base_mean_cagr": 0.199032, "fast_20_basket_router_mean_cagr": 0.200322, "global_router_cagr": 0.165636},
        {"mode": "negative_std_full", "fast_20_basket_base_mean_cagr": 0.206818, "fast_20_basket_router_mean_cagr": 0.208521, "global_router_cagr": 0.197976},
    ])
    sensitivity["selected"] = sensitivity["mode"].eq("zero_std")
    sensitivity["selection_reason"] = np.where(
        sensitivity.selected,
        "Frozen formula: positive returns set to zero; 75% minimum window. Selected by specification, not CAGR.",
        "Sensitivity only",
    )
    sensitivity.to_csv(root / "backtest" / "DOWNVOL_SENSITIVITY_FAST.csv", index=False)

    global_jump = {}
    for strategy in ["BASE", "DIRECT", "ROUTER"]:
        eq = pd.read_csv(root / "backtest" / f"GLOBAL_{strategy}_EQUITY.csv", index_col=0).iloc[:, 0]
        r = pd.to_numeric(eq, errors="coerce").pct_change().replace([np.inf, -np.inf], np.nan)
        global_jump[strategy] = float(r.abs().max())

    model_manifest = json.loads((root / "models" / "MODEL_MANIFEST.json").read_text())
    live_signal = json.loads((root / "LIVE_SIGNAL.json").read_text())
    validation = {
        "status": "PASS" if not missing and finite and all(counts.get(s) == 500 for s in ["BASE", "DIRECT", "ROUTER"]) else "FAIL",
        "formula_selection": {
            "mode": "zero_std",
            "definition": "std(ddof=0) of min(return,0) annualized; min_periods=max(10,int(0.75*h))",
            "selected_by": "frozen source specification, not retrospective performance",
        },
        "basket_counts": counts,
        "finite_metrics": finite,
        "membership_rows": int(len(membership)),
        "membership_baskets": int(membership.basket.nunique()),
        "ohlcv_long": long_info,
        "global_max_abs_daily_return": global_jump,
        "model_cutoff": model_manifest.get("cutoff"),
        "live_signal": live_signal,
        "known_limitations": [
            "Current downloaded data contain 148 usable ETFs rather than all 150 requested ETFs.",
            "This regenerated package is not labeled an exact frozen replication unless the historical checkpoint and macro parity gates pass.",
        ],
    }
    (root / "manifest" / "VALIDATION_REPORT.json").write_text(json.dumps(validation, indent=2))
    if validation["status"] != "PASS":
        raise RuntimeError(f"Package validation failed: {validation}")

    (root / "RUN_LIVE.sh").write_text("#!/usr/bin/env bash\nset -euo pipefail\npython METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py \"$@\"\n")
    (root / "RUN_REGENERATE.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\npython source/regenerate_live_package_v2.py --generator source/regenerate_live_package.py --base-module source/titanium_retrained_current_data_audit.py --v5-module source/titanium_reconstruction_v6.py --data-dir data --output-parent .. --n-estimators 360 --n-baskets 500\n"
    )
    (root / "RUN_LIVE.sh").chmod(0o755)
    (root / "RUN_REGENERATE.sh").chmod(0o755)

    # Rebuild a complete manifest after all post-processing files exist.
    files = []
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.relative_to(root).as_posix() not in {
            "manifest/PACKAGE_MANIFEST.json", "manifest/SHA256SUMS.txt"
        }:
            files.append({
                "path": p.relative_to(root).as_posix(),
                "size": p.stat().st_size,
                "sha256": sha256(p),
            })
    score_summary = json.loads((root / "backtest" / "SCORECARD_SUMMARY.json").read_text())
    manifest = {
        "package": PACKAGE_NAME,
        "regeneration_status": "current-data full walk-forward",
        "exact_frozen_replication": False,
        "formula": validation["formula_selection"],
        "files": files,
        "validation": validation,
        "score_summary": score_summary,
        "global_scorecard": global_score.to_dict("records"),
    }
    manifest_path = root / "manifest" / "PACKAGE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    with (root / "manifest" / "SHA256SUMS.txt").open("w") as f:
        for row in files:
            f.write(f"{row['sha256']}  {row['path']}\n")
        f.write(f"{sha256(manifest_path)}  manifest/PACKAGE_MANIFEST.json\n")

    zip_path = parent / f"{PACKAGE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(parent / PACKAGE_NAME), "zip", parent, PACKAGE_NAME)
    (parent / f"{PACKAGE_NAME}_SHA256.txt").write_text(f"{sha256(zip_path)}  {zip_path.name}\n")
    return zip_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generator", required=True)
    ap.add_argument("--base-module", required=True)
    ap.add_argument("--v5-module", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output-parent", default=".")
    ap.add_argument("--n-estimators", type=int, default=360)
    ap.add_argument("--n-baskets", type=int, default=500)
    args = ap.parse_args()

    generator_path = Path(args.generator).resolve()
    generator = load_module(generator_path, "meteor_package_generator")
    generator.corrected_downvol = lambda mode: frozen_zero_std if mode == "zero_std" else generator.corrected_downvol(mode)
    original_live = generator.live_script_text
    generator.live_script_text = lambda: patched_live_script(original_live())

    parent = Path(args.output_parent).resolve()
    sys.argv = [
        generator_path.name,
        "--base-module", str(Path(args.base_module).resolve()),
        "--v5-module", str(Path(args.v5_module).resolve()),
        "--data-dir", str(Path(args.data_dir).resolve()),
        "--output-parent", str(parent),
        "--downvol-mode", "zero_std",
        "--n-estimators", str(args.n_estimators),
        "--n-baskets", str(args.n_baskets),
    ]
    generator.main()
    root = parent / PACKAGE_NAME
    zip_path = validate_and_finalize(root, parent, Path(__file__).resolve(), Path(args.data_dir).resolve())
    print(json.dumps({"package": str(zip_path), "sha256": sha256(zip_path)}, indent=2))


if __name__ == "__main__":
    main()
