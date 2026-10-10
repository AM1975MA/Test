"""Reconstruct two data-only Compact21 alternatives with byte-preserving non-_dev columns."""
import argparse,ast,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
ALPHAS=(0.05,1.0)
def canon():
 t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 return next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=="F2D_FEATURES" for z in n.targets))
def main():
 a=argparse.ArgumentParser()
 for k in ("r1","r2","r3","out"):a.add_argument("--"+k,required=True)
 z=a.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=False)
 ff=canon();dev=[f for f in ff if f.endswith("_dev")];other=[f for f in ff if f not in dev]
 rows=[];missing=[];masks={}
 for vintage in (1,2,3):
  source=Path(getattr(z,f"r{vintage}"))/"TI_COMPACT.parquet"
  original=pd.read_parquet(source)
  if original.duplicated(["signal_date","ticker"]).any():raise ValueError("Duplicate ticker-date source")
  original["signal_date"]=pd.to_datetime(original.signal_date)
  original=original.sort_values(["signal_date","ticker"]).reset_index(drop=True)
  eligible=np.isfinite(original[ff].to_numpy(float)).sum(axis=1)>=30
  for alpha in ALPHAS:
   d=original.copy(deep=True);changed=0;zero_mad=0
   for f in dev:
    v=original[f[:-4]].astype(float)
    med=v.groupby(original.signal_date).transform("median")
    mad=(v-med).abs().groupby(original.signal_date).transform("median")
    std=v.groupby(original.signal_date).transform(lambda t:t.std(ddof=0))
    scale=np.maximum(1.4826*mad,alpha*std)
    q=(v-med)/scale.replace(0,np.nan)
    # Undefined 0/0 is set to zero ONLY when the full cross-section is identical.
    zero=(scale==0)&std.eq(0)&v.notna()&(v==med)
    q.loc[zero]=0.
    q=q.clip(-8,8)
    if (q.notna()&v.isna()).any():raise ValueError("Fabricated base feature")
    zero_mad+=int((mad.eq(0)&v.notna()).sum())
    changed+=int(((q.notna())&(original[f].notna())&(q!=original[f])).sum())
    d[f]=q
   pd.testing.assert_frame_equal(d[other],original[other],check_exact=True)
   pd.testing.assert_frame_equal(d[["signal_date","ticker"]],original[["signal_date","ticker"]],check_exact=True)
   if not np.isfinite(d[ff].to_numpy(float)[np.isfinite(d[ff].to_numpy(float))]).all():raise ValueError("Nonfinite numerical source")
   allvalid=d[ff].notna().all(axis=1)
   incomplete=eligible&~allvalid
   # Explain all missing cells by base missingness or unresolved transforms.
   fail=d.loc[incomplete,["signal_date","ticker"]].copy()
   fail["missing_count"]=d.loc[incomplete,ff].isna().sum(axis=1).to_numpy()
   fail["repeat"]=vintage;fail["alpha"]=alpha
   missing.append(fail)
   key=(vintage,alpha)
   masks[key]=pd.DataFrame({"date":d.signal_date,"ticker":d.ticker,"complete":allvalid})
   path=out/f"alpha_{alpha:g}"/f"repeat_{vintage}";path.mkdir(parents=True)
   d.to_parquet(path/"TI_COMPACT.parquet",index=False)
   rows.append(dict(repeat=vintage,alpha=alpha,rows=len(d),eligible_30=int(eligible.sum()),
       complete_125=int(allvalid.sum()),eligible_incomplete=int(incomplete.sum()),
       changed_previously_finite_devs=changed,zero_mad_feature_observations=zero_mad,
       non_dev_identical=True,source_file=str(source),candidate_file=str(path/"TI_COMPACT.parquet"),
       sha256=hashlib.sha256((path/"TI_COMPACT.parquet").read_bytes()).hexdigest()))
 for alpha in ALPHAS:
  a=masks[(1,alpha)]
  for i in (2,3):
   b=masks[(i,alpha)]
   pd.testing.assert_frame_equal(a,b,check_exact=True)
 report=dict(status="TWO_ALPHA_PANELS_VERIFIED",source="cleaned-independent-three-source-compact21",
   candidates=rows,missing_rows_each_alpha_repeat=int(len(missing[0])),
   no_training=True,no_production_changes=True,unresolved_causes_require_followup=True)
 pd.concat(missing,ignore_index=True).to_csv(out/"INCOMPLETE_ELIGIBLE_ROWS.csv",index=False)
 pd.DataFrame(rows).to_csv(out/"PANEL_QA.csv",index=False)
 (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
if __name__=="__main__":main()
