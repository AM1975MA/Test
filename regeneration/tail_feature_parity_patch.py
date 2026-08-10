from __future__ import annotations
import argparse
from pathlib import Path

EXACT = r'''def enhance_feature_dictionary(base, mats, dates, D):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]
    logc=np.log(C.where(C>0)); lr=logc.diff(); ret=C.pct_change(fill_method=None); prev=C.shift(1)
    mkt=ret.mean(axis=1,skipna=True)
    gap=O/prev.replace(0,np.nan)-1
    intraday=C/O.replace(0,np.nan)-1
    tr=pd.DataFrame(np.maximum.reduce([(H-L).to_numpy(),(H-prev).abs().to_numpy(),(L-prev).abs().to_numpy()]),index=C.index,columns=C.columns)
    lv=np.log1p(V)
    dollar=V*C
    amihud=ret.abs()/dollar.replace(0,np.nan)

    for h in [3,5,10,21,42,63,126,252]: D[f'ret_{h}']=base.snapshot(C.pct_change(h,fill_method=None),dates)
    D['mom_21_5']=base.snapshot(C.shift(5)/C.shift(21)-1,dates)
    D['mom_63_5']=base.snapshot(C.shift(5)/C.shift(63)-1,dates)
    D['mom_126_21']=base.snapshot(C.shift(21)/C.shift(126)-1,dates)
    D['mom_252_21']=base.snapshot(C.shift(21)/C.shift(252)-1,dates)
    D['acc_3_10']=D['ret_3']-.3*D['ret_10']
    D['acc_5_21']=D['ret_5']-(5/21)*D['ret_21']
    D['acc_5_21_broad']=D['acc_5_21']
    D['acc_21_63']=D['ret_21']-(1/3)*D['ret_63']
    D['acc_21_63_broad']=D['acc_21_63']
    D['acc_63_126']=D['ret_63']-.5*D['ret_126']
    D['jerk']=D['acc_3_10']-D['acc_5_21']
    for h in [20,50,100,200]: D[f'sma_ratio_{h}']=base.snapshot(C/C.rolling(h,min_periods=h).mean()-1,dates)
    for h in [21,63,126]:
        D[f'dist_high_{h}']=base.snapshot(C/C.rolling(h,min_periods=h).max()-1,dates)
        D[f'dd_{h}']=D[f'dist_high_{h}']
        D[f'eff_{h}']=base.snapshot(base.rolling_efficiency(logc,h),dates)
    for h in [10,21,63,126]: D[f'vol_{h}']=base.snapshot(lr.rolling(h,min_periods=h).std()*np.sqrt(252),dates)
    D['downvol_21']=base.snapshot(base.rolling_downvol(lr,21),dates)
    D['downvol_63']=base.snapshot(base.rolling_downvol(lr,63),dates)
    D['downvol126']=base.snapshot(base.rolling_downvol(lr,126),dates)
    gk=(.5*np.log(H/L.replace(0,np.nan))**2-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan))**2).clip(lower=0)
    D['gkvol21']=base.snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252),dates)
    D['atr_14']=base.snapshot(tr.rolling(14,min_periods=14).mean()/C.replace(0,np.nan),dates)
    D['atr_ratio']=D['atr_14']/D['vol_21'].replace(0,np.nan)
    D['energy_21']=base.snapshot(lr.pow(2).rolling(21,min_periods=21).sum(),dates)
    D['energy_63']=base.snapshot(lr.pow(2).rolling(63,min_periods=63).sum(),dates)
    for h in [21,63]:
        num=(np.sign(lr)*lr.pow(2)).rolling(h,min_periods=h).sum(); den=lr.pow(2).rolling(h,min_periods=h).sum().replace(0,np.nan)
        D[f'directional_energy_{h}']=base.snapshot(num/den,dates)
    D['slope_21']=base.snapshot(base.rolling_slope(logc,21),dates)
    D['slope_63']=base.snapshot(base.rolling_slope(logc,63),dates)
    D['r2_63']=base.snapshot(base.rolling_r2(logc,63),dates)
    D['positive_frac63']=base.snapshot((ret>0).rolling(63,min_periods=63).mean(),dates)
    D['max_loss21']=base.snapshot(ret.rolling(21,min_periods=21).min(),dates)
    D['max_loss63']=base.snapshot(ret.rolling(63,min_periods=63).min(),dates)
    D['max_gain21']=base.snapshot(ret.rolling(21,min_periods=21).max(),dates)
    D['max_gain63']=base.snapshot(ret.rolling(63,min_periods=63).max(),dates)
    D['cvar10_63']=base.snapshot(base.rolling_cvar10(ret,63),dates)
    D['sign_entropy63']=base.snapshot(base.rolling_sign_entropy(ret,63),dates)
    lo63=L.rolling(63,min_periods=63).min(); hi63=H.rolling(63,min_periods=63).max()
    D['stoch63']=base.snapshot((C-lo63)/(hi63-lo63).replace(0,np.nan),dates)
    D['breakout_pos126']=base.snapshot((C-C.rolling(126,min_periods=126).min())/(C.rolling(126,min_periods=126).max()-C.rolling(126,min_periods=126).min()).replace(0,np.nan),dates)
    D['breakout_pos252']=base.snapshot((C-C.rolling(252,min_periods=252).min())/(C.rolling(252,min_periods=252).max()-C.rolling(252,min_periods=252).min()).replace(0,np.nan),dates)
    D['ma_gap50']=D['sma_ratio_50']; D['ma_gap200']=D['sma_ratio_200']
    D['ema_gap50']=base.snapshot(C/C.ewm(span=50,adjust=False,min_periods=50).mean()-1,dates)
    D['amihud21']=base.snapshot(np.log1p(amihud.rolling(21,min_periods=21).mean()*1e9),dates)
    D['amihud63']=base.snapshot(np.log1p(amihud.rolling(63,min_periods=63).mean()*1e9),dates)
    D['volume_ratio5_20']=base.snapshot(V.rolling(5,min_periods=5).mean()/V.rolling(20,min_periods=20).mean()-1,dates)
    D['volume_ratio20_63']=base.snapshot(V.rolling(20,min_periods=20).mean()/V.rolling(63,min_periods=63).mean()-1,dates)
    D['gap_vol21']=base.snapshot(gap.rolling(21,min_periods=21).std(),dates)
    D['gap_mom21']=base.snapshot(gap.rolling(21,min_periods=21).sum(),dates)
    D['intraday_mom21']=base.snapshot(intraday.rolling(21,min_periods=21).sum(),dates)
    D['ret63_vol126']=D['ret_63']/D['vol_126'].replace(0,np.nan)
    D['kurt_63']=base.snapshot(lr.rolling(63,min_periods=63).kurt(),dates)
    for h in [63,126]:
        b,c=base.beta_corr(ret,mkt,h); D[f'beta_mkt{h}']=base.snapshot(b,dates); D[f'corr_mkt{h}']=base.snapshot(c,dates)
    D['spectral_entropy64']=base.snapshot(base.spectral_entropy_frame(lr,64),dates)
    for h in [21,63]:
        D[f'signed_volume{h}']=base.snapshot((np.sign(ret)*V).rolling(h,min_periods=h).sum()/V.rolling(h,min_periods=h).sum().replace(0,np.nan),dates)
        D[f'pv_corr{h}']=base.snapshot(ret.rolling(h,min_periods=h).corr(lv.diff()),dates)
    D['volume_z20']=base.snapshot((lv-lv.rolling(20,min_periods=20).mean())/lv.rolling(20,min_periods=20).std().replace(0,np.nan),dates)
    D['volume_z63']=base.snapshot((lv-lv.rolling(63,min_periods=63).mean())/lv.rolling(63,min_periods=63).std().replace(0,np.nan),dates)
    ld=np.log1p(dollar)
    D['dollar_volume_z20']=base.snapshot((ld-ld.rolling(20,min_periods=20).mean())/ld.rolling(20,min_periods=20).std().replace(0,np.nan),dates)

    # Production aliases used by TailMix / Opportunity.
    D['mom21']=D['ret_21']; D['mom42']=D['ret_42']; D['mom63']=D['ret_63']; D['mom126']=D['ret_126']; D['mom252']=D['ret_252']
    D['mom126_ex21']=D['mom_126_21']; D['efficiency126']=D['eff_126']
    D['trend_slope21']=D['slope_21']; D['trend_slope63']=D['slope_63']
    D['acc_mom_5_21']=D['acc_5_21']; D['acc_mom_21_63']=D['acc_21_63']
    D['downvol21']=D['downvol_21']; D['downvol63']=D['downvol_63']
    D['vol21']=D['vol_21']; D['vol63']=D['vol_63']; D['vol126']=D['vol_126']
    D['drawdown63']=D['dist_high_63']
    for k,v in list(D.items()):
        if not k.endswith('_rank'): D[k+'_rank']=base.cs_pct(v)
    aliases={
      'downvol21_rank':'downvol_21_rank','downvol63_rank':'downvol_63_rank','downvol126_rank':'downvol126_rank',
      'vol21_rank':'vol_21_rank','vol63_rank':'vol_63_rank','vol126_rank':'vol_126_rank',
      'mom21_rank':'ret_21_rank','mom42_rank':'ret_42_rank','mom63_rank':'ret_63_rank','mom126_rank':'ret_126_rank',
      'mom126_ex21_rank':'mom_126_21_rank','efficiency126_rank':'eff_126_rank','acc_mom_21_63_rank':'acc_21_63_rank','acc_21_63_broad_rank':'acc_21_63_rank','kurt63_rank':'kurt_63_rank'}
    for dst,src in aliases.items(): D[dst]=D[src]
    return D
'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--v6',type=Path,required=True); a=ap.parse_args()
    s=a.v6.read_text(); start=s.index('def enhance_feature_dictionary('); end=s.index('\ndef rebuild_tail_long(',start)
    s=s[:start]+EXACT+s[end+1:]; a.v6.write_text(s); print('patched exact Tail/broad feature builder')
if __name__=='__main__': main()
