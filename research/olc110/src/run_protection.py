"""Execute the predeclared OLC110 matrix with full account and policy ledgers."""
from pathlib import Path
import argparse,datetime,hashlib,importlib.util,json,platform
import numpy as np
import pandas as pd
import scipy
from threadpoolctl import threadpool_limits
from engine import simulate
from signals import decision_mask
from cluster_selectors import prepare_features
from dedup_selectors import make_policy as make_selector
from protection import ARMS,CONTROL_ARMS,prepare_timing_features,make_account_policy

SCENARIOS={'BASE':(1.,.0015,0,'OPEN'),'ZERO_COST':(0.,0.,0,'OPEN'),
           'DOUBLE_COST':(2.,.003,0,'OPEN'),'LAG1':(1.,.0015,1,'OPEN'),
           'LAG2':(1.,.0015,2,'OPEN'),'NEXT_CLOSE':(1.,.0015,0,'CLOSE')}
FINANCIAL_CODE=('src/engine.py','src/signals.py','src/cluster_selectors.py',
                'src/dedup_selectors.py','src/protection.py','src/run_protection.py',
                'source/src/core.py')
INPUTS=('source/data/XETRA_EUR_ETF.npz','data/LIQUIDITY.npz')


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_inputs(root):
    root=Path(root)
    with np.load(root/INPUTS[0],allow_pickle=False) as z:p={k:z[k] for k in z.files}
    p['dates']=pd.DatetimeIndex(p['dates']);p['benchmark']=int(p['benchmark'])
    with np.load(root/INPUTS[1],allow_pickle=False) as z:
        assert np.array_equal(z['names'],p['names']) and np.array_equal(z['dates'],p['dates'].values)
        turnover=z['turnover']
    spec=importlib.util.spec_from_file_location('olc110_account_core',root/'source/src/core.py')
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    return p,turnover,core


def save_decisions(folder,decisions):
    fields=('units','current_weights','raw_weights','weights')
    arrays={name:np.array([d[name] for d in decisions]) for name in fields}
    arrays.update(k=np.array([d['k'] for d in decisions],int),
                  cash=np.array([d['cash'] for d in decisions]))
    np.savez_compressed(folder/'DECISIONS.npz',**arrays)
    records=[]
    for d in decisions:
        records.append(dict(signal_idx=d['k'],signal_date=d['signal_date'],instruction_id=d['instruction_id'],
                            reason=d.get('reason'),scheduled=d.get('scheduled'),initial=d.get('initial'),
                            sell_only=d.get('sell_only',False),action_indices=json.dumps(d.get('action_indices')),
                            meta_json=json.dumps(d['meta'],separators=(',',':'))))
    pd.DataFrame(records).to_csv(folder/'DECISIONS.csv',index=False)


def compare_baseline(root,out,scenario,result):
    previous=root.parent/'olc109/results_stage2'/f'DEDUP_DUAL_TREND_OPP__{scenario}'
    assert previous.exists(),previous
    errors={}
    for filename,key in [('DAILY.csv.gz','daily'),('ORDERS.csv.gz','orders')]:
        original=pd.read_csv(previous/filename,float_precision='round_trip');current=result[key]
        assert len(original)==len(current),(filename,'row_count')
        for col in original:
            if pd.api.types.is_numeric_dtype(original[col]):
                error=float(np.max(np.abs(original[col].to_numpy(float)-current[col].to_numpy(float)))) if len(original) else 0.
                assert error<1e-8,(scenario,filename,col,error)
                errors[f'{filename}:{col}']=error
            else:assert original[col].astype(str).tolist()==current[col].astype(str).tolist(),(scenario,filename,col)
    with np.load(previous/'DECISIONS.npz',allow_pickle=False) as old:
        with np.load(out/'DECISIONS.npz',allow_pickle=False) as new:
            for key in old.files:
                assert old[key].shape==new[key].shape
                error=float(np.max(np.abs(old[key]-new[key]))) if old[key].size else 0.
                assert error<1e-8,(scenario,'DECISIONS',key,error)
                errors[f'DECISIONS:{key}']=error
    return dict(scenario=scenario,status='PASS_ORIGINAL_OLC109_REPLICATION',
                max_difference=max(errors.values(),default=0.),source=str(previous),details=errors)


