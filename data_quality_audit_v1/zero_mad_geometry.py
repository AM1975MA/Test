"""Inspect whether zero-MAD raw observations coincide with cross-sectional median."""
import argparse,ast,json
from pathlib import Path
import pandas as pd
import numpy as np
def run(args):
  tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
  ff=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="F2D_FEATURES" for x in n.targets))
  out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
  rows=[]; dates=[]
  for i in (1,2,3):
    df=pd.read_parquet(Path(getattr(args,f"r{i}"))/"TI_COMPACT.parquet")
    df.signal_date=pd.to_datetime(df.signal_date)
    eligible=df[ff].notna().sum(axis=1)>=30
    for name in [x for x in ff if x.endswith("_dev")]:
      base=name[:-4];v=df[base]
      med=v.groupby(df.signal_date).transform("median")
      mad=(v-med).abs().groupby(df.signal_date).transform("median")
      ix=eligible&v.notna()&mad.eq(0)&df[name].isna()
      eq=(v==med)&ix
      other=ix&~eq
      rows.append(dict(repeat=i,feature=name,zero_mad=int(ix.sum()),
        all_values_equal_to_median=int(eq.sum()),off_median=int(other.sum())))
      for idx in df.index[other]:
        dates.append(dict(repeat=i,feature=name,ticker=df.at[idx,"ticker"],
          signal_date=str(df.at[idx,"signal_date"].date()),
          raw_value=float(v.at[idx]),median=float(med.at[idx])))
  z=pd.DataFrame(rows)
  z.to_csv(out/"ZERO_MAD_DISTRIBUTION.csv",index=False)
  pd.DataFrame(dates,columns=["repeat","feature","ticker","signal_date","raw_value","median"]).to_csv(out/"OFF_MEDIAN_CASES.csv",index=False)
  report=dict(status="ZERO_MAD_VALUE_GEOMETRY_COMPLETE",by_vintage=z.groupby("repeat")[["zero_mad","all_values_equal_to_median","off_median"]].sum().reset_index().to_dict("records"),
    production_changes=False,training=False)
  (out/"RESULT.json").write_text(json.dumps(report,indent=2)+"\n")
  print(json.dumps(report,indent=2))
if __name__=="__main__":
 p=argparse.ArgumentParser()
 for x in ("r1","r2","r3","out"):p.add_argument("--"+x,required=True)
 run(p.parse_args())
