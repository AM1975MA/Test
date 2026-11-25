"""Report duration frequencies and compare net results on a common calendar."""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd


def comparison(root):
    monthly = pd.read_csv(root/"MONTHLY.csv")
    index = ["market","bps","lag","stop_slippage_bps","month"]
    paired = monthly.pivot(index=index,columns="mode",values="ret")
    assert not paired.isna().any().any()
    diff = np.log1p(paired).sub(np.log1p(paired.OPEN1),axis=0)
    rows = []
    for window, masks in (
        ("ALL",np.ones(len(diff),bool)),
        ("FROM_2023",diff.index.get_level_values("month") >= "2023-01"),
    ):
        for (bps,lag,slip), section in diff[masks].groupby(level=["bps","lag","stop_slippage_bps"]):
            panel = section.droplevel(["bps","lag","stop_slippage_bps"]).unstack("market")
            assert not panel.isna().any().any()
            length = len(panel)
            rng = np.random.default_rng(20261125)
            ids = (rng.integers(0,length,(5000,(length+5)//6,1))+np.arange(6)).reshape(5000,-1)[:,:length]%length
            point = panel.to_numpy().mean(axis=0)*1200
            boot = panel.to_numpy()[ids].mean(axis=1)*1200
            spread = boot.std(axis=0,ddof=1)
            active = spread > 1e-12
            crit = np.quantile(np.max(abs((boot[:,active]-point[active])/spread[active]),axis=1),.95)
            ranks = pd.Series(point,index=panel.columns)
            for j,(mode,market) in enumerate(panel.columns):
                lo,hi = np.quantile(boot[:,j],[.025,.975])
                rows.append(dict(window=window,bps=bps,lag=lag,stop_slippage_bps=slip,
                                 market=market,mode=mode,months=length,annual_log_delta_pp=point[j],
                                 low_nominal=lo,high_nominal=hi,low_simultaneous=point[j]-crit*spread[j],
                                 high_simultaneous=point[j]+crit*spread[j],worst_market_pp=ranks[mode].min()))
    pd.DataFrame(rows).to_csv(root/"CONFIDENCE.csv",index=False)


def local(root):
    features = pd.read_csv(root/"FEATURES.csv")
    labels = pd.read_csv(root/"MATCHED_LABELS.csv")
    master = features.merge(labels,on=["market","index","bps"],validate="one_to_one")
    dates = pd.read_csv(root/"TIMING.csv")
    dates = dates[dates["mode"].ne("MINVAR_OPEN3")]
    merged = master.merge(dates[["market","bps","date","mode","opening"]],on=["market","bps","date"],validate="one_to_many")
    rows = []
    for (market,bps,mode), data in merged.groupby(["market","bps","mode"]):
        for period, df in (("ALL",data),("FROM_2023",data[data.month >= "2023-01"])):
            action = df.opening.to_numpy()-1
            gains = df[[f"log_gain_{i}" for i in range(1,6)]].to_numpy()
            pnl = gains[np.arange(len(action)),action]*10000
            delay = action>0
            rows.append(dict(market=market,bps=bps,mode=mode,window=period,rotations=len(action),
                             waits=int(delay.sum()),mean_gain_bp=pnl.mean(),
                             gain_bp_when_wait=float(pnl[delay].mean()) if delay.any() else np.nan,
                             wait_win_rate=float((pnl[delay]>0).mean()) if delay.any() else np.nan,
                             actual_worst_bp=min(pnl),actual_best_bp=max(pnl),
                             **{f"count_open{i}":int((action==i-1).sum()) for i in range(1,6)}))
    pd.DataFrame(rows).to_csv(root/"ROTATION_EFFECT.csv",index=False)
    stratified=[]
    for (market,bps),g in master.groupby(["market","bps"]):
        for criterion, flag in (
            ("fallback",g.fallback>0),("weak", (g.fallback>0)|(g.proxy_corr<.80)|(g.tracking>.70)),
            ("high_turnover",g.turnover>=1.5),("weak_momentum",g.rel_mom5<0)):
            for group, subset in g.groupby(flag):
                for i in range(2,6):
                    d=subset[f"log_gain_{i}"]*10000
                    stratified.append(dict(market=market,bps=bps,feature=criterion,present=bool(group),opening=i,
                                           rotations=len(d),mean_bp=d.mean(),median_bp=d.median(),win_rate=(d>0).mean()))
    pd.DataFrame(stratified).to_csv(root/"FEATURE_SLICES.csv",index=False)


def main():
    args=argparse.ArgumentParser()
    args.add_argument("--results",type=Path,default=Path(__file__).parent/"results")
    root=args.parse_args().results
    comparison(root)
    local(root)


if __name__=="__main__":
    main()
