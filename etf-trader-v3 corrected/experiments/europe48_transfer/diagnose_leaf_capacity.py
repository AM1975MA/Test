#!/usr/bin/env python3
"""Predeclared diagnostic EU48 XGB capacity sweep, NOT performance optimization.

Keep same 125 features, 3 seeds, original 360 rounds, 2017+ annual mature OOS
training labels, same source EU48 data/US prior as old original 127-leaf run.
Compare max_leaves 15/31/63/127 in each year against immutable old 127 and
the old V2 depth-4 booster. Before using alternatives, require 127 replay
scores and every original target identical. Report per-month skill, not
portfolio strategy promotion. Historical 2021-26 explored: NOT fresh holdout.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from xgboost import XGBRanker
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.compact21_base48.run import strict_build_spy
from isin_first2026.v2_usref48.original_us_references import asof_quotes
F=list(k.F2D_FEATURES)
S=(101,202,303)
LEAVES=(15,31,63,127)
PREF="etf-trader-v3 corrected/experiments/europe48_transfer/results/tables"
REFERENCE="isin_first2026/compact21_base48/results/FITTED_3SEED_ANNUAL/BASE_ORIGINAL_125F_XGB_65x48_TRUE_OOS_SCORES.csv"
def ranks(v):
    x=pd.Series(v);return x.rank(pct=True).to_numpy(float)
def main():
    ap=argparse.ArgumentParser()
    for a in ("year","prep","us","fx","out"):ap.add_argument("--"+a,required=True)
    args=ap.parse_args();year=int(args.year);assert year in range(2021,2027)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    mats,cats,_=load_ticker_csv_folder(Path(args.prep)/"raw_ticker_csv")
    assert len(cats)==48
    refdir=out/"SOURCE_SPY_PRIOR";asof_quotes(args.us,mats["Close"].index,args.fx,refdir)
    spy=pd.read_csv(refdir/"STRICT_PRIOR_US_CLOSE_FOR_EU_FEATURES_AND_CASH_EUR.csv",parse_dates=["date"])
    dates,features,_,_=strict_build_spy(mats,spy)
    full=k.add_labels(features,mats["Open"],dates)
    valid=full[F].notna().sum(axis=1)>=30
    cut=pd.Timestamp(year,1,1)
    base=pd.read_csv(REFERENCE,parse_dates=["signal_date"])
    v2=base[base.signal_date.dt.year.eq(year)].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    old=pd.read_csv(f"{PREF}/v3-europe48-127leaf-heads-{year}/EU48_V3_FIRSTSTAGE_SCORES.csv",parse_dates=["signal_date"])
    old=old[old.variant.eq("CORRECTED")].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    tr=full[full.signal_date.ge(pd.Timestamp("2017-01-01"))&
            full.signal_date.lt(cut)&full.exit_date_21.lt(cut)&
            full.target_rank_21.notna()&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    te=full[full.signal_date.dt.year.eq(year)&
            full.signal_date.isin(v2.signal_date)&valid].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert te[["signal_date","ticker"]].equals(old[["signal_date","ticker"]])
    assert te[["signal_date","ticker"]].equals(v2[["signal_date","ticker"]])
    np.testing.assert_allclose(te.fwd_ret_21,old.fwd_ret_21,rtol=0,atol=1e-12)
    np.testing.assert_allclose(te.fwd_ret_21,v2.fwd_ret_21,rtol=0,atol=1e-12)
    X=tr[F].replace([np.inf,-np.inf],np.nan); Xt=te[F].replace([np.inf,-np.inf],np.nan)
    group=tr.groupby("signal_date").size().to_numpy(int)
    assert np.all(group==48)
    y=np.rint(tr.target_rank_21.to_numpy(float)*100).astype(int)
    params=dict(k.COMPACT_PARAMS,max_depth=0,grow_policy="lossguide")
    rows=[]
    for leaf in LEAVES:
        allp=[]
        for seed in S:
            model=XGBRanker(**dict(params,max_leaves=leaf),random_state=seed)
            model.fit(X,y,group=group,verbose=False)
            allp.append(model.predict(Xt))
            print("EU_LEAF_CAPACITY_FIT",year,leaf,seed,"train",len(tr),flush=True)
        p=np.mean(allp,axis=0)
        if leaf==127:
            raw=np.asarray(old.pred,float)
            err=np.abs(p-raw)
            pmax=float(err.max());rmse=float(np.mean(err**2)**.5)
            print("CAPACITY_127_ORIGINAL_REPRO",year,pmax,rmse,flush=True)
            assert np.allclose(p,raw,rtol=4e-5,atol=3e-5),(year,pmax,rmse)
            for date,part in te.assign(model=p).groupby("signal_date"):
                orig=old[old.signal_date.eq(date)].sort_values("ticker").pred.to_numpy(float)
                mine=part.sort_values("ticker").model.to_numpy(float)
                assert np.argmax(mine)==np.argmax(orig),date
        for date,part in te.assign(model=p).groupby("signal_date"):
            prior=v2[v2.signal_date.eq(date)].sort_values("ticker")
            part=part.sort_values("ticker")
            assert part.ticker.tolist()==prior.ticker.tolist()
            score=part.model.to_numpy(float);y0=part.fwd_ret_21.to_numpy(float)
            x1=int(np.argmax(score));v1=int(np.argmax(prior.pred.to_numpy(float)))
            ranking=ranks(score);oldrank=ranks(prior.pred.to_numpy(float))
            spearman=np.corrcoef(ranking,oldrank)[0,1]
            actual=np.argsort(-y0,kind="stable")
            rows.append(dict(year=year,signal_date=str(date.date()),leaf=leaf,
               ticker=str(part.ticker.iloc[x1]),
               old_ticker=str(part.ticker.iloc[v1]),
               selected_return_21=float(y0[x1]),
               selected_excess_vs_48mean=float(y0[x1]-y0.mean()),
               former_v2_excess=float(y0[v1]-y0.mean()),
               top1_winner=float(x1==actual[0]),
               top3_winner=float(actual[0] in np.argsort(-score,kind="stable")[:3]),
               rho_vs_old_v2=float(spearman),
               unchanged_old_top1=bool(x1==v1),
               delta_ret21_vs_v2=float(y0[x1]-y0[v1])))
    df=pd.DataFrame(rows)
    assert df.groupby("leaf").size().eq(len(v2.signal_date.unique())).all()
    df.to_csv(out/"EUR48_CAPACITY_MONTHLY.csv",index=False)
    summ=df.groupby("leaf").agg(months=("signal_date","size"),
         mean_selected_excess_21=("selected_excess_vs_48mean","mean"),
         top1_hit=("top1_winner","mean"),
         top3_hit=("top3_winner","mean"),
         average_rho_vs_v2=("rho_vs_old_v2","mean"),
         unchanged_original_top1=("unchanged_old_top1","sum"),
         average_delta_vs_v2=("delta_ret21_vs_v2","mean"))
    summ.to_csv(out/"EUR48_CAPACITY_SCORECARD.csv")
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        year=year,leaves=LEAVES,source_v2_train_params=k.COMPACT_PARAMS,
        three_original_seeds=S,original_V3_127_head_exact_replay=True,
        same_125_europe_features=True,training_cutoff=str(cut.date()),
        train_signals=tr.signal_date.nunique(),train_rows=len(tr),
        latest_train_exit=str(tr.exit_date_21.max().date()),
        no_meta_model=True,no_risk_layer=True,
        historic_already_used_for_research=True,
        explanatory_ablation_not_new_model_selection=True,
        production_changed=False),indent=2,default=str))
    print("EU48_LEAF_AUDIT_SUCCESS",year,flush=True)
    print(summ.to_string(),flush=True)
if __name__=="__main__":main()
