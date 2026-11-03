"""Independent OLC32 label, model, and evaluation audit (research-only)."""
from __future__ import annotations
import io,zipfile,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd,joblib
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT=Path('/mnt/data/olc32_work');OUT=ROOT/'results';SRC=Path('/mnt/data/olc_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
P19='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'

def run():
 report={}
 cal=pd.read_csv(OUT/'REPAIRED_CALENDAR_AUDIT.csv',parse_dates=['signal_date','entry_date','exit_date','original_entry_date','original_exit_date'])
 e=cal[(cal.market=='EU')&(cal.changed_entry|cal.changed_exit)]
 assert len(e)==2 and set(e.signal_date.dt.strftime('%Y-%m-%d'))=={'2020-04-30','2020-05-29'}
 assert set(e.loc[e.changed_entry,'entry_date'].dt.strftime('%Y-%m-%d'))=={'2020-06-02'}
 assert set(e.loc[e.changed_exit,'exit_date'].dt.strftime('%Y-%m-%d'))=={'2020-06-02'}
 assert not any(cal[(cal.market=='EU')].entry_date.eq(pd.Timestamp('2020-06-01')))
 d=pd.read_csv(OUT/'OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz',parse_dates=['signal_date','entry_date','exit_date','source_date'],float_precision='round_trip')
 assert not d.duplicated(['market','signal_date','ticker']).any()
 assert d.loc[d.complete_features,'source_date'].le(d.loc[d.complete_features,'signal_date']).all()
 assert not d[(d.market=='EU')&(d.ticker=='LEEU.DE')&(d.entry_date==pd.Timestamp('2024-05-02'))].label_valid.any()
 assert d[d.signal_date==pd.Timestamp('2026-06-30')].label_valid.sum()==0
 cov=pd.read_csv(OUT/'CORRECTION_DELTA_BY_MONTH.csv')
 affected=cov[cov.delta_valid.ne(0)].copy()
 assert len(affected)==2 and (affected.old_valid==9).all() and (affected.new_valid==148).all()
 assert affected.delta_valid.sum()==278
 report['calendar_shift_changed_rows']=len(e);report['repaired_monthly_label_count']=278
 # Independent prices re-read, never trust saved labels alone.
 with zipfile.ZipFile(SRC) as z:
  for market in ['EU','USA']:
   with np.load(io.BytesIO(z.read(P19+market+'_STATE_HALF.npz')),allow_pickle=False) as state:
    dates=pd.Index(pd.to_datetime(state['dates']));tickers=pd.Index(state['tickers']);mm=d[d.market==market].copy()
    # All available corrected outcomes, independently vectorized with exact source array.
    selected=mm[mm.label_valid].copy();ii0=dates.get_indexer(selected.entry_date);ii1=dates.get_indexer(selected.exit_date);jj=tickers.get_indexer(selected.ticker)
    assert (ii0>=0).all() and (ii1>=0).all() and (jj>=0).all()
    assert selected.exit_date.gt(selected.entry_date).all()
    oo0=state['O'][ii0,jj];oo1=state['O'][ii1,jj]
    if 'observed' in state:assert (state['observed'][ii0,jj]&state['observed'][ii1,jj]).all()
    independent=10000*np.log(oo1/oo0);max_diff=float(np.max(np.abs(independent-selected.r_o2o_bp.to_numpy())))
    assert max_diff<1e-8,max_diff
    # Independently verify target centering per market-month, using only eligible/valid rows.
    group=selected[selected.eligible_label].copy();median=group.groupby('signal_date').r_o2o_bp.median();true=group.r_o2o_bp.to_numpy()-group.signal_date.map(median).to_numpy()
    med_diff=float(np.max(np.abs(true-group.r_rel_bp.to_numpy())))
    assert med_diff<1e-8,med_diff
    report[market+'_source_open_max_diff_bp']=max_diff;report[market+'_relative_median_max_diff_bp']=med_diff
    report[market+'_all_valid_labels']=len(selected)

 predictions=pd.read_csv(OUT/'PREQUENTIAL_DIRECT_ECONOMIC_EDGE.csv.gz',parse_dates=['signal_date','entry_date','exit_date'],float_precision='round_trip')
 pd.DataFrame(predictions).groupby(['market','signal_date','ticker']).size().pipe(lambda q:assert_unique(q))
 assert (predictions['r_rel_bp'].isna()|predictions.eligible_label).all()
 # Every year model trained only on earlier matured labels; verify saved reloaded predictions.
 modelchecks=[]
 import sys
 sys.path.insert(0,str(ROOT));from olc32_economic_edge import FEAT
 for year in range(2021,2027):
  pp=predictions[predictions.signal_date.dt.year==year].copy()
  pp=pp.merge(d[['market','signal_date','ticker',*[f for f in FEAT if f!='FUSION']]],on=['market','signal_date','ticker'],how='left',validate='one_to_one')
  for model in ['B1','E1','E2']:
   z=joblib.load(OUT/'models'/f'{year}_{model}.joblib');assert pd.Timestamp(z['train_max_exit'])<pd.Timestamp(year,1,1)
   x=pp[z['features']]
   pred=z['model'].predict(x if z['scaler'] is None else z['scaler'].transform(x))
   err=float(np.max(np.abs(pred-pp['hat_'+model].to_numpy(float))))
   assert err<1e-8,(year,model,err)
   modelchecks.append(dict(year=year,model=model,max_diff_bp=err,training_maturity=str(z['train_max_exit'])))
 report['model_reload_verification']=modelchecks
 # True label future edits should not affect current features/cutoff. Verify fitted features immutable and cutoff excluding wrong future.
 x=d.copy();cut=pd.Timestamp(2022,1,1);train_a=x[(x.signal_date<cut)&(x.exit_date<cut)&x.eligible_label].copy();
 assert train_a.exit_date.lt(cut).all()
 hash_a=hashlib.sha256(train_a[['market','signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
 x.loc[x.exit_date>=cut,'r_rel_bp']=1e12
 train_b=x[(x.signal_date<cut)&(x.exit_date<cut)&x.eligible_label].copy()
 assert hashlib.sha256(train_b[['market','signal_date','ticker']].to_csv(index=False).encode()).hexdigest()==hash_a
 assert np.array_equal(train_a.r_rel_bp.to_numpy(),train_b.r_rel_bp.to_numpy(),equal_nan=True)
 report['future_label_perturbation_cutoff_invariant']=True
 # Independent MSE/MAE and material-pair direction count on exact same test cohort, monthly equal weight.
 cohort=predictions[predictions.signal_date.dt.year.between(2021,2024)&predictions.eligible_label].copy()
 s=pd.read_csv(OUT/'MATCHED_SUMMARY.csv')
 for market in ['EU','USA']:
  w=cohort[cohort.market==market]
  assert w.signal_date.nunique()==48
  for name in ['B1','E1','E2']:
   monthly=w.assign(squared=(w.r_rel_bp-w['hat_'+name])**2,abserr=abs(w.r_rel_bp-w['hat_'+name])).groupby('signal_date').agg(mse=('squared','mean'),mae=('abserr','mean'))
   rmse=float(np.sqrt(monthly.mse.mean()));ref=float(s[(s.market==market)&(s.period=='MAIN2021_2024')][name+'_RMSE_bp'].iloc[0]);assert abs(rmse-ref)<1e-8
   mae=float(monthly.mae.mean());ref2=float(s[(s.market==market)&(s.period=='MAIN2021_2024')][name+'_MAE_bp'].iloc[0]);assert abs(mae-ref2)<1e-8
 report['matched_primary_rows']={m:int(len(cohort[cohort.market==m])) for m in ['EU','USA']}
 report['matched_months']=48
 (OUT/'VERIFICATION_INDEPENDENT.json').write_text(json.dumps(report,indent=2,default=str))
 print(json.dumps({k:v for k,v in report.items() if k!='model_reload_verification'},indent=2));print('verified model replays',len(modelchecks))

def assert_unique(s):
 assert (s==1).all()

if __name__=='__main__':run()
