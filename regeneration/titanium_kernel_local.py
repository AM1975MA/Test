#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import time
import warnings
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('NUMEXPR_NUM_THREADS','2')

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker

warnings.filterwarnings('ignore')

START_DOWNLOAD='2005-01-01'
END_DOWNLOAD='2026-08-03'
BACKTEST_START=pd.Timestamp('2017-01-31')
COST=0.001
STOP=0.055
STOP_SLIP=0.001
REDUCED_EXPOSURE=0.25
N_BASKETS=500
PER_CATEGORY=4
SEED=20260727

CATEGORY_TICKERS = {
'C01_US_BROAD_STYLE': ['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
'C02_US_SECTOR_THEME': ['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
'C03_DEVELOPED_GLOBAL': ['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
'C04_EMERGING': ['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','PIN','ARGT'],
'C05_BONDS_CASH_CREDIT': ['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
'C06_REAL_ASSETS': ['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA'],
}
ALL_TICKERS=[t for xs in CATEGORY_TICKERS.values() for t in xs]
TICKER_CATEGORY={t:c for c,xs in CATEGORY_TICKERS.items() for t in xs}

F2D_FEATURES = ['mom5', 'mom10', 'mom21', 'mom42', 'mom63', 'mom126', 'mom252', 'vol21', 'downvol21', 'drawdown21', 'efficiency21', 'vol63', 'downvol63', 'drawdown63', 'efficiency63', 'vol126', 'downvol126', 'drawdown126', 'efficiency126', 'mom126_ex21', 'mom252_ex21', 'acc_mom_5_21', 'acc_mom_21_63', 'vol_ratio_21_126', 'skew63', 'kurt63', 'gkvol21', 'log_adv63', 'volume_surprise21', 'beta_mkt63', 'corr_mkt63', 'beta_mkt126', 'corr_mkt126', 'mom5_pct', 'mom10_pct', 'mom21_pct', 'mom42_pct', 'mom63_pct', 'mom126_pct', 'mom252_pct', 'vol21_pct', 'downvol21_pct', 'drawdown21_pct', 'efficiency21_pct', 'vol63_pct', 'downvol63_pct', 'drawdown63_pct', 'efficiency63_pct', 'vol126_pct', 'downvol126_pct', 'drawdown126_pct', 'efficiency126_pct', 'mom126_ex21_pct', 'mom252_ex21_pct', 'acc_mom_5_21_pct', 'acc_mom_21_63_pct', 'vol_ratio_21_126_pct', 'skew63_pct', 'kurt63_pct', 'gkvol21_pct', 'log_adv63_pct', 'volume_surprise21_pct', 'beta_mkt63_pct', 'corr_mkt63_pct', 'beta_mkt126_pct', 'corr_mkt126_pct', 'mom5_dev', 'mom10_dev', 'mom21_dev', 'mom42_dev', 'mom63_dev', 'mom126_dev', 'mom252_dev', 'vol21_dev', 'downvol21_dev', 'drawdown21_dev', 'efficiency21_dev', 'vol63_dev', 'downvol63_dev', 'drawdown63_dev', 'efficiency63_dev', 'vol126_dev', 'downvol126_dev', 'drawdown126_dev', 'efficiency126_dev', 'mom126_ex21_dev', 'mom252_ex21_dev', 'acc_mom_5_21_dev', 'acc_mom_21_63_dev', 'vol_ratio_21_126_dev', 'skew63_dev', 'kurt63_dev', 'gkvol21_dev', 'log_adv63_dev', 'volume_surprise21_dev', 'beta_mkt63_dev', 'corr_mkt63_dev', 'beta_mkt126_dev', 'corr_mkt126_dev', 'ma_gap50', 'ma_gap200', 'ema_gap20', 'ema_gap50', 'breakout_pos126', 'breakout_pos252', 'rsi14', 'positive_frac63', 'max_loss63', 'max_gain63', 'cvar10_63', 'sign_entropy63', 'autocorr1_63', 'ma_gap50_pct', 'ma_gap200_pct', 'ema_gap20_pct', 'ema_gap50_pct', 'breakout_pos126_pct', 'breakout_pos252_pct', 'rsi14_pct', 'positive_frac63_pct', 'max_loss63_pct', 'max_gain63_pct', 'cvar10_63_pct', 'sign_entropy63_pct', 'autocorr1_63_pct']
COMPACT_PARAMS={'objective':'rank:pairwise','eval_metric':'ndcg@3','n_estimators':360,'max_depth':4,'learning_rate':0.035,'subsample':0.85,'colsample_bytree':0.8,'min_child_weight':8.0,'reg_lambda':8.0,'reg_alpha':0.1,'tree_method':'hist','n_jobs':2,'verbosity':0}
COMPACT_SEEDS=[101,202,303]

TAIL_FEATURES = ['beta_mkt63_rank', 'ma_gap200_rank', 'sma_ratio_200_rank', 'beta_mkt126_rank', 'atr_14_rank', 'vol_10_rank', 'downvol_21_rank', 'downvol21_rank', 'corr_mkt63_rank', 'corr_mkt126_rank', 'gkvol21_rank', 'energy_21_rank', 'vol_21_rank', 'vol21_rank', 'mom_21_5_rank', 'vol126_rank', 'vol_126_rank', 'sma_ratio_100_rank', 'slope_63_rank', 'vol63_rank', 'vol_63_rank', 'downvol_63_rank', 'downvol63_rank', 'downvol126_rank', 'energy_63_rank', 'ret_126_rank', 'mom126_rank', 'max_gain63_rank', 'mom_63_5_rank', 'positive_frac63_rank', 'breakout_pos126_rank', 'volume_ratio5_20_rank', 'atr_ratio_rank', 'amihud63_rank', 'mom21_rank', 'ret_21_rank', 'kurt_63_rank', 'kurt63_rank', 'amihud21_rank', 'ema_gap50_rank', 'sma_ratio_50_rank', 'ma_gap50_rank', 'sign_entropy63_rank', 'volume_ratio20_63_rank', 'jerk_rank', 'breakout_pos252_rank', 'ret_63_rank', 'mom63_rank', 'gap_vol21_rank', 'mom42_rank', 'ret_42_rank', 'ret63_vol126_rank', 'efficiency126_rank', 'eff_126_rank', 'acc_21_63_broad_rank', 'acc_mom_21_63_rank', 'stoch63_rank', 'mom_126_21_rank', 'mom126_ex21_rank', 'slope_21_rank']
BASE_FEATS=['ret_10_rank','ret_21_rank','ret_42_rank','ret_63_rank','ret_126_rank','ret_252_rank','acc_3_10_rank','acc_5_21_rank','acc_21_63_rank','jerk_rank','eff_21_rank','eff_63_rank','dist_high_21_rank','dist_high_63_rank','dd_63_rank','vol_21_rank','vol_63_rank','vol_ratio_10_63_rank','directional_energy_21_rank','directional_energy_63_rank','spectral_entropy64_rank','signed_volume21_rank','volume_z20_rank','volume_ratio5_20_rank','pv_corr21_rank','r2_63_rank','slope_63_rank']


def download_ohlcv(out:Path):
    import yfinance as yf
    fields={k:[] for k in ['Open','High','Low','Close','Volume']}
    logs=[]
    for i in range(0,len(ALL_TICKERS),25):
        batch=ALL_TICKERS[i:i+25]
        raw=None
        for attempt in range(5):
            try:
                raw=yf.download(batch,start=START_DOWNLOAD,end=END_DOWNLOAD,auto_adjust=True,group_by='column',progress=False,threads=True,timeout=45)
                if raw is None or raw.empty: raise RuntimeError('empty')
                break
            except Exception as exc:
                if attempt==4: logs.extend({'ticker':t,'ok':False,'error':repr(exc)} for t in batch)
                time.sleep(2**attempt)
        if raw is None or raw.empty: continue
        for fld in fields:
            if isinstance(raw.columns,pd.MultiIndex):
                frame=raw[fld].copy() if fld in raw.columns.get_level_values(0) else pd.DataFrame(index=raw.index)
            else:
                frame=raw[[fld]].rename(columns={fld:batch[0]})
            frame.columns=[str(c).upper() for c in frame.columns]
            fields[fld].append(frame)
        for t in batch:
            ok=t in fields['Close'][-1].columns and fields['Close'][-1][t].notna().sum()>=252
            logs.append({'ticker':t,'ok':bool(ok)})
    mats={k:pd.concat(v,axis=1).loc[:,lambda x:~x.columns.duplicated()].sort_index() for k,v in fields.items()}
    common=sorted(set.intersection(*[set(x.columns) for x in mats.values()]))
    mats={k:v.reindex(columns=common) for k,v in mats.items()}
    for k,v in mats.items():
        v.index=pd.to_datetime(v.index).tz_localize(None)
        mats[k]=v.apply(pd.to_numeric,errors='coerce')
        mats[k].to_parquet(out/f'{k.upper()}.parquet')
    pd.DataFrame(logs).to_csv(out/'DOWNLOAD_LOG.csv',index=False)
    return mats


def month_end_dates(idx:pd.DatetimeIndex)->pd.DatetimeIndex:
    s=pd.Series(idx,index=idx)
    return pd.DatetimeIndex(s.groupby(idx.to_period('M')).max().values)

def snapshot(df:pd.DataFrame, dates:pd.DatetimeIndex)->pd.DataFrame:
    return df.reindex(dates)

def cs_pct(df:pd.DataFrame)->pd.DataFrame:
    return df.rank(axis=1,pct=True,method='average')

def cs_robust_dev(df:pd.DataFrame)->pd.DataFrame:
    med=df.median(axis=1)
    mad=df.sub(med,axis=0).abs().median(axis=1).replace(0,np.nan)
    return df.sub(med,axis=0).div(1.4826*mad,axis=0).clip(-8,8)

def rolling_efficiency(logc:pd.DataFrame,h:int)->pd.DataFrame:
    return logc.diff(h).abs()/logc.diff().abs().rolling(h,min_periods=h).sum().replace(0,np.nan)

def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return ret.where(ret<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*np.sqrt(252)

def rolling_rsi(c:pd.DataFrame,h:int=14)->pd.DataFrame:
    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/h,adjust=False,min_periods=h).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/h,adjust=False,min_periods=h).mean()
    rs=up/dn.replace(0,np.nan); return 100-100/(1+rs)

def rolling_cvar10(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return ret.rolling(h,min_periods=h).apply(lambda x: np.nanmean(np.sort(x)[:max(1,int(math.ceil(.1*len(x))))]),raw=True)

def rolling_sign_entropy(ret:pd.DataFrame,h:int)->pd.DataFrame:
    p=(ret>0).rolling(h,min_periods=h).mean().clip(1e-9,1-1e-9)
    return -(p*np.log(p)+(1-p)*np.log(1-p))

def rolling_autocorr(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return ret.rolling(h,min_periods=h).corr(ret.shift(1))

def rolling_slope(logc:pd.DataFrame,h:int)->pd.DataFrame:
    x=np.arange(h,dtype=float); xc=x-x.mean(); den=np.sum(xc*xc)
    return logc.rolling(h,min_periods=h).apply(lambda y: float(np.dot(y-y.mean(),xc)/den),raw=True)

def rolling_r2(logc:pd.DataFrame,h:int)->pd.DataFrame:
    x=np.arange(h,dtype=float); xc=x-x.mean(); den=np.sum(xc*xc)
    def f(y):
        yc=y-y.mean(); d=np.sum(yc*yc)
        if d<=0:return np.nan
        return float(np.dot(yc,xc)**2/(den*d))
    return logc.rolling(h,min_periods=h).apply(f,raw=True)

def spectral_entropy_frame(logret:pd.DataFrame,h:int=64)->pd.DataFrame:
    def ent(x):
        x=np.asarray(x,float); x=x-np.nanmean(x); p=np.abs(np.fft.rfft(x))**2; p=p[1:]
        s=p.sum()
        if s<=0:return np.nan
        p=p/s; return float(-(p*np.log(p+1e-12)).sum()/np.log(len(p)))
    return logret.rolling(h,min_periods=h).apply(ent,raw=True)

def beta_corr(asset:pd.DataFrame,mkt:pd.Series,h:int):
    cov=asset.rolling(h,min_periods=h).cov(mkt); var=mkt.rolling(h,min_periods=h).var().replace(0,np.nan)
    beta=cov.div(var,axis=0); corr=asset.rolling(h,min_periods=h).corr(mkt)
    return beta,corr


def build_features(mats:Mapping[str,pd.DataFrame]):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]
    dates=month_end_dates(C.index)
    logc=np.log(C.where(C>0)); lr=logc.diff(); ret=C.pct_change(fill_method=None); prev=C.shift(1)
    mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)
    compact={}
    for h in [5,10,21,42,63,126,252]: compact[f'mom{h}']=snapshot(C.pct_change(h,fill_method=None),dates)
    for h in [21,63,126]:
        compact[f'vol{h}']=snapshot(lr.rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252),dates)
        compact[f'downvol{h}']=snapshot(rolling_downvol(lr,h),dates)
        compact[f'drawdown{h}']=snapshot(C/C.rolling(h,min_periods=h).max()-1,dates)
        compact[f'efficiency{h}']=snapshot(rolling_efficiency(logc,h),dates)
    compact['mom126_ex21']=snapshot(C.shift(21)/C.shift(126)-1,dates)
    compact['mom252_ex21']=snapshot(C.shift(21)/C.shift(252)-1,dates)
    compact['acc_mom_5_21']=compact['mom5']-(5/21)*compact['mom21']
    compact['acc_mom_21_63']=compact['mom21']-(21/63)*compact['mom63']
    compact['vol_ratio_21_126']=compact['vol21']/compact['vol126'].replace(0,np.nan)
    compact['skew63']=snapshot(lr.rolling(63,min_periods=63).skew(),dates)
    compact['kurt63']=snapshot(lr.rolling(63,min_periods=63).kurt(),dates)
    gk=.5*np.log(H/L.replace(0,np.nan))**2-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan))**2
    compact['gkvol21']=snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252),dates)
    adv=(C*V).rolling(63,min_periods=42).mean()
    compact['log_adv63']=snapshot(np.log(adv.where(adv>0)),dates)
    lv=np.log(V.where(V>0)); compact['volume_surprise21']=snapshot((lv-lv.rolling(21,min_periods=15).mean())/lv.rolling(21,min_periods=15).std(ddof=0).replace(0,np.nan),dates)
    for h in [63,126]:
        b,c=beta_corr(ret,mkt,h); compact[f'beta_mkt{h}']=snapshot(b,dates); compact[f'corr_mkt{h}']=snapshot(c,dates)
    compact['ma_gap50']=snapshot(C/C.rolling(50,min_periods=50).mean()-1,dates)
    compact['ma_gap200']=snapshot(C/C.rolling(200,min_periods=200).mean()-1,dates)
    compact['ema_gap20']=snapshot(C/C.ewm(span=20,adjust=False,min_periods=20).mean()-1,dates)
    compact['ema_gap50']=snapshot(C/C.ewm(span=50,adjust=False,min_periods=50).mean()-1,dates)
    for h in [126,252]: compact[f'breakout_pos{h}']=snapshot((C-C.rolling(h,min_periods=h).min())/(C.rolling(h,min_periods=h).max()-C.rolling(h,min_periods=h).min()).replace(0,np.nan),dates)
    compact['rsi14']=snapshot(rolling_rsi(C,14),dates)
    compact['positive_frac63']=snapshot((ret>0).rolling(63,min_periods=63).mean(),dates)
    compact['max_loss63']=snapshot(ret.rolling(63,min_periods=63).min(),dates)
    compact['max_gain63']=snapshot(ret.rolling(63,min_periods=63).max(),dates)
    compact['cvar10_63']=snapshot(rolling_cvar10(ret,63),dates)
    compact['sign_entropy63']=snapshot(rolling_sign_entropy(ret,63),dates)
    compact['autocorr1_63']=snapshot(rolling_autocorr(ret,63),dates)
    bases=[x for x in F2D_FEATURES if not x.endswith('_pct') and not x.endswith('_dev')]
    for name in list(compact):
        if name+'_pct' in F2D_FEATURES: compact[name+'_pct']=cs_pct(compact[name])
        if name+'_dev' in F2D_FEATURES: compact[name+'_dev']=cs_robust_dev(compact[name])
    for n in F2D_FEATURES:
        if n not in compact: compact[n]=pd.DataFrame(np.nan,index=dates,columns=C.columns)
    compact_long=pd.concat([compact[n].stack(dropna=False).rename(n) for n in F2D_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})

    D={}
    for h in [3,5,10,21,42,63,126,252]:D[f'ret_{h}']=snapshot(C.pct_change(h,fill_method=None),dates)
    D['mom_21_5']=snapshot(C.shift(5)/C.shift(21)-1,dates);D['mom_63_5']=snapshot(C.shift(5)/C.shift(63)-1,dates);D['mom_126_21']=snapshot(C.shift(21)/C.shift(126)-1,dates)
    D['acc_3_10']=D['ret_3']-.3*D['ret_10'];D['acc_5_21_broad']=D['ret_5']-(5/21)*D['ret_21'];D['acc_21_63_broad']=D['ret_21']-(1/3)*D['ret_63'];D['jerk']=D['acc_3_10']-D['acc_5_21_broad']
    for h in [20,50,100,200]:D[f'sma_ratio_{h}']=snapshot(C/C.rolling(h,min_periods=h).mean()-1,dates)
    for h in [21,63,126]:
        D[f'dist_high_{h}']=snapshot(C/C.rolling(h,min_periods=h).max()-1,dates);D[f'dd_{h}']=D[f'dist_high_{h}'];D[f'eff_{h}']=snapshot(rolling_efficiency(logc,h),dates)
    for h in [10,21,63,126]:D[f'vol_{h}']=snapshot(lr.rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252),dates)
    D['downvol_21']=snapshot(rolling_downvol(lr,21),dates);D['downvol_63']=snapshot(rolling_downvol(lr,63),dates);D['downvol126']=snapshot(rolling_downvol(lr,126),dates)
    D['gkvol21']=compact['gkvol21'];D['atr_14']=snapshot(pd.DataFrame(np.maximum.reduce([(H-L).to_numpy(),(H-prev).abs().to_numpy(),(L-prev).abs().to_numpy()]),index=C.index,columns=C.columns).rolling(14,min_periods=14).mean()/C,dates)
    D['atr_ratio']=D['atr_14']/D['vol_21'].replace(0,np.nan)
    D['energy_21']=snapshot(lr.pow(2).rolling(21,min_periods=21).sum(),dates);D['energy_63']=snapshot(lr.pow(2).rolling(63,min_periods=63).sum(),dates)
    D['slope_21']=snapshot(rolling_slope(logc,21),dates);D['slope_63']=snapshot(rolling_slope(logc,63),dates)
    D['r2_63']=snapshot(rolling_r2(logc,63),dates)
    D['max_gain63']=compact['max_gain63'];D['positive_frac63']=compact['positive_frac63'];D['breakout_pos126']=compact['breakout_pos126'];D['breakout_pos252']=compact['breakout_pos252'];D['sign_entropy63']=compact['sign_entropy63']
    dollar=C*V; amihud=ret.abs()/dollar.replace(0,np.nan)
    D['amihud21']=snapshot(amihud.rolling(21,min_periods=15).mean(),dates);D['amihud63']=snapshot(amihud.rolling(63,min_periods=42).mean(),dates)
    D['volume_ratio5_20']=snapshot(V.rolling(5,min_periods=5).mean()/V.rolling(20,min_periods=15).mean(),dates);D['volume_ratio20_63']=snapshot(V.rolling(20,min_periods=15).mean()/V.rolling(63,min_periods=42).mean(),dates)
    D['gap_vol21']=snapshot((O/prev-1).rolling(21,min_periods=21).std(ddof=0),dates);D['stoch63']=snapshot((C-C.rolling(63,min_periods=63).min())/(C.rolling(63,min_periods=63).max()-C.rolling(63,min_periods=63).min()).replace(0,np.nan),dates)
    D['ret63_vol126']=D['ret_63']/D['vol_126'].replace(0,np.nan);D['kurt_63']=snapshot(lr.rolling(63,min_periods=63).kurt(),dates)
    D['ma_gap200']=compact['ma_gap200'];D['ma_gap50']=compact['ma_gap50'];D['ema_gap50']=compact['ema_gap50']
    for h in [63,126]:
        b,c=beta_corr(ret,mkt,h);D[f'beta_mkt{h}']=snapshot(b,dates);D[f'corr_mkt{h}']=snapshot(c,dates)
    D['spectral_entropy64']=snapshot(spectral_entropy_frame(lr,64),dates)
    D['signed_volume21']=snapshot((np.sign(ret)*V).rolling(21,min_periods=15).sum()/V.rolling(21,min_periods=15).sum().replace(0,np.nan),dates)
    D['volume_z20']=snapshot((V-V.rolling(20,min_periods=15).mean())/V.rolling(20,min_periods=15).std(ddof=0).replace(0,np.nan),dates)
    D['pv_corr21']=snapshot(ret.rolling(21,min_periods=21).corr(V.pct_change(fill_method=None)),dates)
    for k,v in list(D.items()):D[k+'_rank']=cs_pct(v)
    aliases={
      'beta_mkt63_rank':'beta_mkt63_rank','beta_mkt126_rank':'beta_mkt126_rank','corr_mkt63_rank':'corr_mkt63_rank','corr_mkt126_rank':'corr_mkt126_rank',
      'vol21_rank':'vol_21_rank','vol63_rank':'vol_63_rank','vol126_rank':'vol_126_rank','downvol21_rank':'downvol_21_rank','downvol63_rank':'downvol_63_rank',
      'mom21_rank':'ret_21_rank','mom42_rank':'ret_42_rank','mom63_rank':'ret_63_rank','mom126_rank':'ret_126_rank','mom126_ex21_rank':'mom_126_21_rank',
      'efficiency126_rank':'eff_126_rank','acc_mom_21_63_rank':'acc_21_63_broad_rank','kurt63_rank':'kurt_63_rank','gkvol21_rank':'gkvol21_rank'}
    for dst,src in aliases.items():
        if src in D:D[dst]=D[src]
    for req in TAIL_FEATURES:
        if req not in D:
            base=req[:-5] if req.endswith('_rank') else req
            D[req]=cs_pct(D[base]) if base in D else pd.DataFrame(np.nan,index=dates,columns=C.columns)
    tail_long=pd.concat([D[n].stack(dropna=False).rename(n) for n in TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    return dates,compact_long,tail_long,D


def add_labels(panel:pd.DataFrame,O:pd.DataFrame,dates:pd.DatetimeIndex):
    info=[]
    idx=O.index
    for k,sd in enumerate(dates):
        pos=idx.get_indexer([sd])[0]
        if pos<0 or pos+1>=len(idx):continue
        rec={'signal_date':sd,'entry_date':idx[pos+1]}
        for h in [21,42,63]:rec[f'exit_date_{h}']=idx[pos+1+h] if pos+1+h<len(idx) else pd.NaT
        rec['exit_date']=idx[idx.get_indexer([dates[k+1]])[0]+1] if k+1<len(dates) and idx.get_indexer([dates[k+1]])[0]+1<len(idx) else pd.NaT
        info.append(rec)
    info=pd.DataFrame(info)
    out=panel.merge(info,on='signal_date',how='left')
    for h in [21,42,63]:
        vals=[]
        for r in info.itertuples():
            if pd.isna(getattr(r,f'exit_date_{h}')):continue
            a=O.loc[r.entry_date];b=O.loc[getattr(r,f'exit_date_{h}')]
            q=(b/a-1).rename('fwd').reset_index().rename(columns={'index':'ticker'});q['signal_date']=r.signal_date;vals.append(q)
        tmp=pd.concat(vals,ignore_index=True) if vals else pd.DataFrame(columns=['ticker','fwd','signal_date'])
        out=out.merge(tmp.rename(columns={'fwd':f'fwd_ret_{h}'}),on=['signal_date','ticker'],how='left')
        out[f'target_rank_{h}']=out.groupby('signal_date')[f'fwd_ret_{h}'].rank(pct=True)
    out['target_rank_pct']=out['target_rank_21']
    out['target_multi_rank']=.45*out.target_rank_21+.35*out.target_rank_42+.20*out.target_rank_63
    out['y_tailmix']=.60*out.target_rank_21.astype(float)**4+.25*out.target_rank_42.astype(float)**4+.15*out.target_rank_63.astype(float)**4
    return out


def build_clusters(D:Mapping[str,pd.DataFrame],dates:pd.DatetimeIndex,cols:Sequence[str]):
    feats=['ret_21','ret_63','ret_126','ret_252','vol_21','vol_63','eff_63','slope_63']
    rows=[]
    for di,dt in enumerate(dates):
        x=pd.DataFrame({f:D[f].loc[dt] for f in feats}).reindex(cols)
        good=x.notna().sum(axis=1)>=5
        if good.sum()<16:continue
        xx=x.loc[good].replace([np.inf,-np.inf],np.nan);xx=xx.fillna(xx.median()).fillna(0.0)
        xx=StandardScaler().fit_transform(xx)
        km=KMeans(n_clusters=8,n_init=20,random_state=SEED+di).fit(xx)
        rows.extend({'signal_date':dt,'ticker':t,'cluster_id':int(c)} for t,c in zip(x.loc[good].index,km.labels_))
    return pd.DataFrame(rows)


def build_macro_panel(tail_panel:pd.DataFrame,labels:pd.DataFrame):
    p=tail_panel.merge(labels[['signal_date','ticker','fwd_ret_21','fwd_ret_42','fwd_ret_63','exit_date_63']],on=['signal_date','ticker'],how='left')
    p['macro_category']=p.ticker.map(TICKER_CATEGORY)
    p['fwd_multi']=.45*p.fwd_ret_21+.35*p.fwd_ret_42+.20*p.fwd_ret_63
    feat=[f for f in BASE_FEATS if f in p.columns]
    # Tail frame does not contain every BASE feature; use available rank fields.
    if len(feat)<8: feat=[c for c in p.columns if c.endswith('_rank')][:30]
    aggs=[]
    for (dt,cat),g in p.groupby(['signal_date','macro_category']):
        rec={'signal_date':dt,'macro_category':cat}
        for f in feat:
            rec[f+'_mean']=g[f].mean();rec[f+'_max']=g[f].max()
        vals=g.fwd_multi.dropna().sort_values(ascending=False)
        rec['target']=vals.iloc[:2].mean() if len(vals)>=2 else np.nan
        rec['label_exit_date_63']=g['exit_date_63'].max()
        aggs.append(rec)
    z=pd.DataFrame(aggs);z['target_rank']=z.groupby('signal_date').target.rank(pct=True)
    return z,[c for c in z if c.endswith(('_mean','_max'))]


def build_opp_panel(D:Mapping[str,pd.DataFrame],clusters:pd.DataFrame,labels:pd.DataFrame):
    raw_names=['ret_21','ret_63','ret_126','ret_252','acc_5_21_broad','acc_21_63_broad','vol_21','vol_63','downvol_21','dist_high_63','slope_21','slope_63']
    blocks=[]
    for n in raw_names:
        if n in D:blocks.append(D[n].stack(dropna=False).rename(n))
    t=pd.concat(blocks,axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    t=t.merge(clusters,on=['signal_date','ticker'],how='inner').merge(labels[['signal_date','ticker','fwd_ret_21','exit_date_21']],on=['signal_date','ticker'],how='left')
    t['resid_mom21']=t.ret_21-t.groupby(['signal_date','cluster_id']).ret_21.transform('mean')
    t['resid_mom63']=t.ret_63-t.groupby(['signal_date','cluster_id']).ret_63.transform('mean')
    features=raw_names+['resid_mom21','resid_mom63']
    rows=[]
    for (dt,cid),g in t.groupby(['signal_date','cluster_id']):
        rec={'signal_date':dt,'cluster_id':cid,'label_exit_date_21':g.exit_date_21.max()}
        for f in features:
            rec[f+'_mean']=g[f].mean();rec[f+'_p75']=g[f].quantile(.75);rec[f+'_max']=g[f].max();rec[f+'_std']=g[f].std()
        vals=g.fwd_ret_21.dropna().sort_values(ascending=False)
        if len(vals):
            rec['target_top2']=vals.iloc[:2].mean();rec['target_spread']=vals.iloc[0]-(vals.iloc[1] if len(vals)>1 else vals.iloc[0]);rec['target_excess_max']=vals.iloc[0]-t.loc[t.signal_date.eq(dt),'fwd_ret_21'].median();rec['target_explosive']=float(vals.iloc[0]>t.loc[t.signal_date.eq(dt),'fwd_ret_21'].quantile(.90))
        rows.append(rec)
    out=pd.DataFrame(rows)
    fcols=[c for c in out if c.endswith(('_mean','_p75','_max','_std'))]
    for c in fcols:out[c+'_rank']=out.groupby('signal_date')[c].rank(pct=True)
    for cid in range(8):out[f'cluster_is_{cid}']=(out.cluster_id==cid).astype(float)
    return out,fcols+[c+'_rank' for c in fcols]+[f'cluster_is_{i}' for i in range(8)]


def fit_predict_all(compact_labeled,tail_labeled,macro_panel,macro_features,opp_panel,opp_features,years):
    preds=[];macro_preds=[];opp_preds=[]
    for year in years:
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        cvalid=compact_labeled[F2D_FEATURES].notna().sum(axis=1)>=30
        tr=compact_labeled[(compact_labeled.signal_date<cutoff)&(compact_labeled.exit_date_21<cutoff)&compact_labeled.target_rank_pct.notna()&cvalid].sort_values(['signal_date','ticker'])
        te=compact_labeled[(compact_labeled.signal_date.dt.year==year)&cvalid].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty:continue
        groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int)
        cp=[]
        for seed in COMPACT_SEEDS:
            m=XGBRanker(**COMPACT_PARAMS,random_state=seed)
            m.fit(tr[F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
            cp.append(m.predict(te[F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
        o=te[['signal_date','ticker']].copy();o['compact_raw']=np.mean(cp,axis=0)
        tvalid=tail_labeled[TAIL_FEATURES].notna().sum(axis=1)>=12
        ttr=tail_labeled[(tail_labeled.signal_date<cutoff)&(tail_labeled.exit_date_63<cutoff)&tail_labeled.y_tailmix.notna()&tvalid]
        tte=tail_labeled[(tail_labeled.signal_date.dt.year==year)&tvalid]
        tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0)).fit(ttr[TAIL_FEATURES],ttr.y_tailmix)
        tp=tte[['signal_date','ticker']].copy();tp['tail_raw']=tm.predict(tte[TAIL_FEATURES])
        o=o.merge(tp,on=['signal_date','ticker'],how='left');preds.append(o)
        mtr=macro_panel[(macro_panel.signal_date<cutoff)&(macro_panel.label_exit_date_63<cutoff)&macro_panel.target_rank.notna()]
        mte=macro_panel[macro_panel.signal_date.dt.year==year]
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0)).fit(mtr[macro_features],mtr.target_rank)
            z=mte[['signal_date','macro_category']].copy();z['macro_raw']=mm.predict(mte[macro_features]);macro_preds.append(z)
        otr=opp_panel[(opp_panel.signal_date<cutoff)&(opp_panel.label_exit_date_21<cutoff)&opp_panel.target_excess_max.notna()]
        ote=opp_panel[opp_panel.signal_date.dt.year==year]
        if len(otr)>100 and len(ote):
            im=SimpleImputer(strategy='median');X=im.fit_transform(otr[opp_features]);Xt=im.transform(ote[opp_features])
            et=ExtraTreesRegressor(n_estimators=300,max_depth=4,min_samples_leaf=30,n_jobs=2,random_state=year).fit(X,otr.target_top2)
            rs=make_pipeline(StandardScaler(),Ridge(alpha=100.0)).fit(X,otr.target_spread)
            re=make_pipeline(StandardScaler(),Ridge(alpha=100.0)).fit(X,otr.target_excess_max)
            rf=RandomForestClassifier(n_estimators=300,max_depth=3,min_samples_leaf=30,n_jobs=2,class_weight='balanced',random_state=year+1).fit(X,otr.target_explosive.astype(int))
            z=ote[['signal_date','cluster_id']].copy();z['p_top2']=et.predict(Xt);z['p_spread']=rs.predict(Xt);z['p_excess']=re.predict(Xt);z['p_explosive']=rf.predict_proba(Xt)[:,1] if len(rf.classes_)>1 else rf.classes_[0]
            for c in ['p_top2','p_spread','p_excess','p_explosive']:z[c+'_rank']=z.groupby('signal_date')[c].rank(pct=True)
            z['opp_raw']=.35*z.p_top2_rank+.15*z.p_spread_rank+.35*z.p_excess_rank+.15*z.p_explosive_rank;opp_preds.append(z)
    p=pd.concat(preds,ignore_index=True);p['compact_rank']=p.groupby('signal_date').compact_raw.rank(pct=True);p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True);p['titanium_score']=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macro_preds,ignore_index=True) if macro_preds else pd.DataFrame(columns=['signal_date','macro_category','macro_raw'])
    if len(mp):
        mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
        tops=[]
        for dt,g in mp.groupby('signal_date'):
            g=g.sort_values('macro_z',ascending=False);tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.})
        top=pd.DataFrame(tops);p['macro_category']=p.ticker.map(TICKER_CATEGORY);p=p.merge(top,on='signal_date',how='left');p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.);p['titanium_score']+=p.macro_bonus
    op=pd.concat(opp_preds,ignore_index=True) if opp_preds else pd.DataFrame(columns=['signal_date','cluster_id','opp_raw'])
    if len(op):op['opp_z']=op.groupby('signal_date').opp_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
    return p,op


