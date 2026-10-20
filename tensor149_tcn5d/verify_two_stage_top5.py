"""Independent review of already-frozen two-stage 476-week Top5 study."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from tensor149_tcn5d.compare_xgb125_depth import bootstrap

METHODS=("XGB_D2","XGB_D3","XGB_D4","XGB_D5","XGB_D6","XGB_D7",
         "STAGE3_20_4","STAGE3_20_7","STAGE3_30_7","STAGE2_20_7",
         "BLEND3_4","BLEND3_7")
HYBRIDS=METHODS[6:]

def run(root,out):
    r=Path(root)
    files=list(r.rglob("REPORT.json"))
    if len(files)!=1:raise ValueError(f"Ambiguous results {files}")
    base=files[0].parent
    doc=json.loads(files[0].read_text())
    if doc["status"]!="ORIGINAL149_TWOSTAGE_TOP5_476W_AUDITED_COMPLETE":
        raise ValueError("Missing original completed full model")
    if doc["date_count"]!=476 or doc["score_rows"]!=70924:
        raise ValueError("Original date/ETF contract mismatched")
    w=pd.read_csv(base/"OOS_WEEKLY_SELECTIONS.csv")
    perf=pd.read_csv(base/"PERFORMANCE.csv")
    if len(w)!=476*len(METHODS) or set(w.model)!=set(METHODS):
        raise ValueError("Incomplete dated weekly model comparison")
    ordered={}
    for name in METHODS:
        x=w[w.model==name].sort_values("date").reset_index(drop=True)
        if len(x)!=476 or x.date.nunique()!=476 or not (x.n>=100).all():
            raise ValueError("Missing ETF predictions "+name)
        ordered[name]=x
    base_dates=ordered["XGB_D4"].date.tolist()
    for name in METHODS:
        if ordered[name].date.tolist()!=base_dates:
            raise ValueError("Inconsistent 476 weekly dates "+name)
    reference={"XGB_D3":(0.17477133827323343,-0.4358093576516019,0.06372864423066002),
               "XGB_D4":(0.15572611194601715,-0.4156956339091581,0.059097812183285484)}
    for key,(cagr,maxdd,ric) in reference.items():
        vals=perf.set_index("model").loc[key]
        if max(abs(float(vals[q])-a) for q,a in zip(["cagr","maxdd","rank_ic"],[cagr,maxdd,ric]))>1e-10:
            raise ValueError("Baseline metric drift "+key)
    results=[]
    for name in HYBRIDS:
        new=ordered[name]
        for key in ("XGB_D3","XGB_D4","XGB_D7"):
            old=ordered[key]
            for metric in ("rank_ic","top5_overlap","top5_mean_future_return"):
                delta=(new[metric]-old[metric]).to_numpy(float)
                results.append(dict(model=name,reference=key,measure=metric,
                   mean_delta=float(delta.mean()),block95_low=bootstrap(delta)[0],
                   block95_high=bootstrap(delta)[1]))
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(results).to_csv(out/"HYBRID_VS_FROZEN_SINGLE_95CI.csv",index=False)
    annual=pd.read_csv(base/"ANNUAL_BY_MODEL.csv")
    if not {2017,2018,2019,2020,2021,2022,2023,2024,2025,2026}.issubset(set(annual.year)):
        raise ValueError("Annual years missing")
    annual.to_csv(out/"ANNUAL_RESULTS.csv",index=False)
    perf.to_csv(out/"PERFORMANCE.csv",index=False)
    result=dict(status="TWO_STAGE_TOP5_INDEPENDENT_AUDIT_SUCCESS",
         matched_476_weeks=True,all_12_strategies=True,
         frozen_depth3_depth4_matched=True,only_previous_OOS_scores=True,
         models=perf[["model","cagr","maxdd","sharpe","rank_ic","top5_overlap"]].to_dict("records"),
         paired_vs_depth3={z["model"]:{key:dict(delta=float((ordered[z["model"]][key]-
                 ordered["XGB_D3"][key]).mean()),ci95=bootstrap((ordered[z["model"]][key]-
                 ordered["XGB_D3"][key]).to_numpy(float))) for key in
                 ("rank_ic","top5_overlap","top5_mean_future_return")} for z in
                 perf[perf.model.isin(HYBRIDS)].to_dict("records")},
         warning="Historical 2017-26 already mined; no prospective validation, intervals descriptive.")
    (out/"INDEPENDENT_AUDIT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({k:result[k] for k in ("status","paired_vs_depth3")},indent=2),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args()
    run(x.root,x.out)
