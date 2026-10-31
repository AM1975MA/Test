"""Original V6 price state cached once; alternative recomputed for actual desired pair."""
from common import *
import warnings
from engine_prepare import v6

def build_cache(market,q):
    C=pd.read_pickle(ROOT/f'inputs/{market}_Close.pkl');ds=pd.DatetimeIndex(q['dates']);T=list(C.columns);N=len(T)
    cf=C.ffill().reindex(ds);allowed=None
    if market=='EU':
        cf['BIL']=1.;cf['SHV']=1.
        spy=pd.read_csv(SOURCE/'raw/_repeat1/SPY.csv',index_col=0,parse_dates=True,float_precision='round_trip').Close
        idx=spy.index.searchsorted(cf.index,side='left')-1
        cf['SPY']=np.where(idx>=0,spy.to_numpy()[np.maximum(idx,0)],np.nan)
        allowed=np.column_stack([C.reindex(ds).notna().to_numpy(),np.zeros((len(ds),3),bool)])
        ns=dict(v6.__dict__);exec(compile((SOURCE/'work/V6_PORT_SOURCE.py').read_text(),'<verified-original-v6-port>','exec'),ns);fun=ns['build_v6_state']
    else:fun=v6.build_v6_state
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        kw={} if allowed is None else {'allowed':allowed}
        state=fun(cf,q['d1'],q['d2'],q['basew'],q['gross'],**kw)
    ti={s:i for i,s in enumerate(cf.columns)};ranked={}
    for k in range(65,len(ds)-1):
        if not (state.recovery[k] and .74<=q['gross'][k]<.999):continue
        t=k-1;ids=np.arange(len(cf.columns));s=state.solidity[t];a=state.ret5[t];b=state.ret21[t];c=state.ret63[t];d=state.dd21[t]
        ok=np.isfinite(s)&np.isfinite(a)&np.isfinite(b)&np.isfinite(c)&np.isfinite(d)
        ok&=(ids!=ti['BIL'])&(ids!=ti['SHV'])
        if allowed is not None:ok&=allowed[t]
        ok&=(a>.005)&(b>0)&(c>-.03)&(d>-.07)&(s>=.72)
        ids=ids[ok]
        if len(ids):
            val=s[ids]+.20*np.clip(a[ids]/.05,-1,1)+.10*np.clip(b[ids]/.10,-1,1)
            ranked[k]=ids[np.argsort(-val)]
    cache=V6Cache(state,ranked)
    calc=np.array([cache(k,int(q['d1'][0,k]),int(q['d2'][0,k]),q['basew'][0,k]) for k in range(len(ds))])
    assert np.array_equal(calc,q['alt'][0]),(market,'V6 parity')
    print('V6_CACHE',market,'active_price_states',len(ranked),'parity_exact',flush=True)
    return cache

class V6Cache:
    def __init__(self,state,ranked):self.state=state;self.ranked=ranked
    def __call__(self,k,i,j,w):
        if k not in self.ranked or i<0:return -1
        if j<0:j=i
        t=k-1;s=self.state
        vals=[w*a[t,i]+(1-w)*a[t,j] for a in [s.ret5,s.ret21,s.dd21,s.solidity]]
        for x in self.ranked[k]:
            if x==i or x==j:continue
            if s.ret5[t,x]>=vals[0]+.015 and s.ret21[t,x]>=vals[1]+.005 and s.dd21[t,x]>=vals[2]+.015 and s.solidity[t,x]>=vals[3]+.05:return int(x)
        return -1
