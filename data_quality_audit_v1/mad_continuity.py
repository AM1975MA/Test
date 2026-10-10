"""Check numerical discontinuity and tiny MAD on frozen independent Compact21 feature panels."""
import argparse,ast,json
from pathlib import Path
import numpy as np,pandas as pd

def main():
 p=argparse.ArgumentParser()
 for a in ("r1","r2","r3","out"):p.add_argument("--"+a,required=True)
 args=p.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
 tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 features=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=="F2D_FEATURES" for z in n.targets))
 ds=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(args,f"r{i}"))/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date)
  d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  ds.append(d)
 for d in ds[1:]:pd.testing.assert_frame_equal(d[["signal_date","ticker"]],ds[0][["signal_date","ticker"]])
 names=[f for f in features if f.endswith("_dev")]
 audits=[];cases={}
 for i,d in enumerate(ds,1):
  eligible=np.isfinite(d[features].to_numpy(dtype=float)).sum(axis=1)>=30
  for f in names:
   x=d[f[:-4]].astype(float);g=x.groupby(d.signal_date)
   med=g.transform("median");mad=(x-med).abs().groupby(d.signal_date).transform("median")
   std=g.transform(lambda z:z.std(ddof=0))
   scale=1.4826*mad
   iszero=eligible&x.notna()&mad.eq(0)
   positive=eligible&x.notna()&mad.gt(0)
   raw_robust=(x-med)/scale.replace(0,np.nan)
   proposed=np.where(mad.eq(0),std,scale)
   candidate=((x-med)/pd.Series(proposed,index=d.index).replace(0,np.nan)).clip(-8,8)
   ratio=scale/std.replace(0,np.nan)
   for threshold in (1e-12,1e-8,1e-4,1e-2,.1):
    near=positive&ratio.le(threshold)
    audits.append(dict(repeat=i,feature=f,threshold=threshold,zero_mad=int(iszero.sum()),
       near_positive=int(near.sum()),near_sat8=int((near & raw_robust.abs().ge(8)).sum()),
       near_max_abs=float(candidate[near].abs().max()) if near.any() else None,
       near_scaled_mad_over_std_min=float(ratio[near].min()) if near.any() else None))
   cases[(i,f)]=dict(zero=iszero.to_numpy(),positive=positive.to_numpy(),values=candidate.to_numpy(),
       ratio=ratio.to_numpy(),std=std.to_numpy())
 pairs=[]
 for f in names:
  for i,j in ((1,2),(1,3),(2,3)):
   a=cases[(i,f)];b=cases[(j,f)]
   exact=a["zero"]&b["zero"]
   transition=(a["zero"]&b["positive"]) | (a["positive"]&b["zero"])
   for kind,mask in (("zero_both",exact),("zero_positive_flip",transition)):
    ok=mask&np.isfinite(a["values"])&np.isfinite(b["values"])
    dif=np.abs(a["values"][ok]-b["values"][ok])
    pairs.append(dict(feature=f,pair=f"{i}-{j}",kind=kind,observations=len(dif),
      p95_abs_diff=float(np.quantile(dif,.95)) if len(dif) else None,
      max_abs_diff=float(dif.max()) if len(dif) else None,
      diff_gt_0_1=int((dif>.1).sum()),diff_gt_1=int((dif>1).sum())))
 a=pd.DataFrame(audits);b=pd.DataFrame(pairs)
 a.to_csv(out/"NEAR_ZERO_MAD.csv",index=False);b.to_csv(out/"ZERO_TO_POSITIVE_TRANSITIONS.csv",index=False)
 report={"status":"MAD_CONTINUITY_CENSUS_FINISHED",
  "near_positive_by_threshold":a.groupby(["repeat","threshold"])[["near_positive","near_sat8"]].sum().reset_index().to_dict("records"),
  "transitions":b.groupby("kind")[["observations","diff_gt_0_1","diff_gt_1"]].sum().reset_index().to_dict("records"),
  "max_transition_abs_diff":float(b.loc[b.kind.eq("zero_positive_flip"),"max_abs_diff"].max()) if b.kind.eq("zero_positive_flip").any() else None,
  "no_model_training":True,"no_approved_repair":True}
 (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
 print(json.dumps(report,indent=2,allow_nan=False))
if __name__=="__main__":main()
