"""Two preregistered purely as-of feature families for weekly Original149 ranking.

R1 strength vs SPY and named 6 historical macro categories.
R2 correlations, peer breadth and cross-sectional dispersion/regime.
No future dates, learned thresholds, target labels, open(t+1), macro revisions.
An as-of panel eligible mask is deliberately not applied during formation:
historical contemporaneous raw returns are used, while candidate tradability
at signal t remains defined by the original *unchanged* eligibility() test.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from tensor149_tcn5d.features import FIELDS

HORIZONS=(5,21,63,126)
GROUP_FIELD="macro_category"

def _other_peer_mean(df,groups):
    out=pd.DataFrame(np.nan,index=df.index,columns=df.columns,dtype=float)
    for group in sorted(set(groups.values())):
        names=[t for t in df.columns if groups[t]==group]
        sub=df[names]
        sums=sub.sum(axis=1,min_count=1)
        counts=sub.notna().sum(axis=1)
        for ticker in names:
            valid=sub[ticker].notna()
            other_sum=sums-sub[ticker].fillna(0.)
            other_n=counts-valid.astype(int)
            out[ticker]=other_sum/other_n.replace(0,np.nan)
    return out

def _other_peer_median(df,groups):
    out=pd.DataFrame(np.nan,index=df.index,columns=df.columns,dtype=float)
    for group in sorted(set(groups.values())):
        names=[t for t in df.columns if groups[t]==group]
        if len(names)<2:continue
        for ticker in names:
            out[ticker]=df[[n for n in names if n!=ticker]].median(axis=1)
    return out

def _group_other_breadth(movement,groups):
    out=pd.DataFrame(np.nan,index=movement.index,columns=movement.columns,dtype=float)
    for group in sorted(set(groups.values())):
        names=[t for t in movement.columns if groups[t]==group]
        if len(names)<2:continue
        sub=movement[names]
        good=sub.notna()
        n=good.sum(axis=1)
        pos=(sub>0).where(good,False).sum(axis=1)
        for ticker in names:
            valid=good[ticker]
            denom=n-valid.astype(int)
            positive=pos-(valid&(sub[ticker]>0)).astype(int)
            out[ticker]=positive/denom.replace(0,np.nan)
    return out

def make_r1r2(mats,universe_csv):
    C=mats["Close"];names=list(C.columns)
    universe=pd.read_csv(universe_csv)
    category=universe.set_index("ticker")[GROUP_FIELD].to_dict()
    if set(category)!=set(names) or len(category)!=149:raise ValueError("Frozen category roster mismatched")
    if "SPY" not in C:raise ValueError("SPY not present")
    ret=C.pct_change(fill_method=None)
    mom={h:C.pct_change(h,fill_method=None) for h in HORIZONS}
    all_d={}
    spy=ret["SPY"]
    # Rolling past-only beta, h=63 (already in source) estimated with data through t.
    beta=ret.rolling(63,min_periods=63).cov(spy).div(
        spy.rolling(63,min_periods=63).var().replace(0,np.nan),axis=0)
    r1={}
    for h in HORIZONS:
        m=mom[h]
        r1[f"r1_excess_spy_{h}"]=m.sub(m["SPY"],axis=0)
        r1[f"r1_beta_resid_spy_{h}"]=m.sub(beta.mul(m["SPY"],axis=0))
        r1[f"r1_excess_peer_{h}"]=m-_other_peer_median(m,category)
    for h in (21,63):
        # 0..1 percentile ranks only among genuinely comparable ETF categories.
        vals=mom[h]
        rank=pd.DataFrame(np.nan,index=C.index,columns=names,dtype=float)
        for group in set(category.values()):
            gg=[ticker for ticker in names if category[ticker]==group]
            rank[gg]=vals[gg].rank(axis=1,pct=True,method="average")
        r1[f"r1_peer_pct_{h}"]=rank

    r2={}
    eq=ret.mean(axis=1)
    peer_ret=_other_peer_mean(ret,category)
    valid=ret.notna()
    # Exclude self from the broad return proxy; available from t without look-ahead.
    universe_exself=(ret.sum(axis=1,min_count=1).to_numpy()[:,None]-
                     ret.fillna(0.).to_numpy()) / np.maximum(valid.sum(axis=1).to_numpy()[:,None]-valid.to_numpy(),1)
    universe_exself=np.where((valid.sum(axis=1).to_numpy()>=2)[:,None],universe_exself,np.nan)
    univ_peer=pd.DataFrame(universe_exself,index=C.index,columns=names)
    for h in (21,63):
        r2[f"r2_corr_universe_{h}"]=ret.rolling(h,min_periods=h).corr(univ_peer)
        r2[f"r2_corr_peer_{h}"]=ret.rolling(h,min_periods=h).corr(peer_ret)
    r2["r2_corr_universe_change_21_63"]=r2["r2_corr_universe_21"]-r2["r2_corr_universe_63"]
    r2["r2_corr_peer_change_21_63"]=r2["r2_corr_peer_21"]-r2["r2_corr_peer_63"]

    for h in (1,5,21):
        current=ret if h==1 else mom[h]
        br=_group_other_breadth(current,category)
        r2[f"r2_peer_breadth_{h}"]=br
        r2[f"r2_univ_breadth_{h}"]=pd.DataFrame(
            np.broadcast_to((current>0).where(current.notna()).mean(axis=1,skipna=True).to_numpy()[:,None],C.shape),
            index=C.index,columns=C.columns)
    for h in (5,21):
        cur=mom[h]
        r2[f"r2_univ_dispersion_{h}"]=pd.DataFrame(
            np.broadcast_to(cur.std(axis=1,ddof=0).to_numpy()[:,None],C.shape),index=C.index,columns=names)
        peer_diff=cur-_other_peer_median(cur,category)
        peer_disp=pd.DataFrame(np.nan,index=C.index,columns=names)
        for group in set(category.values()):
            gg=[ticker for ticker in names if category[ticker]==group]
            groupdev=cur[gg].std(axis=1,ddof=0)
            peer_disp[gg]=np.broadcast_to(groupdev.to_numpy()[:,None],(len(C),len(gg)))
        r2[f"r2_peer_dispersion_{h}"]=peer_disp
    # A stress indicator common to all assets: 21d cross-section dispersion
    # relative to its own 63d past median; market state is retained explicitly.
    for h in (5,21):
        disp=r2[f"r2_univ_dispersion_{h}"].iloc[:,0]
        ratio=disp/disp.rolling(63,min_periods=50).median().replace(0,np.nan)
        r2[f"r2_dispersion_shock_{h}"]=pd.DataFrame(
            np.broadcast_to(ratio.to_numpy()[:,None],C.shape),index=C.index,columns=names)
    r2["r2_spy_mom21"]=pd.DataFrame(
        np.broadcast_to(mom[21]["SPY"].to_numpy()[:,None],C.shape),index=C.index,columns=names)
    r2["r2_spy_vol21"]=pd.DataFrame(
        np.broadcast_to((ret["SPY"].rolling(21,min_periods=21).std(ddof=0)*np.sqrt(252)).to_numpy()[:,None],C.shape),
        index=C.index,columns=names)
    def as_tensor(mapping):
        keys=tuple(mapping)
        a=np.stack([mapping[k].reindex(columns=names).to_numpy(dtype=np.float32) for k in keys],axis=2)
        a[~np.isfinite(a)]=np.nan
        return a,keys
    R1,k1=as_tensor(r1)
    R2,k2=as_tensor(r2)
    if len(k1)!=14 or len(k2)!=20:raise ValueError(f"feature counts: R1 {len(k1)}, R2 {len(k2)}")
    return R1,k1,R2,k2

def attach_blocks(x,r1,r2,variant):
    if variant=="A" or variant=="B":return x,tuple(FIELDS)
    if variant=="C":return np.concatenate([x,r1],axis=2),tuple(FIELDS)+tuple(f"r1_{i}" for i in range(r1.shape[-1]))
    if variant=="D":return np.concatenate([x,r1,r2],axis=2),tuple(FIELDS)+tuple(f"r1_{i}" for i in range(r1.shape[-1]))+tuple(f"r2_{i}" for i in range(r2.shape[-1]))
    raise ValueError(variant)
