"""Strict-causal source-only fragility overlay.

Features and labels are built directly from ticker OHLCV. Models arm a monthly
75/25 allocation only; a flip to 25/75 requires a later close confirmation and
executes at the next open.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def build_asset_risk_panel(mats):
    C=mats["Close"].copy()
    ret=C.pct_change(fill_method=None)

    def mom(n): return C/C.shift(n)-1
    def dd(n): return C/C.rolling(n,min_periods=max(2,n//2)).max()-1

    M={n:mom(n) for n in (5,10,21,42,63,126,252)}
    D={n:dd(n) for n in (21,63,126,252)}
    V={n:ret.rolling(n,min_periods=n).std(ddof=1)*np.sqrt(252) for n in (10,20,63,126)}
    spy_vs200=C["SPY"]/C["SPY"].rolling(200,min_periods=200).mean()-1
    breadth21=(M[21]>0).mean(axis=1)
    breadth63=(M[63]>0).mean(axis=1)
    ratio=C["HYG"]/C["IEF"]
    hygief21=ratio/ratio.shift(21)-1
    hygief63=ratio/ratio.shift(63)-1

    s=pd.Series(C.index,index=C.index)
    mdates=pd.DatetimeIndex(s.groupby(C.index.to_period("M")).max().values)
    pos={d:i for i,d in enumerate(C.index)}
    rows=[]

    for sd in mdates:
        i=pos[sd]
        if i<252 or i+21>=len(C.index):
            continue
        fut=C.iloc[i:i+22]
        peak=fut.cummax()
        fdd=(fut/peak-1).min(axis=0)
        exit_date=C.index[i+21]
        glob={
            "spy_m21":M[21].at[sd,"SPY"],"spy_m63":M[63].at[sd,"SPY"],
            "spy_m126":M[126].at[sd,"SPY"],"spy_vs200":spy_vs200.at[sd],
            "breadth21":breadth21.at[sd],"breadth63":breadth63.at[sd],
            "hygief21":hygief21.at[sd],"hygief63":hygief63.at[sd],
            "spy_vol20":V[20].at[sd,"SPY"],"spy_vol63":V[63].at[sd,"SPY"],
        }
        ranks={
            "rank_m21":M[21].loc[sd].rank(pct=True,method="average",ascending=False),
            "rank_m63":M[63].loc[sd].rank(pct=True,method="average",ascending=False),
            "rank_m126":M[126].loc[sd].rank(pct=True,method="average",ascending=False),
            "rank_dd63":D[63].loc[sd].rank(pct=True,method="average",ascending=False),
            "rank_lowvol20":V[20].loc[sd].rank(pct=True,method="average",ascending=True),
            "rank_lowvol63":V[63].loc[sd].rank(pct=True,method="average",ascending=True),
        }
        for t in C.columns:
            if not np.isfinite(C.at[sd,t]) or not np.isfinite(fdd.get(t,np.nan)):
                continue
            r={"signal_date":sd,"exit_date":exit_date,"ticker":t,
               "fwd_maxdd21":float(fdd[t])}
            for n in M:r[f"m{n}"]=M[n].at[sd,t]
            for n in D:r[f"dd{n}"]=D[n].at[sd,t]
            for n in V:r[f"vol{n}"]=V[n].at[sd,t]
            for name,ser in ranks.items():r[name]=ser.get(t,np.nan)
            r.update(glob);rows.append(r)
    return pd.DataFrame(rows).sort_values(["signal_date","ticker"]).reset_index(drop=True)


def topk_scoring_rows(score_panel, allocation_table, top_k=5):
    score=score_panel.pivot(index="signal_date",columns="ticker",values="score")
    rows=[]
    for a in allocation_table.itertuples(index=False):
        dt=pd.Timestamp(a.signal_date)
        if dt not in score.index:
            continue
        row=score.loc[dt]
        # allocation_table alone does not carry full basket membership, caller
        # must add 'members' before using this helper.
        members=getattr(a,"members",None)
        if members is None:
            raise ValueError("allocation_table must contain a members iterable")
        local=sorted(
            [(t,float(row[t])) for t in members if t in row.index and np.isfinite(row[t])],
            key=lambda x:(-x[1],x[0]),
        )[:top_k]
        for rank,(t,s) in enumerate(local,1):
            rows.append({
                "signal_date":dt,"basket":str(a.basket),"ticker":t,
                "alpha_rank":rank,"alpha_score":s,"leader":a.top1,
                "is_leader":t==a.top1,"w1":float(a.w1),
            })
    return pd.DataFrame(rows)


def replay_confirmed_flip(
    allocation_table,
    armed,
    mats,
    baskets,
    *,
    start="2017-02-01",
    end="2026-07-01",
    cost=.001,
    confirm_loss=.03,
    fired_top1_weight=.25,
):
    dates=mats["Open"].index
    cols=list(mats["Open"].columns)
    ti={t:i for i,t in enumerate(cols)}
    O=mats["Open"].to_numpy(float)
    C=mats["Close"].reindex(index=dates,columns=cols).to_numpy(float)

    tab=allocation_table.copy()
    tab["entry_date"]=pd.to_datetime(tab.entry_date)
    tab["signal_date"]=pd.to_datetime(tab.signal_date)
    by_entry={pd.Timestamp(d):g.copy() for d,g in tab.groupby("entry_date")}
    arm={(pd.Timestamp(r.signal_date),str(r.basket)):bool(r.armed) for r in armed.itertuples(index=False)}

    start_i=dates.searchsorted(pd.Timestamp(start))
    end_i=dates.searchsorted(pd.Timestamp(end),side="right")-1
    B=len(baskets);N=len(cols)
    units=np.zeros((B,N));cash=np.ones(B)
    cur_top1=np.full(B,-1,int);cur_top2=np.full(B,-1,int)
    base_w1=np.zeros(B);entry_ref=np.full(B,np.nan)
    arm_now=np.zeros(B,bool);fired=np.zeros(B,bool);pending=np.zeros(B,bool)
    target=np.zeros((B,N));lastdesired=np.zeros((B,N))
    equity=[];turns=[];out_dates=[];fires=np.zeros(B,int)

    for i in range(start_i,end_i):
        prices=O[i]
        bad=~np.isfinite(prices)|(prices<=0)
        if ((units>0)&bad[None,:]).any():
            raise ValueError(f"missing held open {dates[i]}")
        p=np.where(bad,0,prices)
        value=cash+units@p

        if dates[i] in by_entry:
            g=by_entry[dates[i]]
            target[:]=0
            for r in g.itertuples(index=False):
                b=int(r.basket);i1=ti[r.top1];i2=ti[r.top2]
                cur_top1[b]=i1;cur_top2[b]=i2;base_w1[b]=float(r.w1)
                target[b,i1]=float(r.w1);target[b,i2]=float(r.w2)
                entry_ref[b]=prices[i1]
                arm_now[b]=arm.get((pd.Timestamp(r.signal_date),str(r.basket)),False)
                fired[b]=False;pending[b]=False

        # Close t-1 triggered this open's action.
        just_fire=pending.copy()
        fired|=just_fire
        fires+=just_fire.astype(int)
        pending[:]=False

        desired=target.copy()
        flip=fired & np.isclose(base_w1,.75) & (cur_top1>=0) & (cur_top2>=0)
        for b in np.where(flip)[0]:
            desired[b,:]=0
            desired[b,cur_top1[b]]=fired_top1_weight
            desired[b,cur_top2[b]]=1-fired_top1_weight

        change=np.max(np.abs(desired-lastdesired),axis=1)>1e-12
        if (desired[:,bad]>0).any():
            raise ValueError(f"selected missing open {dates[i]}")
        after=value.copy()
        traded=np.zeros(B)
        for _ in range(10):
            traded=np.abs(desired*after[:,None]-units*p[None,:]).sum(axis=1)
            after=np.where(change,value-cost*traded,value)
        turnover=np.where(change,traded/value,0.)
        safe=np.where(bad,1,prices)
        units=np.where(change[:,None],desired*after[:,None]/safe[None,:],units)
        cash=np.where(change,after*(1-desired.sum(axis=1)),cash)

        # Confirmation observed only at today's close; action earliest next open.
        for b in np.where(arm_now & ~fired & (cur_top1>=0))[0]:
            px=C[i,cur_top1[b]]
            if np.isfinite(px) and np.isfinite(entry_ref[b]) and px<=entry_ref[b]*(1-confirm_loss):
                pending[b]=True

        nextp=O[i+1]
        badnext=~np.isfinite(nextp)|(nextp<=0)
        if ((units>0)&badnext[None,:]).any():
            raise ValueError(f"missing next-open valuation {dates[i+1]}")
        e=cash+units@np.where(badnext,0,nextp)
        equity.append(e);turns.append(turnover);out_dates.append(dates[i+1])
        lastdesired=desired

    return pd.DatetimeIndex(out_dates),np.array(equity).T,np.array(turns).T,fires
