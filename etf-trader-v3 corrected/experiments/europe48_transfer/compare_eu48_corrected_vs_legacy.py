#!/usr/bin/env python3
"""Strict matched EU48 source correction attribution, no training or cherry-pick.

Compare EXACT same 1374 EUR daily opens, old V2 125F baseline, legacy-V2
127-leaf source port, and actual V3 corrected kernel 127-leaf model (with/without
causal meta tree). Inspect 2022 damage and year/regime contributions, not just
headline CAGR. Do not tune or modify the policy.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd,numpy as np
OLD_MODELS=("CORRECTED","NESTED_24_TOP1_GUARD")
ALLOC=("TOP1","TOP2","TOP3","TOP5")
def read(path):
    x=pd.read_csv(path,parse_dates=["date"]);assert x.date.is_unique and x.date.is_monotonic_increasing
    return x.set_index("date")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--corrected",required=True)
    p.add_argument("--out",required=True)
    x=p.parse_args()
    out=Path(x.out);out.mkdir(parents=True,exist_ok=True)
    oldroot=Path("etf-trader-v3 corrected/experiments/europe48_transfer/results/native_alloc_20261024/tables")
    old=read(oldroot/"EUR48_V3_NET_DAILY_NAV.csv")
    corrected=read(Path(x.corrected)/"EUR48_V3_NET_DAILY_NAV.csv")
    assert old.index.equals(corrected.index) and len(old)==1374
    original_old=pd.read_csv(oldroot/"EUR48_FULL_UNRESTRICTED_CHOICE_LOG.csv",parse_dates=["signal_date"])
    actual=pd.read_csv(Path(x.corrected)/"EUR48_FULL_UNRESTRICTED_CHOICE_LOG.csv",parse_dates=["signal_date"])
    assert len(actual)==len(original_old)==65 and actual.signal_date.equals(original_old.signal_date)
    prev=pd.read_csv(oldroot/"PRIOR_EU48_V2_125F_EXACT_ECONOMIC_PARITY.csv")
    assert set(prev.name)=={"COMPACT21_BASE_TOP1","COMPACT21_BASE_TOP2","COMPACT21_BASE_TOP5"}
    oldstats=pd.read_csv(oldroot/"EUR48_V3_NET_SCORECARD.csv")
    newstats=pd.read_csv(Path(x.corrected)/"EUR48_V3_NET_SCORECARD.csv")
    assert len(newstats)==len(oldstats)==8
    rows=[];year=[];dd=[]
    for arm in OLD_MODELS:
        for policy in ALLOC:
            label=arm+"_"+policy
            o=old[label].to_numpy(float);n=corrected[label].to_numpy(float)
            qold=oldstats[(oldstats.model.eq(arm))&(oldstats.allocation.eq(policy))]
            qnew=newstats[(newstats.model.eq(arm))&(newstats.allocation.eq(policy))]
            assert len(qold)==len(qnew)==1
            assert np.isclose(o[-1],qold.terminal_capital.iloc[0],atol=1e-10)
            assert np.isclose(n[-1],qnew.terminal_capital.iloc[0],atol=1e-10)
            rows.append(dict(arm=arm,policy=policy,legacy_cagr=float(qold.cagr.iloc[0]),
                 corrected_cagr=float(qnew.cagr.iloc[0]),
                 legacy_maxdd=float(qold.maxdd_daily_open.iloc[0]),
                 corrected_maxdd=float(qnew.maxdd_daily_open.iloc[0]),
                 delta_cagr_pp=float(100*(qnew.cagr.iloc[0]-qold.cagr.iloc[0])),
                 delta_maxdd_pp=float(100*(qnew.maxdd_daily_open.iloc[0]-qold.maxdd_daily_open.iloc[0]))))
            for name,nav in (("legacy",o),("true_corrected",n)):
                peak=np.maximum.accumulate(np.r_[1.,nav])[1:]
                ind=int(np.argmin(nav/peak-1))
                dd.append(dict(model=name,arm=arm,allocation=policy,
                    maxdd=float(nav[ind]/peak[ind]-1),
                    trough=str(old.index[ind].date()),trough_nav=float(nav[ind])))
                prev_yr=1.
                for yearid in sorted(old.index.year.unique()):
                    within=old.index.year==yearid
                    close=float(nav[within][-1]);ret=close/prev_yr-1
                    year.append(dict(model=name,arm=arm,allocation=policy,year=int(yearid),
                        year_period_return=float(ret),open_months_count=int(within.sum())))
                    prev_yr=close
    changes=[]
    for name,frame in (("legacy",original_old),("true_corrected",actual)):
        for item in frame.itertuples(index=False):
            changes.append(dict(source=name,date=str(item.signal_date.date()),year=int(item.signal_date.year),
                   selected=str(item.selected),original_top1=str(item.original_top1),tree_top1=str(item.tree_top1),
                   changed=int(item.original_top1!=item.tree_top1)))
    joined=original_old[["signal_date","original_top1","tree_top1","selected"]].merge(
        actual[["signal_date","original_top1","tree_top1","selected"]],on="signal_date",
        suffixes=("_legacy","_corrected"),validate="one_to_one")
    joined["ranker_top1_changed_by_kernel"]=joined.original_top1_legacy.ne(joined.original_top1_corrected)
    joined["nested_tree_selected_diff"]=joined.tree_top1_legacy.ne(joined.tree_top1_corrected)
    joined.to_csv(out/"SOURCE_MONTHLY_CHOICES_PAIRED.csv",index=False)
    assert joined.ranker_top1_changed_by_kernel.any()
    pd.DataFrame(changes).to_csv(out/"MONTHLY_CHOICES_EXACT.csv",index=False)
    pd.DataFrame(rows).to_csv(out/"SOURCE_COMPARISON_SCORECARD.csv",index=False)
    pd.DataFrame(year).to_csv(out/"PAIRED_YEARLY_NET_RETURN.csv",index=False)
    pd.DataFrame(dd).to_csv(out/"TRUE_SOURCE_DRAWDOWN_TROUGH.csv",index=False)
    oldb=pd.read_csv(oldroot/"EU48_V3_MONTHLY_NESTED_TREE.csv")
    newb=pd.read_csv(Path(x.corrected)/"EU48_V3_MONTHLY_NESTED_TREE.csv")
    assert oldb.signal_date.equals(newb.signal_date)
    skill=[]
    for k in ("basket_base_top1","basket_meta_top1","basket_base_selected_excess",
        "basket_meta_selected_excess","basket_base_loss10","basket_meta_loss10"):
        skill.append(dict(metric=k,legacy=float(oldb[k].mean()),true_corrected=float(newb[k].mean()),
           delta=float((newb[k]-oldb[k]).mean())))
    pd.DataFrame(skill).to_csv(out/"BASKET_META_SKILL_COMPARISON.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        original_legacy_models_run=40092281559,
        true_corrected_models_run=40113201316,
        true_corrected_head_training_run=40112844351,
        verified_feature_discrepancy_run=40112742559,
        original_compact125_exact_replay=True,
        common_EUR_open_trading_days=1374,
        common_ISIN=48,monthly_signals=65,
        fees_oneway_bps=10,
        frozen_algorithms_and_meta_selection=True,
        no_model_promoted=True,exploratory_historic_not_virgin_holdout=True,
        production_unchanged=True,
        ranker_changed_first_stage_months=int(joined.ranker_top1_changed_by_kernel.sum()),
        tree_changed_months=int(joined.nested_tree_selected_diff.sum())),indent=2))
    print("TRUE_CORRECTED_CODE_ROOTCAUSE_PASS",flush=True)
    print(pd.DataFrame(rows).to_string(index=False),flush=True)
    print("MONTHLY_DIFFERENCE",int(joined.ranker_top1_changed_by_kernel.sum()),"of 65 base; meta",
      int(joined.nested_tree_selected_diff.sum()),"of 65",flush=True)
    print("YEARLY_TOP1",pd.DataFrame(year).query('allocation=="TOP1"').to_string(index=False),flush=True)
    print("TROUGHS",pd.DataFrame(dd).query('allocation=="TOP1"').to_string(index=False),flush=True)
if __name__=="__main__":main()
