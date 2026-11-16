"""Causal account features and native matched-state counterfactual labels."""
from __future__ import annotations
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from replay_engine import simulate

DAILY_VOL_FLOOR = .01 / np.sqrt(252.)
HEADS = ('CASH', 'FRESH', 'ENTRY')


def verify_bank_freeze(root):
    root=Path(root)
    frozen_path=root/'docs/BANK_FREEZE.json'
    frozen_bytes=frozen_path.read_bytes()
    freeze=json.loads(frozen_bytes)
    for kind in ('code_hashes','input_hashes'):
        for path,digest in freeze[kind].items():
            if hashlib.sha256((root/path).read_bytes()).hexdigest()!=digest:
                raise ValueError('FROZEN_INPUT_CHANGED:'+path)
    if hashlib.sha256((root/'docs/DESIGN_AND_PROTOCOL.md').read_bytes()).hexdigest()!=freeze['protocol_sha256']:
        raise ValueError('FROZEN_PROTOCOL_CHANGED')
    fingerprint=hashlib.sha256(frozen_bytes).hexdigest()
    receipt=root/'data/BANK_CACHE_PROVENANCE.json'
    if receipt.exists():
        if json.loads(receipt.read_text())['bank_freeze_sha256']!=fingerprint:
            raise ValueError('CACHE_FROM_DIFFERENT_FREEZE')
    else:
        caches=('CAUSAL_SELECTIONS.npz','BASELINE_STATES.npz','BANK_EVENTS.jsonl')
        if any((root/'data'/name).exists() for name in caches):
            raise ValueError('CACHE_PROVENANCE_MISSING')
        receipt.write_text(json.dumps(dict(bank_freeze_sha256=fingerprint),indent=2)+'\n')
    return fingerprint


def feature_monthly_schedule(dates, monthly):
    """Retain the known terminal month-end in features, never in execution.

    This fixed study ends on2026-10-30, the last weekday of October. A different
    mid-month source endpoint requires an explicit extended exchange calendar;
    it must not silently disable features or pretend that endpoint is month-end.
    """
    dates=pd.DatetimeIndex(dates)
    if dates[-1] != dates[-1]+pd.offsets.BMonthEnd(0):
        raise ValueError('EXPLICIT_FUTURE_EXCHANGE_CALENDAR_REQUIRED')
    out=np.asarray(monthly,bool).copy();out[-1]=True
    return out


def execution_panel(panel, fill):
    if fill=='OPEN':
        return panel
    if fill=='CLOSE':
        return dict(panel,O=panel['C'],open_observed=panel['observed'])
    raise ValueError('EXECUTION_CONVENTION')


def select_action(predictions):
    eligible=[(float(v['lower']),a) for a,v in predictions.items()
              if np.isfinite(v['mean']) and np.isfinite(v['lower'])
              and v['mean']>0 and v['lower']>0]
    if not eligible:
        return 'HOLD'
    return sorted(eligible,key=lambda item:(-item[0],item[1]))[0][1]


def fresh_is_action(current, fresh):
    current, fresh = np.asarray(current, float), np.asarray(fresh, float)
    return bool(fresh.sum() > 1e-10 and np.abs(fresh-current).sum() >= .03 - 1e-12)


def basket_stats(f, k, weights):
    """Trailing descriptive history of today's weights, with uninvested cash."""
    w = np.asarray(weights, float)
    ids = np.flatnonzero(w > 1e-12)
    if not len(ids):
        return dict(nm21=0., nm63=0., log21=0., log63=0., vol21=DAILY_VOL_FLOOR,
                    vol63=DAILY_VOL_FLOOR, ratio=0., history=np.zeros(63))
    rr = np.asarray(f['returns'][k-62:k+1, ids], float)
    if rr.shape != (63, len(ids)) or not np.isfinite(rr).all():
        return None
    daily_simple = np.expm1(rr) @ w[ids]
    if np.any(daily_simple <= -1):
        return None
    history = np.log1p(daily_simple)
    v63 = max(float(history.std(ddof=1)), DAILY_VOL_FLOOR)
    v21 = max(float(history[-21:].std(ddof=1)), DAILY_VOL_FLOOR)
    r21, r63 = float(history[-21:].sum()), float(history.sum())
    return dict(nm21=r21/(v63*np.sqrt(21.)), nm63=r63/(v63*np.sqrt(63.)),
                log21=r21, log63=r63, vol21=v21, vol63=v63,
                ratio=float(np.log(v21/v63)), history=history)


