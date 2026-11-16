"""Frozen complete-plan experiment: monthly mature fits and native accounts."""
from __future__ import annotations
import argparse
import datetime
import gzip
import json
from pathlib import Path
import platform
import sys
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

ROOT=Path(__file__).resolve().parents[1]
for source in (ROOT.parent/'olc111/src',ROOT.parent/'olc110/src'):
    if str(source) not in sys.path:sys.path.append(str(source))
import run_olc111 as previous
from research_pipeline import execution_panel
from cycle_core import HEADS, PlanExecutor, build_bundle, build_bank, plan_features
from cycle_engine import simulate
from cycle_model import ValueModel, canonical_hash, model_hash, fit_head

ARMS=('BASE','STATIC_75','MEAN_CYCLE','RIDGE_CYCLE','TREE_CYCLE')
SCENARIOS={'NEXT_CLOSE':(1.,.0015,0),'DOUBLE_COST':(2.,.003,0),'DELAY1_CLOSE':(1.,.0015,1)}
FIT_OPTIONS=dict(min_dates=504,min_months=24,min_blocks=12,n_boot=32,seed=114,penalty=1.)
MIN_ACTIVATION_IDX=865
ARTIFACTS=('DAILY.csv.gz','ORDERS.csv.gz','INSTRUCTIONS.csv.gz','DECISIONS.npz',
           'DECISIONS_META.json.gz','POLICY_TRACE.csv.gz','PLAN_VALUES.csv.gz',
           'ELIGIBLE_STATES.jsonl.gz','PLAN_SUMMARIES.json.gz')


class MonthlyCycleCache:
    def __init__(self,bank,dates,begin,*,folder=None,provenance=None,fit_options=None,
                 min_activation_idx=MIN_ACTIVATION_IDX):
        self.bank=bank;self.dates=pd.DatetimeIndex(dates);self.begin=int(begin)
        months=self.dates.to_period('M');first=np.r_[True,months[1:]!=months[:-1]]
        self.cutoffs=np.maximum(np.maximum.accumulate(np.where(first,np.arange(len(dates)),0)),self.begin-1)
        self.folder=None if folder is None else Path(folder)
        if self.folder is not None:self.folder.mkdir(parents=True,exist_ok=True)
        self.provenance=provenance;self.options=dict(FIT_OPTIONS,**(fit_options or {}))
        self.min_activation_idx=int(min_activation_idx);self.cache={}
    def cutoff(self,k):return int(self.cutoffs[k])
    def get(self,k):
        cutoff=self.cutoff(k)
        if cutoff in self.cache:return self.cache[cutoff]
        path=None if self.folder is None else self.folder/f'FIT_{cutoff:06d}.json.gz'
        if path is not None and path.exists():
            stored=previous._read_json(path);digest=stored.pop('payload_sha256',None)
            if canonical_hash(stored)!=digest:raise ValueError('FIT_CACHE_PAYLOAD_HASH')
            if (stored['provenance']!=self.provenance or stored['cutoff']!=cutoff or
                stored['fit_options']!=self.options):raise ValueError('FIT_CACHE_PROVENANCE')
            fitted={}
            for head in HEADS:
                record=stored['heads'][head]
                if record is None:fitted[head]=None;continue
                models={name:ValueModel.from_dict(value) for name,value in record['models'].items()}
                if set(models)!=set(('MEAN','RIDGE','TREE')):raise ValueError('FIT_CACHE_MODELS')
                if any(model_hash(model)!=record['hashes'][name] for name,model in models.items()):
                    raise ValueError('FIT_CACHE_MODEL_HASH')
                if record['meta']['max_terminal_idx']>=cutoff:raise ValueError('FIT_CACHE_MATURITY')
                fitted[head]=dict(models=models,meta=record['meta'],hashes=record['hashes'])
        else:
            fitted={};exported={}
            for head in HEADS:
                b=self.bank[head]
                value=fit_head(b['X'],b['y'],b['signal_idx'],b['terminal_idx'],cutoff,self.dates,**self.options)
                fitted[head]=value
                exported[head]=None if value is None else dict(models={n:m.to_dict() for n,m in value['models'].items()},
                                                              hashes=value['hashes'],meta=value['meta'])
            if path is not None:
                stored=dict(cutoff=cutoff,date=str(self.dates[cutoff].date()),provenance=self.provenance,
                            fit_options=self.options,heads=exported,source='normal_cost_next_close_complete_plan_bank')
                stored['payload_sha256']=canonical_hash(stored);previous._write_json(path,stored)
        self.cache[cutoff]=fitted;return fitted
    def prepare(self):
        first={head:None for head in HEADS};raw=None
        for cutoff in np.unique(self.cutoffs[self.begin-1:len(self.dates)-1]):
            fitted=self.get(int(cutoff))
            for head in HEADS:
                if fitted[head] is not None and first[head] is None:
                    first[head]=dict(index=int(cutoff),date=str(self.dates[cutoff].date()))
            if raw is None and all(fitted[head] is not None for head in HEADS):raw=int(cutoff)
        ready=None if raw is None else max(raw,self.min_activation_idx)
        if ready is not None and ready>=len(self.dates)-1:ready=None
        post=None if ready is None else max(self.begin,ready+1)
        return dict(first_ready_by_head=first,raw_all_heads_first_ready_idx=raw,
                    minimum_activation_idx=self.min_activation_idx,all_heads_first_ready_idx=ready,
                    all_heads_first_ready_date=None if ready is None else str(self.dates[ready].date()),
                    postwarmup_start_idx=post,postwarmup_start_date=None if post is None else str(self.dates[post].date()),
                    postwarmup_denominator='each_path_actual_close_nav_immediately_before_start',
                    fit_options=self.options,fitted_calendar_cutoffs=sorted(self.cache),
                    monthly_cutoff='first_panel_date_of_month_clipped_to_begin_minus_one')


