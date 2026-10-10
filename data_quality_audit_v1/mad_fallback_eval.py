"""Data-only stability census for alternatives at zero cross-sectional MAD."""
import argparse,ast,json
from pathlib import Path
import numpy as np
import pandas as pd
def feats():
 tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=="F2D_FEATURES" for z in n.targets))
def main():
 p=argparse.ArgumentParser()
 for n in ("r1","r2","r3","out"):p.add_argument("--"+n,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 ff=feats();ds=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date)
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  if d.duplicated(["signal_date","ticker"]).any():raise ValueError("duplicate")
  ds.append(d)
 for d in ds[1:]:pd.testing.assert_frame_equal(d[["signal_date","ticker"]],ds[0][["signal_date","ticker"]])
 records=[];pair_records=[]
 candidates={}
 for i,d in enumerate(ds,1):
  eligible=d[ff].notna().sum(axis=1)>=30
  for feature in [f for f in ff if f.endswith("_dev")]:
   base=feature[:-4];v=d[base].astype(float)
   g=v.groupby(d.signal_date)
   med=g.transform("median");mad=(v-med).abs().groupby(d.signal_date).transform("median")
   q25=g.transform(lambda z:z.quantile(.25));q75=g.transform(lambda z:z.quantile(.75))
   iqr=q75-q25;sd=g.transform(lambda z:z.std(ddof=0))
   mask=eligible&v.notna()&mad.eq(0)&d[feature].isna()
   # Compute alternatives only where canonical formula was undefined; never overwrite source.
   # Normal-consistent scaled IQR and Std are diagnostically distinct.
   iqrscale=iqr/1.349
   safe_iqr=mask&iqrscale.gt(0)
   safe_std=mask&sd.gt(0)
   fallback_iqr=((v-med)/iqrscale.replace(0,np.nan)).clip(-8,8)
   fallback_sd=((v-med)/sd.replace(0,np.nan)).clip(-8,8)
   candidates[(i,feature)]=dict(mask=mask.to_numpy(),iqr=fallback_iqr.to_numpy(),sd=fallback_sd.to_numpy(),
                               std_positive=safe_std.to_numpy(),iqr_positive=safe_iqr.to_numpy())
   records.append(dict(repeat=i,feature=feature,zero_mad=int(mask.sum()),
      iqr_positive=int(safe_iqr.sum()),std_positive=int(safe_std.sum()),
      neither_scale_positive=int((mask&~safe_iqr&~safe_std).sum()),
      zero_mad_off_median=int((mask&(v!=med)).sum()),
      std_fallback_abs_p95=float(fallback_sd[safe_std].abs().quantile(.95)) if safe_std.any() else None,
      iqr_fallback_abs_p95=float(fallback_iqr[safe_iqr].abs().quantile(.95)) if safe_iqr.any() else None))
 for f in [f for f in ff if f.endswith("_dev")]:
  for i,j in ((1,2),(1,3),(2,3)):
   u=candidates[(i,f)];v=candidates[(j,f)]
   for policy in ("iqr","sd"):
    common=u["mask"]&v["mask"]&np.isfinite(u[policy])&np.isfinite(v[policy])
    delta=np.abs(u[policy][common]-v[policy][common])
    pair_records.append(dict(feature=f,pair=f"{i}-{j}",policy=policy,common=len(delta),
      max_abs_delta=float(delta.max()) if len(delta) else None,
      median_abs_delta=float(np.median(delta)) if len(delta) else None,
      p95_abs_delta=float(np.quantile(delta,.95)) if len(delta) else None,
      n_delta_gt_0_1=int((delta>.1).sum())))
 pd.DataFrame(records).to_csv(out/"FALLBACK_SCALE_COVERAGE.csv",index=False)
 pd.DataFrame(pair_records).to_csv(out/"FALLBACK_THREE_VINTAGE_DRIFT.csv",index=False)
 z=pd.DataFrame(records);p=pd.DataFrame(pair_records)
 report=dict(status="MAD_FALLBACK_DIAGNOSTIC_COMPLETE",
  per_vintage=z.groupby("repeat")[["zero_mad","iqr_positive","std_positive","neither_scale_positive","zero_mad_off_median"]].sum().reset_index().to_dict("records"),
  by_policy=p.groupby("policy").agg(max_abs_delta=("max_abs_delta","max"),cases_delta_gt_0_1=("n_delta_gt_0_1","sum")).reset_index().to_dict("records"),
  model_trained=False,source_changed=False,proposed_repair_adopted=False)
 (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
