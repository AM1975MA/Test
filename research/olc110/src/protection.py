"""Frozen OLC110 cash/reentry rules. No fitting, future labels, or trading API."""
from __future__ import annotations
from copy import deepcopy
import numpy as np
import pandas as pd
from dedup_selectors import make_policy as make_selector, pair_corr

ARMS=('BASE','STATIC_HALF','STATIC_75','REFRESH_WEEKLY',
      'EXIT21_MONTHLY','EXIT21_SLOW','EXIT21_FAST','EXIT21_STAGED',
      'EXIT63_STAGED','TRAIL15_STAGED','VOLTRAIL_STAGED',
      'EXIT21_STAGED_FRESHW','EXIT21_STAGED_FRESHD')
CONTROL_ARMS=ARMS[:4]


def prepare_timing_features(panel,f):
    out=f.copy();c=pd.DataFrame(f['C']);lr=np.log(c/c.shift(1))
    out.update(sma10=c.rolling(10,min_periods=10).mean().to_numpy(),
               sma21=c.rolling(21,min_periods=21).mean().to_numpy(),
               m5=np.log(c/c.shift(5)).to_numpy(),
               high5_prev=c.shift(1).rolling(5,min_periods=5).max().to_numpy(),
               sigma21=lr.rolling(21,min_periods=21).std(ddof=1).to_numpy())
    return out