def select_plan(predictions,names):
    legal=[p for p in predictions if np.isfinite(p['mean']) and np.isfinite(p['lower']) and p['mean']>0 and p['lower']>0]
    return min(legal,key=lambda p:(-p['lower'],p['head'],str(names[p['asset']]))) if legal else None


class CyclePolicy:
    def __init__(self,bundle,arm,fit_cache):
        if arm not in ARMS:raise ValueError('ARM')
        self.bundle=bundle;self.arm=arm;self.fit_cache=fit_cache
        self.dates=pd.DatetimeIndex(bundle['panel']['dates']);self.names=np.asarray(bundle['panel']['names'])
        self.trace=[];self.values=[];self.eligible_states=[];self.plans=[];self.active=None
    def export_plans(self):
        return [dict(item['executor'].summary,selection=item['selection'],trace=item['executor'].trace,
                     right_censored=bool(item['executor'].active)) for item in self.plans]
    def __call__(self,k,current,context):
        row=dict(k=int(k),date=str(self.dates[k].date()),arm=self.arm,initial=bool(context['initial']),
                 scheduled=bool(context['scheduled']),gross=float(np.sum(current)),cash=float(context['cash']),
                 nav=float(context['nav']),positions=int((context['units']>1e-12).sum()),
                 busy=bool(context['pending'] is not None or context['queued']),fit_cutoff_idx=self.fit_cache.cutoff(k),
                 model_ready_all=False,action='HOLD',status='HOLD',active_plan=None,chosen_asset=None)
        def finish(answer,status,action=None):
            row['status']=status
            if action is not None:row['action']=action
            if self.active is not None:
                row.update(active_plan=self.active.summary['plan'],plan_phase=self.active.summary['phase'])
            self.trace.append(row)
            if answer is not None:
                answer=dict(answer);answer['meta']=dict(answer.get('meta',{}),arm=self.arm,status=status)
            return answer
        def baseline(status):
            scale=.75 if self.arm=='STATIC_75' else 1.
            action='INITIAL' if context['initial'] else 'SCHEDULED'
            return finish(dict(weights=np.array(self.bundle['targets'][k],copy=True)*scale,
                               reason=action,force=bool(context['initial'])),status,action)
        if context['initial']:return baseline('BASE_INITIAL')
        # Handoff has priority over pending status, readiness and opportunities.
        if context['scheduled']:
            if self.active is not None:
                answer=self.active(k,current,context)
                row['active_plan']=self.active.summary['plan'];row['plan_phase']=self.active.summary['phase']
                self.active=None
                return finish(answer,'MONTHLY_HANDOFF','SCHEDULED')
            return baseline('BASE_MONTHLY')
        if self.arm in ('BASE','STATIC_75'):return finish(None,'BASE_HOLD')
        if self.active is not None:
            answer=self.active(k,current,context)
            return finish(answer,'PLAN_ACTIVE',None if answer is None else answer['reason'])
        fitted=self.fit_cache.get(k)
        ready=k>=self.fit_cache.min_activation_idx and all(fitted[h] is not None for h in HEADS)
        row['model_ready_all']=ready
        if not ready:return finish(None,'WARMUP_HOLD')
        if row['busy']:return finish(None,'BUSY')
        held=np.flatnonzero(context['units']>1e-12)
        if not len(held):return finish(None,'CASH_WAIT_MONTHLY')
        self.eligible_states.append(dict(k=int(k),date=str(self.dates[k].date()),asset_indices=held.tolist(),
            units=np.asarray(context['units'])[held].tolist(),weights=np.asarray(current)[held].tolist(),
            cash=float(context['cash']),nav=float(context['nav']),fit_cutoff_idx=row['fit_cutoff_idx']))
        name=self.arm.removesuffix('_CYCLE');predictions=[]
        for asset in sorted(held,key=lambda j:str(self.names[j])):
            for head in HEADS:
                x=plan_features(self.bundle,k,current,context['nav'],int(asset),head)
                record=dict(k=int(k),date=str(self.dates[k].date()),arm=self.arm,head=head,asset=int(asset),
                            isin=str(self.names[asset]),fit_cutoff_idx=row['fit_cutoff_idx'],valid=x is not None)
                if x is None:
                    self.values.append(record);continue
                result=fitted[head];prediction=result['models'][name].predict(x)
                scale=result['meta']['scaler'];z=(x-np.asarray(scale['mean']))/np.asarray(scale['scale'])
                outside=(x<np.asarray(result['meta']['feature_min']))|(x>np.asarray(result['meta']['feature_max']))
                record.update(prediction,features=json.dumps(x.tolist(),separators=(',',':')),
                              model_sha256=result['hashes'][name],max_abs_standardized=float(np.abs(z).max()),
                              outside_training_range=int(outside.sum()))
                self.values.append(record);predictions.append(record)
        choice=select_plan(predictions,self.names)
        if choice is None:return finish(None,'HOLD_BUFFER' if predictions else 'HOLD_UNSUPPORTED')
        self.active=PlanExecutor(self.bundle,choice['head'],choice['asset'],k)
        selection={key:value for key,value in choice.items() if key!='features'}
        self.plans.append(dict(executor=self.active,selection=selection))
        row.update(chosen_asset=choice['asset'],selected_head=choice['head'],selected_mean=choice['mean'],
                   selected_lower=choice['lower'],model_sha256=choice['model_sha256'])
        answer=self.active(k,current,context)
        answer['meta'].update(fit_cutoff_idx=row['fit_cutoff_idx'],model_sha256=choice['model_sha256'],
                              selected_mean=choice['mean'],selected_lower=choice['lower'])
        return finish(answer,'PLAN_START',answer['reason'])


