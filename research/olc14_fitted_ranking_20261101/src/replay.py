"""All preregistered target-only strategy replays through immutable parent engine."""
from __future__ import annotations
import time,json
import numpy as np,pandas as pd
from common import ROOT,P12,MARKETS,readcsv
from common import VARIANTS
from portfolio_adapter import adapt_state
from vector_engine import simulate,LEDGER_COLUMNS
from portfolio_metrics_parent import metrics,policy_args
from accounting import decompose
from recovery_core import atomic_json,sha256

def main():
    O=ROOT/'results';P=O/'paths';P.mkdir(exist_ok=True)
    rows=[];checks=[];decisions=[];start=time.time()
    for market in MARKETS:
        q=dict(np.load(P12/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False));cal=readcsv(P12/f'inputs/{market}_CALENDAR.csv')
        scores=readcsv(O/f'{market}_MEAN3_SCORES.csv.gz');scores=scores.rename(columns={v+'_FUSION':v for v in VARIANTS})
        for variant in VARIANTS:
            st,events,dd=adapt_state(q,cal,scores,variant);dd['market']=market;dd['variant']=variant;decisions.append(dd)
            for mode in ('FULL','LAG1'):
                policies=('IMMEDIATE','DELAY3','PHASE5') if mode=='FULL' else ('IMMEDIATE',)
                for policy in policies:
                    for fee in (.001,.003):
                        key=f'{market}_{variant}_{policy}_{mode}_C{round(fee*10000)}'
                        res=simulate(st,events,fee=fee,lag_systemic=mode=='LAG1',**policy_args(policy))
                        assert np.isfinite(res['nav']).all() and (res['nav']>0).all()
                        capital=((res['primary_units'][:-1]+res['defensive_units'][:-1])*st['O'][1:]).sum(1)+res['free_cash'][:-1]
                        err=float(np.max(abs(capital-res['nav'][:-1])));assert err<1e-10,(key,err)
                        attr=decompose(st,res);le=float(np.max(abs(attr['log_components'].sum(1)-attr['log_return'])));assert le<1e-12
                        pe=None
                        if variant=='ORIGINAL':
                            oracle=np.load(P12/f'results/paths/{market}_MATCHED_REG_{policy}_{mode}_C{round(fee*10000)}.npz')
                            pe=max(float(np.max(abs(res[k]-oracle[k]))) for k in res)
                            assert pe==0,(key,pe)
                        obs=st.get('observed',np.ones_like(st['O'],bool));before=np.vstack([np.zeros(st['O'].shape[1]),res['primary_units'][:-1]])
                        bad=(np.abs(res['primary_units']-before)>1e-12)&(~obs);assert not bad.any(),key
                        path=P/f'{key}.npz';np.savez_compressed(path,dates=st['dates'],tickers=st['tickers'],**res)
                        rr=metrics(st,res)
                        rows.extend(dict(market=market,variant=variant,policy=policy,mode=mode,fee=fee,config=key,**r) for r in rr)
                        checks.append(dict(config=key,intervals=len(st['dates'])-1,nav_error=err,log_error=le,parent_error=pe,missing_quote_trades=int(bad.sum()),sha256=sha256(path)))
                        pd.DataFrame(rows).to_csv(O/'SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(O/'PATH_VERIFICATION.csv',index=False)
                        active=next(r for r in rr if r['period']=='ACTIVE2021_2024')
                        print('PATH',len(checks),key,'CAGR',round(100*active['cagr'],4),'MaxDD',round(100*active['maxdd'],4),'elapsed',round(time.time()-start,1),flush=True)
    pd.concat(decisions,ignore_index=True).to_csv(O/'PORTFOLIO_PROPOSALS.csv',index=False)
    atomic_json(O/'PORTFOLIOS_COMPLETE.json',{'paths':len(checks),'main_paths':72,'lagged_systemic_paths':24,'exact_parent_controls':sum(c['parent_error'] is not None for c in checks),'metrics_rows':len(rows),'engine_changed':False})
    atomic_json(O/'LEDGER_COLUMNS.json',{'columns':LEDGER_COLUMNS});print('PORTFOLIOS_COMPLETE',len(checks),flush=True)
if __name__=='__main__':main()
