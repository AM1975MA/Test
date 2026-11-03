"""OLC32: authenticated source-only label repair and direct next Open-to-Open advantage learning.

Research-only. See preregistered PROTOCOL.md. Never mutate frozen parent account data.
"""
from __future__ import annotations
import io, os, sys, json, zipfile, hashlib, time, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import HistGradientBoostingRegressor
import joblib

ROOT=Path('/mnt/data/olc32_work'); OUT=ROOT/'results'; OUT.mkdir(parents=True,exist_ok=True)
ARCH={
'OLC08_SOURCE':Path('/mnt/data/olc_sources/OLC08_01_Pannelli_Verificati_20261101.zip'),
'OLC08_PRED':Path('/mnt/data/magnitude_audit_sources/OLC08_03_RSI_Confronto_Verificato_20261101.zip'),
'OLC19':Path('/mnt/data/olc_sources/OLC19_Rischio_Rientro_Checkpoint_20261102.zip'),
'OLC20':Path('/mnt/data/OLC20_Regime_Validation_Final_20261102.zip'),
}
SHA={'OLC08_SOURCE':'945faa5816aa627c398244d1b2a599fc2ba31f35fa6d789379264b0912d0be02',
'OLC08_PRED':'0dbcb8ee93cd0acaefd7505a202fbf30c9fda8df1804d90a0dd1578abd704f4b',
'OLC19':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
'OLC20':'a81be0fad1da73b48ba0af0080985657ee33e18a10f278db2318f9da06738a9c'}
P19='olc19_combined_risk_20261102/restore/olc18_execution_20261102/parent_archive/parent/olc16_contextual_rank_20261102/inputs/'
P08='parents/olc07_calendar_20261101/phases/P0/results/calendar/'
FEAT=['FUSION','ret_21','ret_63','ret_126','ret_252','mom_126_21','acc_5_21','acc_21_63',
'eff_21','eff_63','dd_21','dd_63','sma_ratio_50','sma_ratio_200','vol_21','vol_63','skew_63']
QUALITY=.70; MODEL_SEED=32001

def digest(path):
 h=hashlib.sha256()
 with open(path,'rb') as f:
  for chunk in iter(lambda:f.read(2**20),b''):h.update(chunk)
 return h.hexdigest()

def readcsv(z,name):
 return pd.read_csv(io.BytesIO(z.read(name)),float_precision='round_trip',compression='gzip' if name.endswith('.gz') else None)

def readnpz(z,name):
 with np.load(io.BytesIO(z.read(name)),allow_pickle=False) as a:return {k:a[k].copy() for k in a.files}

def official_calendar_fix(cal,market):
 d=cal.copy();d[['signal_date','entry_date','exit_date']]=d[['signal_date','entry_date','exit_date']].apply(pd.to_datetime)
 if market=='EU':
  for key in ['entry_date','exit_date']:
   d.loc[d[key].eq(pd.Timestamp('2020-06-01')),key]=pd.Timestamp('2020-06-02')
 # Confirm month signal t is truly before effective entry/exit; terminal may have entry==exit.
 assert (d.entry_date>d.signal_date).all()
 assert (d.exit_date>=d.entry_date).all()
 return d