def summarize_path(bundle,arm,scenario,result,readiness,plans):
    ticket,impact,lag=SCENARIOS[scenario];daily=result['daily'];orders=result['orders']
    financial=previous.performance_window(bundle['core'],daily);years=financial['days']/365.2425
    nav_by_date=daily.set_index('date').nav_open
    turnover=float((orders.notional.to_numpy()/nav_by_date.loc[orders.date].to_numpy()).sum()) if len(orders) else 0.
    metrics=dict(path_id=f'{arm}__{scenario}',arm=arm,scenario=scenario,fill='CLOSE',lag=lag,currency='EUR',
        ticket=ticket,impact_bps=impact*10000,**financial,orders=len(orders),trading_days=int(orders.date.nunique()),
        costs=float(orders.cost.sum()),instructions=len(result['instructions']),trading_days_per_year=float(orders.date.nunique()/years),
        two_sided_turnover_per_year=turnover/years,mean_exposure=float(daily.gross.mean()),
        mean_cash_share=float((1-daily.gross).mean()),mean_positions=float(daily.positions.mean()),
        full_cash_days=int((daily.gross<=1e-8).sum()),deferred_sessions=result['deferred_sessions'],
        max_self_financing_error=result['max_self_financing_error'],cagr_target_pass=financial['cagr']>=.30,
        drawdown_sampling='CLOSE_PRE_POST_FEES',post_warmup_start_idx=readiness['postwarmup_start_idx'],
        plans_started=len(plans),plans_handed_off=sum(p['handoff_idx'] is not None for p in plans),
        plans_right_censored=sum(p['right_censored'] for p in plans),
        plan_signal_nonoverlap_42=previous.separated_episodes([p['signal_idx'] for p in plans],42),
        redeploy_attempts=sum(p['entry_attempt_idx'] is not None for p in plans),
        redeploy_no_candidate=sum(p['entry_attempt_idx'] is not None and p['entry_candidate_idx'] is None for p in plans),
        redeploy_buy_instructions=int(orders.loc[(orders.reason=='REDEPLOY_ENTRY')&(orders.side=='BUY'),'instruction_id'].nunique()))
    if readiness['postwarmup_start_idx'] is not None:
        post=previous.performance_window(bundle['core'],daily,start_idx=readiness['postwarmup_start_idx'])
        metrics.update({f'post_{key}':value for key,value in post.items()})
        metrics['post_warmup_initial_nav']=post['initial_nav']
    for head in HEADS:
        chosen=[p for p in plans if p['head']==head]
        metrics[f'{head.lower()}_plans']=len(chosen)
        complete=[p['signal_idx'] for p in chosen if p['signal_idx']+42<=int(daily.k.iloc[-1])]
        metrics[f'{head.lower()}_complete_nonoverlap_42']=previous.separated_episodes(complete,42)
    return metrics


