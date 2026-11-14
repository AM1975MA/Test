"""Build four price-only panels from immutable OLC104/105 and OLC100 archives.
Never imports old scores, selected ticker IDs, V6 states, or fitted models.
Original USA source-observation masks are unavailable: explicitly research-only.
"""
from pathlib import Path
import zipfile,io,json,hashlib
import numpy as np,pandas as pd

EXPECTED={
 "OLC104_CAMPAGNA_COMPLETA_20261114.zip":"ce7e1b4aaa11eda5ea90480e65e31713e0adf22ed1d9df44a9f840211fbc5923",
 "OLC105_TRADEREPUBLIC_TRANSFER_20261114_VERIFICATO.zip":"cd4344da5143c80f65f9aea2d43a5c48fd5e5e076f591dca2e4fbecfcdab9177",
 "OLC100_CAPTURE_RECHECK_20261112.zip":"69c9dedb9013e8fb8bf1df94b07c61f8ecdbb0a94a6e663ff75ba1b3738119df"}
def archive(path):
 h=hashlib.sha256(path.read_bytes()).hexdigest()
 if h!=EXPECTED[path.name]:raise ValueError(("ARCHIVE_HASH",path.name,h))
 return zipfile.ZipFile(path)
def npz(z,n):
 with np.load(io.BytesIO(z.read(n)),allow_pickle=False) as f:return {k:f[k] for k in f.files}
def read_csv(z,n,**kw):return pd.read_csv(io.BytesIO(z.read(n)),**kw)
def verify_bundle(z,prefix,manifest):
 m=json.loads(z.read(prefix+manifest))["files"];n=0
 for path,entry in m.items():
  digest=entry["sha256"] if isinstance(entry,dict) else entry
  if hashlib.sha256(z.read(prefix+path)).hexdigest()!=digest:raise ValueError(("MEMBER_HASH",path))
  n+=1
 return n

def bridge_scale(expected_close,expected_open,captured_close,captured_open):
 ratio=np.asarray(expected_close)/np.asarray(captured_close)
 scale=float(np.median(ratio))
 errors=np.r_[np.asarray(expected_close)/(np.asarray(captured_close)*scale)-1,
              np.asarray(expected_open)/(np.asarray(captured_open)*scale)-1]
 if not np.isfinite(scale) or scale<=0 or not np.isfinite(errors).all() or np.max(np.abs(errors))>1e-5:
  raise ValueError("NONCONSTANT_SOURCE_UNIT_BRIDGE")
 return scale