def make_baskets(available:Sequence[str]):
    rng=np.random.default_rng(SEED);cats={c:[t for t in xs if t in available] for c,xs in CATEGORY_TICKERS.items()};out=[];seen=set()
    while len(out)<N_BASKETS:
        b=[]
        for c in sorted(cats):b.extend(rng.choice(cats[c],PER_CATEGORY,replace=False).tolist())
        k=tuple(sorted(b))
        if k not in seen:seen.add(k);out.append(b)
    return out


def period_path(weights:Dict[str,float],entry:pd.Timestamp,exit_:pd.Timestamp,O,H,L,C,governor=True):
    days=C.index[(C.index>=entry)&(C.index<exit_)]
    if len(days)==0:return pd.Series(dtype=float)
    sleeve={};
    for t,w in weights.items():
        if t not in O or pd.isna(O.at[entry,t]) or O.at[entry,t]<=0:continue
        ep=float(O.at[entry,t]);vals=[];stopped=False;stop_ratio=1-STOP-STOP_SLIP
        for d in days:
            if not stopped and pd.notna(L.at[d,t]) and float(L.at[d,t])/ep-1<=-STOP:
                stopped=True
            if stopped:
                ratio=stop_ratio
                if governor: ratio=REDUCED_EXPOSURE*stop_ratio+(1-REDUCED_EXPOSURE)
            else:
                px=float(C.at[d,t]) if pd.notna(C.at[d,t]) else ep;ratio=px/ep
            vals.append(ratio)
        sleeve[t]=np.asarray(vals)*w
    if not sleeve:return pd.Series(1.,index=days)
    total=np.sum(list(sleeve.values()),axis=0)+(1-sum(weights.values()))
    series=pd.Series(total,index=days)
    # Include the next rebalance open so the overnight gap is not lost.
    end_total=0.0
    for t,w in weights.items():
        if t not in O.columns or pd.isna(O.at[entry,t]) or O.at[entry,t]<=0: continue
        ep=float(O.at[entry,t])
        crossed=((L.loc[days,t]/ep-1)<=-STOP).any() if t in L.columns else False
        if crossed:
            ratio=(REDUCED_EXPOSURE*(1-STOP-STOP_SLIP)+(1-REDUCED_EXPOSURE)) if governor else (1-STOP-STOP_SLIP)
        else:
            ratio=float(O.at[exit_,t])/ep if pd.notna(O.at[exit_,t]) else float(series.iloc[-1])
        end_total += w*ratio
    end_total += 1-sum(weights.values())
    series.loc[exit_]=end_total
    return series.sort_index()


