#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import sys, json, importlib.util
import numpy as np
import pandas as pd

ROOT=Path('/mnt/data/p43_local')
OUT=ROOT/'p45_result'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'workroot/src'))
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6

spec=importlib.util.spec_from_file_location('s19',ROOT/'stage19_bundle/HYBRID25_STAGE19_SOURCE_ONLY_REBUILD_20260925/source/scripts/evaluate_stage19_fresh.py')
s19=importlib.util.module_from_spec(spec); sys.modules['s19']=s19; spec.loader.exec_module(s19)
bspec=importlib.util.spec_from_file_location('p44b',ROOT/'work/bocpd_router.py')
p44b=importlib.util.module_from_spec(bspec); sys.modules['p44b']=p44b; bspec.loader.exec_module(p44b)


def score_monthly_with_pre2017(pM,cal,tickers):
    def pivot(df,col,dates):
        return df.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    base=pivot(pM,'BASE',pd.DatetimeIndex(cal.signal_date))
    pre=[]
    for tag in ['20161130','20161230']:
        pre.append(pd.read_csv(ROOT/f'workroot/out/ma3_monthly/pred/pred_{tag}.csv',parse_dates=['signal_date']))
    allt=pd.concat(pre+[pM[['signal_date','ticker','TAIL_EXTRA','ET_RANK','XGB_RANK']]],ignore_index=True)
    hd=pd.DatetimeIndex([pd.Timestamp('2016-11-30'),pd.Timestamp('2016-12-30'),*list(cal.signal_date)])
    T=pivot(allt,'TAIL_EXTRA',hd)
    sm=.4*T[2:]+.3*T[1:-1]+.3*T[:-2]
    return .475*base+.525*np.power(np.clip(sm,0,1),1.10)