def save_completed_path(folder,result,policy,metrics,freeze_sha):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    for key,name in [('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz')]:previous._csv(result[key],folder/name)
    instructions=result['instructions'].copy()
    for column in ('target_weights','raw_weights','action_indices','meta'):
        if column in instructions:instructions[column]=instructions[column].map(lambda value:previous._json_bytes(value).decode())
    previous._csv(instructions,folder/'INSTRUCTIONS.csv.gz')
    decisions=result['decisions']
    arrays={field:np.array([d[field] for d in decisions]) for field in ('units','current_units','current_weights','raw_weights','weights')}
    arrays.update(k=np.array([d['k'] for d in decisions],int),cash=np.array([d['cash'] for d in decisions],float))
    np.savez_compressed(folder/'DECISIONS.npz',**arrays)
    previous._write_json(folder/'DECISIONS_META.json.gz',[{key:value for key,value in d.items() if not isinstance(value,np.ndarray)} for d in decisions])
    previous._csv(pd.DataFrame(policy.trace),folder/'POLICY_TRACE.csv.gz')
    values=pd.DataFrame(policy.values)
    if values.empty:values=pd.DataFrame(columns=['k','date','arm','head','asset','isin','fit_cutoff_idx','valid','mean','lower','features','model_sha256','max_abs_standardized','outside_training_range'])
    previous._csv(values,folder/'PLAN_VALUES.csv.gz')
    raw=b''.join(previous._json_bytes(row)+b'\n' for row in policy.eligible_states)
    (folder/'ELIGIBLE_STATES.jsonl.gz').write_bytes(gzip.compress(raw,mtime=0))
    previous._write_json(folder/'PLAN_SUMMARIES.json.gz',policy.export_plans())
    payload=dict(metrics,experiment_freeze_sha256=freeze_sha)
    receipt=dict(path_id=metrics['path_id'],arm=metrics['arm'],scenario=metrics['scenario'],freeze_sha256=freeze_sha,
                 artifacts={name:previous.sha(folder/name) for name in ARTIFACTS},metrics_payload_sha256=canonical_hash(payload))
    previous._write_json(folder/'PATH_RECEIPT.json',receipt)
    previous._write_json(folder/'METRICS.json',payload)
    return payload


