#!/usr/bin/env python3
"""EU48 capacity ablation 15/31/63/127 leaves: actual next-open economic results.

No meta, no stops; identical 48 ETFs, 125 features, 3 seeds, training cutoffs,
360 rounds, monthly held-out signals, execution calendar, and EUR 10bp fees.
Compare original saved Compact21 ranker as independent exact economic parity.
This is previously studied 2021–2026 history, not a fresh holdout.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from isin_first2026.predict48.tournament import price_data,monthly_data
from europe_only75.f3h1_original_transfer.run import costed_path
SRC="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
BASE={"Top1":.04727914934059951,"Top2":.03733920043018113,"Top5":.0496050654456055}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--shards",required=True)
    ap.add_argument("--prep",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    master,names,O,C=price_data(a.prep)
    assert len(names)==48 and O.index.equals(C.index)
    _,cal=monthly_data(master,names,O,C)
    cal=cal.loc[cal.signal_date.ge(pd.Timestamp("2021-01-01"))].reset_index(drop=True)
    assert len(cal)==65 and str(cal.entry_date.iloc[0].date())=="2021-02-01"
    pieces=[]
    for y in range(2021,2027):
        df=pd.read_csv(Path(a.shards)/str(y)/"YEAR_OOS_ALL_LEAVES.csv",parse_dates=["signal_date"])
        assert df.signal_date.dt.year.eq(y).all() and set(df.leaf)=={15,31,63,127}
        pieces.append(df)
    z=pd.concat(pieces,ignore_index=True)
    assert len(z)==65*48*4 and not z.duplicated(["signal_date","ticker","leaf"]).any()
    truth=z[z.leaf==127].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    reference=pd.read_csv(SRC,parse_dates=["signal_date"]).sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert truth[["signal_date","ticker"]].equals(reference[["signal_date","ticker"]])
    np.testing.assert_allclose(truth.fwd_ret_21,reference.fwd_ret_21,rtol=0,atol=1e-12)
    matrix={"REFERENCE_125F_DEPTH4":reference.pivot(index="signal_date",columns="ticker",values="pred")
               .reindex(index=cal.signal_date,columns=names)}
    for leaf in (15,31,63,127):
        mat=z[z.leaf==leaf].pivot(index="signal_date",columns="ticker",values="pred").reindex(
             index=cal.signal_date,columns=names)
        assert mat.notna().all(axis=None)
        matrix["V3_MAXLEAF_"+str(leaf)]=mat
    labels=reference.pivot(index="signal_date",columns="ticker",values="fwd_ret_21").reindex(
        index=cal.signal_date,columns=names)
    assert labels.notna().all(axis=None)
    monthly=[];score=[];ledgers=[];navs=[]
    for model,pred in matrix.items():
        indices=np.argsort(-pred.to_numpy(float),axis=1,kind="stable")
        evals=[]
        y=labels.to_numpy(float)
        for i,row in enumerate(indices):
            vals=y[i];best=int(np.argmax(vals))
            score.append(dict(model=model,signal_date=cal.signal_date.iloc[i],year=cal.signal_date.iloc[i].year,
               top1_win=int(row[0]==best),top3_win=int(best in row[:3]),
               spearman=float(spearmanr(pred.to_numpy(float)[i],vals).statistic),
               selected_excess=float(vals[row[0]]-vals.mean()),
               selected_nextopen21d=float(vals[row[0]]),
               tail_loss10=int(vals[row[0]]<=-.10),
               top1=names[int(row[0])],
               top2=names[int(row[1])],
               top3=names[int(row[2])]))
        for policy,n in (("Top1",1),("Top2",2),("Top5",5)):
            weights=[{names[int(j)]:1/n for j in row[:n]} for row in indices]
            met,nav,ledger=costed_path(weights,cal,O,O.index)
            if model=="REFERENCE_125F_DEPTH4":
                if policy in BASE:np.testing.assert_allclose(
                  met["cagr"],BASE[policy],rtol=0,atol=1e-10,
                  err_msg="V2 independent original reference fee and NAV mismatch")
            monthly.append(dict(model=model,policy=policy,**met))
            ledgers.append(ledger.assign(model=model,policy=policy))
            navs.append(nav.rename(model+"_"+policy))
            print("CAPACITY_ECON",model,policy,met["cagr"],met["maxdd_daily_open"],flush=True)
    comp=pd.DataFrame(score)
    economic=pd.DataFrame(monthly)
    trade=pd.concat(ledgers,ignore_index=True)
    curves=pd.concat(navs,axis=1)
    assert len(comp)==65*5 and curves.notna().all(axis=None)
    base=comp[comp.model.eq("V3_MAXLEAF_127")].sort_values("signal_date").reset_index(drop=True)
    delta=[]
    for model in sorted(comp.model.unique()):
        p=comp[comp.model.eq(model)].sort_values("signal_date").reset_index(drop=True)
        assert p.signal_date.equals(base.signal_date)
        entry=dict(model=model,n_months=65)
        for k in ("top1_win","top3_win","spearman","selected_excess","tail_loss10"):
            entry[k]=float(p[k].mean())
            entry["delta_"+k+"_vs_leaf127"]=float((p[k]-base[k]).mean())
        entry["same_month_top1_fraction_as_127"]=float(p.top1.eq(base.top1).mean())
        delta.append(entry)
    pd.DataFrame(delta).to_csv(out/"SKILL_COMPARISON.csv",index=False)
    comp.to_csv(out/"MONTHLY_65_ETF_PICKS.csv",index=False)
    economic.to_csv(out/"EUR48_ECONOMIC_CAGR_DD.csv",index=False)
    trade.to_csv(out/"MONTHLY_TRADE_LEDGER.csv",index=False)
    curves.rename_axis("date").to_csv(out/"DAILY_NAV.csv")
    audit=[]
    for model in sorted(comp.model.unique()):
        select=trade[(trade.model==model)&(trade.policy=="Top1")].sort_values("signal").reset_index(drop=True)
        old=trade[(trade.model=="V3_MAXLEAF_127")&(trade.policy=="Top1")].sort_values("signal").reset_index(drop=True)
        assert select.signal.equals(old.signal)
        diff=select.net_log_growth.to_numpy(float)-old.net_log_growth.to_numpy(float)
        n=len(diff)
        rng=np.random.default_rng(20261024);rep=3000
        ids=((rng.integers(0,n,size=(rep,(n+5)//6))[:,:,None]
              +np.arange(6))%n).reshape(rep,-1)[:,:n]
        boot=diff[ids].mean(axis=1)
        audit.append(dict(model=model,contrast="Top1 monthly net log return vs leaf127",
             observed=float(diff.mean()),ci025=float(np.quantile(boot,.025)),
             ci975=float(np.quantile(boot,.975)),block_calendar_months=6,reps=rep))
    pd.DataFrame(audit).to_csv(out/"PAIRED_BLOCK_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
         n_funds=48,unique_legal_Europe_exposed_ISIN=48,
         trading_calendar_matches_original_EU48=True,
         original_V2_source_Economic_125F_cagr_parity_1e_10=True,
         original_V3_127_raw_scores_per_year_parity=True,
         only_max_leaves_varied=[15,31,63,127],same_360rounds_same_three_seeds=True,
         original_2017_training_start=True,price_source="2026 snapshot, EUR priced original",
         n_months_2021_2026=65,fee_per_side_bps=10,
         same_125_predictors=True,experiment_hypothesis="excessive capacity of 127 leaves on 48-fund ranking task",
         multiple_comparisons_unadjusted=True,virgin_holdout=False,
         production_unchanged=True),indent=2))
    print("EU48_LEAF_CAPACITY_DIAG_COMPLETE",flush=True)
    print(economic[["model","policy","cagr","maxdd_daily_open"]].to_string(index=False),flush=True)
    print(pd.DataFrame(delta).to_string(index=False),flush=True)
if __name__=="__main__":main()
