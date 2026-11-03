#!/usr/bin/env python3
from pathlib import Path
import zipfile,io,numpy as np,pandas as pd
import argparse
cli=argparse.ArgumentParser()
cli.add_argument('--olc19',type=Path,default=Path(__file__).resolve().parents[1]/'input/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
cli.add_argument('--results',type=Path,default=Path(__file__).resolve().parents[1]/'results')
a=cli.parse_args()
Z=zipfile.ZipFile(a.olc19)
S=np.load(io.BytesIO(Z.read(next(x for x in Z.namelist() if x.endswith('/EU_STATE_HALF.npz')))))
d=pd.DatetimeIndex(S['dates']);t=S['tickers'].astype(str);m=S['observed'];O=S['O'];fs=['EXSA.DE','SXR8.DE','SXRV.DE','QDVE.DE','EXX1.DE','VVSM.DE']
res=[]
for yr in [2021,2022,2023,2024]:
 for tk in fs:
  j=int(np.where(t==tk)[0][0]);valid=(d.year==yr)&m[:,j]&np.isfinite(O[:,j])&(O[:,j]>0)
  i=np.flatnonzero(valid)
  if len(i)<120: continue
  ret=100*(O[i[-1],j]/O[i[0],j]-1)
  res.append({'year':yr,'ticker':tk,'start_open':str(d[i[0]].date()),'end_open':str(d[i[-1]].date()),'year_price_only_pct':float(ret),
              'n_observed_open':len(i),'not_total_return':True})
df=pd.DataFrame(res);df.to_csv(a.results/'EU_FACTOR_ANNUAL_PRICE_DIAGNOSTIC.csv',index=False)
print(df.pivot(index='year',columns='ticker',values='year_price_only_pct').round(2).to_string())
