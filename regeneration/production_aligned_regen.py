#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, math, os, shutil, time, hashlib, zipfile
from pathlib import Path
from typing import Mapping
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker

EPS=1e-12
BACKTEST_START=pd.Timestamp('2017-01-31')
MODEL_SEEDS=[101,202,303]
OPP_WEIGHTS={'target_top2':.35,'target_spread':.15,'target_excess_max':.35,'target_explosive':.15}


def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,str(path)); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod

def load_mats(data_dir:Path):
    mats={}
    for k in ['Open','High','Low','Close','Volume']:
        x=pd.read_parquet(data_dir/f'{k.upper()}.parquet'); x.index=pd.to_datetime(x.index).tz_localize(None); x.columns=[str(c).upper() for c in x.columns]; mats[k]=x.sort_index().apply(pd.to_numeric,errors='coerce')
    common=sorted(set.intersection(*[set(v.columns) for v in mats.values()]))
    return {k:v.reindex(columns=common) for k,v in mats.items()}

def month_end_dates(idx):
    s=pd.Series(idx,index=idx); return pd.DatetimeIndex(s.groupby(idx.to_period('M')).max().values)

def snapshot(x,dates): return x.reindex(dates)
def cs_pct(x): return x.rank(axis=1,pct=True,method='average')
def cs_robust_dev(x):
    med=x.median(axis=1,skipna=True); q75=x.quantile(.75,axis=1); q25=x.quantile(.25,axis=1); sc=(q75-q25).replace(0,np.nan); return x.sub(med,axis=0).div(sc,axis=0).clip(-8,8)
def rolling_efficiency(logc,h):
    lr=logc.diff(); return (logc-logc.shift(h)).abs()/lr.abs().rolling(h,min_periods=h).sum().replace(0,np.nan)
def rolling_downvol(lr,h):
    neg=lr.where(lr<0,0.0); return np.sqrt(neg.pow(2).rolling(h,min_periods=h).mean()*252)
def rolling_gkvol(O,H,L,C,h):
    rs=.5*np.log(H/L).pow(2)-(2*np.log(2)-1)*np.log(C/O).pow(2); rs=rs.clip(lower=0); return np.sqrt(rs.rolling(h,min_periods=h).mean()*252)
def rolling_rsi(C,h=14):
    d=C.diff(); gain=d.clip(lower=0).rolling(h,min_periods=h).mean(); loss=(-d.clip(upper=0)).rolling(h,min_periods=h).mean(); rs=gain/loss.replace(0,np.nan); return 100-100/(1+rs)
def rolling_sign_entropy(ret,h):
    p=(ret>0).rolling(h,min_periods=h).mean(); return -(p*np.log(p.clip(1e-12,1))+(1-p)*np.log((1-p).clip(1e-12,1)))/np.log(2)
def rolling_cvar10(ret,h):
    arr=ret.to_numpy(float); out=np.full_like(arr,np.nan)
    for i in range(h-1,len(ret)):
        w=arr[i-h+1:i+1]; q=np.nanquantile(w,.10,axis=0); mask=w<=q[None,:]; num=np.nansum(np.where(mask,w,np.nan),axis=0); den=np.sum(mask & np.isfinite(w),axis=0); out[i]=np.where(den>0,num/den,np.nan)
    return pd.DataFrame(out,index=ret.index,columns=ret.columns)
def rolling_autocorr(ret,h,lag=1): return ret.rolling(h,min_periods=h).corr(ret.shift(lag))
def rolling_slope(logc,h):
    x=np.arange(h,dtype=float); xc=x-x.mean(); den=(xc*xc).sum(); return logc.rolling(h,min_periods=h).apply(lambda y: np.dot(y-y.mean(),xc)/den,raw=True)
def rolling_r2(logc,h):
    x=np.arange(h,dtype=float); xc=x-x.mean(); den=np.dot(xc,xc)
    def f(y):
        yc=y-y.mean(); d=np.dot(yc,yc); return np.nan if d<=0 else float(np.dot(yc,xc)**2/(den*d))
    return logc.rolling(h,min_periods=h).apply(f,raw=True)
def spectral_entropy_frame(logret,h=64):
    def ent(x):
        x=np.asarray(x,float); x=x-np.nanmean(x); p=np.abs(np.fft.rfft(x))**2; p=p[1:]; s=p.sum()
        if not np.isfinite(s) or s<=0:return np.nan
        p=p/s; return float(-(p*np.log(p+1e-12)).sum()/np.log(len(p)))
    return logret.rolling(h,min_periods=h).apply(ent,raw=True)

