#!/usr/bin/env python3
"""EU120 FULL REFIT: original 125-feature rankers and 42-feature MA3 Hybrid on frozen new universe.

No model is copied from 149 ETF training; price downloads forbidden. All five
candidate policies use identical cross-market common-open execution engine.
"""
from __future__ import annotations
import argparse,hashlib,json,os,subprocess,sys
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker

REPO=Path(__file__).resolve().parents[1]
ROOT=REPO.parent
sys.path.insert(0,str(ROOT/"europe120/eu120_retrain"))
sys.path.insert(0,str(ROOT/"vendor/etf_trader_v2/src"))
import run_eu120_retrain as eu
import replay_audited as au
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from paper_ltr_v2.replay import sha

SEEDS=(101,202,303)
CUTOFF=pd.Timestamp("2026-07-01")
FIRST=pd.Timestamp("2017-01-31")
LAST=pd.Timestamp("2026-06-30")
VARIANTS=("B_ONLY","R_ONLY","H_ONLY","B_H","R_H")

def stable_rank(s,dates):
    f=pd.DataFrame(dict(date=dates,score=s))
    return f.groupby("date",sort=False).score.rank(method="average",pct=True).to_numpy(float)

def feature_matrix(frame):
    x=frame[list(k.F2D_FEATURES)].to_numpy(dtype=float)
    if x.shape[1]!=125:raise ValueError("Expected original 125 Compact21 features")
    x[~np.isfinite(x)]=np.nan
    return x

def annual_fold_compact(comp,year,output):
    cutoff=pd.Timestamp(year,1,1)
    tr=comp[(comp.signal_date<cutoff)&(comp.exit_date_21<cutoff)&
        comp.target_rank_pct.notna()&comp.fwd_ret_21.notna()].copy()
    tr=tr[tr[list(k.F2D_FEATURES)].notna().sum(axis=1)>=30]
    tr=tr.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    te=comp[comp.signal_date.dt.year.eq(year)&comp.signal_date.between(FIRST,LAST)].copy()
    te=te.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    eligible=te[list(k.F2D_FEATURES)].notna().sum(axis=1)>=30
    out=te[["signal_date","ticker"]].copy()
    out["B_RAW"]=np.nan;out["R_RAW"]=np.nan
    if tr.signal_date.nunique()<60 or int(eligible.sum())<20:
        raise ValueError(f"Incomplete EU120 annual Compact21 fit {year}")
    if not (tr.exit_date_21<cutoff).all():raise ValueError("Leaked 21-session label")
    g=tr.groupby("signal_date",sort=True).size().to_numpy(int)
    if len(tr)!=g.sum() or any(n<2 for n in g):raise ValueError("Invalid training query structure")
    xtr=feature_matrix(tr);xte=feature_matrix(te.loc[eligible].copy())
    ranklabel=np.clip(np.rint(tr.target_rank_pct.to_numpy(float)*100),0,100).astype(int)
    # Reproduce the frozen RETURN_RANK_NDCG graded target exactly.
    actual=tr.fwd_ret_21.to_numpy(float)
    graded=np.empty(len(tr),dtype=int);start=0
    for n in g:
        a=slice(start,start+n);v=actual[a]
        spread=max(float(np.quantile(v,.9)-np.quantile(v,.1)),1e-6)
        graded[a]=np.rint(7.5+7.5*np.clip((v-np.median(v))/spread,-1.,1.)).astype(int)
        start+=n
    if np.any((graded<0)|(graded>15)):raise ValueError("Invalid return-aware relevance")
    cfg=dict(k.COMPACT_PARAMS)
    expected=dict(objective="rank:pairwise",n_estimators=360,max_depth=4,
        learning_rate=.035,subsample=.85,colsample_bytree=.8,
        min_child_weight=8.,reg_lambda=8.,reg_alpha=.1,tree_method="hist")
    if any(cfg.get(key)!=v for key,v in expected.items()) or tuple(k.COMPACT_SEEDS)!=SEEDS:
        raise ValueError("Frozen Compact21 architecture/seed drift")
    preds={}
    for name,y in (("B",ranklabel),("R",graded)):
        opts=cfg.copy()
        if name=="R":
            opts.update(objective="rank:ndcg",ndcg_exp_gain=False,
                lambdarank_pair_method="topk",lambdarank_num_pair_per_sample=5,eval_metric="ndcg@5")
        opts["n_jobs"]=2
        values=[]
        for seed in SEEDS:
            model=XGBRanker(**opts,random_state=seed)
            model.fit(xtr,y,group=g.tolist(),verbose=False)
            values.append(model.predict(xte))
        vals=np.mean(np.vstack(values),axis=0)
        if len(vals)!=int(eligible.sum()) or not np.isfinite(vals).all():
            raise ValueError("Invalid EU120 predicted score")
        out.loc[eligible,name+"_RAW"]=vals
    audit=dict(year=year,cutoff=str(cutoff.date()),
        train_rows=len(tr),train_months=int(tr.signal_date.nunique()),
        latest_training_label_exit=str(tr.exit_date_21.max().date()),
        training_feature_sha256=hashlib.sha256(np.nan_to_num(xtr,nan=-999.).tobytes()).hexdigest(),
        native_NaN_train_rows=int(np.isnan(xtr).any(axis=1).sum()),
        train_labels_BASE_sha256=hashlib.sha256(ranklabel.tobytes()).hexdigest(),
        train_labels_RETURN_sha256=hashlib.sha256(graded.tobytes()).hexdigest(),
        test_rows=len(te),eligible_test_rows=int(eligible.sum()),
        methods=["rank:pairwise","rank:ndcg"],seeds=list(SEEDS),
        lookahead_guard_PASS=bool(tr.exit_date_21.max()<cutoff))
    return out,audit

