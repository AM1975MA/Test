#!/usr/bin/env python3
"""Fee stress extension of exact parity-verified 500-basket economic replay.

Frozen first-stage scores and original OHLCV; 101 fully matured signals.
Recreate each chosen tree's predictions and verify precise 500-basket monthly
metric parity with the independently produced nested validation artifact
BEFORE computing any equity or CAGR. Nothing here selects hyperparameters.
"""
from __future__ import annotations
import argparse, importlib.util, hashlib, json, re, sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(HERE))
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
from etf_trader_v3.source_only.statistics import metrics
from parallel_meta import load,prepare_tree_months,pair_features
from aggregate import read_shards,metric_for_order

def import_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

factor=import_module("v3_l08_reference",V3/"experiments"/"l08_score_policy_factorial"/"evaluate.py")
make_schedules=factor.make_schedules
replay=factor.replay
uncertainty=factor.uncertainty
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
STRATEGY="NESTED_24_TOP1_GUARD"
POLICIES=("TOP1","TOP2","TOP3")
WINDOWS={"FULL101":("2018-02-01","2026-06-30"),
         "MATCHED_2022":("2022-02-01","2026-06-30")}
PARSE=re.compile(r"^TREE_(expanding|last36)_D([123])_N(100|300)_P(0\.(?:55|6|65))$")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--shards",default="runs/v3_rrf")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--nested",default="runs/v3_nested_input")
    p.add_argument("--out",default="runs/v3_nested_economic")
    p.add_argument("--fee-bps",type=float,default=10.0)
    p.add_argument("--replace-with-second",action="store_true",help="Keep causal tree correction signal, but select the original ranker second place")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    mats,cats,_=load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    mats={k:v.loc[v.index>=pd.Timestamp("2011-01-01")] for k,v in mats.items()}
    all_cols=list(mats["Open"].columns);days=mats["Open"].index
    basket_members=load_baskets(a.baskets,cats)
    assert len(basket_members)==500 and all(len(x)==24 for x in basket_members)
    source,monthly,_=read_shards(a.shards,"regression")
    baseline=source[source.variant.eq("CORRECTED")].copy()
    validated=pd.read_csv(Path(a.nested)/"NESTED_MONTHLY.csv",parse_dates=["signal_date"])
    validated=validated[validated.strategy.eq(STRATEGY)].sort_values("signal_date")
    audit=pd.read_csv(Path(a.nested)/"NESTED_SELECTION_AUDIT.csv",parse_dates=["signal_date"])
    audit=audit[audit.strategy.eq(STRATEGY)].sort_values("signal_date")
    assert len(validated)==len(audit)==101
    assert validated.signal_date.equals(audit.signal_date)
    assert audit.maximum_mature_signal_date.lt(audit.signal_date.dt.strftime("%Y-%m-%d")).all()
    dates=set(audit.signal_date)
    baseline=baseline[baseline.signal_date.isin(dates)].copy()
    assert baseline.signal_date.nunique()==101
    base_schedules,_=make_schedules(baseline,basket_members,days,all_cols)
    months,reference=load(a.shards,a.baskets)
    training=prepare_tree_months(months)
    assert len(months)==101
    ticker_by_date={dt:list(g.sort_values("ticker").ticker)
                    for dt,g in baseline.groupby("signal_date",sort=True)}
    market_ids={t:i for i,t in enumerate(all_cols)}
    all_schedules={f"BASE__{p}":base_schedules[p] for p in POLICIES}
    all_schedules.update({f"TREE__{p}":{} for p in POLICIES})
    signal_rows=[];trade_rows=[]
    last_quarter=None;model_cache={}
    for i,(dt,v,baskets) in enumerate(months):
        dt=pd.Timestamp(dt)
        assert dt==audit.iloc[i].signal_date
        choice=str(audit.iloc[i].chosen)
        if (dt.year,(dt.month-1)//3)!=last_quarter:
            last_quarter=(dt.year,(dt.month-1)//3)
            model_cache={}
            quarter_start=dt
        if choice!="CORRECTED":
            match=PARSE.fullmatch(choice)
            assert match,choice
            window,depth,leaf,cut=match.groups()
            key=(window,int(depth),int(leaf))
            if key not in model_cache:
                earlier=[(d,x,y) for d,x,y in training
                         if d<quarter_start-pd.Timedelta(days=60)]
                assert len(earlier)>=24,(dt,len(earlier))
                selected=earlier if window=="expanding" else earlier[-36:]
                xx=np.concatenate([z[1] for z in selected])
                yy=np.concatenate([z[2] for z in selected])
                weights=np.concatenate([np.full(len(z[2]),1./len(z[2])) for z in selected])
                model=DecisionTreeClassifier(criterion="log_loss",max_depth=int(depth),
                    min_samples_leaf=int(leaf),random_state=20261024)
                model.fit(xx,yy,sample_weight=weights)
                model_cache[key]=model
        else:
            model=None;cut=0.
        names=ticker_by_date[dt]
        assert len(names)==149
        assert np.array_equal(np.array(names),np.array(sorted(names)))
        assert len(baskets)==500
        # Original candidate order of 500 baskets must be identical to the
        # frozen first-stage score policy (strictly compare full 500x149 weights).
        opens_pos=int(days.searchsorted(dt,side="right"))
        assert opens_pos<len(days) and days[opens_pos]>dt
        weights={p:np.zeros((500,149),float) for p in POLICIES}
        metric_list=[];num_changes=0;num_better=0;num_worse=0
        for bnum,(idx,orig) in enumerate(baskets):
            original_top=orig[:3]
            order=orig
            if choice!="CORRECTED":
                alternatives=list(orig[1:3])
                xx=np.asarray([pair_features(v,idx,orig,alt) for alt in alternatives])
                probs=model_cache[key].predict_proba(xx)
                if len(model_cache[key].classes_)==2:
                    yes=probs[:,list(model_cache[key].classes_).index(1)]
                    best=int(np.argmax(yes))
                    if yes[best]>float(cut):
                        chosen=int(alternatives[0]) if a.replace_with_second else int(alternatives[best])
                        order=np.concatenate(([chosen],orig[orig!=chosen]))
            actual=v["fwd"][idx]
            a_metric=metric_for_order(order,actual)
            metric_list.append(a_metric[:6])
            if order[0]!=orig[0]:
                num_changes+=1
                num_better+=int(actual[order[0]]>actual[orig[0]])
                num_worse+=int(actual[order[0]]<actual[orig[0]])
            pick_idx=idx[order[:3]]
            tickers=[names[int(t)] for t in pick_idx]
            market=[market_ids[t] for t in tickers]
            baseline_gap=float(v["rank"][idx[orig[0]]]-v["rank"][idx[orig[1]]])
            policy_weights={
              "TOP1":(1.0,0.,0.),
              "TOP2":(1.0,0.,0.) if baseline_gap>=.12 else (.75,.25,0.),
              "TOP3":(.5,.3,.2)}
            for policy in POLICIES:
                for k in range(3):
                    weights[policy][bnum,market[k]]+=policy_weights[policy][k]
            trade_rows.append(dict(signal_date=dt,basket=int(bnum),
                base_top1=names[int(idx[orig[0]])],tree_top1=tickers[0],
                top2=tickers[1],top3=tickers[2],meta_arm=choice,
                top1_changed=int(order[0]!=orig[0])))
        mm=np.asarray(metric_list,dtype=float)
        expected=validated.iloc[i]
        assert len(mm)==500 and not np.isnan(mm).any()
        for j,name in enumerate(("basket_top1","basket_top3","basket_ndcg3",
                                 "basket_regret","basket_selected_excess","basket_loss10_top1")):
            if not a.replace_with_second:
                np.testing.assert_allclose(mm[:,j].mean(),expected[name],rtol=0,atol=1e-11,
                err_msg=f"Monthly meta trade pick validation failed: {dt} {name}")
        for name,count in (("changed",num_changes),("changes_better",num_better),("changes_worse",num_worse)):
            if (not a.replace_with_second) or name=="changed":
                assert int(expected[name])==count,(dt,name,int(expected[name]),count)
        for policy in POLICIES:
            assert np.allclose(weights[policy].sum(axis=1),1),policy
            all_schedules[f"TREE__{policy}"][opens_pos]=weights[policy]
            # Keep an exact original allocator comparator in the economic replay.
        signal_rows.append(dict(signal_date=dt,model=choice,changed=num_changes,
           better=num_better,worse=num_worse,price_open_date=days[opens_pos]))
        print("META_CHOICE_PARITY",dt.date(),choice,num_changes,flush=True)
    assert len(signal_rows)==101 and len(trade_rows)==101*500
    assert all(set(all_schedules[f"TREE__{p}"])==set(base_schedules[p]) for p in POLICIES)
    # The reconstruction must have no signal order/timing/availability mismatches.
    t=pd.DataFrame(trade_rows)
    assert not t.duplicated(["signal_date","basket"]).any()
    t.to_csv(out/"ACTUAL_DECISION_LOG.csv",index=False)
    pd.DataFrame(signal_rows).to_csv(out/"DECISION_VALIDATION.csv",index=False)
    stats=[];curves=[];yearly=[];pairwise=[]
    for window,(start,end) in WINDOWS.items():
        paths={}
        for arm in sorted(all_schedules):
            dates_,equity,turnover,nreb=replay(all_schedules[arm],mats,start,end,a.fee_bps/10000.0)
            met=metrics(equity,turnover)
            stats.append(dict(window=window,arm=arm,fee_bps_one_way=a.fee_bps,
                n_rebalances=nreb,trading_days=len(dates_),**met))
            paths[arm]=(dates_,equity,turnover)
            nav=pd.Series(equity.mean(axis=0),index=dates_)
            curves.extend(dict(date=t,window=window,arm=arm,aggregate_nav=float(v))
                          for t,v in nav.items())
            prev=1.
            for year,g in nav.groupby(nav.index.year):
                yearly.append(dict(window=window,arm=arm,year=int(year),
                    aggregate_year_return=float(g.iloc[-1]/prev-1)))
                prev=float(g.iloc[-1])
            print("ECON_REPLAY",window,arm,met["aggregate_cagr"],met["aggregate_maxdd"],flush=True)
        for policy in POLICIES:
            base=paths[f"BASE__{policy}"];alt=paths[f"TREE__{policy}"]
            assert np.array_equal(base[0],alt[0])
            pairwise.append(dict(window=window,policy=policy,
                **uncertainty(base[0],base[1],alt[1],rep=2000)))
    pd.DataFrame(stats).to_csv(out/"ECONOMIC_SCORECARD.csv",index=False)
    pd.DataFrame(curves).to_csv(out/"DAILY_ENSEMBLE_NAV.csv",index=False)
    pd.DataFrame(yearly).to_csv(out/"YEARLY_ENSEMBLE.csv",index=False)
    pd.DataFrame(pairwise).to_csv(out/"PAIRED_21DAY_BLOCK.csv",index=False)
    (out/"ECONOMIC_MANIFEST.json").write_text(json.dumps(dict(
        research_only=True,reference_ranker_run=40016809498,
        meta_tree_run=40031144599,nested_selection_run=40032282233,
        frozen_raw_run=39482809691,reference_baskets_sha=SHA,
        n_baskets=500,n_etfs=149,n_signals=101,
        full_exact_ticker_decision_metrics_verified=True,
        baseline_top2_verifies_original_allocator_via_make_schedules=True,
        next_open_execution=True,cost_oneway_bps=a.fee_bps,
        risk_layers_on=False,execution_start_stop=WINDOWS,
        trading_policy={
          "TOP1":"100 percent first",
          "TOP2":"75/25 first-second; use 100/0 if original base ranker top1-top2 gap >=.12",
          "TOP3":"50/30/20 original candidates in tree-corrected ordering"},
        top2_gap_from_original_ranker=True,
        return_target_not_used_in_selection=True,
        meta_config_selected_before_date_using_60day_maturity=True,
        historical_calendar_previously_researched=True,
        cannot_claim_pristine_holdout=True,
        meta_policy="keep_tree_trigger_switch_to_original_second" if a.replace_with_second else "tree_decides_candidate",
        V2_V3_production_modified=False),indent=2))
    print("NESTED_ECONOMIC_SUCCESS",pd.DataFrame(stats).to_string(index=False),flush=True)
    print("ECON_ALPHA",pd.DataFrame(pairwise).to_string(index=False),flush=True)
if __name__=="__main__":
    main()
