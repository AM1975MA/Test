#!/usr/bin/env python3
"""OLC70B: strictly sequential on-policy, state-matched counterfactual learning.

All decisions at t use only earlier outcomes at most t-2; counterfactual branch
outcomes for month t are revealed only after t's choice is fixed. The selected
branch's complete portfolio state carries into the next event. Native full
replay must match every per-event chunk bitwise on 7 accounting arrays.
"""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
import run_olc70 as base

ROOT=Path(__file__).resolve().parent
S=base.DEFAULT_SOURCE


def route_and_execute(m, original, eng, engine_args, feature_df, native_impl, metrics):
    q,events,ids,dec=original.load(m)
    feat=feature_df[feature_df.market==m].copy().set_index('signal_month',drop=False)
    assert len(feat)==82
    d=len(q['dates'])
    assert len(ids)==90 and ids[-1]==d-1
    state=None
    chosen_rows=[];labels=[];forecast_skill=[]
    # One independent monthly observation for each candidate is produced at
    # the end of its month, not known when making the choice.
    stitch={s:np.zeros_like(np.asarray(v)) for s,v in
            [('nav',np.ones(d)),('ledger',np.zeros((d,26))),
             ('primary_units',np.zeros_like(q['O'])),
             ('defensive_units',np.zeros_like(q['O'])),
             ('free_cash',np.zeros(d)),
             ('targets',np.zeros_like(q['O'])),
             ('risk_trace',np.zeros((d,8)))]}
    plan={};raw_returns=[]
    for j,k0 in enumerate(ids[:-1]):
        k,e=int(k0),int(ids[j+1]);month=str(pd.to_datetime(q['dates'][k]))[:7]
        lookup=feat.loc[month] if month in feat.index else None
        action='A';pred={'A':0.0,'B':np.nan,'C':np.nan,'D':np.nan}
        matured=[]
        if lookup is not None:
            current=pd.Period(month,'M')
            matured=[v for v in labels if v['month'] in feat.index and pd.Period(v['month'],'M')<=current-2]
            if len(matured)>=24:
                train=pd.DataFrame(matured).merge(feat[base.FEATURES],left_on='month',right_index=True,validate='one_to_one')
                x=train[base.FEATURES].to_numpy(float)
                xnow=lookup[base.FEATURES].to_numpy(dtype=float).reshape(1,-1)
                for a in 'BCD':
                    y=train[a+'_vs_A_logbp'].to_numpy(float)
                    fit=make_pipeline(StandardScaler(),Ridge(alpha=25.))
                    fit.fit(x,y);pred[a]=float(fit.predict(xnow)[0])
                    forecast_skill.append(dict(market=m,month=month,action=a,predicted_logbp=pred[a],
                             prior_mean_logbp=float(y.mean()),train_n=int(len(y))))
                best=max(base.ACTIONS,key=lambda a:(pred[a] if np.isfinite(pred[a]) else -np.inf))
                if best!='A' and pred[best]>5:action=best
        plan[k]=action
        branch_results={};branch_log={};starts=[]
        for a in base.ACTIONS:
            qfork,lag=base.make_q(q,ids,dec,{k:a})
            r=eng(qfork,events,policy='ADAPTIVE',fraction=3,adaptive_lag=lag,
                  start_index=k,end_index=e,initial_state=state,**engine_args())
            start=float(r['ledger'][k,0]);end=float(r['nav'][e-1]);assert start>0 and end>0
            starts.append(start);branch_results[a]=r
            branch_log[a]=float(10000*np.log(end/start))
        assert max(starts)-min(starts)<1e-10
        row=dict(market=m,month=month,event_index=k,next_index=e,prestate_nav=starts[0],
                 previous_cooldown=int(state['cd']) if state is not None else 0,
                 previous_locks=int(np.sum(state['lock_until']>=k)) if state is not None else 0,
                 **{a+'_return_logbp':branch_log[a] for a in base.ACTIONS})
        for a in 'BCD':row[a+'_vs_A_logbp']=branch_log[a]-branch_log['A']
        row['chosen_action']=action
        row['chosen_excess_logbp']=branch_log[action]-branch_log['A']
        labels.append(row)
        if lookup is not None:
            chosen_rows.append(dict(market=m,month=month,action=action,train_n=len(matured),
                      asof=str(lookup['feature_asof_date']),
                      **{'pred_'+a:pred[a] for a in 'BCD'},
                      observed_chosen_common_state_logbp=row['chosen_excess_logbp']))
        selected=branch_results[action]
        state=selected['state_out']
        # Stitch 7 arrays exactly, preserving all path-dependent risk and stop flows.
        for key in stitch:stitch[key][k:e]=selected[key][k:e]
        raw_returns.extend(np.log(selected['nav'][k:e]/selected['ledger'][k:e,0]).tolist())
    # Full simulation of the same fixed actions. This MUST produce identical
    # seven original engine arrays and validates all state checkpoint fields.
    z,lag=base.make_q(q,ids,dec,plan)
    full=eng(z,events,policy='ADAPTIVE',fraction=3,adaptive_lag=lag,**engine_args())
    for key in stitch:
        if not np.array_equal(stitch[key][:-1],full[key][:-1]):
            raise AssertionError('OLC70B full-path stitching parity fails: '+m+'/'+key+' max='+str(np.max(abs(stitch[key][:-1]-full[key][:-1]))))
    assert np.allclose(np.asarray(raw_returns),np.log(full['nav'][:-1]/full['ledger'][:-1,0]),rtol=0,atol=1e-13)
    lab=pd.DataFrame(labels);skill=pd.DataFrame(forecast_skill)
    skill=skill.merge(lab[['month','A_return_logbp','B_vs_A_logbp','C_vs_A_logbp','D_vs_A_logbp']],on='month',validate='many_to_one')
    skill['actual_logbp']=[float(row[a+'_vs_A_logbp']) for a,row in zip(skill.action,skill.to_dict('records'))]
    out={'labels':lab,'route':pd.DataFrame(chosen_rows),'skill':skill,'plan':plan,'q':q,
         'z':z,'events':events,'full':full,'parity':'SEVEN_ARRAYS_BITWISE_CHUNKS_AND_FULL'}
    return out