def calculate_observed_returns(scores,cal,state,market):
 # New independent corrected month-level label computation (original state is immutable)
 data=scores[['signal_date','ticker','FUSION']].copy();data.signal_date=pd.to_datetime(data.signal_date)
 cc=cal[['signal_date','entry_date','exit_date']];d=data.merge(cc,on='signal_date',validate='many_to_one',how='left')
 assert not d.duplicated(['signal_date','ticker']).any()
 dates=pd.DatetimeIndex(state['dates']);ticker=list(state['tickers']);dix={v:i for i,v in enumerate(dates)};tix={v:i for i,v in enumerate(ticker)}
 assert d.ticker.isin(tix).all() and d.entry_date.isin(dix).all()
 i0=d.entry_date.map(dix).astype(int).to_numpy();j=d.ticker.map(tix).astype(int).to_numpy()
 has_exit=d.exit_date.isin(dix)&d.exit_date.gt(d.entry_date)
 i1=np.zeros(len(d),dtype=int);i1[has_exit]=d.loc[has_exit,'exit_date'].map(dix).astype(int)
 o0=state['O'][i0,j];o1=state['O'][i1,j]
 okay=np.isfinite(o0)&(o0>0)&np.isfinite(o1)&(o1>0)&has_exit.to_numpy()
 if market=='EU':
  assert 'observed' in state
  okay &= state['observed'][i0,j]&state['observed'][i1,j]
 r=np.full(len(d),np.nan);r[okay]=10000*np.log(o1[okay]/o0[okay])
 d['label_valid']=okay;d['r_o2o_bp']=r;d['entry_price_observed']=np.isfinite(o0)&(o0>0)
 if market=='EU':d['entry_price_observed']&=state['observed'][i0,j]
 d['exit_price_observed']=np.isfinite(o1)&(o1>0)&has_exit.to_numpy()
 if market=='EU':d['exit_price_observed']&=state['observed'][i1,j]
 d['quote_certification']= 'EU_SOURCE_OBSERVED' if market=='EU' else 'USA_FINITE_PREPARED_UNCERTIFIED'
 # median across VALID, not all fill-forward future returns
 d['month_quality']=d.groupby('signal_date')['label_valid'].transform('mean');d['eligible_label']=d.label_valid&d.month_quality.ge(QUALITY)
 d['r_rel_bp']=d.r_o2o_bp-d.where(d.eligible_label).groupby('signal_date')['r_o2o_bp'].transform('median')
 d.loc[~d.eligible_label,'r_rel_bp']=np.nan
 d['month_median_bp']=d.where(d.eligible_label).groupby('signal_date')['r_o2o_bp'].transform('median')
 return d

def prepare():
 manifest={k:dict(name=p.name,size=p.stat().st_size,sha256=digest(p),match=(digest(p)==SHA[k])) for k,p in ARCH.items()};assert all(v['match'] for v in manifest.values())
 frames=[];audits=[];dates_aud=[];fcheck=[]
 with zipfile.ZipFile(ARCH['OLC08_SOURCE']) as z08,zipfile.ZipFile(ARCH['OLC19']) as z19,zipfile.ZipFile(ARCH['OLC20']) as z20:
  for market in ['EU','USA']:
   score=readcsv(z20,f'results/trials/AUTH/{market}_SCORES.csv.gz')
   scores=score[['signal_date','ticker','FUSION']].copy()
   cal=readcsv(z19,P19+f'{market}_CALENDAR.csv')
   corrected=official_calendar_fix(cal,market)
   state=readnpz(z19,P19+f'{market}_STATE_HALF.npz')
   oldcal=official_calendar_fix(cal,'USA') # unchanged original for EU comparison
   older=calculate_observed_returns(scores,oldcal,state,market)
   revised=calculate_observed_returns(scores,corrected,state,market)
   joint=older[['signal_date','ticker','r_o2o_bp','label_valid']].merge(revised[['signal_date','ticker','r_o2o_bp','label_valid']],on=['signal_date','ticker'],suffixes=('_old','_new'),validate='one_to_one')
   for date,grp in joint.groupby('signal_date'):
    old_valid=int(grp.label_valid_old.sum());new_valid=int(grp.label_valid_new.sum()); n_changed=int(np.sum(grp.label_valid_old.to_numpy()!=grp.label_valid_new.to_numpy()));
    old_ret=grp.r_o2o_bp_old.to_numpy();new_ret=grp.r_o2o_bp_new.to_numpy();num_value_changed=int(np.sum((np.isfinite(old_ret)&np.isfinite(new_ret))&(np.abs(old_ret-new_ret)>1e-9)))
    audits.append(dict(market=market,signal_date=str(date.date()),n=len(grp),old_valid=old_valid,new_valid=new_valid,delta_valid=new_valid-old_valid,masked_validity_changes=n_changed,finite_return_changes=num_value_changed))
   hybrid=pd.read_pickle(io.BytesIO(z08.read(P08+market+'_HYBRID.pkl')))
   assert hybrid[['signal_date','ticker']].duplicated().sum()==0
   assert (pd.to_datetime(hybrid.source_date)<=pd.to_datetime(hybrid.signal_date)).all()
   assert all(c in hybrid for c in FEAT if c!='FUSION')
   sf=hybrid[['signal_date','ticker','source_date',*[x for x in FEAT if x!='FUSION']]].copy()
   sf['signal_date']=pd.to_datetime(sf.signal_date)
   before=len(revised);revised=revised.merge(sf,on=['signal_date','ticker'],how='left',validate='one_to_one');assert len(revised)==before
   # candidates' raw features are signal-time; never use future label or observed mask to filter scores
   for c in FEAT:revised[c]=pd.to_numeric(revised[c],errors='coerce')
   revised['complete_features']=np.isfinite(revised[FEAT].to_numpy(float)).all(axis=1)
   revised['market']=market;revised['feature_available_asof']=pd.to_datetime(revised.source_date).le(revised.signal_date)
   assert revised.loc[revised.complete_features,'feature_available_asof'].all()
   revised['auth_rank']=revised.groupby('signal_date').FUSION.rank(method='first',ascending=False).astype('Int64')
   # keep actual ticker order deterministic for tie-break
   revised=revised.sort_values(['signal_date','FUSION','ticker'],ascending=[True,False,True],kind='stable')
   revised['auth_rank']=revised.groupby('signal_date').cumcount()+1
   print('MARKET',market,'total',len(revised),'complete',int(revised.complete_features.sum()),'labels valid',int(revised.eligible_label.sum()))
   frames.append(revised)
   cal2=corrected.copy();cal2['market']=market;cal2['original_entry_date']=pd.to_datetime(cal.entry_date);cal2['original_exit_date']=pd.to_datetime(cal.exit_date)
   cal2['changed_entry']=cal2.original_entry_date.ne(cal2.entry_date);cal2['changed_exit']=cal2.original_exit_date.ne(cal2.exit_date);dates_aud.append(cal2)
   for m in sorted(revised.signal_date.unique()):
    s=revised[revised.signal_date==m];fcheck.append(dict(market=market,signal_date=str(pd.Timestamp(m).date()),n=len(s),complete_features=int(s.complete_features.sum()),eligible_labels=int(s.eligible_label.sum()),valid_fraction=float(s.label_valid.mean()),month_quality=float(s.month_quality.iloc[0]),has_terminal_no_label=bool((s.exit_date==s.entry_date).all())))
  new=pd.concat(frames,ignore_index=True)
  # Legacy FUSION preserved untouched against input. no output from legacy strategy altered.
  assert not new.duplicated(['market','signal_date','ticker']).any()
  new.to_csv(OUT/'OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz',index=False,compression='gzip')
  pd.concat(dates_aud).to_csv(OUT/'REPAIRED_CALENDAR_AUDIT.csv',index=False)
  pd.DataFrame(audits).to_csv(OUT/'CORRECTION_DELTA_BY_MONTH.csv',index=False)
  pd.DataFrame(fcheck).to_csv(OUT/'PER_MONTH_COVERAGE.csv',index=False)
  with open(OUT/'INPUT_MANIFEST.json','w') as f:json.dump(dict(inputs=manifest,protocol='730901d603a9a192db6499fc14d8a1e59ae9643a',fixed_date='2020-06-02',open_holiday='2020-06-01',LEEU_unobserved='2024-05-02',USA_original_observed_mask='MISSING',feature_names=FEAT,notes='Original archived quotes, signals, models, portfolio NAV unchanged; label overlay only'),f,indent=2)
  return new

