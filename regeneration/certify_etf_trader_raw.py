#!/usr/bin/env python3
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
R=Path("etf_trader_raw"); B=Path("regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
u=pd.read_csv(R/"universe.csv"); assert len(u)==149 and u.ticker.nunique()==149
valid=set(u.ticker.str.upper()); issues=[]
for t in sorted(valid):
 x=pd.read_csv(R/f"{t}.csv"); x["date"]=pd.to_datetime(x.date)
 if x.date.duplicated().any(): issues.append([t,"duplicate_date"])
 a=x[["Open","High","Low","Close","Volume"]].to_numpy(float)
 if not np.isfinite(a).all(): issues.append([t,"nonfinite"])
 if (a[:,:4]<=0).any() or (a[:,4]<0).any(): issues.append([t,"invalid"])
 tol=1e-10*np.maximum(1,np.nanmax(np.abs(a[:,:4]),axis=1))
 lo=np.minimum(a[:,0],a[:,3]); hi=np.maximum(a[:,0],a[:,3])
 if np.any(a[:,2]>lo+tol) or np.any(a[:,1]<hi-tol): issues.append([t,"ohlc"])
 if str(x.date.max().date())!="2026-07-01": issues.append([t,"end"])
sha=hashlib.sha256(B.read_bytes()).hexdigest()
m=pd.read_csv(B); missing=sorted(set(m.ticker.str.upper())-valid); sizes=m.groupby("basket").size()
assert sha=="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e",sha
assert m.basket.nunique()==500 and sizes.eq(24).all()
assert not missing,missing
assert not issues,issues[:20]
out={"status":"SOURCE_ONLY_INPUT_GATE_PASS","raw_tickers":149,"baskets":500,"basket_size":24,"basket_sha256":sha,"missing_basket_tickers":[],"ohlcv_validation":"PASS","tolerance":"1e-10 * max(1,max_abs_OHLC_row)","historical_scores_consumed":False,"historical_paths_consumed":False}
Path("certification").mkdir(exist_ok=True);Path("certification/source_only_input_gate.json").write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
