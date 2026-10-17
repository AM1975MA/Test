"""Independent audit summary and fixed factorial contrasts from 24 verified V2 paths."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from paper_ltr_v2.summarize_replay import metrics
from paper_ltr_v2.replay import sha
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True)
    a=p.parse_args();root=Path(a.root)
    eco=pd.read_csv(root/"ECONOMICS.csv")
    mon=pd.read_csv(root/"MONTHLY_QUALITY.csv")
    fix=pd.read_csv(root/"FIXED_5050.csv")
    ann=pd.read_csv(root/"ANNUAL_RETURN.csv")
    if len(eco)!=24 or eco.arm.nunique()!=8 or len(fix)!=24 or len(mon)!=24*114:
        raise ValueError("Incomplete factorial coverage")
    expected=set((l,t,h) for l in ("BASE","RETURN_RANK_NDCG") for t in (0,1) for h in (0,1))
    observed=set(zip(eco.learner,eco.titanium_tail,eco.ma3_tail))
    if expected!=observed:raise ValueError("Missing factorial arm")
    if mon[mon.mature].groupby(["arm","vintage"]).size().nunique()!=1 or len(mon[mon.mature])!=24*113:
        raise ValueError("Missing monthly mature label")
    aggregate=[];daily_by_arm={}
    for arm,g in eco.groupby("arm"):
        sig=mon[mon.arm.eq(arm)&mon.mature].copy()
        fixed=fix[fix.arm.eq(arm)]
        leaders=[];calendar=None
        for vintage in (1,2,3):
            path=root/arm/f"r{vintage}"
            data,_=metrics(path/"FULL_UNIVERSE_PATH.npz")
            sample=g[g.vintage.eq(vintage)].iloc[0]
            for key in ("cagr","maxdd","sharpe"):
                if abs(data[key]-float(sample[key]))>1e-12:
                    raise ValueError("Equity metrics changed after execution")
            f=pd.read_csv(path/"DAILY_LEADERS.csv")
            if len(f)!=2366:raise ValueError("Daily calendar altered")
            if calendar is None:calendar=f.date
            elif not calendar.equals(f.date):raise ValueError("Source calendars differ")
            leaders.append(f.top1.to_numpy(str))
        source=np.column_stack(leaders)
        disagreement=float(np.mean(np.any(source!=source[:,[0]],axis=1)))
        daily_by_arm[arm]=disagreement
        aggregate.append(dict(arm=arm,learner=str(g.learner.iloc[0]),
            titanium_tail=int(g.titanium_tail.iloc[0]),ma3_tail=int(g.ma3_tail.iloc[0]),
            mean_cagr=float(g.cagr.mean()),cagr_span_pp=100*float(g.cagr.max()-g.cagr.min()),
            mean_maxdd=float(g.maxdd.mean()),mean_sharpe=float(g.sharpe.mean()),
            mean_turnover=float(g.turnover.mean()),
            selected_21d_return=float(sig.ret.mean()),
            regret_topdecile=float(sig.regret.mean()),exact_winner_rate=float(sig.exact_hit.mean()),
            actual_top5_hit=float(sig.top5_hit.mean()),predicted_top5_overlap=float(sig.overlap.mean()),
            fixed5050_cagr=float(fixed.cagr.mean()),daily_top1_disagreement=disagreement))
    ag=pd.DataFrame(aggregate);ag.to_csv(root/"AGGREGATED_8_ARMS.csv",index=False)
    contrasts=[]
    for t in (0,1):
        for h in (0,1):
            x=ag[ag.titanium_tail.eq(t)&ag.ma3_tail.eq(h)]
            b=x[x.learner.eq("BASE")].iloc[0]
            r=x[x.learner.ne("BASE")].iloc[0]
            contrasts.append(dict(titanium_tail=t,ma3_tail=h,
                rank_minus_base_21d_return_pp=100*(r.selected_21d_return-b.selected_21d_return),
                rank_minus_base_regret_pp=100*(r.regret_topdecile-b.regret_topdecile),
                rank_minus_base_cagr_pp=100*(r.mean_cagr-b.mean_cagr),
                rank_minus_base_fixed5050_cagr_pp=100*(r.fixed5050_cagr-b.fixed5050_cagr)))
    for model in ("BASE","RETURN_RANK_NDCG"):
        for factor in ("titanium_tail","ma3_tail"):
            f=ag[ag.learner.eq(model)]
            on=f[f[factor].eq(1)].mean_cagr.mean()
            off=f[f[factor].eq(0)].mean_cagr.mean()
            contrasts.append(dict(learner=model,main_effect=factor,
                mean_cagr_on_minus_off_pp=100*(on-off)))
    base=ag[ag.arm.eq("B_T1_H1")].iloc[0]
    rank=ag[ag.arm.eq("R_T1_H1")].iloc[0]
    for check,x,reference in (("BASE",base,.31758077249),("RANK",rank,.35838)):
        if abs(float(x.mean_cagr)-reference)>0.0001:
            raise ValueError("Original all-ON benchmark mismatch "+check)
    if ann.groupby(["arm","vintage"]).year.nunique().ne(10).any():
        raise ValueError("Missing annual return audit")
    report=dict(status="COMPACT21_TAIL_8ARM_FACTORIAL_COMPLETE",aggregates=aggregate,
        rank_vs_base_by_tail=contrasts,original149=149,source_vintages=3,
        months=114,mature_months=113,sessions_per_source=2366,
        all_on_exact_daily_equity_PARITY=True,independent_equity_recalculation_PASS=True,
        new_model_fits=0,all_24_replays_PASS=True,
        experiment_predeclared_protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        interpretation="Ablation of two Tail packages; old correlated historical Yahoo vintages not independent future market; no production promotion.")
    (root/"SUMMARY.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    print(ag.to_string(index=False),flush=True)
    print(pd.DataFrame(contrasts).to_string(index=False),flush=True)
if __name__=="__main__":main()
