#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--source',required=True); a=ap.parse_args()
    p=Path(a.source); s=p.read_text()
    start=s.index('def build_broad(mats,dates,compact_frames,base):')
    end=s.index('\ndef build_macro(', start)
    new=r'''def build_broad(mats,dates,compact_frames,base):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]
    logc=np.log(C.where(C>0)); lr=logc.diff(); ret=C.pct_change(fill_method=None)
    prev=C.shift(1); gap=O/prev-1; intraday=C/O-1
    tr=pd.DataFrame(np.maximum.reduce([(H-L).to_numpy(),(H-prev).abs().to_numpy(),(L-prev).abs().to_numpy()]),index=C.index,columns=C.columns)
    dollar=V*C; signed=np.sign(ret)*V; amihud=ret.abs()/dollar.replace(0,np.nan)
    D={}
    for k,v in compact_frames.items():
        if not k.endswith('_pct') and not k.endswith('_dev'): D[k]=v.copy()
    for h in [3,5,10,21,42,63,126,252]: D[f'ret_{h}']=snapshot(C.pct_change(h,fill_method=None),dates)
    D['mom_21_5']=snapshot(C.shift(5)/C.shift(21)-1,dates)
    D['mom_63_5']=snapshot(C.shift(5)/C.shift(63)-1,dates)
    D['mom_126_21']=snapshot(C.shift(21)/C.shift(126)-1,dates)
    D['mom_252_21']=snapshot(C.shift(21)/C.shift(252)-1,dates)
    D['acc_3_10']=D['ret_3']-(3/10)*D['ret_10']; D['acc_5_21_broad']=D['ret_5']-(5/21)*D['ret_21']; D['acc_21_63_broad']=D['ret_21']-(21/63)*D['ret_63']; D['acc_63_126']=D['ret_63']-.5*D['ret_126']; D['jerk']=D['acc_3_10']-D['acc_5_21_broad']
    for h in [20,50,100,200]: D[f'sma_ratio_{h}']=snapshot(C/C.rolling(h,min_periods=h).mean()-1,dates)
    for h in [21,63,126]:
        D[f'dist_high_{h}']=snapshot(C/C.rolling(h,min_periods=h).max()-1,dates); D[f'dd_{h}']=D[f'dist_high_{h}']; D[f'eff_{h}']=snapshot(rolling_efficiency(logc,h),dates)
    for h in [10,21,63,126]: D[f'vol_{h}']=snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252),dates)
    for h in [21,63,126]: D[f'downvol_{h}']=snapshot(rolling_downvol(lr,h),dates)
    gk=.5*np.log(H/L.replace(0,np.nan)).pow(2)-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan)).pow(2); gk=gk.clip(lower=0)
    D['gkvol21']=snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252),dates)
    atr14=tr.rolling(14,min_periods=14).mean()/C; atr63=tr.rolling(63,min_periods=63).mean()/C
    D['atr_14']=snapshot(atr14,dates); D['atr_ratio']=snapshot(atr14/atr63.replace(0,np.nan),dates)
    D['energy_21']=snapshot(lr.pow(2).rolling(21,min_periods=21).sum(),dates); D['energy_63']=snapshot(lr.pow(2).rolling(63,min_periods=63).sum(),dates)
    D['directional_energy_21']=snapshot(lr.rolling(21,min_periods=21).sum().pow(2)/lr.pow(2).rolling(21,min_periods=21).sum().replace(0,np.nan),dates); D['directional_energy_63']=snapshot(lr.rolling(63,min_periods=63).sum().pow(2)/lr.pow(2).rolling(63,min_periods=63).sum().replace(0,np.nan),dates)
    mean20=C.rolling(20,min_periods=20).mean(); std20=C.rolling(20,min_periods=20).std(); mean63=C.rolling(63,min_periods=63).mean(); std63=C.rolling(63,min_periods=63).std()
    D['boll_z20']=snapshot((C-mean20)/std20.replace(0,np.nan),dates); D['boll_z63']=snapshot((C-mean63)/std63.replace(0,np.nan),dates); D['rsi14_broad']=snapshot(rolling_rsi(C,14),dates)
    D['stoch63']=snapshot((C-L.rolling(63,min_periods=63).min())/(H.rolling(63,min_periods=63).max()-L.rolling(63,min_periods=63).min()).replace(0,np.nan),dates)
    D['gap_mean5']=snapshot(gap.rolling(5,min_periods=5).mean(),dates); D['gap_vol21']=snapshot(gap.rolling(21,min_periods=21).std(),dates); D['gap_min5']=snapshot(gap.rolling(5,min_periods=5).min(),dates); D['intraday_mean5']=snapshot(intraday.rolling(5,min_periods=5).mean(),dates)
    rng=(H-L)/C; D['range_z20']=snapshot((rng-rng.rolling(20,min_periods=20).mean())/rng.rolling(20,min_periods=20).std().replace(0,np.nan),dates)
    lv=np.log1p(V)
    for h in [20,63]: D[f'volume_z{h}']=snapshot((lv-lv.rolling(h,min_periods=h).mean())/lv.rolling(h,min_periods=h).std().replace(0,np.nan),dates)
    D['volume_ratio5_20']=snapshot(V.rolling(5,min_periods=5).mean()/V.rolling(20,min_periods=20).mean()-1,dates); D['volume_ratio20_63']=snapshot(V.rolling(20,min_periods=20).mean()/V.rolling(63,min_periods=63).mean()-1,dates)
    D['signed_volume21']=snapshot(signed.rolling(21,min_periods=21).sum()/V.rolling(21,min_periods=21).sum().replace(0,np.nan),dates); D['amihud21']=snapshot(amihud.rolling(21,min_periods=21).mean(),dates); D['amihud63']=snapshot(amihud.rolling(63,min_periods=63).mean(),dates); D['pv_corr21']=snapshot(ret.rolling(21,min_periods=21).corr(V.pct_change(fill_method=None)),dates)
    D['slope_21']=snapshot(rolling_slope(logc,21),dates); D['slope_63']=snapshot(rolling_slope(logc,63),dates); D['r2_63']=snapshot(rolling_r2(logc,63),dates); D['autocorr1_63']=snapshot(rolling_autocorr(ret,63),dates); D['spectral_entropy64']=snapshot(spectral_entropy_frame(lr,64),dates)
    D['max_loss21']=snapshot(ret.rolling(21,min_periods=21).min(),dates); D['max_gain21']=snapshot(ret.rolling(21,min_periods=21).max(),dates)
    for k in ['max_gain63','positive_frac63','breakout_pos126','breakout_pos252','sign_entropy63','ma_gap200','ma_gap50','ema_gap50','cvar10_63','beta_mkt63','beta_mkt126','corr_mkt63','corr_mkt126']:
        if k in compact_frames: D[k]=compact_frames[k]
    D['ret63_vol126']=D['ret_63']/D['vol_126'].replace(0,np.nan); D['kurt_63']=snapshot(lr.rolling(63,min_periods=63).kurt(),dates); D['vol_ratio_10_63']=D['vol_10']/D['vol_63'].replace(0,np.nan)
    D['acc_5_21']=D['acc_5_21_broad']; D['acc_21_63']=D['acc_21_63_broad']; D['mom21']=D['ret_21']; D['mom42']=D['ret_42']; D['mom63']=D['ret_63']; D['mom126']=D['ret_126']; D['mom252']=D['ret_252']; D['mom126_ex21']=D['mom_126_21']; D['efficiency126']=D['eff_126']; D['vol21']=D['vol_21']; D['vol63']=D['vol_63']; D['vol126']=D['vol_126']; D['downvol21']=D['downvol_21']; D['downvol63']=D['downvol_63']; D['downvol126']=D['downvol_126']; D['acc_mom_21_63']=D['acc_21_63_broad']; D['kurt63']=D['kurt_63']
    for k,v in list(D.items()):
        if not k.endswith('_rank'): D[k+'_rank']=cs_pct(v)
    missing=[f for f in base.TAIL_FEATURES if f not in D]
    if missing: raise RuntimeError(f'Exact July27 Tail missing {missing}')
    tail=pd.concat([D[f].stack(dropna=False).rename(f) for f in base.TAIL_FEATURES],axis=1).reset_index().rename(columns={'level_0':'signal_date','level_1':'ticker'})
    return tail,D
'''
    s=s[:start]+new+s[end:]
    s=s.replace("'compact_historical_params':'PUBLISHED_360x3_WITH_PLATINUM_FEATURE_PARITY'","'compact_historical_params':'PUBLISHED_360x3_PLATINUM_COMPACT_PLUS_EXACT_JUL27_TAIL'")
    p.write_text(s)
    print('Applied exact July-27 Broad/TailMix builder')

if __name__=='__main__': main()
