#!/usr/bin/env python3
"""V3 127leaf + original V3 14F decision tree on legal Europe48 ISINs.

A single Europe48 full-universe Top1/2/3/5 account, next-open EUR fills,
0.1% one-way notional fees and identical dates to certified V2 source Compact.
500 balanced 24-ETF baskets are used ONLY to train, choose and measure
the V3 selective decision tree; NOT a substitute for real account CAGR.
The tree can replace only a Top1 with one of the ranker's own Top3.
Tree fits quarterly from 60-calendar-day matured earlier OOS months; the
NESTED_24_TOP1_GUARD selector uses exactly the same frozen parameters as USA V3
and requires non-negative incremental Top1 hit AND positive excess 21D in
the 24 most recent matured months. No European hyperparameter tuning.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from sklearn.tree import DecisionTreeClassifier
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets
from isin_first2026.predict48.tournament import price_data,monthly_data
from europe_only75.f3h1_original_transfer.run import costed_path
from isin_first2026.compact21_base48.run import ROOT
from collections import defaultdict
ARMS=("CORRECTED","REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
METRICS=("basket_top1","basket_top3","basket_ndcg3","basket_regret",
       "basket_selected_excess","basket_loss10_top1")
WINDOWS=("expanding","last36")
DEPTHS=(1,2,3);LEAVES=(100,300);THRESHOLDS=(.55,.60,.65)
TREE_NAMES=[f"TREE_{w}_D{d}_N{n}_P{p:g}" for w in WINDOWS
            for d in DEPTHS for n in LEAVES for p in THRESHOLDS]
def metric(order,y):
    n=len(y);true=np.argsort(-y,kind="stable")
    r=np.empty(n,float);r[true]=np.linspace(1,0,n)
    top=order[:3];discount=1/np.log2(np.arange(2,len(top)+2))
    ideal=np.sort(r)[::-1][:len(top)]
    picked=int(order[0]);best=int(np.argmax(y))
    return (float(picked==best),float(best in top),
        float(np.dot(r[top],discount)/np.dot(ideal,discount)),
        float(y.max()-y[picked]),float(y[picked]-y.mean()),
        float(y[picked]<=-.1),picked)
def pair_features(v,idx,orig,alternative):
    rank=v["rank"][idx];first=int(orig[0]);j=int(alternative)
    top=orig[:min(3,len(orig))]
    rr=v["REG_REL125"][idx];ar=v["REG_ABS125"][idx]
    rv=v["REG_REL101"][idx];h=v["REG_HUBER125"][idx];av=v["REG_ABS101"][idx]
    z=[float(rank[first]-rank[j]),float(rank[first]-rank[orig[1]]),
       float(rank[first]-rank[top[-1]]),float(rank[first]),float(rank[j]),
       float(rr[j]-rr[first]),float(rv[j]-rv[first]),float(ar[j]-ar[first]),
       float(av[j]-av[first]),float(h[j]-h[first]),float(rr[first]),float(rr[j]),
       float(ar[j]),float(np.std(rank[top]))]
    assert len(z)==14 and np.isfinite(z).all()
    return z
def train_month(dt,v,selections):
    found={}
    for idx,orig in selections:
        a=int(idx[orig[0]])
        for alt in orig[1:3]:
            b=int(idx[alt]);key=(a,b)
            if key not in found:
                found[key]=(pair_features(v,idx,orig,alt),
                            int(v["fwd"][b]>v["fwd"][a]))
    x=np.asarray([q[0] for q in found.values()],float)
    y=np.asarray([q[1] for q in found.values()],np.int8)
    assert len(x)>=40 and x.shape[1]==14
    return dt,x,y
def fit_tree_family(prepared,cutoff):
    prior=[row for row in prepared if row[0]<cutoff-pd.Timedelta(days=60)]
    if len(prior)<24:return {},0
    models={}
    for window in WINDOWS:
        history=prior if window=="expanding" else prior[-36:]
        x=np.concatenate([t[1] for t in history])
        y=np.concatenate([t[2] for t in history])
        w=np.concatenate([np.full(len(t[2]),1/len(t[2])) for t in history])
        for depth in DEPTHS:
            for leaf in LEAVES:
                clf=DecisionTreeClassifier(max_depth=depth,min_samples_leaf=leaf,
                    criterion="log_loss",random_state=20261024)
                clf.fit(x,y,sample_weight=w)
                models[(window,depth,leaf)]=clf
    return models,len(prior)
def order_for(model,threshold,v,idx,orig):
    if model is None or len(model.classes_)!=2:return orig
    alts=list(orig[1:3])
    p=model.predict_proba(np.array([pair_features(v,idx,orig,z) for z in alts]))[:,
                           list(model.classes_).index(1)]
    ix=int(np.argmax(p))
    if p[ix]<=threshold:return orig
    chosen=int(alts[ix])
    return np.r_[chosen,orig[orig!=chosen]]
def parse(name):
    if name=="CORRECTED":return None,0.
    fields=name.split("_");assert len(fields)==5
    return (fields[1],int(fields[2][1:]),int(fields[3][1:])),float(fields[4][1:])
def choose(hist,dt):
    mature=[z for z in hist if z["signal_date"]<dt-pd.Timedelta(days=60)]
    dates=sorted(set(z["signal_date"] for z in mature))[-24:]
    if len(dates)<24:return "CORRECTED",len(dates),0.
    rows=pd.DataFrame([z for z in mature if z["signal_date"] in dates])
    base=rows[rows.variant.eq("CORRECTED")].sort_values("signal_date")
    assert len(base)==24
    chosen="CORRECTED";best=0.
    for candidate in TREE_NAMES:
        v=rows[rows.variant.eq(candidate)].sort_values("signal_date")
        assert len(v)==24
        excess=float((v.basket_selected_excess.to_numpy()-
                      base.basket_selected_excess.to_numpy()).mean())
        t1=float((v.basket_top1.to_numpy()-base.basket_top1.to_numpy()).mean())
        if t1>=0 and excess>best:chosen=candidate;best=excess
    return chosen,len(dates),best
def monthly_frame(scores,months):
    parts=[]
    for year in range(2021,2027):
        f=Path(scores)/str(year)/"EU48_V3_FIRSTSTAGE_SCORES.csv"
        x=pd.read_csv(f,parse_dates=["signal_date"])
        assert set(x.variant)==set(ARMS) and x.signal_date.dt.year.eq(year).all()
        parts.append(x)
    p=pd.concat(parts,ignore_index=True)
    assert len(p)==48*65*6 and not p.duplicated(["signal_date","ticker","variant"]).any()
    assert p.groupby(["signal_date","variant"]).size().eq(48).all()
    old=pd.read_csv("isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv",parse_dates=["signal_date"])
    assert len(old)==48*65
    cc=p[p.variant.eq("CORRECTED")].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    old=old.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert cc[["signal_date","ticker"]].equals(old[["signal_date","ticker"]])
    np.testing.assert_allclose(cc.fwd_ret_21,old.fwd_ret_21,rtol=0,atol=1e-12)
    assert sorted(cc.signal_date.unique())==list(months.signal_date)
    return p,old
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--heads",required=True)
    parser.add_argument("--prep",required=True)
    parser.add_argument("--out",required=True)
    a=parser.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    raw=Path(a.prep)/"raw_ticker_csv"
    mats,cat,_=load_ticker_csv_folder(raw)
    master,names,O,C=price_data(a.prep)
    names=list(mats["Open"].columns);assert set(names)==set(master.ticker) and len(names)==48
    assert master["isin"].is_unique and set(master.benchmark_bucket)=={
        "EU_EQUITY_BROAD","EU_EQUITY_SECTOR","EU_EQUITY_COUNTRY",
        "EU_EQUITY_FACTOR","SOVEREIGN_EUR","EU_PROPERTY"}
    roster=pd.read_csv(raw/"universe.csv")
    mem=build_canonical_baskets(roster,names)
    assert len(mem)==12000 and mem.basket.nunique()==500
    bm=[]
    ticker_index={t:i for i,t in enumerate(names)}
    for _,b in mem.groupby("basket",sort=True):
        assert b.ticker.nunique()==24
        idx=np.array([ticker_index[t] for t in b.ticker],int)
        bm.append(idx)
        groups=b.merge(roster[["ticker","macro_category"]],on="ticker",validate="one_to_one").macro_category.value_counts()
        assert len(groups)==6 and groups.eq(4).all()
    membership_hash=hashlib.sha256(mem.to_csv(index=False).encode()).hexdigest()
    _,cal=monthly_data(master,names,O,C)
    cal=cal[cal.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65 and len(names)==48
    scores,prior=monthly_frame(a.heads,cal)
    source=prior.set_index(["signal_date","ticker"])
    v_by_date={};selected={}
    for date,g in scores.groupby("signal_date",sort=True):
        wide=g.pivot(index="ticker",columns="variant",values="pred").reindex(names)
        assert wide.notna().all().all()
        y=source.loc[pd.IndexSlice[date,names],"fwd_ret_21"].to_numpy(float)
        vals={"rank":wide.CORRECTED.rank(pct=True).to_numpy(float),"fwd":y}
        vals.update({r:wide[r].rank(pct=True).to_numpy(float) for r in ARMS if r!="CORRECTED"})
        v_by_date[pd.Timestamp(date)]=vals
        selected[pd.Timestamp(date)]=[(idx,np.argsort(-vals["rank"][idx],kind="stable")) for idx in bm]
    prepared=[train_month(date,v_by_date[date],selected[date]) for date in sorted(v_by_date)]
    dates=list(sorted(v_by_date))
    assert dates==list(cal.signal_date)
    history=[];audits=[];decisions=[];selected_global={}
    cache={};latestquarter=None
    for date in dates:
        vals=v_by_date[date];basket_rows=selected[date]
        q=(date.year,(date.month-1)//3)
        if q!=latestquarter:
            models,training_months=fit_tree_family(prepared,date)
            cache=models
            latestquarter=q
            audits.append(dict(quarter_start=str(date.date()),last_eligible_train=str(
                (date-pd.Timedelta(days=60)).date()),mature_months=training_months,
                models=len(models)))
        monthscore={}
        for arm in ("CORRECTED",)+tuple(TREE_NAMES):monthscore[arm]=[]
        for idx,orig in basket_rows:
            f=vals["fwd"][idx];base=metric(orig,f)
            monthscore["CORRECTED"].append(base[:6])
            for arm in TREE_NAMES:
                key,t=parse(arm)
                order=order_for(cache.get(key),t,vals,idx,orig)
                monthscore[arm].append(metric(order,f)[:6])
        for arm,arr in monthscore.items():
            m=np.asarray(arr,float).mean(axis=0)
            history.append(dict(signal_date=date,variant=arm,n_baskets=500,
                **dict(zip(METRICS,m))))
        # Select configuration using only earlier-matured OOS results, never
        # return of current signal month.
        chosen,n_hist,score=choose(history,date)
        key,prob=parse(chosen)
        base=np.argsort(-vals["rank"],kind="stable")
        altered=order_for(cache.get(key),prob,vals,np.arange(48),base)
        selected_global[date]=altered
        decisions.append(dict(signal_date=date,tree_variant=chosen,
            previous_mature_months=n_hist,historical_utility_score=score,
            incumbent_top1=names[base[0]],tree_top1=names[altered[0]],
            first_stage_top3=";".join(names[i] for i in base[:3]),
            changes_top1=bool(base[0]!=altered[0])))
        if len(history)%37==0:
            print("EU48_TREE_MONTH",date.date(),chosen,"history",n_hist,flush=True)
    history_df=pd.DataFrame(history)
    assert len(history_df)==65*37
    assert not history_df.duplicated(["variant","signal_date"]).any()
    choosing=pd.DataFrame(decisions)
    assert len(choosing)==65 and set(choosing.tree_variant).issubset({"CORRECTED",*TREE_NAMES})
    summary=[];monthly=[]
    for i,date in enumerate(dates):
        row=history_df[(history_df.signal_date.eq(date))]
        arm=choosing.loc[i,"tree_variant"]
        sub=row[row.variant.eq(arm)].iloc[0]
        base=row[row.variant.eq("CORRECTED")].iloc[0]
        baseline_rank=v_by_date[date]["rank"];ix=np.argsort(-baseline_rank,kind="stable")
        top=selected_global[date]
        assert set(top[:3])==set(ix[:3]),"Top3 NOT PRESERVED"
        summary.append(dict(signal_date=date,variant="CORRECTED",
            **{m:float(base[m]) for m in METRICS}))
        summary.append(dict(signal_date=date,variant="NESTED_24_TOP1_GUARD",
            **{m:float(sub[m]) for m in METRICS}))
    pair=pd.DataFrame(summary)
    pair.to_csv(out/"EUR48_PAIRED_500_BASKET_MONTHLY.csv",index=False)
    history_df.to_csv(out/"EUR48_ALL37_META_TREE_MONTHLY.csv",index=False)
    choosing.to_csv(out/"EUR48_NESTED_TREE_SELECTION_AUDIT.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"EUR48_MATURE_META_FIT_AUDIT.csv",index=False)
    # Economically compare genuine EUR 48-account execution to 125F
    # previously CERTIFIED result, with identical fee and dates.
    previous_result=json.loads(Path("isin_first2026/compact21_base48/results/RESULT.json").read_text())
    assert previous_result["signal_month_count"]==65
    oldpred=prior.pivot(index="signal_date",columns="ticker",values="pred").reindex(columns=names)
    assert list(oldpred.index)==dates
    ops=[]
    for variant in ("EU48_V2_ORIGINAL_125F","EU48_V3_127LEAF","EU48_V3_127LEAF_TREE"):
        ranks=[]
        for date in dates:
            if variant=="EU48_V2_ORIGINAL_125F":
                raw=oldpred.loc[date].to_numpy(float)
                order=np.argsort(-raw,kind="stable")
            elif variant=="EU48_V3_127LEAF":
                order=np.argsort(-v_by_date[date]["rank"],kind="stable")
            else:
                order=selected_global[date]
            ranks.append(order)
        for take in (1,2,3,5):
            weights=[{names[int(index)]:1/take for index in order[:take]} for order in ranks]
            econ,nav,ledger=costed_path(weights,cal,O,O.index)
            assert econ["n_sessions"]==1374
            key=f"Top{take}"
            if variant=="EU48_V2_ORIGINAL_125F" and take in (1,2,5):
                control=previous_result["method_outcomes"]["COMPACT21_BASE"][key]["economic"]
                for metric_name in ("cagr","terminal_capital","maxdd_daily_open","sharpe_daily_log"):
                    np.testing.assert_allclose(econ[metric_name],control[metric_name],
                        rtol=0,atol=1e-10,err_msg="STRICT PRIOR EUROPE 48 ECONOMIC REPLAY PARITY FAILED")
            ops.append(dict(variant=variant,policy=key,**econ))
            nav.rename(f"{variant}_{key}").to_csv(out/f"NAV_{variant}_{key}.csv")
            ledger.insert(0,"variant",variant);ledger.insert(1,"policy",key)
            monthly.append(ledger)
            print("EU48_ACTUAL_COSTED",variant,key,round(econ["cagr"]*100,4),
                  round(econ["maxdd_daily_open"]*100,4),flush=True)
    economics=pd.DataFrame(ops)
    economics.to_csv(out/"EU48_COSTED_ECONOMIC_SCORECARD.csv",index=False)
    pd.concat(monthly,ignore_index=True).to_csv(out/"EU48_TRADE_LOG_NEXT_OPEN.csv",index=False)
    # Full 48 skill sampled at 65 truly OOS monthly dates, no sample overlap:
    months=[]
    for date in dates:
        v=v_by_date[date]
        f=v["fwd"];mean=float(np.mean(f))
        oldrow=oldpred.loc[date].to_numpy(float)
        for arm,scores_ in (("EU48_V2_ORIGINAL_125F",oldrow),
                            ("EU48_V3_127LEAF",v["rank"])):
            order=np.argsort(-scores_,kind="stable")
            months.append(dict(variant=arm,signal_date=date,
                 universe_top1=int(order[0]==np.argmax(f)),
                 universe_top3=int(np.argmax(f) in order[:3]),
                 selected_excess_21=float(f[order[0]]-mean),
                 universe_spearman_21=float(spearmanr(scores_,f).statistic)))
        order=selected_global[date]
        months.append(dict(variant="EU48_V3_127LEAF_TREE",signal_date=date,
            universe_top1=int(order[0]==np.argmax(f)),
            universe_top3=int(np.argmax(f) in order[:3]),
            selected_excess_21=float(f[order[0]]-mean),
            universe_spearman_21=float(spearmanr(v["rank"],f).statistic)))
    skill=pd.DataFrame(months)
    skill.to_csv(out/"EU48_UNRESTRICTED_48_PREDICTIVE_SKILL_MONTHLY.csv",index=False)
    # Bootstrap calendar blocks, not overlapping 500 baskets.
    rng=np.random.default_rng(20261024);n=65;B=3000
    ix=((rng.integers(0,n,size=(B,(n+2)//3))[:,:,None]+np.arange(3))%n).reshape(B,-1)[:,:n]
    bs=[];y=skill.set_index(["variant","signal_date"])
    for alt,ref in (("EU48_V3_127LEAF_TREE","EU48_V3_127LEAF"),
                    ("EU48_V3_127LEAF","EU48_V2_ORIGINAL_125F")):
        for metric_name in ("universe_top1","universe_spearman_21","selected_excess_21"):
            t=(y.loc[alt].sort_index()[metric_name]-y.loc[ref].sort_index()[metric_name]).to_numpy(float)
            dist=t[ix].mean(axis=1)
            bs.append(dict(challenger=alt,reference=ref,metric=metric_name,
                mean_delta=float(t.mean()),lo95=float(np.quantile(dist,.025)),
                hi95=float(np.quantile(dist,.975)),months=65,block_months=3))
    pd.DataFrame(bs).to_csv(out/"EU48_PAIRED_SKILL_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        study="Europe-only EUR-listed 48 genuinely independent ISIN",
        reference="V2 125F XGB original European refit, not USA149",
        v3_base="127 leaf rank-pairwise x360 three seeds yearly",
        original_v3_meta="36 selective tree variants quarterly mature label 60day lag",
        selector="NESTED_24_TOP1_GUARD original 24 matured months Top1 guard",
        trained_on_all_48_not_baskets=True,
        category_balanced_500_baskets_24_each=True,basket_sha256=membership_hash,
        account_single_unrestricted_48=True,
        first_oos_signal="2021-01-29",last_oos_signal="2026-05-29",
        pricing_venue="all 48 strictly common real quoted EUR opens",
        costs_one_way=.001,months=65,quote_sessions=1374,
        money_simulation_original125_exact_parity=True,
        full_v2_original_stage19_separately_available=True,
        original_v2_stage19_cagr=-.001548735494856131,
        original_v2_stage19_maxdd=-.3990932998524386,
        source_population_selection_vintage_2026_and_history_backadjusted=True,
        test_history_previously_used_for_eu_research=True,
        production_changed=False),indent=2))
    print("EU48_V3_TREE_COMPLETE",flush=True)
    print(economics[["variant","policy","cagr","maxdd_daily_open","sharpe_daily_log"]].to_string(index=False),flush=True)
    print(skill.groupby("variant")[["universe_top1","universe_spearman_21","selected_excess_21"]].mean().to_string(),flush=True)
if __name__=="__main__":main()