def build_compact(mats,base):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]; dates=month_end_dates(C.index)
    logc=np.log(C.where(C>0)); lr=logc.diff(); ret=C.pct_change(fill_method=None); market=ret.mean(axis=1,skipna=True)
    out={}
    for h in [5,10,21,42,63,126,252]: out[f'mom{h}']=snapshot(C.pct_change(h,fill_method=None),dates)
    for h in [21,63,126]:
        out[f'vol{h}']=snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252),dates)
        out[f'downvol{h}']=snapshot(rolling_downvol(lr,h),dates)
        out[f'drawdown{h}']=snapshot(C/C.rolling(h,min_periods=h).max()-1,dates)
        out[f'efficiency{h}']=snapshot(rolling_efficiency(logc,h),dates)
    out['mom126_ex21']=snapshot(C.shift(21)/C.shift(126)-1,dates); out['mom252_ex21']=snapshot(C.shift(21)/C.shift(252)-1,dates)
    out['acc_mom_5_21']=out['mom5']-(5/21)*out['mom21']; out['acc_mom_21_63']=out['mom21']-(21/63)*out['mom63']; out['vol_ratio_21_126']=out['vol21']/out['vol126'].replace(0,np.nan)
    out['skew63']=snapshot(lr.rolling(63,min_periods=63).skew(),dates); out['kurt63']=snapshot(lr.rolling(63,min_periods=63).kurt(),dates)
    out['gkvol21']=snapshot(rolling_gkvol(O,H,L,C,21),dates)
    dollar=V*C; out['log_adv63']=snapshot(np.log1p(dollar.rolling(63,min_periods=63).mean()),dates)
    lv=np.log1p(V); out['volume_surprise21']=snapshot((lv-lv.rolling(21,min_periods=21).mean())/lv.rolling(21,min_periods=21).std().replace(0,np.nan),dates)
    for h in [63,126]:
        cov=ret.rolling(h,min_periods=h).cov(market); var=market.rolling(h,min_periods=h).var(); out[f'beta_mkt{h}']=snapshot(cov.div(var.replace(0,np.nan),axis=0),dates); out[f'corr_mkt{h}']=snapshot(ret.rolling(h,min_periods=h).corr(market),dates)
    out['ma_gap50']=snapshot(C/C.rolling(50,min_periods=50).mean()-1,dates); out['ma_gap200']=snapshot(C/C.rolling(200,min_periods=200).mean()-1,dates)
    out['ema_gap20']=snapshot(C/C.ewm(span=20,adjust=False,min_periods=20).mean()-1,dates); out['ema_gap50']=snapshot(C/C.ewm(span=50,adjust=False,min_periods=50).mean()-1,dates)
    for h in [126,252]: out[f'breakout_pos{h}']=snapshot((C-C.rolling(h,min_periods=h).min())/(C.rolling(h,min_periods=h).max()-C.rolling(h,min_periods=h).min()).replace(0,np.nan),dates)
    out['rsi14']=snapshot(rolling_rsi(C,14),dates); out['positive_frac63']=snapshot((ret>0).rolling(63,min_periods=63).mean(),dates); out['max_loss63']=snapshot(ret.rolling(63,min_periods=63).min(),dates); out['max_gain63']=snapshot(ret.rolling(63,min_periods=63).max(),dates)
    out['cvar10_63']=snapshot(rolling_cvar10(ret,63),dates); out['sign_entropy63']=snapshot(rolling_sign_entropy(ret,63),dates); out['autocorr1_63']=snapshot(rolling_autocorr(ret,63),dates)
    for n in list(out.keys()):
        if n+'_pct' in base.F2D_FEATURES: out[n+'_pct']=cs_pct(out[n])
        if n+'_dev' in base.F2D_FEATURES: out[n+'_dev']=cs_robust_dev(out[n])
    missing=[f for f in base.F2D_FEATURES if f not in out]
    if missing: raise RuntimeError(f'Compact missing {missing}')
    panel=pd.concat([out[f].stack(dropna=False).rename(f) for f in base.F2D_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    return dates,panel,out

def add_labels(panel,O,signal_dates):
    dates=O.index; info=[]
    for k,sd in enumerate(signal_dates):
        if sd not in dates: continue
        i=dates.get_loc(sd)
        if i+1>=len(dates): continue
        rec={'signal_date':sd,'entry_date':dates[i+1]}
        if k+1<len(signal_dates):
            ni=dates.get_loc(signal_dates[k+1]); rec['exit_date']=dates[ni+1] if ni+1<len(dates) else pd.NaT
        else: rec['exit_date']=pd.NaT
        for h in [21,42,63]: rec[f'exit_date_{h}']=dates[i+1+h] if i+1+h<len(dates) else pd.NaT
        info.append(rec)
    out=panel.merge(pd.DataFrame(info),on='signal_date',how='left'); ti={t:j for j,t in enumerate(O.columns)}; pos={d:i for i,d in enumerate(dates)}
    vals={h:np.full(len(out),np.nan) for h in [21,42,63]}; vals['monthly']=np.full(len(out),np.nan)
    for sd,inds0 in out.groupby('signal_date').groups.items():
        inds=np.asarray(list(inds0)); i=pos.get(pd.Timestamp(sd))
        if i is None or i+1>=len(dates): continue
        tix=np.array([ti[t] for t in out.loc[inds,'ticker']],int); entry=i+1
        exd=out.loc[inds[0],'exit_date']
        if pd.notna(exd): vals['monthly'][inds]=O.iloc[pos[pd.Timestamp(exd)],tix].to_numpy()/O.iloc[entry,tix].to_numpy()-1
        for h in [21,42,63]:
            ex=entry+h
            if ex<len(dates): vals[h][inds]=O.iloc[ex,tix].to_numpy()/O.iloc[entry,tix].to_numpy()-1
    out['fwd_ret_monthly']=vals['monthly']
    for h in [21,42,63]: out[f'fwd_ret_{h}']=vals[h]; out[f'target_rank_{h}']=out.groupby('signal_date')[f'fwd_ret_{h}'].rank(pct=True,method='average')
    out['target_rank_pct']=out.groupby('signal_date')['fwd_ret_monthly'].rank(pct=True,method='average'); out['target_top25']=(out.target_rank_pct>=.75).astype('Int64'); out['target_multi_rank']=.45*out.target_rank_21+.35*out.target_rank_42+.20*out.target_rank_63; out['y_tailmix']=.60*out.target_rank_21.astype(float)**4+.25*out.target_rank_42.astype(float)**4+.15*out.target_rank_63.astype(float)**4
    return out

def build_broad(mats,dates,compact_frames,base):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]; logc=np.log(C.where(C>0));lr=logc.diff();ret=C.pct_change(fill_method=None);prev=C.shift(1);gap=O/prev-1;intraday=C/O-1
    tr=pd.DataFrame(np.maximum.reduce([(H-L).to_numpy(),(H-prev).abs().to_numpy(),(L-prev).abs().to_numpy()]),index=C.index,columns=C.columns);dollar=V*C;signed=np.sign(ret)*V;amihud=ret.abs()/dollar.replace(0,np.nan)
    D={}
    for k,v in compact_frames.items():
        if not k.endswith('_pct') and not k.endswith('_dev'): D[k]=v.copy()
    for h in [3,5,10,21,42,63,126,252]: D[f'ret_{h}']=snapshot(C.pct_change(h,fill_method=None),dates)
    D['mom_21_5']=snapshot(C.shift(5)/C.shift(21)-1,dates);D['mom_63_5']=snapshot(C.shift(5)/C.shift(63)-1,dates);D['mom_126_21']=snapshot(C.shift(21)/C.shift(126)-1,dates);D['mom_252_21']=snapshot(C.shift(21)/C.shift(252)-1,dates)
    D['acc_3_10']=D['ret_3']-(3/10)*D['ret_10'];D['acc_5_21_broad']=D['ret_5']-(5/21)*D['ret_21'];D['acc_21_63_broad']=D['ret_21']-(21/63)*D['ret_63'];D['acc_63_126']=D['ret_63']-.5*D['ret_126'];D['jerk']=D['acc_3_10']-D['acc_5_21_broad']
    D['acc_5_21']=D['acc_5_21_broad']; D['acc_21_63']=D['acc_21_63_broad']
    for h in [20,50,100,200]: D[f'sma_ratio_{h}']=snapshot(C/C.rolling(h,min_periods=h).mean()-1,dates)
    for h in [21,63,126]: D[f'dist_high_{h}']=snapshot(C/C.rolling(h,min_periods=h).max()-1,dates);D[f'dd_{h}']=D[f'dist_high_{h}'];D[f'eff_{h}']=snapshot(rolling_efficiency(logc,h),dates)
    for h in [10,21,63,126]: D[f'vol_{h}']=snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252),dates)
    for h in [21,63]: D[f'downvol_{h}']=snapshot(rolling_downvol(lr,h),dates);D[f'skew_{h}']=snapshot(lr.rolling(h,min_periods=h).skew(),dates)
    D['kurt_63']=snapshot(lr.rolling(63,min_periods=63).kurt(),dates);D['vol_ratio_10_63']=D['vol_10']/D['vol_63'].replace(0,np.nan);D['vol_ratio_21_126_broad']=D['vol_21']/D['vol_126'].replace(0,np.nan)
    D['atr_14']=snapshot(tr.rolling(14,min_periods=14).mean()/C,dates);D['atr_ratio']=snapshot((tr.rolling(14,min_periods=14).mean()/C)/(tr.rolling(63,min_periods=63).mean()/C),dates)
    for h in [21,63]:
        D[f'energy_{h}']=snapshot(lr.pow(2).rolling(h,min_periods=h).sum(),dates);D[f'directional_energy_{h}']=snapshot(lr.rolling(h,min_periods=h).sum().pow(2)/lr.pow(2).rolling(h,min_periods=h).sum().replace(0,np.nan),dates)
    mean20=C.rolling(20,min_periods=20).mean();std20=C.rolling(20,min_periods=20).std();mean63=C.rolling(63,min_periods=63).mean();std63=C.rolling(63,min_periods=63).std();D['boll_z20']=snapshot((C-mean20)/std20.replace(0,np.nan),dates);D['boll_z63']=snapshot((C-mean63)/std63.replace(0,np.nan),dates)
    D['rsi14_broad']=snapshot(rolling_rsi(C),dates);D['stoch63']=snapshot((C-L.rolling(63,min_periods=63).min())/(H.rolling(63,min_periods=63).max()-L.rolling(63,min_periods=63).min()).replace(0,np.nan),dates)
    D['gap_mean5']=snapshot(gap.rolling(5,min_periods=5).mean(),dates);D['gap_vol21']=snapshot(gap.rolling(21,min_periods=21).std(),dates);D['gap_min5']=snapshot(gap.rolling(5,min_periods=5).min(),dates);D['intraday_mean5']=snapshot(intraday.rolling(5,min_periods=5).mean(),dates)
    rng=(H-L)/C;D['range_z20']=snapshot((rng-rng.rolling(20,min_periods=20).mean())/rng.rolling(20,min_periods=20).std().replace(0,np.nan),dates)
    lv=np.log1p(V)
    for h in [20,63]: D[f'volume_z{h}']=snapshot((lv-lv.rolling(h,min_periods=h).mean())/lv.rolling(h,min_periods=h).std().replace(0,np.nan),dates)
    D['volume_ratio5_20']=snapshot(V.rolling(5,min_periods=5).mean()/V.rolling(20,min_periods=20).mean()-1,dates);D['volume_ratio20_63']=snapshot(V.rolling(20,min_periods=20).mean()/V.rolling(63,min_periods=63).mean()-1,dates)
    D['signed_volume21']=snapshot(signed.rolling(21,min_periods=21).sum()/V.rolling(21,min_periods=21).sum().replace(0,np.nan),dates);D['signed_volume63']=snapshot(signed.rolling(63,min_periods=63).sum()/V.rolling(63,min_periods=63).sum().replace(0,np.nan),dates)
    D['pv_corr21']=snapshot(ret.rolling(21,min_periods=21).corr(lv.diff()),dates);D['pv_corr63']=snapshot(ret.rolling(63,min_periods=63).corr(lv.diff()),dates)
    D['amihud21']=snapshot(np.log1p(amihud.rolling(21,min_periods=21).mean()*1e9),dates);D['amihud63']=snapshot(np.log1p(amihud.rolling(63,min_periods=63).mean()*1e9),dates)
    ld=np.log1p(dollar);D['dollar_volume_z20']=snapshot((ld-ld.rolling(20,min_periods=20).mean())/ld.rolling(20,min_periods=20).std().replace(0,np.nan),dates)
    D['ret21_vol63']=D['ret_21']/D['vol_63'].replace(0,np.nan);D['ret63_vol126']=D['ret_63']/D['vol_126'].replace(0,np.nan)
    D['slope_21']=snapshot(rolling_slope(logc,21),dates);D['slope_63']=snapshot(rolling_slope(logc,63),dates);D['r2_63']=snapshot(rolling_r2(logc,63),dates);D['autocorr1_21']=snapshot(rolling_autocorr(ret,21),dates);D['autocorr1_63']=snapshot(rolling_autocorr(ret,63),dates);D['spectral_entropy64']=snapshot(spectral_entropy_frame(lr,64),dates)
    aliases={'ma_gap200':'ma_gap200','ma_gap50':'ma_gap50','ema_gap50':'ema_gap50','breakout_pos126':'breakout_pos126','breakout_pos252':'breakout_pos252','positive_frac63':'positive_frac63','max_gain63':'max_gain63','sign_entropy63':'sign_entropy63','gkvol21':'gkvol21','mom126_ex21':'mom126_ex21'}
    for dst,src in aliases.items():
        if src in compact_frames: D[dst]=compact_frames[src]
    for k,v in list(D.items()):
        if not k.endswith('_rank'): D[k+'_rank']=cs_pct(v)
    amap={'beta_mkt63_rank':'beta_mkt63_rank','beta_mkt126_rank':'beta_mkt126_rank','corr_mkt63_rank':'corr_mkt63_rank','corr_mkt126_rank':'corr_mkt126_rank','ma_gap200_rank':'ma_gap200_rank','ma_gap50_rank':'ma_gap50_rank','ema_gap50_rank':'ema_gap50_rank','gkvol21_rank':'gkvol21_rank','positive_frac63_rank':'positive_frac63_rank','max_gain63_rank':'max_gain63_rank','breakout_pos126_rank':'breakout_pos126_rank','breakout_pos252_rank':'breakout_pos252_rank','sign_entropy63_rank':'sign_entropy63_rank','mom126_ex21_rank':'mom_126_21_rank','efficiency126_rank':'eff_126_rank','acc_mom_21_63_rank':'acc_21_63_broad_rank','mom21_rank':'ret_21_rank','mom42_rank':'ret_42_rank','mom63_rank':'ret_63_rank','mom126_rank':'ret_126_rank','vol21_rank':'vol_21_rank','vol63_rank':'vol_63_rank','vol126_rank':'vol_126_rank','downvol21_rank':'downvol_21_rank','downvol63_rank':'downvol_63_rank','kurt63_rank':'kurt_63_rank'}
    for dst,src in amap.items():
        if src in D: D[dst]=D[src]
    missing=[f for f in base.TAIL_FEATURES if f not in D]
    if missing: raise RuntimeError(f'Tail missing {missing}')
    tail=pd.concat([D[f].stack(dropna=False).rename(f) for f in base.TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    return tail,D

def build_macro(D,labels,category_map,base):
    missing=[f for f in base.BASE_FEATS if f not in D]
    if missing: raise RuntimeError(f'Macro BASE_FEATS missing {missing}')
    p=pd.concat([D[f].stack(dropna=False).rename(f) for f in base.BASE_FEATS],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    p=p.merge(labels[['signal_date','ticker','fwd_ret_21','fwd_ret_42','fwd_ret_63','exit_date_63']].drop_duplicates(['signal_date','ticker']),on=['signal_date','ticker'],how='left');p['macro_category']=p.ticker.map(category_map)
    rows=[]
    for (dt,cat),g in p.dropna(subset=['macro_category']).groupby(['signal_date','macro_category']):
        rec={'signal_date':dt,'macro_category':cat}
        for f in base.BASE_FEATS: rec[f'{f}_mean']=g[f].mean();rec[f'{f}_max']=g[f].max()
        for f in ['ret_21_rank','ret_63_rank','acc_5_21_rank','eff_63_rank','signed_volume21_rank','vol_63_rank']:
            x=g[f];rec[f'{f}_p75']=x.quantile(.75);rec[f'{f}_std']=x.std();rec[f'{f}_topfrac']=(x>.70).mean()
        vals=(.45*g.fwd_ret_21+.35*g.fwd_ret_42+.20*g.fwd_ret_63).dropna().sort_values(ascending=False)
        rec['cat_top2_mean']=vals.iloc[:2].mean() if len(vals)>=2 else np.nan; rec['cat_p75']=vals.quantile(.75) if len(vals) else np.nan; rec['cat_mean']=vals.mean() if len(vals) else np.nan;rec['macro_label_exit_date_63']=g.exit_date_63.dropna().max() if g.exit_date_63.notna().any() else pd.NaT
        rows.append(rec)
    out=pd.DataFrame(rows)
    for target in ['cat_top2_mean','cat_p75','cat_mean']: out[target+'_rank']=out.groupby('signal_date')[target].rank(pct=True,method='average')
    feats=[c for c in out.columns if c.endswith(('_mean','_max','_p75','_std','_topfrac')) and not c.startswith('cat_')]
    return out,feats

def build_opportunity(D,clusters,labels,base):
    raw_names=['mom21','mom63','mom126','mom252','acc_mom_5_21','acc_mom_21_63','vol21','vol63','downvol21','drawdown63','intraday_mom21','gap_mom21','trend_slope21','trend_slope63','max_gain21','max_gain63','max_loss21','cvar10_63']
    alias={'mom21':'ret_21','mom63':'ret_63','mom126':'ret_126','mom252':'ret_252','acc_mom_5_21':'acc_5_21_broad','acc_mom_21_63':'acc_21_63_broad','vol21':'vol_21','vol63':'vol_63','downvol21':'downvol_21','drawdown63':'dd_63','trend_slope21':'slope_21','trend_slope63':'slope_63','max_gain63':'max_gain63','cvar10_63':'cvar10_63'}
    for dst,src in alias.items():
        if dst not in D and src in D: D[dst]=D[src]
    missing=[x for x in raw_names if x not in D]
    if missing: raise RuntimeError(f'Opportunity raw missing {missing}')
    t=pd.concat([D[n].stack(dropna=False).rename(n) for n in raw_names],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    t=t.merge(clusters[['signal_date','ticker','cluster_id']],on=['signal_date','ticker'],how='inner').merge(labels[['signal_date','ticker','fwd_ret_21','exit_date_21']].drop_duplicates(['signal_date','ticker']),on=['signal_date','ticker'],how='left')
    grp=t.groupby(['signal_date','cluster_id']);t['resid_cluster_mom21']=t.mom21-grp.mom21.transform('mean');t['resid_cluster_mom63']=t.mom63-grp.mom63.transform('mean');t['ctx_cluster_disp63']=grp.mom63.transform('std')
    feats=raw_names+['resid_cluster_mom21','resid_cluster_mom63','ctx_cluster_disp63']; rows=[]
    for (dt,cid),g in t.groupby(['signal_date','cluster_id']):
        rec={'signal_date':dt,'cluster_id':int(cid),'label_exit_date_21':g.exit_date_21.max()}
        for f in feats: rec[f+'_mean']=g[f].mean();rec[f+'_p75']=g[f].quantile(.75);rec[f+'_max']=g[f].max();rec[f+'_std']=g[f].std()
        vals=g.fwd_ret_21.dropna().sort_values(ascending=False)
        if len(vals):
            top2=vals.iloc[:2].mean(); med=vals.median(); mean=vals.mean(); mx=vals.max(); rec['target_top2']=top2; rec['target_spread']=top2-mean; rec['target_excess_max']=mx-med
        rows.append(rec)
    out=pd.DataFrame(rows);out['target_explosive']=(out.groupby('signal_date')['target_spread'].rank(pct=True,method='average')>=.75).astype(float)
    numeric=[c for c in out.columns if c.endswith(('_mean','_p75','_max','_std'))]
    for c in numeric: out[c+'_rank']=out.groupby('signal_date')[c].rank(pct=True,method='average')
    for cid in range(8): out[f'cluster_is_{cid}']=(out.cluster_id==cid).astype(float)
    return out

def fit_predict(compact,tail,macro,macro_feats,opp,base,years,n_estimators,models_dir):
    models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2
    pred_rows=[];macro_rows=[];opp_rows=[];audit=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1); ydir=models_dir/str(year);ydir.mkdir(exist_ok=True)
        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]
        for seed in MODEL_SEEDS:
            m=XGBRanker(**params,random_state=seed);m.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False);raw=m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan));q=te[['signal_date','ticker']].copy();q[f'compact_seed_{seed}_rank']=pd.Series(raw,index=te.index).groupby(te.signal_date).rank(pct=True,method='average').to_numpy();seed_parts.append(q.set_index(['signal_date','ticker'])[f'compact_seed_{seed}_rank']);m.save_model(ydir/f'COMPACT_SEED_{seed}.json')
        comp=pd.concat(seed_parts,axis=1).mean(axis=1).rename('compact_rank').reset_index()
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()];tte=tail[tail.signal_date.dt.year==year]
        tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0));tm.fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix);tp=tte[['signal_date','ticker']].copy();tp['tail_raw']=tm.predict(tte[base.TAIL_FEATURES]);tp['tail_rank']=tp.groupby('signal_date').tail_raw.rank(pct=True,method='average');joblib.dump(tm,ydir/'TAILMIX.joblib')
        pred_rows.append(comp.merge(tp[['signal_date','ticker','tail_raw','tail_rank']],on=['signal_date','ticker'],how='left'))
        mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.cat_top2_mean_rank.notna()];mte=macro[macro.signal_date.dt.year==year]
        if len(mtr):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0));mm.fit(mtr[macro_feats],mtr.cat_top2_mean_rank);mq=mte[['signal_date','macro_category']].copy();mq['macro_raw']=mm.predict(mte[macro_feats]);macro_rows.append(mq);joblib.dump(mm,ydir/'MACRO.joblib')
        oq=opp[opp.signal_date.dt.year==year][['signal_date','cluster_id']].copy()
        for spec0 in base.OPPORTUNITY_SPECS:
            target=spec0['target']; feats=spec0['features']; otr=opp[(opp.signal_date<cutoff)&(opp.label_exit_date_21<cutoff)&opp[target].notna()];ote=opp[opp.signal_date.dt.year==year]
            if ote.empty or otr.empty: oq[target+'_pred']=np.nan;continue
            if spec0['model']=='ET_D4_L30': model=make_pipeline(SimpleImputer(strategy='median'),ExtraTreesRegressor(n_estimators=120,max_depth=4,min_samples_leaf=30,max_features=.7,n_jobs=-1,random_state=7))
            elif spec0['model']=='RF_D3_L30': model=make_pipeline(SimpleImputer(strategy='median'),RandomForestClassifier(n_estimators=150,max_depth=3,min_samples_leaf=30,max_features=.7,n_jobs=-1,class_weight='balanced',random_state=7))
            else: model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.0))
            yy=otr[target].astype(int) if target=='target_explosive' else otr[target];model.fit(otr[feats],yy)
            if target=='target_explosive':
                pp=model.predict_proba(ote[feats]);classes=list(model[-1].classes_); val=pp[:,classes.index(1)] if 1 in classes else np.zeros(len(ote))
            else: val=model.predict(ote[feats])
            oq[target+'_pred']=val;joblib.dump(model,ydir/f'OPP_{target}.joblib')
        opp_rows.append(oq);audit.append({'year':year,'compact_train_rows':len(tr),'compact_train_dates':tr.signal_date.nunique(),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr),'opp_rows_before_cutoff':len(opp[opp.signal_date<cutoff])})
    pred=pd.concat(pred_rows,ignore_index=True); pred['titanium_score_pre_macro']=.70*pred.compact_rank+.30*pred.tail_rank
    mp=pd.concat(macro_rows,ignore_index=True);mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS));tops=[]
    for dt,g in mp.groupby('signal_date'):
        g=g.sort_values('macro_z',ascending=False);tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
    pred['macro_category']=pred.ticker.map(base.TICKER_CATEGORY);pred=pred.merge(pd.DataFrame(tops),on='signal_date',how='left');pred['macro_bonus']=np.where((pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.tail_rank>=.80),.15,0.0);pred['titanium_score']=pred.titanium_score_pre_macro+pred.macro_bonus
    op=pd.concat(opp_rows,ignore_index=True)
    for target,w in OPP_WEIGHTS.items(): op[target+'_pred_rank']=op.groupby('signal_date')[target+'_pred'].rank(pct=True,method='average')
    op['opp_raw']=sum(w*op[target+'_pred_rank'] for target,w in OPP_WEIGHTS.items());op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+EPS))
    return pred.sort_values(['signal_date','ticker']),op.sort_values(['signal_date','cluster_id']),pd.DataFrame(audit),mp

