#!/usr/bin/env python3
"""Out-of-time 48 European ISIN V3 127-leaf vs nested 36-config decision-tree.

Sources:
- V3 research main/experiments/l00_rank_reg_fusion/parallel_meta.py: exactly
  pair_features, 36 tree combinations, quarterly refits, 60-day maturity.
- V3 research .../nested_tree_selector.py: 24 eligible months, top1 guard.
- Certified real Euro48 previous raw and Compact125 OOS predictions, 65 months.
- Original 500 canonical Europe48 category-balanced 24-fund pocket generator.
- Original Europe real EUR next-open self-financing costed_path, 10bp per leg.

No lookahead, no parameter search on Europe outcomes. The original V3 tree
predictive weights cannot be blindly transferred as they were US149-trained.
This trial deliberately fits the frozen *algorithm* on Europe48 2017-26 data,
then learns the meta only from unique matured Europe pair events.
"""
from __future__ import annotations
import argparse,json,hashlib,re
from collections import defaultdict
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.tree import DecisionTreeClassifier
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.predict48.tournament import price_data,monthly_data
SEEDS=(101,202,303)
REGS=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
WINDOWS=("expanding","last36"); DEPTHS=(1,2,3); LEAVES=(100,300);THRESHOLDS=(.55,.60,.65)
SOURCE_CMP=Path("isin_first2026/compact21_base48/results")
PREV_125=SOURCE_CMP/"FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
ORIGINAL_METRICS={"COMPACT21_BASE": {"TOP1":.04727914934059951,"TOP2":.03733920043018113,"TOP5":.0496050654456055}}
def pct(x):return pd.Series(np.asarray(x,float)).rank(method="average",pct=True).to_numpy()
def pair_features(v,idx,orig,alternative):
    rank=v["rank"][idx];first=int(orig[0]);j=int(alternative);top=orig[:min(3,len(orig))]
    rr=v["REG_REL125"][idx];ar=v["REG_ABS125"][idx]
    rv=v["REG_REL101"][idx];h=v["REG_HUBER125"][idx];av=v["REG_ABS101"][idx]
    return np.array([float(rank[first]-rank[j]),float(rank[first]-rank[orig[1]]),
       float(rank[first]-rank[top[-1]]),float(rank[first]),float(rank[j]),
       float(rr[j]-rr[first]),float(rv[j]-rv[first]),float(ar[j]-ar[first]),
       float(av[j]-av[first]),float(h[j]-h[first]),float(rr[first]),float(rr[j]),
       float(ar[j]),float(np.std(rank[top]))],float)
def metrics(chosen,order,indices,fwd):
    vals=fwd[indices]
    true_best=int(np.argmax(vals))
    # Correlative winners and signed log excess are not economic returns.
    return dict(top1=float(chosen==true_best),top3=float(true_best in order[:3]),
        selected_excess=float(vals[chosen]-vals.mean()),top1_loss10=float(vals[chosen]<=-.10))
def train(cache,dates,first_date):
    eligible=[(d,p) for d,p in cache if d<first_date-pd.Timedelta(days=60)]
    models={};fits=[]
    if len(eligible)<24:return models,fits
    for window in WINDOWS:
        chosen=eligible if window=="expanding" else eligible[-36:]
        X=np.concatenate([x[0] for _,x in chosen])
        y=np.concatenate([x[1] for _,x in chosen])
        weights=np.concatenate([np.full(len(x[1]),1./len(x[1])) for _,x in chosen])
        assert np.isfinite(X).all() and np.isfinite(y).all() and len(X)==len(y)
        for dep in DEPTHS:
            for leaf in LEAVES:
                m=DecisionTreeClassifier(criterion="log_loss",max_depth=dep,
                    min_samples_leaf=leaf,random_state=20261024)
                m.fit(X,y,sample_weight=weights)
                models[(window,dep,leaf)]=m
                fits.append(dict(quarter_start=str(first_date.date()),window=window,
                    depth=dep,leaf=leaf,n_months=len(chosen),n_dedup_pairs=len(y),
                    newest_train_month=str(chosen[-1][0].date()),trained_depth=m.get_depth(),
                    nodes=m.tree_.node_count))
    return models,fits