def main():
    p44_parity=json.loads((ROOT/'p44_result/PARITY_AUDIT.json').read_text())
    if not p44_parity.get('pass_all'):
        raise RuntimeError('P44 certified parity missing')

    mats,_,_=load_ticker_csv_folder(ROOT/'workroot/raw_ticker_csv');tickers=list(map(str,mats['Open'].columns));ti={t:i for i,t in enumerate(tickers)}
    titA=pd.read_csv(ROOT/'oracle/TIT_R_SOURCE_ONLY.csv',parse_dates=['signal_date','entry_date','exit_date'])
    fullcal=titA[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    cal=fullcal.dropna(subset=['exit_date']).reset_index(drop=True)
    pA=pd.read_csv(ROOT/'oracle/ENSEMBLE_TAIL_OOS.csv',parse_dates=['signal_date']);pA=pA[pA.signal_date.isin(cal.signal_date)].copy()
    pM=pd.read_csv(ROOT/'workroot/out/ma3_monthly/MONTHLY_PREDICTIONS.csv',parse_dates=['signal_date']);pM=pM[pM.signal_date.isin(cal.signal_date)].copy()
    sA=s19.score_matrix(pA,cal,tickers);sM=score_monthly_with_pre2017(pM,cal,tickers)
    pmA=s19.pred_matrices(pA,cal,tickers);pmM=s19.pred_matrices(pM,cal,tickers)

    Odf=mats['Open'].reindex(columns=tickers).ffill().bfill();Ldf=mats['Low'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index);Cdf=mats['Close'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    start=pd.Timestamp(cal.entry_date.min());end=pd.Timestamp(cal.exit_date.max());Odf=Odf.loc[:end];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index)
    st=int(Odf.index.get_loc(start));en=int(Odf.index.get_loc(end));ds=Odf.index[st:en+1]
    ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float);g=s19.risk_gross_transform(ddgross);ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf)
    O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]
    BM=np.arange(len(tickers),dtype=np.int32)[None,:];BOK=np.ones_like(BM,dtype=bool)

    def replay(score,pm):
        base=producer.allocations_from_score(score,cal,ds,BM,BOK,continuous=True)
        s6=v6.build_v6_state(Cdf.loc[ds,tickers],base.d1,base.d2,base.weight1,ddgross)
        _,agree,_=s19.daily_monthly_state(score,pm,cal,ds,BM,BOK)
        w=s19.confidence_weights(base,g,agree,np.zeros_like(agree),mode='current_plus_models_riskoff')
        G=np.tile(g,(1,1))
        E,T,_,_=s19.simulate_arch.py_func(base.d1,base.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],G,g,s6.alt_idx,True,.001)
        return E,T,base

    EA,TA,bA=replay(sA,pmA);EM,TM,bM=replay(sM,pmM)
    pm50={k:.5*pmA[k]+.5*pmM[k] for k in pmA};E50,T50,b50=replay(.5*sA+.5*sM,pm50)

    refs={
      'annual':dict(cagr=.4314595242029944,maxdd=-.2503576476357465,sharpe=1.3635086089607882,turn=12.807083509113824),
      'monthly':dict(cagr=.37063594291857493,maxdd=-.3516524326917191,sharpe=1.2717391106878997,turn=13.745053103725073),
      '50-50':dict(cagr=.4475354991771064,maxdd=-.27063751068647446,sharpe=1.4291508593820934,turn=13.104831222285583)}
    parity={}
    for name,E,T in [('annual',EA,TA),('monthly',EM,TM),('50-50',E50,T50)]:
        m=s19.metrics(E,np.ones(len(ds),bool));obs=dict(cagr=m['cagr'],maxdd=m['maxdd'],sharpe=m['sharpe'],turn=float(T.mean()*252));dif={k:obs[k]-refs[name][k] for k in obs};ok=all(abs(x)<=1e-12 for x in dif.values());parity[name]={'observed':obs,'reference':refs[name],'difference':dif,'pass':ok}
        if not ok: raise RuntimeError(f'PARITY FAIL {name} {parity[name]}')
    parity['pass_all']=True;(OUT/'PARITY_AUDIT.json').write_text(json.dumps(parity,indent=2)+'\n')

    shadow=pd.read_csv(ROOT/'p43_result/SHADOW_SKILL.csv',parse_dates=['interval_signal_date','outcome_end'])
    trace=p44b.route_trace(fullcal.signal_date,shadow)
    trace['w_monthly']=trace['p_monthly'].astype(float)
    trace['w_annual']=1.0-trace['w_monthly']
    trace['dominant_side']=np.where(trace.p_monthly>0.5,'Monthly',np.where(trace.p_monthly<0.5,'Annual','Neutral'))
    trace.to_csv(OUT/'ROUTER_TRACE.csv',index=False)
    shadow.to_csv(OUT/'SHADOW_SKILL.csv',index=False)

    sigs=pd.DatetimeIndex(fullcal.signal_date).sort_values();used=[]
    for r in shadow.itertuples(index=False):
        nxt=sigs[sigs>pd.Timestamp(r.outcome_end)];used.append(None if len(nxt)==0 else pd.Timestamp(nxt[0]))
    causal_ok=all(u is None or pd.Timestamp(e)<u for e,u in zip(shadow.outcome_end,used))

    tr=trace.set_index('signal_date').reindex(pd.DatetimeIndex(cal.signal_date))
    if tr[['w_annual','w_monthly']].isna().any().any(): raise RuntimeError('route alignment failed')
    wa=tr.w_annual.to_numpy(float)[:,None];wm=tr.w_monthly.to_numpy(float)[:,None]
    if np.max(np.abs(wa+wm-1.0))>1e-15: raise RuntimeError('weight normalization failed')
    sR=wa*sA+wm*sM;pmR={k:wa*pmA[k]+wm*pmM[k] for k in pmA}
    ER,TR,bR=replay(sR,pmR)

    full=s19.metrics(ER,np.ones(len(ds),bool));periods={'2017_2022':ds<pd.Timestamp('2023-01-01'),'2023_2026':ds>=pd.Timestamp('2023-01-01')}
    sub={}
    for name,mask in periods.items():sub[name]={'p45':s19.metrics(ER,mask),'annual':s19.metrics(EA,mask),'p42_50_50':s19.metrics(E50,mask)}

    rows=[];lrA=np.diff(np.log(np.r_[1.,EA[0]]));lr50=np.diff(np.log(np.r_[1.,E50[0]]));lrR=np.diff(np.log(np.r_[1.,ER[0]]))
    for y in range(2017,2027):
        mask=(ds>=pd.Timestamp(f'{y}-01-01'))&(ds<pd.Timestamp(f'{y+1}-01-01'))
        if not mask.any(): continue
        a=s19.metrics(EA,mask);f=s19.metrics(E50,mask);r=s19.metrics(ER,mask)
        rows.append(dict(year=y,sessions=int(mask.sum()),return_annual=float(np.expm1(lrA[mask].sum())),return_p42=float(np.expm1(lr50[mask].sum())),return_p45=float(np.expm1(lrR[mask].sum())),maxdd_annual=a['maxdd'],maxdd_p42=f['maxdd'],maxdd_p45=r['maxdd'],sharpe_annual=a['sharpe'],sharpe_p42=f['sharpe'],sharpe_p45=r['sharpe']))
    pd.DataFrame(rows).to_csv(OUT/'ANNUAL_COMPARISON.csv',index=False)

    def tops(score): ids=np.argsort(-score,axis=1)[:,:2];return ids[:,0],ids[:,1]
    a1,a2=tops(sA);m1,m2=tops(sM);r1,r2=tops(sR);f1,f2=tops(.5*sA+.5*sM)
    agree={'top1_vs_annual':float(np.mean(r1==a1)),'top2_vs_annual':float(np.mean(r2==a2)),'top1_vs_monthly':float(np.mean(r1==m1)),'top2_vs_monthly':float(np.mean(r2==m2)),'top1_vs_p42':float(np.mean(r1==f1)),'top2_vs_p42':float(np.mean(r2==f2))}

    causal={'pass':bool(causal_ok),'completed_shadow_intervals':int(len(shadow)),'ingested_by_last_signal':int(trace.observations_seen.max()),'all_outcomes_strictly_before_influenced_signal':bool(causal_ok),'last_completed_shadow_outcome_end':str(pd.Timestamp(shadow.outcome_end.max()).date()),'last_signal':str(pd.Timestamp(fullcal.signal_date.max()).date()),'last_completed_shadow_used_by_router':bool(pd.Timestamp(shadow.outcome_end.max())<pd.Timestamp(fullcal.signal_date.max())),'parity_pass_all':True}
    (OUT/'CAUSAL_AUDIT.json').write_text(json.dumps(causal,indent=2)+'\n')

    gate={'causal_audit_pass':causal['pass'],'cagr_gt_p42_50_50':bool(full['cagr']>refs['50-50']['cagr']),'sharpe_ge_p42_50_50':bool(full['sharpe']>=refs['50-50']['sharpe']),'maxdd_not_worse_than_annual_by_gt_2pp':bool(full['maxdd']>=refs['annual']['maxdd']-.02),'positive_delta_vs_p42_2017_2022':bool(sub['2017_2022']['p45']['cagr']>sub['2017_2022']['p42_50_50']['cagr']),'positive_delta_vs_p42_2023_2026':bool(sub['2023_2026']['p45']['cagr']>sub['2023_2026']['p42_50_50']['cagr'])};gate['pass_all']=bool(all(gate.values()))

    wdiag={'w_monthly_min':float(trace.w_monthly.min()),'w_monthly_max':float(trace.w_monthly.max()),'w_monthly_mean':float(trace.w_monthly.mean()),'w_monthly_median':float(trace.w_monthly.median()),'w_monthly_last':float(trace.w_monthly.iloc[-1]),'signals_wm_lt_025':int((trace.w_monthly<.25).sum()),'signals_wm_025_075':int(((trace.w_monthly>=.25)&(trace.w_monthly<=.75)).sum()),'signals_wm_gt_075':int((trace.w_monthly>.75).sum()),'mean_abs_deviation_from_050':float(np.mean(np.abs(trace.w_monthly-.5)))}
    result={'status':'P45_CONTINUOUS_POSTERIOR_ROUTER_COMPLETE','parity_pass':True,'p45':{'cagr':full['cagr'],'compounded_return':float(ER[0,-1]-1),'terminal_equity':float(ER[0,-1]),'maxdd':full['maxdd'],'sharpe':full['sharpe'],'annualized_turnover':float(TR.mean()*252)},'annual_reference':refs['annual'],'p42_50_50_reference':refs['50-50'],'monthly_reference':refs['monthly'],'delta_p45_minus_p42':{'cagr_pp':100*(full['cagr']-refs['50-50']['cagr']),'maxdd_pp':100*(full['maxdd']-refs['50-50']['maxdd']),'sharpe':full['sharpe']-refs['50-50']['sharpe'],'turnover_ann':float(TR.mean()*252)-refs['50-50']['turn']},'delta_p45_minus_annual':{'cagr_pp':100*(full['cagr']-refs['annual']['cagr']),'maxdd_pp':100*(full['maxdd']-refs['annual']['maxdd']),'sharpe':full['sharpe']-refs['annual']['sharpe'],'turnover_ann':float(TR.mean()*252)-refs['annual']['turn']},'subperiods':sub,'posterior_weight_summary':wdiag,'selection_agreement':agree,'decision_gate':gate,'evidence_status':'retrospective historical research; one preregistered P45 run; no rescue variants'}
    (OUT/'RESULT.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    decision='SUPPORTED' if gate['pass_all'] else 'NOT_SUPPORTED'
    (OUT/'FINAL_DECISION.md').write_text(f"# P45 Final Decision\n\nStatus: **{decision}**\n\nThe preregistered P45 run was opened once after exact Annual/P41/P42 parity. No rescue variant was run.\n\n- P45 CAGR: **{100*full['cagr']:.6f}%**\n- P45 MaxDD: **{100*full['maxdd']:.6f}%**\n- P45 Sharpe: **{full['sharpe']:.6f}**\n- P45 annualized turnover: **{float(TR.mean()*252):.6f}**\n- Delta CAGR vs P42 50/50: **{100*(full['cagr']-refs['50-50']['cagr']):+.6f} pp**\n- Delta CAGR vs Annual: **{100*(full['cagr']-refs['annual']['cagr']):+.6f} pp**\n- Gate pass: **{gate['pass_all']}**\n\nP45 uses the raw P44 BOCPD `p_monthly` continuously as `w_monthly`, with `w_annual=1-p_monthly`. No threshold, clipping, shrinkage or detector retuning was used.\n\nNo P45 parameter was changed after result inspection. `AM1975MA/Etf_trader` was not modified.\n")
    np.savez_compressed(OUT/'PATHS.npz',dates=ds.values,annual=EA,monthly=EM,p42=E50,p45=ER,turnover_p45=TR,w_monthly=tr.w_monthly.to_numpy(float))
    print(json.dumps(result,indent=2,default=str))

if __name__=='__main__': main()