class ProtectionPolicy:
    def __init__(self,panel,f,monthly,weekly,arm,start_index):
        if arm not in ARMS or arm in CONTROL_ARMS:raise ValueError('PROTECTED_ARM')
        self.panel=panel;self.f=f;self.monthly=np.asarray(monthly,bool)
        self.weekly=np.asarray(weekly,bool);self.arm=arm;self.start_index=int(start_index)
        self.names=np.asarray(panel['names']);self.n=len(self.names)
        self.dates=pd.DatetimeIndex(panel['dates']);self.observed=np.asarray(panel['observed'],bool)
        self.selector=make_selector(panel,f,{},'DEDUP_DUAL_TREND_OPP')
        self.kind=('EXIT63' if arm.startswith('EXIT63') else
                   'TRAIL15' if arm.startswith('TRAIL15') else
                   'VOLTRAIL' if arm.startswith('VOLTRAIL') else 'EXIT21')
        self.reentry=('MONTHLY' if arm.endswith('_MONTHLY') else
                      'SLOW' if arm.endswith('_SLOW') else
                      'FAST' if arm.endswith('_FAST') else 'STAGED')
        self.fresh='W' if arm.endswith('_FRESHW') else ('D' if arm.endswith('_FRESHD') else None)
        self.slots=[];self.last_intent=np.zeros(self.n);self.last_k=None;self.trace=[]

    def width_at(self,k,j):
        value=float(self.f['sigma21'][k,j])
        return float(np.clip(2.5*np.sqrt(5.)*value,.05,.20)) if np.isfinite(value) else .20

    def bad(self,k,j,width=None):
        if j is None or not self.observed[k,j]:return False
        c=float(self.f['C'][k,j])
        if self.kind=='EXIT21':return bool(c<self.f['sma21'][k,j] and self.f['m5'][k,j]<0)
        if self.kind=='EXIT63':return bool(c<self.f['sma63'][k,j] and self.f['m21'][k,j]<0)
        barrier=.15 if self.kind=='TRAIL15' else (self.width_at(k,j) if width is None else width)
        return bool(c/self.f['peak63'][k,j]-1 <= -barrier)

    def slow(self,k,j,width=None):
        if j is None or not self.observed[k,j]:return False
        return bool(self.f['C'][k,j]>self.f['sma63'][k,j] and self.f['m21'][k,j]>0
                    and not self.bad(k,j,width)
                    and (self.kind!='VOLTRAIL' or not self.bad(k,j,self.width_at(k,j))))

    def fast(self,k,j):
        if j is None or not self.observed[k,j]:return False
        c=self.f['C'][k,j]
        return bool(c>self.f['high5_prev'][k,j] and c>self.f['sma10'][k,j]
                    and self.f['m5'][k,j]>0)

    def rebound_bad(self,k,j):
        return bool(j is not None and self.observed[k,j] and
                    self.f['C'][k,j]<self.f['sma10'][k,j] and self.f['m5'][k,j]<0)

    def new_slot(self,k,j):
        if j is None:
            return dict(primary=None,asset=None,state='CASH',level=0.,width=None,
                        entry_signal=None,first_fill_idx=None,new_assignment_at=int(k),vacancy_confirmed=True)
        width=self.width_at(k,j)
        blocked=not self.observed[k,j] or self.bad(k,j,width)
        return dict(primary=int(j),asset=int(j),state='CASH' if blocked else 'NORMAL',
                    level=0. if blocked else 1.,width=width,
                    entry_signal=None if blocked else int(k),first_fill_idx=None,new_assignment_at=int(k),
                    vacancy_confirmed=False)

    def select_monthly(self,k,current):
        target,meta=self.selector(k,current)
        # The selector's explicit order is retained, rather than ticker-index order.
        ids=list(meta['selected_indices']);old=deepcopy(self.slots);used=set();new=[]
        for j in ids[:2]:
            matches=[i for i,s in enumerate(old) if i not in used and s['asset']==j]
            matches.sort(key=lambda i:(-int(old[i]['level']>0),
                                       int(old[i]['vacancy_confirmed']),
                                       -int(old[i]['primary']==j),i))
            match=matches[0] if matches else None
            if match is None:s=self.new_slot(k,j)
            else:
                used.add(match);s=old[match];s['primary']=int(j)
            new.append(s)
        while len(new)<2:new.append(self.new_slot(k,None))
        self.slots=new
        return meta

    def intent(self):
        w=np.zeros(self.n)
        for s in self.slots:
            if s['asset'] is not None and s['level']>0:w[s['asset']]+=.5*s['level']
        if np.any(w>.5+1e-12) or w.sum()>1+1e-12:raise AssertionError('DUPLICATE_SLOT')
        return w

    def enter(self,s,k,j,state,level):
        s.update(asset=int(j),state=state,level=float(level),entry_signal=int(k),first_fill_idx=None,
                 vacancy_confirmed=False)
        if state=='NORMAL':s['width']=self.width_at(k,j)

    def fresh_candidate(self,k,slot_index,current):
        f=self.f;lf=f['liquid_features'];c=f['C'][k]
        pool=(f['liquid_eligible'][k] & (f['b21'][k]>0) &
              (lf['rank_b21'][k]>=2/3) & (lf['rank_a21'][k]<2/3) &
              (f['acceleration21'][k]>0) & (c>f['sma63'][k]) &
              (f['m252'][k]>0) & (f['m63'][k]>0) & (c>f['sma200'][k]) &
              (c>f['sma10'][k]) & (f['m5'][k]>0) & self.observed[k])
        used={int(j) for j in np.flatnonzero(current>1e-10)}
        committed=set()
        for pos,s in enumerate(self.slots):
            if pos!=slot_index and s['asset'] is not None:
                used.add(s['asset'])
                if s['level']>0:committed.add(s['asset'])
        compare=set(np.flatnonzero(current>1e-10).tolist())|committed
        ranked=sorted(np.flatnonzero(pool).tolist(),
                      key=lambda j:(-float(f['acceleration21'][k,j]),str(self.names[j])))
        for j in ranked:
            if j in used:continue
            if all(pair_corr(f,k,j,other)<=.85+1e-12 for other in compare):return int(j)
        return None

    def __call__(self,k,current,context):
        k=int(k);current=np.asarray(current,float)
        if self.last_k is not None and k<=self.last_k:raise ValueError('NONMONOTONE_POLICY_TIME')
        if current.shape!=(self.n,):raise ValueError('CURRENT_WEIGHTS')
        scheduled=bool(context['scheduled'] or context['initial'])
        busy=context.get('pending') is not None or len(context.get('queued',()))>0
        selection_meta={}
        if scheduled:selection_meta=self.select_monthly(k,current)
        if len(self.slots)!=2:raise ValueError('POLICY_NOT_INITIALIZED')
        units=np.asarray(context['units']);last_buy=np.asarray(context['last_buy_idx'])
        changes=[];exited=set();entered=set();confirmed=set();fresh=set()
        # Existing positions are processed before admissions so other slots'
        # desired commitments are known when a new opportunity is considered.
        for i,s in enumerate(self.slots):
            j=s['asset']
            if j is None:continue
            if s['state']=='NORMAL' and self.bad(k,j,s['width']):
                s.update(state='CASH',level=0.,first_fill_idx=None,vacancy_confirmed=False)
                changes.append(f'EXIT:{i}:{j}');exited.add(j)
            elif s['state']=='REBOUND':
                if (s['first_fill_idx'] is None and units[j]>1e-10 and
                    last_buy[j]>=s['entry_signal']+1):
                    s['first_fill_idx']=int(last_buy[j])
                if self.rebound_bad(k,j):
                    s.update(state='CASH',level=0.,first_fill_idx=None,vacancy_confirmed=False)
                    changes.append(f'REBOUND_EXIT:{i}:{j}');exited.add(j)
                elif (s['first_fill_idx'] is not None and k>s['first_fill_idx'] and
                      self.slow(k,j,s['width'])):
                    s.update(state='NORMAL',level=1.,width=self.width_at(k,j))
                    changes.append(f'CONFIRM:{i}:{j}');confirmed.add(j)

        # Once liquidation has actually been observed, later units of the same
        # fund may belong to the other slot. Retain that confirmed vacancy.
        for s in self.slots:
            if (s['state']=='CASH' and not busy and
                (s['asset'] is None or units[s['asset']]<=1e-10)):
                s['vacancy_confirmed']=True
        # Admission uses actual vacancy. A desired exit or missing quote cannot
        # create cash. Calendar changes still issue the full scheduled target.
        free_cash=float(context['cash'])>max(1e-8,.03*float(context['nav']))
        for i,s in enumerate(self.slots):
            if s['state']!='CASH' or not free_cash or busy:continue
            if s['new_assignment_at']==k:continue
            outgoing=s['asset']
            if not s['vacancy_confirmed'] or outgoing in exited:continue
            j=s['primary']
            base_available=not(j is not None and any(pos!=i and other['asset']==j and other['level']>0
                                     for pos,other in enumerate(self.slots)))
            same_width=s['width'] if j==s['asset'] else None
            if base_available and (self.reentry!='MONTHLY' or scheduled) and self.slow(k,j,same_width):
                self.enter(s,k,j,'NORMAL',1.);changes.append(f'REENTER_SLOW:{i}:{j}');entered.add(j)
            elif base_available and self.reentry in ('FAST','STAGED') and self.fast(k,j):
                self.enter(s,k,j,'REBOUND',1. if self.reentry=='FAST' else .5)
                changes.append(f'REENTER_FAST:{i}:{j}');entered.add(j)
            elif (self.fresh is not None and not scheduled and
                  (self.fresh=='D' or self.weekly[k])):
                candidate=self.fresh_candidate(k,i,current)
                if candidate is not None:
                    self.enter(s,k,candidate,'REBOUND',.5)
                    changes.append(f'FRESH:{i}:{candidate}');fresh.add(candidate)

        desired=self.intent()
        mask=np.abs(desired-self.last_intent)>1e-12
        emitted=scheduled or (not busy and bool(mask.any()))
        reason='INITIAL' if context['initial'] else 'SCHEDULED' if scheduled else (
            'MIXED' if sum(bool(x) for x in [exited,entered,confirmed,fresh])>1 else
            'EXIT' if exited else 'REENTRY' if entered else 'CONFIRM' if confirmed else
            'FRESH' if fresh else 'DEFERRED_STATE')
        if emitted:
            sell_only=bool(not scheduled and np.all(desired[mask]<=current[mask]+1e-12))
            answer=dict(weights=desired.copy(),action_mask=None if scheduled else mask.copy(),
                        sell_only=sell_only,force=bool(context['initial'] or sell_only or exited),reason=reason,
                        meta=dict(arm=self.arm,changes=changes,slots=deepcopy(self.slots),
                                  book_busy=bool(busy),
                                  selection=selection_meta))
            self.last_intent=desired.copy()
        else:answer=None
        for pos,s in enumerate(self.slots):
            j=s['asset']
            self.trace.append(dict(k=k,date=str(self.dates[k].date()),arm=self.arm,slot=pos,
                primary_index=s['primary'],asset_index=j,
                primary_isin=None if s['primary'] is None else str(self.names[s['primary']]),
                asset_isin=None if j is None else str(self.names[j]),state=s['state'],
                level=s['level'],nominal_weight=.5*s['level'],actual_weight=0. if j is None else float(current[j]),
                first_fill_idx=s['first_fill_idx'],entry_signal=s['entry_signal'],width=s['width'],
                vacancy_confirmed=s['vacancy_confirmed'],
                busy=bool(busy),scheduled=scheduled,action_emitted=bool(emitted),reason=reason,
                observed=False if j is None else bool(self.observed[k,j]),
                exit_condition=self.bad(k,j,s['width']),slow_condition=self.slow(k,j,s['width']),
                fast_condition=self.fast(k,j),rebound_failure=self.rebound_bad(k,j)))
        self.last_k=k
        return answer


def make_account_policy(panel,f,monthly_mask,weekly_mask,arm,start_index):
    return ProtectionPolicy(panel,f,monthly_mask,weekly_mask,arm,start_index)
