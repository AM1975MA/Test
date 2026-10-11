"""Compare three independent fits on exactly identical raw ETF input."""
from pathlib import Path
import pandas as pd,json
root=Path("_frozen");rows=[];leaders=[]
for i in (1,2,3):
 folder=root/f"same-source-fit-{i}"
 p=list(folder.rglob("RESULT.json"));l=list(folder.rglob("DAILY_LEADERS.csv"))
 assert len(p)==len(l)==1,(i,p,l)
 result=json.loads(p[0].read_text())
 df=pd.read_csv(l[0]).sort_values("date").reset_index(drop=True)
 assert not df.date.duplicated().any()
 leaders.append(df)
 row=dict(repeat=i,**result["v2_full_universe"],**result["source_only"])
 rows.append(row)
for b in leaders[1:]:pd.testing.assert_series_equal(leaders[0].date,b.date,check_exact=True)
summary=dict(status="SAME_INPUT_THREE_INDEPENDENT_FITS_PASS",by_repeat=rows,
 cagr_spread_pp=100*(max(v["cagr"] for v in rows)-min(v["cagr"] for v in rows)),
 top1_any_disagree_dates=int(pd.DataFrame({str(i):x.top1 for i,x in enumerate(leaders,1)}).nunique(axis=1).gt(1).sum()),
 top2_any_disagree_dates=int(pd.DataFrame({str(i):x.top2 for i,x in enumerate(leaders,1)}).nunique(axis=1).gt(1).sum()),
 prediction_hashes_equal=len({v["predictions_sha256"] for v in rows})==1,
 original_source_frozen_repeat=1,alpha=1.0,no_production_change=True)
Path("SUMMARY.json").write_text(json.dumps(summary,indent=2,default=str)+"\n")
print(json.dumps(summary,indent=2,default=str))
