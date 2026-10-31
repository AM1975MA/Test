"""Prepare exact archived Stage19 inputs, with no fitting and no new downloads."""
from pathlib import Path
import sys,importlib.util,os
import numpy as np,pandas as pd
B=Path(os.environ.get('RECONCILIATION_ROOT','/mnt/data/reconciliation'))
SRC=B/'selected/research/tail-only-and-allocation-ablation-20261017'
sys.path[:0]=[str(SRC),str(SRC/'vendor/etf_trader_v2/src')]
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer,ddfirst,v6
spec=importlib.util.spec_from_file_location('canonical_stage19',SRC/'vendor/p45/v2_stage19_kernel.py')
stage=importlib.util.module_from_spec(spec);spec.loader.exec_module(stage)

def read_frame(path):
    f=pd.read_csv(path,float_precision='round_trip')
    for c in ['signal_date','entry_date','exit_date']:
        if c in f:f[c]=pd.to_datetime(f[c])
    return f

def prepare(vintage,arm):
    raw=B/'raw'/f'_repeat{vintage}'
    mats,_,_=load_ticker_csv_folder(raw)
    tickers=pd.read_csv(raw/'universe.csv')['ticker'].astype(str).str.upper().drop_duplicates().tolist()
    assert len(tickers)==149 and 'BIL' in tickers and 'SHV' in tickers
    root=B/'factorial'/arm/f'r{vintage}'
    tit=read_frame(root/'TIT_R_SOURCE_ONLY.csv');pred=read_frame(root/'ENSEMBLE_TAIL_OOS.csv')
    cal=tit[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    cutoff=min(mats['Close'][t].last_valid_index() for t in tickers)
    cal=cal[cal.exit_date.le(cutoff)].copy().reset_index(drop=True)
    p=pred.rename(columns={'ET_TAIL':'ET_RANK','XGB_TAIL':'XGB_RANK'})
    score=stage.score_matrix(p,cal,tickers);pm=stage.pred_matrices(p,cal,tickers)
    oo=mats['Open'].reindex(columns=tickers).ffill().bfill()
    ll=mats['Low'].reindex(columns=tickers).ffill().bfill().reindex(oo.index)
    cc=mats['Close'].reindex(columns=tickers).ffill().bfill().reindex(oo.index)
    st=int(oo.index.get_loc(cal.entry_date.min()));en=int(oo.index.get_loc(cal.exit_date.max()))
    ds=oo.index[st:en+1];oo=oo.loc[:cal.exit_date.max()];ll=ll.reindex(oo.index);cc=cc.reindex(oo.index)
    bm=np.arange(len(tickers),dtype=np.int32)[None,:];bok=np.ones_like(bm,dtype=bool)
    alloc=producer.allocations_from_score(score,cal,ds,bm,bok,continuous=True)
    gross=np.asarray(ddfirst.sync_c95_m75_gross(cc[tickers])[st:en+1],float)
    g=stage.risk_gross_transform(gross)
    agreement=np.zeros_like(alloc.d1,bool)
    for m,row in enumerate(cal.itertuples(index=False)):
        a=int(ds.searchsorted(row.entry_date));e=int(ds.searchsorted(row.exit_date))
        if e<=a or a>=len(ds):continue
        x,y=alloc.d1[:,a],alloc.d2[:,a]
        agreement[:,a:e]=((pm['ET_RANK'][m,x]>pm['ET_RANK'][m,y])&(pm['XGB_RANK'][m,x]>pm['XGB_RANK'][m,y]))[:,None]
    weights=stage.confidence_weights(alloc,g,agreement,np.zeros_like(agreement),mode='current_plus_models_riskoff')
    s6=v6.build_v6_state(cc[tickers].loc[ds],alloc.d1,alloc.d2,alloc.weight1,gross)
    full=ddfirst.daily_execution_inputs(oo,ll,cc)
    ex={k:np.ascontiguousarray(v[st:en+1]) for k,v in full.items()}
    args=[alloc.d1,alloc.d2,weights]+[ex[k] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]+[tickers.index('BIL'),tickers.index('SHV'),np.tile(g,(1,1)),g,s6.alt_idx,True,.001]
    E,T,X,AW=stage.simulate_arch(*args)
    reference=np.load(root/'FULL_UNIVERSE_PATH.npz',allow_pickle=False)
    actual={'dates':ds.values,'equity':E,'turnover':T,'d1':alloc.d1,'d2':alloc.d2,'weight1':weights,'margin':alloc.margin,'alt_idx':s6.alt_idx}
    errors={}
    for key,val in actual.items():
        assert val.shape==reference[key].shape,(vintage,arm,key,'shape')
        if val.dtype.kind in 'f':
            errors[key]=float(np.max(np.abs(val-reference[key])))
            assert errors[key]<1e-12,(vintage,arm,key,errors[key])
        else:
            assert np.array_equal(val,reference[key]),(vintage,arm,key)
            errors[key]=0.
    return dict(vintage=vintage,arm=arm,tickers=tickers,dates=ds,cal=cal,pred=p,score=score,alloc=alloc,gross=gross,g=g,agreement=agreement,weights=weights,alt=s6.alt_idx,close=cc[tickers].loc[ds],ex=ex,canonical=(E,T,X,AW),errors=errors)

if __name__=='__main__':
    import json,time
    t=time.time();out=prepare(1,'B_T1_H1');print('PARITY',json.dumps(out['errors']),'elapsed',time.time()-t)
