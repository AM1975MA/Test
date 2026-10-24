#!/usr/bin/env python3
"""EU48 2022 source-level capacity and overfitting audit, no winner selection.

Explicitly diagnose depth4 original ~<=16 leaves against the 127-leaf V3.
The same 125 source feature columns, all 48 EU ISINs, 3 seeds, 360 rounds,
annual 2022 fully matured train rows, true adjusted EUR next-open 21d
labels, original asof prior-close SPY, and EU account costed-path evaluator.
No meta, leverage, governor or parameter promotion. Results NOT a holdout.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from scipy.stats import spearmanr
from xgboost import XGBRanker
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.compact21_base48.run import strict_build_spy
from isin_first2026.v2_usref48.original_us_references import asof_quotes
from isin_first2026.predict48.tournament import price_data,monthly_data
from europe_only75.f3h1_original_transfer.run import costed_path
BASKET_LEAFS=("ORIGINAL_DEPTH4", "LEAVES15","LEAVES31","LEAVES63","LEAVES127")
YEAR=2022
SOURCE125="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
def rankstats(y,p,dates):
    t=pd.DataFrame({"d":dates,"y":y,"p":p})
    per=[]
    for d,z in t.groupby("d",sort=True):
        assert len(z)==48
        corr=float(spearmanr(z.y,z.p).statistic)
        selected=int(np.argmax(z.p.to_numpy()))
        per.append((d,corr,float(z.y.iloc[selected]-z.y.mean()),float(z.y.iloc[selected]),
                     int(selected==int(np.argmax(z.y.to_numpy())))))
    pp=np.asarray([row[1:] for row in per],float)
    return dict(nmonths=len(per),mean_spearman=float(pp[:,0].mean()),
                mean_21d_excess=float(pp[:,1].mean()),
                mean_selected_21d=float(pp[:,2].mean()),
                correct_top1=int(pp[:,3].sum()))
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--prep",required=True)
    ap.add_argument("--us",required=True)
    ap.add_argument("--fx",required=True)
    ap.add_argument("--reference127",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    dest=Path(args.out);dest.mkdir(exist_ok=True,parents=True)
    mats,cats,_=load_ticker_csv_folder(Path(args.prep)/"raw_ticker_csv")
    assert len(cats)==48
    usref=dest/"SPY_REF";asof_quotes(args.us,mats["Close"].index,args.fx,usref)
    prior=pd.read_csv(usref/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",parse_dates=["date"])
    dates,feat,_,_=strict_build_spy(mats,prior)
    labeled=k.add_labels(feat,mats["Open"],dates)
    valid=labeled[k.F2D_FEATURES].notna().sum(axis=1)>=30
    stamp=pd.Timestamp("2022-01-01")
    tr=labeled[(labeled.signal_date>=pd.Timestamp("2017-01-01"))&
               (labeled.signal_date<stamp)&(labeled.exit_date_21<stamp)&
               labeled.target_rank_21.notna()&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    te=labeled[(labeled.signal_date.dt.year==2022)&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert len(tr)==2784 and len(te)==576
    assert tr.signal_date.nunique()==58 and te.signal_date.nunique()==12
    assert tr.groupby("signal_date").ticker.nunique().eq(48).all()
    assert te.groupby("signal_date").ticker.nunique().eq(48).all()
    o125=pd.read_csv(SOURCE125,parse_dates=["signal_date"])
    o125=o125[o125.signal_date.dt.year.eq(2022)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    o127=pd.read_csv(Path(args.reference127)/"EU48_V3_FIRSTSTAGE_SCORES.csv",parse_dates=["signal_date"])
    o127=o127[o127.variant.eq("CORRECTED")].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert o125[["signal_date","ticker"]].equals(te[["signal_date","ticker"]])
    assert o127[["signal_date","ticker"]].equals(te[["signal_date","ticker"]])
    np.testing.assert_allclose(o125.fwd_ret_21,te.fwd_ret_21,rtol=0,atol=1e-12)
    np.testing.assert_allclose(o127.fwd_ret_21,te.fwd_ret_21,rtol=0,atol=1e-12)
    master,names,O,C=price_data(args.prep)
    names=list(mats["Open"].columns)
    _,cal=monthly_data(master,names,O,C)
    cal=cal[cal.signal_date.dt.year.eq(2022)].reset_index(drop=True)
    assert len(cal)==12
    assert te.groupby("signal_date").size().eq(48).all()
    cfg=dict(k.COMPACT_PARAMS)
    y=np.rint(tr.target_rank_21.to_numpy(float)*100).astype(int)
    groups=tr.groupby("signal_date",sort=True).size().to_numpy()
    Xt=tr[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
    Xv=te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
    results=[];logs=[];scores=[]
    for setup in BASKET_LEAFS:
        if setup=="ORIGINAL_DEPTH4":
            pars=dict(cfg)
        else:
            leaf=int(setup.split("LEAVES")[1])
            pars=dict(cfg,max_depth=0,max_leaves=leaf,grow_policy="lossguide")
        train_preds=[];test_preds=[];leaf_summary=[]
        for seed in (101,202,303):
            m=XGBRanker(**pars,random_state=seed)
            m.fit(Xt,y,group=groups,verbose=False)
            train_preds.append(m.predict(Xt));test_preds.append(m.predict(Xv))
            dumped=m.get_booster().get_dump(dump_format="json")
            nleaf=np.array([tree.count('"leaf":') for tree in dumped],dtype=int)
            assert len(nleaf)==360
            leaf_summary.append(dict(config=setup,seed=seed,
                  mean_leaves=float(nleaf.mean()),early_mean=float(nleaf[:60].mean()),
                  last60_mean=float(nleaf[-60:].mean()),
                  max_leaves_actual=int(nleaf.max()),theoretical_limit=16 if setup=="ORIGINAL_DEPTH4" else leaf))
        pt=np.mean(train_preds,axis=0)
        pv=np.mean(test_preds,axis=0)
        assert np.isfinite(pv).all()
        actual=te.fwd_ret_21.to_numpy(float)
        if setup=="ORIGINAL_DEPTH4":saved=o125.pred.to_numpy(float)
        elif setup=="LEAVES127":saved=o127.pred.to_numpy(float)
        else:saved=None
        differing=0;mean_abs=np.nan
        if saved is not None:
            mean_abs=float(np.abs(saved-pv).mean())
            for g in te.signal_date.unique():
                ind=np.flatnonzero(te.signal_date.eq(g))
                differing+=int(ind[int(np.argmax(saved[ind]))]!=ind[int(np.argmax(pv[ind]))])
            assert differing==0,(setup,differing,mean_abs)
        skill_train=rankstats(tr.fwd_ret_21.to_numpy(float),pt,tr.signal_date.to_numpy())
        skill_test=rankstats(actual,pv,te.signal_date.to_numpy())
        bydate=te[["signal_date","ticker"]].copy();bydate["pred"]=pv;bydate["true_ret21"]=actual
        holdings=[]
        for day in cal.signal_date:
            g=bydate[bydate.signal_date.eq(day)]
            best=g.loc[g.pred.idxmax(),"ticker"]
            holdings.append({best:1.0})
            item=g[g.ticker.eq(best)].iloc[0]
            logs.append(dict(config=setup,signal_date=str(day.date()),selected_ticker=best,
                  fwd_21day_return=float(item.true_ret21)))
        economic,eq,ledger=costed_path(holdings,cal,O,O.index)
        results.append(dict(config=setup,**{f"train_{k}":v for k,v in skill_train.items()},
                 **{f"oos_{k}":v for k,v in skill_test.items()},
                 signals_switched_vs_saved=int(differing),mean_abs_saved_prediction_diff=mean_abs,
                 **{f"account_{k}":float(economic[k]) for k in ("cagr","maxdd_daily_open","terminal_capital")},
                 model_leaf_early=float(np.mean([x["early_mean"] for x in leaf_summary])),
                 model_leaf_last60=float(np.mean([x["last60_mean"] for x in leaf_summary]))))
        scores.append(bydate.assign(config=setup))
        print("EU48_CAPACITY_DIAG",results[-1],flush=True)
        pd.DataFrame(leaf_summary).to_csv(dest/(setup+"_ACTUAL_LEAF_COUNTS.csv"),index=False)
    pd.DataFrame(results).to_csv(dest/"2022_CAPACITY_DIAGNOSTIC.csv",index=False)
    pd.DataFrame(logs).to_csv(dest/"2022_EACH_MONTH_TOP1.csv",index=False)
    pd.concat(scores).to_csv(dest/"2022_ALL_SCORES.csv",index=False)
    (dest/"MANIFEST.json").write_text(json.dumps(dict(nETF=48,year=2022,months_fit=58,months_OOS=12,
        target="21day next-open rank pct",training_records=2784,
        model_params_fixed_except_capacity=True,base_original_model="depth4",
        V3_original_model="max_leaves127 lossguide",seeds=[101,202,303],
        n_estimators=360,source_labels_reproduced=True,
        parity_of_old125_and_127_selected_top1=True,
        retrospective_diagnostic_not_hyperparam_selection=True),indent=2))
    print("EU48_2022_CAPACITY_DIAGNOSTIC_DONE",flush=True)
if __name__=="__main__":main()
