import setup_paths
from setup_paths import ROOT,OLC2,OLC3
from assets import Assets,PARENT,digest
from pair_controller import PairController
from selective_controller import SelectiveController
from information_bank import InformationBank,InformationCalibration
from relative_information import Information
from run_pairs import metrics
import numpy as np,pandas as pd,json,time,sys

def configurations():
 yield 'CL01_HALF',None,None,None,None
 yield 'CL01_ORIGINAL',None,None,None,None
 for feature in ['OLD','REL','PEER']:
  for family in ['RIDGE','HGB']:
   for h in ['21','PROFILE']:
    for kind in ['RAW','UTILITY']:yield f'{feature}_{kind}_{family}_{h}',feature,family,h,kind

def run(market):
 t=time.time();a=Assets(market);rows=[];au=[]
 info=Information(pd.read_pickle(PARENT/f'inputs/{market}_Close.pkl').reindex(columns=a.score.columns))
 banks={f:InformationBank(a,f,info) for f in ['OLD','REL','PEER']}
 calibrations={f:InformationCalibration(market,f) for f in banks}
 for folder in ['paths','decisions','actions']:(ROOT/'results'/folder).mkdir(exist_ok=True)
 for name,familyset,family,h,kind in configurations():
  for fee in [.001,.003]:
   if kind=='RAW':c=PairController(a,banks[familyset],f'{family}_{h}_FULL',fee)
   elif kind=='UTILITY':c=SelectiveController(a,banks[familyset],calibrations[familyset],family,h,'UTILITY',fee,.05)
   else:c=None
   E,T,X,AW,L=a.run(controller=c,fee=fee,original=name=='CL01_ORIGINAL');nav=E[0];led=L[0]
   assert np.isfinite(nav).all() and nav.min()>0 and np.max(abs(led[:-1,46]))<1e-9
   cfg=f'{name}_C{int(fee*10000)}';path=ROOT/f'results/paths/{market}_{cfg}.npz'
   np.savez_compressed(path,dates=a.ds.values,nav=nav,ledger=led,tickers=a.names)
   if c:
    pd.DataFrame(c.records).to_csv(ROOT/f'results/decisions/{market}_{cfg}.csv',index=False)
    pd.DataFrame(c.action_records).to_csv(ROOT/f'results/actions/{market}_{cfg}.csv.gz',index=False,compression='gzip')
   parity=None
   if kind is None:
    ref=np.load(OLC2/f'results/paths/{market}_{cfg}.npz')['nav'];parity=float(np.max(abs(nav-ref)))
   elif familyset=='OLD':
    oldname=f'{family}_{h}_FULL' if kind=='RAW' else f'UTILITY_{family}_{h}'
    parent=OLC2 if kind=='RAW' else OLC3
    ref=np.load(parent/f'results/paths/{market}_{oldname}_C{int(fee*10000)}.npz')['nav'];parity=float(np.max(abs(nav-ref)))
   else:
    ref=np.load(OLC2/f'results/paths/{market}_CL01_HALF_C{int(fee*10000)}.npz')['nav'];warm=a.ds<'2021-02-01';assert np.array_equal(nav[warm],ref[warm])
   if parity is not None:assert parity<1e-12,(market,name,fee,parity)
   for r in metrics(nav,led,a.ds):rows.append(dict(market=market,feature_set=familyset or 'CONTROL',policy=name,fee=fee,config=cfg,**r))
   au.append(dict(market=market,config=cfg,parent_parity_error=parity,accounting_error=float(np.max(abs(led[:-1,46]))),sha256=digest(path)))
   print('REPLAY',market,cfg,'elapsed',round(time.time()-t,1),flush=True)
  pd.DataFrame(rows).to_csv(ROOT/f'results/{market}_SCORECARD.csv',index=False);pd.DataFrame(au).to_csv(ROOT/f'results/{market}_PATH_AUDIT.csv',index=False)
 cas=[]
 for name,cb in calibrations.items():cas.extend([dict(feature_set=name,**r) for r in cb.audit])
 pd.DataFrame(cas).to_csv(ROOT/f'results/{market}_CALIBRATIONS.csv',index=False)
 print('DONE',market,len(au),'paths',flush=True)
if __name__=='__main__':
 for m in sys.argv[1:] or ['EU','USA']:run(m)
 pd.concat([pd.read_csv(ROOT/f'results/{m}_SCORECARD.csv') for m in ['EU','USA']]).to_csv(ROOT/'results/SCORECARD.csv',index=False)
