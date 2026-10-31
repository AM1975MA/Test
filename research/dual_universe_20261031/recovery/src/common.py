"""Recovery DUAL-01 contracts. Model-independent chronology and persistence."""
from pathlib import Path
import hashlib,json,os,tempfile
import numpy as np
import pandas as pd

def digest(data: bytes)->str:return hashlib.sha256(data).hexdigest()

def atomic_bytes(path: Path, data: bytes) -> None:
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)

def atomic_json(path: Path, obj)->None:
    atomic_bytes(path,json.dumps(obj,indent=2,ensure_ascii=False,allow_nan=False,default=str).encode())

def eligibility(close: pd.DataFrame, volume: pd.DataFrame) -> pd.DataFrame:
    observed=np.isfinite(close)&(close>0)
    age=observed.cummax().cumsum()-1
    observed_count=observed.rolling(252,min_periods=252).sum()
    positive_volume=(volume>0).rolling(63,min_periods=63).mean()
    return (observed&(age>=252)&(observed_count>=200)&(positive_volume>=.5)).fillna(False)

def forward_labels(opens: pd.DataFrame, signals: pd.DatetimeIndex) -> pd.DataFrame:
    records=[];ix=opens.index
    for sd in signals:
        loc=ix.get_indexer([sd])[0]
        if loc<0 or loc+1>=len(ix):continue
        row=pd.DataFrame({'signal_date':sd,'ticker':opens.columns,'entry_date':ix[loc+1]})
        for h in [21,42,63]:
            end=loc+1+h
            row[f'exit_date_{h}']=ix[end] if end<len(ix) else pd.NaT
            if end<len(ix):
                a=opens.iloc[loc+1].where(opens.iloc[loc+1]>0);b=opens.iloc[end].where(opens.iloc[end]>0)
                row[f'fwd_ret_{h}']=(b/a-1).to_numpy()
            else:row[f'fwd_ret_{h}']=np.nan
        records.append(row)
    return pd.concat(records,ignore_index=True) if records else pd.DataFrame()

def mature_mask(panel: pd.DataFrame, year: int, multi: bool=False) -> pd.Series:
    cut=pd.Timestamp(year,1,1)
    keep=panel.eligible & (panel.signal_date<cut)
    for h in ([21,42,63] if multi else [21]):
        keep=keep & (panel[f'exit_date_{h}']<cut) & np.isfinite(panel[f'fwd_ret_{h}'])
    return keep.fillna(False)

def return_grades(returns: np.ndarray) -> np.ndarray:
    r=np.asarray(returns,dtype=float)
    if r.ndim!=1 or not len(r) or not np.isfinite(r).all():raise ValueError('Finite nonempty one-dimensional returns required')
    spread=max(float(np.quantile(r,.9)-np.quantile(r,.1)),1e-6)
    return np.rint(7.5+7.5*np.clip((r-np.median(r))/spread,-1,1)).astype('int32')
