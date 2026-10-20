"""Exact daily Compact21 analogue: 125 canonical features, no future data."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder

FIELDS = tuple(k.F2D_FEATURES)

def load_frozen(folder: str):
    folder = Path(folder)
    meta = json.loads((folder / "manifest.json").read_text())
    universe = pd.read_csv(folder / "universe.csv")
    if len(universe) != 149 or universe.ticker.nunique() != 149:
        raise ValueError("Original149 frozen roster changed")
    for ticker, expected in meta["file_sha256"].items():
        actual = hashlib.sha256((folder / (ticker + ".csv")).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError("Original149 raw file SHA changed: " + ticker)
    mats, cats, audit = load_ticker_csv_folder(folder)
    if set(mats["Open"].columns) != set(universe.ticker):
        raise ValueError("Original149 panel mismatch")
    for name, frame in mats.items():
        mats[name] = frame.sort_index().reindex(columns=sorted(universe.ticker))
    return mats, audit, hashlib.sha256((folder/"universe.csv").read_bytes()).hexdigest()

def daily_compact(mats):
    """No month-end sampling: each output row is the information known at that day's close.
    Source formulas below are kept identical to kernel.build_features' Compact21 portion.
    """
    O,H,L,C,V=[mats[q] for q in ("Open","High","Low","Close","Volume")]
    dates=C.index
    logc=np.log(C.where(C>0))
    lr=logc.diff()
    ret=C.pct_change(fill_method=None)
    mkt=ret["SPY"] if "SPY" in ret else ret.median(axis=1)
    d={}
    for h in (5,10,21,42,63,126,252):
        d[f"mom{h}"]=C.pct_change(h,fill_method=None)
    for h in (21,63,126):
        d[f"vol{h}"]=lr.rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)
        d[f"downvol{h}"]=k.rolling_downvol(lr,h)
        d[f"drawdown{h}"]=C/C.rolling(h,min_periods=h).max()-1
        d[f"efficiency{h}"]=k.rolling_efficiency(logc,h)
    d["mom126_ex21"]=C.shift(21)/C.shift(126)-1
    d["mom252_ex21"]=C.shift(21)/C.shift(252)-1
    d["acc_mom_5_21"]=d["mom5"]-(5/21)*d["mom21"]
    d["acc_mom_21_63"]=d["mom21"]-(21/63)*d["mom63"]
    d["vol_ratio_21_126"]=d["vol21"]/d["vol126"].replace(0,np.nan)
    d["skew63"]=lr.rolling(63,min_periods=63).skew()
    d["kurt63"]=lr.rolling(63,min_periods=63).kurt()
    gk=.5*np.log(H/L.replace(0,np.nan))**2-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan))**2
    d["gkvol21"]=np.sqrt(gk.rolling(21,min_periods=21).mean()*252)
    adv=(C*V).rolling(63,min_periods=42).mean()
    d["log_adv63"]=np.log(adv.where(adv>0))
    lv=np.log(V.where(V>0))
    d["volume_surprise21"]=(lv-lv.rolling(21,min_periods=15).mean())/lv.rolling(21,min_periods=15).std(ddof=0).replace(0,np.nan)
    for h in (63,126):
        b,co=k.beta_corr(ret,mkt,h)
        d[f"beta_mkt{h}"]=b
        d[f"corr_mkt{h}"]=co
    d["ma_gap50"]=C/C.rolling(50,min_periods=50).mean()-1
    d["ma_gap200"]=C/C.rolling(200,min_periods=200).mean()-1
    d["ema_gap20"]=C/C.ewm(span=20,adjust=False,min_periods=20).mean()-1
    d["ema_gap50"]=C/C.ewm(span=50,adjust=False,min_periods=50).mean()-1
    for h in (126,252):
        d[f"breakout_pos{h}"]=(C-C.rolling(h,min_periods=h).min())/(C.rolling(h,min_periods=h).max()-C.rolling(h,min_periods=h).min()).replace(0,np.nan)
    d["rsi14"]=k.rolling_rsi(C,14)
    d["positive_frac63"]=(ret>0).rolling(63,min_periods=63).mean()
    d["max_loss63"]=ret.rolling(63,min_periods=63).min()
    d["max_gain63"]=ret.rolling(63,min_periods=63).max()
    d["cvar10_63"]=k.rolling_cvar10(ret,63)
    d["sign_entropy63"]=k.rolling_sign_entropy(ret,63)
    d["autocorr1_63"]=k.rolling_autocorr(ret,63)
    if len(FIELDS)!=125: raise ValueError("Expected canonical 125 features")
    ans=np.full((len(dates),len(C.columns),len(FIELDS)),np.nan,dtype=np.float32)
    for j,name in enumerate(FIELDS):
        if name in d:
            v=d[name]
        elif name.endswith("_pct"):
            v=k.cs_pct(d[name[:-4]])
        elif name.endswith("_dev"):
            v=k.cs_robust_dev(d[name[:-4]])
        else:
            raise ValueError("Unknown canonical feature: "+name)
        a=v.to_numpy(dtype=np.float32,copy=False)
        ans[:,:,j]=a
    ans[~np.isfinite(ans)]=np.nan
    return ans

def labels_next_open(mats, horizon=5):
    """Signal close(t), entry open(t+1), exit open(t+1+h)."""
    O=mats["Open"]
    ret=O.shift(-(horizon+1))/O.shift(-1)-1
    ret=ret.replace([np.inf,-np.inf],np.nan)
    pct=ret.rank(axis=1,pct=True,method="average")
    y=(2*pct-1).to_numpy(dtype=np.float32)
    return ret.to_numpy(dtype=np.float32),y

def eligible(x,open_prices):
    """Live-available price and >=30 valid Compact21 features in all 30 input bars."""
    valid=(np.isfinite(x).sum(axis=2)>=30)&np.isfinite(open_prices)&(open_prices>0)
    trailing=pd.DataFrame(valid.astype("int8")).rolling(30,min_periods=30).sum().to_numpy()
    return valid & (trailing>=30)