def run(args):
    source=Path(args.source)
    obs={name:base.digest(source/name) for name in base.SOURCE_HASHES}
    assert obs==base.SOURCE_HASHES
    olc67=source/'OLC67';native=olc67/'native/olc19_combined_risk_20261102';parent=native/'restore/olc18_execution_20261102'
    for p in [olc67,native/'src',parent/'parent_archive/parent/olc16_contextual_rank_20261102/src']:
        sys.path.insert(0,str(p))
    import run_olc67 as original
    from combined_engine import _s,_fill,_impl
    from portfolio_metrics_parent import metrics
    eng,_=base.state_matched_engine(_s,_fill)
    feat=pd.read_csv(source/'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv')
    out=ROOT/'results';out.mkdir(exist_ok=True)
    audit={'source_sha256':obs,'component':'OLC70B','policy':'ON_POLICY_SAME_STATE_WITH_2MONTH_LABEL_MATURITY',
           'markets':{}}
    labels=[];routes=[];skill=[];daily=[];annual=[];sc=[];drifts=[]
    a_labels=pd.read_csv(out/'OLC70_COMMON_STATE_LABELS.csv')
    for m in ['EU','USA']:
        q=route_and_execute(m,original,eng,base.engine_args,feat,_impl,metrics)
        audit['markets'][m]={'n_events':len(q['labels']),'n_forecasts':len(q['skill']),
                    'native_parity':q['parity'],'action_counts':q['route'].action.value_counts().to_dict()}
        labels.append(q['labels']);routes.append(q['route']);skill.append(q['skill'])
        joined=q['labels'].merge(a_labels[a_labels.market==m],on=['market','month'],suffixes=('_onpolicy','_baseline_state'),validate='one_to_one')
        for a in 'BCD':
            drifts.append(pd.DataFrame(dict(market=m,month=joined.month,action=a,
                        onpolicy_logbp=joined[a+'_vs_A_logbp_onpolicy'],
                        baseline_state_logbp=joined[a+'_vs_A_logbp_baseline_state'],
                        drift_logbp=joined[a+'_vs_A_logbp_onpolicy']-joined[a+'_vs_A_logbp_baseline_state'])))
        for fee in [.001,.003]:
            if fee==.001:r=q['full']
            else:r=eng(q['z'],q['events'],policy='ADAPTIVE',fraction=3,
                       adaptive_lag=base.make_q(q['q'],np.flatnonzero(q['events']),original.load(m)[3],q['plan'])[1],
                       **base.engine_args(fee))
            rscore=base.score_metric(q['z'],r,metrics);rscore['fee']=fee;rscore['market']=m;rscore['policy']='OLC70B_ONPOLICY';sc.append(rscore)
            lr=np.log(r['nav'][:-1]/r['ledger'][:-1,0]);dates=pd.to_datetime(q['q']['dates'][1:]);assert len(lr)==len(dates)
            for z in rscore.itertuples():
                f=(dates>=z.first_valuation)&(dates<=z.last_valuation)
                assert int(f.sum())==z.n
                assert abs(np.expm1(float(np.mean(lr[f]))*252)-z.cagr)<1e-11
            for year in sorted(set(dates.year)):
                sl=dates.year==year
                annual.append(dict(market=m,fee=fee,year=int(year),
                         annual_return=float(np.expm1(np.sum(lr[sl]))),days=int(sl.sum())))
            daily.append(pd.DataFrame({'market':m,'fee':fee,'date':dates,'logr':lr}))
            print('OLC70B',m,'fee',fee,'MAIN/FULL',rscore[rscore.period.isin(['ACTIVE2021_2024','FULL'])][['period','cagr','maxdd']].to_dict('records'),flush=True)
    pd.concat(labels).to_csv(out/'OLC70B_ON_POLICY_LABELS.csv',index=False)
    pd.concat(routes).to_csv(out/'OLC70B_ROUTE.csv',index=False)
    pd.concat(skill).to_csv(out/'OLC70B_FORECAST_SKILL.csv',index=False)
    pd.concat(drifts).to_csv(out/'OLC70B_STATE_SHIFT_VS_BASELINE.csv',index=False)
    pd.concat(sc).to_csv(out/'OLC70B_SCORECARD.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'OLC70B_ANNUAL.csv',index=False)
    pd.concat(daily).to_csv(out/'OLC70B_DAILY_LOGRET.csv.gz',index=False)
    (out/'OLC70B_QA.json').write_text(json.dumps(audit,indent=2,default=str))
    print('COMPLETE',audit['markets'],flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',default=str(S))
    run(ap.parse_args())