def calculate_scores(compact,hybrid,calendar,tickers):
    dates=pd.DatetimeIndex(calendar.signal_date)
    expected=pd.MultiIndex.from_product([dates,tickers],names=["signal_date","ticker"])
    a=compact.set_index(["signal_date","ticker"]).reindex(expected)
    b=hybrid.set_index(["signal_date","ticker"]).reindex(expected)
    for name in ("B_RAW","R_RAW"):
        if name not in a:raise ValueError("Missing learned Compact score "+name)
    vals={}
    for letter in ("B","R"):
        series=a[letter+"_RAW"]
        ranks=series.groupby(level=0,sort=True).rank(method="average",pct=True)
        vals[letter]=ranks.to_numpy(float).reshape(len(dates),len(tickers))
    et=b.ET_RANK.to_numpy(float).reshape(len(dates),len(tickers))
    xb=b.XGB_RANK.to_numpy(float).reshape(len(dates),len(tickers))
    if not np.isfinite(et).all() or not np.isfinite(xb).all():
        raise ValueError("Incomplete independently retrained 42-feature Hybrid Tail scores")
    h=.6*et+.4*xb
    prev=np.concatenate([h[0:1],h[:-1]],axis=0)
    prev2=np.concatenate([h[0:1],h[0:1],h[:-2]],axis=0)
    smooth=.4*h+.3*prev+.3*prev2
    hybrid_score=np.power(np.clip(smooth,0,1),1.1)
    scores={
        "B_ONLY":vals["B"],
        "R_ONLY":vals["R"],
        "H_ONLY":hybrid_score,
        "B_H":.475*vals["B"]+.525*hybrid_score,
        "R_H":.475*vals["R"]+.525*hybrid_score}
    pm=dict(ET_RANK=et,XGB_RANK=xb)
    if any(x.shape!=(len(dates),len(tickers)) for x in scores.values()):
        raise ValueError("Unexpected score support")
    if not np.isfinite(scores["H_ONLY"]).all():raise ValueError("Tail-only missing")
    return scores,pm

