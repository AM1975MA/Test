#!/usr/bin/env python3
"""OLC74C: original native risk engine, on-policy 3 same-state allocation interventions.
This tests causal *simulation* effect of weight: prices are taken exogenously/fixed.
"""
from __future__ import annotations
import sys,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import run_olc74 as A
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
sys.path.insert(0,str(ROOT/'original_olc70_reference'))
import run_olc70 as old
from combined_engine import _s,_fill,_impl

KEYS=['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']

def create_policy_q(q,k,e,weight):
    z=dict(q)
    z['weights']=q['weights'].copy()
    z['weights'][0,k:e]=weight
    return z

def causal_marginal(m):
    q=dict(np.load(A.P/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
    events=q['events'];ids=np.flatnonzero(events);D=len(q['dates']);assert ids[0]==0 and ids[-1]==D-1 and len(ids)==90
    feats=pd.read_csv(R/'OLC74_PAIR_PANEL.csv')
    feats=feats[feats.market==m].sort_values('pos').reset_index(drop=True)
    assert len(feats)==90 and np.array_equal(ids,feats.event_index.to_numpy())
    eng,txt=old.state_matched_engine(_s,_fill)
    args=old.engine_args(fee=.001)
    b=_impl(q,events,policy='IMMEDIATE',fraction=1,**args)
    rr=eng(q,events,policy='IMMEDIATE',fraction=1,**args)
    for key in KEYS:assert np.array_equal(b[key],rr[key]),(m,key)
    plan={};labels=[];routes=[];fitq=[];prestate=None
    stitched={n:np.zeros_like(b[n]) for n in KEYS}
    for pos,k0 in enumerate(ids[:-1]):
        k,e=int(k0),int(ids[pos+1])
        now=feats.iloc[pos]
        # train on *own* past on-policy branch effects; labels t−1 are not yet eligible.
        mature=[v for v in labels if v['pos']<=pos-2]
        pred=0.;sd=np.nan;mean=np.nan; w=.5;enough=len(mature)>=24
        if enough:
            oldm=pd.DataFrame(mature)
            train=feats.merge(oldm[['pos','marginal_y_logbp']],on='pos',how='inner',validate='one_to_one')
            assert len(train)==len(mature) and int(train.pos.max())<=pos-2
            im=SimpleImputer(strategy='median',keep_empty_features=True)
            sc=StandardScaler()
            Xtr=sc.fit_transform(im.fit_transform(train[A.XCOLS].to_numpy(float)))
            Xnow=sc.transform(im.transform(now[A.XCOLS].to_numpy(float).reshape(1,-1)))
            y=train.marginal_y_logbp.to_numpy(float)
            mdl=Ridge(alpha=20).fit(Xtr,y)
            pred=float(mdl.predict(Xnow)[0]);sd=float(max(y.std(ddof=0),1e-5));mean=float(np.mean(y))
            w=float(np.clip(.5+.25*np.tanh(pred/sd),.25,.75))
        plan[k]=w
        branch={};start=[]
        for value,name in [(.25,'W25'),(.5,'W50'),(.75,'W75')]:
            fork=create_policy_q(q,k,e,value)
            result=eng(fork,events,policy='IMMEDIATE',fraction=1,start_index=k,end_index=e,initial_state=prestate,**args)
            st=float(result['ledger'][k,0]);ed=float(result['nav'][e-1]);assert st>0 and ed>0
            start.append(st)
            branch[name]=dict(logbp=float(10000*np.log(ed/st)),r=result,stops=float(result['ledger'][k:e,8].sum()))
            # When state matches baseline (at start) the same-weight branch is identical.
            if pos==0 and name=='W50':
                for key in KEYS:assert np.array_equal(result[key][k:e],b[key][k:e]),(m,pos,name,key)
        assert max(start)-min(start)<1e-10,(m,pos,start)
        chosen=branch['W50']['r'] if w==.5 else eng(create_policy_q(q,k,e,w),events,policy='IMMEDIATE',fraction=1,start_index=k,end_index=e,initial_state=prestate,**args)
        # It is legal to inspect the labels only *after* choosing w; they are used from t+2.
        label=branch['W75']['logbp']-branch['W25']['logbp']
        labels.append({'market':m,'pos':int(pos),'date':str(q['dates'][k])[:10],'event_index':k,'next_index':e,'ticker1':str(now.ticker1),'ticker2':str(now.ticker2),'start_nav':start[0],
                       'w25_bp':branch['W25']['logbp'],'w50_bp':branch['W50']['logbp'],'w75_bp':branch['W75']['logbp'],
                       'marginal_y_logbp':label,'price_monthly_spread_logbp':float(10000*now.diff_month_log) if np.isfinite(now.diff_month_log) else np.nan,
                       'w25_stops':branch['W25']['stops'],'w50_stops':branch['W50']['stops'],'w75_stops':branch['W75']['stops']})
        if enough:fitq.append({'market':m,'pos':int(pos),'date':str(q['dates'][k])[:10],'n_train':len(mature),'max_train_pos':int(oldm.pos.max()),'forecast_bp':pred,'actual_bp':label,'prior_mean_bp':mean,'sd_train_bp':sd})
        routes.append({'market':m,'pos':int(pos),'date':str(q['dates'][k])[:10],'w1':w,'w2':1-w,'fit_available':bool(enough),'n_train':len(mature),'forecast_effect_bp':pred,'same_state_effect_bp_EXPOST':label,'actual_selected_logbp':float(10000*np.log(float(chosen['nav'][e-1])/float(chosen['ledger'][k,0])))})
        prestate=chosen['state_out']
        for key in KEYS:stitched[key][k:e]=chosen[key][k:e]
    z=dict(q);z['weights']=q['weights'].copy()
    for j,k in enumerate(ids):
        e=int(ids[j+1]) if j+1<len(ids) else D
        z['weights'][0,int(k):e]=plan.get(int(k),.5)
    full=eng(z,events,policy='IMMEDIATE',fraction=1,**args)
    for key in KEYS:
        assert np.array_equal(stitched[key][:-1],full[key][:-1]),(m,key,float(np.max(np.abs(stitched[key][:-1]-full[key][:-1]))))
    return z,full,eng,labels,routes,fitq,{'market':m,'baseline_7arrays_exact':True,'adaptive_full_vs_segment_7arrays_bitwise':True,'events_with_label':len(labels),'branch_forks':3*len(labels),'onpolicy_path':True,'train_min_history_months':24,'train_maturity_2months':True}

def main():
    labels=[];routes=[];forecast=[];scores=[];ann=[];daily=[];qa={}
    for m in ['EU','USA']:
        z,full,engine,lab,rte,fit,audit=causal_marginal(m)
        qa[m]=audit;labels.extend(lab);routes.extend(rte);forecast.extend(fit)
        ds=pd.to_datetime(z['dates'][1:])
        for fee in [.001,.003]:
            r=full if fee==.001 else engine(z,z['events'],policy='IMMEDIATE',fraction=1,**old.engine_args(fee=fee))
            x=A.logr(r)
            policy='OLC74C_ONPOLICY'
            key=f'{m}_{policy}_IMMEDIATE_{int(fee*10000)}'
            met=A.metrics(z,r)
            for row in met:
                if row['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026','CRASH2020','2021','2022','2023'):
                    mask=(ds>=row['first_valuation'])&(ds<=row['last_valuation'])
                    c,dd=A.independent_metrics(x[mask]);assert abs(c-row['cagr'])<1e-10 and abs(dd-row['maxdd'])<1e-10
                    scores.append({'market':m,'policy':policy,'timing':'IMMEDIATE','fee':fee,'key':key,**row})
            for year in sorted(set(ds.year)):
                t=x[ds.year==year]
                ann.append({'market':m,'policy':policy,'timing':'IMMEDIATE','fee':fee,'year':int(year),'n':len(t),'return':float(np.expm1(t.sum()))})
            daily.append(pd.DataFrame({'date':ds,'market':m,'policy':policy,'timing':'IMMEDIATE','fee':fee,'key':key,'logr':x}))
            print('OLC74C',m,fee,'MAIN/FULL',[(r['period'],round(100*r['cagr'],3),round(100*r['maxdd'],3)) for r in met if r['period'] in ['ACTIVE2021_2024','FULL']],flush=True)
    pd.DataFrame(labels).to_csv(R/'OLC74C_ON_POLICY_COUNTERFACTUAL_LABELS.csv',index=False)
    pd.DataFrame(routes).to_csv(R/'OLC74C_ON_POLICY_ROUTE.csv',index=False)
    fit=pd.DataFrame(forecast);fit.to_csv(R/'OLC74C_FORECAST_SKILL.csv',index=False)
    pd.DataFrame(scores).to_csv(R/'OLC74C_SCORECARD.csv',index=False)
    pd.DataFrame(ann).to_csv(R/'OLC74C_ANNUAL.csv',index=False)
    pd.concat(daily,ignore_index=True).to_csv(R/'OLC74C_DAILY_LOGRET.csv.gz',index=False)
    skill=[]
    for m,g in fit.groupby('market'):
        g.date=pd.to_datetime(g.date)
        for per,mask in [('MAIN',g.date.dt.year.between(2021,2024)),('2024',g.date.dt.year==2024),('2025',g.date.dt.year==2025),('2026',g.date.dt.year==2026),('FULL',g.date.dt.year>=2019)]:
            a=g[mask]
            if len(a):
                y=a.actual_bp.to_numpy();mu=a.forecast_bp.to_numpy();p=a.prior_mean_bp.to_numpy()
                skill.append({'market':m,'period':per,'n':len(a),'ridge_MSE_bp2':float(np.mean((y-mu)**2)),'mean_only_MSE_bp2':float(np.mean((y-p)**2)),'pred_actual_spearman':float(pd.Series(y).corr(pd.Series(mu),method='spearman')),'mean_action_effect_bp':float(np.mean(y))})
    pd.DataFrame(skill).to_csv(R/'OLC74C_FORECAST_SKILL_SUMMARY.csv',index=False)
    qa.update({'status':'PASS','conditional_market_contrast':'AS_OF_ORIGINAL_OLC19','fixed_prices_causality_scope':'simulator intervention only'})
    (R/'OLC74C_QA.json').write_text(json.dumps(qa,indent=2))
    print('SKILL',pd.DataFrame(skill).query("period=='MAIN'").to_string(index=False))
    print('QA',json.dumps(qa,indent=2))
if __name__=='__main__':main()