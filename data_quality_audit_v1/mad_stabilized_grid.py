"""Prereigstered data-only robust deviation denominator grid. No model fitting."""
import argparse,ast,json
from pathlib import Path
import numpy as np,pandas as pd
ALPHAS=(0.05,0.1,0.25,0.5,1.0)
def main():
 ap=argparse.ArgumentParser()
 for s in ("r1","r2","r3","out"):ap.add_argument("--"+s,required=True)
 a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 features=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="F2D_FEATURES" for t in n.targets))
 devs=[f for f in features if f.endswith("_dev")]
 panels=[]
 for i in (1,2,3):
  d=pd.read_parquet(Path(getattr(a,f"r{i}"))/"TI_COMPACT.parquet")
  d.signal_date=pd.to_datetime(d.signal_date);d=d.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  panels.append(d)
 for d in panels[1:]:pd.testing.assert_frame_equal(d[["signal_date","ticker"]],panels[0][["signal_date","ticker"]])
 policies=[f"max_{x:g}" for x in ALPHAS]+["std_only"]
 outputs={};audit=[]
 for i,d in enumerate(panels,1):
  original=d[features].to_numpy(float)
  eligible=np.isfinite(original).sum(axis=1)>=30
  bases={};base_nonmissing={}
  for feat in devs:
   x=d[feat[:-4]].astype(float);g=x.groupby(d.signal_date)
   med=g.transform("median")
   mad=(x-med).abs().groupby(d.signal_date).transform("median")
   sd=g.transform(lambda z:z.std(ddof=0))
   bases[feat]=(x-med,1.4826*mad,sd)
   base_nonmissing[feat]=x.notna().to_numpy()
  for policy in policies:
   arr=original.copy()
   altered=0;saturations=0;missing_cause=0
   for feat in devs:
    ix=features.index(feat);numer,madscale,sd=bases[feat]
    scale=sd if policy=="std_only" else np.maximum(madscale,float(policy.split("_")[1])*sd)
    y=(numer/scale.replace(0,np.nan)).clip(-8,8).to_numpy(float)
    # A completely tied cross-section has numerator 0 and scale 0; assign neutral 0 only where proven all tied.
    full_tie=np.isfinite(numer.to_numpy(float))&(numer.to_numpy(float)==0)&(scale.to_numpy(float)==0)&(sd.to_numpy(float)==0)
    y[full_tie]=0.
    # strict causality: missing original base -> missing transformed feature.
    y[~base_nonmissing[feat]]=np.nan
    curr=arr[:,ix]
    altered+=int(np.count_nonzero(np.isfinite(y)&np.isfinite(curr)&(y!=curr)))
    saturations+=int(np.count_nonzero(np.isfinite(y)&(np.abs(y)>=8)))
    arr[:,ix]=y
   n=np.isfinite(arr).sum(axis=1)
   outmask=(n>=30)&(n==125)
   audit.append(dict(repeat=i,policy=policy,rows=len(d),original_eligible=int(eligible.sum()),
     complete_all=int((n==125).sum()),complete_among_original_eligible=int((eligible&(n==125)).sum()),
     newly_complete_vs_original=int((eligible&(n==125)&~np.isfinite(original).all(axis=1)).sum()),
     remaining_missing_eligible=int((eligible&(n<125)).sum()),changed_finite_dev_cells=altered,
     saturated_dev_cells=saturations))
   outputs[(i,policy)]=arr[:,[features.index(f) for f in devs]]
 comparisons=[]
 for policy in policies:
  for j,k in ((1,2),(1,3),(2,3)):
   aa=outputs[(j,policy)];bb=outputs[(k,policy)]
   mask=np.isfinite(aa)&np.isfinite(bb)
   delta=np.abs(aa-bb)
   differences=delta[mask]
   comparisons.append(dict(policy=policy,pair=f"{j}-{k}",both_finite=int(mask.sum()),
      max_abs_diff=float(differences.max()) if len(differences) else None,
      p99_abs_diff=float(np.quantile(differences,.99)) if len(differences) else None,
      changed_gt_0_1=int(np.count_nonzero(differences>.1))))
 # Synthetic continuity test: perturb a tied majority by epsilon, compare candidate output as epsilon -> 0.
 # For alpha>0, denominator floor remains positive whenever distribution includes an off-median observation.
 synthetic=[]
 for policy in policies:
  base=np.array([0.]*8+[2.,3.])
  vals=[]
  for eps in (0,1e-12,1e-9,1e-6):
   x=base.copy()
   if eps:x[:4]=eps
   med=np.median(x);mad=np.median(np.abs(x-med));sd=x.std(ddof=0)
   scale=sd if policy=="std_only" else max(1.4826*mad,float(policy.split("_")[1])*sd)
   vals.append(np.clip((x-med)/scale,-8,8))
  synthetic.append(dict(policy=policy,max_perturbation_impact=float(max(np.max(np.abs(vals[t]-vals[0])) for t in (1,2,3))),
    finite_all=bool(all(np.isfinite(v).all() for v in vals))))
 pd.DataFrame(audit).to_csv(out/"POLICY_COVERAGE.csv",index=False)
 pd.DataFrame(comparisons).to_csv(out/"POLICY_THREE_SOURCE_DRIFT.csv",index=False)
 pd.DataFrame(synthetic).to_csv(out/"SYNTHETIC_CONTINUITY.csv",index=False)
 summary=dict(status="STABILIZED_GRID_DATA_ONLY_COMPLETE",alphas=ALPHAS,policies=policies,
  coverage=audit,drift=comparisons,synthetic=synthetic,
  model_trained=False,production_changed=False,research_only=True)
 (out/"RESULT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
 for r in audit:print("COVERAGE",r)
 for r in comparisons:print("DRIFT",r)
 for r in synthetic:print("SYNTHETIC",r)
if __name__=="__main__":main()