def monthly_quality(score,cal,tickers,full_labels,name):
    rows=[];l=full_labels.copy()
    l["signal_date"]=pd.to_datetime(l.signal_date)
    for index,signal in enumerate(pd.DatetimeIndex(cal.signal_date)):
        g=l[l.signal_date.eq(signal)].set_index("ticker")
        if g.empty:raise ValueError(f"Missing labeled EU120 month {signal}")
        order=np.argsort(-np.where(np.isfinite(score[index]),score[index],-1e6),kind="stable")
        selection=[tickers[i] for i in order[:5] if np.isfinite(score[index,i])]
        if len(selection)<5:raise ValueError("Fewer than five model-eligible EU120 ETFs")
        row=dict(variant=name,signal_date=str(signal.date()),selected_top1=selection[0],
            eligible_ETFs=int(np.isfinite(score[index]).sum()))
        ex=g.loc[selection[0],"exit_date_21"]
        mature=pd.notna(ex) and pd.Timestamp(ex)<=CUTOFF
        row["mature"]=bool(mature)
        if mature:
            realized=g.fwd_ret_21.dropna().astype(float)
            if not np.isfinite(realized.loc[selection]).all() or len(realized)<20:
                raise ValueError("Mature EU120 target incomplete")
            actual_best=realized.nlargest(5)
            x=float(realized.loc[selection[0]])
            row.update(chosen_return_21d=x,
                regret_to_topdecile=float(realized.nlargest(max(1,int(np.ceil(len(realized)/10)))).mean()-x),
                exact_best_hit=int(selection[0]==realized.idxmax()),
                top5_hit=int(selection[0] in actual_best.index),
                top5_overlap=len(set(selection)&set(actual_best.index))/5,
                mature_tickers=len(realized))
        rows.append(row)
    return rows

def fixed_5050_common_open(score,calendar,tickers,prices):
    equity=1.;last_weights={};months=0
    dates=pd.DatetimeIndex(calendar.signal_date)
    for m,row in enumerate(calendar.itertuples(index=False)):
        selected=[tickers[j] for j in np.argsort(
            -np.where(np.isfinite(score[m]),score[m],-1e6),kind="stable")[:2]]
        if not all(np.isfinite(score[m,tickers.index(t)]) for t in selected):
            raise ValueError("50/50 selected an ineligible ETF")
        start=pd.Timestamp(row.entry_date);end=pd.Timestamp(row.exit_date)
        if start not in prices.index or end not in prices.index:
            raise ValueError("No synchronized open for 50/50 monthly ETF basket")
        opening=prices.loc[start,selected].to_numpy(float)
        closing=prices.loc[end,selected].to_numpy(float)
        if not np.isfinite(opening).all() or not np.isfinite(closing).all() or np.any(opening<=0):
            raise ValueError("Missing frozen common open for top-two trade")
        w={str(t):.5 for t in selected}
        turnover=.5*sum(abs(w.get(t,0)-last_weights.get(t,0)) for t in set(w)|set(last_weights))
        equity*=float(np.mean(closing/opening))*(1.-0.001*turnover)
        last_weights=w;months+=1
    if months!=len(dates):raise ValueError("Incomplete simple fixed portfolio")
    return dict(terminal_equity=float(equity),periods=months,
        cagr=float(equity**(12/months)-1),turnover_fee_one_way=.001)

