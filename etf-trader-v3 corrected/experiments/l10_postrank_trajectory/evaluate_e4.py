#!/usr/bin/env python3
"""L10.E4: strictly prior-year OOT Platt calibration of frozen E3 probabilities.

Original CORRECTED ranking is NEVER changed globally. A rank4+ candidate
may replace only an E1-flagged Top3 incumbent, in its original weight slot,
if the past-only conditional pairwise confidence exceeds a frozen 0.70.
Already-explored history, research only. Do not tune on 2018-26.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
WEIGHT=np.array([0.5,0.3,0.2])
F=["mom21","mom63","draw63","efficiency21","downvol63","accel21"]
N_FEATURES=7
THRESHOLD=.70

def feat_matrices(close):
    log=np.log(close.where(close>0))
    ret=log.diff()
    mom21=log-log.shift(21)
    mom63=log-log.shift(63)
    draw63=close/close.rolling(63,min_periods=63).max()-1
    gross=ret.abs().rolling(21,min_periods=21).sum()
    eff=mom21.abs()/gross.where(gross>1e-12)
    down=np.sqrt(ret.clip(upper=0).pow(2).rolling(63,min_periods=63).mean())
    accel=mom21-(log.shift(21)-log.shift(42))
    mats=dict(mom21=mom21,mom63=mom63,draw63=draw63,
              efficiency21=eff,downvol63=down,accel21=accel)
    flag=(mom21<0)&(draw63<=-.10)
    assert len(mats)==6
    return mats,flag

def test_prefix():
    d=pd.bdate_range("2019-01-01",periods=270)
    k=np.arange(len(d),dtype=float)
    c=pd.DataFrame({"SPY":100*np.exp(.00015*k+.07*np.sin(.05*k)),
                   "AAA":82*np.exp(-.00028*k+.05*np.cos(.09*k))},index=d)
    t=d[220]
    a,f=feat_matrices(c)
    v=c.copy();v.loc[d[221]:,"AAA"]*=1.8
    b,g=feat_matrices(v)
    for key in F:
        np.testing.assert_allclose(a[key].loc[t],b[key].loc[t],
                                   atol=1e-12,rtol=0,equal_nan=True)
    assert f.loc[t].equals(g.loc[t])
    return True

def boot_delta(df,left,right,repeat=6000,width=6):
    d=(df[left]-df[right]).to_numpy(float)
    assert len(d)==101 and np.isfinite(d).all()
    n=len(d);rng=np.random.default_rng(20261022)
    start=rng.integers(0,n,size=(repeat,math.ceil(n/width)))
    ix=((start[:,:,None]+np.arange(width))%n).reshape(repeat,-1)[:,:n]
    b=d[ix].mean(axis=1)
    return dict(trial=left,reference=right,delta=float(d.mean()),
                low=float(np.quantile(b,.025)),high=float(np.quantile(b,.975)),
                months=n)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--scores",required=True)
    ap.add_argument("--baskets",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--e3-pairs",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert test_prefix()
    assert hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest()==SHA
    sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
    from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
    mats,cats,rawmanifest=load_ticker_csv_folder(args.raw)
    assert len(cats)==149
    close=mats["Close"].sort_index()
    feature_matrix,warning=feat_matrices(close)
    calendar=list(close.index)
    calmap={pd.Timestamp(date):i for i,date in enumerate(calendar)}
    membership=pd.read_csv(args.baskets);membership.ticker=membership.ticker.astype(str).str.upper()
    baskets=[g.ticker.tolist() for _,g in membership.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(baskets)==500 and all(len(b)==24 for b in baskets)
    ref=pd.read_csv(args.scores,parse_dates=["signal_date"])
    ref=ref.loc[ref.variant.eq("CORRECTED"),["signal_date","ticker","pred","fwd_ret_21"]].copy()
    ref.ticker=ref.ticker.astype(str).str.upper()
    assert len(ref)==15198 and ref.signal_date.nunique()==102 and ref.ticker.nunique()==149
    assert not ref.duplicated(["signal_date","ticker"]).any()
    # First pass: all prospective pair features/labels are computed in separate
    # columns. ONLY earlier matured label rows can be used in an annual fit.
    states=[]
    allpairs={}
    for date,group in ref.groupby("signal_date",sort=True):
        group=group.sort_values("ticker").reset_index(drop=True)
        if group.fwd_ret_21.isna().any():
            assert group.fwd_ret_21.isna().all()
            continue
        assert len(group)==149
        date=pd.Timestamp(date);tickers=group.ticker.tolist()
        today_index=calmap.get(date)
        if today_index is None or today_index+22>=len(calendar):
            raise RuntimeError("Missing strict 21-trading-day label maturity calendar "+str(date))
        label_exit=pd.Timestamp(calendar[today_index+22])
        fid={t:i for i,t in enumerate(tickers)}
        ix=np.array([[fid[t] for t in row] for row in baskets],int)
        pred=group.pred.rank(pct=True,method="average").to_numpy(float)
        y=group.fwd_ret_21.to_numpy(float)
        vals={k:feature_matrix[k].loc[date,tickers].to_numpy(float) for k in F}
        e1=warning.loc[date,tickers].to_numpy(bool)
        for k in F:
            if not np.isfinite(vals[k]).all():raise ValueError("NONFINITE "+str(date)+" "+k)
        width={k:max(float(np.percentile(vals[k],75)-np.percentile(vals[k],25)),1e-4) for k in F}
        ranked=pred[ix]
        order=np.argsort(-ranked,axis=1,kind="stable")
        proposed=[]
        for j in range(500):
            base=[int(k) for k in order[j,:3]]
            used=set(base)
            event=[]
            for slot,old in enumerate(base):
                if not e1[ix[j,old]]:continue
                for alternative in order[j,3:]:
                    alternative=int(alternative)
                    if alternative in used or e1[ix[j,alternative]]:continue
                    used.add(alternative)
                    inc=int(ix[j,old]);alt=int(ix[j,alternative])
                    key=(str(date.date()),tickers[inc],tickers[alt])
                    if key not in allpairs:
                        delta=[float(np.clip((vals[k][alt]-vals[k][inc])/width[k],-5,5)) for k in F]
                        delta.append(float(pred[alt]-pred[inc]))
                        assert len(delta)==N_FEATURES and np.isfinite(delta).all()
                        allpairs[key]={
                          "signal_date":date,"exit_date21":label_exit,
                          "incumbent":tickers[inc],"challenger":tickers[alt],
                          "features":delta,"label":int(y[alt]-y[inc]>=.01),
                          "ret_advantage_AUDIT_ONLY":float(y[alt]-y[inc]),
                        }
                    event.append({"slot":slot,"old":old,"alt":alternative,"pair_key":key})
                    break
            proposed.append(event)
        states.append(dict(date=date,ix=ix,y=y,pred=pred,proposed=proposed,
                           e1=e1,tickers=tickers,calendar_exit=label_exit))
    assert len(states)==101 and len(allpairs)>0
    monthdates=sorted({r["signal_date"] for r in allpairs.values()})
    # Some months have zero E1 warnings: no candidate pairs is legitimate abstention.
    assert len(monthdates)>=18
    # Exact original E3 OOT pair predictions; NEVER refit its classifier.
    history=pd.read_csv(args.e3_pairs,parse_dates=["signal_date","label_exit21"])
    assert len(history)==18218
    assert not history.duplicated(["signal_date","incumbent","challenger"]).any()
    e3prob={}
    for rec in history.itertuples(index=False):
        key=(str(rec.signal_date.date()),str(rec.incumbent),str(rec.challenger))
        assert key in allpairs,("unmatched original frozen pair",key)
        ground=allpairs[key]
        assert ground["label"]==int(rec.future_challenger_beats_by_1pct_AUDIT_ONLY)
        assert abs(ground["ret_advantage_AUDIT_ONLY"]-float(rec.future_relative_return_AUDIT_ONLY))<1e-12
        assert ground["exit_date21"]==rec.label_exit21
        prob=float(rec.pred_prob_higher_by_1pct) if pd.notna(rec.pred_prob_higher_by_1pct) else None
        if prob is not None:
            assert 0<prob<1 and bool(rec.model_fitted)
        else:assert not bool(rec.model_fitted)
        e3prob[key]=prob
    assert len(e3prob)==len(allpairs)==18218
    fit_by_year={};audits=[]
    for year in sorted({st["date"].year for st in states}):
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        keys=[k for k,z in allpairs.items() if e3prob[k] is not None
              and z["signal_date"]<cutoff and z["exit_date21"]<cutoff]
        dates=sorted({allpairs[k]["signal_date"] for k in keys})
        target=np.array([allpairs[k]["label"] for k in keys],int)
        sufficient=len(dates)>=8 and len(keys)>=300 and len(set(target))==2
        model=None;coef=None;intercept=None;reason="insufficient_past_mature_OOT"
        if sufficient:
            pp=np.clip(np.array([e3prob[k] for k in keys],float),1e-6,1-1e-6)
            xx=np.log(pp/(1-pp)).reshape(-1,1)
            counts=pd.Series([allpairs[k]["signal_date"] for k in keys]).value_counts()
            sw=np.array([1/counts[allpairs[k]["signal_date"]] for k in keys],float)
            sw*=len(sw)/sw.sum()
            model=LogisticRegression(C=1.,max_iter=2000,random_state=20261022)
            model.fit(xx,target,sample_weight=sw)
            coef=float(model.coef_[0,0]);intercept=float(model.intercept_[0])
            if coef<=0:
                model=None;reason="nonpositive_sigmoid_slope_abstain"
            else:reason="trained_on_past_year_OOT_pairs"
        fit_by_year[year]=model
        audits.append({"year":year,"annual_cutoff":str(cutoff.date()),
          "n_training_oos_mature_pair_observations":len(keys),
          "n_training_oos_mature_months":len(dates),
          "last_label_exit":str(max((allpairs[k]["exit_date21"] for k in keys)).date()) if keys else None,
          "all_labels_mature_pre_cutoff":all(allpairs[k]["exit_date21"]<cutoff for k in keys),
          "class1_rate":float(target.mean()) if len(target) else None,
          "fitted":model is not None,"calibration_slope":coef,"calibration_intercept":intercept,
          "reason":reason})
    assert all(d["all_labels_mature_pre_cutoff"] for d in audits)
    raw_yearly=[];cal_yearly=[]
    monthly=[];events=[];all_pred=[]
    for state in states:
        date=state["date"];year=date.year
        model=fit_by_year[year]
        unique_keys=sorted({e["pair_key"] for row in state["proposed"] for e in row})
        probs={}
        active=[k for k in unique_keys if e3prob[k] is not None]
        if model is not None and active:
            pp=np.clip(np.array([e3prob[k] for k in active],float),1e-6,1-1e-6)
            x=np.log(pp/(1-pp)).reshape(-1,1)
            probs=dict(zip(active,model.predict_proba(x)[:,1]))
        if active:
            target=np.array([allpairs[k]["label"] for k in active],int)
            source=np.array([e3prob[k] for k in active],float)
            raw_yearly.append({"year":year,"signal_date":str(date.date()),"pairs":len(active),
                "brier":float(brier_score_loss(target,source)),
                "raw_mean_pred":float(source.mean()),"observed_event_rate":float(target.mean())})
            evaluated=[k for k in active if k in probs]
            if evaluated:
                yy=np.array([allpairs[k]["label"] for k in evaluated],int)
                before=np.array([e3prob[k] for k in evaluated],float)
                after=np.array([probs[k] for k in evaluated],float)
                cal_yearly.append({"year":year,"signal_date":str(date.date()),"pairs":len(evaluated),
                    "calibrated_brier":float(brier_score_loss(yy,after)),
                    "raw_brier_same_pairs":float(brier_score_loss(yy,before)),
                    "calibrated_mean_prob":float(after.mean()),
                    "raw_mean_prob":float(before.mean()),"observed_event_rate":float(yy.mean())})
        for key in unique_keys:
            z=allpairs[key]
            all_pred.append({
                "signal_date":str(date.date()),"year":year,
                "incumbent":z["incumbent"],"challenger":z["challenger"],
                "label_exit21":str(z["exit_date21"].date()),
                "future_challenger_beats_by_1pct_AUDIT_ONLY":z["label"],
                "future_relative_return_AUDIT_ONLY":z["ret_advantage_AUDIT_ONLY"],
                "e3_raw_probability":e3prob[key],
                "e4_calibrated_probability":float(probs[key]) if key in probs else None,
                "veto_probability_threshold":THRESHOLD,
                "past_annual_calibration_fitted":model is not None})
        iy=state["ix"];y=state["y"];pred=state["pred"]
        basket_y=y[iy];ranked=pred[iy]
        order=np.argsort(-ranked,axis=1,kind="stable")
        future_order=np.argsort(-basket_y,axis=1,kind="stable")
        future_quality=np.empty_like(basket_y)
        future_quality[np.arange(500)[:,None],future_order]=np.linspace(1,0,24)
        future_best=np.argmax(basket_y,axis=1)
        m=[]
        for j in range(500):
            base=[int(k) for k in order[j,:3]]
            e1=base.copy();e3_edited=base.copy();edited=base.copy()
            change_count=0
            veto_true_win_weight=0.; veto_loss10_weight=0.; incoming_loss10_weight=0.
            for proposal in state["proposed"][j]:
                slot=proposal["slot"];alt=proposal["alt"];old=proposal["old"]
                assert base[slot]==old
                e1[slot]=alt
                baseprob=e3prob[proposal["pair_key"]]
                if baseprob is not None and baseprob>=THRESHOLD:e3_edited[slot]=alt
                prob=probs.get(proposal["pair_key"])
                if prob is None or prob<THRESHOLD:continue
                edited[slot]=alt
                change_count+=1
                veto_true_win_weight+=WEIGHT[slot]*int(old==future_best[j])
                veto_loss10_weight+=WEIGHT[slot]*int(basket_y[j,old]<=-.1)
                incoming_loss10_weight+=WEIGHT[slot]*int(basket_y[j,alt]<=-.1)
                events.append({"signal_date":str(date.date()),"basket":j,"slot":slot+1,
                     "incumbent":state["tickers"][int(iy[j,old])],
                     "challenger":state["tickers"][int(iy[j,alt])],
                     "calibrated_probability":float(prob),
                     "original_e3_probability":float(baseprob),
                     "future_incumbent_return_AUDIT_ONLY":float(basket_y[j,old]),
                     "future_challenger_return_AUDIT_ONLY":float(basket_y[j,alt])})
            assert len(set(edited))==3 and len(set(e1))==3 and len(set(e3_edited))==3
            worst3=set(int(i) for i in future_order[j,-3:])
            row={"changed":float(change_count>0),"n_changes":change_count,
                 "weight_vetoed_true_winner":veto_true_win_weight,
                 "loss10_weight_removed":veto_loss10_weight,
                 "loss10_weight_incoming":incoming_loss10_weight,
                 "suggested":len(state["proposed"][j])}
            for tag,picked in [("BASE",base),("E1",e1),("E3",e3_edited),("E4",edited)]:
                p=np.array(picked,int)
                rr=basket_y[j,p]
                row[tag+"_winner_hit"]=float(future_best[j] in p)
                row[tag+"_winner_weight"]=float(WEIGHT@np.array([int(t==future_best[j]) for t in p]))
                row[tag+"_loss10_weight"]=float(WEIGHT@(rr<=-.1))
                row[tag+"_weighted_rank"]=float(WEIGHT@future_quality[j,p])
                row[tag+"_return21"]=float(WEIGHT@rr)
                row[tag+"_regret21"]=float(np.max(basket_y[j])-WEIGHT@rr)
                row[tag+"_bottom3_weight"]=float(WEIGHT@np.array([int(t in worst3) for t in p]))
            m.append(row)
        q=pd.DataFrame(m)
        data=dict(signal_date=str(date.date()),year=year,n_baskets=500,
                  trained=int(model is not None),n_unique_pairs=len(unique_keys))
        data.update({k:float(q[k].mean()) for k in q.columns})
        monthly.append(data)
    results=pd.DataFrame(monthly).sort_values("signal_date").reset_index(drop=True)
    assert len(results)==101 and all(results.n_baskets.eq(500))
    # Fail fast: recomputed original BASE / E1 / E3 reference parity.
    expected={
        "BASE_winner_hit":.3547128712871288,
        "E1_winner_hit":.2927128712871287,
        "BASE_loss10_weight":.0848613861386138,
        "E1_loss10_weight":.0678336633663366,
        "BASE_winner_weight":.1258178217821782,
        "E1_winner_weight":.1018257425742574,
        "E3_winner_hit":.3533267326732673,
        "E3_loss10_weight":.0840257425742574}
    for k,v in expected.items():
        actual=results[k].mean()
        if not np.isclose(actual,v,atol=1e-10,rtol=0):
            raise AssertionError("BASE/E1 parity failure "+k+" "+str(actual)+" "+str(v))
    measure=["winner_hit","winner_weight","loss10_weight","weighted_rank",
             "return21","regret21","bottom3_weight"]
    b=[]
    for m in measure:
        for comparator in ["BASE","E3"]:
            b.append(boot_delta(results,"E4_"+m,comparator+"_"+m))
    results.to_csv(out/"MONTHLY.csv",index=False)
    results.groupby("year").mean(numeric_only=True).to_csv(out/"YEARLY.csv")
    pd.DataFrame(b).to_csv(out/"BOOTSTRAP.csv",index=False)
    pd.DataFrame(all_pred).to_csv(out/"PAIR_MODEL_PREDICTION_AUDIT.csv",index=False)
    pd.DataFrame(events).to_csv(out/"SUBSTITUTIONS.csv",index=False)
    pd.DataFrame(audits).to_csv(out/"CALIBRATION_FIT_AUDIT.csv",index=False)
    pd.DataFrame(raw_yearly).to_csv(out/"E3_RAW_CALIBRATION_BY_MONTH.csv",index=False)
    pd.DataFrame(cal_yearly).to_csv(out/"E4_CALIBRATION_BY_MONTH.csv",index=False)
    pd.DataFrame([{"metric":c,"mean":float(results[c].mean())}
                  for c in results.select_dtypes(include="number").columns]).to_csv(
                  out/"SUMMARY.csv",index=False)
    manifest=dict(status="L10.E4 research, no promotion before acceptance",
             underlying_frozen_raw_run=39482809691,frozen_scores_run=39700865721,
             frozen_e3_run=39752940429,
             original_rank="CORRECTED Pairwise127",
             original_E3_pair_predictions_unchanged=True,
             n_etfs=149,n_baskets=500,n_months=101,basket_sha256=SHA,
             calibrator="annual sigmoid logistic C=1, input logit of frozen E3 OOT probability",
             minimum_prior_months=8,minimum_prior_unique_pairs=300,
             entire_E3_pair_audit_reproduced=len(e3prob)==18218,
             full_label_maturity_gate=all(a["all_labels_mature_pre_cutoff"] for a in audits),
             no_future_feature_and_prefix_pass=True,
             E3_and_E1_metrics_reproduced=True,
             threshold=.70,refit_original_E3_model=False,
             n_unique_pairs=len(allpairs),n_E4_changed_basket_slots=len(events),
             slot_weights=[float(w) for w in WEIGHT],
             no_CAGR_tuning=True,nonvirgin_reused_history=True,production_unchanged=True)
    (out/"MANIFEST.json").write_text(json.dumps(manifest,indent=2)+"\n")
    print("E4_CALIBRATION_FIT_AUDIT",pd.DataFrame(audits).to_string(index=False),flush=True)
    print("E4_SUMMARY",pd.read_csv(out/"SUMMARY.csv").to_string(index=False),flush=True)
    print("E4_BOOTSTRAP",pd.DataFrame(b).to_string(index=False),flush=True)
    print("E4_MANIFEST",json.dumps(manifest),flush=True)

if __name__=="__main__":
    main()