def run(root,resume=False):
    root=Path(root).resolve();res=root/'results';res.mkdir(exist_ok=True)
    freeze=json.loads((root/'docs/EXPERIMENT_FREEZE.json').read_text())
    code={p:sha(root/p) for p in FINANCIAL_CODE};inputs={p:sha(root/p) for p in INPUTS}
    protocol=sha(root/'docs/DESIGN_AND_PROTOCOL.md')
    assert code==freeze['code_hashes'] and inputs==freeze['input_hashes']
    assert protocol==freeze['protocol_sha256']
    assert list(ARMS)==freeze['arms'] and list(SCENARIOS)==freeze['scenarios']
    cases=[(arm,scenario) for arm in ARMS for scenario in SCENARIOS]
    assert len(cases)==freeze['planned_paths']==78
    manifest_path=res/'RUN_MANIFEST.json'
    if manifest_path.exists():
        if not resume:raise FileExistsError('Refusing to overwrite completed or partial research')
        manifest=json.loads(manifest_path.read_text())
        assert manifest['code_hashes']==code and manifest['input_hashes']==inputs
        assert manifest['protocol_sha256']==protocol
    else:
        manifest=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            code_hashes=code,input_hashes=inputs,protocol_sha256=protocol,
            planned_paths=78,completed_paths=0,configurations=13,
            primary_arm='EXIT21_STAGED_FRESHW',baseline_arm='BASE',
            current_cagr_target=.30,drawdown_exclusion_gate=False,all_results_exploratory=True,
            pristine_holdout=False,prior_olc109_results_seen=True,fit_or_optimization=False,
            python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__)
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    p,turnover,core=load_inputs(root)
    monthly=decision_mask(p['dates'],'MONTHLY');weekly=decision_mask(p['dates'],'WEEKLY')
    begin=int(p['dates'].searchsorted('2020-03-02'))
    scores=[];annual=[];segments=[];replications=[]
    with threadpool_limits(limits=1):
        print('Preparing frozen selector and causal timing features',flush=True)
        f=prepare_timing_features(p,prepare_features(p,core,turnover))
        for seq,(arm,scenario) in enumerate(cases,1):
            path_id=f'{arm}__{scenario}';folder=res/path_id;folder.mkdir(exist_ok=True)
            if resume and (folder/'METRICS.json').exists():
                metrics=json.loads((folder/'METRICS.json').read_text())
                daily=pd.read_csv(folder/'DAILY.csv.gz',float_precision='round_trip')
            else:
                ticket,impact,lag,fill=SCENARIOS[scenario]
                panel=p if fill=='OPEN' else dict(p,O=p['C'],open_observed=p['observed'])
                base=make_selector(panel,f,{},'DEDUP_DUAL_TREND_OPP')
                scale=.5 if arm=='STATIC_HALF' else .75 if arm=='STATIC_75' else 1.
                def policy(k,current,base=base,scale=scale):
                    w,m=base(k,current);return w*scale,m
                mask=weekly if arm=='REFRESH_WEEKLY' else monthly
                ap=None if arm in CONTROL_ARMS else make_account_policy(panel,f,monthly,weekly,arm,begin-1)
                result=simulate(panel,f,policy,mask,legacy=core,account_policy=ap,
                                lag=lag,ticket=ticket,impact=impact)
                daily,orders=result['daily'],result['orders']
                financial=core.portfolio_metrics(daily.nav_close,daily.date,10000.,daily.nav_open)
                years=financial['days']/365.2425
                instruction=result['instructions'].copy()
                if len(orders):
                    nav_at=pd.Series(daily.nav_open.to_numpy(),index=daily.date)
                    turnover_annual=float((orders.notional.to_numpy()/nav_at.loc[orders.date].to_numpy()).sum()/years)
                else:turnover_annual=0.
                metrics=dict(path_id=path_id,arm=arm,scenario=scenario,fill=fill,
                    cadence='WEEKLY' if arm=='REFRESH_WEEKLY' else 'MONTHLY_WITH_EVENTS' if ap else 'MONTHLY',
                    currency='EUR',ticket=ticket,impact_bps=impact*10000,lag_extra=lag,
                    **financial,orders=len(orders),trading_days=int(orders.date.nunique()),
                    trading_days_per_year=float(orders.date.nunique()/years),
                    instructions=len(instruction),costs=float(orders.cost.sum()),
                    two_sided_turnover_per_year=turnover_annual,mean_exposure=float(daily.gross.mean()),
                    mean_cash_share=float((1-daily.gross).mean()),mean_positions=float(daily.positions.mean()),
                    full_cash_days=int((daily.gross<=1e-8).sum()),
                    deferred_sessions=result['deferred_sessions'],max_self_financing_error=result['max_self_financing_error'],
                    cagr_target_pass=financial['cagr']>=.30,drawdown_exclusion_gate=False,
                    drawdown_sampling='OPEN_CLOSE' if fill=='OPEN' else 'CLOSE_PRE_POST_FEES')
                daily.to_csv(folder/'DAILY.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                orders.to_csv(folder/'ORDERS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                for col in ['target_weights','raw_weights','action_indices','meta']:
                    if col in instruction:instruction[col]=instruction[col].map(lambda value:json.dumps(value,separators=(',',':')))
                instruction.to_csv(folder/'INSTRUCTIONS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                save_decisions(folder,result['decisions'])
                if ap:pd.DataFrame(ap.trace).to_csv(folder/'POLICY_TRACE.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                (folder/'METRICS.json').write_text(json.dumps(metrics,indent=2)+'\n')
                if arm=='BASE' and scenario!='NEXT_CLOSE':
                    replications.append(compare_baseline(root,folder,scenario,result))
                    (res/'BASELINE_REPLICATION.json').write_text(json.dumps(replications,indent=2)+'\n')
                print(f'{seq}/{len(cases)} {path_id}: CAGR {100*financial["cagr"]:.2f}% DD {100*financial["maxdd_sampled"]:.2f}% exposure {100*metrics["mean_exposure"]:.1f}% trades/y {metrics["trading_days_per_year"]:.1f}',flush=True)
            scores.append(metrics)
            dt=pd.to_datetime(daily.date);yy=dt.dt.year.to_numpy()
            for year in sorted(set(yy)):
                ix=np.flatnonzero(yy==year);initial=10000. if ix[0]==0 else float(daily.nav_close.iloc[ix[0]-1])
                mm=core.portfolio_metrics(daily.nav_close.iloc[ix],daily.date.iloc[ix],initial,daily.nav_open.iloc[ix])
                annual.append(dict(path_id=path_id,arm=arm,scenario=scenario,year=int(year),annual_return=mm['cumulative'],
                                   maxdd_in_year=mm['maxdd_sampled'],partial_year=year in [2020,2026]))
            for label,cond in [('2020',yy==2020),('2021_2024',(yy>=2021)&(yy<=2024)),('2025_2026',yy>=2025),('2021_2026',yy>=2021)]:
                ix=np.flatnonzero(cond);initial=10000. if ix[0]==0 else float(daily.nav_close.iloc[ix[0]-1])
                mm=core.portfolio_metrics(daily.nav_close.iloc[ix],daily.date.iloc[ix],initial,daily.nav_open.iloc[ix])
                segments.append(dict(path_id=path_id,arm=arm,scenario=scenario,segment=label,**mm))
            pd.DataFrame(scores).to_csv(res/'SCORECARD.csv',index=False)
            manifest['completed_paths']=len(scores);manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
        pd.DataFrame(annual).to_csv(res/'ANNUAL_RETURNS.csv',index=False)
        pd.DataFrame(segments).to_csv(res/'DESCRIPTIVE_SEGMENTS.csv',index=False)
    assert {path:sha(root/path) for path in code}==code
    assert {path:sha(root/path) for path in inputs}==inputs
    assert sha(root/'docs/DESIGN_AND_PROTOCOL.md')==protocol
    manifest.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_paths=len(scores))
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print('COMPLETE',len(scores),'paths;',sum(m['cagr_target_pass'] for m in scores),'CAGR30 passes',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();run(args.root,args.resume)
