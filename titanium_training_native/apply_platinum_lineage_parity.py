#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def one(s, old, new, label):
    n=s.count(old)
    if n!=1:
        raise RuntimeError(f'{label}: expected one site, found {n}')
    return s.replace(old,new)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()

    # Platinum/Super Gold frozen cross-sectional deviation is raw - current-date median.
    old="def cs_robust_dev(x):\n    med=x.median(axis=1,skipna=True); q75=x.quantile(.75,axis=1); q25=x.quantile(.25,axis=1); sc=(q75-q25).replace(0,np.nan); return x.sub(med,axis=0).div(sc,axis=0).clip(-8,8)"
    new="def cs_robust_dev(x):\n    med=x.median(axis=1,skipna=True); return x.sub(med,axis=0)"
    s=one(s,old,new,'cross-section dev')

    # Replace the Compact builder with the Jul22/23 Platinum formulas while retaining
    # the later Compact extensions that are part of the 125-feature frozen contract.
    start=s.index('def build_compact(mats,base):')
    end=s.index('\ndef add_labels(panel,O,signal_dates):',start)
    new_build=r'''def build_compact(mats,base):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]; dates=month_end_dates(C.index)
    logc=np.log(C.where(C>0)); lr=logc.diff(); ret=C.pct_change(fill_method=None)
    out={}
    for h in [5,10,21,42,63,126,252]: out[f'mom{h}']=snapshot(logc-logc.shift(h),dates)
    for h in [21,63,126]:
        minp=max(10,int(h*.75))
        out[f'vol{h}']=snapshot(lr.rolling(h,min_periods=minp).std(ddof=0)*np.sqrt(252),dates)
        neg=lr.where(lr<0,0.0)
        out[f'downvol{h}']=snapshot(neg.rolling(h,min_periods=minp).std(ddof=0)*np.sqrt(252),dates)
        out[f'drawdown{h}']=snapshot(C/C.rolling(h,min_periods=minp).max()-1,dates)
        path=lr.abs().rolling(h,min_periods=minp).sum()
        out[f'efficiency{h}']=snapshot((logc-logc.shift(h)).abs()/path.replace(0,np.nan),dates)
    out['mom126_ex21']=snapshot(logc.shift(21)-logc.shift(126),dates)
    out['mom252_ex21']=snapshot(logc.shift(21)-logc.shift(252),dates)
    out['acc_mom_5_21']=out['mom5']-(5.0/16.0)*snapshot(logc.shift(5)-logc.shift(21),dates)
    out['acc_mom_21_63']=out['mom21']-0.5*snapshot(logc.shift(21)-logc.shift(63),dates)
    out['vol_ratio_21_126']=np.log(out['vol21']/out['vol126'].replace(0,np.nan))
    out['skew63']=snapshot(lr.rolling(63,min_periods=45).skew(),dates)
    out['kurt63']=snapshot(lr.rolling(63,min_periods=45).kurt(),dates)
    hl=np.log(H.where(H>0)/L.where(L>0)); co=np.log(C.where(C>0)/O.where(O>0))
    gk=(.5*hl.pow(2)-(2*np.log(2)-1)*co.pow(2)).clip(lower=0)
    out['gkvol21']=snapshot(np.sqrt(gk.rolling(21,min_periods=15).mean()*252),dates)
    dollar=C*V
    out['log_adv63']=snapshot(np.log(dollar.rolling(63,min_periods=42).median().where(lambda x:x>0)),dates)
    out['volume_surprise21']=snapshot(np.log(V.rolling(21,min_periods=15).mean()/V.rolling(63,min_periods=42).median().replace(0,np.nan)),dates)
    market='SPY' if 'SPY' in lr.columns else lr.notna().sum().idxmax(); mret=lr[market]
    for h in [63,126]:
        minp=int(h*.75); cov=lr.rolling(h,min_periods=minp).cov(mret); var=mret.rolling(h,min_periods=minp).var(ddof=0)
        out[f'beta_mkt{h}']=snapshot(cov.div(var.replace(0,np.nan),axis=0),dates)
        out[f'corr_mkt{h}']=snapshot(lr.rolling(h,min_periods=minp).corr(mret),dates)
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
    vc=C.notna().rolling(252,min_periods=1).sum().reindex(dates); vc.index.name='signal_date'; vc.columns.name='ticker'
    panel=panel.merge(vc.stack(dropna=False).rename('past_close_obs').reset_index(),on=['signal_date','ticker'],how='left')
    return dates,panel,out
'''
    s=s[:start]+new_build+s[end:]

    old="out['target_rank_pct']=out.groupby('signal_date')['fwd_ret_monthly'].rank(pct=True,method='average'); out['target_top25']=(out.target_rank_pct>=.75).astype('Int64'); out['target_multi_rank']=.45*out.target_rank_21+.35*out.target_rank_42+.20*out.target_rank_63; out['y_tailmix']=.60*out.target_rank_21.astype(float)**4+.25*out.target_rank_42.astype(float)**4+.15*out.target_rank_63.astype(float)**4\n    return out"
    new="out['target_rank_pct']=out['target_rank_21']; out['target_top25']=(out.target_rank_pct>=.75).astype('Int64'); out['target_multi_rank']=.45*out.target_rank_21+.35*out.target_rank_42+.20*out.target_rank_63; out['y_tailmix']=.60*out.target_rank_21.astype(float)**4+.25*out.target_rank_42.astype(float)**4+.15*out.target_rank_63.astype(float)**4\n    entry_ok=np.zeros(len(out),dtype=bool)\n    for sd,inds0 in out.groupby('signal_date').groups.items():\n        inds=np.asarray(list(inds0)); i=pos.get(pd.Timestamp(sd))\n        if i is None or i+1>=len(dates): continue\n        tix=np.array([ti[t] for t in out.loc[inds,'ticker']],int); entry_ok[inds]=np.isfinite(O.iloc[i+1,tix].to_numpy(float))\n    out=out[(out.past_close_obs>=126)&entry_ok].copy()\n    return out"
    s=one(s,old,new,'21d target and PIT eligibility')

    old="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    new="tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])"
    s=one(s,old,new,'Compact 21d maturity')
    relevance="groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]"
    if s.count(relevance)!=1: raise RuntimeError(f'Compact relevance anchor count={s.count(relevance)}')

    s=s.replace("'compact_target':'fwd_ret_monthly'","'compact_target':'fwd_ret_21_PLATINUM_LINEAGE'")
    s=s.replace("'compact_historical_params':False","'compact_historical_params':'PUBLISHED_360x3_WITH_PLATINUM_FEATURE_PARITY'")
    s=s.replace("'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None","'compact_max_exit':str(pd.to_datetime(tr.exit_date_21).max().date()) if len(tr) else None")
    p.write_text(s)
    print('Applied Platinum-lineage Compact feature/target/PIT parity')

if __name__=='__main__': main()
