"""As-of daily 126-session PCA/RMT and simple-correlation controls, Original149.

Exactly five global, five per-ETF spectral and five simple-correlation features.
All raw data strictly through the signal close, no future normalization.
"""
from __future__ import annotations
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.linalg import eigh
from tensor149_tcn5d.features import load_frozen

WINDOW=126
GLOBAL=("rmt_lambda1_share126","rmt_lambda2_share126","rmt_effective_rank126",
        "rmt_lambda1_delta21","rmt_effective_rank_delta21")
ETF=("rmt_pc1_abs_loading126","rmt_pc2to4_share126","rmt_pc1to4_idio_share126",
     "rmt_pc1_abs_delta21","rmt_pc1_residual_logmom21")
CONTROL=("simple_mean_corr126","simple_corr_dispersion126",
         "simple_spy_corr126","simple_spy_beta126","simple_spy_vol_ratio126")
HISTORY=21

def build(close):
    if "SPY" not in close.columns:raise ValueError("SPY required")
    if len(close.columns)<60:raise ValueError("Too few ETF")
    names=list(close.columns)
    spy=names.index("SPY")
    lc=np.log(close.where(close>0))
    returns=lc.diff().to_numpy(dtype=float)
    tlen,n=returns.shape
    gl=np.full((tlen,len(GLOBAL)),np.nan,dtype=np.float32)
    et=np.full((tlen,n,len(ETF)),np.nan,dtype=np.float32)
    ctl=np.full((tlen,n,len(CONTROL)),np.nan,dtype=np.float32)
    for t in range(WINDOW,tlen):
        raw=returns[t-WINDOW+1:t+1]
        active=np.isfinite(raw).all(axis=0)
        ids=np.flatnonzero(active)
        if len(ids)<60 or spy not in ids:continue
        x=raw[:,ids]
        mu=x.mean(axis=0)
        std=x.std(axis=0,ddof=1)
        good=np.isfinite(std)&(std>1e-10)
        ids=ids[good];x=x[:,good];mu=mu[good];std=std[good]
        k=len(ids)
        if k<60 or spy not in ids:continue
        z=(x-mu)/std
        gram=(z@z.T)/(WINDOW-1)
        # NumPy/Scipy eigh: only past data; last 5 nonzero eigenvectors,
        # use squared loadings to avoid arbitrary principal component signs.
        vals,u=eigh(gram,check_finite=False,overwrite_a=True)
        vals=np.maximum(vals,0.)
        total=vals.sum()
        if total<=1e-9:continue
        # Top four eigenvectors, in descending lambda order.
        uk=u[:,-4:][:,::-1]
        lam=vals[-4:][::-1]
        q=(z.T@uk)/np.sqrt(WINDOW-1)  # q_i,k = sqrt(lam_k) * eigenvector loading
        qsq=np.square(q)
        p=vals[vals>1e-12]/total
        neff=np.exp(-(p*np.log(p)).sum())
        gl[t,:3]=[lam[0]/total,lam[1]/total,neff/k]
        if t>=WINDOW+HISTORY:
            gl[t,3]=gl[t,0]-gl[t-HISTORY,0]
            gl[t,4]=gl[t,2]-gl[t-HISTORY,2]
        et[t,ids,0]=np.abs(q[:,0])
        et[t,ids,1]=qsq[:,1:4].sum(axis=1)
        et[t,ids,2]=np.clip(1-qsq[:,:4].sum(axis=1),0,1)
        if t>=WINDOW+HISTORY:
            et[t,ids,3]=et[t,ids,0]-et[t-HISTORY,ids,0]
        # Reconstruct PC1 common daily movement in this trailing as-of sample:
        # PC1 residual of each ETF (21 latest log-return samples) is test-free.
        pc1_projection=np.outer(uk[-HISTORY:,0],uk[:,0]@z)
        et[t,ids,4]=x[-HISTORY:].sum(axis=0) - (std*pc1_projection.sum(axis=0))
        # E: simple risk/correlation controls, same 126 bars, no RMT.
        corr=(z.T@z)/(WINDOW-1)
        tri=corr[np.triu_indices(k,k=1)]
        ctl[t,:,0]=tri.mean()
        ctl[t,:,1]=tri.std(ddof=0)
        i_spy=int(np.where(ids==spy)[0][0])
        ctl[t,ids,2]=corr[:,i_spy]
        ctl[t,ids,3]=corr[:,i_spy]*(std/std[i_spy])
        ctl[t,ids,4]=std/std[i_spy]
    for x in (gl,et,ctl):
        x[~np.isfinite(x)]=np.nan
    return gl,et,ctl

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--raw",default="evidence_v1/data/original149")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,raw_audit,sha=load_frozen(args.raw)
    times=mats["Close"].index
    start=time.monotonic()
    g,e,c=build(mats["Close"])
    if g.shape!=(len(times),5) or e.shape!=(len(times),149,5) or c.shape!=e.shape:
        raise ValueError("RMT panel dimensions not invariant")
    if not all(np.isfinite(g[np.where(np.isfinite(g[:,0]))[0],0])):
        raise ValueError("Broken spectral values")
    target=out/"RMT_CAUSAL_DAILY_CACHE.npz"
    np.savez_compressed(target,global_rmt=g,etf_rmt=e,control=c,
        dates=np.asarray(times.strftime("%Y-%m-%d"),dtype="U10"),
        tickers=np.asarray(list(mats["Close"].columns),dtype="U32"),
        feature_global=np.asarray(GLOBAL),feature_etf=np.asarray(ETF),
        feature_control=np.asarray(CONTROL),roster_sha=np.asarray(sha))
    metadata=dict(status="CAUSAL_RMT_DAILY_FEATURE_CACHE_COMPLETE",
        original_roster_sha256=sha,window_returns=WINDOW,days=len(times),tickers=149,
        first_date=str(times[0].date()),last_date=str(times[-1].date()),
        features={"global":list(GLOBAL),"etf":list(ETF),"control":list(CONTROL)},
        global_complete_days=int(np.isfinite(g[:,0]).sum()),
        idio_complete_ticker_days=int(np.isfinite(e[:,:,0]).sum()),
        cache_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
        seconds=float(time.monotonic()-start),raw_audit=raw_audit)
    (out/"MANIFEST.json").write_text(json.dumps(metadata,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:metadata[k] for k in ("status","days","tickers","global_complete_days",
                 "idio_complete_ticker_days","seconds","cache_sha256")},indent=2),flush=True)
if __name__=="__main__":main()