def load_completed_path(folder,arm,scenario,freeze_sha):
    folder=Path(folder);receipt=previous._read_json(folder/'PATH_RECEIPT.json');metrics=previous._read_json(folder/'METRICS.json')
    if (receipt['path_id']!=f'{arm}__{scenario}' or receipt['arm']!=arm or receipt['scenario']!=scenario or
        receipt['freeze_sha256']!=freeze_sha or metrics['experiment_freeze_sha256']!=freeze_sha):raise ValueError('PATH_RECEIPT_IDENTITY')
    if set(receipt['artifacts'])!=set(ARTIFACTS):raise ValueError('PATH_RECEIPT_ARTIFACTS')
    if canonical_hash(metrics)!=receipt['metrics_payload_sha256']:raise ValueError('PATH_RECEIPT_METRICS')
    for name,digest in receipt['artifacts'].items():
        if previous.sha(folder/name)!=digest:raise ValueError('PATH_RECEIPT_HASH:'+name)
    return metrics,pd.read_csv(folder/'DAILY.csv.gz',float_precision='round_trip')


def compare_control(root,arm,scenario,result):
    if arm not in ('BASE','STATIC_75') or scenario=='DELAY1_CLOSE':return None
    folder=Path(root).parent/'olc111/results'/f'{arm}__{scenario}'
    for key,name in [('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz')]:
        expected=pd.read_csv(folder/name,float_precision='round_trip')
        pd.testing.assert_frame_equal(result[key].reset_index(drop=True),expected,check_exact=True,check_dtype=False)
    return dict(arm=arm,scenario=scenario,daily_exact=True,orders_exact=True,
                daily_source_sha256=previous.sha(folder/'DAILY.csv.gz'),orders_source_sha256=previous.sha(folder/'ORDERS.csv.gz'))


def prequential_forecasts(bundle,bank,cache):
    rows=[];dates=pd.DatetimeIndex(bundle['panel']['dates'])
    for head in HEADS:
        b=bank[head]
        for i,k in enumerate(b['signal_idx']):
            fitted=cache.get(int(k));ready=k>=cache.min_activation_idx and all(fitted[h] is not None for h in HEADS)
            record=fitted[head]
            for name in ('MEAN','RIDGE','TREE'):
                pred=None if record is None else record['models'][name].predict(b['X'][i])
                rows.append(dict(head=head,arm=name,signal_idx=int(k),signal_date=str(dates[k].date()),
                    terminal_idx=int(b['terminal_idx'][i]),asset_idx=int(b['asset_idx'][i]),
                    isin=str(bundle['panel']['names'][b['asset_idx'][i]]),fit_cutoff_idx=cache.cutoff(k),
                    head_ready=record is not None,all_heads_ready=ready,outcome=float(b['y'][i]),
                    prediction=None if pred is None else pred['mean'],lower=None if pred is None else pred['lower'],
                    positive_buffer=pred is not None and pred['mean']>0 and pred['lower']>0,
                    model_sha256=None if record is None else record['hashes'][name]))
    return pd.DataFrame(rows)


