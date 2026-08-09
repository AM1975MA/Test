#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def rms_downvol(lr: pd.DataFrame, h: int) -> pd.DataFrame:
    neg = lr.where(lr < 0, 0.0)
    return np.sqrt(neg.pow(2).rolling(h, min_periods=h).mean() * 252)


def exact_broad(base, mats, dates, compact_frames):
    O, H, L, C, V = [mats[k] for k in ['Open','High','Low','Close','Volume']]
    logc = np.log(C.where(C > 0))
    lr = logc.diff()
    ret = C.pct_change(fill_method=None)
    prev = C.shift(1)
    gap = O / prev - 1
    intraday = C / O - 1
    tr = pd.DataFrame(
        np.maximum.reduce([(H-L).to_numpy(), (H-prev).abs().to_numpy(), (L-prev).abs().to_numpy()]),
        index=C.index, columns=C.columns,
    )
    dollar = V * C
    signed = np.sign(ret) * V
    amihud = ret.abs() / dollar.replace(0, np.nan)
    D = {}
    for k, v in compact_frames.items():
        if not k.endswith('_pct') and not k.endswith('_dev'):
            D[k] = v.copy()

    for h in [3,5,10,21,42,63,126,252]:
        D[f'ret_{h}'] = base.snapshot(C.pct_change(h, fill_method=None), dates)
    D['mom_21_5'] = base.snapshot(C.shift(5)/C.shift(21)-1, dates)
    D['mom_63_5'] = base.snapshot(C.shift(5)/C.shift(63)-1, dates)
    D['mom_126_21'] = base.snapshot(C.shift(21)/C.shift(126)-1, dates)
    D['mom_252_21'] = base.snapshot(C.shift(21)/C.shift(252)-1, dates)
    D['acc_3_10'] = D['ret_3'] - (3/10)*D['ret_10']
    D['acc_5_21_broad'] = D['ret_5'] - (5/21)*D['ret_21']
    D['acc_21_63_broad'] = D['ret_21'] - (21/63)*D['ret_63']
    D['acc_63_126'] = D['ret_63'] - .5*D['ret_126']
    D['jerk'] = D['acc_3_10'] - D['acc_5_21_broad']

    for h in [20,50,100,200]:
        D[f'sma_ratio_{h}'] = base.snapshot(C/C.rolling(h,min_periods=h).mean()-1, dates)
    for h in [21,63,126]:
        D[f'dist_high_{h}'] = base.snapshot(C/C.rolling(h,min_periods=h).max()-1, dates)
        D[f'dd_{h}'] = D[f'dist_high_{h}']
        D[f'eff_{h}'] = base.snapshot(base.rolling_efficiency(logc,h), dates)
    for h in [10,21,63,126]:
        D[f'vol_{h}'] = base.snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252), dates)
    for h in [21,63,126]:
        D[f'downvol_{h}'] = base.snapshot(rms_downvol(lr,h), dates)

    # Exact July-27 risk/shape block.
    gk = .5*np.log(H/L.replace(0,np.nan)).pow(2) - (2*np.log(2)-1)*np.log(C/O.replace(0,np.nan)).pow(2)
    gk = gk.clip(lower=0)
    D['gkvol21'] = base.snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252), dates)
    atr14 = tr.rolling(14,min_periods=14).mean()/C
    atr63 = tr.rolling(63,min_periods=63).mean()/C
    D['atr_14'] = base.snapshot(atr14, dates)
    D['atr_ratio'] = base.snapshot(atr14/atr63.replace(0,np.nan), dates)
    D['energy_21'] = base.snapshot(lr.pow(2).rolling(21,min_periods=21).sum(), dates)
    D['energy_63'] = base.snapshot(lr.pow(2).rolling(63,min_periods=63).sum(), dates)
    D['directional_energy_21'] = base.snapshot(
        lr.rolling(21,min_periods=21).sum().pow(2)/lr.pow(2).rolling(21,min_periods=21).sum().replace(0,np.nan), dates)
    D['directional_energy_63'] = base.snapshot(
        lr.rolling(63,min_periods=63).sum().pow(2)/lr.pow(2).rolling(63,min_periods=63).sum().replace(0,np.nan), dates)

    mean20=C.rolling(20,min_periods=20).mean(); std20=C.rolling(20,min_periods=20).std()
    mean63=C.rolling(63,min_periods=63).mean(); std63=C.rolling(63,min_periods=63).std()
    D['boll_z20'] = base.snapshot((C-mean20)/std20.replace(0,np.nan), dates)
    D['boll_z63'] = base.snapshot((C-mean63)/std63.replace(0,np.nan), dates)
    D['rsi14_broad'] = base.snapshot(base.rolling_rsi(C,14), dates)
    D['stoch63'] = base.snapshot((C-L.rolling(63,min_periods=63).min())/(H.rolling(63,min_periods=63).max()-L.rolling(63,min_periods=63).min()).replace(0,np.nan), dates)
    D['gap_mean5'] = base.snapshot(gap.rolling(5,min_periods=5).mean(), dates)
    D['gap_vol21'] = base.snapshot(gap.rolling(21,min_periods=21).std(), dates)
    D['gap_min5'] = base.snapshot(gap.rolling(5,min_periods=5).min(), dates)
    D['intraday_mean5'] = base.snapshot(intraday.rolling(5,min_periods=5).mean(), dates)
    rng=(H-L)/C
    D['range_z20'] = base.snapshot((rng-rng.rolling(20,min_periods=20).mean())/rng.rolling(20,min_periods=20).std().replace(0,np.nan), dates)

    lv=np.log1p(V)
    for h in [20,63]:
        D[f'volume_z{h}'] = base.snapshot((lv-lv.rolling(h,min_periods=h).mean())/lv.rolling(h,min_periods=h).std().replace(0,np.nan), dates)
    D['volume_ratio5_20'] = base.snapshot(V.rolling(5,min_periods=5).mean()/V.rolling(20,min_periods=20).mean()-1, dates)
    D['volume_ratio20_63'] = base.snapshot(V.rolling(20,min_periods=20).mean()/V.rolling(63,min_periods=63).mean()-1, dates)
    D['signed_volume21'] = base.snapshot(signed.rolling(21,min_periods=21).sum()/V.rolling(21,min_periods=21).sum().replace(0,np.nan), dates)
    D['amihud21'] = base.snapshot(amihud.rolling(21,min_periods=21).mean(), dates)
    D['amihud63'] = base.snapshot(amihud.rolling(63,min_periods=63).mean(), dates)
    D['pv_corr21'] = base.snapshot(ret.rolling(21,min_periods=21).corr(V.pct_change(fill_method=None)), dates)

    D['slope_21'] = base.snapshot(base.rolling_slope(logc,21), dates)
    D['slope_63'] = base.snapshot(base.rolling_slope(logc,63), dates)
    D['r2_63'] = base.snapshot(base.rolling_r2(logc,63), dates)
    D['autocorr1_63'] = base.snapshot(base.rolling_autocorr(ret,63), dates)
    D['spectral_entropy64'] = base.snapshot(base.spectral_entropy_frame(lr,64), dates)

    D['max_loss21'] = base.snapshot(ret.rolling(21,min_periods=21).min(), dates)
    D['max_gain21'] = base.snapshot(ret.rolling(21,min_periods=21).max(), dates)
    D['max_gain63'] = compact_frames['max_gain63']
    D['positive_frac63'] = compact_frames['positive_frac63']
    D['breakout_pos126'] = compact_frames['breakout_pos126']
    D['breakout_pos252'] = compact_frames['breakout_pos252']
    D['sign_entropy63'] = compact_frames['sign_entropy63']
    D['ma_gap200'] = compact_frames['ma_gap200']
    D['ma_gap50'] = compact_frames['ma_gap50']
    D['ema_gap50'] = compact_frames['ema_gap50']
    D['cvar10_63'] = compact_frames['cvar10_63']
    D['ret63_vol126'] = D['ret_63']/D['vol_126'].replace(0,np.nan)
    D['kurt_63'] = base.snapshot(lr.rolling(63,min_periods=63).kurt(), dates)

    # Production naming aliases before cross-sectional ranking.
    D['acc_5_21'] = D['acc_5_21_broad']
    D['acc_21_63'] = D['acc_21_63_broad']
    D['mom21'] = D['ret_21']; D['mom42'] = D['ret_42']; D['mom63'] = D['ret_63']; D['mom126'] = D['ret_126']; D['mom252'] = D['ret_252']
    D['mom126_ex21'] = D['mom_126_21']
    D['efficiency126'] = D['eff_126']
    D['vol21'] = D['vol_21']; D['vol63'] = D['vol_63']; D['vol126'] = D['vol_126']
    D['downvol21'] = D['downvol_21']; D['downvol63'] = D['downvol_63']; D['downvol126'] = D['downvol_126']
    D['acc_mom_21_63'] = D['acc_21_63_broad']
    D['kurt63'] = D['kurt_63']

    # Cross-sectional ranks after the exact raw block exists.
    for k,v in list(D.items()):
        if not k.endswith('_rank'):
            D[k+'_rank'] = base.cs_pct(v)

    # Required duplicate aliases retained in the historical TailMix feature list.
    alias = {
        'beta_mkt63_rank':'beta_mkt63_rank',
        'beta_mkt126_rank':'beta_mkt126_rank',
        'corr_mkt63_rank':'corr_mkt63_rank',
        'corr_mkt126_rank':'corr_mkt126_rank',
        'ma_gap200_rank':'ma_gap200_rank',
        'ma_gap50_rank':'ma_gap50_rank',
        'ema_gap50_rank':'ema_gap50_rank',
        'gkvol21_rank':'gkvol21_rank',
        'energy_21_rank':'energy_21_rank','energy_63_rank':'energy_63_rank',
        'vol_21_rank':'vol_21_rank','vol21_rank':'vol21_rank','vol63_rank':'vol63_rank','vol_63_rank':'vol_63_rank','vol126_rank':'vol126_rank','vol_126_rank':'vol_126_rank',
        'downvol_21_rank':'downvol_21_rank','downvol21_rank':'downvol21_rank','downvol_63_rank':'downvol_63_rank','downvol63_rank':'downvol63_rank','downvol126_rank':'downvol126_rank',
        'mom_21_5_rank':'mom_21_5_rank','mom_63_5_rank':'mom_63_5_rank','mom_126_21_rank':'mom_126_21_rank','mom126_ex21_rank':'mom126_ex21_rank',
        'ret_21_rank':'ret_21_rank','mom21_rank':'mom21_rank','ret_42_rank':'ret_42_rank','mom42_rank':'mom42_rank','ret_63_rank':'ret_63_rank','mom63_rank':'mom63_rank','ret_126_rank':'ret_126_rank','mom126_rank':'mom126_rank',
        'eff_126_rank':'eff_126_rank','efficiency126_rank':'efficiency126_rank',
        'acc_21_63_broad_rank':'acc_21_63_broad_rank','acc_mom_21_63_rank':'acc_mom_21_63_rank',
        'kurt_63_rank':'kurt_63_rank','kurt63_rank':'kurt63_rank',
    }
    for dst,src in alias.items():
        if src in D: D[dst]=D[src]

    for req in base.TAIL_FEATURES:
        if req not in D:
            raw=req[:-5] if req.endswith('_rank') else req
            D[req]=base.cs_pct(D[raw]) if raw in D else pd.DataFrame(np.nan,index=dates,columns=C.columns)
    tail_long=pd.concat([D[n].stack(dropna=False).rename(n) for n in base.TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    return tail_long,D


def fit_all(base, compact, tail, macro, macro_feats, years, n_estimators):
    params=dict(base.COMPACT_PARAMS); params['n_estimators']=n_estimators; params['n_jobs']=2
    preds=[]; macros=[]; audits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker'])
        te=compact[compact.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist(); y=(tr.target_rank_pct*100).round().astype(int)
        cp=[]
        for seed in base.COMPACT_SEEDS:
            m=XGBRanker(**params,random_state=seed)
            m.fit(tr[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
            cp.append(m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
        q=te[['signal_date','ticker']].copy(); q['compact_raw']=np.mean(cp,axis=0)

        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()]
        tte=tail[tail.signal_date.dt.year.eq(year)]
        tm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.0))
        tm.fit(ttr[base.TAIL_FEATURES],ttr.y_tailmix)
        tq=tte[['signal_date','ticker']].copy(); tq['tail_raw']=tm.predict(tte[base.TAIL_FEATURES])
        preds.append(q.merge(tq,on=['signal_date','ticker'],how='left'))

        mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year.eq(year)]
        if len(mtr)>50 and len(mte):
            mm=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.0))
            mm.fit(mtr[macro_feats],mtr.target_rank)
            mq=mte[['signal_date','macro_category']].copy(); mq['macro_raw']=mm.predict(mte[macro_feats]); macros.append(mq)
        audits.append({'year':year,'compact_train_rows':len(tr),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr)})
    p=pd.concat(preds,ignore_index=True)
    p['compact_rank']=p.groupby('signal_date').compact_raw.rank(pct=True)
    p['tail_rank']=p.groupby('signal_date').tail_raw.rank(pct=True)
    p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macros,ignore_index=True)
    mp['macro_z']=mp.groupby('signal_date').macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
    tops=[]
    for dt,g in mp.groupby('signal_date'):
        g=g.sort_values('macro_z',ascending=False)
        tops.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap_z':float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.0})
    p['macro_category']=p.ticker.map(base.TICKER_CATEGORY)
    p=p.merge(pd.DataFrame(tops),on='signal_date',how='left')
    p['macro_bonus']=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.0)
    p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    return p.sort_values(['signal_date','ticker']),pd.DataFrame(audits),mp


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--package',required=True); ap.add_argument('--prior-probe',required=True); ap.add_argument('--output',default='BROAD_TAIL_PARITY'); ap.add_argument('--trees',type=int,default=360)
    a=ap.parse_args(); pkg=Path(a.package).resolve(); prior=Path(a.prior_probe).resolve(); out=Path(a.output).resolve(); shutil.rmtree(out,ignore_errors=True); out.mkdir(parents=True)
    t0=time.time()
    base=load_module('bt_base',pkg/'source'/'titanium_retrained_current_data_audit.py')
    v6=load_module('bt_v6',pkg/'source'/'titanium_reconstruction_v6.py')
    probe=load_module('bt_probe',prior)
    mats=v6.load_mats(pkg/'data')
    dates=base.month_end_dates(mats['Close'].index)
    compact,compact_frames=probe.exact_compact(base,mats,dates)
    compact=base.add_labels(compact,mats['Open'],dates)
    tail,D=exact_broad(base,mats,dates,compact_frames)
    labels=compact[['signal_date','ticker','entry_date','exit_date','exit_date_21','exit_date_63','target_rank_21','target_rank_42','target_rank_63','target_multi_rank','y_tailmix','fwd_ret_21','fwd_ret_42','fwd_ret_63']]
    tail=tail.merge(labels,on=['signal_date','ticker'],how='left')
    macro,macro_feats=v6.build_macro_panel(base,D,compact,base.TICKER_CATEGORY)
    pred,audit,mp=fit_all(base,compact,tail,macro,macro_feats,range(2017,2027),a.trees)
    pred=pred[pred.signal_date>=v6.BACKTEST_START].copy()
    cal=pd.read_csv(pkg/'panels'/'MONTHLY_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date']); cal=cal[cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    clusters=pd.read_csv(pkg/'panels'/'DYNAMIC_CLUSTERS_MONTHLY.csv',parse_dates=['signal_date'])
    opp=pd.read_csv(pkg/'panels'/'TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv',parse_dates=['signal_date'])
    mem=pd.read_csv(pkg/'panels'/'BASKET_MEMBERSHIP_500.csv'); baskets=[tuple(sorted(g.ticker.astype(str))) for _,g in mem.groupby('basket',sort=True)]
    idx,EB,ED,ER,active,margin,cond,*_=v6.simulate_all(baskets,pred,opp,clusters,mats,cal)
    rows=[]
    for b in range(500):
        cagr,maxdd,sharpe,fe=v6.metrics(EB[b],idx); rows.append({'basket':b,'cagr':cagr,'maxdd':maxdd,'sharpe':sharpe,'final_equity':fe})
    r=pd.DataFrame(rows); r.to_csv(out/'BASE_BASKET_RESULTS.csv',index=False); pred.to_parquet(out/'OOS_TICKER_SCORES.parquet',index=False); audit.to_csv(out/'FIT_AUDIT.csv',index=False)
    chk=pred[pred.signal_date.eq(pd.Timestamp('2026-06-30'))].sort_values('titanium_score',ascending=False)
    chk.head(20).to_csv(out/'CHECKPOINT_20260630.csv',index=False)
    tail_snapshot=tail[tail.signal_date.eq(pd.Timestamp('2026-06-30')) & tail.ticker.isin(['USO','PALL','BNO'])]
    tail_snapshot.to_csv(out/'TAIL_FEATURES_USO_PALL_BNO_20260630.csv',index=False)
    summary={'trees':a.trees,'n_scored_tickers':int(pred.ticker.nunique()),'n_oos_months':int(pred.signal_date.nunique()),'base_mean_cagr':float(r.cagr.mean()),'base_median_cagr':float(r.cagr.median()),'base_median_maxdd':float(r.maxdd.median()),'frozen_base_mean_cagr':.21654064,'gap_pp':float((r.cagr.mean()-.21654064)*100),'checkpoint_top1':str(chk.iloc[0].ticker),'checkpoint_top2':str(chk.iloc[1].ticker),'checkpoint_matches_USO_PALL':bool(chk.iloc[0].ticker=='USO' and chk.iloc[1].ticker=='PALL'),'pall_tail_rank':float(chk.set_index('ticker').loc['PALL','tail_rank']),'bno_tail_rank':float(chk.set_index('ticker').loc['BNO','tail_rank']),'macro_bonus_months':int(pred.groupby('signal_date').macro_bonus.max().gt(0).sum()),'elapsed_seconds':time.time()-t0}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2)); print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__': main()
