"""Independent OLC114 ledger/model audit. Never fits or replays a policy."""
from __future__ import annotations
import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
ARMS=('BASE','STATIC_75','MEAN_CYCLE','RIDGE_CYCLE','TREE_CYCLE')
TERMS={'NEXT_CLOSE':(1.,.0015,0),'DOUBLE_COST':(2.,.003,0),'DELAY1_CLOSE':(1.,.0015,1)}
HEADS=('PARK','REDEPLOY')
ARTIFACTS=('DAILY.csv.gz','ORDERS.csv.gz','INSTRUCTIONS.csv.gz','DECISIONS.npz',
           'DECISIONS_META.json.gz','POLICY_TRACE.csv.gz','PLAN_VALUES.csv.gz',
           'ELIGIBLE_STATES.jsonl.gz','PLAN_SUMMARIES.json.gz')

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);value=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value);return value

audit=module('olc114_independent_metrics',ROOT.parent/'olc111/src/analyze_results.py')
compare=module('olc114_independent_comparisons',ROOT.parent/'olc112/src/analyze_results.py')

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode()
def digest(value):return hashlib.sha256(canonical(value)).hexdigest()
def parsed(value):
    if value is None or isinstance(value,(float,np.floating)) and np.isnan(value):return None
    return json.loads(value) if isinstance(value,str) else value
def boolval(value):
    if isinstance(value,(bool,np.bool_)):return bool(value)
    if value in (0,1):return bool(value)
    if isinstance(value,str) and value.lower() in ('true','false'):return value.lower()=='true'
    raise ValueError('BOOLEAN_LEDGER_VALUE')
def nonoverlap(values,horizon=42):
    picked=[]
    for k in sorted(set(int(v) for v in values)):
        if not picked or k>=picked[-1]+horizon:picked.append(k)
    return len(picked)
def material_criterion(candidate,base):
    out={}
    for w in ('whole','post'):
        gain=candidate[w]['cagr']-base[w]['cagr'];dd=candidate[w]['maxdd_sampled']-base[w]['maxdd_sampled']
        out[w]=dict(cagr_gain=gain,maxdd_change=dd,material=bool(gain>=.03-1e-12 and dd>=-1e-12))
    out.update(material_both_windows=all(out[w]['material'] for w in ('whole','post')),
               target30_whole=candidate['whole']['cagr']>=.30,target30_post=candidate['post']['cagr']>=.30)
    return out

def signal_target(raw,indices,sell_only,current):
    target=np.asarray(raw,float).copy()
    if sell_only:target=np.minimum(target,current)
    if indices is not None:
        mask=np.zeros(len(target),bool);mask[indices]=True
        target[~mask]=current[~mask];budget=max(0.,1.-float(current[~mask].sum()))
        total=float(target[mask].sum())
        if total>budget:target[mask]*=budget/total
    return target

def expected_fills(units,cash,mark,prices,valid,target,force,ticket,impact):
    """Audit one recorded immutable instruction's sizing, without choosing a policy."""
    inventory=units.copy();wealth=float(cash+np.nansum(inventory*mark));desired=wealth*target
    delta=desired-np.where(np.isfinite(mark),inventory*mark,0.);threshold=max(1e-8,0. if force else .03*wealth)
    out=[]
    for j in np.flatnonzero(valid&(delta < -1e-8)&((np.abs(delta)>=threshold)|(target==0))):
        qty=min(inventory[j],-delta[j]/prices[j]);notional=qty*prices[j];fee=ticket+impact*notional
        if notional<=fee and cash+notional<fee:continue
        inventory[j]-=qty;cash+=notional-fee;out.append((int(j),'SELL',float(qty),float(notional)))
    requested=np.maximum(0.,desired-np.where(np.isfinite(mark),inventory*mark,0.))
    ids=np.flatnonzero(valid&(requested>1e-8)&(requested>=threshold));ids=ids[requested[ids]>ticket]
    if len(ids) and cash>ticket*len(ids):
        factor=min(1.,(cash-ticket*len(ids))/((1+impact)*requested[ids].sum()))
        for j in ids:
            notional=float(requested[j]*factor)
            if notional>1e-8:out.append((int(j),'BUY',notional/prices[j],notional))
    return out

