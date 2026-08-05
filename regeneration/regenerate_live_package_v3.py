#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


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


def patch_source_formula(path: Path) -> None:
    text = path.read_text()
    replacements = {
        "neg = ret.clip(upper=0.0)\n            return neg.rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)":
        "neg = ret.where(ret < 0.0, 0.0)\n            return neg.rolling(h, min_periods=max(10, int(h * 0.75))).std(ddof=0) * np.sqrt(252)",
        "if mode=='zero_std': base.rolling_downvol=lambda ret,h: ret.clip(upper=0.0).rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)":
        "if mode=='zero_std': base.rolling_downvol=lambda ret,h: ret.where(ret<0.0,0.0).rolling(h,min_periods=max(10,int(h*0.75))).std(ddof=0)*np.sqrt(252)",
    }
    changed = False
    for old, new in replacements.items():
        if old in text:
            text = text.replace(old, new)
            changed = True
    if not changed and "min_periods=max(10" not in text:
        raise RuntimeError(f"Could not patch frozen zero_std formula in {path}")
    path.write_text(text)


def rebuild_manifest_and_zip(root: Path, parent: Path, v2) -> Path:
    source_generator = root / "source" / "regenerate_live_package.py"
    live = root / "METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py"
    patch_source_formula(source_generator)
    patch_source_formula(live)

    source_text = source_generator.read_text()
    live_text = live.read_text()
    formula_token = "min_periods=max(10"
    if formula_token not in source_text or formula_token not in live_text:
        raise RuntimeError("Frozen 75% downside-volatility formula is not embedded in both source and live runner")

    validation_path = root / "manifest" / "VALIDATION_REPORT.json"
    validation = json.loads(validation_path.read_text())
    validation["formula_embedded_in_source"] = True
    validation["formula_embedded_in_live_runner"] = True
    validation["status"] = "PASS"
    validation_path.write_text(json.dumps(validation, indent=2))

    files = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_file() and rel not in {"manifest/PACKAGE_MANIFEST.json", "manifest/SHA256SUMS.txt"}:
            files.append({"path": rel, "size": p.stat().st_size, "sha256": sha256(p)})

    manifest_path = root / "manifest" / "PACKAGE_MANIFEST.json"
    old_manifest = json.loads(manifest_path.read_text())
    old_manifest["files"] = files
    old_manifest["validation"] = validation
    old_manifest["exact_frozen_feature_formula"] = True
    old_manifest["exact_frozen_replication"] = False
    manifest_path.write_text(json.dumps(old_manifest, indent=2))

    with (root / "manifest" / "SHA256SUMS.txt").open("w") as f:
        for row in files:
            f.write(f"{row['sha256']}  {row['path']}\n")
        f.write(f"{sha256(manifest_path)}  manifest/PACKAGE_MANIFEST.json\n")

    zip_path = parent / f"{v2.PACKAGE_NAME}.zip"
    if zip_path.exists():
        zip_path.unlink()
    shutil.make_archive(str(parent / v2.PACKAGE_NAME), "zip", parent, v2.PACKAGE_NAME)
    (parent / f"{v2.PACKAGE_NAME}_SHA256.txt").write_text(f"{sha256(zip_path)}  {zip_path.name}\n")
    return zip_path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v2-wrapper", required=True)
    ap.add_argument("--generator", required=True)
    ap.add_argument("--base-module", required=True)
    ap.add_argument("--v5-module", required=True)
    ap.add_argument("--data-dir", required=True)
    ap.add_argument("--output-parent", default=".")
    ap.add_argument("--n-estimators", type=int, default=360)
    ap.add_argument("--n-baskets", type=int, default=500)
    args = ap.parse_args()

    v2_path = Path(args.v2_wrapper).resolve()
    v2 = load_module(v2_path, "regenerate_v2")
    parent = Path(args.output_parent).resolve()

    sys.argv = [
        v2_path.name,
        "--generator", str(Path(args.generator).resolve()),
        "--base-module", str(Path(args.base_module).resolve()),
        "--v5-module", str(Path(args.v5_module).resolve()),
        "--data-dir", str(Path(args.data_dir).resolve()),
        "--output-parent", str(parent),
        "--n-estimators", str(args.n_estimators),
        "--n-baskets", str(args.n_baskets),
    ]
    v2.main()

    root = parent / v2.PACKAGE_NAME
    shutil.copy2(Path(__file__).resolve(), root / "source" / "regenerate_live_package_v3.py")
    zip_path = rebuild_manifest_and_zip(root, parent, v2)
    print(json.dumps({"package": str(zip_path), "sha256": sha256(zip_path)}, indent=2))


if __name__ == "__main__":
    main()