def selection(hist,dt):
    cutoff=dt-pd.Timedelta(days=60)
    older=[d for d in sorted(hist) if d<cutoff][-24:]
    if len(older)<24:return "CORRECTED",0.,len(older)
    control=np.array([hist[d]["CORRECTED"] for d in older],float)
    best="CORRECTED";value=0.
    arms=sorted(set(hist[older[-1]])-{"CORRECTED"})
    for arm in arms:
        current=np.array([hist[d][arm] for d in older],float)
        gain=float(np.mean(current[:,1]-control[:,1]))
        top1=float(np.mean(current[:,0]-control[:,0]))
        if gain>value and top1>=0:best=arm;value=gain
    return best,value,len(older)
def monthly_roster(data,types,master,names,prices):
    # Global Eu48 original legal-ISIN source checks
    assert master.ticker.nunique()==master["isin"].nunique()==48
    ref=pd.read_csv(PREV_125,parse_dates=["signal_date"])
    assert len(ref)==65*48
    allpred=pd.concat([pd.read_csv(p,parse_dates=["signal_date"]) for p in data])
    assert len(allpred)==65*48*6 and not allpred.duplicated(["variant","signal_date","ticker"]).any()
    assert set(allpred.variant)=={"CORRECTED",*REGS}
    control=allpred[allpred.variant.eq("CORRECTED")]
    control=control.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    baseline=ref.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert control[["signal_date","ticker"]].equals(baseline[["signal_date","ticker"]])
    np.testing.assert_allclose(control.fwd_ret_21,baseline.fwd_ret_21,rtol=0,atol=1e-12)
    assert len(control.signal_date.unique())==65
    wide=allpred.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    labels=allpred[allpred.variant.eq("CORRECTED")].set_index(["signal_date","ticker"])["fwd_ret_21"]
    wide=wide.join(labels.rename("fwd"))
    assert np.isfinite(wide.to_numpy()).all()
    for sd,sub in wide.groupby(level=0,sort=True):
        z=sub.droplevel(0).reindex(names)
        assert z.notna().all(axis=None) and len(z)==48
        yield pd.Timestamp(sd),{k:pct(z[k]) for k in ("CORRECTED",*REGS)},z.fwd.to_numpy(float),z