def reconcile_account(daily,orders,instructions,panel,scenario):
    """Reconstruct observed trades, masks and queue maturity; generate no orders."""
    ticket,impact,lag=TERMS[scenario];dates=np.asarray(panel['dates'],dtype='datetime64[D]')
    raw=np.asarray(panel['C'],float);valid=np.asarray(panel['observed'],bool)&np.isfinite(raw)&(raw>0)
    marks=pd.DataFrame(np.where(valid,raw,np.nan)).ffill().to_numpy();n=raw.shape[1]
    by_signal={};by_iid={}
    for row in instructions.itertuples():
        iid,k,due=int(row.instruction_id),int(row.signal_idx),int(row.due_idx)
        target=np.asarray(parsed(row.target_weights),float);indices=parsed(row.action_indices)
        mask=np.ones(n,bool) if indices is None else np.zeros(n,bool)
        if indices is not None:
            if any(not isinstance(j,int) or j<0 or j>=n for j in indices):raise ValueError('INSTRUCTION_MASK')
            mask[indices]=True
        if (iid in by_iid or target.shape!=(n,) or not np.isfinite(target).all() or
            np.any(target<0) or target.sum()>1+1e-9 or due!=k+1+lag):raise ValueError('INSTRUCTION_CONTRACT')
        rec=dict(iid=iid,k=k,due=due,target=target,mask=mask,reason=row.reason,sell_only=boolval(row.sell_only),force=boolval(row.force))
        by_iid[iid]=rec;by_signal.setdefault(k,[]).append(rec)
    grouped={int(k):g for k,g in orders.groupby('execution_idx')} if len(orders) else {}
    units=np.zeros(n);cash=10000.;pending=None;queue=[];start=int(daily.k.iloc[0])
    states={start-1:dict(units=units.copy(),cash=cash,nav=cash,weights=units.copy(),busy=False)}
    queue.extend(by_signal.get(start-1,[]));errors={k:0. for k in ('fee','notional','price','pre_nav','nav','cash','gross','self_financing')}
    violations=0;attempts=[];outside=0
    for day in daily.itertuples():
        k=int(day.k);mark=np.where(valid[k],raw[k],marks[k-1]);pre=cash+float(np.nansum(units*mark))
        errors['pre_nav']=max(errors['pre_nav'],abs(pre-day.nav_open))
        eligible=[i for i in queue if i['due']<=k];queue=[i for i in queue if i['due']>k]
        for item in eligible:pending=item
        missing=np.zeros(n,bool)
        if pending is not None:
            target=pending['target']
            if pending['sell_only']:target=np.minimum(target,np.where(np.isfinite(mark),units*mark,0.)/pre)
            missing=((units>1e-10)|(target>0))&pending['mask']&~valid[k]
            attempts.append(dict(k=k,instruction_id=pending['iid'],signal_idx=pending['k'],due_idx=pending['due'],
                                 deferred=bool(missing.any()),missing_count=int(missing.sum())))
            expected=expected_fills(units,cash,mark,raw[k],valid[k]&pending['mask'],target,pending['force'],ticket,impact)
            actual=[] if k not in grouped else list(grouped[k].itertuples())
            if len(expected)!=len(actual):raise ValueError('TARGET_EXECUTION_MISMATCH:COUNT')
            for (j,side,qty,notional),got in zip(expected,actual):
                if (j!=int(got.j) or side!=got.side or not np.isclose(qty,got.quantity,rtol=1e-10,atol=1e-8) or
                    not np.isclose(notional,got.notional,rtol=1e-10,atol=1e-8)):raise ValueError('TARGET_EXECUTION_MISMATCH:SIZE')
        fees=0.;before=units.copy()
        if k in grouped:
            for row in grouped[k].itertuples():
                j=int(row.j);iid=int(row.instruction_id)
                if pending is None or iid!=pending['iid']:raise ValueError('ORDER_WITHOUT_PENDING')
                if (row.reason!=pending['reason'] or int(row.signal_idx)!=pending['k'] or int(row.due_idx)!=pending['due'] or
                    k<pending['due'] or k<=pending['k']):raise ValueError('ORDER_TIMING')
                if j<0 or j>=n or str(row.ticker)!=str(panel['names'][j]):raise ValueError('ORDER_IDENTITY')
                if not pending['mask'][j]:raise ValueError('ORDER_OUTSIDE_MASK')
                if str(row.date)!=str(dates[k]):raise ValueError('ORDER_DATE')
                q,p,notional,cost=map(float,(row.quantity,row.price,row.notional,row.cost))
                if not np.isfinite([q,p,notional,cost]).all() or min(q,p,notional)<=0 or cost<0:raise ValueError('ORDER_AMOUNTS')
                errors['fee']=max(errors['fee'],abs(cost-ticket-impact*notional));errors['notional']=max(errors['notional'],abs(q*p-notional))
                violations+=int(not valid[k,j]);errors['price']=max(errors['price'],abs(p-raw[k,j]) if valid[k,j] else 0.)
                if row.side=='BUY':units[j]+=q;cash-=notional+cost
                elif row.side=='SELL':units[j]-=q;cash+=notional-cost
                else:raise ValueError('ORDER_SIDE')
                if pending['sell_only'] and row.side!='SELL':raise ValueError('SELL_ONLY_ORDER')
                fees+=cost
        if pending is not None:
            outside+=int(not np.array_equal(units[~pending['mask']],before[~pending['mask']]))
            if not missing.any():pending=None
        errors['self_financing']=max(errors['self_financing'],abs(cash+np.nansum(units*mark)+fees-pre))
        nav=cash+float(np.nansum(units*marks[k]));weights=np.where(np.isfinite(marks[k]),units*marks[k],0.)/nav
        for key,value in [('nav',nav-day.nav_close),('cash',cash-day.cash),('gross',weights.sum()-day.gross)]:errors[key]=max(errors[key],abs(value))
        violations+=int(cash < -1e-8 or np.any(units < -1e-8) or int((units>1e-10).sum())!=day.positions)
        states[k]=dict(units=units.copy(),cash=float(cash),nav=float(nav),weights=weights,busy=bool(pending is not None or queue))
        queue.extend(by_signal.get(k,[]))
    tol=max(1e-6,float(daily.nav_close.max())*1e-10)
    passed=all(v<= (1e-10 if k=='gross' else tol) for k,v in errors.items()) and not violations and not outside
    return dict(pass_all=bool(passed),**{f'maximum_{k}_error':v for k,v in errors.items()},
        quote_or_account_violations=violations,unaffected_unit_violations=outside,
        deferred_sessions=sum(a['deferred'] for a in attempts),tolerance=tol),states,pd.DataFrame(attempts)

def check_plan_chronology(plans,monthly,weekly,last):
    previous_handoff=-1
    for p in plans:
        k=int(p['signal_idx']);handoff=p['handoff_idx'];entry=p['entry_attempt_idx'];sale=p['sale_complete_idx']
        if k<=previous_handoff:raise ValueError('PLAN_OVERLAP')
        if monthly[k]:raise ValueError('PLAN_MONTHLY_START')
        future=np.flatnonzero(monthly & (np.arange(len(monthly))>k) & (np.arange(len(monthly))<last))
        expected=None if not len(future) else int(future[0])
        if handoff!=expected or bool(p['right_censored'])!=(handoff is None):raise ValueError('PLAN_HANDOFF')
        if entry is not None and (p['head']!='REDEPLOY' or sale is None or entry<=sale or not weekly[entry] or
                                   handoff is not None and entry>=handoff):raise ValueError('PLAN_ENTRY_TIMING')
        if p['head']=='PARK' and entry is not None:raise ValueError('PARK_ENTRY')
        previous_handoff=last if handoff is None else handoff
    return dict(pass_all=True,plans=len(plans),handoffs=sum(p['handoff_idx'] is not None for p in plans),
                complete_nonoverlap42=nonoverlap(p['signal_idx'] for p in plans if p['signal_idx']+42<=last),
                right_censored=sum(bool(p['right_censored']) for p in plans))

def confirmed_sale(fills,states,asset,stop_idx):
    """The executor has no callback on the terminal Close or after handoff."""
    value=None
    for fill in fills.itertuples():
        k=int(fill.execution_idx)
        if k<stop_idx and states[k]['units'][asset]<=1e-12:value=k
    return value

def validate_sale_instruction(sale,head,asset):
    if (sale.reason!=head+'_SALE' or parsed(sale.action_indices)!=[asset] or not boolval(sale.sell_only) or
        not boolval(sale.force) or np.any(np.asarray(parsed(sale.raw_weights),float)!=0.)):
        raise ValueError('PLAN_SALE_INSTRUCTION')

def predict_payload(model,x):
    x=np.asarray(x,float)
    def one(fit):
        if model['kind']=='MEAN':return float(fit['value'])
        if model['kind']=='RIDGE':
            z=(x-np.asarray(model['scaler']['mean']))/np.asarray(model['scaler']['scale'])
            return float(fit['intercept']+z@np.asarray(fit['coef']))
        node=0;xx=x.astype(np.float32)
        while fit['children_left'][node]!=-1:
            node=fit['children_left'][node] if xx[fit['feature'][node]]<=fit['threshold'][node] else fit['children_right'][node]
        return float(fit['value'][node])
    return one(model['fitted']),float(np.quantile([one(v) for v in model['bootstraps']],.10))

def candidate(order,returns,k,retained):
    for j in order[k]:
        if j in retained:continue
        ok=True
        for held in retained:
            x=returns[k-125:k+1,[j,held]]
            if x.shape[0]!=126 or not np.isfinite(x).all():raise ValueError('FEATURE_CORRELATION_SUPPORT')
            x=x-x.mean(axis=0);den=np.sqrt(np.sum(x*x,axis=0)).prod();corr=float(x[:,0]@x[:,1]/den) if den>1e-14 else 0.
            ok &= corr<=.85+1e-12
        if ok:return int(j)
    return None

