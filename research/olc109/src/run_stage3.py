"""Run all40 declared adaptive stage3 OLC109 configurations with a complete account ledger."""
from pathlib import Path
import argparse,datetime,gzip,hashlib,importlib.util,json,platform
import numpy as np
import pandas as pd
import scipy
from threadpoolctl import threadpool_limits
from engine import simulate
from signals import decision_mask
from cluster_selectors import prepare_features,build_snapshot,make_guard
from horizon_selectors import ARMS,make_policy

SCENARIOS={'BASE':(1.,.0015,0),'ZERO_COST':(0.,0.,0),
           'DOUBLE_COST':(2.,.003,0),'LAG1':(1.,.0015,1),'LAG2':(1.,.0015,2)}
FINANCIAL_CODE=('src/engine.py','src/signals.py','src/cluster_selectors.py',
                'src/prepare_liquidity.py','src/run_research.py','src/run_stage3.py','src/dedup_selectors.py','src/horizon_selectors.py','source/src/core.py')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load_panel(root):
    with np.load(Path(root)/'source/data/XETRA_EUR_ETF.npz',allow_pickle=False) as z:p={k:z[k] for k in z.files}
    p['dates']=pd.DatetimeIndex(p['dates']);p['benchmark']=int(p['benchmark'])
    return p

