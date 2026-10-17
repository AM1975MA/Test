"""Independent economic audit: all 6 historical V2 replays, repeated BASE parity."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from compact21_return_v1.core import VARIANTS
from paper_ltr_v2.summarize_replay import metrics,checked_leaders,selections,dispersion
def annual(path):
    with np.load(path,allow_pickle=False) as z:
        eq=np.asarray(z["equity"],float).reshape(-1)
        dates=pd.to_datetime(z["dates"])
    ret=np.diff(np.log(np.concatenate([[1.],eq])))
    dateseries=pd.DataFrame(dict(year=dates.year,logret=ret))
    return {str(year):float(np.expm1(g.logret.sum())) for year,g in dateseries.groupby("year")}

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--inputs",required=True);ap.add_argument("--out",required=True);a=ap.parse_args()
    root=Path(a.inputs)
    rows={v:[] for v in ("BASE",*VARIANTS)}
    frames={v:[] for v in rows}
    years={v:{} for v in rows}
    reference_calendar=None
    for i in (1,2,3):
        for variant in VARIANTS:
            path=root/f"v2replay-{variant}-r{i}";obj=json.loads((path/"RESULT.json").read_text())
            if obj.get("status")!="PAPER_LTR_V2_CACHE_REPLAY_COMPLETE" or obj.get("variant")!=variant or obj.get("repeat")!=i:
                raise ValueError("Unverified variant")
            if obj["audit"]["baseline_replay"]["PASS"] is not True or obj["audit"]["input_linkage"]["PASS"] is not True:
                raise ValueError("Baseline parity or raw linkage failure")
            for label,scope,folder in [(variant,"candidate","candidate")]+([("BASE","baseline","baseline_control")] if variant==VARIANTS[0] else []):
                file=path/folder/"FULL_UNIVERSE_PATH.npz"
                result,dates=metrics(file)
                if reference_calendar is None:reference_calendar=dates
                if not reference_calendar.equals(dates):raise ValueError("Daily calendar mismatch")
                expected=obj[scope]["v2_full_universe"]
                if max(abs(result[key]-float(expected[key])) for key in result)>1e-12:
                    raise ValueError(f"Equity recomputation mismatch for {variant} {i}")
                rows[label].append(dict(source=i,**result))
                frames[label].append(checked_leaders(file.parent/"DAILY_LEADERS.csv",dates))
                years[label][str(i)]=annual(file)
    summary={}
    for v in rows:
        s=dispersion(rows[v]);selected=selections(frames[v])
        yearmean={str(year):float(np.mean([years[v][str(i)][str(year)] for i in (1,2,3)]))
                  for year in range(2017,2027)}
        summary[v]=dict(dispersion=s,paths=rows[v],
            leaders=selected,yearly_sources=years[v],yearly_mean=yearmean)
    result=dict(status="COMPACT21_RETURN_ECONOMIC_COMPLETE",
        variants=summary,all_six_replays_complete=True,
        all_three_base_parity_pass=True,independent_metrics_verified=True,
        common_calendar_sessions=len(reference_calendar),historical_only=True,
        source_vintages_correlated=True,production_adoption=False)
    Path(a.out).write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({v:dict(**d["dispersion"],top1_disagreement=d["leaders"]["top1_any_fraction"],
        ret2021=d["yearly_mean"]["2021"],ret2023=d["yearly_mean"]["2023"]) for v,d in summary.items()},indent=2),flush=True)

if __name__=="__main__":main()
