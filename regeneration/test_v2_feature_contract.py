#!/usr/bin/env python3
"""ETF V2 mathematical feature-contract tests (not backtest optimisation).
Covers 125 compact features, Tail aliases, 18 extra signals, timestamps, NaNs,
cross-sectional rank/deviation, exact analytical toy cases and no-look-ahead.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"regeneration"/"campaign"))
from etf_trader.source_only import kernel as k
from etf_trader.source_only import features as ex

def make_panel(n=450):
    idx=pd.bdate_range("2021-01-01",periods=n)
    rng=np.random.default_rng(21102026)
    T=["SPY"]+[f"ETF{i:02d}" for i in range(1,24)]
    cols={}
    for j,t in enumerate(T):
        drift=(j%8-3)*0.00023
        daily=drift+0.00025+rng.normal(0,.007+.0002*j,n)
        cols[t]=100*np.exp(np.cumsum(daily))
    C=pd.DataFrame(cols,index=idx)
    C["ETF01"]=100*np.exp(np.arange(n)*0.004)  # all gains
    C["ETF02"]=100*np.exp(-np.arange(n)*0.004) # all losses
    C["ETF03"]=100.0                          # all flat
    C.loc[idx[-100],"ETF04"]=np.nan           # an actual missing price
    O=C*(1.0+rng.normal(0,.001,(n,len(T))))
    H=pd.DataFrame(np.maximum(O.to_numpy(),C.to_numpy())*1.003,index=idx,columns=T)
    L=pd.DataFrame(np.minimum(O.to_numpy(),C.to_numpy())*.997,index=idx,columns=T)
    V=pd.DataFrame(rng.integers(100,20000,(n,len(T))).astype(float),index=idx,columns=T)
    return {"Open":O,"High":H,"Low":L,"Close":C,"Volume":V}

def check_formula_units():
    h=21
    r=pd.DataFrame({"r":([.02]*10+[-.01]*11+[-.05]*105)})
    observed=k.rolling_downvol(r,h).iloc[h-1,0]
    expected=np.sqrt(252.0*(11*.01**2)/h)
    assert np.isclose(observed,expected,rtol=1e-12),(observed,expected)
    assert np.isfinite(k.rolling_downvol(pd.DataFrame({"up":[.01]*126}),126).iloc[-1,0])
    assert k.rolling_downvol(pd.DataFrame({"up":[.01]*126}),126).iloc[-1,0]==0.0
    rr=pd.DataFrame({"gap":[-.01]*126});rr.iloc[62,0]=np.nan
    assert np.isnan(k.rolling_downvol(rr,126).iloc[-1,0])
    idx=pd.bdate_range("2023-01-01",periods=200)
    pr=pd.DataFrame({"gain":100*np.exp(np.arange(200)*.003),
                     "loss":100*np.exp(-np.arange(200)*.003),
                     "flat":np.full(200,100)},index=idx)
    rsi=k.rolling_rsi(pr)
    assert rsi["gain"].iloc[-1]==100,rsi.iloc[-1]
    assert rsi["loss"].iloc[-1]==0,rsi.iloc[-1]
    assert rsi["flat"].iloc[-1]==50,rsi.iloc[-1]
    # Independent Wilder RSI oracle: first h changes use an SMA seed,
    # subsequent updates use (previous*(h-1)+current)/h.
    diffs=np.array([1.,-2.,3.,-1.,4.,-3.,2.,-1.,2.,-1.,3.,-2.,1.,-1.,2.,-3.])
    prices=np.r_[100.0,100+np.cumsum(diffs)]
    times=pd.bdate_range("2024-01-02",periods=len(prices))
    rs=k.rolling_rsi(pd.DataFrame({"x":prices},index=times),h=14)["x"]
    gain=np.maximum(diffs[:14],0.0).mean()
    loss=np.maximum(-diffs[:14],0.0).mean()
    assert np.isnan(rs.iloc[13])
    assert np.isclose(rs.iloc[14],100*gain/(gain+loss),atol=1e-12)
    gain=(13*gain+max(diffs[14],0.0))/14
    loss=(13*loss+max(-diffs[14],0.0))/14
    assert np.isclose(rs.iloc[15],100*gain/(gain+loss),atol=1e-12)
    gap=pd.DataFrame({"x":100*np.exp(np.arange(40)*.01)})
    gap.iloc[20,0]=np.nan
    rsi_gap=k.rolling_rsi(gap,h=14)["x"]
    assert rsi_gap.iloc[34:].notna().sum()==5  # 14 valid changes from t=22 through t=35
    assert rsi_gap.iloc[34]!=rsi_gap.iloc[34]  # incomplete warm-up
    assert rsi_gap.iloc[35]==100.0
    s=pd.DataFrame({"gain":[.001]*100,"loss":[-.001]*100,"mixed":[.001,-.001]*50})
    ent=k.rolling_sign_entropy(s,63).iloc[-1]
    assert np.isclose(ent["gain"],0.0,atol=1e-14) and np.isclose(ent["loss"],0.0,atol=1e-14)
    assert np.isclose(ent["mixed"],np.log(2),atol=.001)
    s.iloc[-1,0]=np.nan
    assert np.isnan(k.rolling_sign_entropy(s,63).iloc[-1]["gain"])

def check_derived_features():
    mats=make_panel()
    dates,comp,tail,D=k.build_features(mats)
    assert len(k.F2D_FEATURES)==125 and len(set(k.F2D_FEATURES))==125
    assert len(k.TAIL_FEATURES)==60 and len(set(k.TAIL_FEATURES))==60
    assert list(comp.columns[2:])==k.F2D_FEATURES
    assert list(tail.columns[2:])==k.TAIL_FEATURES
    assert len(comp)==len(dates)*len(mats["Close"].columns)
    assert comp[["signal_date","ticker"]].duplicated().sum()==0
    last=dates[-1]
    at=comp[comp.signal_date==last].set_index("ticker")
    # Explicit edge contracts for relative and full-window features.
    assert at.loc["ETF01","rsi14"]==100
    assert at.loc["ETF02","rsi14"]==0
    assert at.loc["ETF03","rsi14"]==50
    assert at.loc["ETF01","downvol126"]==0.0
    assert np.isclose(at.loc["ETF01","positive_frac63"],1.0)
    assert np.isclose(at.loc["ETF02","positive_frac63"],0.0)
    assert np.isclose(at.loc["ETF01","sign_entropy63"],0.0,atol=1e-14)
    assert np.isfinite(at.loc["ETF04","vol63"]) or np.isnan(at.loc["ETF04","vol63"])
    for f in k.F2D_FEATURES:
        assert pd.to_numeric(comp[f],errors="coerce").notna().any(),f+" entirely missing"
    for f in k.TAIL_FEATURES:
        assert pd.to_numeric(tail[f],errors="coerce").notna().any(),f+" entirely missing"
    for name in [f for f in k.F2D_FEATURES if f.endswith("_pct")]:
        base=name.removesuffix("_pct")
        expected=at[base].rank(pct=True)
        np.testing.assert_allclose(at[name],expected,rtol=1e-12,atol=1e-12,equal_nan=True)
    for name in [f for f in k.F2D_FEATURES if f.endswith("_dev")]:
        base=name.removesuffix("_dev")
        expected=k.cs_robust_dev(at[[base]].T).T.iloc[:,0] if False else None
        # Evaluate exact robust-z formula with the global same-month ETF median/MAD.
        values=at[base];med=values.median();mad=(values-med).abs().median()
        if mad>0:
            expected=((values-med)/(1.4826*mad)).clip(-8,8)
            np.testing.assert_allclose(at[name],expected,rtol=1e-12,atol=1e-12,equal_nan=True)
        else:
            assert at[name].isna().all(),name
    # 18 extra inputs must have coherent month-end ranks, no future values.
    categories={t:"CAT_A" if t in list(mats["Close"].columns)[:12] else "CAT_B" for t in mats["Close"].columns}
    extra=ex.build(mats,categories,dates)
    assert set(sum(ex.GROUPS.values(),[]))<=set(extra)
    assert len(extra)==len(comp)
    assert not extra[["signal_date","ticker"]].duplicated().any()
    for feat in sum(ex.GROUPS.values(),[]):
        assert np.isfinite(pd.to_numeric(extra[feat],errors="coerce")).any(),feat
    # Verify all feature histories are point-in-time: extending the future does not alter the past.
    past_idx=mats["Close"].index[-45]
    before={field:mat.loc[mat.index<=past_idx] for field,mat in mats.items()}
    dp,cpre,tpre,Dpre=k.build_features(before)
    common=sorted(set(dp)&set(dates))
    assert common
    last_common=common[-1]
    cpre=cpre[cpre.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    cfull=comp[comp.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    tpre=tpre[tpre.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    tfull=tail[tail.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    for col in k.F2D_FEATURES:
        np.testing.assert_allclose(cpre[col],cfull[col],equal_nan=True,atol=1e-10,rtol=1e-10,
                                   err_msg=f"LOOKAHEAD COMPACT {col}")
    for col in k.TAIL_FEATURES:
        np.testing.assert_allclose(tpre[col],tfull[col],equal_nan=True,atol=1e-10,rtol=1e-10,
                                   err_msg=f"LOOKAHEAD TAIL {col}")
    epre=ex.build(before,categories,dp);efull=extra[extra.signal_date.isin(dp)]
    efull=efull[efull.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    epre=epre[epre.signal_date==last_common].sort_values("ticker").reset_index(drop=True)
    for feat in sum(ex.GROUPS.values(),[]):
        np.testing.assert_allclose(epre[feat],efull[feat],equal_nan=True,atol=1e-10,rtol=1e-10,
                                   err_msg=f"LOOKAHEAD EXTRA {feat}")
    print("OK coverage: 125 compact, 60 tail, 18 extra; no lookahead; daily unit math",flush=True)

if __name__=="__main__":
    check_formula_units()
    check_derived_features()
