from run23 import *

def frozen_paths():
    saved={}
    for bps in [15,30]:
        saved[bps]={}
        for m in MARKETS:
            for r in RULES:
                with np.load(OUT/f'{tag(m,r,bps)}.npz') as z:saved[bps][m,r]={key:z[key].copy() for key in ['dates','close_nav']}
    return saved

def choose(saved_by_cost=None,save=True):
    audit=[];plans=[];inputs=[]
    if saved_by_cost is None:saved_by_cost=frozen_paths()
    for bps in [15,30]:
        saved=saved_by_cost[bps]
        for year in range(2022,2027):
            cut=pd.Timestamp(year,1,1);lo=pd.Timestamp(year-2,1,1)
            panel={};drawdowns={}
            for (m,r),z in saved.items():
                ds=pd.DatetimeIndex(z['dates']);take=ds<cut;s=pd.Series(z['close_nav'][take],index=ds[take])
                month=s.groupby(s.index.to_period('M')).last();previous=month.shift(1).fillna(1.)
                returns=month/previous-1;returns=returns[(returns.index>=lo.to_period('M'))&(returns.index<cut.to_period('M'))]
                assert len(returns)==24 and s.index.max()<cut
                panel[m,r]=np.log1p(returns.to_numpy())
                seg=s[s.index>=lo];pre=s[s.index<lo];a=np.r_[pre.iloc[-1] if len(pre) else 1.,seg.to_numpy()]
                drawdowns[m,r]=-float(np.min(a/np.maximum.accumulate(a)-1))
                if r=='BASE':inputs.append(dict(year=year,bps=bps,market=m,last_input=str(s.index.max().date()),cutoff=str(cut.date()),months=len(returns)))
            rng=np.random.default_rng(2300+year+bps)
            ix=((rng.integers(0,24,(500,8,1))+np.arange(3))%24).reshape(500,24)
            candidates=[]
            for r in RULES[1:]:
                diff=np.array([panel[m,r]-panel[m,'BASE'] for m in MARKETS]).T
                delta=12*diff.mean(0);pen=np.array([.5*max(0,drawdowns[m,r]-drawdowns[m,'BASE']) for m in MARKETS])
                lower=float(np.quantile(np.min(12*diff[ix].mean(1),axis=1),.2));score=float(np.min(delta-pen))
                row=dict(year=year,bps=bps,rule=r,score=score,worst_log_delta=float(delta.min()),lower80=lower)
                candidates.append(row);audit.append(row)
            for rule,strict in [('WF_ECONOMIC',False),('WF_PRUDENT',True)]:
                ok=[a for a in candidates if a['score']>0 and a['worst_log_delta']>0 and (not strict or a['lower80']>0)]
                pick=max(ok,key=lambda a:a['score'])['rule'] if ok else 'BASE'
                plans.append(dict(year=year,bps=bps,procedure=rule,choice=pick))
    if save:
        pd.DataFrame(audit).to_csv(OUT/'WF_SELECTION_AUDIT.csv',index=False)
        pd.DataFrame(inputs).to_csv(OUT/'WF_INPUT_CUTOFFS.csv',index=False)
        pd.DataFrame(plans).to_csv(OUT/'WF_PLAN.csv',index=False)
    return pd.DataFrame(plans)

def main():
    p=choose();rows=[]
    print(p.to_string(index=False),flush=True)
    for m in MARKETS:
        q=state(m);built=signals(q,m)
        for rule in ['WF_ECONOMIC','WF_PRUDENT']:
            for bps in [15,30]:
                a=p[(p.procedure==rule)&(p.bps==bps)]
                plan={str(r.year):r.choice for r in a.itertuples()}
                row,_,_=run(m,rule,bps,q=q,built=built,plan=plan);rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'SUMMARY_WF.csv',index=False)
    pd.concat([pd.read_csv(OUT/'SUMMARY_FIXED.csv'),pd.DataFrame(rows)],ignore_index=True).to_csv(OUT/'SUMMARY.csv',index=False)
    print('WF_COMPLETE',len(rows),flush=True)

if __name__=='__main__':main()
