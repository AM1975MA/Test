#!/usr/bin/env python3
"""Independently rebuild canonical MA3 reference evidence from frozen raw CSVs.

This job does not build/consume Titanium scores or any historical model output.
The full replay must regenerate its own MA3 panel and compare it to this
reference; using this reference panel as productive input is forbidden.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "vendor" / "etf_trader_v2" / "src"
sys.path.insert(0, str(REPO))

from compact21_learner_swap_v1.integrity import SEMANTIC_CONTRACT, compare_panels, file_hash, write_ma3_evidence


def environment_contract() -> dict:
    import scipy
    import sklearn
    from threadpoolctl import threadpool_info
    cpu_model = None
    if Path("/proc/cpuinfo").is_file():
        cpu_model = next((line.split(":", 1)[1].strip() for line in Path("/proc/cpuinfo").read_text().splitlines()
                          if line.startswith("model name")), None)
    return {"python": sys.version, "platform": platform.platform(), "machine": platform.machine(),
            "cpu_model": cpu_model, "numpy_build_config": np.show_config(mode="dicts"),
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
            "sklearn": sklearn.__version__, "threadpools": threadpool_info(),
            "execution_env": {key: os.environ.get(key) for key in
                              ("PYTHONHASHSEED", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
                               "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS", "NPY_DISABLE_CPU_FEATURES", "OPENBLAS_CORETYPE")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--verify-repeat", action="store_true",
                        help="Rebuild in a second independent child process; exact semantic equality is mandatory")
    args = parser.parse_args()
    raw, out = Path(args.raw).resolve(), Path(args.out).resolve()
    if not (raw / "universe.csv").is_file():
        raise FileNotFoundError(raw / "universe.csv")
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("MA3 evidence output must be fresh")
    out.mkdir(parents=True, exist_ok=True)
    builder = REPO / "vendor" / "etf_trader_v2" / "scripts" / "build_ma3_panel_source_only.py"
    # The exact normalization performed by canonical prepare_candidate_and_titanium_raw.
    # MA3 uses economic candidates only, so no Titanium infrastructure is appended.
    universe = pd.read_csv(raw / "universe.csv")[["ticker", "macro_category"]].copy()
    universe["ticker"] = universe.ticker.astype(str).str.upper()
    universe = universe.drop_duplicates("ticker").reset_index(drop=True)
    if universe.empty or universe.ticker.isna().any():
        raise RuntimeError("empty/invalid MA3 universe")
    with tempfile.TemporaryDirectory(prefix="ma3_reference_raw_") as td:
        candidate = Path(td)
        universe.to_csv(candidate / "universe.csv", index=False)
        for ticker in universe.ticker:
            if "/" in ticker or "\\" in ticker:
                raise ValueError("ticker cannot contain a path separator")
            shutil.copyfile(raw / f"{ticker}.csv", candidate / f"{ticker}.csv")
        candidate_hashes = {p.name: file_hash(p) for p in sorted(candidate.glob("*.csv"))}
        env = os.environ.copy()
        env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
        command = [sys.executable, str(builder), "--data", str(candidate),
                   "--cluster-data", str(candidate), "--output", str(out)]
        subprocess.run(command, cwd=REPO, env=env, check=True)
        repeat_proof = {"requested": bool(args.verify_repeat), "passed": False}
        if args.verify_repeat:
            repeat_dir = out / "repeat_rebuild"
            repeat_command = [sys.executable, str(builder), "--data", str(candidate),
                              "--cluster-data", str(candidate), "--output", str(repeat_dir)]
            subprocess.run(repeat_command, cwd=REPO, env=env, check=True)
            write_ma3_evidence(repeat_dir)
            repeat_proof.update(
                panel=compare_panels(pd.read_pickle(out / "RAW_FEATURE_PANEL.pkl"),
                                     pd.read_pickle(repeat_dir / "RAW_FEATURE_PANEL.pkl")),
                clusters=compare_panels(pd.read_csv(out / "DYNAMIC_CLUSTER_MEMBERSHIP.csv"),
                                        pd.read_csv(repeat_dir / "DYNAMIC_CLUSTER_MEMBERSHIP.csv")))
            repeat_proof["passed"] = repeat_proof["panel"]["exact_equal"] and repeat_proof["clusters"]["exact_equal"]
            (out / "VERIFY_REPEAT.json").write_text(json.dumps(repeat_proof, indent=2, allow_nan=False) + "\n")
            if not repeat_proof["passed"]:
                raise RuntimeError("independent canonical MA3 rebuild differs semantically; promotion blocked")
    manifest = json.loads((out / "RAW_FEATURE_PANEL_MANIFEST.json").read_text())
    if manifest.get("historical_cluster_membership_consumed") is not False or manifest.get("dynamic_clusters_generated_from_raw") is not True:
        raise RuntimeError("MA3 reference must be independently source-only")
    evidence = write_ma3_evidence(out)
    sources = [builder, REPO / "holdout70" / "v2_canonical_same_source_compare.py"]
    sources += sorted((SRC / "etf_trader" / "source_only").glob("*.py"))
    contract = {"line": "COMPACT21_LEARNER_SWAP_V1", "purpose": "independent_ma3_reference",
                "historical_outputs_consumed": False, "titanium_scores_consumed": False,
                "must_not_replace_replay_generated_panel": True,
                "raw_files_sha256": {p.name: file_hash(p) for p in sorted(raw.glob("*.csv"))},
                "candidate_raw_files_sha256": candidate_hashes,
                "canonical_sources_sha256": {str(p.relative_to(REPO)): file_hash(p) for p in sources},
                "reference_sources_sha256": {p.name: file_hash(p) for p in (Path(__file__), HERE / "integrity.py")},
                "environment": environment_contract(), "semantic_contract": SEMANTIC_CONTRACT,
                "repeat_verification": repeat_proof,
                "ma3_panel_semantic_sha256": evidence["panel"]["sha256"],
                "cluster_membership_semantic_sha256": evidence["clusters"]["sha256"],
                "candidate_count": len(universe), "candidate_tickers": universe.ticker.tolist()}
    (out / "INPUT_CONTRACT.json").write_text(json.dumps(contract, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "MA3_REFERENCE_REBUILT_FROM_RAW", "rows": evidence["panel"]["shape"][0],
                      "panel_semantic_sha256": evidence["panel"]["sha256"],
                      "cluster_semantic_sha256": evidence["clusters"]["sha256"]}), flush=True)


if __name__ == "__main__":
    main()
