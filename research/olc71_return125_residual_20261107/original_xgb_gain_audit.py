#!/usr/bin/env python3
"""Inspect archived 2021-25 original EU Return125 XGB model usage (not predictive proof)."""
from pathlib import Path
from zipfile import ZipFile
import json,tempfile,os
import pandas as pd,numpy as np,xgboost as xgb
OUT=Path(__file__).resolve().parent/'results'; OUT.mkdir(exist_ok=True)
Z=ZipFile(Path(os.environ.get('OLC71_SOURCE_DIR','/mnt/data/etf_source'))/'OLC08_03_RSI_Confronto_Verificato_20261101.zip')
rows=[];frows=[]
for m in ['EU','USA']:
 for y in range(2019,2027):
  audit=json.loads(Z.read(f'fits/{m}/R_RSI_DOMAIN/{y}/audit.json'))
  features=audit['return_features'];assert len(features)==125
  for seed in [101,202,303]:
   path=f'fits/{m}/R_RSI_DOMAIN/{y}/RETURN_{seed}.ubj'
   if path not in Z.namelist():
    frows.append({'market':m,'year':y,'seed':seed,'found':False})
    continue
   with tempfile.NamedTemporaryFile(suffix='.ubj',delete=False) as tmp:
    tmp.write(Z.read(path));name=tmp.name
   model=xgb.Booster(model_file=name);os.unlink(name)
   imp=model.get_score(importance_type='total_gain')
   total=sum(imp.values());used=sum(imp.get(f'f{i}',0)>0 for i in range(len(features)))
   frows.append({'market':m,'year':y,'seed':seed,'found':True,'n_feature_with_gain':used,'total_gain':total})
   for i,c in enumerate(features):
    gain=imp.get(f'f{i}',0.0)
    rows.append({'market':m,'year':y,'seed':seed,'feature':c,'gain':gain,'share':gain/total if total else np.nan,'group':'PCT' if c.endswith('_pct') else 'DEV' if c.endswith('_dev') else 'RAW'})
pd.DataFrame(rows).to_csv(OUT/'OLC71_ORIGINAL_XGB_GAIN_EU.csv',index=False)
pd.DataFrame(frows).to_csv(OUT/'OLC71_ORIGINAL_XGB_GAIN_COVERAGE.csv',index=False)
if rows:
 d=pd.DataFrame(rows)
 print('SOURCE COVERAGE')
 print(pd.DataFrame(frows).groupby('market').found.agg(['sum','count']))
 print('TOTAL NORMALIZED GAIN BY GROUP 2021-24:')
 print(d[d.year.between(2021,2024)].groupby('group').share.mean().to_string())
 # These shares are per feature, need sum grouped within model first then average.
 g=d[d.year.between(2021,2024)].groupby(['year','seed','group']).share.sum().reset_index()
 print(g.groupby('group').share.agg(['mean','min','max']).to_string())
 x=d[d.year.between(2021,2024)].groupby('feature').share.agg(['mean','std']).sort_values('mean',ascending=False)
 print('TOP',x.head(22).to_string())
 print('used feature avg',pd.DataFrame(frows).query("market=='EU' and year>=2021 and year<=2024").n_feature_with_gain.mean())