def state_features(f, k, current, fresh, breadth, monthly):
    current, fresh = np.asarray(current, float), np.asarray(fresh, float)
    held, new = basket_stats(f, k, current), basket_stats(f, k, fresh)
    future = np.flatnonzero(np.asarray(monthly, bool) & (np.arange(len(monthly)) > k))
    if not len(future) or not np.isfinite(breadth):
        return {h: None for h in HEADS}
    time = float(future[0]-k)/21.
    out = {h: None for h in HEADS}
    gross = float(current.sum())
    if held is not None and gross > 1e-10:
        out['CASH'] = np.array([held['nm21'],held['nm63'],held['ratio'],breadth,time,gross])
    if new is not None and fresh.sum() > 1e-10:
        out['ENTRY'] = np.array([new['nm21'],new['nm63'],new['ratio'],breadth,time])
    if held is not None and new is not None and gross > 1e-10 and fresh.sum()>1e-10:
        a = held['history']-held['history'].mean()
        b = new['history']-new['history'].mean()
        den = np.sqrt(a@a)*np.sqrt(b@b)
        corr = float(a@b/den) if den > 1e-14 else 0.
        out['FRESH'] = np.array([new['nm21']-held['nm21'],new['nm63']-held['nm63'],
                                np.log(new['vol63']/held['vol63']),corr,time,gross])
    return out


def _valid_valuation_path(result, small_panel, small_f, k, state):
    """Check each realized held mark; one censored branch invalidates its group."""
    dates = pd.DatetimeIndex(small_panel['dates']).values.astype('datetime64[D]').astype(int)
    obs = np.asarray(small_panel['observed'],bool)
    valid_obs = obs & np.isfinite(small_panel['C']) & (small_panel['C']>0)
    last = np.maximum.accumulate(np.where(valid_obs,np.arange(len(obs))[:,None],-1),axis=0)
    units = np.asarray(state['units'],float).copy()
    grouped = {int(q): g for q,g in result['orders'].groupby('execution_idx')}
    for j in [k] + result['daily']['k'].astype(int).tolist():
        if j in grouped:
            for trade in grouped[j].itertuples():
                units[trade.j] += trade.quantity if trade.side=='BUY' else -trade.quantity
        held = np.flatnonzero(units>1e-10)
        if not len(held):
            continue
        seen = last[j,held]
        ages = dates[j]-dates[np.maximum(seen,0)]
        marks = small_f['C'][j,held]
        if np.any(seen<0) or np.any(ages>5) or not np.isfinite(marks).all() or np.any(marks<=0):
            return False, dict(index=int(j),tickers=small_panel['names'][held].tolist(),
                               ages_calendar_days=ages.tolist())
    return True, None