def package(out:Path,base_src:Path,v5_src:Path):
    if (out/'OOS_TICKER_SCORES.parquet').exists(): shutil.copy2(out/'OOS_TICKER_SCORES.parquet',out/'SUPER_GOLD_OOS_SCORE_PANEL.parquet')
    if (out/'COMPACT_LABELED.parquet').exists(): shutil.copy2(out/'COMPACT_LABELED.parquet',out/'NPORT_TITANIUM_PANEL.parquet')
    mats={k:pd.read_parquet(out/f'{k.upper()}.parquet') for k in ['Open','High','Low','Close','Volume']};longs=[]
    for k,x in mats.items(): longs.append(x.stack(dropna=False).rename(k.lower()).reset_index().rename(columns={'level_0':'date','level_1':'ticker'}))
    daily=longs[0]
    for x in longs[1:]:daily=daily.merge(x,on=['date','ticker'],how='outer')
    daily.to_parquet(out/'DAILY_OHLCV_ACTIONS_150ETF.parquet',index=False);shutil.copy2(base_src,out/'RECONSTRUCTION_CONSTANTS_SOURCE.py');shutil.copy2(v5_src,out/'EXECUTION_ENGINE_SOURCE.py');shutil.copy2(Path(__file__),out/'PRODUCTION_ALIGNED_REGENERATOR.py')
    sha=[]
    for p in sorted(out.rglob('*')):
        if p.is_file() and p.name!='SHA256SUMS.txt': sha.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(out)}")
    (out/'SHA256SUMS.txt').write_text('\n'.join(sha)+'\n');z=out.parent/'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE.zip'
    if z.exists():z.unlink()
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as zz:
        for p in out.rglob('*'):
            if p.is_file():zz.write(p,p.relative_to(out))
    (out.parent/'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE.sha256').write_text(f"{hashlib.sha256(z.read_bytes()).hexdigest()}  {z.name}\n");return z

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--base-module',required=True);ap.add_argument('--v5-module',required=True);ap.add_argument('--data-dir',required=True);ap.add_argument('--output',required=True);ap.add_argument('--n-estimators',type=int,default=360);ap.add_argument('--n-baskets',type=int,default=500);args=ap.parse_args()
    out=Path(args.output);shutil.rmtree(out,ignore_errors=True);out.mkdir(parents=True);models=out/'MODELS';base=load_module(Path(args.base_module),'base_spec');v5=load_module(Path(args.v5_module),'v5_exec');base.OPPORTUNITY_SPECS=v5.OPPORTUNITY_SPECS;mats=load_mats(Path(args.data_dir))
    for k,x in mats.items():x.to_parquet(out/f'{k.upper()}.parquet',compression='zstd')
    t0=time.time();dates,compact0,CF=build_compact(mats,base);compact=add_labels(compact0,mats['Open'],dates);tail0,D=build_broad(mats,dates,CF,base)
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']];ret=C.pct_change(fill_method=None);prev=C.shift(1);D['intraday_mom21']=snapshot((C/O-1).rolling(21,min_periods=21).sum(),dates);D['gap_mom21']=snapshot((O/prev-1).rolling(21,min_periods=21).sum(),dates);D['max_gain21']=snapshot(ret.rolling(21,min_periods=21).max(),dates);D['max_loss21']=snapshot(ret.rolling(21,min_periods=21).min(),dates);D['cvar10_63']=snapshot(rolling_cvar10(ret,63),dates)
    tail=add_labels(tail0,mats['Open'],dates);clusters,balance,ari=v5.build_s3b_clusters(mats,dates,base.TICKER_CATEGORY);macro,macro_feats=build_macro(D,compact,base.TICKER_CATEGORY,base);opp=build_opportunity(D,clusters,compact,base)
    pred,opred,fit_audit,macro_pred=fit_predict(compact,tail,macro,macro_feats,opp,base,range(2017,2027),args.n_estimators,models);pred=pred[pred.signal_date>=BACKTEST_START].copy();opred=opred[opred.signal_date>=BACKTEST_START].copy();cal=compact[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date');cal=cal[(cal.signal_date>=BACKTEST_START)&cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    baskets,cats=v5.make_baskets(base,pred,args.n_baskets);idx,EB,ED,ER,active,margin,cond,bs,bw,ds,dw=v5.simulate_all(baskets,pred,opred,clusters,mats,cal);rows=[]
    for b in range(len(baskets)):
        for name,arr in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
            c,dd,sh,fe=v5.metrics(arr,idx);rows.append({'basket':b,'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(active.sum()),'direct_condition_months':int(cond[b].sum())})
    res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS_500.csv',index=False);pd.DataFrame([{'basket':b,'ticker':t,'category':base.TICKER_CATEGORY.get(t)} for b,u in enumerate(baskets) for t in u]).to_csv(out/'BASKET_MEMBERSHIP_500.csv',index=False)
    tick_index={t:i for i,t in enumerate(mats['Open'].columns)};base_s,base_w,dir_s,dir_w,mar,con=v5.build_target_arrays(baskets,pred,opred,clusters,pd.DatetimeIndex(cal.signal_date),tick_index,mats['Open'],pd.DatetimeIndex(cal.entry_date));np.savez_compressed(out/'TARGET_ARRAYS_500.npz',base_sel=base_s,base_w=base_w,direct_sel=dir_s,direct_w=dir_w,margin=mar,direct_condition=con,router_active=active);np.savez_compressed(out/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz',BASE=EB,DIRECT=ED,ROUTER=ER,dates=np.array(idx,dtype='datetime64[ns]'));pd.DataFrame({'signal_date':cal.signal_date,'router_active':active}).to_csv(out/'ROUTER_SCHEDULE.csv',index=False)
    global_u=[sorted(pred.ticker.unique())];idxg,Ebg,Edg,Erg,ag,mg,cg,*_=v5.simulate_all(global_u,pred,opred,clusters,mats,cal,forced_active=active);grow=[]
    for name,arr in [('BASE',Ebg[0]),('DIRECT',Edg[0]),('ROUTER',Erg[0])]:
        c,dd,sh,fe=v5.metrics(arr,idxg);grow.append({'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(active.sum()),'direct_condition_months':int(cg[0].sum())});pd.Series(arr,index=idxg,name='equity').to_csv(out/f'GLOBAL_{name}_EQUITY.csv')
    pd.DataFrame(grow).to_csv(out/'GLOBAL_SCORECARD.csv',index=False);compact.to_parquet(out/'COMPACT_LABELED.parquet',index=False);tail.to_parquet(out/'TAILMIX_LABELED.parquet',index=False);macro.to_parquet(out/'MACRO_TRAINING_PANEL.parquet',index=False);opp.to_parquet(out/'OPPORTUNITY_TRAINING_PANEL.parquet',index=False);pred.to_parquet(out/'OOS_TICKER_SCORES.parquet',index=False);opred.to_parquet(out/'OOS_OPPORTUNITY_SCORES.parquet',index=False);clusters.to_csv(out/'DYNAMIC_CLUSTER_MEMBERSHIP.csv',index=False);balance.to_csv(out/'S3B_BALANCE.csv',index=False);ari.to_csv(out/'S3B_ARI.csv',index=False);fit_audit.to_csv(out/'FIT_AUDIT.csv',index=False);macro_pred.to_parquet(out/'OOS_MACRO_SCORES.parquet',index=False);cal.to_csv(out/'MONTHLY_CALENDAR.csv',index=False)
    feature_audit=[]
    for fam,cols,fr in [('COMPACT',base.F2D_FEATURES,compact),('TAIL',base.TAIL_FEATURES,tail),('MACRO',macro_feats,macro)]:
        for c in cols:feature_audit.append({'family':fam,'feature':c,'exists':c in fr,'missing_rate':float(fr[c].isna().mean()) if c in fr else 1.0})
    pd.DataFrame(feature_audit).to_csv(out/'FEATURE_PARITY_AUDIT.csv',index=False);router=res[res.strategy=='ROUTER'];router.cagr.describe(percentiles=[.01,.05,.10,.25,.50,.75,.90,.95,.99]).to_csv(out/'CAGR_DISTRIBUTION_SUMMARY.csv');plt.figure(figsize=(10,6));plt.hist(router.cagr*100,bins=30);plt.axvline(router.cagr.mean()*100,label=f'Media {router.cagr.mean()*100:.2f}%');plt.axvline(router.cagr.median()*100,label=f'Mediana {router.cagr.median()*100:.2f}%');plt.xlabel('CAGR (%)');plt.ylabel('Panieri');plt.legend();plt.tight_layout();plt.savefig(out/'CAGR_DISTRIBUTION.png',dpi=180);plt.close()
    chk=pred[pred.signal_date==pd.Timestamp('2026-06-30')].sort_values('titanium_score',ascending=False).head(5);known={'top1':str(chk.iloc[0].ticker) if len(chk) else None,'top2':str(chk.iloc[1].ticker) if len(chk)>1 else None,'expected_top1':'USO','expected_top2':'PALL','matches':bool(len(chk)>1 and chk.iloc[0].ticker=='USO' and chk.iloc[1].ticker=='PALL')};(out/'KNOWN_SIGNAL_CHECK.json').write_text(json.dumps(known,indent=2));manifest={'architecture':'Titanium_V2 + Opportunity_3.0 production-aligned regeneration','data_source':'downloaded ticker OHLCV matrices','n_scored_tickers':int(pred.ticker.nunique()),'n_baskets':len(baskets),'n_oos_months':len(cal),'compact_trees':args.n_estimators,'compact_seeds':MODEL_SEEDS,'downvol_definition':'sqrt(mean(min(logret,0)^2)*252)','macro_features':len(macro_feats),'router_active_months':int(active.sum()),'known_signal_check':known,'elapsed_seconds':time.time()-t0};(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    glob=pd.DataFrame(grow).set_index('strategy');br=res[res.strategy=='BASE'];dr=res[res.strategy=='DIRECT'];q=router.cagr.quantile([.01,.05,.10,.25,.50,.75,.90,.95,.99]);report=f'''# Titanium V2 + Opportunity 3.0 — production-aligned regeneration\n\n- OOS months: {len(cal)}\n- scored tickers: {pred.ticker.nunique()}\n- 500-basket Base mean CAGR: {br.cagr.mean():.4%}\n- 500-basket Direct mean CAGR: {dr.cagr.mean():.4%}\n- 500-basket Router mean CAGR: {router.cagr.mean():.4%}\n- Router median CAGR: {router.cagr.median():.4%}\n- Router P05/P95: {q.loc[.05]:.4%} / {q.loc[.95]:.4%}\n- Router median MaxDD: {router.maxdd.median():.4%}\n\n## Global unrestricted\n\n|Strategy|CAGR|MaxDD|Sharpe|\n|---|---:|---:|---:|\n|BASE|{glob.loc['BASE','cagr']:.4%}|{glob.loc['BASE','maxdd']:.4%}|{glob.loc['BASE','sharpe']:.3f}|\n|DIRECT|{glob.loc['DIRECT','cagr']:.4%}|{glob.loc['DIRECT','maxdd']:.4%}|{glob.loc['DIRECT','sharpe']:.3f}|\n|ROUTER|{glob.loc['ROUTER','cagr']:.4%}|{glob.loc['ROUTER','maxdd']:.4%}|{glob.loc['ROUTER','sharpe']:.3f}|\n\nKnown checkpoint: {known}\n''';(out/'REPORT.md').write_text(report);z=package(out,Path(args.base_module),Path(args.v5_module));print(report);print('PACKAGE',z,hashlib.sha256(z.read_bytes()).hexdigest(),flush=True)
if __name__=='__main__':main()
