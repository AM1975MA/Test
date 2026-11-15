"""Matched actual-state gate diagnosis; never compounds counterfactual paths."""
from pathlib import Path
import sys,argparse,json,hashlib,datetime
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from run_research import load_panel,load_core
from cluster_selectors import prepare_features
from dedup_selectors import make_policy

def replay(p,f,core,units,cash,target,k,end_k,lag,force,common_prior_orders):
    units=np.array(units,copy=True);cash=float(cash);target=np.array(target,copy=True)
    costs=0.;orders=0;pending=True;due=k+1+lag
    for trade in common_prior_orders:
        j=int(trade.j)
        if trade.side=='BUY':units[j]+=trade.quantity;cash-=trade.notional+trade.cost
        else:units[j]-=trade.quantity;cash+=trade.notional-trade.cost
        costs+=trade.cost;orders+=1
    units=np.maximum(units,0.);cash=max(cash,0.)
    deferred=0
    for j in range(due,end_k+1):
        if not pending:continue
        op=np.array(p['O'][j],copy=True)
        op[~p['open_observed'][j]|~np.isfinite(op)|(op<=0)]=np.nan
        mark=np.where(np.isfinite(op),op,f['C'][j-1])
        missing=((units>1e-10)|(target>0))&~np.isfinite(op)
        units,cash,trades=core.rebalance(units,cash,op,target,1.,.0015,.03,force,mark=mark)
        costs+=sum(t['cost'] for t in trades);orders+=len(trades)
        if missing.any():deferred+=1
        else:pending=False
    value=float(cash+np.nansum(units*f['C'][end_k]))
    return dict(nav=value,costs=costs,orders=orders,deferred=deferred,pending_at_end=bool(pending))

def summarize(g):
    x=g.increment_bps.to_numpy()
    return dict(n=len(x),mean_increment_bps=float(x.mean()) if len(x) else None,
                median_increment_bps=float(np.median(x)) if len(x) else None,
                wins=int((x>1e-8).sum()),losses=int((x< -1e-8).sum()),ties=int((abs(x)<=1e-8).sum()),
                min_increment_bps=float(x.min()) if len(x) else None,max_increment_bps=float(x.max()) if len(x) else None,
                maximum_terminal_parity_error=float(g.terminal_parity_error.max()) if len(x) else None)

def analyze(root):
    root=Path(root).resolve();p=load_panel(root);core=load_core(root)
    with np.load(root/'data/LIQUIDITY.npz',allow_pickle=False) as z:turnover=z['turnover']
    rows=[]
    with threadpool_limits(limits=1):
        f=prepare_features(p,core,turnover)
        chosen=make_policy(p,f,{},'DEDUP_DUAL_TREND_OPP');control=make_policy(p,f,{},'DEDUP_DUAL21')
        for scenario,lag in (('BASE',0),('LAG2',2)):
            folder=root/'results_stage2'/f'DEDUP_DUAL_TREND_OPP__{scenario}'
            with np.load(folder/'DECISIONS.npz',allow_pickle=False) as z:saved={name:z[name] for name in z.files}
            daily=pd.read_csv(folder/'DAILY.csv.gz',float_precision='round_trip').set_index('k')
            ledger=pd.read_csv(folder/'ORDERS.csv.gz',float_precision='round_trip')
            ks=saved['k'];finish=int(daily.index[-1])
            for i,k in enumerate(ks):
                k=int(k);end_k=int(ks[i+1]) if i+1<len(ks) else finish
                u=saved['units'][i];cash=float(saved['cash'][i]);current=saved['current_weights'][i]
                nav=float(cash+np.nansum(u*f['C'][k]))
                actual,am=chosen(k,current);alternate,cm=control(k,current)
                assert np.array_equal(actual,saved['raw_weights'][i])
                assert np.array_equal(actual,saved['weights'][i])
                prior=ledger[(ledger.execution_idx>k)&(ledger.execution_idx<k+1+lag)]
                assert prior.empty or (prior.signal_idx<k).all()
                common=list(prior.itertuples(index=False))
                a=replay(p,f,core,u,cash,actual,k,end_k,lag,i==0,common)
                b=replay(p,f,core,u,cash,alternate,k,end_k,lag,i==0,common)
                error=abs(a['nav']-float(daily.loc[end_k,'nav_close']))
                assert error<1e-6,(scenario,k,error)
                rows.append(dict(scenario=scenario,decision=i,signal_idx=k,end_idx=end_k,
                    signal_date=str(p['dates'][k].date()),end_date=str(p['dates'][end_k].date()),
                    end_year=int(p['dates'][end_k].year),crosses_year=p['dates'][k].year!=p['dates'][end_k].year,
                    start_nav=nav,targets_differ=bool(np.any(actual!=alternate)),
                    actual_selected=json.dumps(am['selected_names']),control_selected=json.dumps(cm['selected_names']),
                    actual_opportunity=am['opportunity_used'],control_opportunity=cm['opportunity_used'],
                    prior_common_orders=len(common),actual_terminal_nav=a['nav'],control_terminal_nav=b['nav'],
                    actual_return=a['nav']/nav-1,control_return=b['nav']/nav-1,
                    increment_bps=10000*(a['nav']-b['nav'])/nav,
                    actual_costs=a['costs'],control_costs=b['costs'],terminal_parity_error=error))
    frame=pd.DataFrame(rows);out=root/'analysis'
    frame.to_csv(out/'MATCHED_STATE_INTERVALS.csv',index=False)
    sums=[];annual=[]
    for scenario,g in frame.groupby('scenario'):
        for subset,h in (('ALL',g),('CHANGED',g[g.targets_differ])):
            sums.append(dict(scenario=scenario,subset=subset,**summarize(h)))
        for year,h in g[g.targets_differ].groupby('end_year'):
            annual.append(dict(scenario=scenario,end_year=int(year),**summarize(h)))
    pd.DataFrame(sums).to_csv(out/'MATCHED_STATE_SUMMARY.csv',index=False)
    pd.DataFrame(annual).to_csv(out/'MATCHED_STATE_ANNUAL.csv',index=False)
    meta=dict(status='PASS',completed_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
              intervals=len(frame),scenarios=['BASE','LAG2'],compounded=False,
              maximum_terminal_parity_error=float(frame.terminal_parity_error.max()),
              common_prior_fills=int(frame.prior_common_orders.sum()),
              protocol_sha256=hashlib.sha256((out/'MATCHED_STATE_PROTOCOL.md').read_bytes()).hexdigest(),
              summary=sums,limitations='Post-selection descriptive intervention; not independent strategy performance; same source/account conventions.')
    (out/'MATCHED_STATE_QA.json').write_text(json.dumps(meta,indent=2)+'\n')
    print(json.dumps(meta,indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root');a=ap.parse_args();analyze(a.root)