def features(returns,k,weights,nav,asset,head,monthly,weekly,order):
    floor=.01/np.sqrt(252.)
    def stats(w):
        ids=np.flatnonzero(w>1e-12)
        if not len(ids):return 0.,0.,0.,floor
        r=returns[k-62:k+1,ids]
        if r.shape!=(63,len(ids)) or not np.isfinite(r).all():return None
        h=np.log1p(np.expm1(r)@w[ids]);v63=max(float(h.std(ddof=1)),floor);v21=max(float(h[-21:].std(ddof=1)),floor)
        return float(h[-21:].sum())/(v63*np.sqrt(21)),float(h.sum())/(v63*np.sqrt(63)),float(np.log(v21/v63)),v63
    own=np.zeros_like(weights);own[asset]=1.;held=stats(own);other=weights.copy();other[asset]=0.;remaining=stats(other)
    future=np.flatnonzero(monthly & (np.arange(len(monthly))>k))
    if held is None or remaining is None or not len(future):return None
    x=[*held[:3],held[3]*np.sqrt(252),weights[asset],remaining[0],(future[0]-k)/21,1./nav]
    if head=='REDEPLOY':
        j=candidate(order,returns,k,np.flatnonzero(other>1e-12));extra=[0.,0.,0.]
        if j is not None:
            w=np.zeros_like(weights);w[j]=1.;s=stats(w)
            if s is None:return None
            extra=[1.,s[0]-held[0],np.log(s[3]/held[3])]
        later=np.flatnonzero(weekly & (np.arange(len(weekly))>k+1))
        if not len(later):return None
        x+=extra+[(later[0]-k)/5]
    return np.asarray(x,float)

