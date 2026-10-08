"""L2-M: causal source-only orthogonalization core. Diagnostic features ONLY.

The complete executed data loader, evaluators and independent checker accompany
the conversation ZIP ETF_Trader_L2M_volatilita_ortogonale.zip.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

MOMS=("mom21","mom63","mom126","abs_mom21","abs_mom63","abs_mom126")


def monthly_category_projection(panel:pd.DataFrame)->tuple[pd.DataFrame,pd.DataFrame]:
    """Compute volatility orthogonal to six signed/absolute momentum windows.

    panel: rows (signal_date,ticker,macro_category), containing strictly
    historical log_vol63 and MOMS. No forward economic label enters.
    """
    p=panel.copy()
    p["vol_orthogonal"]=np.nan
    audits=[]
    for (dt,cat),g in p.groupby(["signal_date","macro_category"],sort=True):
        vals=g[["log_vol63",*MOMS]].to_numpy(float)
        ok=np.isfinite(vals).all(axis=1)
        a=vals[ok]
        if len(a)<10:
            continue
        mu=a.mean(axis=0); sd=a.std(axis=0,ddof=0)
        if np.any(sd<1e-12):
            continue
        z=(a-mu)/sd
        X=np.column_stack([np.ones(len(z)),z[:,1:]])
        # SVD via lstsq handles rank deficiency when abs(mom)==+/-mom.
        beta,_,rank,_=np.linalg.lstsq(X,z[:,0],rcond=1e-12)
        if rank<3:
            continue
        residual=z[:,0]-X@beta
        max_orth=float(np.max(np.abs(X.T@residual)/len(z)))
        if max_orth>1e-10:
            raise RuntimeError("Non-orthogonal feature: numerical projection failed")
        p.loc[g.index[ok],"vol_orthogonal"]=residual
        audits.append({"signal_date":dt,"macro_category":cat,"n":len(z),
                       "effective_rank":int(rank),"max_orthogonality":max_orth})
    return p,pd.DataFrame(audits)


def annual_past_only_residual(panel:pd.DataFrame,year:int)->tuple[pd.DataFrame,dict]:
    """Independent diagnostic of genuinely out-of-period conditional residual.

    Must supply precomputed date/category percentile ranks and fixed category
    indicators. Only pre-1-Jan rows are fitted. Does NOT guarantee orthogonality
    in each future month; compare explicitly with contemporaneous projection.
    """
    cutoff=pd.Timestamp(year,1,1)
    cols=[m+"_catrank" for m in MOMS]
    categories=sorted(panel.macro_category.unique())
    frame=panel.copy()
    for cat in categories[:-1]:
        frame[f"cat_{cat}"]=(frame.macro_category==cat).astype(int)
    cols += ["cat_"+cat for cat in categories[:-1]]
    train=frame[(frame.signal_date<cutoff)&(frame.signal_date>="2010-01-01")]
    test=frame[frame.signal_date.dt.year.eq(year)]
    train=train[train[cols+["log_vol63_catrank"]].notna().all(axis=1)]
    test=test[test[cols+["log_vol63_catrank"]].notna().all(axis=1)]
    if train.empty or train.signal_date.max()>=cutoff:
        raise ValueError("Missing causal train history")
    model=make_pipeline(SimpleImputer(strategy="median",keep_empty_features=True),
                        StandardScaler(),Ridge(alpha=100.0))
    model.fit(train[cols],train["log_vol63_catrank"])
    out=test[["signal_date","ticker"]].copy()
    out["vol_conditional"]=test.log_vol63_catrank-model.predict(test[cols])
    return out,{"year":year,"train_rows":len(train),
                "train_max_date":str(train.signal_date.max().date()),
                "test_rows":len(test)}
