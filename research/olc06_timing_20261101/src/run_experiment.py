"""48 prespecified persistent replays, including32 immutable references."""
from common import *
from vector_engine import simulate,LEDGER_COLUMNS
import time

def main():
    rows=[];audit=[];t0=time.time()
    old=pd.read_csv(VENDOR/'results/ALL_SCORECARD.csv',float_precision='round_trip')
    for market in ('EU','USA'):
      for weight in ('HALF','ORIGINAL'):
        q,events,cal=load(market,weight)
        modes=['FULL','RISKOFF','LAG1'] if weight=='HALF' else ['FULL']
        for fee in (.001,.003):
          for mode in modes:
            for strategy in ('IMMEDIATE','DELAY3','PHASE5'):
              key=f'{market}_{weight}_{strategy}_{mode}_C{round(fee*10000)}'
              res=simulate(q,events,fee=fee,**policy_args(strategy),**mode_args(mode))
              assert np.isfinite(res['nav']).all() and (res['nav']>0).all(),key
              rec=np.einsum('ij,ij->i',res['primary_units'][:-1]+res['defensive_units'][:-1],q['O'][1:])+res['free_cash'][:-1]
              err=float(np.max(abs(rec-res['nav'][:-1])));assert err<1e-10,(key,err)
              account=float(np.max(abs(res['ledger'][:,25])));assert account<1e-10
              assert np.max(res['targets'].sum(axis=1)-1)<1e-10
              max_old=None;metric_error=None
              if strategy!='DELAY3':
                suffix='' if mode=='FULL' else '_'+mode
                oldkey=f'{market}_{weight}_{strategy}{suffix}_C{round(fee*10000)}'
                oracle=np.load(VENDOR/f'results/paths/{oldkey}.npz',allow_pickle=False)
                max_old=max(float(np.max(abs(res[k]-oracle[k]))) for k in ('nav','primary_units','defensive_units','free_cash','targets','ledger'))
                assert max_old==0,(key,max_old)
                rs=pd.DataFrame(metrics(q,res)).set_index('period')
                os=old[old.config==oldkey].set_index('period')
                metric_error=float(np.max(abs(rs[['cagr','maxdd','period_return']]-os[['cagr','maxdd','period_return']]).to_numpy()))
                assert metric_error<1e-10,(key,metric_error)
              path=OUT/f'paths/{key}.npz'
              np.savez_compressed(path,dates=q['dates'],tickers=q['tickers'],**res)
              stats=metrics(q,res)
              rows.extend(dict(market=market,weight=weight,fee=fee,mode=mode,strategy=strategy,config=key,**row) for row in stats)
              audit.append(dict(config=key,independent_nav_error=err,accounting_error=account,original_arrays_error=max_old,original_metric_error=metric_error,path_sha256=digest(path)))
              z=next(x for x in stats if x['period']=='ACTIVE2021_2024')
              print(key,'CAGR',round(100*z['cagr'],3),'DD',round(100*z['maxdd'],3),'elapsed',round(time.time()-t0,1),flush=True)
              pd.DataFrame(rows).to_csv(OUT/'SCORECARD.csv',index=False)
              pd.DataFrame(audit).to_csv(OUT/'PARITY_AND_ACCOUNTING.csv',index=False)
    (OUT/'LEDGER_COLUMNS.json').write_text(json.dumps(LEDGER_COLUMNS,indent=2))
    print('FINISHED',len(audit),'paths; unchanged controls',sum(x['original_arrays_error'] is not None for x in audit),flush=True)
if __name__=='__main__':main()