def validate_fits(saved,bank,dates,cutoffs,freeze_sha):
    counts=dict(files=0,ready_heads=0,models=0,max_terminal=0);first=None
    for cutoff in sorted(saved):
        document=saved[cutoff].copy();value=document.pop('payload_sha256')
        if digest(document)!=value or document['cutoff']!=cutoff or document['provenance']!=freeze_sha:raise ValueError('FIT_PROVENANCE')
        ready=[]
        for head in HEADS:
            b=bank[head];mature=b['terminal_idx']<cutoff;signal=b['signal_idx'][mature];terminal=b['terminal_idx'][mature]
            distinct,inverse,n=np.unique(signal,return_inverse=True,return_counts=True);months=np.unique(dates[distinct].astype('datetime64[M]'))
            enough=len(distinct)>=504 and len(months)>=24 and nonoverlap(distinct)>=12
            record=document['heads'][head];ready.append(enough)
            if (record is not None)!=enough:raise ValueError('FIT_READINESS')
            if record is None:continue
            meta=record['meta'];weights=1./n[inverse];X=b['X'][mature];y=b['y'][mature];w=weights/weights.sum()
            expected_hash=digest(dict(X=X.tolist(),y=y.tolist(),signal_idx=signal.tolist(),terminal_idx=terminal.tolist(),
                signal_dates=dates[distinct].astype(str).tolist(),weights=weights.tolist()))
            if (meta['training_hash']!=expected_hash or not np.array_equal(meta['signal_idx'],signal) or
                not np.array_equal(meta['terminal_idx'],terminal) or not np.array_equal(meta['training_weights'],weights) or
                np.any(terminal!=signal+42) or terminal.max()>=cutoff or meta['nonoverlap_42']!=nonoverlap(distinct)):
                raise ValueError('FIT_MATURITY_OR_WEIGHT')
            mean=w@X;scale=np.sqrt(w@((X-mean)**2));scale[scale==0]=1.
            if not np.allclose(mean,meta['scaler']['mean'],rtol=1e-12,atol=1e-12) or not np.allclose(scale,meta['scaler']['scale'],rtol=1e-12,atol=1e-12):raise ValueError('FIT_TRAINING_SCALER')
            support=np.unique(distinct//63);draws=np.random.default_rng(114).choice(support,size=(32,len(support)),replace=True)
            if not np.array_equal(meta['bootstrap_draws'],draws) or digest(meta['bootstrap_spec'])!=meta['draw_hash']:raise ValueError('FIT_BOOTSTRAP')
            for name,model in record['models'].items():
                if digest(model)!=record['hashes'][name] or model['provenance']['training_hash']!=expected_hash or model['provenance']['cutoff']!=cutoff or len(model['bootstraps'])!=32:raise ValueError('MODEL_IDENTITY')
                if name=='TREE' and any(sum(np.asarray(t['children_left'])==-1)>4 for t in [model['fitted']]+model['bootstraps']):raise ValueError('TREE_DEPTH')
                counts['models']+=1
            counts['ready_heads']+=1;counts['max_terminal']=max(counts['max_terminal'],int(terminal.max()))
        if all(ready) and first is None:first=cutoff
        if all(ready) and document['heads']['PARK']['meta']['block_support']==document['heads']['REDEPLOY']['meta']['block_support']:
            if document['heads']['PARK']['meta']['draw_hash']!=document['heads']['REDEPLOY']['meta']['draw_hash']:raise ValueError('UNPAIRED_HEAD_BOOTSTRAP')
        counts['files']+=1
    counts.update(pass_all=True,raw_first_ready_idx=first,activation_idx=None if first is None else max(865,first))
    return counts

def audit_policy(path,states,marks,returns,dates,monthly,feature_monthly,weekly,targets,order,saved,cutoffs,ready):
    trace=path['trace'];inst=path['instructions'];plans=path['plans'];arm=path['arm'];orders=path['orders'];values=path['values'];n=marks.shape[1]
    by_signal={int(k):g for k,g in inst.groupby('signal_idx')};modelname=arm.removesuffix('_CYCLE')
    for instruction in inst.itertuples():
        raw=np.asarray(parsed(instruction.raw_weights),float);current=states[int(instruction.signal_idx)]['weights']
        expected=signal_target(raw,parsed(instruction.action_indices),boolval(instruction.sell_only),current)
        if not np.allclose(expected,parsed(instruction.target_weights),rtol=1e-11,atol=1e-12):raise ValueError('FINAL_SIGNAL_TARGET_TRANSFORMATION')
    value_groups={int(k):g for k,g in values.groupby('k')} if len(values) else {}
    state_records={int(v['k']):v for v in path['eligible']};planstarts={int(p['signal_idx']):p for p in plans}
    if len(state_records)!=len(path['eligible']):raise ValueError('DUPLICATE_ELIGIBLE_STATE')
    if len(planstarts)!=len(plans):raise ValueError('DUPLICATE_PLAN_START')
    checked_features=0;maximum_feature_error=maximum_predict_error=maximum_standardized=0.;outside_range=0
    maximum_nonconstant_standardized=0.;constant_unseen=[]
    actualeligible=set();sale_ids=set();entry_ids=set()
    for row in trace.itertuples():
        k=int(row.k);state=states[k];initial=boolval(row.initial);scheduled=bool(monthly[k]) and not initial
        if int(row.fit_cutoff_idx)!=int(cutoffs[k]) or boolval(row.scheduled)!=scheduled:raise ValueError('TRACE_CALENDAR')
        for field,expected in [('nav',state['nav']),('cash',state['cash']),('gross',state['weights'].sum()),('positions',int((state['units']>1e-12).sum()))]:
            if not np.isclose(float(getattr(row,field)),expected,rtol=1e-11,atol=1e-8):raise ValueError('TRACE_ACCOUNT_STATE')
        if boolval(row.busy)!=state['busy']:raise ValueError('TRACE_BUSY_STATE')
        emitted=by_signal.get(k,pd.DataFrame())
        if initial or scheduled:
            if len(emitted)!=1:raise ValueError('MISSING_MONTHLY_TARGET')
            instruction=emitted.iloc[0];scale=.75 if arm=='STATIC_75' else 1.
            if parsed(instruction.action_indices) is not None or not np.array_equal(parsed(instruction.raw_weights),targets[k]*scale) or boolval(instruction.force)!=initial:raise ValueError('MONTHLY_TARGET_CHANGED')
            continue
        if arm in ('BASE','STATIC_75'):
            if len(emitted):raise ValueError('CONTROL_DISCRETIONARY')
            continue
        active=next((p for p in plans if p['signal_idx']<k and (p['handoff_idx'] is None or k<p['handoff_idx'])),None)
        eligible=k>=ready and not state['busy'] and active is None and np.any(state['units']>1e-12)
        if not eligible:
            if k in state_records or k in value_groups:raise ValueError('INELIGIBLE_STATE_VALUE')
            continue
        actualeligible.add(k)
        if k not in state_records:raise ValueError('MISSING_ELIGIBLE_STATE')
        rec=state_records[k];held=np.flatnonzero(state['units']>1e-12)
        if not np.array_equal(rec['asset_indices'],held) or not np.allclose(rec['units'],state['units'][held],rtol=1e-11,atol=1e-8) or not np.allclose(rec['weights'],state['weights'][held],rtol=1e-11,atol=1e-12) or not np.isclose(rec['nav'],state['nav'],rtol=1e-11):raise ValueError('ELIGIBLE_STATE_MISMATCH')
        group=value_groups.get(k,pd.DataFrame())
        if len(group)!=len(held)*2 or set(zip(group['head'],group.asset.astype(int)))!={(h,int(j)) for h in HEADS for j in held}:raise ValueError('VALUE_ACTION_SET')
        qualified=[]
        for value in group.itertuples():
            x=features(returns,k,state['weights'],state['nav'],int(value.asset),value.head,feature_monthly,weekly,order)
            if boolval(value.valid)!=(x is not None):raise ValueError('VALUE_FEATURE_SUPPORT')
            if x is None:continue
            model=saved[int(cutoffs[k])]['heads'][value.head];v=np.asarray(parsed(value.features),float)
            err=float(np.max(np.abs(v-x)));maximum_feature_error=max(maximum_feature_error,err)
            if not np.allclose(v,x,rtol=1e-10,atol=1e-11):raise ValueError('ACTUAL_STATE_FEATURE_MISMATCH')
            pred,lower=predict_payload(model['models'][modelname],v)
            err=max(abs(pred-value.mean),abs(lower-value.lower));maximum_predict_error=max(maximum_predict_error,err)
            if err>1e-11 or value.model_sha256!=model['hashes'][modelname] or int(value.fit_cutoff_idx)!=int(cutoffs[k]):raise ValueError('VALUE_MODEL_PREDICTION')
            meta=model['meta'];z=(x-np.asarray(meta['scaler']['mean']))/np.asarray(meta['scaler']['scale']);mx=float(np.abs(z).max())
            outside=int(((x<np.asarray(meta['feature_min']))|(x>np.asarray(meta['feature_max']))).sum())
            if not np.isclose(mx,value.max_abs_standardized,rtol=1e-10,atol=1e-11) or outside!=int(value.outside_training_range):raise ValueError('VALUE_SUPPORT_DIAGNOSTIC')
            checked_features+=1;maximum_standardized=max(maximum_standardized,mx);outside_range+=int(outside>0)
            low=np.asarray(meta['feature_min']);high=np.asarray(meta['feature_max']);constant=low==high
            if np.any(~constant):maximum_nonconstant_standardized=max(maximum_nonconstant_standardized,float(np.abs(z[~constant]).max()))
            for feature in np.flatnonzero(constant&(x!=low)):
                constant_unseen.append(dict(k=k,head=value.head,asset=int(value.asset),feature_index=int(feature),
                    feature_value=float(x[feature]),constant_training_value=float(low[feature]),reported_abs_z=float(abs(z[feature]))))
            if pred>0 and lower>0:qualified.append(value)
        chosen=min(qualified,key=lambda p:(-p.lower,p.head,p.isin)) if qualified else None
        if (chosen is not None)!=(k in planstarts):raise ValueError('PLAN_QUALIFICATION')
        if chosen is not None:
            plan=planstarts[k]
            if plan['head']!=chosen.head or plan['asset']!=int(chosen.asset):raise ValueError('PLAN_RANKING')
    if actualeligible!=set(state_records):raise ValueError('ELIGIBLE_STATE_CALENDAR')
    chronology=check_plan_chronology(plans,monthly,weekly,int(path['daily'].k.iloc[-1]))
    for plan in plans:
        k=int(plan['signal_idx']);asset=int(plan['asset']);start=by_signal[k]
        if len(start)!=1:raise ValueError('PLAN_SALE_INSTRUCTION_COUNT')
        sale=start.iloc[0];iid=int(sale.instruction_id);sale_ids.add(iid)
        validate_sale_instruction(sale,plan['head'],asset)
        fills=orders.loc[(orders.instruction_id==iid)&(orders.side=='SELL')]
        stop=int(path['daily'].k.iloc[-1]) if plan['handoff_idx'] is None else min(plan['handoff_idx'],int(path['daily'].k.iloc[-1]))
        completion=confirmed_sale(fills,states,asset,stop)
        if plan['sale_complete_idx']!=completion:raise ValueError('PLAN_SALE_CONFIRMATION')
        expected_attempt=None
        if completion is not None and plan['head']=='REDEPLOY':
            endpoint=int(path['daily'].k.iloc[-1]) if plan['handoff_idx'] is None else plan['handoff_idx']
            possible=[j for j in range(completion+1,endpoint) if weekly[j] and not states[j]['busy']]
            if possible:expected_attempt=possible[0]
        if plan['entry_attempt_idx']!=expected_attempt:raise ValueError('PLAN_FIRST_WEEKLY_ATTEMPT')
        if expected_attempt is not None:
            state=states[expected_attempt];j=candidate(order,returns,expected_attempt,np.flatnonzero(state['units']>1e-12))
            if plan['entry_candidate_idx']!=j:raise ValueError('PLAN_ENTRY_CANDIDATE')
            emitted=by_signal.get(expected_attempt,pd.DataFrame())
            if j is None:
                if len(emitted):raise ValueError('NO_CANDIDATE_INSTRUCTION')
            else:
                if len(emitted)!=1:raise ValueError('ENTRY_INSTRUCTION_COUNT')
                entry=emitted.iloc[0];entry_ids.add(int(entry.instruction_id));raw=np.asarray(parsed(entry.raw_weights))
                if (entry.reason!='REDEPLOY_ENTRY' or parsed(entry.action_indices)!=[j] or not boolval(entry.force) or
                    not np.isclose(raw[j],state['cash']/state['nav'],rtol=1e-12,atol=1e-12) or np.count_nonzero(raw)!=1):raise ValueError('ENTRY_CASH_BUDGET')
    if set(inst.loc[inst.reason.str.endswith('_SALE'),'instruction_id'].astype(int))!=sale_ids:raise ValueError('UNATTRIBUTED_SALE')
    if set(inst.loc[inst.reason=='REDEPLOY_ENTRY','instruction_id'].astype(int))!=entry_ids:raise ValueError('UNATTRIBUTED_ENTRY')
    discretionary=inst.loc[(inst.signal_idx!=int(path['daily'].k.iloc[0])-1)&~inst.signal_idx.map(lambda k:bool(monthly[int(k)]))]
    if set(discretionary.instruction_id.astype(int))!=sale_ids|entry_ids:raise ValueError('UNATTRIBUTED_DISCRETIONARY_INSTRUCTION')
    return dict(pass_all=True,chronology=chronology,eligible_dates=len(actualeligible),verified_values=checked_features,
        maximum_feature_error=maximum_feature_error,maximum_prediction_error=maximum_predict_error,
        maximum_abs_standardized_feature=maximum_standardized,value_rows_outside_training_range=outside_range,
        maximum_abs_standardized_nonconstant_features=maximum_nonconstant_standardized,
        unseen_constant_feature_records=constant_unseen,
        unseen_constant_feature_dates=len(set(v['k'] for v in constant_unseen)),
        sale_instructions=len(sale_ids),entry_instructions=len(entry_ids))

def plot_primary(paths,ready,destination,post):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    colors={'BASE':'#616974','STATIC_75':'#9c8c71','MEAN_CYCLE':'#8773ad','RIDGE_CYCLE':'#258a84','TREE_CYCLE':'#c44039','PRICE_RESET':'#c88e28'}
    fig,(ax,dd)=plt.subplots(2,1,figsize=(12.5,8),sharex=True,gridspec_kw={'height_ratios':[1.6,1],'hspace':.12})
    for arm in ('BASE','STATIC_75','MEAN_CYCLE','RIDGE_CYCLE','TREE_CYCLE','PRICE_RESET'):
        daily=paths[arm+'__NEXT_CLOSE']['daily'];first=0 if not post else int(np.flatnonzero(daily.k.to_numpy()==ready)[0])
        nav=10000. if first==0 else float(daily.nav_close.iloc[first-1]);frame=daily.iloc[first:];dates=pd.DatetimeIndex(frame.date)
        before=dates[0] if first==0 else pd.Timestamp(daily.date.iloc[first-1]);x=pd.DatetimeIndex([before]).append(dates)
        label=arm.replace('_CYCLE','').replace('STATIC_75','Esposizione 75%').replace('PRICE_RESET','OLC113')
        width=2.3 if arm=='TREE_CYCLE' else 1.2
        ax.plot(x,np.r_[nav,frame.nav_close]/nav,label=label,color=colors[arm],linewidth=width,linestyle='--' if arm=='PRICE_RESET' else '-')
        chain=np.r_[nav,frame[['nav_open','nav_close']].to_numpy().ravel()];draw=chain/np.maximum.accumulate(chain)-1
        dd.plot(pd.DatetimeIndex([before]).append(dates.repeat(2)),draw,color=colors[arm],linewidth=width)
    ax.set_yscale('log');ax.set_ylabel('Capitale relativo · scala logaritmica');ax.legend(ncol=3,frameon=False,loc='upper left',fontsize=9)
    dd.set_ylabel('Drawdown campionato');dd.yaxis.set_major_formatter(FuncFormatter(lambda x,_:f'{x:.0%}'));dd.axhline(0,color='#aaa',linewidth=.6)
    for a in (ax,dd):a.grid(True,alpha=.18);a.spines[['top','right']].set_visible(False)
    title='Periodo comune dopo la disponibilità dei modelli' if post else 'Intero periodo storico, inclusa la fase iniziale senza interventi'
    fig.suptitle('OLC114 · Piani completi di protezione e rientro\n'+title,fontsize=14,x=.08,ha='left',y=.98)
    fig.text(.08,.025,'EUR · Costi inclusi · Esecuzione alla chiusura successiva · Campione storico già analizzato; risultati esplorativi',fontsize=9,color='#555')
    fig.subplots_adjust(left=.09,right=.98,top=.87,bottom=.09);fig.savefig(destination,dpi=160);plt.close(fig)

def run_audit(root=ROOT):
    root=Path(root).resolve();results=root/'results';hashes={};checks={}
    def record(path):
        path=Path(path);hashes[str(path.resolve().relative_to(root.parent))]=sha(path);return path
    def read_json(path):
        path=record(path);raw=path.read_bytes();return json.loads(gzip.decompress(raw) if path.suffix=='.gz' else raw)
    def read_csv(path):return pd.read_csv(record(path),float_precision='round_trip')
    def write_json(path,value):Path(path).write_text(json.dumps(audit._jsonable(value),indent=2,allow_nan=False)+'\n')
    def write_csv(name,rows):pd.DataFrame(rows).to_csv(results/name,index=False)
    freeze=read_json(root/'docs/EXPERIMENT_FREEZE.json');freeze_sha=sha(root/'docs/EXPERIMENT_FREEZE.json')
    for filename in ('BANK_FREEZE.json','EXPERIMENT_FREEZE.json'):
        f=read_json(root/'docs'/filename)
        for section in ('code_hashes','input_hashes'):
            for name,value in f[section].items():
                if sha(record(root/name))!=value:raise ValueError('FROZEN_SOURCE_CHANGED:'+name)
        if sha(record(root/'docs/DESIGN_AND_PROTOCOL.md'))!=f['protocol_sha256']:raise ValueError('FROZEN_PROTOCOL_CHANGED')
    manifest=read_json(results/'RUN_MANIFEST.json');expected={f'{a}__{s}' for a in ARMS for s in TERMS}
    if manifest['completed_paths']!=15 or set(manifest['completed_path_ids'])!=expected or manifest['primary_arm']!='TREE_CYCLE' or manifest['freeze_sha256']!=freeze_sha:raise ValueError('INCOMPLETE_MATRIX')
    if pd.Timestamp(manifest['start_utc'])<pd.Timestamp(freeze['created_utc']):raise ValueError('RUN_PRECEDES_FREEZE')
    checks['source_freeze_and_complete_matrix']=True
    with np.load(record(root.parent/'olc110/source/data/XETRA_EUR_ETF.npz'),allow_pickle=False) as f:
        panel={k:f[k] for k in ('dates','names','C','observed')}
    dates=np.asarray(panel['dates'],dtype='datetime64[D]');cal=pd.DatetimeIndex(dates);month=cal.to_period('M');week=cal.to_period('W-FRI')
    monthly=np.r_[month[:-1]!=month[1:],False];weekly=np.r_[week[:-1]!=week[1:],False]
    # Feature-only month endpoint includes the known final calendar month, as in the frozen convention.
    feature_monthly=monthly.copy();feature_monthly[-1]=cal[-1].normalize()==(cal[-1]+pd.offsets.BMonthEnd(0)).normalize()
    with np.load(record(root.parent/'olc111/data/CAUSAL_SELECTIONS.npz'),allow_pickle=False) as f:targets=f['targets']
    order=read_json(root/'data/SELECTED_ORDER.json');valid=np.asarray(panel['observed'],bool)&np.isfinite(panel['C'])&(panel['C']>0)
    marks=pd.DataFrame(np.where(valid,panel['C'],np.nan)).ffill().to_numpy()
    with np.errstate(divide='ignore',invalid='ignore'):returns=np.log(pd.DataFrame(marks)/pd.DataFrame(marks).shift(1)).to_numpy()
    bank={h:dict(np.load(record(root/f'data/BANK_{h}.npz'),allow_pickle=False)) for h in HEADS}
    bank_summary=read_json(root/'data/BANK_SUMMARY.json')
    for name,value in bank_summary['artifact_hashes'].items():
        if sha(record(root/'data'/name))!=value:raise ValueError('BANK_HASH')
    eventrows={h:[] for h in HEADS};events=[]
    base_reference=read_csv(root.parent/'olc111/data/BASELINE_PRIMARY_DAILY.csv.gz').set_index('k').nav_close
    for line in (root/'data/BANK_EVENTS.jsonl').read_text().splitlines():
        e=json.loads(line);v=e.pop('event_sha256')
        if hashlib.sha256(canonical(e)+b'\n').hexdigest()!=v:raise ValueError('BANK_EVENT_HASH')
        if e['status']=='OK':
            if (e['terminal_idx']!=e['signal_idx']+42 or e['base_replay_error']>1e-7 or
                abs(e['nav']['BASE']-base_reference.loc[e['terminal_idx']])>1e-7):raise ValueError('BANK_TERMINAL')
            for row in e['records']:
                if not np.isclose(row['y'],np.log(e['nav'][f"{row['head']}:{row['asset']}"]/e['nav']['BASE']),rtol=1e-12,atol=1e-12):raise ValueError('BANK_ADVANTAGE')
                eventrows[row['head']].append(row)
        elif e['records']:raise ValueError('CENSORED_BANK_ROWS')
        events.append(e)
    for head in HEADS:
        for key in ('X','y','signal_idx','terminal_idx','asset_idx'):
            values=[r['asset' if key=='asset_idx' else key] for r in eventrows[head]]
            if not np.array_equal(values,bank[head][key]):raise ValueError('BANK_NPZ_EVENT_MISMATCH')
    checks['bank_hashes_endpoint_and_row_reconciliation']=True
    readiness=read_json(results/'FIT_READINESS.json');begin=int(np.flatnonzero(dates==np.datetime64('2020-03-02'))[0]);end=len(dates)-1
    first=np.r_[True,month[1:]!=month[:-1]];cutoffs=np.maximum(np.maximum.accumulate(np.where(first,np.arange(len(dates)),0)),begin-1)
    actual_cutoffs=np.unique(cutoffs[begin-1:end]);saved={int(k):read_json(results/f'FITS/FIT_{k:06d}.json.gz') for k in actual_cutoffs}
    fitcheck=validate_fits(saved,bank,dates,cutoffs,freeze_sha);ready=fitcheck['activation_idx'];post=ready+1
    if (readiness['raw_all_heads_first_ready_idx']!=fitcheck['raw_first_ready_idx'] or readiness['all_heads_first_ready_idx']!=ready or
        readiness['postwarmup_start_idx']!=post or readiness['all_heads_first_ready_date']!=str(dates[ready]) or
        readiness['postwarmup_start_date']!=str(dates[post]) or not np.array_equal(readiness['fitted_calendar_cutoffs'],actual_cutoffs)):
        raise ValueError('READINESS_RECONCILIATION')
    checks['mature_models_date_weights_paired_bootstrap']=True
    scores=read_csv(results/'SCORES.csv');paths={};diagnostics={};compact=[];planrows=[];annual=[];attemptrows=[]
    parity_controls={};native_plan_fields=['plans_started','plans_handed_off','plans_right_censored']
    for arm in ARMS:
        for scenario in TERMS:
            path_id=f'{arm}__{scenario}';folder=results/path_id
            loaded={k:read_csv(folder/n) for k,n in [('daily','DAILY.csv.gz'),('orders','ORDERS.csv.gz'),('instructions','INSTRUCTIONS.csv.gz'),('trace','POLICY_TRACE.csv.gz'),('values','PLAN_VALUES.csv.gz')]}
            loaded.update(arm=arm,plans=read_json(folder/'PLAN_SUMMARIES.json.gz'),native=read_json(folder/'METRICS.json'))
            raw=gzip.decompress(record(folder/'ELIGIBLE_STATES.jsonl.gz').read_bytes());loaded['eligible']=[json.loads(s) for s in raw.splitlines()]
            native=loaded['native'];receipt=read_json(folder/'PATH_RECEIPT.json')
            if (receipt['path_id']!=path_id or native['path_id']!=path_id or receipt['arm']!=arm or receipt['scenario']!=scenario or receipt['freeze_sha256']!=freeze_sha or native['experiment_freeze_sha256']!=freeze_sha or digest(native)!=receipt['metrics_payload_sha256'] or set(receipt['artifacts'])!=set(ARTIFACTS)):raise ValueError('PATH_RECEIPT_IDENTITY')
            for name,value in receipt['artifacts'].items():
                if sha(record(folder/name))!=value:raise ValueError('PATH_ARTIFACT_HASH')
            daily=loaded['daily'];orders=loaded['orders'];trace=loaded['trace'];instructions=loaded['instructions']
            audit.validate_result_calendar(daily,dates,start_idx=begin,end_idx=end)
            if not np.array_equal(trace.k,np.arange(begin-1,end)) or not np.array_equal(pd.DatetimeIndex(trace.date).to_numpy(dtype='datetime64[D]'),dates[begin-1:end]):raise ValueError('TRACE_CALENDAR_INCOMPLETE')
            whole=audit.performance_window(daily);postmetrics=audit.performance_window(daily,start_idx=post)
            years=whole['days']/audit.YEAR_DAYS;navs=daily.set_index('date').nav_open.loc[orders.date].to_numpy()
            whole.update(orders=len(orders),costs=float(orders.cost.sum()),instructions=len(instructions),
                trading_days=int(orders.date.nunique()),trading_days_per_year=float(orders.date.nunique()/years),
                two_sided_turnover_per_year=float((orders.notional.to_numpy()/navs).sum()/years))
            monetary,states,attempts=reconcile_account(daily,orders,instructions,panel,scenario)
            markscheck,violations=audit.held_mark_audit(daily,orders,panel)
            if not monetary['pass_all'] or not markscheck['ledger_reconciliation_pass'] or not markscheck['valuation_support_pass'] or monetary['deferred_sessions']!=native['deferred_sessions']:raise ValueError('ACCOUNT_RECONCILIATION:'+path_id)
            policy=audit_policy(loaded,states,marks,returns,dates,monthly,feature_monthly,weekly,targets,order,saved,cutoffs,ready)
            fullpar=audit.metric_parity(whole,native);postpar=audit.metric_parity(postmetrics,native,prefix='post_')
            sc=scores.loc[scores.path_id==path_id].iloc[0].to_dict();scorepar=audit.metric_parity(whole,sc);scorepost=audit.metric_parity(postmetrics,sc,prefix='post_')
            if not all(p['pass_all'] for p in (fullpar,postpar,scorepar,scorepost)):raise ValueError('METRIC_PARITY:'+path_id)
            if arm in ('BASE','STATIC_75') and scenario!='DELAY1_CLOSE':
                old=root.parent/'olc111/results'/path_id
                equal=daily.equals(read_csv(old/'DAILY.csv.gz')) and orders.equals(read_csv(old/'ORDERS.csv.gz'))
                if not equal:raise ValueError('CONTROL_PARITY:'+path_id)
                parity_controls[path_id]=True
            if arm.endswith('_CYCLE'):
                warmup=audit.warmup_replication(paths['BASE__'+scenario]['daily'],daily,ready_idx=ready)
                if not warmup['exact_match']:raise ValueError('WARMUP_PARITY:'+path_id)
            if arm=='MEAN_CYCLE':
                if not daily.equals(paths['BASE__'+scenario]['daily']) or not orders.equals(read_csv(results/f'BASE__{scenario}/ORDERS.csv.gz')):
                    raise ValueError('MEAN_CONTROL_NOT_EXACT_BASE')
            if [native[x] for x in native_plan_fields]!=[len(loaded['plans']),policy['chronology']['handoffs'],policy['chronology']['right_censored']]:raise ValueError('NATIVE_PLAN_COUNTS')
            diagnostics[path_id]=dict(whole=whole,post=postmetrics,account=monetary,held_marks=markscheck,policy=policy,
                                      metric_parity=dict(full=fullpar,post=postpar,scores=scorepar,scores_post=scorepost))
            compact.append(dict(path_id=path_id,arm=arm,scenario=scenario,cagr=whole['cagr'],maxdd=whole['maxdd_sampled'],
                post_cagr=postmetrics['cagr'],post_maxdd=postmetrics['maxdd_sampled'],initial_post_nav=postmetrics['initial_nav'],
                end_equity=whole['end_equity'],orders=len(orders),costs=float(orders.cost.sum()),mean_exposure=whole['mean_exposure'],
                cash_days=whole['full_cash_days'],plans=len(loaded['plans']),redeployments=policy['entry_instructions'],
                full_nonoverlap42=policy['chronology']['complete_nonoverlap42']))
            for p in loaded['plans']:
                sale_iid=int(instructions.loc[instructions.signal_idx==p['signal_idx'],'instruction_id'].iloc[0])
                sale_orders=orders.loc[(orders.instruction_id==sale_iid)&(orders.side=='SELL')]
                entry_orders=pd.DataFrame()
                if p['entry_attempt_idx'] is not None and p['entry_candidate_idx'] is not None:
                    entry_iid=int(instructions.loc[instructions.signal_idx==p['entry_attempt_idx'],'instruction_id'].iloc[0])
                    entry_orders=orders.loc[(orders.instruction_id==entry_iid)&(orders.side=='BUY')]
                planrows.append(dict(path_id=path_id,**{k:v for k,v in p.items() if k not in ('selection','trace')},
                    actual_sale_last_idx=None if sale_orders.empty else int(sale_orders.execution_idx.max()),
                    actual_sale_orders=len(sale_orders),actual_entry_buy_orders=len(entry_orders),
                    actual_entry_first_idx=None if entry_orders.empty else int(entry_orders.execution_idx.min())))
            attempts.insert(0,'path_id',path_id);attemptrows.extend(attempts.to_dict('records'))
            for year,frame in daily.groupby(pd.to_datetime(daily.date).dt.year):
                m=audit.performance_window(daily,start_idx=int(frame.k.iloc[0]),end_idx=int(frame.k.iloc[-1]))
                annual.append(dict(path_id=path_id,year=int(year),annual_return=m['cumulative'],log_growth=m['log_growth'],maxdd=m['maxdd_sampled']))
            paths[path_id]=dict(daily=daily)
            print('AUDITED',path_id,flush=True)
    checks['all15_accounts_costs_masks_calendar_marks']=True;checks['all15_actual_policy_states_plans_and_entry_budget']=True
    checks['four_exact_prior_controls']=len(parity_controls)==4;checks['whole_common_metrics_and_warmup']=True
    checks['three_exact_mean_baseline_paths']=True
    comparisons=[];criteria=[]
    for scenario in TERMS:
        if scenario!='DELAY1_CLOSE':paths['PRICE_RESET__'+scenario]=dict(daily=read_csv(root.parent/f'olc113/results/PRICE_RESET__{scenario}/DAILY.csv.gz'))
        for arm in ARMS[2:]:
            pid=arm+'__'+scenario
            for reference in ('BASE','STATIC_75','MEAN_CYCLE','RIDGE_CYCLE')+(('PRICE_RESET',) if scenario!='DELAY1_CLOSE' else ()):
                if reference==arm:continue
                for window,idx in [('whole',None),('post',post)]:
                    value=compare.compare_accounts(paths[pid]['daily'],paths[reference+'__'+scenario]['daily'],start_idx=idx)
                    comparisons.append(dict(path_id=pid,reference=reference,window=window,**value))
            criterion=material_criterion(diagnostics[pid],diagnostics['BASE__'+scenario])
            criteria.append(dict(path_id=pid,primary=arm=='TREE_CYCLE',scenario=scenario,
                material_both_windows=criterion['material_both_windows'],target30_whole=criterion['target30_whole'],target30_post=criterion['target30_post'],
                cagr_gain=criterion['whole']['cagr_gain'],dd_change=criterion['whole']['maxdd_change'],
                post_cagr_gain=criterion['post']['cagr_gain'],post_dd_change=criterion['post']['maxdd_change']))
    forecast=read_csv(results/'PREQUENTIAL_FORECASTS.csv.gz');forecast_scores=[];max_pred_error=0.
    expected_forecasts=sum(len(b['y']) for b in bank.values())*3
    if len(forecast)!=expected_forecasts or forecast.duplicated(['head','arm','signal_idx','asset_idx']).any():raise ValueError('FORECAST_COVERAGE')
    lookup={(h,int(k),int(j)):i for h,b in bank.items() for i,(k,j) in enumerate(zip(b['signal_idx'],b['asset_idx']))}
    for row in forecast.itertuples():
        b=bank[row.head];i=lookup[(row.head,int(row.signal_idx),int(row.asset_idx))];model=saved[int(cutoffs[row.signal_idx])]['heads'][row.head]
        if int(row.terminal_idx)!=row.signal_idx+42 or row.outcome!=b['y'][i] or int(row.fit_cutoff_idx)!=int(cutoffs[row.signal_idx]):raise ValueError('FORECAST_BANK_ALIGNMENT')
        if boolval(row.head_ready)!=(model is not None) or boolval(row.all_heads_ready)!=(row.signal_idx>=ready):raise ValueError('FORECAST_READY_FLAG')
        if model is not None:
            pred,lower=predict_payload(model['models'][row.arm],b['X'][i]);max_pred_error=max(max_pred_error,abs(pred-row.prediction),abs(lower-row.lower))
            if row.model_sha256!=model['hashes'][row.arm] or boolval(row.positive_buffer)!=(pred>0 and lower>0):raise ValueError('FORECAST_MODEL_ALIGNMENT')
        elif not pd.isna(row.prediction) or not pd.isna(row.lower) or boolval(row.positive_buffer):raise ValueError('FORECAST_BEFORE_READY')
    if max_pred_error>1e-11:raise ValueError('FORECAST_PREDICTION')
    for (head,arm),g in forecast.loc[forecast.all_heads_ready].groupby(['head','arm']):
        w=1./g.groupby('signal_idx').signal_idx.transform('size').to_numpy();w/=w.sum();e=(g.prediction-g.outcome).to_numpy();positive=g.loc[g.positive_buffer]
        wp=1./positive.groupby('signal_idx').signal_idx.transform('size').to_numpy() if len(positive) else np.array([])
        forecast_scores.append(dict(head=head,arm=arm,mse=float(w@(e*e)),bias=float(w@e),n_dates=int(g.signal_idx.nunique()),
            positive_dates=int(positive.signal_idx.nunique()),positive_nonoverlap42=nonoverlap(positive.signal_idx),
            positive_realized_mean=float(wp@positive.outcome.to_numpy()/wp.sum()) if len(positive) else None))
    native_forecast=read_csv(results/'FORECAST_SCORES.csv')
    for row in forecast_scores:
        r=native_forecast.loc[(native_forecast['head']==row['head'])&(native_forecast.arm==row['arm'])].iloc[0]
        if not np.isclose(row['mse'],r.mse,rtol=1e-11,atol=1e-13) or not np.isclose(row['bias'],r.bias,rtol=1e-11,atol=1e-13):raise ValueError('FORECAST_SCORE_RECONCILIATION')
    mse={(r['head'],r['arm']):r['mse'] for r in forecast_scores}
    for row in forecast_scores:
        row['mse_delta_vs_mean']=row['mse']-mse[(row['head'],'MEAN')]
        row['mse_delta_vs_ridge']=row['mse']-mse[(row['head'],'RIDGE')]
    ranking=read_csv(results/'FORECAST_RANKING.csv.gz');ranking_summaries=[]
    if ranking.duplicated(['arm','signal_idx']).any():raise ValueError('FORECAST_RANKING_DUPLICATE')
    ranking_lookup=ranking.set_index(['arm','signal_idx']);ranking_count=0
    for (arm,k),g in forecast.loc[forecast.all_heads_ready].groupby(['arm','signal_idx']):
        ranked=g.loc[g.positive_buffer].sort_values(['lower','head','isin'],ascending=[False,True,True]);choice=None if ranked.empty else ranked.iloc[0]
        row=ranking_lookup.loc[(arm,k)];actual=0. if choice is None else float(choice.outcome);best=max(0.,float(g.outcome.max()))
        if (boolval(row.chosen)!=(choice is not None) or not np.isclose(actual,row.selected_realized_advantage,rtol=1e-12,atol=1e-12) or
            not np.isclose(best,row.hindsight_best_advantage,rtol=1e-12,atol=1e-12) or not np.isclose(best-actual,row.ranking_regret,rtol=1e-12,atol=1e-12)):
            raise ValueError('FORECAST_RANKING_VALUES')
        if choice is not None and (row.selected_head!=choice['head'] or row.selected_asset!=choice.asset_idx):raise ValueError('FORECAST_RANKING_ACTION')
        ranking_count+=1
    if ranking_count!=len(ranking):raise ValueError('FORECAST_RANKING_COVERAGE')
    for arm,g in ranking.groupby('arm'):
        ranking_summaries.append(dict(arm=arm,dates=len(g),selected_dates=int(g.chosen.sum()),
            mean_selected_advantage=float(g.selected_realized_advantage.mean()),mean_regret=float(g.ranking_regret.mean()),
            diagnostic_only=True,overlapping_not_additive=True))
    checks['prequential_saved_predictions_and_date_balanced_scores']=True
    write_csv('INDEPENDENT_SCORES.csv',compact);write_csv('INDEPENDENT_COMPARISONS.csv',comparisons)
    write_csv('INDEPENDENT_CRITERIA.csv',criteria);write_csv('INDEPENDENT_PLANS.csv',planrows)
    write_csv('INDEPENDENT_ANNUAL_RETURNS.csv',annual);write_csv('INDEPENDENT_EXECUTION_ATTEMPTS.csv',attemptrows)
    write_csv('INDEPENDENT_FORECAST_SCORES.csv',forecast_scores);write_csv('INDEPENDENT_FORECAST_RANKING_SUMMARY.csv',ranking_summaries)
    robustness={arm:all(next(c for c in criteria if c['path_id']==arm+'__'+s)['cagr_gain']>0 and next(c for c in criteria if c['path_id']==arm+'__'+s)['post_cagr_gain']>0 for s in TERMS) for arm in ARMS[2:]}
    diagnosis=dict(all_checks_pass=all(checks.values()),checks=checks,readiness=readiness,fit_audit=fitcheck,
        bank=bank_summary,control_replication=parity_controls,paths=diagnostics,criteria=criteria,
        cagr_gain_direction_survives_both_stresses=robustness,forecast_scores=forecast_scores,
        max_forecast_prediction_error=max_pred_error,new_fits=0,new_policy_replays=0,pristine_holdout=False,
        no_delayed_OLC113_comparator=True)
    write_json(results/'INDEPENDENT_DIAGNOSTICS.json',diagnosis)
    for postflag,name in [(True,'INDEPENDENT_PRIMARY_POSTWARMUP.png'),(False,'INDEPENDENT_PRIMARY_FULL.png')]:plot_primary(paths,post,results/name,postflag)
    for file in (Path(__file__),root/'tests/test_cycle_audit.py',ROOT.parent/'olc111/src/analyze_results.py',ROOT.parent/'olc112/src/analyze_results.py'):record(file)
    write_json(results/'INDEPENDENT_SOURCE_MANIFEST.json',dict(files=hashes,source_count=len(hashes)))
    outputs={p.name:sha(p) for p in sorted(results.glob('INDEPENDENT_*')) if p.is_file() and p.suffix!='.log' and p.name!='INDEPENDENT_OUTPUT_MANIFEST.json'}
    write_json(results/'INDEPENDENT_OUTPUT_MANIFEST.json',dict(files=outputs))
    print('OLC114_INDEPENDENT_AUDIT_COMPLETE',len(checks),'checks',len(hashes),'sources',flush=True)
    return diagnosis

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=ROOT);args=parser.parse_args();run_audit(args.root)
