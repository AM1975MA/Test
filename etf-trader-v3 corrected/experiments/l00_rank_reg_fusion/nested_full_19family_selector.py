#!/usr/bin/env python3
"""Strictly chronological chooser across original V3 tree and all 19 novel model families.

Each evaluation month t chooses using only previous OOS months ending earlier
than t-60 days. Configuration selection is separate from both base model
training and later economic simulation. IMPORTANT: these 2018-2026 research
months have been explored previously; selection does NOT imply a virgin holdout.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
METRICS=("basket_top1","basket_top3","basket_ndcg3",
         "basket_regret","basket_selected_excess","basket_loss10_top1")
FAMILIES=("DT","RF","ET","HGB","XGB","LGB","CAT","XGB_RET","LGB_RET",
          "DT_PAYOFF","DT_LOSS","RF_PAYOFF","XGB_PAYOFF","CAT_PAYOFF","LGB_PAYOFF",
          "DT_EVENT","RF_EVENT","XGB_EVENT","CAT_EVENT")
SCOPES=("PRIOR_ONLY","NEW_ONLY","ALL")
RULES=("GUARD24","GUARD36","UTILITY24","CONSERVATIVE24")
def load_file(path):
    t=pd.read_csv(path,parse_dates=["signal_date"])
    assert not t.duplicated(["signal_date","variant"]).any(),path
    assert t.groupby("variant").size().eq(101).all(),path
    return t

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True)
    p.add_argument("--incumbent",required=True)
    p.add_argument("--new",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    original=load_file(Path(a.base)/"PAIRED_MONTHLY.csv")
    prior=[x for x in original.variant.unique() if x!="CORRECTED"]
    assert len(prior)==36
    parts=[original]
    names=set(original.variant)
    for family in FAMILIES:
        part=load_file(Path(a.new)/family/"PAIRED_MONTHLY.csv")
        p2=part[part.variant!="CORRECTED"].copy()
        assert not set(p2.variant)&names,(family,set(p2.variant)&names)
        names|=set(p2.variant)
        control=part[part.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
        baseline=original[original.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
        assert control.signal_date.equals(baseline.signal_date),family
        np.testing.assert_allclose(control[list(METRICS)],
             baseline[list(METRICS)],atol=1e-12,rtol=0)
        parts.append(p2)
    frame=pd.concat(parts,ignore_index=True)
    assert not frame.duplicated(["signal_date","variant"]).any()
    base=frame[frame.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    dates=base.signal_date.to_numpy(dtype="datetime64[ns]")
    arms=["CORRECTED"]+sorted(set(frame.variant)-{"CORRECTED"})
    new_names=set(arms)-set(prior)-{"CORRECTED"}
    assert len(new_names)==93,(len(new_names),sorted(new_names)) # 7 binary x5 + 2 regress x4 + 6 payoff x5 + 4 event x5
    n=len(dates)
    values=np.full((n,len(arms),len(METRICS)),np.nan)
    for j,arm in enumerate(arms):
        rows=frame[frame.variant==arm].sort_values("signal_date").reset_index(drop=True)
        assert rows.signal_date.equals(base.signal_date)
        values[:,j,:]=rows[list(METRICS)].to_numpy(float)
    assert np.isfinite(values).all()
    assert np.allclose(values[:,:,1],values[:,0:1,1],atol=1e-12,rtol=0)
    diff=values-values[:,0:1,:]
    incumbent=pd.read_csv(Path(a.incumbent)/"NESTED_MONTHLY.csv",parse_dates=["signal_date"])
    incumbent=incumbent[incumbent.strategy.eq("NESTED_24_TOP1_GUARD")].sort_values("signal_date").reset_index(drop=True)
    assert incumbent.signal_date.equals(base.signal_date)
    incumbent_metrics=incumbent[list(METRICS)].to_numpy(float)
    # Explicitly verify earlier chronological best-tree selector can be
    # reproduced on the original 36 old tree variants EXACTLY.
    evals=[];month_rows=[];audit=[]
    for scope in SCOPES:
        allowed=[k for k in range(1,len(arms)) if
            (scope=="PRIOR_ONLY" and arms[k] in prior) or
            (scope=="NEW_ONLY" and arms[k] in new_names) or
            scope=="ALL"]
        assert allowed
        for rule in RULES:
            name=f"{scope}__{rule}"
            window=36 if "36" in rule else 24
            selection=np.zeros(n,dtype=int)
            for i,date in enumerate(dates):
                hist=np.flatnonzero(dates < date-np.timedelta64(60,"D"))[-window:]
                choice=0;best=0.
                if len(hist)>=24:
                    delta=diff[np.ix_(hist,allowed,np.arange(len(METRICS)))]
                    mu=delta.mean(axis=0)
                    top1=mu[:,0]; excess=mu[:,4]
                    if rule.startswith("GUARD"):
                        score=np.where((excess>0)&(top1>=0),excess,-np.inf)
                    elif rule.startswith("CONSERVATIVE"):
                        se=delta[:,:,4].std(axis=0,ddof=1)/np.sqrt(len(hist))
                        score=np.where(top1>=0,excess-1.64*se,-np.inf)
                    else:
                        # Broad regression-oriented criterion: positive mean
                        # return minus half the Top1 hit-rate delta penalty.
                        score=excess+np.minimum(0,top1)*.5
                    k=int(np.argmax(score))
                    if np.isfinite(score[k]) and score[k]>0:
                        choice=allowed[k];best=float(score[k])
                selection[i]=choice
                audit.append(dict(strategy=name,signal_date=pd.Timestamp(date),
                    chosen=arms[choice],candidate_scope=scope,window=window,
                    n_eligible_history=len(hist),historical_fitness=best,
                    used_signal_data_cutoff=pd.Timestamp(date-np.timedelta64(60,"D"))))
            selected=values[np.arange(n),selection,:]
            for i,d in enumerate(dates):
                z=dict(strategy=name,signal_date=pd.Timestamp(d),chosen=arms[selection[i]],year=pd.Timestamp(d).year)
                z.update({metric:float(selected[i,j]) for j,metric in enumerate(METRICS)})
                month_rows.append(z)
            for contrast,target in (("ORIGINAL",values[:,0,:]),("INCUMBENT",incumbent_metrics)):
                d=selected-target
                z=dict(strategy=name,contrast=contrast,n_months=n,
                    chosen_nonbaseline_months=int(np.count_nonzero(selection)),
                    pre2026_delta_excess=float(d[dates<np.datetime64("2026-01-01"),4].mean()))
                for k,metric in enumerate(METRICS):z["delta_"+metric]=float(d[:,k].mean())
                evals.append(z)
    chosen=pd.DataFrame(month_rows)
    prior_solution=chosen[chosen.strategy.eq("PRIOR_ONLY__GUARD24")].sort_values("signal_date").reset_index(drop=True)
    np.testing.assert_allclose(prior_solution[list(METRICS)].to_numpy(),
        incumbent_metrics,rtol=0,atol=1e-12,
        err_msg="The prior tree-only nested guard selector MUST match exact already certified incumbent")
    checks=[];rng=np.random.default_rng(20261024);boot=3000
    draw=((rng.integers(0,n,size=(boot,(n+5)//6))[:,:,None]
          +np.arange(6))%n).reshape(boot,-1)[:,:n]
    for name,sub in chosen.groupby("strategy",sort=True):
        v=sub.sort_values("signal_date")[list(METRICS)].to_numpy(float)
        for label,ref in (("ORIGINAL",values[:,0,:]),("INCUMBENT",incumbent_metrics)):
            for k,metric in enumerate(METRICS):
                dx=v[:,k]-ref[:,k]
                reps=dx[draw].mean(axis=1)
                checks.append(dict(strategy=name,reference=label,metric=metric,
                   delta=float(dx.mean()),ci025=float(np.quantile(reps,.025)),
                   ci975=float(np.quantile(reps,.975)),
                   n=101,calendar_block=6,reps=boot))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    pd.DataFrame(evals).to_csv(out/"SELECTOR_SUMMARY.csv",index=False)
    chosen.to_csv(out/"SELECTOR_MONTHLY.csv",index=False)
    pd.DataFrame(audit).to_csv(out/"SELECTOR_CHOICE_AUDIT.csv",index=False)
    pd.DataFrame(checks).to_csv(out/"SELECTOR_PAIRED_BOOTSTRAP.csv",index=False)
    yearly=chosen.groupby(["strategy","year"])[list(METRICS)].mean()
    yearly.to_csv(out/"SELECTOR_YEARLY.csv")
    raw=frame.groupby("variant")[list(METRICS)].mean()
    raw.to_csv(out/"SINGLE_MODEL_SKILL.csv")
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        base_run=40031144599,baseline_selector_run=40032282233,
        meta_algorithms_run="See GitHub workflow with nine matrix jobs",
        n_base_tree_candidates=36,n_new_candidates=len(new_names),
        months=101,baskets=500,etfs=149,lookahead_maturity_days=60,
        n_selector_variations=len(SCOPES)*len(RULES),
        incumbent_oracle_parity_passed=True,
        history_reused_not_virgin=True, production_unchanged=True,
        objectives_exploratory_not_final_model_selection=True),indent=2))
    print("NESTED_BAKEOFF_SUCCESS",flush=True)
    print(pd.DataFrame(evals).query('contrast=="INCUMBENT"').to_string(index=False),flush=True)
if __name__=="__main__":
    main()