def load_core(root):
    spec=importlib.util.spec_from_file_location('olc109_frozen_core',Path(root)/'source/src/core.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def write_decisions(out,decisions):
    arrays={name:np.array([d[name] for d in decisions]) for name in ('units','current_weights','raw_weights','weights')}
    arrays['k']=np.array([d['k'] for d in decisions],int)
    arrays['cash']=np.array([d['cash'] for d in decisions])
    np.savez_compressed(out/'DECISIONS.npz',**arrays)
    pd.DataFrame([dict(signal_idx=d['k'],signal_date=d['signal_date'],instruction_id=d['instruction_id'],
                       opportunity_used=d['meta'].get('opportunity_used',False),meta_json=json.dumps(d['meta']))
                  for d in decisions]).to_csv(out/'DECISIONS.csv',index=False)

def run(root,resume=False):
    root=Path(root).resolve();results=root/'results_stage3';results.mkdir(exist_ok=True)
    freeze=json.loads((root/'docs/STAGE3_FREEZE.json').read_text())
    protocol_hash=sha(root/'docs/STAGE3_PROTOCOL.md')
    assert protocol_hash==freeze['protocol_sha256']
    code_hashes={name:sha(root/name) for name in FINANCIAL_CODE}
    data_hashes={name:sha(root/name) for name in ('source/data/XETRA_EUR_ETF.npz','data/LIQUIDITY.npz')}
    cases=[(a,s) for a in ARMS for s in SCENARIOS]
    assert len(cases)==freeze['planned_unique_paths']==40
    mpath=results/'RUN_MANIFEST.json'
    if mpath.exists():
        if not resume:raise FileExistsError('Use --resume only with unchanged frozen inputs/code')
        manifest=json.loads(mpath.read_text())
        assert manifest['code_hashes']==code_hashes and manifest['data_hashes']==data_hashes
        assert manifest['protocol_sha256']==protocol_hash
    else:
        manifest=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                      protocol_sha256=protocol_hash,code_hashes=code_hashes,data_hashes=data_hashes,
                      planned_unique_paths=len(cases),completed_paths=0,primary_arm='CAPITAL_3H',adaptive_stage=True,prior_stage1_stage2_results_seen=True,drawdown_limit_active=False,
                      universe='XETRA_EUR_ETF_V3',data_revision=3,pristine_holdout=False,
                      prior_results_seen=True,fit_or_optimization=False,
                      python=platform.python_version(),numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__)
        mpath.write_text(json.dumps(manifest,indent=2)+'\n')
    p=load_panel(root);legacy=load_core(root)
    with np.load(root/'data/LIQUIDITY.npz',allow_pickle=False) as z:
        assert np.array_equal(z['names'],p['names']) and np.array_equal(z['dates'],p['dates'].values)
        turnover=z['turnover']
    monthly=decision_mask(p['dates'],'MONTHLY');weekly=decision_mask(p['dates'],'WEEKLY')
    begin=p['dates'].searchsorted('2020-03-02');finish=p['dates'].searchsorted('2026-10-30',side='right')
    keys=sorted({int(begin-1)}|set(np.flatnonzero(monthly & (np.arange(len(monthly))>=begin) & (np.arange(len(monthly))<finish-1)).tolist()))
    scores=[];annual=[];segments=[]
    with threadpool_limits(limits=1):
        print('Preparing causal features',flush=True)
        f=prepare_features(p,legacy,turnover)
        snapshots={}
        for seq,k in enumerate(keys,1):
            snapshots[k]=build_snapshot(p,f,k)
            if seq%10==0:print(f'Clusters {seq}/{len(keys)}',flush=True)
        payload=[{name:value for name,value in snapshots[k].items() if name!='rep_corr'} for k in keys]
        with gzip.GzipFile(filename=str(root/'data/STAGE3_SNAPSHOTS.json.gz'),mode='wb',mtime=0) as h:
            h.write(json.dumps(payload,separators=(',',':')).encode())
        np.savez_compressed(root/'data/STAGE3_REP_CORRELATIONS.npz',**{f'k_{k}':snapshots[k]['rep_corr'] for k in keys})
        pd.DataFrame([dict(signal_idx=k,date=str(p['dates'][k].date()),
                           history_eligible=int(f['eligible'][k].sum()),
                           liquid_eligible=int(f['liquid_eligible'][k].sum()),
                           groups=len(snapshots[k]['groups']),
                           groups_with_two_or_more=sum(g['size']>=2 for g in snapshots[k]['groups'])) for k in keys]).to_csv(results/'ELIGIBLE_AND_GROUP_COUNTS.csv',index=False)
        for seq,(arm,scenario) in enumerate(cases,1):
            path_id=f'{arm}__{scenario}';out=results/path_id
            if resume and (out/'METRICS.json').exists():
                meta=json.loads((out/'METRICS.json').read_text());daily=pd.read_csv(out/'DAILY.csv.gz')
                print(f'Resumed {seq}/{len(cases)} {path_id}',flush=True)
            else:
                ticket,impact,lag=SCENARIOS[scenario]
                risk=.15 if arm.endswith('RISK15') else (.20 if arm.endswith('RISK20') else None)
                guard_kind='EXIT63' if arm.endswith('EXIT63') else ('TRAIL15' if arm.endswith('TRAIL15') else None)
                mask=np.zeros(len(monthly),bool) if arm=='PASSIVE' else monthly
                result=simulate(p,f,make_policy(p,f,snapshots,arm),mask,legacy=legacy,
                                risk_target=risk,lag=lag,ticket=ticket,impact=impact,
                                guard_policy=make_guard(f,guard_kind) if guard_kind else None,
                                guard_mask=weekly if guard_kind else None)
                daily,orders=result['daily'],result['orders']
                metrics=legacy.portfolio_metrics(daily.nav_close,daily.date,10000.,daily.nav_open)
                years=metrics['days']/365.2425
                meta=dict(path_id=path_id,universe='XETRA_EUR_ETF',arm=arm,cadence='MONTHLY',
                          risk=('RISK'+str(round(100*risk))) if risk else 'RAW',scenario=scenario,
                          guard=guard_kind,currency='EUR',ticket=ticket,impact_bps=impact*10000,lag_extra=lag,
                          **metrics,orders=len(orders),trading_days=int(orders.date.nunique()),
                          trading_days_per_year=float(orders.date.nunique()/years),
                          alerts=len(result['alerts']),alerts_per_year=float(len(result['alerts'])/years),
                          actionable_instructions=int(orders.instruction_id.nunique()),
                          scheduled_decisions=len(result['decisions']),costs=float(orders.cost.sum()),
                          two_sided_turnover_per_year=float(orders.notional.sum()/daily.nav_close.mean()/years),
                          mean_exposure=float(daily.gross.mean()),mean_positions=float(daily.positions.mean()),
                          opportunity_decision_share=float(np.mean([d['meta'].get('opportunity_used',False) for d in result['decisions']])),
                          deferred_sessions=result['deferred_sessions'],max_self_financing_error=result['max_self_financing_error'])
                meta['numeric_target_pass']=bool(metrics['cagr']>=.30 and metrics['maxdd_sampled']>=-.25 and metrics['calmar']>=1.)
                meta['operational_pass']=bool(meta['trading_days_per_year']<=24.)
                meta['research_return_target_pass']=bool(metrics['cagr']>=.30)
                meta['drawdown_limit_active']=False
                out.mkdir(exist_ok=True)
                for name,frame in (('DAILY',daily),('ORDERS',orders)):
                    frame.to_csv(out/f'{name}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                ins=result['instructions'].copy()
                for col in ('target_weights','raw_weights'):ins[col]=ins[col].map(lambda x:json.dumps(list(x)))
                ins.to_csv(out/'INSTRUCTIONS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                write_decisions(out,result['decisions'])
                (out/'METRICS.json').write_text(json.dumps(meta,indent=2)+'\n')
                print(f'{seq}/{len(cases)} {path_id}: CAGR {100*meta["cagr"]:.2f}% DD {100*meta["maxdd_sampled"]:.2f}% days/y {meta["trading_days_per_year"]:.2f}',flush=True)
            scores.append(meta)
            dt=pd.to_datetime(daily.date);yy=dt.dt.year.to_numpy()
            for year in sorted(set(yy)):
                ix=np.flatnonzero(yy==year);initial=10000. if ix[0]==0 else float(daily.nav_close.iloc[ix[0]-1])
                mm=legacy.portfolio_metrics(daily.nav_close.iloc[ix],daily.date.iloc[ix],initial,daily.nav_open.iloc[ix])
                annual.append(dict(path_id=path_id,arm=arm,scenario=scenario,year=int(year),annual_return=mm['cumulative'],maxdd_in_year=mm['maxdd_sampled'],partial_year=year in (2020,2026)))
            for label,cond in (('2020',yy==2020),('2021_2024',(yy>=2021)&(yy<=2024)),('2025_2026',yy>=2025),('2021_2026',yy>=2021)):
                ix=np.flatnonzero(cond);initial=10000. if ix[0]==0 else float(daily.nav_close.iloc[ix[0]-1])
                mm=legacy.portfolio_metrics(daily.nav_close.iloc[ix],daily.date.iloc[ix],initial,daily.nav_open.iloc[ix])
                segments.append(dict(path_id=path_id,arm=arm,scenario=scenario,segment=label,**mm))
            pd.DataFrame(scores).to_csv(results/'SCORECARD.csv',index=False)
            manifest['completed_paths']=len(scores)
            mpath.write_text(json.dumps(manifest,indent=2)+'\n')
        pd.DataFrame(annual).to_csv(results/'ANNUAL_RETURNS.csv',index=False)
        pd.DataFrame(segments).to_csv(results/'DESCRIPTIVE_SEGMENTS.csv',index=False)
    assert {name:sha(root/name) for name in FINANCIAL_CODE}==code_hashes
    assert {name:sha(root/name) for name in data_hashes}==data_hashes
    manifest.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_paths=len(scores),
                    snapshot_sha256=sha(root/'data/STAGE3_SNAPSHOTS.json.gz'),correlation_sha256=sha(root/'data/STAGE3_REP_CORRELATIONS.npz'))
    mpath.write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'COMPLETE: {len(scores)} paths, {sum(m["numeric_target_pass"] for m in scores)} numeric passes',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root');parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();run(args.root,args.resume)
