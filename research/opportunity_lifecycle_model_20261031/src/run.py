"""Persistent single-account OLC-01 comparisons. No splicing of independent NAVs."""
from common import *
from controller import Controller
from action_engine import simulate_action
from v6_cache import build_cache
import warnings,time,sys
FIELDS=['O','L','C','PC','gap','ud1','uneg','UH','SA']

def run_market(market,additional=False):
    started=time.time();out=ROOT/'results';paths=out/'paths';paths.mkdir(exist_ok=True);dec=out/'decisions';dec.mkdir(exist_ok=True)
    q=dict(np.load(ROOT/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
    orig=dict(np.load(ROOT/f'inputs/{market}_STATE_ORIGINAL.npz',allow_pickle=False))
    score=pd.read_csv(ROOT/f'inputs/{market}_SCORE.csv',index_col=0,parse_dates=True,float_precision='round_trip')
    cal=pd.read_csv(ROOT/f'inputs/{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
    pred=pd.read_csv(out/f'{market}_PREDICTIONS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
    covs=np.load(ROOT/f'inputs/{market}_COVARIANCE.npz')['covariance'];mus={}
    for model in ['RIDGE','HGB']:
        a=pred[pred.model==model];mus[model]=np.stack([a.pivot(index='signal_date',columns='ticker',values=f'mu{h}').reindex(index=score.index,columns=score.columns).to_numpy() for h in [1,2,3]],axis=1)
    cache=build_cache(market,q);ds=pd.DatetimeIndex(q['dates']);ts=list(q['tickers'])
    bil=ts.index('BIL' if market=='USA' else 'EUR_CASH_A');shv=ts.index('SHV' if market=='USA' else 'EUR_CASH_B')
    configs=[('CL01_ORIGINAL',None,None,True),('CL01_HALF',None,None,True)]
    for ctrl in ['BUFFER4','FIXED_2_0','FIXED_2_1','FIXED_3_0','FIXED_3_1','FIXED_3_2']:configs.append((ctrl,'RIDGE',ctrl,True))
    for m in ['RIDGE','HGB']:
        for policy,profile in [('RANK',False),('RANK',True),('GATE',False),('GATE',True),('PARTIAL',True)]:configs.append((f'{m}_{policy}_{"PROFILE" if profile else "21"}',m,policy,profile))
    if additional:
        configs=[]
        for m in ['RIDGE','HGB']:
            for profile in [False,True]:configs.append((f'{m}_BASE_GATE_{"PROFILE" if profile else "21"}',m,'BASE_GATE',profile))
    stats=[];aud=[]
    for name,model,policy,profile in configs:
        st=orig if name=='CL01_ORIGINAL' else q
        for fee in [.001,.003]:
            controller=None if model is None else Controller(st,cal,score.to_numpy(),mus[model],covs,fee,policy,profile)
            args=[st['d1'],st['d2'],st['weights']]+[st[k] for k in FIELDS]+[bil,shv,st['g'][None,:],st['g'],st['alt'],True]
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                E,T,X,AW,L=simulate_action(*args,cost=fee,slip=.001,observed=st.get('observed'),low_observed=st.get('low_observed'),strict_quotes=True,controller=controller,alt_selector=cache if controller else None)
            nav=E[0];led=L[0];referr=None
            if controller is None and fee==.001:
                ref=np.load(out/f'{market}_REFERENCE_{"ORIGINAL" if name.endswith("ORIGINAL") else "HALF"}.npz');referr=float(np.max(abs(nav-ref['nav'])));assert referr<1e-12,(market,name,referr)
            assert np.isfinite(nav).all() and nav.min()>0
            accounting=float(np.max(abs(led[:-1,46])));assert accounting<1e-9
            rebuilt=np.cumprod(1+led[:-1,38]/led[:-1,0]);err=float(np.max(abs(rebuilt-nav[:-1])));assert err<1e-10
            config=f'{name}_C{int(fee*10000)}'
            np.savez_compressed(paths/f'{market}_{config}.npz',dates=ds.values,nav=nav,ledger=led,tickers=ts)
            if controller:
                f=pd.DataFrame(controller.records);f.insert(0,'market',market);f.insert(1,'config',config);f.to_csv(dec/f'{market}_{config}.csv',index=False)
            for row in metrics(nav,led,ds):stats.append(dict(market=market,policy=name,fee=fee,config=config,**row))
            # Model-active primary period is separate from unchanged warmup.
            lr=np.diff(np.log(np.r_[1.,nav]));ix=(ds>='2021-01-01')&(ds<='2024-12-31');eq=np.exp(np.cumsum(lr[ix]));peak=np.maximum.accumulate(np.r_[1.,eq])[1:]
            stats.append(dict(market=market,policy=name,fee=fee,config=config,period='ACTIVE_2021_2024',n=int(ix.sum()),period_return=float(np.expm1(lr[ix].sum())),cagr=float(np.expm1(lr[ix].mean()*252)),annual_log=float(lr[ix].mean()*252),maxdd=float((eq/peak-1).min()),annual_turnover=float(led[ix,5].mean()*252),risky_weight=float(led[ix,41].mean())))
            aud.append(dict(market=market,config=config,reference_error=referr,accounting_error=accounting,nav_rebuild_error=err,positive_nav=True,path_sha256=digest(paths/f'{market}_{config}.npz')))
            print('REPLAY',market,config,'sec',round(time.time()-started,1),flush=True)
        suffix='_ADDITIONAL' if additional else '';pd.DataFrame(stats).to_csv(out/f'{market}{suffix}_SCORECARD.csv',index=False);pd.DataFrame(aud).to_csv(out/f'{market}{suffix}_PATH_AUDIT.csv',index=False)
    print('COMPLETE',market,len(aud),'paths',round(time.time()-started,1),flush=True)

if __name__=='__main__':
    additional='--additional' in sys.argv
    for m in [x for x in sys.argv[1:] if not x.startswith('--')] or ['EU','USA']:run_market(m,additional)
