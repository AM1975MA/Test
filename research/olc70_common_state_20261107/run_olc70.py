#!/usr/bin/env python3
"""OLC70: same-state monthly counterfactual outcomes and causal adaptive replay.

Uses OLC67 frozen OLC19 code and OLC68 ex-ante inputs. Does NOT alter the original.
The counterfactual 4 actions branch from the exact OLC19 A *pre-event* book,
then run natively until the next event's opening. The route fit is deterministic,
strictly expanding with t-2 maturity, same hyperparams and features as OLC69.
"""
from __future__ import annotations
import argparse, hashlib, json, sys, copy
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

ROOT=Path(__file__).resolve().parent
DEFAULT_SOURCE=(ROOT/'inputs' if (ROOT/'inputs/OLC67').is_dir() else Path('/mnt/data/OLC69_Adaptive_Opportunity_20261107'))
FEATURES=['universe_breadth_63','pair_avg_mom63','pair_prior_mom_weighted_tilt','pair_corr63']
ACTIONS={'A':(False,1),'B':(True,1),'C':(False,3),'D':(True,3)}
SOURCE_HASHES={
  'OLC67_Strategia_ETF_Verificata.zip':'dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4',
  'OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv':'b7911d1346f6d78a19513547fd4b91b8a68a1806b2332f3a95815fcaf2caf330',
}
STATE_KEYS=['units','au','bu','su','free','at','cd','force_target','lock_until','pending_reentry',
            'tar','executed','previous_proposal','last_cohort','executed_f','executed_aw',
            'last_i','last_j','last_sig','remaining','last_proposal_vector']


