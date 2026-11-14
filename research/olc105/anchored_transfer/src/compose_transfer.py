from settings import *
import json,numpy as np,pandas as pd
from context_model import predict_weights,PRIOR
from revalue_memory import revalue
from core import benchmark_context,leadership
import data_transfer as dat
from transfer_contract import select_pair,require_asof

def compose(f,close):
    models={int(y):v['TOP2_CONTEXT'] for y,v in json.loads((P16/'results/ANNUAL_MODELS.json').read_text()).items()}
    ctx=benchmark_context(close);groups=[];previous=None;lastx=np.full(3,np.nan);betas=[]
    for dt,g0 in f.groupby('signal_date',sort=True):
        g=g0.sort_values('ticker');current=g.set_index('ticker').CUM_FIXED_MAPPED
        lead=leadership(current,previous) if previous is not None else np.nan
        prior=ctx.loc[:dt];c=prior.iloc[-1] if len(prior) else pd.Series(dtype=float)
        x=np.array([c.get('trend126',np.nan),c.get('vol_ratio',np.nan),lead])
        groups.append(dict(date=dt,positions=g.index.to_numpy(),tickers=g.ticker.to_numpy(),z=g[['C21','C42','C63']].to_numpy(float),x=x,xlag=lastx.copy(),anchor=g.CUM_FIXED_MAPPED.to_numpy(float)))
        betas.append(predict_weights(models[dt.year],x) if dt.year in models else PRIOR.copy());previous=current;lastx=x
    scores=revalue(groups,betas);out=f.copy();out['score']=np.nan
    trace=[]
    for g,sm,beta in zip(groups,scores,betas):
        out.loc[g['positions'],'score']=.475*out.loc[g['positions'],'RETURN']+.525*sm
        trace.append({'signal_date':g['date'],**dict(zip(['beta21','beta42','beta63'],map(float,beta))),'feature_max_source_date':g['date']})
    return out,pd.DataFrame(trace)

def run(which):
    f=pd.read_pickle(ROOT/f'data/{which}_FORECASTS.pkl').sort_values(['signal_date','ticker']).reset_index(drop=True)
    if which=='PARITY':
        folder=BASE/'source/raw/inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029/prices'
        close=pd.read_csv(folder/'EXSA.DE.csv',index_col=0,parse_dates=True,float_precision='round_trip').loc[:'2026-07-01','Close']
    else:close=dat.benchmark()
    out,trace=compose(f,close)
    if which=='PARITY':
        ref=pd.read_csv(P16/'results/EU_SCORES.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
        j=out.merge(ref[['signal_date','ticker','TOP2_CONTEXT_REVALUE_FUSION']],on=['signal_date','ticker'],validate='one_to_one')
        err=float(abs(j.score-j.TOP2_CONTEXT_REVALUE_FUSION).max())
        old=pd.read_csv(P18/'inputs/EU_TOP2_CONTEXT_REVALUE_DECISIONS.csv',parse_dates=['signal_date']);dec=[]
        for dt,g in out.groupby('signal_date'):
            pair=select_pair(g,set(g.ticker));dec.append({'signal_date':dt,'ticker1':pair[0],'ticker2':pair[1]})
        z=pd.DataFrame(dec).merge(old,on='signal_date',suffixes=('','_ref'),validate='one_to_one')
        equal=int(((z.ticker1==z.ticker1_ref)&(z.ticker2==z.ticker2_ref)).sum())
        # Some raw XGB ranks have adjacent tie rounding; failed exact parity is explicit.
        assert len(z)==90 and equal==90,(len(z),equal,err)
        (ROOT/'results/ORIGINAL_CONTEXT_PARITY.json').write_text(json.dumps({'status':'PASS_TOP2_90','decisions':len(z),'exact_pairs':equal,'max_score_abs_error':err},indent=2))
        print('CONTEXT_PARITY',equal,err,flush=True)
    else:
        elig=pd.read_csv(ROOT/'results/ASOF_ELIGIBILITY_CORRECTED.csv',parse_dates=['signal_date'])
        ev=pd.read_csv(ROOT/'results/MOMENTUM_SIGNALS_CORRECTED.csv',parse_dates=['signal_date','effective_date'])
        decisions=[]
        for row in ev.itertuples():
            allowed=set(elig.loc[elig.signal_date.eq(row.signal_date),'isin'])
            g=out[out.signal_date.eq(row.signal_date)]
            pair=select_pair(g,allowed);require_asof(row.signal_date,row.effective_date)
            decisions.append({'signal_date':row.signal_date,'effective_date':row.effective_date,'ticker1':pair[0],'ticker2':pair[1],'eligible_candidates':len(allowed),'model_candidates':len(g[g.ticker.isin(allowed)]),'score1':float(g.set_index('ticker').score[pair[0]]),'score2':float(g.set_index('ticker').score[pair[1]])})
        pd.DataFrame(decisions).to_csv(ROOT/'results/ANCHORED_TRANSFER_DECISIONS.csv',index=False)
        print('NEW_DECISIONS',len(decisions),flush=True)
    out.to_csv(ROOT/f'results/{which}_CONTEXT_SCORES.csv.gz',index=False,compression={'method':'gzip','mtime':0});trace.to_csv(ROOT/f'results/{which}_CONTEXT_PARAMETERS.csv',index=False)
if __name__=='__main__':run(sys.argv[1])