def load():
 p=OUT/'OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz';return pd.read_csv(p,parse_dates=['signal_date','entry_date','exit_date','source_date'],compression='gzip',float_precision='round_trip')

def cutoff_train(d,year):
 cutoff=pd.Timestamp(year,1,1)
 sample=d[(d.signal_date<cutoff)&(d.exit_date<cutoff)&d.eligible_label&d.complete_features].copy()
 sample=sample[np.isfinite(sample.r_rel_bp)&np.isfinite(sample[FEAT]).all(axis=1)]
 if any(sample.loc[sample.market==m,'signal_date'].nunique()<12 for m in ['EU','USA']):return None
 assert (sample.exit_date<cutoff).all()
 return sample

def balanced_weights(d):
 count=d.groupby(['market','signal_date']).size();months=d.groupby('market').signal_date.nunique()
 assert months.min()>0
 weights=d.apply(lambda r:0.5/(months.loc[r.market]*count.loc[(r.market,r.signal_date)]),axis=1).to_numpy(float)
 assert np.isclose(weights.sum(),1.)
 assert np.isclose(weights[d.market.eq('EU')].sum(),.5) and np.isclose(weights[d.market.eq('USA')].sum(),.5)
 return weights*len(d)

def fit_models(data):
 w=balanced_weights(data);y=data.r_rel_bp.to_numpy(float)
 b1=StandardScaler().fit(data[['FUSION']],sample_weight=w)
 m1=Ridge(alpha=10).fit(b1.transform(data[['FUSION']]),y,sample_weight=w)
 b2=StandardScaler().fit(data[FEAT],sample_weight=w)
 m2=Ridge(alpha=100).fit(b2.transform(data[FEAT]),y,sample_weight=w)
 m3=HistGradientBoostingRegressor(loss='squared_error',max_iter=100,learning_rate=.04,max_leaf_nodes=7,min_samples_leaf=100,l2_regularization=50,early_stopping=False,random_state=MODEL_SEED).fit(data[FEAT],y,sample_weight=w)
 return {'B1':(b1,m1),'E1':(b2,m2),'E2':(None,m3)}