def run(args):
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    prep=Path(args.prep)
    mats,cats,_=load_ticker_csv_folder(prep/"raw_ticker_csv")
    master,names,O,C=price_data(prep)
    assert len(names)==48 and set(mats["Open"].columns)==set(names)
    names=list(mats["Open"].columns)
    assert master["isin"].nunique()==48 and master.ticker.nunique()==48
    roster=pd.read_csv(prep/"raw_ticker_csv/universe.csv")
    assert roster.ticker.nunique()==roster["isin"].nunique()==48
    mem=build_canonical_baskets(roster,names)
    mem=mem.merge(roster[["ticker","macro_category"]],on="ticker",how="left",
                  validate="many_to_one")
    assert len(mem)==12000 and mem.basket.nunique()==500
    bidx=[]
    for bid,g in mem.groupby("basket",sort=True):
        assert len(g)==24 and g.ticker.nunique()==24
        assert len(g.macro_category.value_counts())==6 and g.macro_category.value_counts().eq(4).all()
        bidx.append((int(bid),np.array([names.index(t) for t in g.ticker],dtype=int)))
    mm,cal=monthly_data(master,names,O,C)
    cal=cal[cal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65 and str(cal.entry_date.iloc[0].date())=="2021-02-01"
    assert str(cal.exit_date.iloc[-1].date())=="2026-07-01"
    assert O.index.equals(C.index)
    assert not O.isna().any(axis=None)
    # Original benchmark numeric parity on 3 frozen Compact125 pick policies
    prev=pd.read_csv(PREV_125,parse_dates=["signal_date"])
    prevs=prev.pivot(index="signal_date",columns="ticker",values="pred").reindex(
        index=cal.signal_date,columns=names)
    assert prevs.notna().all(axis=None)
    verified=[]
    for size in (1,2,5):
        weights=[{names[i]:1/size for i in np.argsort(-sc,kind="stable")[:size]}
                    for sc in prevs.to_numpy(float)]
        check,_,_=costed_path(weights,cal,O,O.index)
        original=ORIGINAL_METRICS["COMPACT21_BASE"]["TOP"+str(size)]
        np.testing.assert_allclose(check["cagr"],original,rtol=0,atol=1e-9)
        verified.append(dict(name=f"COMPACT21_BASE_TOP{size}",**check))
    print("ORIGINAL_EU48_ECONOMIC_PARITY",verified,flush=True)
    allmonths=list(monthly_roster(args.head,REGS,master,names,O))
    assert len(allmonths)==65
    assert [m[0] for m in allmonths]==list(cal.signal_date)
    # Unique original/alternative ETF pairs from 500 balanced baskets,
    # only chronology <= quarter start - 60 calendar days used in refits.
    dedup=[]
    for dt,preds,yy,_ in allmonths:
        v={"rank":preds["CORRECTED"],**{k:preds[k] for k in REGS}}
        seen={}
        for bid,idx in bidx:
            rank=v["rank"][idx];orig=np.argsort(-rank,kind="stable")
            for alt in orig[1:3]:
                i,j=int(idx[orig[0]]),int(idx[alt])
                key=(i,j)
                if key not in seen:
                    seen[key]=(pair_features(v,idx,orig,alt),int(yy[j]>yy[i]))
        XX=np.stack([x[0] for x in seen.values()]); labels=np.array([x[1] for x in seen.values()])
        assert XX.shape[1]==14 and len(XX)>=10
        dedup.append((dt,(XX,labels)))
    # Train all 36 precommitted V3 meta variants, choose using prior matured
    # Europe 500-basket OOS decisions, then execute on full 48 unrestricted.
    history={};allstats=[];sel_log=[];fit_audit=[];holdings={k:[] for k in ("CORRECTED","NESTED_24_TOP1_GUARD")}
    baskets_trade=[];full_trade=[]
    quarter=None;models={}
    for di,(dt,preds,yy,z) in enumerate(allmonths):
        q=(dt.year,(dt.month-1)//3)
        if q!=quarter:
            models, audit=train(dedup,cal.signal_date,dt)
            fit_audit.extend(audit);quarter=q
        v={"rank":preds["CORRECTED"],**{k:preds[k] for k in REGS}}
        full_idx=np.arange(48,dtype=int)
        full_order=np.argsort(-v["rank"],kind="stable")
        all_arms=["CORRECTED"]+[f"TREE_{window}_D{dep}_N{leaf}_P{cut:g}"
          for window in WINDOWS for dep in DEPTHS for leaf in LEAVES for cut in THRESHOLDS]
        stats={a:[] for a in all_arms}
        corr=defaultdict(lambda:[0,0,0])
        fullorders={"CORRECTED":full_order}
        def evaluate(idx,orig):
            score={}
            original=metrics(int(orig[0]),orig,idx,yy)
            score["CORRECTED"]=original
            X=np.array([pair_features(v,idx,orig,alt) for alt in orig[1:3]])
            for key,model in models.items():
                p=model.predict_proba(X)
                prob=p[:,list(model.classes_).index(1)] if len(model.classes_)==2 else np.zeros(2)
                cand=int(orig[1+np.argmax(prob)])
                probability=float(prob.max())
                for cut in THRESHOLDS:
                    arm=f"TREE_{key[0]}_D{key[1]}_N{key[2]}_P{cut:g}"
                    order=np.r_[cand,orig[orig!=cand]] if probability>cut else orig
                    score[arm]=metrics(int(order[0]),order,idx,yy)
            for arm in all_arms:
                score.setdefault(arm,original)
            return score,X
        global_scores,_=evaluate(full_idx,full_order)
        # For EU meta model competence: evaluate on frozen balanced 500 pockets
        # independently of the unrestricted executable account.
        for bid,idx in bidx:
            orig=np.argsort(-v["rank"][idx],kind="stable")
            vals,_=evaluate(idx,orig)
            for arm,obj in vals.items():
                stats[arm].append([obj["top1"],obj["selected_excess"],
                                  obj["top3"],obj["top1_loss10"]])
                if arm!="CORRECTED" and not np.isclose(obj["selected_excess"],vals["CORRECTED"]["selected_excess"]):
                    cc=corr[arm];cc[0]+=1
                    cc[1]+=int(obj["selected_excess"]>vals["CORRECTED"]["selected_excess"])
                    cc[2]+=int(obj["selected_excess"]<vals["CORRECTED"]["selected_excess"])
        assert set(stats)==set(all_arms) and all(len(rows)==500 for rows in stats.values())
        history[dt]={arm:np.array(rows).mean(axis=0) for arm,rows in stats.items()}
        # IMPORTANT use only dates strictly earlier than dt-60, not current date
        # for dynamic selection.
        chosen,value,n_hist=selection({d:h for d,h in history.items() if d<dt},
                                      dt)
        assert chosen in all_arms
        if chosen=="CORRECTED":
            global_selected=full_order
        else:
            # Repeat selected frozen variant on 48 unrestricted ETFs, identical
            # model trained from 500 EU basket OOF data only.
            match=re.fullmatch(r"TREE_(expanding|last36)_D([123])_N(100|300)_P(0\.(?:55|6|65))",chosen)
            assert match
            window,depth,leaf,cut=match.groups()
            m=models[(window,int(depth),int(leaf))]
            xx=np.array([pair_features(v,full_idx,full_order,a) for a in full_order[1:3]])
            pro=m.predict_proba(xx)
            ps=pro[:,list(m.classes_).index(1)] if len(m.classes_)==2 else np.zeros(2)
            alternative=int(full_order[1+np.argmax(ps)])
            global_selected=np.r_[alternative,full_order[full_order!=alternative]] if ps.max()>float(cut) else full_order
        # Validate V3 frozen Top3 coverage at the full unrestricted universe.
        assert set(global_selected[:3])==set(full_order[:3])
        chosen_baskets=history[dt][chosen]
        baseline_baskets=history[dt]["CORRECTED"]
        allstats.append(dict(signal_date=dt,year=dt.year,n_baskets=500,selected=chosen,
            basket_base_top1=baseline_baskets[0],basket_meta_top1=chosen_baskets[0],
            basket_base_selected_excess=baseline_baskets[1],
            basket_meta_selected_excess=chosen_baskets[1],
            basket_base_top3=baseline_baskets[2],basket_meta_top3=chosen_baskets[2],
            basket_base_loss10=baseline_baskets[3],basket_meta_loss10=chosen_baskets[3],
            unrestricted_base_top1=global_scores["CORRECTED"]["top1"],
            unrestricted_meta_top1=metrics(int(global_selected[0]),global_selected,full_idx,yy)["top1"],
            unrestricted_base_selected_excess=global_scores["CORRECTED"]["selected_excess"],
            unrestricted_meta_selected_excess=metrics(int(global_selected[0]),global_selected,full_idx,yy)["selected_excess"],
            original_top1=names[int(full_order[0])],
            tree_top1=names[int(global_selected[0])],
            switched=int(global_selected[0]!=full_order[0]),
            chosen_prior_objective=value,history_months=n_hist,
            full_rank_gap=float(v["rank"][full_order[0]]-v["rank"][full_order[1]])))
        for label,order in (("CORRECTED",full_order),("NESTED_24_TOP1_GUARD",global_selected)):
            holdings[label].append(tuple(names[i] for i in order[:5]))
        full_trade.append(dict(signal_date=dt,selected=chosen,
           original_top1=names[int(full_order[0])],
           tree_top1=names[int(global_selected[0])]))
        print("EU48_TREE_MONTH",str(dt.date()),"choose",chosen,"changed",int(global_selected[0]!=full_order[0]),
            "ret_base",global_scores["CORRECTED"]["selected_excess"],
            "ret_tree",metrics(int(global_selected[0]),global_selected,full_idx,yy)["selected_excess"],flush=True)
    result=pd.DataFrame(allstats)
    # Compute real executable EUR next-open Top1/Top2/Top3/Top5 with 10bp/leg.
    scorecards=[];navs=[];ledgers=[]
    for arm,orders in holdings.items():
        assert len(orders)==65
        for label in ("TOP1","TOP2","TOP3","TOP5"):
            weights=[]
            for i,tickers in enumerate(orders):
                if label=="TOP1":current=(1.,0.,0.,0.,0.)
                elif label=="TOP2":
                    current=(1.,0.,0.,0.,0.) if result.full_rank_gap.iloc[i]>=.12 else (.75,.25,0.,0.,0.)
                elif label=="TOP3":current=(.5,.3,.2,0.,0.)
                else:current=(.2,)*5
                w={name:float(q) for name,q in zip(tickers,current) if q>0}
                assert np.isclose(sum(w.values()),1)
                weights.append(w)
            measure,nav,ledger=costed_path(weights,cal,O,O.index)
            key=arm+"_"+label
            scorecards.append(dict(model=arm,allocation=label,fees_bps_one_way=10,**measure))
            navs.append(nav.rename(key))
            ledgers.append(ledger.assign(model=arm,allocation=label))
            print("EU48_ECONOMIC_COSTED",key,measure["cagr"],measure["maxdd_daily_open"],flush=True)
    econ=pd.DataFrame(scorecards)
    assert len(econ)==8 and econ.n_sessions.eq(1374).all()
    curves=pd.concat(navs,axis=1)
    assert curves.shape==(1374,8) and curves.notna().all(axis=None)
    econ.to_csv(out/"EUR48_V3_NET_SCORECARD.csv",index=False)
    curves.rename_axis("date").to_csv(out/"EUR48_V3_NET_DAILY_NAV.csv")
    pd.concat(ledgers).to_csv(out/"EUR48_V3_MONTHLY_TRADE_LEDGER.csv",index=False)
    result.to_csv(out/"EU48_V3_MONTHLY_NESTED_TREE.csv",index=False)
    pd.DataFrame(full_trade).to_csv(out/"EUR48_FULL_UNRESTRICTED_CHOICE_LOG.csv",index=False)
    pd.DataFrame(fit_audit).to_csv(out/"FIT_META_AUDIT.csv",index=False)
    pd.DataFrame(verified).to_csv(out/"PRIOR_EU48_V2_125F_EXACT_ECONOMIC_PARITY.csv",index=False)
    (out/"EU48_V3_RESULTS_MANIFEST.json").write_text(json.dumps(dict(
       method="V3 127-leaf refit EU48, 36 unique-pair tree variants, nested asof24 top1 guard",
       universe="48 European legal ISIN only, EUR venue",
       n_baskets_training=500,basket_members=24,balanced_six_categories_four_each=True,
       date_start="2021-02-01",date_end="2026-07-01",
       source_firststage_run=40086216896,
       source_preV3_Compact125_original_exact_replay=True,
       six_regression_heads_unique_48_ISR=True,
       meta_months_first24_only_baseline=True,
       mature_lag_calendar_days=60,refit_quarterly=True,
       no_new_model_hyperparam_optimization=True,
       original_V3_meta_rule="20261024 frozen tree family and selector",
       original_EU48_risk_Stage19_not_equal_to_standalone_V3=True,
       baskets500_results_depend_not_independent=True,
       survivor_2026_universe_yahoo_backfilled=True,
       macro_spy_last_US_close_prior_EU_open=True,
       genuine_independent_holdout=False,
       source_only_research=True,production_unchanged=True),indent=2))
    print("EU48_V3_DECISION_TREE_COMPLETE",flush=True)
    print(econ.to_string(index=False),flush=True)
    print("V3_SELECTION",result.selected.value_counts().to_dict(),flush=True)
    print("EU48_V3_COMPETENCE",result[["basket_base_top1","basket_meta_top1",
         "basket_base_selected_excess","basket_meta_selected_excess"]].mean().to_dict(),flush=True)
if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--prep",required=True)
    parser.add_argument("--head",action="append",required=True)
    parser.add_argument("--out",required=True)
    run(parser.parse_args())
