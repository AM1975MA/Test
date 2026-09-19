#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd
THIS=Path(__file__).resolve(); sys.path.insert(0,str(THIS.parent)); sys.path.insert(0,str(THIS.parents[2]/'cvx_macro_prior'/'src'))
from armed_engine_v2 import simulate_armed_v2
from run_cvx_daily_exact import load,prices,select,daily,row
CONFIRM_LOSS=.03

def unpack(path,cal):
    x=json.loads(Path(path).read_text()); raw=np.frombuffer(base64.b64decode(x['bitset_b64']),dtype=np.uint8); z=np.unpackbits(raw,bitorder='little')[:x['shape'][0]*x['shape'][1]].reshape(x['shape']).astype(np.uint8)
    if x.get('sha256_unpacked') and hashlib.sha256(z.tobytes()).hexdigest()!=x['sha256_unpacked']: raise RuntimeError('trigger hash mismatch')
    if list(pd.to_datetime(x['dates']))!=list(pd.DatetimeIndex(cal.signal_date)): raise RuntimeError('calendar mismatch')
    return z

def pm(E,mask):
    X=E[:,mask]; X=X/X[:,[0]]; r=X[:,1:]/X[:,:-1]-1; yrs=max(r.shape[1]/252.,1/252.); c=X[:,-1]**(1/yrs)-1; d=(X/np.maximum.accumulate(X,axis=1)-1).min(1); sd=r.std(1,ddof=1); s=np.where(sd>0,r.mean(1)/sd*np.sqrt(252),np.nan); return c,d,s

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-dir',type=Path,required=True); ap.add_argument('--output-dir',type=Path,required=True); ap.add_argument('--final-date',default='2026-07-01'); a=ap.parse_args()
    root=THIS.parents[3]; rc=root/'research'/'cvx_macro_prior'; rr=root/'research'/'risk_sentinel'; out=a.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True); final=pd.Timestamp(a.final_date)
    from titanium import reconstruction as rec
    off,p,mem,cal,gate,reg,fr=load(root,rc,final); mats=rec.load_mats(a.data_dir.resolve()); all_dates=pd.DatetimeIndex(fr['dates']); mm=np.asarray(all_dates<=final); dates=all_dates[mm]; frozen=fr['BALANCED'][:,mm]
    ticks,pti,O,L,C,PC,gap,ud1,uneg,UH,SA=prices(mats,dates); base,v36,v4,_=select(p,mem,cal,gate,reg,pti); old=unpack(rr/'inputs'/'FROZEN_RISK_OVERLAY_TRIGGERS.json',cal)
    variants=[base,v4,v4,v4,v4]; d1,d2,wg=daily(variants,cal,dates); D=len(dates); B=500; armed=np.zeros((5,B,D),np.uint8); month_start=np.zeros(D,np.uint8)
    for k,en in enumerate(pd.to_datetime(cal.entry_date)):
        j=dates.get_loc(pd.Timestamp(en)); month_start[j]=1
        for n in [2,3,4]: armed[n,:,j]=old[k]
    target=np.array([.75,.75,.50,.25,0.0],float); E,F=simulate_armed_v2(d1,d2,wg,month_start,armed,target,O,L,C,PC,gap,ud1,uneg,UH,SA,pti['BIL'],pti['SHV'],confirm_loss=CONFIRM_LOSS)
    names=['Titanium_V2_rebuilt','CVX70_TOP3_STABLE_4OF4','ARMED_EQ_50_50','ARMED_FLIP_25_75','ARMED_SWAP_0_100']; score=pd.DataFrame([row(names[i],E[i]) for i in range(5)]+[row('Titanium_V2_frozen',frozen)])
    br=score.iloc[0]; cv=score.iloc[1]; fr0=score.iloc[-1]; parity={'cagr_gap_pp':100*(br.cagr_mean-fr0.cagr_mean),'maxdd_gap_pp':100*(br.maxdd_mean-fr0.maxdd_mean),'sharpe_gap':br.sharpe_mean-fr0.sharpe_mean}; ok=abs(parity['cagr_gap_pp'])<=.10 and abs(parity['maxdd_gap_pp'])<=.15 and abs(parity['sharpe_gap'])<=.005
    ref=pd.read_csv(root/'research'/'cvx_macro_prior'/'daily_exact_snapshot'/'DAILY_EXACT_SCORECARD.csv'); rr4=ref[ref.strategy.eq('CVX70_TOP3_STABLE_4OF4')].iloc[0]; cvgap={'cagr_gap_pp':100*(cv.cagr_mean-rr4.cagr_mean),'maxdd_gap_pp':100*(cv.maxdd_mean-rr4.maxdd_mean),'sharpe_gap':cv.sharpe_mean-rr4.sharpe_mean}; ok=ok and abs(cvgap['cagr_gap_pp'])<=.02 and abs(cvgap['maxdd_gap_pp'])<=.03 and abs(cvgap['sharpe_gap'])<=.001
    for i in [2,3,4]:
        hit=score.strategy.eq(names[i]); r=score.iloc[i]; score.loc[hit,'delta_cagr_pp_vs_4of4']=100*(r.cagr_mean-cv.cagr_mean); score.loc[hit,'delta_maxdd_pp_vs_4of4']=100*(r.maxdd_mean-cv.maxdd_mean); score.loc[hit,'delta_sharpe_vs_4of4']=r.sharpe_mean-cv.sharpe_mean; score.loc[hit,'fires']=int(F[i].sum())
    score['accepted_for_inference']=bool(ok); score.to_csv(out/'ARMED_ACTION_FRONTIER_SCORECARD.csv',index=False)
    periods={'D1_2017_2019':('2017-02-01','2019-12-31'),'D2_2020_2022':('2020-01-01','2022-12-31'),'HOLD_2023_2026':('2023-01-01','2026-07-01'),'Y2025':('2025-01-01','2025-12-31'),'FULL':(str(dates.min().date()),'2026-07-01')}; rows=[]
    for pn,(lo,hi) in periods.items():
        mask=np.asarray((dates>=pd.Timestamp(lo))&(dates<=pd.Timestamp(hi))); bc,bd,bs=pm(E[1],mask)
        for i in [2,3,4]:
            c,d,s=pm(E[i],mask); rows.append({'period':pn,'strategy':names[i],'delta_cagr_pp_vs_4of4':100*(c.mean()-bc.mean()),'delta_maxdd_pp_vs_4of4':100*(d.mean()-bd.mean()),'delta_sharpe_vs_4of4':s.mean()-bs.mean()})
    pd.DataFrame(rows).to_csv(out/'ARMED_ACTION_FRONTIER_PERIODS.csv',index=False)
    np.savez_compressed(out/'ARMED_ACTION_FRONTIER_PATHS.npz',dates=dates.values,CVX4=E[1],EQ=E[2],FLIP=E[3],SWAP=E[4],V2=E[0],FROZEN_V2=frozen)
    (out/'ARMED_ACTION_FRONTIER_REPORT.json').write_text(json.dumps({'status':'ACCEPTED' if ok else 'REJECTED_PARITY','confirm_loss':CONFIRM_LOSS,'armed_decisions':int(old.sum()),'fires':{names[i]:int(F[i].sum()) for i in [2,3,4]},'v2_parity':parity,'cvx4_parity':cvgap},indent=2)+'\n'); print(score.to_string(index=False)); print(pd.DataFrame(rows).to_string(index=False)); raise SystemExit(0 if ok else 2)
if __name__=='__main__': main()
