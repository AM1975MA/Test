"""Research-only global source correction, applied AFTER canonical source identity gate."""
from __future__ import annotations
import argparse, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

OLD = """def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return ret.where(ret<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*np.sqrt(252)"""
NEW = """def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:
    # Research-only full-window zero-target annualized downside semideviation.
    # No raw price imputation. Complete historical data needed for every h-window.
    return np.sqrt(ret.clip(upper=0).pow(2).rolling(h,min_periods=h).mean()*252.0)"""

def patch(path:Path):
    raw=path.read_text()
    assert raw.count(OLD)==1, "Canonical original rolling_downvol not found exactly once"
    assert raw.count("def rolling_downvol(")==1
    path.write_text(raw.replace(OLD,NEW))
    assert NEW in path.read_text()
    print("RESEARCH_DOWNVOL_ALL_SUBMODELS_PATCH_APPLIED", hashlib.sha256(path.read_bytes()).hexdigest())

if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("path",type=Path)
    patch(ap.parse_args().path)
