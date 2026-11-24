from run20 import *

def path(m,expert):
 if expert=='LOCAL':return DEST/f'{m}_LOCAL_BASE_15.npz'
 if m=='USA':return DEST/'USA_NATIVE_REFERENCE_BASE_15.npz'
 fam='TRANSFER' if expert=='TRANSFER_CASH' else 'TRANSFER_LOCAL'
 return DEST/f'{m}_{fam}_TRANSFER_BASE_15.npz'

def plan():
 saved={(m,e):load(path(m,e)) for m in ['EU','USA','TR'] for e in ['LOCAL','TRANSFER_CASH','TRANSFER_LOCAL']};rows=[];choices=[]
 for year in range(2022,2027):
  rng=np.random.default_rng(20261123+year);ix=((rng.integers(0,24,(500,8,1))+np.arange(3))%24).reshape(500,24);audit=[]
  for expert in ['TRANSFER_CASH','TRANSFER_LOCAL']:
   ds=[];pen=[]
   for m in ['EU','USA','TR']:
    vals=[];dds=[]
    for e in [expert,'LOCAL']:
     z=saved[m,e];s=pd.Series(z['nav'],index=pd.DatetimeIndex(z['dates']));r=s.pct_change().fillna(0);mo=(1+r).groupby(s.index.to_period('M')).prod()-1
     take=mo[(mo.index>=f'{year-2}-01')&(mo.index<f'{year}-01')];assert len(take)==24;vals.append(np.log1p(take.to_numpy()))
     seg=s[(s.index>=f'{year-2}-01-01')&(s.index<f'{year}-01-01')];dds.append(-min(seg/seg.cummax()-1))
    ds.append(vals[0]-vals[1]);pen.append(.5*max(0,dds[0]-dds[1]))
   ds=np.array(ds).T;delta=ds.mean(0)*12;score=float(min(delta-np.array(pen)));lower=float(np.quantile(np.min(ds[ix].mean(1)*12,axis=1),.2))
   row=dict(year=year,expert=expert,score=score,worst_log_excess=float(min(delta)),lower80=lower,last_month=f'{year-1}-12');rows.append(row);audit.append(row)
  one={'year':year}
  for strict,name in [(False,'WF_ARCH_ECONOMIC'),(True,'WF_ARCH_CONFIDENCE')]:
   ok=[a for a in audit if a['score']>0 and a['worst_log_excess']>0 and (not strict or a['lower80']>0)]
   one[name]=max(ok,key=lambda a:a['score'])['expert'] if ok else 'LOCAL'
  choices.append(one)
 pd.DataFrame(rows).to_csv(DEST/'ARCH_SELECTION_AUDIT.csv',index=False);pd.DataFrame(choices).to_csv(DEST/'ARCH_PLAN.csv',index=False);print(pd.DataFrame(choices).to_string(index=False),flush=True);return choices

def main():
 choices=plan();rows=[];months=[]
 for m in ['EU','USA','TR']:
  lib={'LOCAL':prepare(m,'LOCAL')}
  for e in ['TRANSFER_CASH','TRANSFER_LOCAL']:
   lib[e]=prepare(m,'NATIVE_REFERENCE') if m=='USA' else load(STATES/f'{m}_{"TRANSFER" if e=="TRANSFER_CASH" else e}.npz')
  for name in ['WF_ARCH_ECONOMIC','WF_ARCH_CONFIDENCE']:
   q={k:v.copy() for k,v in lib['LOCAL'].items()};years=pd.DatetimeIndex(q['dates']).year
   for choice in choices:
    ix=years==choice['year'];source=lib[choice[name]]
    for key in ['d1','d2','weights','basew','alt']:q[key][:,ix]=source[key][:,ix]
    q['events'][ix]=source['events'][ix];q['events'][np.flatnonzero(ix)[0]]=True
   for bps in [15,30]:
    r,mm=run(q,name,m,'ARCHITECTURE',bps);rows.append(r);months.extend(mm)
   np.savez_compressed(STATES/f'{m}_{name}.npz',**q)
 # BASE risk/cost and 1-session stale decision stress for the unified candidate.
 for m in ['EU','TR']:
  q=load(STATES/f'{m}_TRANSFER_LOCAL.npz')
  r,mm=run(q,'TRANSFER_BASE',m,'TRANSFER_LOCAL',30);rows.append(r);months.extend(mm)
  z={k:v.copy() for k,v in q.items()}
  for key in ['d1','d2','alt']:z[key][:,1:]=q[key][:,:-1]
  z['events'][1:]=q['events'][:-1];z['events'][0]=True
  r,mm=run(z,'TRANSFER_BASE_LAG1',m,'TRANSFER_LOCAL');rows.append(r);months.extend(mm)
 pd.DataFrame(rows).to_csv(DEST/'ARCH_SUMMARY.csv',index=False);pd.DataFrame(months).to_csv(DEST/'MONTHLY_ARCH.csv',index=False)
if __name__=='__main__':main()