def forecast_diagnostics(ledger):
    rows=[];bins=[];ranking=[]
    selected=ledger.loc[ledger.all_heads_ready&ledger.prediction.notna()]
    for (head,arm),frame in selected.groupby(['head','arm'],sort=True):
        weights=previous._date_weights(frame);error=(frame.prediction-frame.outcome).to_numpy()
        positive=frame.loc[frame.positive_buffer]
        rows.append(dict(head=head,arm=arm,n_rows=len(frame),n_dates=int(frame.signal_idx.nunique()),
            nonoverlap_42=previous.separated_episodes(frame.signal_idx,42),mse=float(weights@(error**2)),bias=float(weights@error),
            mean_prediction=float(weights@frame.prediction.to_numpy()),mean_outcome=float(weights@frame.outcome.to_numpy()),
            positive_buffer_rows=len(positive),positive_buffer_dates=int(positive.signal_idx.nunique()),
            positive_buffer_nonoverlap_42=previous.separated_episodes(positive.signal_idx,42),
            positive_buffer_realized_mean=float(previous._date_weights(positive)@positive.outcome.to_numpy()) if len(positive) else None))
        labels=pd.qcut(frame.prediction,5,labels=False,duplicates='drop')
        if labels.isna().all():labels=pd.Series(0,index=frame.index)
        for label,group in frame.groupby(labels,observed=True):
            w=previous._date_weights(group)
            bins.append(dict(head=head,arm=arm,bin=int(label)+1,n_rows=len(group),n_dates=int(group.signal_idx.nunique()),
                mean_prediction=float(w@group.prediction.to_numpy()),mean_outcome=float(w@group.outcome.to_numpy())))
    mse={(r['head'],r['arm']):r['mse'] for r in rows}
    for row in rows:
        for reference in ('MEAN','RIDGE'):
            row[f'mse_delta_vs_{reference.lower()}']=row['mse']-mse[(row['head'],reference)]
    # A reference-state forecast diagnostic, never an additive account return.
    for (arm,k),group in selected.groupby(['arm','signal_idx'],sort=True):
        legal=group.loc[group.positive_buffer].sort_values(['lower','head','isin'],ascending=[False,True,True])
        chosen=None if legal.empty else legal.iloc[0]
        best=max(0.,float(group.outcome.max()));actual=0. if chosen is None else float(chosen.outcome)
        ranking.append(dict(arm=arm,signal_idx=int(k),selected_head=None if chosen is None else chosen['head'],
            selected_asset=None if chosen is None else int(chosen.asset_idx),selected_realized_advantage=actual,
            hindsight_best_advantage=best,ranking_regret=best-actual,chosen=chosen is not None))
    return pd.DataFrame(rows),pd.DataFrame(bins),pd.DataFrame(ranking)


def verify_experiment_freeze(root):
    root=Path(root);freeze=previous._read_json(root/'docs/EXPERIMENT_FREEZE.json')
    for section in ('code_hashes','input_hashes'):
        for path,digest in freeze[section].items():
            if previous.sha(root/path)!=digest:raise ValueError('FREEZE_HASH_MISMATCH:'+path)
    if previous.sha(root/'docs/DESIGN_AND_PROTOCOL.md')!=freeze['protocol_sha256']:raise ValueError('FREEZE_PROTOCOL')
    if freeze['arms']!=list(ARMS) or freeze['scenarios']!=list(SCENARIOS) or freeze['planned_paths']!=15:raise ValueError('FREEZE_MATRIX')
    return freeze


