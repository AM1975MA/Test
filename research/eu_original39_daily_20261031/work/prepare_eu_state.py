"""Market adapter; preserves score/allocator/risk equations and exposes differences."""
from research_common import B,SRC,asof_external,score_blend,select_pair
import os,sys,inspect,importlib.util,json,warnings
os.environ['RECONCILIATION_ROOT']=str(B)
import numpy as np,pandas as pd
from engine_prepare import stage,producer,ddfirst,v6
P=B/'inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029'
OUT=B/'results'
# Original V6 with informational market benchmark excluded from purchasable alternatives.
vsrc=inspect.getsource(v6.build_v6_state)
vsrc=vsrc.replace('shv_ticker: str = "SHV",','shv_ticker: str = "SHV",\n    allowed=None,')
vsrc=vsrc.replace('ids=ids[ok & (np.arange(N)!=bil) & (np.arange(N)!=shv)]','ids=ids[ok & (np.arange(N)!=bil) & (np.arange(N)!=shv) & (allowed[t] if allowed is not None else np.ones(N,bool))]')
ns=dict(v6.__dict__);exec(compile(vsrc,'<original-v6-eligibility-only>','exec'),ns)
(B/'work/V6_PORT_SOURCE.py').write_text(vsrc)
build_v6=ns['build_v6_state']

