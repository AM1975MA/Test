#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,subprocess,sys
from pathlib import Path
import numpy as np,pandas as pd
from frozen_engine import simulate

TH=.12; LOWW=.75; BLEND=.70; EPS=1e-12

def metrics(E):
    r=np.zeros_like(E,float); r[:,1:]=E[:,1:]/E[:,:-1]-1
    c=np.cumprod(1+r,axis=1); cagr=c[:,-1]**(252./r.shape[1])-1
    dd=c/np.maximum.accumulate(c,axis=1)-1; md=dd.min(1); sd=r.std(1,ddof=1)
    sh=np.sqrt(252.)*r.mean(1)/np.where(sd>0,sd,np.nan)
    return pd.DataFrame({'cagr':cagr,'maxdd':md,'sharpe':sh,'calmar':cagr/np.maximum(-md,1e-12)})

def row(name,E):
    m=metrics(E); return {'strategy':name,'cagr_mean':m.cagr.mean(),'cagr_median':m.cagr.median(),'maxdd_mean':m.maxdd.mean(),'sharpe_mean':m.sharpe.mean(),'calmar_mean':m.calmar.mean(),'cagr_p10':m.cagr.quantile(.1),'cagr_p90':m.cagr.quantile(.9)}

def canonical():
    from titanium.parity import CATEGORY_TICKERS
    x=sorted({t for v in CATEGORY_TICKERS.values() for t in v}); assert len(x)==150; return x