def run(root,resume=False):
    root=Path(root).resolve();freeze=verify_experiment_freeze(root);freeze_sha=previous.sha(root/'docs/EXPERIMENT_FREEZE.json')
    results=root/'results';results.mkdir(exist_ok=True);manifest_path=results/'RUN_MANIFEST.json'
    if manifest_path.exists():
        if not resume:raise FileExistsError('Use --resume under exact freeze')
        manifest=previous._read_json(manifest_path)
        if manifest['freeze_sha256']!=freeze_sha:raise ValueError('RUN_FREEZE_MISMATCH')
    else:
        manifest=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=freeze_sha,
            arms=list(ARMS),scenarios=list(SCENARIOS),planned_paths=15,completed_paths=0,completed_path_ids=[],
            primary_arm='TREE_CYCLE',fit_options=FIT_OPTIONS,pristine_holdout=False,all_results_exploratory=True,
            bootstrap_lower_is_calibrated_confidence=False,stress_model_refits=False,python=platform.python_version(),
            numpy=np.__version__,pandas=pd.__version__)
    previous._write_json(manifest_path,manifest)
    with threadpool_limits(limits=1):
        bundle=build_bundle(root)
        # Load sealed banks directly: runner never regenerates training outcomes.
        bank={head:dict(np.load(root/f'data/BANK_{head}.npz',allow_pickle=False)) for head in HEADS}
        cache=MonthlyCycleCache(bank,bundle['panel']['dates'],bundle['begin'],folder=results/'FITS',provenance=freeze_sha)
        print('OLC114: fitting monthly mature complete-plan heads',flush=True)
        readiness=cache.prepare();previous._write_json(results/'FIT_READINESS.json',readiness)
        print('OLC114 readiness:',readiness['all_heads_first_ready_date'],flush=True)
        ledger=prequential_forecasts(bundle,bank,cache)
        previous._csv(ledger,results/'PREQUENTIAL_FORECASTS.csv.gz')
        fs,fb,fr=forecast_diagnostics(ledger)
        previous._csv(fs,results/'FORECAST_SCORES.csv');previous._csv(fb,results/'FORECAST_BINS.csv')
        previous._csv(fr,results/'FORECAST_RANKING.csv.gz')
        scores=[];annual=[];common=[];drawdowns=[];replications=[]
        panel=execution_panel(bundle['panel'],'CLOSE')
        for arm in ARMS:
            for scenario,(ticket,impact,lag) in SCENARIOS.items():
                folder=results/f'{arm}__{scenario}'
                if resume and (folder/'METRICS.json').exists():
                    metrics,daily=load_completed_path(folder,arm,scenario,freeze_sha)
                    result=dict(daily=daily,orders=pd.read_csv(folder/'ORDERS.csv.gz',float_precision='round_trip'))
                else:
                    policy=CyclePolicy(bundle,arm,cache)
                    result=simulate(panel,bundle['f'],lambda k,w:bundle['targets'][k],bundle['monthly'],
                        legacy=bundle['core'],account_policy=policy,ticket=ticket,impact=impact,lag=lag,
                        start=str(panel['dates'][bundle['begin']].date()),end=str(panel['dates'][-1].date()))
                    compare_control(root,arm,scenario,result)
                    metrics=summarize_path(bundle,arm,scenario,result,readiness,policy.export_plans())
                    metrics=save_completed_path(folder,result,policy,metrics,freeze_sha);daily=result['daily']
                replication=compare_control(root,arm,scenario,result)
                if replication is not None:replications.append(replication)
                scores.append(metrics);annual.extend(previous.annual_rows(bundle,daily,arm,scenario))
                drawdowns.extend(previous.drawdown_rows(daily,arm,scenario))
                common.append(dict(path_id=metrics['path_id'],arm=arm,scenario=scenario,
                    **previous.performance_window(bundle['core'],daily,start_idx=readiness['postwarmup_start_idx'])))
                previous._csv(pd.DataFrame(scores),results/'SCORES.csv')
                manifest.update(completed_paths=len(scores),completed_path_ids=[r['path_id'] for r in scores])
                previous._write_json(manifest_path,manifest)
                print(f"{len(scores)}/15 {metrics['path_id']}: CAGR {metrics['cagr']:.6f}, DD {metrics['maxdd_sampled']:.6f}, plans {metrics['plans_started']}",flush=True)
        previous._csv(pd.DataFrame(annual),results/'ANNUAL_RETURNS.csv')
        previous._csv(pd.DataFrame(common),results/'COMMON_POST_WARMUP.csv')
        previous._csv(pd.DataFrame(drawdowns),results/'DRAWDOWN_EPISODES.csv')
        previous._write_json(results/'CONTROL_REPLICATION.json',replications)
        verify_experiment_freeze(root)
        manifest.update(completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_paths=15)
        previous._write_json(manifest_path,manifest)
    return scores


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();run(args.root,args.resume)
