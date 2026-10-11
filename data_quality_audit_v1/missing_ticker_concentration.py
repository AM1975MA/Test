import pandas as pd, numpy as np, ast, json
from pathlib import Path
t=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
ff=next(ast.literal_eval(n.value) for n in t.body if isinstance(n,ast.Assign) and any(isinstance(z,ast.Name) and z.id=="F2D_FEATURES" for z in n.targets))
out=Path("_out");out.mkdir(exist_ok=True)
results=[]
for i in (1,2,3):
 d=pd.read_parquet(f"_panels/alpha_1/repeat_{i}/TI_COMPACT.parquet")
 n=d[ff].notna().sum(axis=1)
 d["incomplete"]=n.ge(30)&n.lt(125)
 d["eligible"]=n.ge(30)
 a=d.groupby("ticker",as_index=False).agg(incomplete_rows=("incomplete","sum"),eligible_rows=("eligible","sum"),total_rows=("ticker","size"),first_date=("signal_date","min"),last_date=("signal_date","max"))
 a=a.sort_values(["incomplete_rows","ticker"],ascending=[False,True])
 a["repeat"]=i;a.to_csv(out/f"BY_TICKER_R{i}.csv",index=False)
 nonzero=a[a.incomplete_rows>0]
 total=int(a.incomplete_rows.sum())
 summary={"repeat":i,"total_incomplete":total,"tickers_affected":len(nonzero),"total_tickers":len(a),
 "top5_rows":int(nonzero.head(5).incomplete_rows.sum()),"top10_rows":int(nonzero.head(10).incomplete_rows.sum()),
 "top20_rows":int(nonzero.head(20).incomplete_rows.sum()),
 "top20":nonzero[["ticker","incomplete_rows","eligible_rows","first_date"]].head(20).astype({"first_date":str}).to_dict("records")}
 results.append(summary)
assert results[0]["total_incomplete"]==1665
print(json.dumps(results,indent=2,default=str))
(out/"RESULT.json").write_text(json.dumps(results,indent=2,default=str))