def main():
    p=argparse.ArgumentParser()
    for key in ("raw149","out"):p.add_argument("--"+key,required=True)
    args=p.parse_args()
    out=Path(args.out)
    if out.exists() and any(out.iterdir()):raise ValueError("Fresh output required")
    out.mkdir(parents=True)
    frozen=ROOT/"data/eu120"
    manifest=json.loads((frozen/"manifest.json").read_text())
    universe=pd.read_csv(frozen/"raw_ticker_csv/universe.csv")
    target=pd.read_csv(ROOT/"europe120/eu120_retrain/UNIVERSE_120.csv")
    if manifest.get("selected_count")!=120 or len(universe)!=120 or len(target)!=120:
        raise ValueError("Frozen EU120 120-member gate failed")
    if set(target.ticker)!=set(universe.ticker) or len(set(target.ticker))!=120:
        raise ValueError("EU120 chosen universe differs from frozen raw")
    if manifest.get("original149_overlap")!=0:raise ValueError("Original149 overlap")
    if any(not (frozen/"raw_ticker_csv"/(str(t)+".csv")).exists() for t in target.ticker):
        raise ValueError("Missing source ticker frozen CSV")
    refs=pd.DataFrame({"ticker":eu.REF_TICKERS,
        "macro_category":["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"]})
    scratch=out/"working"
    raw120=scratch/"raw120";rawref=scratch/"rawref";paneldir=scratch/"ma3_panel"
    os.environ["FROZEN_EU120_ROOT"]=str(frozen)
    os.environ["FROZEN_149_ROOT"]=str(Path(args.raw149))
    eu.download_folder(target,raw120)
    eu.download_folder(refs,rawref)
    e=os.environ.copy();e["PYTHONPATH"]=str(ROOT/"vendor/etf_trader_v2/src")
    subprocess.run([sys.executable,str(ROOT/"europe120/eu120_retrain/build_ma3_panel_causal.py"),
                    "--data",str(raw120),"--output",str(paneldir)],
                   cwd=ROOT/"vendor/etf_trader_v2",env=e,check=True)
    train_panel=pd.read_pickle(paneldir/"RAW_FEATURE_PANEL.pkl")
    for name in ("signal_date","exit_date_63"):
        train_panel[name]=pd.to_datetime(train_panel[name])
    cand_mats,cats,dates,compact,tail=eu.build_titanium_parts(
        raw120,market_spy_raw=rawref,candidates=target.ticker.astype(str).tolist())
    labeled_compact,labeled_tail,_,_=eu.add_train_labels(compact,tail,cand_mats,dates)
    for col in ("signal_date","exit_date_21"):
        labeled_compact[col]=pd.to_datetime(labeled_compact[col])
    signal_days=sorted(set(labeled_compact.signal_date))
    signal_days=[d for d in signal_days if FIRST<=pd.Timestamp(d)<=LAST]
    signal_idx=pd.DatetimeIndex(signal_days)
    if len(signal_idx)<110 or len(signal_idx)>114:raise ValueError("Unexpected EU120 annual walk-forward decision dates")
    models=out/"models";models.mkdir();(models/"hybrid").mkdir()
    predicted=[];hybrid_preds=[];audits=[]
    for year in range(2017,2027):
        pred,audit=annual_fold_compact(labeled_compact,year,models)
        predicted.append(pred)
        cutoff=pd.Timestamp(year,1,1)
        target_dates=signal_idx[signal_idx.year==year]
        train_only=train_panel[(train_panel.signal_date<cutoff)&(train_panel.exit_date_63<cutoff)]
        if train_only.empty or not (train_only.exit_date_63<cutoff).all():
            raise ValueError("MA3 Target63 cutoff missing")
        hybrid=eu.fit_ma3_one(train_panel,train_panel,cutoff,target_dates,
            f"EU120_A{year}",models/"hybrid")
        if hybrid.signal_date.nunique()!=len(target_dates):
            raise ValueError(f"Missing annual EU120 Hybrid Tail dates {year}")
        hybrid_preds.append(hybrid)
        audit.update(ma3_train_rows=int(len(train_only)),ma3_train_months=int(train_only.signal_date.nunique()),
            ma3_latest_exit=str(train_only.exit_date_63.max().date()),
            hybrid_test_rows=int(len(hybrid)))
        audits.append(audit)
        print("EU120_REFIT_FOLD "+json.dumps(audit),flush=True)
    cp=pd.concat(predicted,ignore_index=True)
    hp=pd.concat(hybrid_preds,ignore_index=True)
    cp.to_parquet(out/"COMPACT_REFITTED.parquet",index=False)
    hp.to_parquet(out/"HYBRID_REFITTED.parquet",index=False)
    pd.DataFrame(audits).to_csv(out/"TRAINING_AUDIT.csv",index=False)
    cand,_,_=load_ticker_csv_folder(raw120)
    refm,_,_=load_ticker_csv_folder(rawref)
    tickers=target.ticker.astype(str).tolist()
    combined_open=pd.concat([cand["Open"][tickers],refm["Open"][eu.REF_TICKERS]],axis=1).sort_index()
    cal=au.common_calendar(combined_open,signal_idx)
    if not 108<=len(cal)<=113:raise ValueError(f"Unexpected shared-market completed periods {len(cal)}")
    cp=cp[cp.signal_date.isin(cal.signal_date)]
    hp=hp[hp.signal_date.isin(cal.signal_date)]
    scores,pm=calculate_scores(cp,hp,cal,tickers)
    for name,score in scores.items():
        vals=dict(variant=name,nan_scores=int(np.isnan(score).sum()),
            min_available=int(np.isfinite(score).sum(axis=1).min()),
            max_available=int(np.isfinite(score).sum(axis=1).max()))
        print("EU120_SCORE "+json.dumps(vals),flush=True)
        if vals["min_available"]<5:raise ValueError("Fewer than five eligible ETFs")
    quality=[];economics=[];annual=[]
    for name,score in scores.items():
        quality.extend(monthly_quality(score,cal,tickers,labeled_compact,name))
        diagnostic=fixed_5050_common_open(score,cal,tickers,cand["Open"].reindex(columns=tickers))
        fixed.append(dict(variant=name,**diagnostic))
        original_daily_state=au.m.daily_state
        try:
            if name.endswith("_ONLY") and name!="H_ONLY":
                def no_hybrid_agreement(sc,pr,cl,ds,bm,bok):
                    return np.zeros((len(bm),len(ds)),dtype=bool)
                au.m.daily_state=no_hybrid_agreement
            result,E,T,ds=au.replay(score,pm,cal,cand,refm,tickers)
        finally:
            au.m.daily_state=original_daily_state
        if len(E)!=len(ds) or len(ds)<2200 or not np.isfinite(E).all() or np.any(E<=0):
            raise ValueError("Replay equity invalid")
        path=out/(name+"_EQUITY.npz")
        np.savez_compressed(path,equity=E,turnover=T,dates=ds.values)
        for year in range(2017,2027):
            mask=ds.year==year
            if mask.any():
                rets=np.diff(np.log(np.r_[1.,E]))
                annual.append(dict(variant=name,year=year,sessions=int(mask.sum()),
                    return_pct=100*float(np.expm1(rets[mask].sum()))))
        economics.append(dict(variant=name,**result,
            sessions=len(ds),signals=len(cal),min_eligible=int(np.isfinite(score).sum(axis=1).min()),
            max_eligible=int(np.isfinite(score).sum(axis=1).max())))
        print("EU120_AUDITED_V2 "+json.dumps(economics[-1]),flush=True)
    pd.DataFrame(quality).to_csv(out/"MONTHLY_QUALITY.csv",index=False)
    pd.DataFrame(fixed).to_csv(out/"FIXED_5050.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"ANNUAL_RETURN.csv",index=False)
    pd.DataFrame(economics).to_csv(out/"ECONOMICS.csv",index=False)
    outcome=dict(status="EU120_REFITTED_5_POLICY_COMMON_OPEN_COMPLETE",
        universe_count=120,point_in_time_universe_integrity="FAIL_ex_post_2026_07_01_selection",
        eur_quoted_universe_verified=False,
        original149_candidate_overlap=0,
        annual_fold_count=10,compact_seed_models_fit=60,
        hybrid_annual_model_fits=20,
        completed_months=len(cal),
        source_frozen_manifest_sha256=sha(frozen/"manifest.json"),
        original_frozen_provenance_sha256=sha(frozen/"PROVENANCE.json"),
        eu120_universe_sha256=sha(frozen/"raw_ticker_csv/universe.csv"),
        source_reference_run=36551650325,
        original_source=36597035280,
        end_cutoff=str(CUTOFF.date()),variants=VARIANTS,
        economics=economics,fixed_5050=fixed,
        training_guard_ALL_PASS=all(a["lookahead_guard_PASS"] for a in audits),
        no_model_reused_from_original149=True,
        no_production_change=True,
        research_historical_not_prospective=True,
        notes="Same EU120 frozen vintage for every policy, no independent new market; common-open audited execution.")
    (out/"RESULT.json").write_text(json.dumps(outcome,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:outcome[key] for key in ("status","economics","training_guard_ALL_PASS")},indent=2),flush=True)

if __name__=="__main__":main()
