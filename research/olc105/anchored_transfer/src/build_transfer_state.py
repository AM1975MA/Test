"""Source-native V6/FAST inputs. Anchors are never investable."""
from settings import *
import numpy as np,pandas as pd,json,inspect,warnings
import ddfirst,v6
import data_transfer as data
from transfer_contract import require_allowed
CASH=['EUR_CASH_A','EUR_CASH_B']

def macro_history(index):
    out=pd.DataFrame(index=index)
    for ticker in ['SPY','HYG','IEF']:
        folder=BASE/'source/raw/raw/_repeat1'
        old=pd.read_csv(folder/f'{ticker}.csv',index_col=0,parse_dates=True,float_precision='round_trip').sort_index().loc[:'2026-07-01','Close']
        new=pd.read_csv(CONTROL/f'source_complete/prices/{ticker}.csv.gz',index_col='date',parse_dates=True,float_precision='round_trip')['Adj Close']
        a=pd.Timestamp('2026-07-01');scale=float(old.loc[a]/new.loc[a]);s=pd.concat([old,new.loc[new.index>a]*scale])
        pos=s.index.searchsorted(index,side='left')-1
        out[ticker]=np.where(pos>=0,s.to_numpy()[np.maximum(0,pos)],np.nan)
    return out

def build():
    fs,roster=data.anchored_data();candidates=set(data.candidate_data()[0]);names=list(fs)+CASH
    raw={fld:pd.DataFrame({t:f[fld] for t,f in fs.items()}).sort_index() for fld in ['Open','Low','Close']}
    idx=raw['Close'].index;macro=macro_history(idx);c=raw['Close'].ffill()
    old=ddfirst.market_state;src=inspect.getsource(old).replace('def market_state(','def market_state_port(').replace('spy=close["SPY"]','spy=MACRO["SPY"]').replace('hygief=close["HYG"]/close["IEF"]','hygief=MACRO["HYG"]/MACRO["IEF"]')
    ns=dict(ddfirst.__dict__,MACRO=macro);exec(src,ns);ddfirst.market_state=ns['market_state_port']
    try:gross=ddfirst.sync_c95_m75_gross(c)
    finally:ddfirst.market_state=old
    g=np.where(np.isclose(gross,.95),1.,np.where(np.isclose(gross,.75),.945,np.where(gross<=.251,.66,1.)))
    mats={fld:f.ffill().fillna(1.) for fld,f in raw.items()}
    for m in mats.values():
        for t in CASH:m[t]=1.
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');ex=ddfirst.daily_execution_inputs(mats['Open'],mats['Low'],mats['Close'])
    obs=np.column_stack([raw['Open'].notna().to_numpy(),np.ones((len(idx),2),bool)])
    lowobs=np.column_stack([raw['Low'].notna().to_numpy(),np.ones((len(idx),2),bool)])
    ex['gap'][~obs]=0.;ex['ud1']=np.mean(ex['gap']<-.01,axis=1);ex['uneg']=np.mean(ex['gap']<0,axis=1)
    D=len(idx);q=dict(dates=idx.to_numpy(),tickers=np.array(names),g=g,gross=gross,observed=obs,low_observed=lowobs,**ex)
    q.update(d1=np.full((1,D),-1,np.int64),d2=np.full((1,D),-1,np.int64),margin=np.zeros((1,D)),basew=np.full((1,D),.5),weights=np.full((1,D),.5),events=np.zeros(D,bool))
    dec=pd.read_csv(ROOT/'results/ANCHORED_TRANSFER_DECISIONS.csv',parse_dates=['signal_date','effective_date'])
    for row in dec.itertuples():
        k=idx.searchsorted(row.signal_date,side='right');assert idx[k]==row.effective_date,(idx[k],row.effective_date)
        q['d1'][0,k:]=names.index(row.ticker1);q['d2'][0,k:]=names.index(row.ticker2);q['events'][k]=True
    vc=mats['Close'].rename(columns={'EUR_CASH_A':'BIL','EUR_CASH_B':'SHV'});vc['SPY']=macro.SPY
    allowed=np.column_stack([raw['Close'].notna().to_numpy()&np.array([t in candidates for t in fs])[None,:],np.zeros((D,3),bool)])
    ns=v6.__dict__.copy();exec((S/'V6_PORT_SOURCE.py').read_text(),ns)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');q['alt']=ns['build_v6_state'](vc,q['d1'],q['d2'],q['basew'],gross,allowed=allowed).alt_idx
    require_allowed([names[j] for j in np.unique(q['alt']) if j>=0],candidates)
    # Keep warm-up in state; simulation starts at the common eligible opening.
    start=pd.Timestamp(dec.effective_date.iloc[0]);keep=idx>=start
    for key in list(q):
        if key=='tickers':continue
        a=q[key];q[key]=a[:,keep] if a.ndim==2 and a.shape[0]==1 else a[keep]
    np.savez_compressed(ROOT/'data/TRANSFER_STATE.npz',**q)
    (ROOT/'results/STATE_BUILD_QA.json').write_text(json.dumps({'status':'PASS','start':str(start.date()),'last':str(idx[-1].date()),'n_sessions':int(keep.sum()),'context_assets':len(fs),'investable_assets':len(candidates),'decision_count':len(dec),'alternatives_restricted_to_candidates':True,'geometry_flags_do_not_filter_current_open':True,'cash':'constant EUR placeholders, zero interest','source_prices':'adjusted Yahoo retrospective proxies, NOT broker fills'},indent=2))
    print('STATE_DONE',keep.sum(),len(dec),flush=True)
if __name__=='__main__':build()