def main():
 T=pd.read_csv(P/'input/universe.csv').ticker.tolist();N=len(T)
 mats={f:pd.read_pickle(B/'inputs'/f'EU_{f}.pkl') for f in ['Open','High','Low','Close','Volume']}
 rawO=mats['Open'];rawC=mats['Close'];idx=rawO.index
 native=pd.read_csv(P/'input/EU165_NATIVE_MODEL_SCORES_AND_LABELS.csv.gz',parse_dates=['signal_date'])
 ret=pd.read_csv(OUT/'EU_RETURN_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
 dates=pd.DatetimeIndex(sorted(native[native.model=='V2_ET_TAIL'].signal_date.unique()))
 dates=dates[(dates>='2019-01-01')&(dates<'2026-07-01')]
 def mat(model):return native[native.model==model].pivot(index='signal_date',columns='ticker',values='score').reindex(index=dates,columns=T).to_numpy(float)
 rr=ret.pivot(index='signal_date',columns='ticker',values='RETURN_PCT').reindex(index=dates,columns=T).to_numpy(float)
 et=mat('V2_ET_TAIL');x=mat('V2_XGB_TAIL')
 tt=.6*et+.4*x;sm=.4*tt+.3*np.vstack([tt[:1],tt[:-1]])+.3*np.vstack([tt[:1],tt[:1],tt[:-2]])
 hy=np.clip(sm,0,1)**1.1
 score=score_blend(rr,et,x)
 entries=[idx[idx.searchsorted(d,side='right')] for d in dates]
 exits=entries[1:]+[idx[-1]]
 cal=pd.DataFrame({'signal_date':dates,'entry_date':entries,'exit_date':exits})
 ds=idx[(idx>=entries[0])&(idx<=idx[-1])]
 # Valuation carry only; actual quote availability remains distinct.
 c=rawC.ffill();o=rawO.ffill();l=mats['Low'].ffill()
 # Original macro inputs retained as real external information, never traded.
 macro=pd.DataFrame(index=idx);macrodates=[]
 for t in ['SPY','HYG','IEF']:
  us=pd.read_csv(B/'raw/_repeat1'/f'{t}.csv',parse_dates=['date'],float_precision='round_trip').set_index('date').Close
  macro[t]=asof_external(us,idx)
  pos=us.dropna().index.searchsorted(idx,side='left')-1
  assert (us.dropna().index[pos[pos>=0]]<idx[pos>=0]).all()
  macrodates.append({'ticker':t,'strict_prior_date':True})
 orig=ddfirst.market_state
 msource=inspect.getsource(orig).replace('def market_state(','def market_state_port(').replace('spy=close["SPY"]','spy=MACRO["SPY"]') .replace('hygief=close["HYG"]/close["IEF"]','hygief=MACRO["HYG"]/MACRO["IEF"]')
 nspace=dict(ddfirst.__dict__,MACRO=macro);exec(compile(msource,'<original-market-risk-external-series>','exec'),nspace)
 (B/'work/DD_PORT_SOURCE.py').write_text(msource)
 try:
  ddfirst.market_state=nspace['market_state_port'];gross=ddfirst.sync_c95_m75_gross(c)
 finally:ddfirst.market_state=orig
 gross=pd.Series(gross,index=idx).loc[ds].to_numpy();g=stage.risk_gross_transform(gross)
 # Explicit unremunerated cash accounts. Not USD bills and not bond proxies.
 t_all=T+['EUR_CASH_A','EUR_CASH_B']
 for f in [o,l,c]:
  f['EUR_CASH_A']=1.;f['EUR_CASH_B']=1.
 exfull=ddfirst.daily_execution_inputs(o.fillna(1.),l.fillna(1.),c.fillna(1.))
 ex={k:v[idx.get_indexer(ds)] for k,v in exfull.items()}
 obs=np.column_stack([rawO.loc[ds].notna().to_numpy()&(rawO.loc[ds].to_numpy()>0),np.ones((len(ds),2),bool)])
 lowobs=np.column_stack([mats['Low'].loc[ds].notna().to_numpy(),np.ones((len(ds),2),bool)])
 # Risk estimates never imply an observed gap on a closed exchange.
 # Preserve original breadth denominator (local universe + cash) for identity; mark missing gap zero.
 ex['gap'][~obs]=0.;ex['ud1']=np.mean(ex['gap']<-.01,axis=1);ex['uneg']=np.mean(ex['gap']<0,axis=1)
 coverage=[]
 for j,d in enumerate(dates):
  coverage.append({'signal_date':d,'entry_date':entries[j],'return_count':int(np.isfinite(rr[j]).sum()),'hybrid_current_count':int(np.isfinite(tt[j]).sum()),'hybrid_smoothed_count':int(np.isfinite(hy[j]).sum()),'combined_count':int(np.isfinite(score[j]).sum()),'raw_closes_count':int(rawC.loc[d].notna().sum())})
 pd.DataFrame(coverage).to_csv(OUT/'EU_MONTHLY_COVERAGE.csv',index=False)
 pd.DataFrame(score,index=dates,columns=T).to_csv(OUT/'EU_COMBINED_SCORE.csv')
 pd.DataFrame(rr,index=dates,columns=T).to_csv(OUT/'EU_RETURN_SCORE.csv');pd.DataFrame(hy,index=dates,columns=T).to_csv(OUT/'EU_HYBRID_SCORE.csv')
 # Exact score architecture; finite-mask only, not an invented zero score.
 carry=lambda a:pd.DataFrame(a,index=dates,columns=T).ffill(limit=1).to_numpy()
 mask=np.isfinite(score)
 repair=score_blend(carry(rr),carry(et),carry(x))
 # New DIAGNOSTIC: carry missing native forecast for at most one monthly event.
 # It is a stale-forecast fallback, not a newly predicted December signal.
 cohorts={'RETURN_H':score,'RETURN_ONLY':rr,'HYBRID_ONLY':hy,'MOM252':mat('MOM252'),
          'RETURN_MATCHED':np.where(mask,rr,np.nan),'HYBRID_MATCHED':np.where(mask,hy,np.nan),
          'MOM252_MATCHED':np.where(mask,mat('MOM252'),np.nan),'ASOF1_RETURN_H':repair}
 pd.DataFrame({'signal_date':dates,'original_finite':mask.sum(axis=1),'asof1_finite':np.isfinite(repair).sum(axis=1),'rr_carried':((~np.isfinite(rr))&np.isfinite(carry(rr))).sum(axis=1),'et_carried':((~np.isfinite(et))&np.isfinite(carry(et))).sum(axis=1)}).to_csv(OUT/'ASOF1_DIAGNOSTIC_COVERAGE.csv',index=False)
 pd.DataFrame(repair,index=dates,columns=T).to_csv(OUT/'EU_ASOF1_COMBINED_SCORE.csv')
 records=[]
 for name,s in cohorts.items():
  d1=np.full((1,len(ds)),-1,np.int16);d2=d1.copy();wg=np.ones((1,len(ds)));margin=np.zeros_like(wg);ags=np.zeros_like(wg,bool)
  lastids=[];lastmargin=0.;lastweight=1.;lastagree=False
  for i,r in enumerate(cal.itertuples(index=False)):
   ids=select_pair(s[i]);a=ds.searchsorted(r.entry_date);e=ds.searchsorted(r.exit_date)
   if len(ids)==2:
    # same original argpartition order, after excluding NaNs; any ties recorded
    safe=np.where(np.isfinite(s[i]),s[i],-np.inf)
    part=np.argpartition(safe,-2)[-2:];ids=part[np.argsort(-safe[part])].tolist()
    mg=float(s[i,ids[0]]-s[i,ids[1]]);w=.60+.40*min(mg/.13,1.)**2
    et_i=carry(et)[i] if name=='ASOF1_RETURN_H' else et[i]
    x_i=carry(x)[i] if name=='ASOF1_RETURN_H' else x[i]
    ag=bool(et_i[ids[0]]>et_i[ids[1]] and x_i[ids[0]]>x_i[ids[1]])
    lastids=ids;lastmargin=mg;lastweight=w;lastagree=ag
   if len(lastids)==2:
    d1[0,a:e]=lastids[0];d2[0,a:e]=lastids[1];wg[0,a:e]=lastweight;margin[0,a:e]=lastmargin;ags[0,a:e]=lastagree
   records.append({'selector':name,'signal_date':r.signal_date,'n_finite':int(np.isfinite(s[i]).sum()),'top1':T[lastids[0]] if lastids else '', 'top2':T[lastids[1]] if lastids else '','margin':lastmargin,'refreshed':len(ids)==2,'entry_date':r.entry_date,'exit_date':r.exit_date})
  alloc=producer.AllocationResult(d1,d2,wg,margin)
  for weight in (['ORIGINAL','HALF'] if name in ['RETURN_H','ASOF1_RETURN_H'] else ['HALF']):
   if weight=='HALF':basew=np.full_like(wg,.5);mg=np.zeros_like(margin);aa=producer.AllocationResult(d1,d2,basew,mg)
   else:basew=wg;aa=alloc
   weights=stage.confidence_weights(aa,g,ags,np.zeros_like(ags),mode='current_plus_models_riskoff')
   vclose=c.loc[ds].copy();vclose.columns=T+['BIL','SHV'];vclose['SPY']=macro.SPY.loc[ds]
   allowed=np.column_stack([rawC.loc[ds].notna().to_numpy(),np.zeros((len(ds),3),bool)])
   with warnings.catch_warnings():
    warnings.simplefilter('ignore');state=build_v6(vclose,d1,d2,basew,gross,allowed=allowed)
   assert np.all((state.alt_idx<165)|(state.alt_idx==-1))
   path=B/'inputs'/f'EU_STATE_{name}_{weight}.npz'
   np.savez_compressed(path,dates=ds.values,tickers=t_all,d1=d1,d2=d2,margin=aa.margin,basew=basew,weights=weights,g=g,gross=gross,alt=state.alt_idx,observed=obs,low_observed=lowobs,**ex)
   print('STATE',name,weight,'months',len(dates),'days',len(ds),'V6days',int((state.alt_idx>=0).sum()),flush=True)
 pd.DataFrame(records).to_csv(OUT/'EU_MONTHLY_DECISIONS.csv',index=False)
 cal.to_csv(OUT/'EU_CALENDAR.csv',index=False)
 (OUT/'EU_PORT_DIFFERENCES.json').write_text(json.dumps({'market':'EU165 full-universe Top2','cash':'EUR cash zero return; original US bill returns not used','macro':'real US SPY HYG IEF strictly before prior EU close; never investible','macro_alignment':macrodates,'features':'unchanged legacy compact125, built-in median-market fallback','Hybrid':'native archived EU ET/XGB; no invented missing predictions','quotes':'last observed Open for valuation carry only; no trade or stop on missing quote','native_formula_stop':'prior Close * (1-.055), conditional weakness/breadth, not cost anchor','unresolved':'same-opening gap decision/fill retained as legacy diagnostic; no total-return certification','source':str(SRC)},indent=2))
if __name__=='__main__':main()