def load(root,research,final):
    off=root/'reference'/'official'; subprocess.run([sys.executable,str(root/'scripts'/'materialize_frozen_artifacts.py'),'--official-root',str(off)],cwd=root,check=True)
    p=pd.read_pickle(off/'authentic'/'ORTHOGONAL_SCORE_PANEL.pkl'); mem=pd.read_csv(off/'authentic'/'SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    for c in ['signal_date','entry_date','exit_date']: p[c]=pd.to_datetime(p[c])
    p.ticker=p.ticker.astype(str).str.upper(); mem.ticker=mem.ticker.astype(str).str.upper(); p=p[p.exit_date<=final].copy()
    cal=p[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    cat=pd.read_csv(research/'inputs'/'CATEGORY_PRIOR_2017_2026.csv',parse_dates=['signal_date']); gate=pd.read_csv(research/'inputs'/'FROZEN_GATE_CALENDAR.csv',parse_dates=['signal_date']).set_index('signal_date').reindex(pd.DatetimeIndex(cal.signal_date))
    p=p.merge(cat[['signal_date','category','cat_rank']],left_on=['signal_date','macro_category'],right_on=['signal_date','category'],how='left',validate='many_to_one').drop(columns='category'); p.cat_rank=p.cat_rank.fillna(.5)
    reg=np.load(off/'frozen_paths'/'REG_W24_F005_S008_PATHS.npz'); fr=np.load(off/'frozen_paths'/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz')
    return off,p,mem,cal,gate,reg,fr

def prices(mats,dates):
    ticks=list(mats['Open'].columns); Odf=mats['Open'].reindex(dates,columns=ticks).ffill().bfill(); Ldf=mats['Low'].reindex(dates,columns=ticks).ffill().bfill(); Cdf=mats['Close'].reindex(dates,columns=ticks).ffill().bfill()
    ti={t:i for i,t in enumerate(ticks)}; required=set(ticks)-{'PIN'}
    for t in required:
        if Odf[t].isna().any() or Ldf[t].isna().any() or Cdf[t].isna().any(): raise RuntimeError(f'unfillable {t}')
    O=Odf.to_numpy(float); L=Ldf.to_numpy(float); C=Cdf.to_numpy(float); gap=np.zeros_like(O); gap[1:]=O[1:]/C[:-1]-1
    ud1=np.mean(gap<-.01,1); uneg=np.mean(gap<0,1); hist=Cdf[ticks]; m3=hist/hist.shift(3)-1; m5=hist/hist.shift(5)-1; s10=hist.rolling(10).mean(); s20=hist.rolling(20).mean()
    UH=((((hist<s10)&(m3<0))|((hist<s20)&(m5<-.015))).shift(1).fillna(False)).to_numpy(bool); SA=(((m5<-.04)|((hist<s20)&(m3<-.025))).shift(1).fillna(False)).to_numpy(bool)
    PC=np.empty_like(C); PC[0]=O[0]; PC[1:]=C[:-1]; return ticks,ti,O,L,C,PC,gap,ud1,uneg,UH,SA

def select(p,mem,cal,gate,reg,pti):
    dates=pd.DatetimeIndex(cal.signal_date); B=500; K=len(dates); top1=np.asarray(canonical(),object)[reg['BASE_SELECTED'].astype(int)].T
    st=sorted(p.ticker.unique()); si={t:i for i,t in enumerate(st)}; T=p.pivot(index='signal_date',columns='ticker',values='TIT_R').reindex(index=dates,columns=st).to_numpy(float); C=p.pivot(index='signal_date',columns='ticker',values='cat_rank').reindex(index=dates,columns=st).to_numpy(float)
    mn=[mem.loc[mem.basket.eq(b),'ticker'].tolist() for b in range(B)]
    def blank(): return np.full((K,B),-1,np.int16),np.full((K,B),-1,np.int16),np.ones((K,B),float)
    base=blank(); v36=blank(); v4=blank(); changes=[]
    for k,dt in enumerate(dates):
      for b in range(B):
        t1=str(top1[k,b]); names=mn[b]; idx=np.array([si[t] for t in names]); sc=T[k,idx]; order=np.argsort(np.where(np.isfinite(sc),sc,-np.inf))[::-1]; alts=[names[i] for i in order if names[i]!=t1]; t2=alts[0]
        w=1. if T[k,si[t1]]-T[k,si[t2]]>=TH else LOWW; base[0][k,b]=pti[t1]; base[1][k,b]=pti[t2]; base[2][k,b]=w; cand=[t1,alts[0],alts[1]]
        for label,on,v in [('CVX70_TOP3_W36Q60',bool(gate.iloc[k].gate_w36_q60),v36),('CVX70_TOP3_STABLE_4OF4',bool(gate.iloc[k].gate_stable_4of4),v4)]:
          a,c,wa=t1,t2,w
          if on:
            z=np.array([(1-BLEND)*T[k,si[t]]+BLEND*C[k,si[t]] for t in cand]); o=np.argsort(np.nan_to_num(z,nan=-1e99))[::-1]; a,c=cand[o[0]],cand[o[1]]; wa=1. if z[o[0]]-z[o[1]]>=TH else LOWW
          v[0][k,b]=pti[a]; v[1][k,b]=pti[c]; v[2][k,b]=wa
          if (a,c,wa)!=(t1,t2,w): changes.append({'strategy':label,'signal_date':dt,'basket':b,'v2_top1':t1,'v2_top2':t2,'v2_w1':w,'cvx_top1':a,'cvx_top2':c,'cvx_w1':wa})
    return base,v36,v4,pd.DataFrame(changes)

def daily(vars,cal,dates):
    N=len(vars); K,B=vars[0][0].shape; D=len(dates); d1=np.full((N,B,D),-1,np.int16); d2=d1.copy(); wg=np.ones((N,B,D))
    for k,(en,ex) in enumerate(zip(cal.entry_date,cal.exit_date)):
      a=dates.get_loc(pd.Timestamp(en)); e=dates.get_loc(pd.Timestamp(ex))
      for n,v in enumerate(vars): d1[n,:,a:e]=v[0][k,:,None]; d2[n,:,a:e]=v[1][k,:,None]; wg[n,:,a:e]=v[2][k,:,None]
    return d1,d2,wg

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--final-date',default='2026-07-01'); ap.add_argument('--cagr-tol-pp',type=float,default=.10); ap.add_argument('--maxdd-tol-pp',type=float,default=.15); ap.add_argument('--sharpe-tol',type=float,default=.005); a=ap.parse_args()
    root=Path(__file__).resolve().parents[3]; research=Path(__file__).resolve().parents[1]; out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True); final=pd.Timestamp(a.final_date)
    from titanium import reconstruction as rec
    off,p,mem,cal,gate,reg,fr=load(root,research,final); mats=rec.load_mats(a.data_dir.resolve()); all_dates=pd.DatetimeIndex(fr['dates']); mask=np.asarray(all_dates<=final); dates=all_dates[mask]; frozen=fr['BALANCED'][:,mask]
    ticks,pti,O,L,C,PC,gap,ud1,uneg,UH,SA=prices(mats,dates); base,v36,v4,changes=select(p,mem,cal,gate,reg,pti); d1,d2,wg=daily([base,v36,v4],cal,dates); E=simulate(d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,pti['BIL'],pti['SHV'])
    score=pd.DataFrame([row('Titanium_V2_rebuilt',E[0]),row('CVX70_TOP3_W36Q60',E[1]),row('CVX70_TOP3_STABLE_4OF4',E[2]),row('Titanium_V2_frozen',frozen)])
    br=score[score.strategy.eq('Titanium_V2_rebuilt')].iloc[0]; fr0=score[score.strategy.eq('Titanium_V2_frozen')].iloc[0]; diff=np.abs(E[0]-frozen)
    parity={'cagr_gap_pp':100*(br.cagr_mean-fr0.cagr_mean),'maxdd_gap_pp':100*(br.maxdd_mean-fr0.maxdd_mean),'sharpe_gap':br.sharpe_mean-fr0.sharpe_mean,'max_abs_equity_gap':float(np.nanmax(diff)),'mean_abs_equity_gap':float(np.nanmean(diff)),'price_ticker_count':len(ticks),'missing_canonical_price_tickers':sorted(set(canonical())-set(ticks))}
    ok=abs(parity['cagr_gap_pp'])<=a.cagr_tol_pp and abs(parity['maxdd_gap_pp'])<=a.maxdd_tol_pp and abs(parity['sharpe_gap'])<=a.sharpe_tol; parity['status']='ACCEPTED_ECONOMIC_PARITY' if ok else 'REJECTED_DATA_PARITY'; parity['strict_byte_equity_parity']=bool(parity['max_abs_equity_gap']<=1e-12)
    for name in ['CVX70_TOP3_W36Q60','CVX70_TOP3_STABLE_4OF4']:
      r=score[score.strategy.eq(name)].iloc[0]; hit=score.strategy.eq(name); score.loc[hit,'delta_cagr_pp_vs_rebuilt_v2']=100*(r.cagr_mean-br.cagr_mean); score.loc[hit,'delta_maxdd_pp_vs_rebuilt_v2']=100*(r.maxdd_mean-br.maxdd_mean); score.loc[hit,'delta_sharpe_vs_rebuilt_v2']=r.sharpe_mean-br.sharpe_mean
    score['accepted_for_inference']=ok; score.to_csv(out/'DAILY_EXACT_SCORECARD.csv',index=False); changes.to_csv(out/'SELECTION_CHANGES.csv',index=False); (out/'PARITY_REPORT.json').write_text(json.dumps(parity,indent=2,default=float)+'\n')
    pd.DataFrame({'date':dates,'mean_abs_gap':diff.mean(0),'max_abs_gap':diff.max(0)}).to_csv(out/'DAILY_PARITY_GAP.csv',index=False); np.savez_compressed(out/'DAILY_EXACT_PATHS.npz',dates=dates.values,V2=E[0],CVX_W36=E[1],CVX_4OF4=E[2],FROZEN_V2=frozen)
    rep={'status':parity['status'],'simulator':'original_frozen_v2_concentration_frontier','gate_w36_active_months':int(gate.gate_w36_q60.sum()),'gate_4of4_active_months':int(gate.gate_stable_4of4.sum()),'selection_changes':changes.groupby('strategy').size().to_dict(),'parity':parity}; (out/'RUN_REPORT.json').write_text(json.dumps(rep,indent=2,default=str)+'\n'); print(score.to_string(index=False)); print(json.dumps(rep,indent=2,default=str)); raise SystemExit(0 if ok else 2)
if __name__=='__main__': main()
