"""Analyze six frozen V2 leader outputs. No retraining and no PnL attribution claims."""
import argparse,json
from pathlib import Path
import pandas as pd
def main():
 p=argparse.ArgumentParser();p.add_argument("--root",required=True);p.add_argument("--out",required=True)
 z=p.parse_args();root=Path(z.root);out=Path(z.out);out.mkdir(parents=True,exist_ok=False)
 allframes=[];spec=[]
 for alpha in ("0.05","1.0"):
  for repeat in (1,2,3):
   folder=root/f"v2-alpha-{alpha}-repeat-{repeat}"
   matches=list(folder.rglob("DAILY_LEADERS.csv"))
   if len(matches)!=1:raise ValueError(f"Expected exactly one leaders table in {folder}: {matches}")
   d=pd.read_csv(matches[0]); d["alpha"]=alpha;d["repeat"]=repeat
   spec.append(dict(alpha=alpha,repeat=repeat,rows=len(d),columns=list(d.columns)))
   allframes.append(d)
 (out/"SCHEMA.json").write_text(json.dumps(spec,indent=2)+"\n")
 for alpha in ("0.05","1.0"):
  source=[d for d in allframes if d.alpha.iloc[0]==alpha]
  cols=set(source[0].columns)
  datecol=next((c for c in ("signal_date","date","entry_date","session_date") if c in cols),None)
  winners=[c for c in source[0].columns if ("top1" in c.lower() or "leader" in c.lower() or "ticker" in c.lower()) and c not in ("alpha","repeat")]
  if not datecol or not winners:raise ValueError(f"Unrecognized DAILY_LEADERS schema: {list(cols)}")
  for d in source:
   if d[datecol].duplicated().any():raise ValueError(f"Duplicated decision date in {alpha}")
  joined=source[0].set_index(datecol)
  for d in source[1:]:
   joined=joined.join(d.set_index(datecol),rsuffix="_"+str(int(d.repeat.iloc[0])),how="outer")
  if joined.isna().all(axis=1).any():raise ValueError("Unmatched rows")
  primary=winners[0]
  variants=[primary,primary+"_2",primary+"_3"]
  if any(v not in joined for v in variants):raise ValueError(f"Primary key mismatch: {variants}")
  complete=joined[variants].notna().all(axis=1)
  if not complete.all():raise ValueError("Source calendar mismatch")
  disagree=joined[variants].nunique(axis=1)>1
  summary=dict(alpha=alpha,date_column=datecol,primary_leader_column=primary,
    date_count=len(joined),disagreement_dates=int(disagree.sum()),
    agreement_dates=int((~disagree).sum()),disagreement_fraction=float(disagree.mean()),
    source_columns=sorted(cols))
  joined.reset_index().to_csv(out/f"JOINED_LEADERS_ALPHA_{alpha}.csv",index=False)
  joined.loc[disagree].reset_index().to_csv(out/f"DISAGREEMENT_DATES_ALPHA_{alpha}.csv",index=False)
  # Pairwise comparisons and joint top1/top2 disagreements, not PnL attribution.
  pair_stats=[]
  for field in ("top1","top2"):
   if field not in joined:continue
   triplet=[field,field+"_2",field+"_3"]
   if any(c not in joined for c in triplet):continue
   discord=joined[triplet].nunique(axis=1)>1
   summary[field+"_disagreement_days"]=int(discord.sum())
   for x,y in ((0,1),(0,2),(1,2)):
    changed=joined[triplet[x]].ne(joined[triplet[y]])
    pair_stats.append(dict(alpha=alpha,field=field,comparison=f"{x+1}-{y+1}",
      differences=int(changed.sum()),days=len(joined),fraction=float(changed.mean())))
  pd.DataFrame(pair_stats).to_csv(out/f"PAIRWISE_ALPHA_{alpha}.csv",index=False)
  # Record dates with both independent repeat 1 vs 2 and 1 vs 3 disagreement for diagnosis.
  disagreement_details=joined.loc[disagree,[c for c in joined.columns if c.startswith("top")]].copy()
  disagreement_details.index.name=datecol
  disagreement_details.reset_index().to_csv(out/f"LEADER_DISAGREEMENT_COMPACT_ALPHA_{alpha}.csv",index=False)
  print("LEADER_DIAGNOSIS",json.dumps(summary))
  (out/f"SUMMARY_ALPHA_{alpha}.json").write_text(json.dumps(summary,indent=2)+"\n")
 print("SCHEMA",json.dumps(spec,indent=2))
if __name__=="__main__":main()
