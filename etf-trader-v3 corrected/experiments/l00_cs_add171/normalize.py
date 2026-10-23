"""Point-in-time cross-sectional [-1,+1] min/max normalization.

No fitted per-feature scaler or temporal rolling fit: each asof date has its
own investable-ticker distribution. Missingness is NEVER imputed. In
particular, prices/volumes/labels from later dates cannot enter this scaler.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

def normalize_same_day(panel:pd.DataFrame,feature_names:list[str],*,date_col:str="signal_date")->pd.DataFrame:
    if date_col not in panel:raise ValueError("Missing asof date")
    if len(feature_names)!=len(set(feature_names)):raise ValueError("Duplicated feature names")
    if not set(feature_names).issubset(panel.columns):raise ValueError("Missing features")
    out=panel.copy()
    for name in feature_names:
        raw=pd.to_numeric(out[name],errors="raise").replace([np.inf,-np.inf],np.nan)
        grp=raw.groupby(out[date_col],sort=False)
        lower=grp.transform("min")
        upper=grp.transform("max")
        span=upper-lower
        result=(2*(raw-lower)/span-1).where(span>0,0.0)
        result=result.where(raw.notna(),np.nan)
        out[name]=result.clip(-1,1)
    return out

def audit_scaling(original:pd.DataFrame,scaled:pd.DataFrame,features:list[str],date_col="signal_date")->pd.DataFrame:
    if len(original)!=len(scaled):raise AssertionError("row count mismatch")
    summaries=[]
    for dt,indices in original.groupby(date_col,sort=True).indices.items():
        for name in features:
            x=pd.to_numeric(original.iloc[indices][name],errors="raise").replace([np.inf,-np.inf],np.nan).to_numpy(float)
            z=scaled.iloc[indices][name].to_numpy(float)
            ok=np.isfinite(x)
            if not np.array_equal(np.isfinite(z),ok):raise AssertionError("NaN mask changed")
            if ok.sum()==0:continue
            if np.nanmax(np.abs(z[ok]))>1+1e-12:raise AssertionError("out of [-1,1]")
            xmi,xma=float(np.nanmin(x)),float(np.nanmax(x))
            if xma>xmi:
                if not np.isclose(z[np.nanargmin(x)],-1,atol=1e-10):raise AssertionError("minimum not -1")
                if not np.isclose(z[np.nanargmax(x)],1,atol=1e-10):raise AssertionError("maximum not +1")
            else:
                if not np.allclose(z[ok],0,atol=0):raise AssertionError("flat feature not zero")
            summaries.append(dict(signal_date=str(dt),feature=name,n_finite=int(ok.sum()),
                min_original=xmi,max_original=xma,
                min_scaled=float(np.nanmin(z)),max_scaled=float(np.nanmax(z)),
                is_constant=bool(xmi==xma)))
    return pd.DataFrame(summaries)

def unit_contract():
    dates=["2024-01-31"]*4+["2024-02-29"]*3
    x=pd.DataFrame({"signal_date":dates,"ticker":list("ABCDABC"),
                    "a":[-12,-3,2,20,8,8,np.nan],
                    "b":[10,np.nan,20,30,0,0,0]})
    y=normalize_same_day(x,["a","b"])
    np.testing.assert_allclose(y.a.iloc[:4].to_numpy(),[-1,-.4375,-.125,1])
    assert pd.isna(y.b.iloc[1]) and pd.isna(y.a.iloc[-1])
    assert np.all(y.b.iloc[-3:]==0)
    altered=x.copy();altered.loc[4:,"a"]=-999
    z=normalize_same_day(altered,["a","b"])
    np.testing.assert_allclose(z.a.iloc[:4],y.a.iloc[:4])
    shuffled=x.sample(frac=1,random_state=13).reset_index(drop=True)
    u=normalize_same_day(shuffled,["a","b"])
    m=y.merge(u,on=["signal_date","ticker"],suffixes=("_orig","_shuf"))
    np.testing.assert_allclose(m.a_orig,m.a_shuf)
    np.testing.assert_allclose(m.b_orig,m.b_shuf,equal_nan=True)
    audit_scaling(x,y,["a","b"])
if __name__=="__main__":unit_contract();print("CS_NORMALIZER_CAUSAL_UNIT_PASS")
