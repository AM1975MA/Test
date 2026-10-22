"""Corrected MA3 maturity-safe producer.

This module reproduces the 2026-09-23 target-specific producer correction:
- target = 0.45*r21^1.5 + 0.35*r42^1.5 + 0.20*r63^1.5
- ExtraTrees(max_features=.6, min_samples_leaf=30, max_depth=9, seed=101)
- annual expanding maturity-safe fits
- downstream smoothing 40/30/30, power 1.10, BASE/TAIL blend 47.5/52.5
- continuous two-name allocation weight used by V6 / High-CAGR24

Productive inputs are only source-generated RAW_FEATURE_PANEL, source-generated TIT_R,
the canonical basket membership and the ticker order of the raw price matrices.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer


FEATURES_42: tuple[str, ...] = (
    "cluster_acc_5_21_univ_rank",
    "cluster_acc_5_21_mean_rank",
    "intraday_mean5_rank",
    "mom_21_5_rank",
    "atr_14_rank",
    "cluster_eff_63_univ_rank",
    "cluster_eff_63_mean_rank",
    "jerk_rank",
    "acc_5_21_rank",
    "mom_63_5_rank",
    "boll_z20_rank",
    "vol_10_rank",
    "slope_63_rank",
    "cluster_ret_21_univ_rank",
    "cluster_ret_21_mean_rank",
    "downvol_21_rank",
    "directional_energy_63_rank",
    "energy_21_rank",
    "eff_63_rank",
    "vol_21_rank",
    "autocorr1_21_rank",
    "cluster_breadth63_rank",
    "rsi14_rank",
    "ret_21_vs_cluster_rank",
    "volume_ratio5_20_rank",
    "downvol_63_rank",
    "vol_63_vs_cluster_rank",
    "ret_21_cluster_rank",
    "ret_5_rank",
    "acc_21_63_rank",
    "ret_63_rank",
    "vol_63_rank",
    "ret_21_rank",
    "eff_63_cluster_rank",
    "energy_63_rank",
    "dominant_energy64_rank",
    "slope_21_rank",
    "vol_126_rank",
    "volume_ratio20_63_rank",
    "atr_ratio_rank",
    "eff_63_vs_cluster_rank",
    "dd_21_rank",
)

TARGET_POWER = 1.5
TARGET_WEIGHTS = (0.45, 0.35, 0.20)
MODEL_KW = dict(
    n_estimators=120,
    max_features=0.6,
    min_samples_leaf=30,
    max_depth=9,
    random_state=101,
)

TAIL_LAG_WEIGHTS = (0.40, 0.30, 0.30)
TAIL_POWER = 1.10
BASE_WEIGHT = 0.475
TAIL_WEIGHT = 0.525


@dataclass(frozen=True)
class ProducerResult:
    predictions: pd.DataFrame
    calendar: pd.DataFrame
    score: np.ndarray
    base: np.ndarray
    tail: np.ndarray
    fit_audit: pd.DataFrame


@dataclass(frozen=True)
class AllocationResult:
    d1: np.ndarray
    d2: np.ndarray
    weight1: np.ndarray
    margin: np.ndarray


def corrected_target(panel: pd.DataFrame) -> pd.Series:
    r21=panel["target_rank_21"].astype(float)
    r42=panel["target_rank_42"].astype(float)
    r63=panel["target_rank_63"].astype(float)
    w21,w42,w63=TARGET_WEIGHTS
    return w21*r21.pow(TARGET_POWER)+w42*r42.pow(TARGET_POWER)+w63*r63.pow(TARGET_POWER)


def fit_corrected_producer(
    panel: pd.DataFrame,
    tit_r: pd.DataFrame,
    ticker_order: Sequence[str],
    *,
    feature_cols: Sequence[str] = FEATURES_42,
    start_year: int = 2017,
    end_year: int = 2026,
    n_jobs: int = 1,
) -> ProducerResult:
    df=panel.copy()
    df["signal_date"]=pd.to_datetime(df["signal_date"])
    df["exit_date_63"]=pd.to_datetime(df["exit_date_63"])
    missing=[c for c in feature_cols if c not in df.columns]
    if missing:
        raise KeyError(f"missing corrected-producer features: {missing}")
    df["CORRECTED_TARGET"]=corrected_target(df)

    schedule=tit_r.copy()
    for c in ("signal_date","entry_date","exit_date"):
        schedule[c]=pd.to_datetime(schedule[c])
    if "TIT_R" not in schedule.columns:
        raise KeyError("TIT_R column missing from source-generated Titanium schedule")
    cal=(schedule[["signal_date","entry_date","exit_date"]]
         .drop_duplicates()
         .sort_values("signal_date")
         .reset_index(drop=True))
    base=schedule[["signal_date","ticker","TIT_R"]].copy()

    outs=[]
    audit=[]
    for yr in range(start_year,end_year+1):
        a=pd.Timestamp(f"{yr}-01-01")
        b=pd.Timestamp(f"{yr+1}-01-01")
        tr=df[
            (df["signal_date"]<a)
            &(df["exit_date_63"]<a)
            &df["CORRECTED_TARGET"].notna()
        ].copy()
        pr=df[
            (df["signal_date"]>=a)
            &(df["signal_date"]<b)
            &df["signal_date"].isin(cal["signal_date"])
        ].copy().reset_index(drop=True)
        if pr.empty:
            continue
        if tr.empty:
            raise RuntimeError(f"no maturity-safe training rows for {yr}")
        imp=SimpleImputer(strategy="median")
        xtr=imp.fit_transform(tr[list(feature_cols)])
        xp=imp.transform(pr[list(feature_cols)])
        model=ExtraTreesRegressor(n_jobs=n_jobs,**MODEL_KW)
        model.fit(xtr,tr["CORRECTED_TARGET"].to_numpy(float))
        pr["TAIL_EXTRA_RAW"]=model.predict(xp)
        pr["TAIL_EXTRA"]=pr.groupby("signal_date")["TAIL_EXTRA_RAW"].rank(
            pct=True,method="average"
        )
        outs.append(pr[["signal_date","ticker","TAIL_EXTRA"]])
        audit.append({
            "year":yr,
            "n_train":int(len(tr)),
            "n_predict":int(len(pr)),
            "max_train_signal":str(tr["signal_date"].max().date()),
            "max_train_exit63":str(tr["exit_date_63"].max().date()),
            "cutoff":str(a.date()),
            "maturity_ok":bool(
                (tr["signal_date"]<a).all() and (tr["exit_date_63"]<a).all()
            ),
        })
    if not outs:
        raise RuntimeError("corrected producer generated no predictions")

    pred=pd.concat(outs,ignore_index=True).merge(
        base,on=["signal_date","ticker"],how="inner",validate="one_to_one"
    ).rename(columns={"TIT_R":"BASE"})

    tickers=list(map(str,ticker_order))
    dates=pd.DatetimeIndex(cal["signal_date"])
    B=(pred.pivot(index="signal_date",columns="ticker",values="BASE")
       .reindex(index=dates,columns=tickers).to_numpy(float))
    T=(pred.pivot(index="signal_date",columns="ticker",values="TAIL_EXTRA")
       .reindex(index=dates,columns=tickers).to_numpy(float))

    lag1=np.vstack([T[:1],T[:-1]])
    lag2=np.vstack([T[:1],T[:1],T[:-2]])
    a0,a1,a2=TAIL_LAG_WEIGHTS
    smooth=a0*T+a1*lag1+a2*lag2
    transformed=np.power(np.clip(smooth,0.0,1.0),TAIL_POWER)
    score=BASE_WEIGHT*B+TAIL_WEIGHT*transformed
    return ProducerResult(
        predictions=pred,
        calendar=cal,
        score=score,
        base=B,
        tail=T,
        fit_audit=pd.DataFrame(audit),
    )


def basket_arrays(
    membership: pd.DataFrame,
    ticker_order: Sequence[str],
    *,
    n_baskets: int | None = 500,
) -> tuple[np.ndarray,np.ndarray]:
    ti={t:i for i,t in enumerate(map(str,ticker_order))}
    mem=membership.copy()
    mem["ticker"]=mem["ticker"].astype(str)
    groups={
        int(b):[t for t in g["ticker"] if t in ti]
        for b,g in mem.groupby("basket",sort=True)
    }
    if n_baskets is None:
        n_baskets=max(groups)+1
    if set(range(n_baskets)).difference(groups):
        raise ValueError("basket membership does not cover every expected basket id")
    L=max(len(groups[b]) for b in range(n_baskets))
    BM=np.zeros((n_baskets,L),dtype=np.int32)
    BOK=np.zeros((n_baskets,L),dtype=bool)
    for b in range(n_baskets):
        ids=[ti[t] for t in groups[b]]
        if len(ids)<2:
            raise ValueError(f"basket {b} has fewer than two tradable members")
        BM[b,:len(ids)]=ids
        BOK[b,:len(ids)]=True
    return BM,BOK


def allocations_from_score(
    score: np.ndarray,
    calendar: pd.DataFrame,
    daily_dates: pd.DatetimeIndex,
    basket_matrix: np.ndarray,
    basket_valid: np.ndarray,
    *,
    continuous: bool = True,
) -> AllocationResult:
    B=basket_matrix.shape[0]
    D=len(daily_dates)
    d1=np.full((B,D),-1,np.int16)
    d2=np.full_like(d1,-1)
    wg=np.ones((B,D),dtype=float)
    margin=np.zeros((B,D),dtype=float)

    for m,row in enumerate(calendar.itertuples(index=False)):
        a=int(daily_dates.searchsorted(pd.Timestamp(row.entry_date)))
        e=int(daily_dates.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=D or e<=a:
            continue
        S=np.where(basket_valid,score[m,basket_matrix],-np.inf)
        top=np.argpartition(S,-2,axis=1)[:,-2:]
        ts=np.take_along_axis(S,top,axis=1)
        order=np.argsort(-ts,axis=1)
        top=np.take_along_axis(top,order,axis=1)
        ts=np.take_along_axis(ts,order,axis=1)
        ids=np.take_along_axis(basket_matrix,top,axis=1)
        mg=ts[:,0]-ts[:,1]
        if continuous:
            w=.60+.40*np.minimum(mg/.13,1.0)**2
        else:
            w=np.where(mg>=.12,1.0,.75)
        d1[:,a:e]=ids[:,0,None]
        d2[:,a:e]=ids[:,1,None]
        wg[:,a:e]=w[:,None]
        margin[:,a:e]=mg[:,None]
    return AllocationResult(d1=d1,d2=d2,weight1=wg,margin=margin)
