#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import shutil
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
RAW149_INPUT = Path(os.environ["RAW149_INPUT"])
EU120_INPUT = Path(os.environ["EU120_INPUT"])
P45_ROUTE = Path(os.environ["P45_ROUTE_PATH"])
P45_PARITY = Path(os.environ["P45_PARITY_PATH"])
P41_COMMIT = os.environ.get("P41_COMMIT", "")
P45_COMMIT = os.environ.get("P45_COMMIT", "")

BASE_SCRIPT = HERE.parent / "p45_zero_shot_56" / "run_p45_zero_shot_56.py"
spec = importlib.util.spec_from_file_location("p45base", BASE_SCRIPT)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

# Redirect every mutable/output path to the 120-ETF run.
m.ROOT = HERE
m.OUT = HERE / "results"
m.MODELS = m.OUT / "model_bundle"
m.RAW_TRAIN = m.OUT / "raw149"
m.RAW_TARGET = m.OUT / "raw120"
m.RAW_REF = m.OUT / "raw_refs"
m.MA3_TRAIN = m.OUT / "ma3_train149"
m.MA3_TARGET = m.OUT / "ma3_target120"
for p in (m.OUT, m.MODELS, m.RAW_TRAIN, m.RAW_TARGET, m.RAW_REF, m.MA3_TRAIN, m.MA3_TARGET):
    p.mkdir(parents=True, exist_ok=True)


def find_universe(root: Path, count: int) -> Path:
    hits = []
    for p in root.rglob("universe.csv"):
        try:
            q = pd.read_csv(p)
        except Exception:
            continue
        if len(q) == count and "ticker" in q.columns:
            hits.append(p)
    if len(hits) != 1:
        raise RuntimeError(f"expected one {count}-row universe under {root}, found {hits}")
    return hits[0]


def copy_frozen_folder(src_universe: Path, dst: Path) -> pd.DataFrame:
    src = src_universe.parent
    u = pd.read_csv(src_universe)
    u.to_csv(dst / "universe.csv", index=False)
    missing = []
    for t in u.ticker.astype(str):
        s = src / f"{t}.csv"
        if not s.exists():
            missing.append(t)
        else:
            shutil.copy2(s, dst / s.name)
    if missing:
        raise RuntimeError(f"missing frozen CSVs: {missing}")
    return u


u149_path = find_universe(RAW149_INPUT, 149)
u120_path = find_universe(EU120_INPUT, 120)
u149 = copy_frozen_folder(u149_path, m.RAW_TRAIN)
u120 = copy_frozen_folder(u120_path, m.RAW_TARGET)

# Main transfer runner reads this legacy filename; contents are the verified 120 universe.
u120.to_csv(HERE / "UNIVERSE_56.csv", index=False)

# Risk/reference series come from the exact frozen 149 input, never from a live download.
refs = ["SPY", "HYG", "IEF", "BIL", "SHV"]
ref_rows = []
for t in refs:
    src = m.RAW_TRAIN / f"{t}.csv"
    if not src.exists():
        raise RuntimeError(f"reference {t} missing from frozen raw149")
    shutil.copy2(src, m.RAW_REF / src.name)
    ref_rows.append({"ticker": t, "macro_category": "REF"})
pd.DataFrame(ref_rows).to_csv(m.RAW_REF / "universe.csv", index=False)

# Replace the legacy 3-part copy with the exact frozen P45 route at the certified commit.
route = pd.read_csv(P45_ROUTE)
if len(route) < 100 or "w_monthly" not in route.columns:
    raise RuntimeError("invalid canonical P45 router trace")
a = max(1, len(route) // 3)
b = max(a + 1, 2 * len(route) // 3)
route.iloc[:a].to_csv(HERE / "P45_ROUTER_PART1.csv", index=False)
route.iloc[a:b].to_csv(HERE / "P45_ROUTER_PART2.csv", index=False, header=False)
route.iloc[b:].to_csv(HERE / "P45_ROUTER_PART3.csv", index=False, header=False)

# Frozen-data integrity gates.
raw149_manifest = json.loads((u149_path.parent / "manifest.json").read_text())
eu120_manifest = json.loads((EU120_INPUT / "manifest.json").read_text()) if (EU120_INPUT / "manifest.json").exists() else json.loads((u120_path.parent.parent / "manifest.json").read_text())
if int(raw149_manifest.get("tickers", -1)) != 149:
    raise RuntimeError("raw149 manifest is not the certified 149 snapshot")
if int(eu120_manifest.get("selected_count", -1)) != 120 or int(eu120_manifest.get("unique_tickers", -1)) != 120:
    raise RuntimeError("EU120 manifest does not contain 120 unique ETFs")
if int(eu120_manifest.get("original149_overlap", -1)) != 0:
    raise RuntimeError("EU120 overlaps original149")
if set(u149.ticker.astype(str)) & set(u120.ticker.astype(str)):
    raise RuntimeError("actual frozen universes overlap")

# Diagnostic/reference only: confirms the router/source lineage is the certified P45 lineage.
parity_ref = json.loads(P45_PARITY.read_text())
(HERE / "CANONICAL_PARITY_REFERENCE.json").write_text(json.dumps(parity_ref, indent=2) + "\n")

# Crucial: disable every live Yahoo download in the inherited runner.
def frozen_only(meta: pd.DataFrame, out: Path) -> None:
    expected = set(meta.ticker.astype(str).str.upper())
    have = {p.stem.upper() for p in out.glob("*.csv") if p.name != "universe.csv"}
    miss = sorted(expected - have)
    if miss:
        raise RuntimeError(f"frozen-only input missing {len(miss)} tickers: {miss[:20]}")

m.download_folder = frozen_only
m.main()

result_path = m.OUT / "RESULT.json"
r = json.loads(result_path.read_text())
if int(r.get("training_universe_count", -1)) != 149:
    raise RuntimeError("unexpected training universe count")
if int(r.get("target_count", -1)) != 120:
    raise RuntimeError(f"runner did not use all 120 ETFs: {r.get('target_count')}")
if int(r.get("training_target_overlap", -1)) != 0 or bool(r.get("target_labels_used_for_fit", True)):
    raise RuntimeError("zero-shot integrity gate failed")
r["status"] = "P45_EU120_ZERO_SHOT_COMPLETE"
r["target_count"] = 120
r["fit_scope"] = "all fitted estimators use frozen original149 only; frozen EU120 is prediction-only"
r["target_universe_file"] = "Actions artifact eu120-frozen-20260701 / raw_ticker_csv/universe.csv"
r["raw149_source"] = "Actions artifact etf-trader-raw-149 from run 36551650325"
r["eu120_source"] = "Actions artifact eu120-frozen-20260701 from run 36597035280"
r["p41_source_commit"] = P41_COMMIT
r["p45_router_commit"] = P45_COMMIT
r["live_market_downloads"] = False
r["eu120_manifest_status"] = eu120_manifest.get("status")
result_path.write_text(json.dumps(r, indent=2) + "\n")
print("EU120_FINAL_RESULT", json.dumps(r, indent=2), flush=True)
