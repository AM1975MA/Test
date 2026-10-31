"""Independent arithmetic/coverage verification, without importing replay helpers."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];out=R/'results/verification';out.mkdir(exist_ok=True)
checks=[];errors=[]
for stage in ['native','rebuilt','execution']:
 root=R/'results'/stage;sc=pd.read_csv(root/'SCORECARD.csv');pairs=sc[['market','config']].drop_duplicates()
 assert len(pairs)=={'native':912,'rebuilt':488,'execution':40}[stage]
 assert sc.groupby('config').market.nunique().eq(2).all()
 assert not sc.duplicated(['market','config','period']).any()
 maxnav=maxpnl=maxcagr=maxdd=0.;numvals=0
 for z in pairs.itertuples(index=False):
  p=root/'paths'/f'{z.market}_{z.config}.npz';a=np.load(p,allow_pickle=False);nav=a['nav'];ld=a['ledger'];ds=pd.DatetimeIndex(a['dates']);D=len(nav)
  assert ds.is_unique and ds.is_monotonic_increasing and (nav>0).all() and np.isfinite(nav).all()
  rec=1+np.cumsum(ld[:-1,38]);rec=np.r_[rec,rec[-1]];en=float(np.max(abs(rec-nav)));maxnav=max(maxnav,en);assert en<1e-9,(stage,z,en)
  component=ld[:-1,31:38].sum(axis=1)-ld[:-1,45];ep=float(np.max(abs(component-ld[:-1,38])));maxpnl=max(maxpnl,ep);assert ep<1e-9
  assert np.max(abs(ld[1:-1,0]-nav[:-2]))<1e-9
  windows={'FULL':(ds[0],ds[-1]),'COMMON_2019_2026':('2019-02-01','2026-07-01'),'PRE2025':('2019-02-01','2024-12-31'),'2020_CRASH':('2020-02-01','2020-03-31'),'LATE2021_2023':('2021-11-01','2023-12-31')}
  windows.update({str(y):(f'{y}-01-01',f'{y}-12-31') for y in range(2019,2027)})
  rows=sc[(sc.market==z.market)&(sc.config==z.config)].set_index('period')
  for name,(first,last) in windows.items():
   ids=np.flatnonzero((ds>=pd.Timestamp(first))&(ds<=pd.Timestamp(last)))
   if not len(ids):continue
   base=1. if ids[0]==0 else nav[ids[0]-1];v=nav[ids]/base
   cagr=float((v[-1])**(252/len(v))-1);dd=float((v/np.maximum.accumulate(np.r_[1.,v])[1:]-1).min())
   ec=abs(cagr-rows.loc[name,'cagr']);ed=abs(dd-rows.loc[name,'maxdd']);maxcagr=max(maxcagr,ec);maxdd=max(maxdd,ed);numvals+=2
   assert ec<1e-10 and ed<1e-10 and rows.loc[name,'n']==len(v),(stage,z,name,ec,ed)
  checks.append({'stage':stage,'market':z.market,'config':z.config,'rows':D,'max_nav_rebuild_error':en,'max_pnl_identity_error':ep,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
 errors.append({'stage':stage,'paths':len(pairs),'metric_values_recomputed':numvals,'max_nav_error':maxnav,'max_pnl_error':maxpnl,'max_cagr_error':maxcagr,'max_maxdd_error':maxdd})
 print('VERIFIED',errors[-1],flush=True)
pd.DataFrame(checks).to_csv(out/'ALL_PATHS_HASHES_AND_CHECKS.csv',index=False)
model=[]
for p in (R/'results/calendar/models').glob('*'):
 model.append({'file':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(model)==96 # 80 predictive models and 16 training-only imputers
(out/'MODEL_MANIFEST.json').write_text(json.dumps(model,indent=2))
summary={'path_checks':errors,'total_replays':len(checks),'new_predictive_models':80,'training_imputers':16,'forecast_months_per_market':90,'same_spec_US_EU':True,'four_original_reference_errors':json.loads((R/'results/native/PARITY.json').read_text()),'calendar_checks':json.loads((R/'results/calendar/CAUSAL_CHECKS.json').read_text()),'limitations':'Arithmetic and declared temporal checks; not total-return, delisting, all-data provenance or same-Open live-fill certification. No independent reviewer agent available; tests and recomputation performed in this session.'}
(out/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print('ALL_VERIFIED',len(checks),flush=True)