def counterfactual_values(panel, f, core, monthly, targets, k, state, *,
                          horizon=21, actions=('HOLD','CASH','FRESH'), ticket=1.,impact=.0015):
    """One intervention followed by common baseline continuation, net of fees.

    Subsetting removes only assets that cannot be held or targeted in any
    branch. All dates, account cash, native netting and full NAV are preserved.
    This is a label generator, not an annualized strategy return calculation.
    """
    terminal = k + horizon
    n_dates = len(panel['dates'])
    if terminal >= n_dates:
        return dict(status='RIGHT_EDGE',signal_idx=int(k),terminal_idx=int(terminal))
    if state.get('pending') is not None or state.get('queued'):
        return dict(status='BUSY_STATE',signal_idx=int(k),terminal_idx=int(terminal))
    seed_units = np.asarray(state['units'],float)
    ids = set(np.flatnonzero(seed_units>1e-12).tolist())
    ids.update(np.flatnonzero(targets[k]>0).tolist())
    for j in range(k+1,terminal):
        if monthly[j]:
            ids.update(np.flatnonzero(targets[j]>0).tolist())
    if not ids:
        # A harmless zero-weight column is required by the native account API.
        ids.add(0)
    ids=np.array(sorted(ids),int)
    sp=dict(dates=panel['dates'],names=np.asarray(panel['names'])[ids],
            O=np.asarray(panel['O'])[:,ids],C=np.asarray(panel['C'])[:,ids],
            observed=np.asarray(panel['observed'])[:,ids],
            open_observed=np.asarray(panel.get('open_observed',panel['observed']))[:,ids],benchmark=0)
    sf={'C':np.asarray(f['C'])[:,ids]}
    seed=dict(units=seed_units[ids].copy(),cash=float(state['cash']))
    current_nav=float(seed['cash']+np.nansum(seed['units']*sf['C'][k]))
    outcomes={}; orders={}; deferred={}; errors={}
    for action in actions:
        initial_target = np.zeros(len(ids)) if action=='CASH' else targets[k,ids].copy()
        def policy(j,current,initial_target=initial_target):
            return initial_target if j==k else targets[j,ids]
        try:
            result=simulate(sp,sf,policy,monthly,legacy=core,
                start=str(pd.Timestamp(panel['dates'][k+1]).date()),
                end=str(pd.Timestamp(panel['dates'][terminal]).date()),
                initial=current_nav,initial_state=seed,issue_initial=action!='HOLD',
                ticket=ticket,impact=impact)
        except ValueError as exc:
            if str(exc)!='INITIAL_STATE_MARK':
                raise
            return dict(status='CENSORED_MISSING_MARK',signal_idx=int(k),terminal_idx=int(terminal),
                        failed_action=action,detail=str(exc))
        except AssertionError as exc:
            # Missing marks are a known censor mechanism; other accounting
            # assertions are implementation errors and must stop the run.
            if 'NO_MARK_FOR_HOLDING' not in str(exc) and 'NO_CLOSE_MARK_FOR_HOLDING' not in str(exc):
                raise
            return dict(status='CENSORED_MISSING_MARK',signal_idx=int(k),terminal_idx=int(terminal),
                        failed_action=action,detail=str(exc))
        valid, detail = _valid_valuation_path(result,sp,sf,k,seed)
        if not valid:
            return dict(status='CENSORED_STALE_MARK',signal_idx=int(k),terminal_idx=int(terminal),
                        failed_action=action,detail=detail)
        outcomes[action]=float(result['daily'].nav_close.iloc[-1])
        orders[action]=int(len(result['orders']))
        deferred[action]=int(result['deferred_sessions'])
        errors[action]=float(result['max_self_financing_error'])
    base=outcomes['HOLD']
    return dict(status='OK',signal_idx=int(k),terminal_idx=int(terminal),nav=outcomes,
                net={a:float(np.log(v/base)) for a,v in outcomes.items() if a!='HOLD'},
                orders=orders,deferred=deferred,max_account_error=max(errors.values(),default=0.),
                initial_nav=current_nav,asset_indices=ids.tolist())


