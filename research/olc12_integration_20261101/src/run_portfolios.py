"""Persistent full-strategy replays; identical engine and prices in paired contrasts."""
from pathlib import Path
import json,time,hashlib
import numpy as np,pandas as pd
from integration import VARIANTS
from prepare import read
from portfolio_adapter import adapt_state
from vector_engine import simulate,LEDGER_COLUMNS
from portfolio_metrics_parent import metrics,policy_args
from accounting import decompose
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'inputs';O=ROOT/'results';P=O/'paths';P.mkdir(exist_ok=True)

def main():
    rows=[];checks=[];decisions=[];t0=time.time()
    for market in ['EU','USA']:
        q=dict(np.load(I/f'{market}_STATE_HALF.npz',allow_pickle=False));cal=read(I/f'{market}_CALENDAR.csv');ds=pd.DatetimeIndex(q['dates'])
        events=np.asarray(ds.isin(cal.entry_date),bool);scores=read(O/f'{market}_INTEGRATED_SCORES.csv.gz')
        for variant in ['ENGINE_CONTROL',*VARIANTS]:
            if variant=='ENGINE_CONTROL':st=q;ev=events
            else:
                st,ev,dd=adapt_state(q,cal,scores,variant);dd['market']=market;dd['variant']=variant;decisions.append(dd)
            modes=['FULL','LAG1'] if variant in ['MATCHED_REG','NAIVE_CLASS','SOLO_CLASS_CURRENT','SPECIALIST20_CURRENT','RERANK5'] else ['FULL']
            for mode in modes:
                policies=['IMMEDIATE'] if mode=='LAG1' else ['IMMEDIATE','DELAY3','PHASE5']
                for policy in policies:
                    for fee in [.001,.003]:
                        key=f'{market}_{variant}_{policy}_{mode}_C{round(fee*10000)}';path=P/f'{key}.npz'
                        res=simulate(st,ev,fee=fee,lag_systemic=mode=='LAG1',**policy_args(policy))
                        assert np.isfinite(res['nav']).all() and np.min(res['nav'])>0
                        capital=np.einsum('ij,ij->i',res['primary_units'][:-1]+res['defensive_units'][:-1],st['O'][1:])+res['free_cash'][:-1]
                        err=float(np.max(abs(capital-res['nav'][:-1])));assert err<1e-10,(key,err)
                        attr=decompose(st,res);le=float(np.max(abs(attr['log_components'].sum(1)-attr['log_return'])));assert le<1e-12
                        parity=None
                        if variant=='ENGINE_CONTROL':
                            oracle=np.load(ROOT/f'oracles/paths/{market}_HALF_{policy}_FULL_C{round(fee*10000)}.npz')
                            parity=max(float(np.max(abs(res[k]-oracle[k]))) for k in ['nav','primary_units','defensive_units','free_cash','targets','ledger']);assert parity==0,(key,parity)
                        obs=st.get('observed',np.ones_like(st['O'],bool));before=np.vstack([np.zeros(st['O'].shape[1]),res['primary_units'][:-1]])
                        bad=(np.abs(res['primary_units']-before)>1e-12)&(~obs)
                        assert not bad.any(),key
                        np.savez_compressed(path,dates=st['dates'],tickers=st['tickers'],**res)
                        rr=metrics(st,res)
                        rows.extend(dict(market=market,variant=variant,policy=policy,mode=mode,fee=fee,config=key,**r) for r in rr)
                        checks.append(dict(config=key,intervals=len(ds)-1,nav_error=err,log_error=le,parent_error=parity,missing_quote_trades=int(bad.sum()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                        active=next(r for r in rr if r['period']=='ACTIVE2021_2024')
                        print(len(checks),key,round(100*active['cagr'],4),round(100*active['maxdd'],4),'seconds',round(time.time()-t0,1),flush=True)
                        pd.DataFrame(rows).to_csv(O/'SCORECARD.csv',index=False);pd.DataFrame(checks).to_csv(O/'PATH_VERIFICATION.csv',index=False)
        pd.concat(decisions,ignore_index=True).to_csv(O/'PORTFOLIO_PROPOSALS.csv',index=False)
    (O/'PORTFOLIOS_COMPLETE.json').write_text(json.dumps({'paths':len(checks),'exact_engine_controls':sum(c['parent_error'] is not None for c in checks),'intervals':sum(c['intervals'] for c in checks),'metrics_rows':len(rows),'new_base_model_fits':0},indent=2))
    (O/'LEDGER_COLUMNS.json').write_text(json.dumps(LEDGER_COLUMNS))
    print('PORTFOLIOS_COMPLETE',len(checks),flush=True)
if __name__=='__main__':main()
