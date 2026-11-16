"""Finite position plans shared verbatim between native labels and deployment."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from cycle_engine import simulate

ROOT=Path(__file__).resolve().parents[1]
for _source in (ROOT.parent/'olc111/src',ROOT.parent/'olc110/src'):
    if str(_source) not in sys.path:sys.path.append(str(_source))
from research_pipeline import basket_stats, execution_panel, feature_monthly_schedule, _valid_valuation_path
from dedup_selectors import pair_corr
HEADS=('PARK','REDEPLOY')
FEATURE_DIMS={'PARK':8,'REDEPLOY':12}


def candidate_for(bundle,k,retained):
    retained=tuple(int(j) for j in retained)
    for candidate in bundle['selected_order'][k]:
        candidate=int(candidate)
        if candidate in retained:continue
        if all(pair_corr(bundle['f'],k,candidate,j)<=.85+1e-12 for j in retained):
            return candidate
    return None


def plan_features(bundle,k,current,nav,asset,head):
    if head not in HEADS:raise ValueError('PLAN_HEAD')
    current=np.asarray(current,float)
    if not np.isfinite(nav) or nav<=0 or current[asset]<=1e-12:return None
    own=np.zeros(len(current));own[asset]=1.
    held=basket_stats(bundle['f'],k,own)
    retained=current.copy();retained[asset]=0.
    other=basket_stats(bundle['f'],k,retained)
    monthly=np.flatnonzero(bundle.get('feature_monthly',bundle['monthly']))
    future=monthly[monthly>k]
    if held is None or other is None or not len(future):return None
    x=[held['nm21'],held['nm63'],held['ratio'],held['vol63']*np.sqrt(252.),
       current[asset],other['nm21'],(int(future[0])-k)/21.,1./nav]
    if head=='REDEPLOY':
        try:candidate=candidate_for(bundle,k,np.flatnonzero(retained>1e-12))
        except ValueError as exc:
            if str(exc)=='CORRELATION_WINDOW':return None
            raise
        extra=[0.,0.,0.]
        if candidate is not None:
            weights=np.zeros(len(current));weights[candidate]=1.
            stats=basket_stats(bundle['f'],k,weights)
            if stats is None:return None
            extra=[1.,stats['nm21']-held['nm21'],np.log(stats['vol63']/held['vol63'])]
        weeks=np.flatnonzero(bundle['weekly']);weeks=weeks[weeks>k+1]
        if not len(weeks):return None
        x.extend(extra+[(int(weeks[0])-k)/5.])
    x=np.asarray(x,float)
    return x if np.isfinite(x).all() else None


class PlanExecutor:
    """One sale, at most one weekly selection, then mandatory monthly handoff.

    Trace is transition-only (including changed pending status), not a dense
    copy of every idle close. Global identities are preserved under subsetting.
    """
    def __init__(self,bundle,head,asset,signal_idx,local_ids=None):
        if head not in HEADS:raise ValueError('PLAN_HEAD')
        self.bundle=bundle;self.head=head;self.asset=int(asset);self.signal_idx=int(signal_idx)
        self.ids=np.arange(len(bundle['panel']['names'])) if local_ids is None else np.asarray(local_ids,int)
        if len(set(self.ids.tolist()))!=len(self.ids) or self.asset not in self.ids:raise ValueError('PLAN_LOCAL_IDS')
        self.local_asset=int(np.flatnonzero(self.ids==self.asset)[0]);self.active=True;self.trace=[]
        self.summary=dict(plan=f'{head}:{self.asset}:{self.signal_idx}',head=head,asset=self.asset,
            signal_idx=self.signal_idx,sale_complete_idx=None,entry_attempt_idx=None,entry_candidate_idx=None,
            handoff_idx=None,phase='NEW')
        self._pending=None
    def _record(self,k,event,**data):
        self.trace.append(dict(k=int(k),event=event,**data))
    def __call__(self,k,current,context):
        # Even a still-pending sale/entry yields immediately to the native full
        # scheduled instruction; the engine retains its normal maturation rules.
        if context.get('scheduled',False) or self.bundle['monthly'][k]:
            if self.active:
                self.active=False;self.summary.update(handoff_idx=int(k),phase='HANDED_OFF')
                self._record(k,'HANDOFF',pending=bool(context.get('pending') or context.get('queued')))
            return dict(weights=np.asarray(self.bundle['targets'][k])[self.ids].copy(),reason='SCHEDULED',force=False,
                        meta=dict(plan=self.summary['plan'],event='HANDOFF'))
        if not self.active:return None
        busy=bool(context.get('pending') or context.get('queued'))
        if busy!=self._pending:
            self._record(k,'PENDING_STATUS',pending=busy);self._pending=busy
        if self.summary['phase']=='NEW':
            if k!=self.signal_idx or busy:raise ValueError('PLAN_INITIAL_STATE')
            if np.asarray(context['units'])[self.local_asset]<=1e-12:raise ValueError('PLAN_ASSET_NOT_HELD')
            self.summary['phase']='SELL_PENDING'
            mask=np.zeros(len(current),bool);mask[self.local_asset]=True
            self._record(k,'SALE_INSTRUCTION',asset=self.asset)
            return dict(weights=np.zeros(len(current)),action_mask=mask,sell_only=True,force=True,
                        reason=f'{self.head}_SALE',meta=dict(plan=self.summary['plan'],asset=self.asset))
        if self.summary['sale_complete_idx'] is None:
            last=int(context['last_sell_idx'][self.local_asset])
            if context['units'][self.local_asset]<=1e-12 and last>self.signal_idx:
                self.summary.update(sale_complete_idx=last,phase='WAIT_WEEKLY' if self.head=='REDEPLOY' else 'PARKED')
                self._record(k,'SALE_CONFIRMED',sale_complete_idx=last)
        sale_idx=self.summary['sale_complete_idx']
        if (self.head=='REDEPLOY' and sale_idx is not None and self.summary['entry_attempt_idx'] is None
                and k>sale_idx and self.bundle['weekly'][k] and not busy):
            retained=self.ids[np.asarray(context['units'])>1e-12]
            candidate=candidate_for(self.bundle,k,retained)
            self.summary.update(entry_attempt_idx=int(k),entry_candidate_idx=candidate,phase='WAIT_HANDOFF')
            self._record(k,'ENTRY_ATTEMPT',candidate=candidate)
            if candidate is None:return None
            if candidate not in self.ids:raise ValueError('CANDIDATE_OUTSIDE_SUBSET')
            j=int(np.flatnonzero(self.ids==candidate)[0]);weights=np.zeros(len(current));mask=np.zeros(len(current),bool)
            mask[j]=True;weights[j]=float(context['cash'])/float(context['nav'])
            self._record(k,'ENTRY_INSTRUCTION',candidate=candidate,cash=float(context['cash']),nav=float(context['nav']),target=float(weights[j]))
            return dict(weights=weights,action_mask=mask,force=True,reason='REDEPLOY_ENTRY',
                        meta=dict(plan=self.summary['plan'],candidate=candidate))
        return None


def counterfactual_group(bundle,k,state,horizon=42):
    terminal=int(k+horizon)
    group=dict(status='OK',signal_idx=int(k),terminal_idx=terminal,records=[],events={})
    p=bundle['panel'];f=bundle['f'];monthly=bundle['monthly'];targets=bundle['targets']
    if terminal>=len(p['dates']):return dict(group,status='RIGHT_EDGE')
    if state.get('busy',False) or state.get('pending') is not None or state.get('queued'):
        return dict(group,status='BUSY_STATE')
    if monthly[k]:return dict(group,status='SCHEDULED_STATE')
    units=np.asarray(state['units'],float);held=np.flatnonzero(units>1e-12)
    if not len(held):return dict(group,status='NO_HOLDINGS')
    marks=np.asarray(f['C'][k])
    if np.any(~np.isfinite(marks[held]) | (marks[held]<=0)):
        return dict(group,status='CENSORED_MISSING_MARK',failed_branch='SEED')
    nav=float(state['cash']+np.nansum(units*marks))
    current=units*np.where(np.isfinite(marks),marks,0.)/nav
    features={(head,int(asset)):plan_features(bundle,k,current,nav,int(asset),head) for asset in held for head in HEADS}
    if any(x is None for x in features.values()):return dict(group,status='INVALID_FEATURES')
    ids=set(held.tolist())
    # Union is an execution optimization only. Features and later candidate
    # choices access global data solely at their own causal decision index.
    for j in range(k+1,terminal):
        if monthly[j]:ids.update(np.flatnonzero(targets[j]>0).tolist())
        if bundle['weekly'][j]:ids.update(bundle['selected_order'][j])
    ids=np.array(sorted(ids),int)
    sp=dict(dates=p['dates'],names=np.asarray(p['names'])[ids],O=np.asarray(p['C'])[:,ids],
            C=np.asarray(p['C'])[:,ids],observed=np.asarray(p['observed'])[:,ids],
            open_observed=np.asarray(p['observed'])[:,ids])
    sf=dict(C=np.asarray(f['C'])[:,ids]);seed=dict(units=units[ids].copy(),cash=float(state['cash']))
    outcomes={};errors=[]
    branches=[('BASE',None,None)]+[(f'{head}:{asset}',head,asset) for head,asset in features]
    for label,head,asset in branches:
        executor=PlanExecutor(bundle,head,asset,k,ids) if head else None
        try:
            result=simulate(sp,sf,lambda j,w:targets[j,ids],monthly,legacy=bundle['core'],
                account_policy=executor,initial_state=seed,issue_initial=head is not None,
                allow_initial_targeted=head is not None,ticket=1.,impact=.0015,
                start=str(pd.Timestamp(p['dates'][k+1]).date()),end=str(pd.Timestamp(p['dates'][terminal]).date()))
        except (ValueError,AssertionError) as exc:
            if str(exc) not in ('INITIAL_STATE_MARK','NO_MARK_FOR_HOLDING','NO_CLOSE_MARK_FOR_HOLDING'):raise
            return dict(group,status='CENSORED_MISSING_MARK',failed_branch=label,detail=str(exc))
        valid,detail=_valid_valuation_path(result,sp,sf,k,seed)
        if not valid:return dict(group,status='CENSORED_STALE_MARK',failed_branch=label,detail=detail)
        outcomes[label]=float(result['daily'].nav_close.iloc[-1]);errors.append(float(result['max_self_financing_error']))
        group['events'][label]=dict(trace=[] if executor is None else executor.trace,
            summary={} if executor is None else executor.summary,orders=int(len(result['orders'])),
            deferred_sessions=int(result['deferred_sessions']),max_account_error=errors[-1])
    base=outcomes['BASE'];reference=bundle.get('baseline_nav',{}).get(terminal)
    error=None if reference is None else abs(base-float(reference))
    if error is not None and not np.isclose(base,reference,rtol=1e-11,atol=1e-8):
        raise AssertionError(('BASE_REPLAY_MISMATCH',k,terminal,base,reference,error))
    for (head,asset),x in features.items():
        group['records'].append(dict(head=head,asset=asset,X=x.tolist(),y=float(np.log(outcomes[f'{head}:{asset}']/base)),
                                    signal_idx=int(k),terminal_idx=terminal))
    group.update(nav=outcomes,base_replay_endpoint=base,base_reference_endpoint=reference,base_replay_error=error,
                 max_account_error=max(errors),initial_nav=nav,asset_indices=ids.tolist())
    return group


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_bytes(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def reconstruct_selected_order(panel,targets,begin,selector):
    """Keep causal selector metadata order, verifying the cached half weights."""
    selected=[[] for _ in panel['dates']]
    for k in range(begin-1,len(panel['dates'])):
        weights,metadata=selector(k,np.zeros(len(panel['names'])))
        if not np.array_equal(weights,targets[k]):raise AssertionError(('CAUSAL_TARGET_MISMATCH',k))
        selected[k]=[int(j) for j in metadata['selected_indices']]
    return selected


def build_bundle(root:Path)->dict:
    """Read old inputs and cached states without invoking old bank construction."""
    from run_protection import load_inputs
    from cluster_selectors import prepare_features
    from dedup_selectors import make_policy
    from signals import decision_mask
    root=Path(root).resolve();previous=root.parent/'olc111';source=root.parent/'olc110'
    p,turnover,core=load_inputs(source);f=prepare_features(p,core,turnover)
    monthly=decision_mask(p['dates'],'MONTHLY');weekly=decision_mask(p['dates'],'WEEKLY')
    begin=int(p['dates'].searchsorted('2020-03-02'))
    with np.load(previous/'data/CAUSAL_SELECTIONS.npz',allow_pickle=False) as data:targets=data['targets']
    with np.load(previous/'data/BASELINE_STATES.npz',allow_pickle=False) as data:
        states={key:data[key] for key in ('k','units','cash','nav','busy')}
    baseline=pd.read_csv(previous/'data/BASELINE_PRIMARY_DAILY.csv.gz',float_precision='round_trip')
    inputs=[source/'source/data/XETRA_EUR_ETF.npz',source/'data/LIQUIDITY.npz',
            previous/'data/CAUSAL_SELECTIONS.npz',previous/'data/BASELINE_STATES.npz',
            previous/'data/BASELINE_PRIMARY_DAILY.csv.gz',source/'src/dedup_selectors.py',
            source/'src/cluster_selectors.py',source/'src/signals.py',source/'source/src/core.py',
            previous/'src/research_pipeline.py',Path(__file__)]
    identity={str(path.relative_to(root.parent)):_sha(path) for path in inputs}
    folder=root/'data';folder.mkdir(parents=True,exist_ok=True)
    cache=folder/'SELECTED_ORDER.json';receipt=folder/'SELECTED_ORDER_PROVENANCE.json'
    if cache.exists() or receipt.exists():
        if not(cache.exists() and receipt.exists()):raise ValueError('ORDER_CACHE_PROVENANCE_MISSING')
        meta=json.loads(receipt.read_text())
        if meta['input_hashes']!=identity or meta['selected_order_sha256']!=_sha(cache):
            raise ValueError('ORDER_CACHE_IDENTITY_MISMATCH')
        selected=json.loads(cache.read_text())
    else:
        selector=make_policy(p,f,{},'DEDUP_DUAL_TREND_OPP')
        selected=reconstruct_selected_order(p,targets,begin,selector)
        cache.write_bytes(_json_bytes(selected))
        receipt.write_bytes(_json_bytes(dict(input_hashes=identity,selected_order_sha256=_sha(cache))))
    if len(selected)!=len(p['dates']):raise ValueError('ORDER_CACHE_SHAPE')
    for k in range(begin-1,len(p['dates'])):
        check=np.zeros(len(p['names']));check[selected[k]]=.5
        if not np.array_equal(check,targets[k]):raise AssertionError(('ORDER_TARGET_MISMATCH',k))
    return dict(panel=p,f=f,core=core,monthly=monthly,weekly=weekly,
        feature_monthly=feature_monthly_schedule(p['dates'],monthly),targets=targets,selected_order=selected,
        begin=begin,states=states,baseline_nav={int(row.k):float(row.nav_close) for row in baseline.itertuples()},
        input_hashes=identity,selected_order_sha256=_sha(cache))


def verify_bank_freeze(root):
    root=Path(root);path=root/'docs/BANK_FREEZE.json';freeze=json.loads(path.read_text())
    for kind in ('code_hashes','input_hashes'):
        for name,digest in freeze[kind].items():
            if _sha(root/name)!=digest:raise ValueError('FROZEN_INPUT_CHANGED:'+name)
    if _sha(root/'docs/DESIGN_AND_PROTOCOL.md')!=freeze['protocol_sha256']:
        raise ValueError('FROZEN_PROTOCOL_CHANGED')
    return _sha(path)


def build_bank(root:Path,bundle:dict,resume=False)->dict[str,dict]:
    """Build both paired banks once under an exact verified protocol/source seal."""
    root=Path(root);fingerprint=verify_bank_freeze(root);folder=root/'data';folder.mkdir(parents=True,exist_ok=True)
    receipt=folder/'BANK_CACHE_PROVENANCE.json';events_path=folder/'BANK_EVENTS.jsonl';summary_path=folder/'BANK_SUMMARY.json'
    identity=dict(bank_freeze_sha256=fingerprint,selected_order_sha256=bundle.get('selected_order_sha256'))
    outputs=[events_path,summary_path]+[folder/f'BANK_{head}.npz' for head in HEADS]
    if receipt.exists():
        if json.loads(receipt.read_text())!=identity:raise ValueError('CACHE_FROM_DIFFERENT_FREEZE')
        if not resume:raise FileExistsError('Bank already initialized; use resume under exact freeze')
    else:
        if any(path.exists() for path in outputs):raise ValueError('CACHE_PROVENANCE_MISSING')
        receipt.write_bytes(_json_bytes(identity))
    events=[];completed=set()
    if events_path.exists():
        for line in events_path.read_text().splitlines():
            event=json.loads(line);digest=event.pop('event_sha256')
            if hashlib.sha256(_json_bytes(event)).hexdigest()!=digest:raise ValueError('BANK_EVENT_CORRUPT')
            k=int(event['signal_idx'])
            if k in completed:raise ValueError('DUPLICATE_BANK_DATE')
            completed.add(k);events.append(event)
    if summary_path.exists():
        prior_summary=json.loads(summary_path.read_text())
        for name,digest in prior_summary['artifact_hashes'].items():
            if _sha(folder/name)!=digest:raise ValueError('BANK_ARTIFACT_CHANGED:'+name)
    states=bundle['states'];dates=pd.DatetimeIndex(bundle['panel']['dates'])
    with events_path.open('a',encoding='utf-8') as stream:
        for seq,value in enumerate(states['k']):
            k=int(value)
            if k<bundle['begin'] or k in completed:continue
            state=dict(units=states['units'][seq],cash=float(states['cash'][seq]),nav=float(states['nav'][seq]),busy=bool(states['busy'][seq]))
            event=counterfactual_group(bundle,k,state)
            event['date']=str(dates[k].date())
            event['event_sha256']=hashlib.sha256(_json_bytes(event)).hexdigest()
            stream.write(_json_bytes(event).decode());stream.flush()
            event.pop('event_sha256');events.append(event);completed.add(k)
            if len(events)%100==0:print(f'OLC114 bank: {len(events)} dates through {dates[k].date()}',flush=True)
    rows=[row for event in events for row in event['records']];bank={}
    for head in HEADS:
        chosen=[row for row in rows if row['head']==head]
        bank[head]={key:np.array([row['asset' if key=='asset_idx' else key] for row in chosen],
                            dtype=float if key in ('X','y') else int)
                    for key in ('X','y','signal_idx','terminal_idx','asset_idx')}
        bank[head]['X']=bank[head]['X'].reshape(-1,FEATURE_DIMS[head])
        np.savez_compressed(folder/f'BANK_{head}.npz',**bank[head])
    summary=dict(dates=len(events),rows={head:len(bank[head]['y']) for head in HEADS},
        statuses=pd.Series([event['status'] for event in events],dtype=str).value_counts().to_dict(),
        max_account_error=max((event.get('max_account_error',0.) for event in events),default=0.),
        max_base_replay_error=max((event.get('base_replay_error') or 0. for event in events),default=0.),
        horizon=42,execution='NEXT_CLOSE',ticket=1.,impact=.0015,provenance=identity,
        artifact_hashes={path.name:_sha(path) for path in [events_path]+[folder/f'BANK_{head}.npz' for head in HEADS]})
    summary_path.write_bytes(_json_bytes(summary));verify_bank_freeze(root)
    return bank