def predict_one(model,df,cols):
 scaler,m=model
 if scaler is None:
  return m.predict(df[cols])
 return m.predict(scaler.transform(df[cols]))

def train():
 d=load(); rows=[];audit=[]; mod_dir=OUT/'models';mod_dir.mkdir(exist_ok=True)
 for year in range(2021,2027):
  tr=cutoff_train(d,year)
  test=d[d.signal_date.dt.year==year].copy();test=test[test.complete_features].copy()
  auditrow=dict(year=year,train_n=int(len(tr)) if tr is not None else 0,train_months={m:int(tr[tr.market==m].signal_date.nunique()) for m in ['EU','USA']} if tr is not None else None,test_n=len(test),last_train_maturity=str(tr.exit_date.max()) if tr is not None else None)
  if tr is None or len(test)==0:auditrow['reason']='insufficient_mature_history_or_no_test';audit.append(auditrow);continue
  models=fit_models(tr)
  for model,cols in [('B1',['FUSION']),('E1',FEAT),('E2',FEAT)]:
   scaler,fitted=models[model]
   test['hat_'+model]=predict_one(models[model],test,cols)
   joblib.dump(dict(features=cols,scaler=scaler,model=fitted,year=year,train_max_exit=tr.exit_date.max(),train_keys_sha256=hashlib.sha256(tr[['market','signal_date','ticker','exit_date']].to_csv(index=False).encode()).hexdigest()),mod_dir/f'{year}_{model}.joblib')
  auditrow['models']=['B1','E1','E2'];audit.append(auditrow)
  rows.append(test[['market','signal_date','ticker','entry_date','exit_date','auth_rank','label_valid','eligible_label','complete_features','FUSION','r_o2o_bp','r_rel_bp','hat_B1','hat_E1','hat_E2']].copy())
  print(f'fit year={year} trainrows={len(tr)} testrows={len(test)} last_known={tr.exit_date.max().date()}',flush=True)
 if not rows:raise RuntimeError('No trained years')
 allout=pd.concat(rows,ignore_index=True); allout.to_csv(OUT/'PREQUENTIAL_DIRECT_ECONOMIC_EDGE.csv.gz',index=False,compression='gzip')
 (OUT/'FIT_AUDIT.json').write_text(json.dumps({'protocol':'730901d603a9a192db6499fc14d8a1e59ae9643a','training_audit':audit,'model_set':['B1','E1','E2'],'no_strategy_change':True},indent=2))
 return allout