def build_research_bundle(root, resume=False):
    """Prepare fixed candidates, actual baseline states and one primary label bank."""
    root=Path(root).resolve();old=root.parent/'olc110'
    verify_bank_freeze(root)
    sys.path.insert(0,str(old/'src'))
    from run_protection import load_inputs
    from cluster_selectors import prepare_features,build_snapshot
    from dedup_selectors import make_policy
    from signals import decision_mask
    from cboe_features import load_cboe_features
    p,turnover,core=load_inputs(old)
    f=prepare_features(p,core,turnover)
    monthly=decision_mask(p['dates'],'MONTHLY')
    feature_monthly=feature_monthly_schedule(p['dates'],monthly)
    begin=int(p['dates'].searchsorted('2020-03-02'))
    data=root/'data';data.mkdir(exist_ok=True)
    cboe=load_cboe_features(data/'raw',p['dates'])
    np.savez_compressed(data/'CBOE_ALIGNED.npz',**{k:v for k,v in cboe.items() if k!='metadata'})
    (data/'CBOE_ALIGNED_METADATA.json').write_text(json.dumps(cboe['metadata'],indent=2)+'\n')
    selector=make_policy(p,f,{},'DEDUP_DUAL_TREND_OPP')
    selection_path=data/'CAUSAL_SELECTIONS.npz'
    if resume and selection_path.exists():
        with np.load(selection_path,allow_pickle=False) as z:
            targets=z['targets'];breadth=z['breadth']
    else:
        targets=np.zeros_like(p['C']);breadth=np.full(len(p['dates']),np.nan)
        representatives=[];groups=[]
        print('Preparing unchanged daily candidates and monthly representative breadth',flush=True)
        for k in range(begin-1,len(p['dates'])):
            targets[k],_=selector(k,np.zeros(len(p['names'])))
            if k==begin-1 or monthly[k]:
                snapshot=build_snapshot(p,f,k)
                representatives=[g['representative'] for g in snapshot['groups']]
                groups.append(dict(k=int(k),date=str(p['dates'][k].date()),
                                   representatives=representatives,groups=len(representatives),
                                   eligible=int(snapshot['eligible_count'])))
            ids=np.array(representatives,int)
            if len(ids):
                ids=ids[f['liquid_eligible'][k,ids]&np.isfinite(f['m63'][k,ids])]
                if len(ids):breadth[k]=float(np.mean(f['m63'][k,ids]>0))
            if (k-begin+1)%250==0:
                print(f'  candidates through {p["dates"][k].date()}',flush=True)
        np.savez_compressed(selection_path,targets=targets,breadth=breadth)
        (data/'BREADTH_GROUP_SCHEDULE.json').write_text(json.dumps(groups,indent=2)+'\n')
    primary=execution_panel(p,'CLOSE')
    state_path=data/'BASELINE_STATES.npz'
    if resume and state_path.exists():
        with np.load(state_path,allow_pickle=False) as z:
            snapshot_idx=z['k'];units=z['units'];cash=z['cash'];nav=z['nav'];busy=z['busy']
    else:
        snapshots=[]
        def capture(k,current,context):
            snapshots.append(dict(k=k,units=context['units'].copy(),cash=context['cash'],
                                  nav=context['nav'],busy=bool(context['pending'] or context['queued'])))
            if context['initial'] or context['scheduled']:
                return dict(weights=targets[k],reason='INITIAL' if context['initial'] else 'SCHEDULED',
                            force=bool(context['initial']))
            return None
        baseline=simulate(primary,f,lambda k,w:targets[k],monthly,legacy=core,account_policy=capture)
        baseline['daily'].to_csv(data/'BASELINE_PRIMARY_DAILY.csv.gz',index=False,
                                compression={'method':'gzip','mtime':0})
        snapshot_idx=np.array([s['k'] for s in snapshots],int)
        units=np.array([s['units'] for s in snapshots]);cash=np.array([s['cash'] for s in snapshots])
        nav=np.array([s['nav'] for s in snapshots]);busy=np.array([s['busy'] for s in snapshots],bool)
        np.savez_compressed(state_path,k=snapshot_idx,units=units,cash=cash,nav=nav,busy=busy)
    events_path=data/'BANK_EVENTS.jsonl'
    events=[]
    if events_path.exists():
        if not resume:raise FileExistsError('Bank already exists; use resume with unchanged freeze')
        events=[json.loads(line) for line in events_path.read_text().splitlines() if line]
    completed={int(e['k']) for e in events}
    with events_path.open('a',encoding='utf-8') as stream:
        for seq,k in enumerate(snapshot_idx):
            k=int(k)
            if k<begin or k in completed:continue
            event=dict(k=k,date=str(p['dates'][k].date()),rows=[])
            if busy[seq]:
                event['status']='BUSY_STATE'
            elif not cboe['available'][k]:
                event['status']='SOURCE_UNAVAILABLE_COMMON_SUPPORT'
            elif k+21>=len(p['dates']):
                event['status']='RIGHT_EDGE'
            else:
                current=units[seq]*np.where(np.isfinite(f['C'][k]),f['C'][k],0.)/nav[seq]
                fresh=targets[k]
                features=state_features(f,k,current,fresh,breadth[k],feature_monthly)
                legal_fresh=fresh_is_action(current,fresh)
                if current.sum()>1e-8 and features['CASH'] is not None:
                    state=dict(units=units[seq],cash=cash[seq])
                    actions=('HOLD','CASH','FRESH') if legal_fresh and features['FRESH'] is not None else ('HOLD','CASH')
                    invested=counterfactual_values(primary,f,core,monthly,targets,k,state,actions=actions)
                    event['invested']=invested
                    if invested['status']=='OK':
                        for action in ('CASH','FRESH'):
                            if action not in invested['net']:continue
                            event['rows'].append(dict(head=action,Xprice=features[action].tolist(),
                                Xlegacy=cboe['legacy'][k].tolist(),Xterm=cboe['term'][k].tolist(),
                                y=invested['net'][action],signal_idx=k,terminal_idx=k+21))
                if fresh.sum()>1e-10 and features['ENTRY'] is not None:
                    state=dict(units=np.zeros(len(p['names'])),cash=float(nav[seq]))
                    entry=counterfactual_values(primary,f,core,monthly,targets,k,state,actions=('HOLD','FRESH'))
                    event['cash']=entry
                    if entry['status']=='OK':
                        event['rows'].append(dict(head='ENTRY',Xprice=features['ENTRY'].tolist(),
                            Xlegacy=cboe['legacy'][k].tolist(),Xterm=cboe['term'][k].tolist(),
                            y=entry['net']['FRESH'],signal_idx=k,terminal_idx=k+21))
                event['status']='EVALUATED'
            stream.write(json.dumps(event,separators=(',',':'),allow_nan=False)+'\n')
            stream.flush();events.append(event)
            if len(events)%100==0:
                print(f'  native comparison bank {len(events)} dates through {p["dates"][k].date()}',flush=True)
    bank={}
    rows=[r for event in events for r in event['rows']]
    for head in HEADS:
        selected=[r for r in rows if r['head']==head]
        dimension=5 if head=='ENTRY' else 6
        bank[head]={key:np.array([r[key] for r in selected],dtype=float if key.startswith('X') or key=='y' else int)
                    for key in ('Xprice','Xlegacy','Xterm','y','signal_idx','terminal_idx')}
        bank[head]['Xprice']=bank[head]['Xprice'].reshape(-1,dimension)
        bank[head]['Xlegacy']=bank[head]['Xlegacy'].reshape(-1,2)
        bank[head]['Xterm']=bank[head]['Xterm'].reshape(-1,2)
        np.savez_compressed(data/f'BANK_{head}.npz',**bank[head])
    summary=dict(dates=len(events),rows={h:len(bank[h]['y']) for h in HEADS},
                 event_status=pd.Series([e['status'] for e in events]).value_counts().to_dict(),
                 comparison_status=pd.Series([e[s]['status'] for e in events for s in ('invested','cash') if s in e]).value_counts().to_dict(),
                 max_account_error=max([e[s].get('max_account_error',0.) for e in events for s in ('invested','cash') if s in e],default=0.),
                 primary_execution='NEXT_CLOSE',normal_ticket=1.,normal_impact=.0015,
                 source_unavailable_in_study=int((~cboe['available'][begin:]).sum()))
    (data/'BANK_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('Bank complete '+json.dumps(summary),flush=True)
    return dict(panel=p,f=f,core=core,monthly=monthly,feature_monthly=feature_monthly,
                targets=targets,breadth=breadth,cboe=cboe,bank=bank,begin=begin)
