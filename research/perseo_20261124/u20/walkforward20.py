from run20 import *

def choose(months,year):
 x=months[(months.family=='LOCAL')&(months.bps==15)&(months.month>=f'{year-2}-01')&(months.month<f'{year}-01')]
 dates=sorted(x.month.unique());audit=[]
 assert len(dates)==24
 rng=np.random.default_rng(20261123+year);starts=rng.integers(0,24,(500,8));ix=((starts[:,:,None]+np.arange(3))%24).reshape(500,24)
 for rule in MODES[1:6]:
  dif=[];pen=[]
  for m in ['EU','USA','TR']:
   a=x[(x.market==m)&(x.rule==rule)].set_index('month').net_return.reindex(dates)
   b=x[(x.market==m)&(x.rule=='BASE')].set_index('month').net_return.reindex(dates)
   assert a.notna().all() and b.notna().all()
   dif.append((np.log1p(a)-np.log1p(b)).to_numpy())
   def dd(v):
    nav=np.r_[1,np.cumprod(1+v)];return -min(nav/np.maximum.accumulate(nav)-1)
   # Daily drawdown within the training window.
   def ddd(rule):
    z=load(DEST/f'{m}_LOCAL_{rule}_15.npz');keep=(z['dates']>=np.datetime64(f'{year-2}-01-01'))&(z['dates']<np.datetime64(f'{year}-01-01'));return -min(z['nav'][keep]/np.maximum.accumulate(z['nav'][keep])-1)
   pen.append(.5*max(0,ddd(rule)-ddd('BASE')))
  dif=np.array(dif).T;delta=dif.mean(0)*12
  score=float(min(delta-np.array(pen)));lower=float(np.quantile(np.min(dif[ix].mean(1)*12,axis=1),.2))
  audit.append(dict(year=year,rule=rule,score=score,worst_log_excess=float(min(delta)),lower80=lower,last_month=dates[-1],months=len(dates)))
 def best(strict):
  good=[a for a in audit if a['score']>0 and a['worst_log_excess']>0 and (not strict or a['lower80']>0)]
  return max(good,key=lambda a:a['score'])['rule'] if good else 'BASE'
 return best(True),best(False),audit

def main():
 mo=pd.read_csv(DEST/'MONTHLY_SCREEN.csv');plans=[];aud=[]
 for y in range(2022,2027):
  strict,plain,a=choose(mo,y);plans.append(dict(year=y,WF_CONFIDENCE=strict,WF_ECONOMIC=plain));aud.extend(a)
 plan=pd.DataFrame(plans);print(plan.to_string(index=False),flush=True);plan.to_csv(DEST/'WF_PLAN.csv',index=False);pd.DataFrame(aud).to_csv(DEST/'WF_SELECTION_AUDIT.csv',index=False)
 rows=[];months=[]
 for m in ['EU','USA','TR']:
  q=prepare(m,'LOCAL');years=pd.DatetimeIndex(q['dates']).year
  for name in ['WF_CONFIDENCE','WF_ECONOMIC']:
   modes=np.zeros(len(years),int)
   for a in plans:modes[years==a['year']]=MODES.index(a[name])
   for bps in [15,30]:
    r,mm=run(q,name,m,'LOCAL',bps,modes);rows.append(r);months.extend(mm)
  for name in ['BASE','ISOLATED','VOLATILITY']:
   r,mm=run(q,name,m,'LOCAL',30);rows.append(r);months.extend(mm)
 for name in ['BASE','ISOLATED','VOLATILITY']:
  r,mm=run(prepare('USA','NATIVE_REFERENCE'),name,'USA','NATIVE_REFERENCE',30);rows.append(r);months.extend(mm)
 pd.DataFrame(rows).to_csv(DEST/'WF_STRESS.csv',index=False);pd.DataFrame(months).to_csv(DEST/'MONTHLY_WF_STRESS.csv',index=False)
if __name__=='__main__':main()