def evaluate():
 p=OUT/'PREQUENTIAL_DIRECT_ECONOMIC_EDGE.csv.gz';d=pd.read_csv(p,parse_dates=['signal_date','entry_date','exit_date'],float_precision='round_trip')
 d=d[d.eligible_label & np.isfinite(d.r_rel_bp)].copy()
 ms=[];prs=[];paired=[]
 for (market,signal),g in d.groupby(['market','signal_date'],sort=True):
  row={'market':market,'signal_date':signal,'year':signal.year,'n':len(g)}
  for m in ['B1','E1','E2']:
   x=g['hat_'+m].to_numpy(float);y=g.r_rel_bp.to_numpy(float)
   row[m+'_mse']=float(np.mean((x-y)**2));row[m+'_mae']=float(np.mean(np.abs(x-y)))
  top=g[g.auth_rank<=5].sort_values(['auth_rank','ticker']).copy()
  row['top5_valid']=int(len(top))
  for m in ['B1','E1','E2']:
   pairs=[];true=[];pred=[]
   for i in range(len(top)):
    for j in range(i+1,len(top)):
     p1=top.iloc[i];p2=top.iloc[j]
     yi=p1.r_rel_bp-p2.r_rel_bp;pi=p1['hat_'+m]-p2['hat_'+m]
     true.append(yi);pred.append(pi)
   yy=np.asarray(true);pp=np.asarray(pred)
   row[m+'_top5_pair_mae']=float(np.mean(np.abs(yy-pp))) if len(yy) else np.nan
   row[m+'_material_n']=int(np.sum(np.abs(yy)>=100))
   row[m+'_material_correct_n']=int(np.sum((yy*pp>0)&(np.abs(yy)>=100)))
   row[m+'_material_sign_accuracy']=row[m+'_material_correct_n']/row[m+'_material_n'] if row[m+'_material_n'] else np.nan
   if len(yy):
    for j in range(len(yy)):
     paired.append({'market':market,'signal_date':signal,'model':m,'realized_spread_bp':float(yy[j]),'predicted_spread_bp':float(pp[j]),'material_edge':bool(abs(yy[j])>=100)})
  ms.append(row)
 months=pd.DataFrame(ms);months.to_csv(OUT/'MATCHED_MONTHLY_MODEL_ERRORS.csv',index=False)
 pd.DataFrame(paired).to_csv(OUT/'TOP5_PAIRWISE_SPREADS.csv',index=False)
 main=months[months.year.between(2021,2024)];out=[]
 for m in ['EU','USA']:
  for period,df in [('MAIN2021_2024',main[main.market==m]),('YEAR2025',months[(months.market==m)&(months.year==2025)]),('YEAR2026_PARTIAL',months[(months.market==m)&(months.year==2026)])]:
   if not len(df):continue
   row=dict(market=m,period=period,months=len(df),avg_n=float(df.n.mean()))
   for mm in ['B1','E1','E2']:
    row[mm+'_RMSE_bp']=float(np.sqrt(df[mm+'_mse'].mean()));row[mm+'_MAE_bp']=float(df[mm+'_mae'].mean())
    row[mm+'_Top5_pair_MAE_bp']=float(df[mm+'_top5_pair_mae'].mean())
    row[mm+'_material_edges']=int(df[mm+'_material_n'].sum());row[mm+'_material_sign_acc']=float(df[mm+'_material_correct_n'].sum()/max(1,df[mm+'_material_n'].sum()))
   for mm in ['E1','E2']:
    row[mm+'_MSE_improvement_bp2']=float((df['B1_mse']-df[mm+'_mse']).mean())
    row[mm+'_Top5_MAE_improvement_bp']=float((df['B1_top5_pair_mae']-df[mm+'_top5_pair_mae']).mean())
   out.append(row)
 summary=pd.DataFrame(out);summary.to_csv(OUT/'MATCHED_SUMMARY.csv',index=False)
 # fixed bootstrap same calendar month block 6 months, within each EU/USA month paired
 pairmonth=main.copy();pairmonth['month']=pairmonth.signal_date.dt.to_period('M')
 universe={m:pairmonth[pairmonth.market==m].sort_values('month') for m in ['EU','USA']}
 rng=np.random.default_rng(32001);n=48
 assert all(len(universe[m])==n for m in ['EU','USA']);assert universe['EU'].month.tolist()==universe['USA'].month.tolist()
 draws=np.stack([np.concatenate([(np.arange(start,start+6)%n) for start in rng.integers(0,n,size=8)])[:n] for _ in range(3000)])
 boot=[]
 for mod in ['E1','E2']:
  for metric,suffix in [('mse','mse'),('top5_pair_mae','top5_pair_mae')]:
   joint=[]
   for m in ['EU','USA']:
    x=(universe[m]['B1_'+suffix]-universe[m][mod+'_'+suffix]).to_numpy(float)
    bs=x[draws].mean(axis=1);boot.append(dict(model=mod,market=m,metric=metric,improvement_mean=float(x.mean()),ci_low=float(np.quantile(bs,.025)),ci_high=float(np.quantile(bs,.975)),months=48,nboot=3000,block=6))
    joint.append(bs)
   vals=np.minimum(joint[0],joint[1]);boot.append(dict(model=mod,market='MIN_BOTH',metric=metric,improvement_mean=float(min(j.mean() for j in joint)),ci_low=float(np.quantile(vals,.025)),ci_high=float(np.quantile(vals,.975)),months=48,nboot=3000,block=6))
 pd.DataFrame(boot).to_csv(OUT/'BLOCK6_BOOTSTRAP.csv',index=False)
 print('\nPRIMARY SUMMARY:\n',summary[summary.period=='MAIN2021_2024'].round(4).to_string(index=False),flush=True)
 return summary

if __name__=='__main__':
 t=time.time();cmd=sys.argv[1] if len(sys.argv)>1 else 'all';
 if cmd in ('prepare','all'):prepare()
 if cmd in ('train','all'):train()
 if cmd in ('evaluate','all'):evaluate()
 print('completed',cmd,'in',round(time.time()-t,1),'s')