def build(inputs,out):
 inputs=Path(inputs);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 z4=archive(inputs/"OLC104_CAMPAGNA_COMPLETA_20261114.zip")
 z5=archive(inputs/"OLC105_TRADEREPUBLIC_TRANSFER_20261114_VERIFICATO.zip")
 za=archive(inputs/"OLC100_CAPTURE_RECHECK_20261112.zip")
 verified=verify_bundle(z4,"OLC104_20261114/","MANIFEST_SHA256.json")+verify_bundle(z5,"OLC105/","BUNDLE_MANIFEST_SHA256.json")
 q5=npz(z5,"OLC105/data/WORLD_PASSIVE_STATE.npz");frames={};summary=[]
 qa=read_csv(z5,"OLC105/results/CANDIDATE_SOURCE_QA.csv")
 # Load the frozen, same-ISIN replacement listings already selected before OLC105.
 tr={}
 for rec in qa.to_dict("records"):
  p="OLC105/source_snapshots/"+rec["source"]+"/prices/"+rec["symbol"]+".csv.gz"
  raw=read_csv(z5,p,compression="gzip",parse_dates=["date"]).set_index("date").sort_index()
  if hashlib.sha256(z5.read(p)).hexdigest()!=rec["sha256"]:raise ValueError("RAW_HASH")
  if rec["macro_category"]=="C02_US_SECTOR_THEME":raw=raw.loc["2016-05-03":]
  factor=raw["Adj Close"]/raw["Close"]
  o=raw["Open"]*factor;c=raw["Adj Close"].copy()
  if rec["isin"]=="IE00B3YCGJ38":
   before=c.loc[:"2025-12-12"].iloc[-1];after=c.loc["2025-12-15"]
   if not .008<after/before<.012:raise ValueError("P500_REPAIR_NOT_APPLICABLE")
   o.loc["2025-12-15":]*=100;c.loc["2025-12-15":]*=100
  good=np.isfinite(raw[["Open","High","Low","Close"]]).all(axis=1)&(raw[["Open","High","Low","Close"]]>0).all(axis=1)
  tr[rec["isin"]]=pd.DataFrame({"O":o.where(good),"C":c.where(good),"observed":good}).loc["2019-02-01":"2026-11-12"]
  summary.append(dict(universe="TR29",id=rec["isin"],ticker=rec["symbol"],observed_mask="source_valid_OHLC",source=rec["source"],geometry_bad=int(rec["geometry_bad"])))
 assert len(tr)==29
 # Confirm corrected candidate values reproduce the stored OLC105 economic series.
 max_diff=0.
 for name,f in tr.items():
  j=list(q5["tickers"]).index(name);dates=pd.DatetimeIndex(q5["dates"])
  common=f.index.intersection(dates)
  ii=dates.get_indexer(common);vv=f.loc[common]
  mask=vv.observed.to_numpy(bool)&q5["observed"][ii,j]
  for field in ["O","C"]:
   a=vv[field].to_numpy()[mask];b=q5[field][ii,j][mask]
   max_diff=max(max_diff,float(np.max(np.abs(a-b)/np.maximum(1,np.abs(b)))) if len(a) else 0.)
 if max_diff>1e-9:raise ValueError(("CANDIDATE_PARITY",max_diff))
 groups={}
 anchor_error={}
 for market in ["EU","USA"]:
  q=npz(z4,"OLC104_20261114/data/"+("EU165" if market=="EU" else "USA149")+"_ORIGINAL_STATE.npz")
  dates=pd.DatetimeIndex(q["dates"]);d={}
  for j,name in enumerate(q["tickers"]):
   if str(name).startswith("EUR_CASH"):continue
   seen=q["observed"][:,j] if "observed" in q else np.isfinite(q["O"][:,j])&np.isfinite(q["C"][:,j])
   f=pd.DataFrame({"O":np.where(seen,q["O"][:,j],np.nan),"C":np.where(seen,q["C"][:,j],np.nan),"observed":seen},index=dates)
   if market=="EU":
    l=list(q5["tickers"]).index(name);keep=pd.DatetimeIndex(q5["dates"])>dates[-1]
    dd=pd.DatetimeIndex(q5["dates"])[keep];ss=q5["observed"][keep,l]
    a=pd.DataFrame({"O":np.where(ss,q5["O"][keep,l],np.nan),"C":np.where(ss,q5["C"][keep,l],np.nan),"observed":ss},index=dd)
   else:
    a=read_csv(za,"quotes/USA_"+str(name)+".csv",parse_dates=["date"]).set_index("date")
    old=read_csv(za,"overlap/USA_"+str(name)+".csv",parse_dates=["date"]).set_index("date")
    common=old.index.intersection(dates);ii=dates.get_indexer(common)
    scale=bridge_scale(q["C"][ii,j],q["O"][ii,j],old.loc[common,"adj_close"].to_numpy(),old.loc[common,"adj_open"].to_numpy())
    err=float(np.max(np.abs(old.loc[common,"adj_close"].to_numpy()*scale/q["C"][ii,j]-1)))
    anchor_error[str(name)]=err
    a=pd.DataFrame({"O":a.adj_open*scale,"C":a.adj_close*scale,"observed":np.isfinite(a.adj_open)&np.isfinite(a.adj_close)&(a.adj_open>0)&(a.adj_close>0)},index=a.index)
   f=pd.concat([f,a]).loc["2019-02-01":"2026-11-12"]
   if f.index.has_duplicates:raise ValueError(("DUP_DATE",name))
   d[str(name)]=f
   summary.append(dict(universe=market+"165" if market=="EU" else "USA149",id=str(name),ticker=str(name),observed_mask="original_EU_observed" if market=="EU" else "UNKNOWN_original_USA_assumed_finite",source="OLC104_plus_audited_append",geometry_bad=None))
  groups["EU165" if market=="EU" else "USA149"]=d
 groups["TR29"]=tr;groups["EU194"]={**groups["EU165"],**tr}
 benchmarks={"EU165":"EUNL.DE","USA149":"ACWI","TR29":"IE00BFY0GT14","EU194":"IE00BFY0GT14"}
 metadata={}
 for key,series in groups.items():
  names=sorted(series);dates=pd.DatetimeIndex(sorted(set().union(*(set(f.index) for f in series.values()))))
  O=pd.DataFrame({n:series[n].O for n in names}).reindex(dates).to_numpy()
  C=pd.DataFrame({n:series[n].C for n in names}).reindex(dates).to_numpy()
  seen=pd.DataFrame({n:series[n].observed for n in names}).reindex(dates).fillna(False).to_numpy(bool)
  seen&=np.isfinite(C)&(C>0)&np.isfinite(O)&(O>0)
  O=np.where(seen,O,np.nan);C=np.where(seen,C,np.nan)
  np.savez_compressed(out/(key+".npz"),dates=dates.values,names=np.array(names),O=O,C=C,observed=seen,benchmark=np.array(names.index(benchmarks[key])))
  metadata[key]=dict(instruments=len(names),start=str(dates[0].date()),end=str(dates[-1].date()),benchmark=benchmarks[key],
   currency="USD" if key=="USA149" else "EUR",traderepublic_verified="public_catalogue_only" if key=="TR29" else "NOT_CERTIFIED",missing_open=int((~seen).sum()))
 pd.DataFrame(summary).to_csv(out/"SOURCE_INSTRUMENTS.csv",index=False)
 result=dict(status="PRICE_PANEL_RECONSTRUCTION_PASS_NOT_BROKER_CERTIFIED",verified_bundle_members=verified,
  max_candidate_parity_relative=max_diff,USA_append_max_overlap_error=max(anchor_error.values()),universes=metadata,
  warnings=["USA original source-observation mask unavailable","Adjusted economic units, not physical shares","Not full PIT universe/survivorship verified","Open and Close proxy quotes; not Trade Republic execution","Geometric OHLC anomalies remain; no intraday stops used","US performance in USD, not converted to EUR"])
 (out/"INPUT_QA.json").write_text(json.dumps(result,indent=2)+"\n")
 return result
if __name__=="__main__":
 import argparse
 a=argparse.ArgumentParser();a.add_argument("--inputs",required=True);a.add_argument("--out",required=True)
 x=a.parse_args();print(json.dumps(build(x.inputs,x.out),indent=2))