def digest(path:Path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for blob in iter(lambda:f.read(1<<20),b''): h.update(blob)
    return h.hexdigest()


def replace_once(s,old,new):
    if s.count(old)!=1:raise AssertionError(f'Unexpected original source contract; {s.count(old)} matches of {old[:100]!r}')
    return s.replace(old,new,1)


def state_matched_engine(source, fill):
    """Instrument, without modifying, the *original OLC19* native sim function.

    Snapshots consist of every accounting state field needed to resume from a
    pre-event opening. Parity tests run against the untouched OLC19 engine.
    """
    s=source
    s=replace_once(s, 'order_log=None):',
        'order_log=None, initial_state=None, start_index=0, end_index=None, '
        'snapshot_indices=None, snapshot_store=None, adaptive_lag=None):')
    s=replace_once(s,"if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY']:",
                     "if policy not in ['IMMEDIATE','PARTIAL','TOP4','COHORT2','PHASE','DELAY','ADAPTIVE']:")
    s=replace_once(s,"if policy=='IMMEDIATE':tar=p", "if policy=='IMMEDIATE' or (policy=='ADAPTIVE' and int(adaptive_lag[k])==1):\n            tar=p;remaining=0")
    s=replace_once(s,"elif policy=='DELAY':", "elif policy=='DELAY' or (policy=='ADAPTIVE' and int(adaptive_lag[k])==3):")
    marker="    for k in range(D):"
    inject="""    if end_index is None:end_index=D
    if not (0 <= start_index < D and start_index < end_index <= D):
        raise AssertionError('Invalid subperiod')
    if policy=='ADAPTIVE':
        if adaptive_lag is None or len(adaptive_lag)!=D or not np.isin(adaptive_lag,[1,3]).all():
            raise AssertionError('Invalid adaptive lag vector')
    if initial_state is not None:
        units=initial_state['units'].copy()
        au=float(initial_state['au']);bu=float(initial_state['bu']);su=float(initial_state['su'])
        free=float(initial_state['free']);at=int(initial_state['at']);cd=int(initial_state['cd'])
        force_target=bool(initial_state['force_target'])
        lock_until=initial_state['lock_until'].copy()
        pending_reentry=initial_state['pending_reentry'].copy()
        tar=initial_state['tar'].copy();executed=initial_state['executed'].copy()
        previous_proposal=None if initial_state['previous_proposal'] is None else initial_state['previous_proposal'].copy()
        last_cohort=None if initial_state['last_cohort'] is None else initial_state['last_cohort'].copy()
        executed_f=float(initial_state['executed_f']);executed_aw=float(initial_state['executed_aw'])
        last_i=int(initial_state['last_i']);last_j=int(initial_state['last_j'])
        last_sig=initial_state['last_sig'];remaining=int(initial_state['remaining'])
        last_proposal_vector=None if initial_state['last_proposal_vector'] is None else initial_state['last_proposal_vector'].copy()
    def _save_state():
        # Snapshot prior to *this* event's trade, not after it.
        return {
          'units':units.copy(),'au':au,'bu':bu,'su':su,'free':free,'at':at,
          'cd':cd,'force_target':force_target,'lock_until':lock_until.copy(),
          'pending_reentry':pending_reentry.copy(),'tar':tar.copy(),
          'executed':executed.copy(),
          'previous_proposal':None if previous_proposal is None else previous_proposal.copy(),
          'last_cohort':None if last_cohort is None else last_cohort.copy(),
          'executed_f':executed_f,'executed_aw':executed_aw,
          'last_i':last_i,'last_j':last_j,'last_sig':last_sig,
          'remaining':remaining,
          'last_proposal_vector':None if last_proposal_vector is None else last_proposal_vector.copy(),
        }
    if snapshot_indices is None:snapshot_indices=set()
    for k in range(start_index,end_index):
        if k in snapshot_indices:
            assert snapshot_store is not None
            snapshot_store[k]=_save_state()"""
    s=replace_once(s,marker,inject)
    s=replace_once(s,"return {'risk_trace':risk_trace,'nav':nav,",
        "return {'state_out':_save_state(),'risk_trace':risk_trace,'nav':nav,")
    ns={'_fill':fill}
    exec(compile(s,'<OLC70_STATE_MATCHED_NATIVE_OLC19>','exec'),ns)
    return ns['simulate'],s


def make_q(q,ids,decision,mixed_actions=None):
    z=dict(q)
    z['weights']=np.array(q['weights'],copy=True)
    lag=np.ones(len(q['dates']),dtype=int)
    for j,k in enumerate(ids):
        end=int(ids[j+1]) if j+1<len(ids) else len(lag)
        action = mixed_actions.get(int(k),'A') if mixed_actions is not None else 'A'
        minvar, lag_n = ACTIONS[action]
        w=float(decision.loc[j,'weight__B1_MINVAR63_CAP25']) if minvar else .5
        z['weights'][0,k:end]=w
        lag[k:end]=lag_n
    return z,lag


def engine_args(fee=.001,fast=True):
    return dict(fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,
                ordinary_alarm=False,fast_stop=fast,lock_days=3 if fast else 0)


def test_seven(actual,expected,start=0,stop=None,where=''):
    for key in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
        a,b=actual[key],expected[key]
        aa=a[start:stop];bb=b[start:stop]
        if not np.array_equal(aa,bb):
            bad=float(np.max(np.abs(aa-bb)))
            raise AssertionError(f'Native parity mismatch {where}/{key}: {bad}')


def counterfactual(market,q,events,ids,decisions,engine,native_impl):
    """All four actions start from the same actual A pre-event portfolio."""
    qa={}
    snapshots={}
    base=q
    base_orig=native_impl(base,events,policy='IMMEDIATE',fraction=1,**engine_args())
    base_r=engine(base,events,policy='IMMEDIATE',fraction=1,snapshot_indices=set(map(int,ids)),snapshot_store=snapshots,**engine_args())
    test_seven(base_r,base_orig,where=market+' A whole replay')
    assert len(snapshots)==len(ids)
    qa['A_bitwise_seven_arrays']='PASS'
    fixed_d={int(k):'D' for k in ids}
    d,dl=make_q(q,ids,decisions,fixed_d)
    d_orig=native_impl(d,events,policy='DELAY',fraction=3,**engine_args())
    d_r=engine(d,events,policy='ADAPTIVE',fraction=3,adaptive_lag=dl,**engine_args())
    test_seven(d_r,d_orig,where=market+' D whole replay')
    qa['D_bitwise_seven_arrays']='PASS'
    rows=[]
    n_branch=0
    for j,k0 in enumerate(ids[:-1]):
        k,e=int(k0),int(ids[j+1])
        row={'market':market,'month':str(pd.to_datetime(q['dates'][k]))[:7],
             'event_index':k,'next_index':e,'start_date':str(pd.to_datetime(q['dates'][k]))[:10],
             'next_date':str(pd.to_datetime(q['dates'][e]))[:10],
             'ticker1':str(q['tickers'][q['d1'][0,k]]),'ticker2':str(q['tickers'][q['d2'][0,k]]),
             'minvar_weight1':float(decisions.loc[j,'weight__B1_MINVAR63_CAP25']),
             'start_cooldown':int(snapshots[k]['cd']),
             'start_locked_count':int(np.sum(snapshots[k]['lock_until']>=k)),
             'start_free_cash':float(snapshots[k]['free'])}
        start_values=[]
        for action in ACTIONS:
            qfork,lfork=make_q(q,ids,decisions,{k:action})
            # *** All forks share EXACT same state ***
            f=engine(qfork,events,policy='ADAPTIVE',fraction=3,adaptive_lag=lfork,
                     start_index=k,end_index=e,initial_state=snapshots[k],**engine_args())
            start=float(f['ledger'][k,0]);end=float(f['nav'][e-1])
            assert start>0 and end>0
            start_values.append(start)
            row[f'{action}_return_logbp']=float(np.log(end/start)*10000)
            row[f'{action}_branch_stops']=int(round(float(f['ledger'][k:e,8].sum())))
            row[f'{action}_branch_fees']=float(f['ledger'][k:e,5:7].sum())
            n_branch+=1
            if action=='A':
                test_seven(f,base_orig,start=k,stop=e,where=market+' A chunk '+str(j))
                assert abs(row[f'{action}_return_logbp']-float(np.log(base_orig['nav'][e-1]/base_orig['ledger'][k,0])*10000))<1e-9
            if action=='D' and j==0:
                # This is a local fork off A, not an independent full D portfolio.
                assert np.isfinite(row[f'{action}_return_logbp'])
        assert max(start_values)-min(start_values)<1e-10
        for action in 'BCD':row[f'{action}_vs_A_logbp']=row[f'{action}_return_logbp']-row['A_return_logbp']
        row['oracle_best_action_EXPOST']=max(ACTIONS,key=lambda x:row[x+'_return_logbp'])
        row['oracle_gain_logbp_EXPOST']=max(row[x+'_return_logbp'] for x in ACTIONS)-row['A_return_logbp']
        rows.append(row)
    qa['snapshots_pre_event']=len(snapshots)
    qa['counterfactual_event_months']=len(rows)
    qa['branch_runs']=n_branch
    qa['A_chunk_exact_parity']='PASS'
    return pd.DataFrame(rows),qa


def route_model(features,labels,market):
    d=features[features.market==market].merge(labels[labels.market==market],left_on='signal_month',right_on='month',validate='one_to_one')
    d=d.sort_values('signal_month').reset_index(drop=True)
    assert len(d)==82, (market,len(d))
    assert d[FEATURES+['B_vs_A_logbp','C_vs_A_logbp','D_vs_A_logbp']].notna().all().all()
    d['p']=pd.PeriodIndex(d.signal_month,freq='M')
    predictions=[];skill=[]
    for row in d.itertuples(index=False):
        old=d[d['p']<=row.p-2]
        enough=len(old)>=24
        forecast={'A':0.0,'B':np.nan,'C':np.nan,'D':np.nan}
        action='A'
        if enough:
            X=old[FEATURES].to_numpy(float)
            now=d.loc[d.signal_month==row.signal_month,FEATURES].to_numpy(float)
            for a in 'BCD':
                y=old[a+'_vs_A_logbp'].to_numpy(float)
                model=make_pipeline(StandardScaler(),Ridge(alpha=25.))
                model.fit(X,y)
                forecast[a]=float(model.predict(now)[0])
                skill.append(dict(market=market,month=row.signal_month,action=a,
                                  predicted_logbp=forecast[a],actual_common_state_logbp=float(getattr(row,a+'_vs_A_logbp')),
                                  mean_prior_logbp=float(y.mean()),n_training=int(len(old))))
            winner=max(ACTIONS,key=lambda a:(forecast[a] if np.isfinite(forecast[a]) else -float('inf')))
            if winner!='A' and forecast[winner]>5:action=winner
        predictions.append(dict(market=market,month=row.signal_month,asof=row.feature_asof_date,
                                action=action,train_n=int(len(old)),
                                **{'pred_'+a+'_logbp':forecast[a] for a in 'BCD'},
                                observed_common_state_action_logbp=float(getattr(row,action+'_vs_A_logbp') if action!='A' else 0.)))
    return pd.DataFrame(predictions),pd.DataFrame(skill)


def score_metric(q,r,metrics_fn):
    return pd.DataFrame([row for row in metrics_fn(q,r) if row['period'] in ['ACTIVE2021_2024','FULL','2025','2026','CRASH2020']])


def run(args):
    out=ROOT/'results';out.mkdir(parents=True,exist_ok=True)
    source=Path(args.source)
    files={n:(source/n) for n in SOURCE_HASHES}
    hashes={n:digest(f) for n,f in files.items()}
    assert hashes==SOURCE_HASHES,(hashes,SOURCE_HASHES)
    olc67=source/'OLC67'
    native=olc67/'native/olc19_combined_risk_20261102'
    parent=native/'restore/olc18_execution_20261102'
    for p in [olc67,native/'src',parent/'parent_archive/parent/olc16_contextual_rank_20261102/src']:
        sys.path.insert(0,str(p))
    import run_olc67 as original
    from combined_engine import _s, _fill, _impl
    from portfolio_metrics_parent import metrics
    eng,patched_src=state_matched_engine(_s,_fill)
    (ROOT/'engine_olc70_instrumented.py.txt').write_text(patched_src)
    features=pd.read_csv(files['OLC68_PRESIGNAL_EVENT_DIAGNOSTIC.csv'])
    assert len(features)==164
    all_cf=[];all_skill=[];all_route=[];all_daily=[];all_score=[];all_annual=[]
    old_labs=[];qa={'inputs_sha256':hashes,'markets':{},'engine_patch_sha256':digest(ROOT/'engine_olc70_instrumented.py.txt'),'policy_parameters':dict(alpha=25,min_train=24,edge_logbp=5,features=FEATURES,fee_primary=.001)}
    for m in ['EU','USA']:
        q,events,ids,dec=original.load(m)
        rows,qm=counterfactual(m,q,events,ids,dec,eng,_impl)
        assert len(rows)==89
        qa['markets'][m]=qm
        all_cf.append(rows)
        tmp=features[features.market==m].merge(rows,left_on='signal_month',right_on='month',validate='one_to_one')
        for a,olc69_col in [('B','weightonly_logbp'),('C','timingonly_logbp'),('D','paired_logbp')]:
            old_labs.append(pd.DataFrame({'market':m,'month':tmp.signal_month,'action':a,
                     'original_independent_path_logbp':tmp[olc69_col],
                     'olc70_state_matched_logbp':tmp[a+'_vs_A_logbp'],
                     'difference_logbp':tmp[a+'_vs_A_logbp']-tmp[olc69_col]}))
        decisions,forecast=route_model(features,rows,m)
        all_route.append(decisions);all_skill.append(forecast)
        actions={}
        for i,k in enumerate(ids):
            mon=str(pd.to_datetime(q['dates'][k]))[:7]
            match=decisions.loc[decisions.month==mon]
            actions[int(k)]=str(match.iloc[0].action) if len(match) else 'A'
        z,ad_lag=make_q(q,ids,dec,actions)
        for fee in [.001,.003]:
            r=eng(z,events,policy='ADAPTIVE',fraction=3,adaptive_lag=ad_lag,**engine_args(fee))
            sc=score_metric(z,r,metrics)
            sc['market']=m;sc['fee']=fee;sc['policy']='OLC70_COMMONSTATE_ROUTE';all_score.append(sc)
            dr=np.log(r['nav'][:-1]/r['ledger'][:-1,0]);dt=pd.to_datetime(q['dates'][1:])
            assert len(dr)==len(dt) and np.isfinite(dr).all()
            daily=pd.DataFrame({'market':m,'fee':fee,'policy':'OLC70_COMMONSTATE_ROUTE','date':dt,'logr':dr})
            all_daily.append(daily)
            for year in sorted(set(dt.year)):
                ix=dt.year==year
                all_annual.append(dict(market=m,fee=fee,policy='OLC70_COMMONSTATE_ROUTE',year=int(year),
                              n=int(ix.sum()),return_arithmetic=float(np.expm1(dr[ix].sum()))))
            for metric in sc.itertuples():
                mask=(dt>=metric.first_valuation)&(dt<=metric.last_valuation)
                v=dr[mask]
                assert len(v)==metric.n
                cagr=float(np.expm1(v.mean()*252))
                assert abs(cagr-metric.cagr)<1e-11,(m,fee,metric.period)
            print('OLC70',m,'fee',fee,'MAIN/FULL',sc.loc[sc.period.isin(['ACTIVE2021_2024','FULL']),['period','cagr','maxdd']].to_dict('records'),flush=True)
        print('OLC70',m,'action_count',decisions.action.value_counts().to_dict(), 'label_std',rows[[s+'_vs_A_logbp' for s in 'BCD']].std().to_dict(),flush=True)
    cf=pd.concat(all_cf,ignore_index=True); cf.to_csv(out/'OLC70_COMMON_STATE_LABELS.csv',index=False)
    pd.concat(old_labs,ignore_index=True).to_csv(out/'OLC70_LABEL_BRIDGE_OLC69.csv',index=False)
    pd.concat(all_route,ignore_index=True).to_csv(out/'OLC70_ROUTING.csv',index=False)
    skill=pd.concat(all_skill,ignore_index=True);skill.to_csv(out/'OLC70_FORECAST_SKILL.csv',index=False)
    pd.concat(all_score,ignore_index=True).to_csv(out/'OLC70_SCORECARD.csv',index=False)
    pd.DataFrame(all_annual).to_csv(out/'OLC70_ANNUAL.csv',index=False)
    pd.concat(all_daily,ignore_index=True).to_csv(out/'OLC70_DAILY_LOGRET.csv.gz',index=False)
    qa['n_common_state_labels']=len(cf)
    qa['forecast_records']=len(skill)
    qa['route_months']=len(pd.concat(all_route))
    qa['full_engine_replays']=4
    (out/'OLC70_QA.json').write_text(json.dumps(qa,indent=2,default=str))
    return qa

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--source',default=str(DEFAULT_SOURCE))
    run(ap.parse_args())