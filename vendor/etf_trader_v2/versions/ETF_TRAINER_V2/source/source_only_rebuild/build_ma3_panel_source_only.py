#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.a4_cluster_destination import (
    DEFAULT_SEED,
    RECOVERED_SOURCE_SHA256,
    build_persistent_membership,
)

def _select_cluster_tickers(primary_cols, primary_cats, cluster_cols, cluster_cats):
    primary=list(map(str,primary_cols))
    cluster_set=set(map(str,cluster_cols))
    missing_prices=sorted(set(primary)-cluster_set)
    missing_meta=sorted(set(primary)-set(cluster_cats))
    if missing_prices or missing_meta:
        raise ValueError("cluster raw is missing primary ticker(s): "+f"prices={missing_prices[:10]} metadata={missing_meta[:10]}")
    category_mismatch=sorted(t for t in primary if str(primary_cats[t]) != str(cluster_cats[t]))
    if category_mismatch: raise ValueError(f"cluster raw category mismatch: {category_mismatch[:10]}")
    extras=sorted(cluster_set-set(primary))
    return primary,extras

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--data",required=True,help="primary raw ticker CSV folder used for MA3 features/targets")
    ap.add_argument("--cluster-data",default=None,help="optional distinct raw ticker CSV folder used only for S3B membership")
    ap.add_argument("--output",default="artifact/ma3_source_only")
    args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    mats,cats,manifest=load_ticker_csv_folder(args.data)
    cols=list(mats["Close"].columns)
    k.ALL_TICKERS=sorted(cols);k.TICKER_CATEGORY=cats;k.CATEGORY_TICKERS={c:sorted([t for t in cols if cats[t]==c]) for c in sorted(set(cats.values()))}
    primary_data=Path(args.data).resolve();cluster_data=Path(args.cluster_data).resolve() if args.cluster_data else primary_data
    if cluster_data==primary_data: cluster_mats,cluster_cats,cluster_manifest=mats,cats,manifest
    else: cluster_mats,cluster_cats,cluster_manifest=load_ticker_csv_folder(cluster_data,allow_missing=True)
    cluster_cols,cluster_extra_tickers=_select_cluster_tickers(cols,cats,cluster_mats["Close"].columns,cluster_cats)
    ref="SPY" if "SPY" in cluster_cols else cluster_mats["Close"][cluster_cols].notna().sum().idxmax()
    calendar=pd.DatetimeIndex(cluster_mats["Close"].index[cluster_mats["Close"][ref].notna()]).sort_values().unique()
    close_cluster=cluster_mats["Close"].reindex(index=calendar,columns=cluster_cols).ffill(limit=3)
    open_cluster=cluster_mats["Open"].reindex(index=calendar,columns=cluster_cols)
    dates=k.month_end_dates(calendar);dates=dates[(dates>=calendar.min()+pd.Timedelta(days=365))&(dates<calendar.max())]
    cal_pos={pd.Timestamp(d):i for i,d in enumerate(calendar)};valid_count=close_cluster.notna().rolling(252,min_periods=1).sum()
    label_rows=[]
    for sd in dates:
        i=cal_pos.get(pd.Timestamp(sd))
        if i is None or i+1>=len(calendar):continue
        entry_date=calendar[i+1];entry=open_cluster.loc[entry_date,cluster_cols];eligible=(valid_count.loc[sd,cluster_cols]>=126)&entry.notna();tick=[t for t in cluster_cols if bool(eligible[t])]
        if not tick:continue
        rec=pd.DataFrame({"ticker":tick});rec["signal_date"]=pd.Timestamp(sd);rec["entry_date"]=entry_date;ev=entry.reindex(tick).to_numpy(float)
        for h in (42,63):
            xi=i+1+h
            if xi>=len(calendar): rec[f"exit_date_{h}"]=pd.NaT;rec[f"fwd_ret_{h}"]=np.nan
            else:
                xd=calendar[xi];rec[f"exit_date_{h}"]=xd;rec[f"fwd_ret_{h}"]=open_cluster.loc[xd,tick].to_numpy(float)/ev-1.0
        label_rows.append(rec)
    if not label_rows: raise RuntimeError("no causal label panel available for S3B cluster rebuild")
    cluster_labels=pd.concat(label_rows,ignore_index=True)
    cluster_build=build_persistent_membership(close_cluster,cluster_labels,dates,cluster_cats,seed=DEFAULT_SEED)
    clusters=cluster_build.membership

    close=mats["Close"].astype(float);openp=mats["Open"].astype(float);high=mats["High"].astype(float);low=mats["Low"].astype(float);volume=mats["Volume"].astype(float)
    idx=close.index;logc=np.log(close.where(close>0));lr=logc.diff();ret=close.pct_change(fill_method=None);prev_close=close.shift(1);gap=openp/prev_close-1;intraday=close/openp-1
    tr=pd.DataFrame(np.maximum.reduce([(high-low).to_numpy(),(high-prev_close).abs().to_numpy(),(low-prev_close).abs().to_numpy()]),index=idx,columns=cols)
    dollar_vol=volume*close;signed_vol=np.sign(ret)*volume;amihud=ret.abs()/dollar_vol.replace(0,np.nan)
    F={}
    for h in [3,5,10,21,42,63,126,252]: F[f"ret_{h}"]=close.pct_change(h,fill_method=None)
    F["mom_21_5"]=close.shift(5)/close.shift(21)-1;F["mom_63_5"]=close.shift(5)/close.shift(63)-1;F["mom_126_21"]=close.shift(21)/close.shift(126)-1;F["mom_252_21"]=close.shift(21)/close.shift(252)-1
    F["acc_3_10"]=F["ret_3"]-(3/10)*F["ret_10"];F["acc_5_21"]=F["ret_5"]-(5/21)*F["ret_21"];F["acc_21_63"]=F["ret_21"]-(21/63)*F["ret_63"];F["acc_63_126"]=F["ret_63"]-(63/126)*F["ret_126"];F["jerk"]=F["acc_3_10"]-F["acc_5_21"]
    for h in [20,50,100,200]: F[f"sma_ratio_{h}"]=close/close.rolling(h,min_periods=h).mean()-1
    for h in [21,63,126]:
        F[f"dist_high_{h}"]=close/close.rolling(h,min_periods=h).max()-1;F[f"dd_{h}"]=F[f"dist_high_{h}"];F[f"eff_{h}"]=lr.rolling(h,min_periods=h).sum().abs()/lr.abs().rolling(h,min_periods=h).sum().replace(0,np.nan)
    for h in [10,21,63,126]: F[f"vol_{h}"]=lr.rolling(h,min_periods=h).std()*np.sqrt(252)
    for h in [21,63]:
        neg=lr.where(lr<0,0.0);F[f"downvol_{h}"]=np.sqrt(neg.pow(2).rolling(h,min_periods=h).mean()*252);F[f"skew_{h}"]=lr.rolling(h,min_periods=h).skew()
    F["kurt_63"]=lr.rolling(63,min_periods=63).kurt();F["vol_ratio_10_63"]=F["vol_10"]/F["vol_63"];F["vol_ratio_21_126"]=F["vol_21"]/F["vol_126"]
    F["atr_14"]=tr.rolling(14,min_periods=14).mean()/close;F["atr_ratio"]=F["atr_14"]/(tr.rolling(63,min_periods=63).mean()/close)
    F["energy_21"]=lr.pow(2).rolling(21,min_periods=21).sum();F["energy_63"]=lr.pow(2).rolling(63,min_periods=63).sum();F["directional_energy_21"]=lr.rolling(21,min_periods=21).sum().pow(2)/F["energy_21"].replace(0,np.nan);F["directional_energy_63"]=lr.rolling(63,min_periods=63).sum().pow(2)/F["energy_63"].replace(0,np.nan)
    mean20=close.rolling(20,min_periods=20).mean();std20=close.rolling(20,min_periods=20).std();mean63=close.rolling(63,min_periods=63).mean();std63=close.rolling(63,min_periods=63).std()
    F["boll_z20"]=(close-mean20)/std20.replace(0,np.nan);F["boll_z63"]=(close-mean63)/std63.replace(0,np.nan)
    delta=close.diff();gain=delta.clip(lower=0).rolling(14,min_periods=14).mean();loss=(-delta.clip(upper=0)).rolling(14,min_periods=14).mean();F["rsi14"]=100-100/(1+gain/loss.replace(0,np.nan))
    F["stoch63"]=(close-low.rolling(63,min_periods=63).min())/(high.rolling(63,min_periods=63).max()-low.rolling(63,min_periods=63).min()).replace(0,np.nan)
    F["gap_mean5"]=gap.rolling(5,min_periods=5).mean();F["gap_vol21"]=gap.rolling(21,min_periods=21).std();F["gap_min5"]=gap.rolling(5,min_periods=5).min();F["intraday_mean5"]=intraday.rolling(5,min_periods=5).mean();rng=(high-low)/close;F["range_z20"]=(rng-rng.rolling(20,min_periods=20).mean())/rng.rolling(20,min_periods=20).std().replace(0,np.nan)
    lv=np.log1p(volume)
    for h in [20,63]:F[f"volume_z{h}"]=(lv-lv.rolling(h,min_periods=h).mean())/lv.rolling(h,min_periods=h).std().replace(0,np.nan)
    F["volume_ratio5_20"]=volume.rolling(5,min_periods=5).mean()/volume.rolling(20,min_periods=20).mean()-1;F["volume_ratio20_63"]=volume.rolling(20,min_periods=20).mean()/volume.rolling(63,min_periods=63).mean()-1
    F["signed_volume21"]=signed_vol.rolling(21,min_periods=21).sum()/volume.rolling(21,min_periods=21).sum().replace(0,np.nan);F["signed_volume63"]=signed_vol.rolling(63,min_periods=63).sum()/volume.rolling(63,min_periods=63).sum().replace(0,np.nan)
    F["pv_corr21"]=ret.rolling(21,min_periods=21).corr(lv.diff());F["pv_corr63"]=ret.rolling(63,min_periods=63).corr(lv.diff());F["amihud21"]=np.log1p(amihud.rolling(21,min_periods=21).mean()*1e9);F["amihud63"]=np.log1p(amihud.rolling(63,min_periods=63).mean()*1e9);F["dollar_volume_z20"]=(np.log1p(dollar_vol)-np.log1p(dollar_vol).rolling(20,min_periods=20).mean())/np.log1p(dollar_vol).rolling(20,min_periods=20).std().replace(0,np.nan)
    F["ret21_vol63"]=F["ret_21"]/F["vol_63"].replace(0,np.nan);F["ret63_vol126"]=F["ret_63"]/F["vol_126"].replace(0,np.nan)

    locmap={d:i for i,d in enumerate(idx)};log_arr=logc.to_numpy(float);lr_arr=lr.to_numpy(float);op_arr=openp.to_numpy(float);ticker_pos={t:i for i,t in enumerate(cols)}
    rows=[]
    for sd,g in clusters.groupby("signal_date",sort=True):
        if sd not in locmap:continue
        i=locmap[sd];ids=[ticker_pos[t] for t in g.ticker if t in ticker_pos];tick=[cols[j] for j in ids]
        if not ids:continue
        gm=g.set_index("ticker");base=pd.DataFrame({"signal_date":sd,"ticker":tick,"cluster_id":gm.loc[tick,"cluster_id"].to_numpy()})
        for name,frame in F.items():base[name]=frame.iloc[i,ids].to_numpy()
        for w in [21,63]:
            if i-w+1>=0:
                Y=log_arr[i-w+1:i+1,ids];x=np.arange(w,dtype=float);xc=x-x.mean();den=(xc*xc).sum();ym=np.nanmean(Y,axis=0);centered=Y-ym;slope=np.nansum(centered*xc[:,None],axis=0)/den;fit=ym[None,:]+slope[None,:]*xc[:,None];ssr=np.nansum((Y-fit)**2,axis=0);sst=np.nansum(centered**2,axis=0);base[f"slope_{w}"]=slope;base[f"r2_{w}"]=1-ssr/np.where(sst>0,sst,np.nan)
                R=lr_arr[i-w+1:i+1,ids];a=R[1:];b=R[:-1];am=np.nanmean(a,axis=0);bm=np.nanmean(b,axis=0);num=np.nansum((a-am)*(b-bm),axis=0);den2=np.sqrt(np.nansum((a-am)**2,axis=0)*np.nansum((b-bm)**2,axis=0));base[f"autocorr1_{w}"]=num/np.where(den2>0,den2,np.nan)
        w=64
        if i-w+1>=0:
            R=lr_arr[i-w+1:i+1,ids];R=R-np.nanmean(R,axis=0,keepdims=True);R=np.nan_to_num(R,nan=0.0);powr=np.abs(np.fft.rfft(R,axis=0))[1:]**2;total=powr.sum(axis=0);p=powr/np.where(total>0,total,np.nan);base["spectral_entropy64"]=-(p*np.log(p+1e-15)).sum(axis=0)/np.log(powr.shape[0]);base["low_freq_energy64"]=powr[:4].sum(axis=0)/np.where(total>0,total,np.nan);base["dominant_energy64"]=powr.max(axis=0)/np.where(total>0,total,np.nan)
        if i+1<len(idx):
            entry=op_arr[i+1,ids];base["entry_date"]=idx[i+1]
            for h in [21,42,63]:
                if i+1+h<len(idx):base[f"fwd_ret_{h}"]=op_arr[i+1+h,ids]/entry-1;base[f"exit_date_{h}"]=idx[i+1+h]
                else:base[f"fwd_ret_{h}"]=np.nan;base[f"exit_date_{h}"]=pd.NaT
        rows.append(base)
    panel=pd.concat(rows,ignore_index=True)
    base_cols=["signal_date","entry_date","ticker","cluster_id"];num_features=[c for c in panel.columns if c not in base_cols and not c.startswith("fwd_ret_") and not c.startswith("exit_date_")]
    panel[num_features]=panel[num_features].replace([np.inf,-np.inf],np.nan)
    for c in num_features:panel[c+"_rank"]=panel.groupby("signal_date")[c].rank(pct=True,method="average")
    for c in ["ret_21","ret_63","ret_126","vol_63","acc_5_21","eff_63","signed_volume21"]:
        panel[f"cluster_{c}_mean"]=panel.groupby(["signal_date","cluster_id"])[c].transform("mean");panel[f"{c}_vs_cluster"]=panel[c]-panel[f"cluster_{c}_mean"];panel[f"{c}_cluster_rank"]=panel.groupby(["signal_date","cluster_id"])[c].rank(pct=True,method="average");panel[f"cluster_{c}_univ_rank"]=panel.groupby("signal_date")[f"cluster_{c}_mean"].rank(pct=True,method="average")
    panel["cluster_breadth21"]=panel.groupby(["signal_date","cluster_id"])["ret_21"].transform(lambda x:(x>0).mean());panel["cluster_breadth63"]=panel.groupby(["signal_date","cluster_id"])["ret_63"].transform(lambda x:(x>0).mean());panel["univ_breadth21"]=panel.groupby("signal_date")["ret_21"].transform(lambda x:(x>0).mean());panel["univ_breadth63"]=panel.groupby("signal_date")["ret_63"].transform(lambda x:(x>0).mean())
    context_extra=[c for c in panel.columns if (c.startswith("cluster_") or c.endswith("_vs_cluster") or c.endswith("_cluster_rank")) and pd.api.types.is_numeric_dtype(panel[c])]
    for c in context_extra:
        rc=c+"_rank"
        if rc not in panel:panel[rc]=panel.groupby("signal_date")[c].rank(pct=True,method="average")
    for h in [21,42,63]:panel[f"target_rank_{h}"]=panel.groupby("signal_date")[f"fwd_ret_{h}"].rank(pct=True,method="average")
    panel["target_multi_rank"]=.45*panel.target_rank_21+.35*panel.target_rank_42+.20*panel.target_rank_63
    panel["target_tailmix"]=.60*panel.target_rank_21**4+.25*panel.target_rank_42**4+.15*panel.target_rank_63**4
    panel["target_tailmix6"]=.60*panel.target_rank_21**6+.25*panel.target_rank_42**6+.15*panel.target_rank_63**6
    panel["target_tailmix_top"]=.55*panel.target_rank_21**6+.30*panel.target_rank_42**4+.15*panel.target_rank_63**2
    panel["target_relevance"]=np.minimum(9,np.floor(panel.target_multi_rank*10)).astype("Int64")
    for q in [5,10,15,20,25]:panel[f"top{q:02d}"]=(panel.target_multi_rank>=1-q/100).astype("Int64")

    panel.to_pickle(out/"RAW_FEATURE_PANEL.pkl");clusters.to_csv(out/"DYNAMIC_CLUSTER_MEMBERSHIP.csv",index=False);cluster_build.source_audit.to_csv(out/"CLUSTER_SOURCE_DATE_AUDIT.csv",index=False);cluster_build.balance_audit.to_csv(out/"CLUSTER_BALANCE_BY_DATE.csv",index=False)
    (out/"RAW_FEATURE_PANEL_MANIFEST.json").write_text(json.dumps({"status":"SOURCE_ONLY","productive_inputs":["primary raw per-ticker OHLCV CSV","cluster raw per-ticker OHLCV CSV","universe.csv","repository source"],"historical_cluster_membership_consumed":False,"primary_raw_manifest":manifest,"cluster_raw_manifest":cluster_manifest,"cluster_raw_distinct":bool(cluster_data!=primary_data),"cluster_raw_extra_tickers_ignored":cluster_extra_tickers,"cluster_productive_tickers":len(cluster_cols),"rows":len(panel),"tickers":int(panel.ticker.nunique()),"signal_dates":int(panel.signal_date.nunique()),"dynamic_clusters_generated_from_raw":True,"cluster_producer":"src/etf_trader/source_only/a4_cluster_destination.py::build_persistent_membership","cluster_seed":int(DEFAULT_SEED),"cluster_recovered_source_sha256":RECOVERED_SOURCE_SHA256},indent=2,default=str)+"\n")
    print(json.dumps({"status":"SOURCE_ONLY_PANEL_BUILT","rows":len(panel),"signal_dates":int(panel.signal_date.nunique())},indent=2));return 0
if __name__=="__main__": raise SystemExit(main())