def simulate(universe:Sequence[str],p:pd.DataFrame,op:pd.DataFrame,clusters:pd.DataFrame,mats,governor=True):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']];dates=sorted(p.signal_date.unique());cmap=clusters.set_index(['signal_date','ticker']).cluster_id.to_dict();opm=op.set_index(['signal_date','cluster_id']).opp_z.to_dict() if len(op) else {}
    old={'BASE':{},'DIRECT':{},'ROUTER':{}};shadow=[];paths={k:[] for k in old};targets=[]
    for i,dt in enumerate(dates[:-1]):
        dt=pd.Timestamp(dt);nxt=pd.Timestamp(dates[i+1]);pos=O.index.get_indexer([dt])[0];pos2=O.index.get_indexer([nxt])[0]
        if pos<0 or pos2<0 or pos+1>=len(O) or pos2+1>=len(O):continue
        entry=O.index[pos+1];exit_=O.index[pos2+1]
        g=p[(p.signal_date==dt)&p.ticker.isin(universe)&p.titanium_score.notna()].sort_values('titanium_score',ascending=False)
        g=g[g.ticker.map(lambda t: t in O.columns and pd.notna(O.at[entry,t]) and pd.notna(O.at[exit_,t]))]
        if len(g)<2:continue
        t1,t2=g.iloc[0].ticker,g.iloc[1].ticker;margin=float(g.iloc[0].titanium_score-g.iloc[1].titanium_score);w1=1.0 if margin>=.12 else .75
        wb={t1:w1,t2:1-w1}
        cid=cmap.get((dt,t1));scores={c:opm.get((dt,c),np.nan) for c in range(8)};ss=pd.Series(scores).dropna().sort_values(ascending=False);gap=float(ss.iloc[0]-ss.iloc[1]) if len(ss)>1 else -np.inf;topc=int(ss.index[0]) if len(ss) else None
        direct=bool(w1<1 and cid is not None and cid==topc and gap>=.50);wd={t1:1.0} if direct else dict(wb)
        router_on=len(shadow)>=12 and float(np.sum(shadow[-12:]))>0;wr=dict(wd if router_on else wb)
        gross={}
        for name,w in [('BASE',wb),('DIRECT',wd),('ROUTER',wr)]:
            q=period_path(w,entry,exit_,O,H,L,C,governor);turn=sum(abs(w.get(t,0)-old[name].get(t,0)) for t in set(w)|set(old[name]));cost=COST*turn;q=(1-cost)*q;gross[name]=float(q.iloc[-1]-1) if len(q) else np.nan
            if len(q):
                paths[name].append((q,1-cost))
            old[name]=w
        shadow.append(math.log1p(max(-.999999,gross['DIRECT']))-math.log1p(max(-.999999,gross['BASE'])))
        targets.append({'signal_date':dt,'entry_date':entry,'exit_date':exit_,'top1':t1,'top2':t2,'margin':margin,'direct':direct,'router_on':router_on,'opp_gap_z':gap})
    result={}
    for name,segments in paths.items():
        wealth=1.;pieces=[]
        for q,costfac in segments:
            qq=q*wealth;pieces.append(qq);wealth=float(qq.iloc[-1])
        eq=pd.concat(pieces) if pieces else pd.Series(dtype=float);eq=eq[~eq.index.duplicated(keep='last')]
        if len(eq)<2:result[name]={'cagr':np.nan,'maxdd':np.nan,'sharpe':np.nan,'final_equity':np.nan,'months':0};continue
        years=(eq.index[-1]-eq.index[0]).days/365.25;cagr=eq.iloc[-1]**(1/years)-1;dd=eq/eq.cummax()-1;dr=eq.pct_change().dropna();sh=np.sqrt(252)*dr.mean()/dr.std(ddof=0) if dr.std(ddof=0)>0 else np.nan
        result[name]={'cagr':float(cagr),'maxdd':float(dd.min()),'sharpe':float(sh),'final_equity':float(eq.iloc[-1]),'months':len(targets),'equity':eq}
    return result,pd.DataFrame(targets)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',default='titanium_retrained_output');ap.add_argument('--fast',action='store_true');args=ap.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
    global N_BASKETS,COMPACT_PARAMS
    if args.fast:N_BASKETS=20;COMPACT_PARAMS=dict(COMPACT_PARAMS,n_estimators=60,n_jobs=2)
    mats=download_ohlcv(out);dates,compact,tail,D=build_features(mats);compact_l=add_labels(compact,mats['Open'],dates);tail_l=add_labels(tail,mats['Open'],dates)
    clusters=build_clusters(D,dates,mats['Close'].columns);macro,macro_f=build_macro_panel(tail,tail_l);opp,opp_f=build_opp_panel(D,clusters,compact_l)
    years=range(BACKTEST_START.year,pd.Timestamp(END_DOWNLOAD).year+1);pred,opp_pred=fit_predict_all(compact_l,tail_l,macro,macro_f,opp,opp_f,years)
    pred=pred[pred.signal_date>=BACKTEST_START];opp_pred=opp_pred[opp_pred.signal_date>=BACKTEST_START]
    available=[t for t in ALL_TICKERS if t in mats['Close'].columns];baskets=make_baskets(available)
    rows=[];membership=[]
    for i,b in enumerate(baskets):
        r,t=simulate(b,pred,opp_pred,clusters,mats,True);membership.extend({'basket_id':i,'ticker':x,'category':TICKER_CATEGORY[x]} for x in b)
        for s in ['BASE','DIRECT','ROUTER']:rows.append({'basket_id':i,'strategy':s,**{k:v for k,v in r[s].items() if k!='equity'}})
        if (i+1)%25==0:print('basket',i+1,flush=True)
    res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS_500.csv',index=False);pd.DataFrame(membership).to_csv(out/'BASKET_MEMBERSHIP_500.csv',index=False)
    gr,gt=simulate(available,pred,opp_pred,clusters,mats,True);grows=[]
    for s in ['BASE','DIRECT','ROUTER']:
        grows.append({'strategy':s,**{k:v for k,v in gr[s].items() if k!='equity'}})
        gr[s]['equity'].rename(s).to_csv(out/f'GLOBAL_{s}_EQUITY.csv')
    pd.DataFrame(grows).to_csv(out/'GLOBAL_UNRESTRICTED_SCORECARD.csv',index=False);gt.to_csv(out/'GLOBAL_MONTHLY_TARGETS.csv',index=False)
    pred.to_parquet(out/'OOS_TICKER_SCORES.parquet');opp_pred.to_csv(out/'OOS_OPPORTUNITY_CLUSTER_SCORES.csv',index=False);clusters.to_csv(out/'DYNAMIC_CLUSTERS_CURRENT_DATA.csv',index=False)
    router=res.query("strategy=='ROUTER'").copy();summary=router[['cagr','maxdd','sharpe']].describe(percentiles=[.01,.05,.10,.25,.5,.75,.90,.95,.99]).T;summary.to_csv(out/'ROUTER_DISTRIBUTION_SUMMARY.csv')
    gc=float(pd.DataFrame(grows).query("strategy=='ROUTER'").cagr.iloc[0])*100
    plt.figure(figsize=(10,6));plt.hist(router.cagr*100,bins=30,edgecolor='black');plt.axvline(router.cagr.mean()*100,linestyle='--',label=f"Media {router.cagr.mean()*100:.2f}%");plt.axvline(router.cagr.median()*100,linestyle=':',label=f"Mediana {router.cagr.median()*100:.2f}%");plt.axvline(gc,label=f"Universo libero {gc:.2f}%");plt.xlabel('CAGR (%)');plt.ylabel('Panieri');plt.title('Titanium retrained — CAGR su 500 panieri');plt.legend();plt.grid(alpha=.2);plt.tight_layout();plt.savefig(out/'CAGR_500_BASKETS_HISTOGRAM.png',dpi=180);plt.close()
    vals=np.sort(router.cagr.dropna()*100);plt.figure(figsize=(10,6));plt.plot(vals,np.arange(1,len(vals)+1)/len(vals));plt.axvline(gc,linestyle='--',label=f"Universo libero {gc:.2f}%");plt.xlabel('CAGR (%)');plt.ylabel('Distribuzione cumulata');plt.title('Titanium retrained — ECDF CAGR');plt.legend();plt.grid(alpha=.2);plt.tight_layout();plt.savefig(out/'CAGR_500_BASKETS_ECDF.png',dpi=180);plt.close()
    manifest={'status':'executed_current_data_retraining','not_frozen_replication':True,'architecture':['3-seed XGBRanker exact published params','Ridge TailMix alpha30','70/30 score','macro Ridge alpha50 and +0.15 gate','8 dynamic causal clusters','Opportunity multi-model router trailing12','adaptive concentration 0.12','D+1 adjusted open','10bp one-way costs','5.5% stop, 25% residual exposure'],'deviations':['Yahoo data current, not frozen','dynamic clusters recomputed from current data rather than embedded frozen intervals','governor reconstructed from published constants','500 baskets newly generated, 24 ETF, 4 per category'],'tickers_requested':150,'tickers_downloaded':len(available),'baskets':len(baskets)}
    (out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2));
    q=router.cagr.quantile([.01,.05,.10,.25,.5,.75,.90,.95,.99])*100;glob=pd.DataFrame(grows).set_index('strategy')
    report=f"""# Titanium retrained on current data\n\nThis is an executed current-data retraining of the published architecture, not the frozen historical artifact.\n\n## Router distribution across {len(baskets)} balanced 24-ETF baskets\n\n- Mean CAGR: {router.cagr.mean()*100:.3f}%\n- Median CAGR: {router.cagr.median()*100:.3f}%\n- P05/P95: {q.loc[.05]:.3f}% / {q.loc[.95]:.3f}%\n- P10/P90: {q.loc[.10]:.3f}% / {q.loc[.90]:.3f}%\n- Min/Max: {router.cagr.min()*100:.3f}% / {router.cagr.max()*100:.3f}%\n- Positive CAGR: {(router.cagr>0).mean()*100:.1f}%\n- Median MaxDD: {router.maxdd.median()*100:.3f}%\n\n## Unrestricted universe\n\n| Strategy | CAGR | MaxDD | Sharpe |\n|---|---:|---:|---:|\n| BASE | {glob.loc['BASE','cagr']*100:.3f}% | {glob.loc['BASE','maxdd']*100:.3f}% | {glob.loc['BASE','sharpe']:.3f} |\n| DIRECT | {glob.loc['DIRECT','cagr']*100:.3f}% | {glob.loc['DIRECT','maxdd']*100:.3f}% | {glob.loc['DIRECT','sharpe']:.3f} |\n| ROUTER | {glob.loc['ROUTER','cagr']*100:.3f}% | {glob.loc['ROUTER','maxdd']*100:.3f}% | {glob.loc['ROUTER','sharpe']:.3f} |\n""";(out/'REPORT.md').write_text(report)
    import shutil;shutil.make_archive(str(out),'zip',out);print(report,flush=True)
if __name__=='__main__':main()
