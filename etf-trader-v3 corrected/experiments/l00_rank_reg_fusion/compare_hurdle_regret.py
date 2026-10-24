#!/usr/bin/env python3
"""Fixed-metric audit comparing original V3 meta selector to 4x2 utility trials.

The evaluation code does NOT select the best variant or alter production;
reports every preregistered candidate with original calendar month paired
six-month block bootstrap. Adverse regimes are excluded only diagnostically.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

FAMILIES=("DT14","DT_REGIME","HGB_REGIME","RF_REGIME")
METRICS=("basket_top1","basket_top3","basket_ndcg3","basket_regret",
         "basket_selected_excess","basket_loss10_top1")
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--research",required=True)
    ap.add_argument("--incumbent",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    r=Path(a.research);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    base=pd.read_csv(Path(a.incumbent)/"NESTED_MONTHLY.csv",parse_dates=["signal_date"])
    base=base[base.strategy.eq("NESTED_24_TOP1_GUARD")].sort_values("signal_date").reset_index(drop=True)
    assert len(base)==101 and base.signal_date.nunique()==101
    rows=[];events=[];original=None
    for fam in FAMILIES:
        folder=r/fam
        m=pd.read_csv(folder/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
        assert len(m)==303,(fam,len(m))
        m=m.sort_values(["variant","signal_date"]).reset_index(drop=True)
        b=m[m.variant.eq("CORRECTED")].sort_values("signal_date").reset_index(drop=True)
        assert b.signal_date.equals(base.signal_date)
        if original is None:original=b
        else:np.testing.assert_allclose(original[list(METRICS)],b[list(METRICS)],atol=1e-12,rtol=0)
        c=pd.read_csv(folder/"CORRECTIONS.csv",parse_dates=["signal_date"])
        unique=pd.read_csv(folder/"UNIQUE_PAIR_EVENTS.csv",parse_dates=["signal_date"])
        events.append(unique.assign(family=fam))
        for arm in sorted(set(m.variant)-{"CORRECTED"}):
            df=m[m.variant.eq(arm)].sort_values("signal_date").reset_index(drop=True)
            assert df.signal_date.equals(base.signal_date)
            assert np.allclose(df.basket_top3,base.basket_top3,rtol=0,atol=1e-12)
            cc=c[c.variant.eq(arm)]
            ui=unique[unique.variant.eq(arm)]
            z=dict(variant=arm,family=fam,months=len(df),
               changed=int(cc.changed.sum()),better=int(cc.changes_better.sum()),
               worse=int(cc.changes_worse.sum()),unique_pair_events=len(ui),
               frequency=float(cc.changed.sum()/(500*101)),
               correction_winrate=float(cc.changes_better.sum()/max(1,cc.changed.sum())),
               winrate_unique_events=float((ui.delta>0).mean()) if len(ui) else np.nan)
            for metric in METRICS:
                z[metric]=float(df[metric].mean())
                z["delta_vs_incumbent_"+metric]=float((df[metric]-base[metric]).mean())
            for years,tag in [([2026],"without_2026"),
                              ([2022,2025,2026],"without_2022_2025_2026")]:
                ok=~df.signal_date.dt.year.isin(years)
                z["excess_delta_"+tag]=float((df.loc[ok,"basket_selected_excess"]-
                       base.loc[ok,"basket_selected_excess"]).mean())
            rows.append(z)
    summary=pd.DataFrame(rows)
    assert len(summary)==8
    summary.to_csv(out/"AGGREGATE_SCORECARD.csv",index=False)
    rng=np.random.default_rng(20261024);N=101;rep=3000
    indices=((rng.integers(0,N,size=(rep,(N+5)//6))[:,:,None]
         +np.arange(6))%N).reshape(rep,-1)[:,:N]
    conf=[]
    for fam in FAMILIES:
        d=pd.read_csv(r/fam/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
        for arm in sorted(set(d.variant)-{"CORRECTED"}):
            k=d[d.variant.eq(arm)].sort_values("signal_date").reset_index(drop=True)
            for reference,r0 in (("INCUMBENT",base),("CORRECTED",original)):
                for metric in METRICS:
                    dx=k[metric].to_numpy()-r0[metric].to_numpy()
                    sample=dx[indices].mean(axis=1)
                    conf.append(dict(variant=arm,reference=reference,metric=metric,
                       observed=float(dx.mean()),lo95=float(np.quantile(sample,.025)),
                       hi95=float(np.quantile(sample,.975)),calendar_block=6,reps=rep))
    pd.DataFrame(conf).to_csv(out/"FULL_COMPARISON_BOOTSTRAP.csv",index=False)
    ev=pd.concat(events,ignore_index=True)
    ev.to_csv(out/"UNIQUE_PAIR_EVENTS_ALL.csv",index=False)
    summary_year=[]
    for fam in FAMILIES:
        d=pd.read_csv(r/fam/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
        for arm in sorted(set(d.variant)-{"CORRECTED"}):
            frame=d[d.variant.eq(arm)].sort_values("signal_date").reset_index(drop=True)
            for year in sorted(frame.signal_date.dt.year.unique()):
                match=frame.signal_date.dt.year.eq(year)
                summary_year.append(dict(variant=arm,year=int(year),months=int(match.sum()),
                   delta_excess=float((frame.loc[match,"basket_selected_excess"]-
                          base.loc[match,"basket_selected_excess"]).mean()),
                   delta_top1=float((frame.loc[match,"basket_top1"]-
                          base.loc[match,"basket_top1"]).mean())))
    pd.DataFrame(summary_year).to_csv(out/"PAIRED_YEARLY_VS_INCUMBENT.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        preregistered_families=FAMILIES,
        variants=8,selected_winner=False,
        historic_period_already_researched=True,virgin_holdout=False,
        149_etfs=True,canonical_baskets=500,
        fixed_incumbent="NESTED_24_TOP1_GUARD",monthly_block_bootstrap=6,
        production_modified=False),indent=2))
    print("HURDLE_AGGREGATE_PASS",flush=True)
    print(summary[["variant","basket_top1","basket_selected_excess",
       "basket_loss10_top1","delta_vs_incumbent_basket_selected_excess",
       "delta_vs_incumbent_basket_top1","unique_pair_events",
       "excess_delta_without_2026","excess_delta_without_2022_2025_2026"]].to_string(index=False),flush=True)
    print("CIs vs incumbent",flush=True)
    c=pd.DataFrame(conf)
    print(c[(c.reference=="INCUMBENT") & (c.metric=="basket_selected_excess")].to_string(index=False),flush=True)
if __name__=="__main__":main()
