#!/usr/bin/env python3
"""OASIS V2 G1: a causal, matched and PREQUENTIAL paired net-opportunity test.

No trading/backtest optimization here. Uses no existing LM scores.
All labels created from future OPENs for evaluation only. Every future
label admitted into learning must have matured BEFORE the next signal close.
"""
from __future__ import annotations
import argparse,hashlib,json,math
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd
from scipy.stats import t as student_t
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/"oasis150/results/frozen"
COST=.003
HORIZON=21
ANCHOR_STRIDE=21
SEED=20261018
FIRST_EVAL=pd.Timestamp("2021-01-01")
VARIANTS=("H0_PRIOR","H1_RAW_TREND","H2_GROUP_RESIDUAL","H3_HIERARCHICAL_REGIME","H4_STUDENT_T")
GROUPS=("C01_US_BROAD_STYLE","C02_US_SECTOR_THEME","C03_DEVELOPED_GLOBAL",
        "C04_EMERGING","C05_BONDS_CASH_CREDIT","C06_REAL_ASSETS")

def digest(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for z in iter(lambda:f.read(1024*1024),b""):h.update(z)
    return h.hexdigest()

def data_source():
    roster=pd.read_csv(P/"OASIS_TOP150.csv")
    assert len(roster)==150 and roster.ticker.nunique()==150
    close={};op={}
    for rec in roster.itertuples(index=False):
        path=ROOT/rec.source_path
        if digest(path)!=rec.source_sha256:raise AssertionError("ticker source changed "+rec.ticker)
        d=pd.read_csv(path,parse_dates=["date"]).set_index("date").sort_index()
        close[rec.ticker]=d.Close
        op[rec.ticker]=d.Open
    C=pd.concat(close,axis=1).reindex(columns=roster.ticker.tolist()).astype(float)
    O=pd.concat(op,axis=1).reindex(columns=roster.ticker.tolist()).astype(float)
    portfolio=pd.read_csv(P/"P3_OASIS_CRISIS_ACTIVE.csv",parse_dates=["day","signal_date"])
    assert len(portfolio)==2366
    assert (portfolio.signal_date<portfolio.day).all()
    assert all(x in C.index for x in portfolio.signal_date)
    assert all(x in O.index for x in portfolio.day)
    return roster,C,O,portfolio

def features(C,roster):
    lp=np.log(C.where(C>0))
    ret=lp.diff()
    groups={k:list(roster.loc[roster.macro_category==k,"ticker"]) for k in GROUPS}
    grpprice=pd.DataFrame(index=C.index)
    for k,members in groups.items():
        # Prior close group-factor *return*, not a future rebalanced fund.
        grpprice[k]=ret[members].mean(axis=1).fillna(0).cumsum()
    d={}
    for length in (5,10,21,63,126):
        d[f"r{length}"]=lp-lp.shift(length)
    for length in (5,21,63,126):
        baseline=pd.DataFrame({t:grpprice[k]-grpprice[k].shift(length)
            for k,members in groups.items() for t in members},index=C.index)
        baseline=baseline.reindex(columns=C.columns)
        d[f"res{length}"]=d[f"r{length}"]-baseline
    d["vol21"]=ret.rolling(21,min_periods=20).std()
    d["vol63"]=ret.rolling(63,min_periods=50).std()
    d["down63"]=(ret.clip(upper=0)**2).rolling(63,min_periods=50).mean().pow(.5)
    d["draw63"]=lp-lp.rolling(63,min_periods=50).max()
    d["accel"]=d["res5"]*4.2-d["res21"]
    d["volshock"]=d["vol21"]/d["vol63"].clip(lower=.0001)
    d["regime"]=(d["r21"].mean(axis=1)<0).astype(int)
    return d,ret

def vector_at(f,ret,signal,challenger,incumbent,catmap,regime):
    def delta(key):
        x=f[key].loc[signal]
        return float(x[challenger]-x[incumbent])
    raw=np.array([delta("r21"),delta("r63"),delta("r126")],float)
    residual=np.array([delta("res5"),delta("res21"),
        delta("res63"),delta("res126")],float)
    risk=np.array([delta("vol21"),delta("vol63"),
                   delta("down63"),delta("draw63"),
                   delta("accel"),delta("volshock")],float)
    diffgroup=np.array([(int(catmap[challenger]==k)-int(catmap[incumbent]==k))
                        for k in GROUPS],float)
    stressed=float(regime in ("SHOCK","CONTINUATION"))
    recovery=float(regime=="RECOVERY")
    b2=np.r_[raw,residual,risk]
    b3=np.r_[b2,diffgroup,
        residual[0]*stressed,residual[1]*stressed,
        risk[2]*stressed,risk[3]*stressed,
        residual[0]*recovery,residual[1]*recovery]
    # Independent Student-t generative model approximate expected relative
    # 21-session DRIFT, small shrink, no fitted future outcome.
    mu=.25*(.3*residual[1]+.7*residual[2]/3)
    spread=(ret[challenger]-ret[incumbent]).loc[:signal].dropna().tail(63)
    sig=float(spread.std(ddof=1))*math.sqrt(21) if len(spread)>=45 else math.nan
    tprob=float(student_t.sf((COST-mu)/max(sig,.002),df=5)) if math.isfinite(sig) else math.nan
    return raw,b2,b3,float(tprob),float(mu-COST)

def pair_catalog(roster,signal,holdings,features_dict,seed):
    names=roster.ticker.tolist()
    cats=roster.set_index("ticker").macro_category.to_dict()
    rng=np.random.default_rng(SEED+seed)
    entries=[]
    # Incumbent-centric, as-of candidate from simple raw 21d+63d trends;
    # never the prior OASIS model's prediction.
    r21=features_dict["r21"].loc[signal]
    r63=features_dict["r63"].loc[signal]
    screen=(.5*r21+.5*r63/3).dropna().sort_values(ascending=False)
    challengers=[t for t in screen.index if t not in holdings][:8]
    for incumb in holdings:
        for alt in challengers:
            if alt!=incumb:entries.append((alt,incumb,"challenge"))
    # Constant 64 deterministic random pair comparisons per anchor;
    # half within-group and half cross-group. Orientation is randomized.
    grouped={g:[t for t in names if cats[t]==g] for g in GROUPS}
    for p in range(64):
        g=str(rng.choice(GROUPS))
        x=str(rng.choice(grouped[g]))
        if p<32:
            y=str(rng.choice([t for t in grouped[g] if t!=x]))
        else:
            other=str(rng.choice([t for t in GROUPS if t!=g]))
            y=str(rng.choice(grouped[other]))
        if rng.integers(2):x,y=y,x
        entries.append((x,y,"probe"))
    return entries

def make_dataset(roster,C,O,portfolio):
    f,ret=features(C,roster)
    categories=roster.set_index("ticker").macro_category.to_dict()
    rows=[]
    for j in range(21,len(portfolio)-HORIZON,ANCHOR_STRIDE):
        s=pd.Timestamp(portfolio.signal_date.iloc[j])
        entry=pd.Timestamp(portfolio.day.iloc[j])
        exit_=pd.Timestamp(portfolio.day.iloc[j+HORIZON])
        assert s<entry<exit_
        held=[x for x in str(portfolio.names.iloc[j-1]).split(";") if x and x!="nan"]
        if len(held)!=2:continue
        cat=pair_catalog(roster,s,held,f,j)
        for a,b,kind in cat:
            if a==b:continue
            try:
                va,vb=C.loc[s,[a,b]].to_numpy(float)
                o0=O.loc[entry,[a,b]].to_numpy(float)
                o1=O.loc[exit_,[a,b]].to_numpy(float)
                if not (np.isfinite([va,vb,*o0,*o1]).all() and min(va,vb,*o0,*o1)>0):
                    continue
                raw,b2,b3,tprob,mu=vector_at(f,ret,s,a,b,categories,
                         str(portfolio.regime.iloc[j]))
                if not (np.isfinite(raw).all() and np.isfinite(b2).all()
                        and np.isfinite(b3).all() and np.isfinite(tprob)):
                    continue
                realized=math.log(o1[0]/o0[0])-math.log(o1[1]/o0[1])-COST
                rows.append(dict(anchor=j,signal=str(s.date()),entry=str(entry.date()),
                    label_matures=str(exit_.date()),pair_type=kind,asset=a,held=b,
                    source_group_a=categories[a],source_group_b=categories[b],
                    regime=str(portfolio.regime.iloc[j]),y=int(realized>0),
                    realized_net_relative_log=realized,
                    H0_PRIOR=np.nan,H4_STUDENT_T=tprob,
                    expected_gen_net=mu,
                    x1=raw.tolist(),x2=b2.tolist(),x3=b3.tolist()))
            except (KeyError,ValueError,OverflowError):continue
    dataset=pd.DataFrame(rows)
    assert dataset.anchor.nunique()>=75, "Not enough independent 21d anchor periods"
    assert all((pd.to_datetime(dataset.signal)<pd.to_datetime(dataset.entry))&
        (pd.to_datetime(dataset.entry)<pd.to_datetime(dataset.label_matures)))
    return dataset

def summarize(y,p):
    y=np.asarray(y,int);p=np.clip(np.asarray(p,float),.00001,.99999)
    if not len(y):return dict(n=0)
    b=float(np.mean((y-p)**2))
    ll=float(np.mean(-y*np.log(p)-(1-y)*np.log(1-p)))
    try:auc=float(roc_auc_score(y,p)) if len(np.unique(y))==2 else None
    except ValueError:auc=None
    return dict(n=int(len(y)),brier=b,log_loss=ll,auc=auc,
        observed_frequency=float(y.mean()),average_prediction=float(p.mean()),
        calibration_gap=float(abs(y.mean()-p.mean())))

def run_predictions(ds):
    ds=ds.copy()
    evalanchors=sorted(ds.loc[pd.to_datetime(ds.signal)>=FIRST_EVAL,"anchor"].unique())
    result=[]
    for anchor in evalanchors:
        test=ds[ds.anchor==anchor].copy()
        now=pd.Timestamp(test.signal.iloc[0])
        prior=ds[pd.to_datetime(ds.label_matures)<now].copy()
        # Training COMPLETED labels only; no immediate previous next-open outcome.
        if prior.anchor.nunique()<24:continue
        yy=prior.y.to_numpy(int)
        if len(np.unique(yy))<2:raise AssertionError("no training event variation")
        model_prob={}
        # Honest unconditional baseline per task type.
        priorfreq=prior.groupby("pair_type").y.mean().to_dict()
        model_prob["H0_PRIOR"]=test.pair_type.map(priorfreq).fillna(float(yy.mean())).clip(.10,.90).to_numpy(float)
        model_prob["H4_STUDENT_T"]=test.H4_STUDENT_T.to_numpy(float)
        for name,key,lam in (
              ("H1_RAW_TREND","x1",.15),
              ("H2_GROUP_RESIDUAL","x2",.15),
              ("H3_HIERARCHICAL_REGIME","x3",.08)):
            X=np.vstack(prior[key].to_list())
            Z=np.vstack(test[key].to_list())
            scale=StandardScaler()
            Xn=scale.fit_transform(X)
            Zn=scale.transform(Z)
            model=LogisticRegression(C=lam,solver="liblinear",
                 max_iter=400,random_state=SEED)
            # Equal total importance per prior anchor, not 80 correlated
            # pair observations acting as independent samples.
            ct=prior.groupby("anchor").anchor.transform("size").to_numpy(float)
            sw=len(prior)/len(prior.anchor.unique())/ct
            model.fit(Xn,yy,sample_weight=sw)
            model_prob[name]=model.predict_proba(Zn)[:,1]
        for k,val in model_prob.items():test[k]=np.asarray(val,float)
        test["matured_anchor_count"]=int(prior.anchor.nunique())
        test["latest_training_label_maturity"]=str(prior.label_matures.max())
        result.append(test)
        if len(result) in (1,10,40,60):
            print("G1_PREQUENTIAL_ANCHOR",len(result),str(now.date()),
                  "matured",prior.anchor.nunique(),"prob_H2",float(test.H2_GROUP_RESIDUAL.mean()),flush=True)
    if not result:raise AssertionError("No out-of-development prequential anchors")
    pred=pd.concat(result,ignore_index=True)
    assert (pd.to_datetime(pred.latest_training_label_maturity)<pd.to_datetime(pred.signal)).all()
    return pred

def bootstrap_anchor_brier(pred,reference="H0_PRIOR",N=1500):
    # Use every independent (non-overlapping 21-session) decision anchor as
    # the resampling unit; 3-anchor circular blocks for serial dependence.
    task=pred[pred.pair_type=="challenge"].copy()
    anchor=sorted(task.anchor.unique())
    n=len(anchor);rng=np.random.default_rng(SEED+1)
    errs={}
    for model in VARIANTS:
        groups=task.assign(err=(task.y-task[model])**2).groupby("anchor").err.mean()
        errs[model]=np.array([float(groups.loc[a]) for a in anchor])
    output={}
    for model in VARIANTS:
        if model==reference:continue
        diff=errs[reference]-errs[model]
        draws=[]
        for _ in range(N):
            indexes=[]
            while len(indexes)<n:
                start=int(rng.integers(0,n))
                indexes.extend((start+i)%n for i in range(3))
            draws.append(float(diff[np.asarray(indexes[:n],int)].mean()))
        output[model]=dict(mean_brier_reduction_vs_null=float(diff.mean()),
             ci95=np.quantile(draws,[.025,.975]).tolist(),n_anchors=n,
             frac_anchors_improved=float(np.mean(diff>0)))
    return output

def shadow_accepts(pred):
    decisions=[]
    for anchor,d in pred[pred.pair_type=="challenge"].groupby("anchor"):
        h0=float(d.H0_PRIOR.mean())
        # Use H2 only, precommitted; do not pick historical winner.
        eligible=d[(d.H2_GROUP_RESIDUAL>.65)&
                   (d.H2_GROUP_RESIDUAL>d.H0_PRIOR+.10)&
                   (d.expected_gen_net>0)]
        if eligible.empty:continue
        best=eligible.sort_values("H2_GROUP_RESIDUAL",ascending=False).iloc[0]
        decisions.append(dict(anchor=int(anchor),signal=best.signal,
            held=best.held,challenger=best.asset,
            p=float(best.H2_GROUP_RESIDUAL),
            p_null=float(best.H0_PRIOR),
            realized_net_relative_log=float(best.realized_net_relative_log)))
    return decisions

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True);args=parser.parse_args()
    dest=Path(args.out);dest.mkdir(parents=True,exist_ok=False)
    roster,C,O,port=data_source()
    ds=make_dataset(roster,C,O,port)
    predictions=run_predictions(ds)
    if predictions.anchor.nunique()<40:raise AssertionError("insufficient eval anchors")
    analysis={};per_era={}
    for task in ("challenge","probe"):
        x=predictions[predictions.pair_type==task]
        analysis[task]={m:summarize(x.y,x[m]) for m in VARIANTS}
        per_era[task]={}
        for title,mask in (("2021_2023",pd.to_datetime(x.signal).dt.year<=2023),
                           ("2024_2026",pd.to_datetime(x.signal).dt.year>=2024)):
            v=x[mask]
            per_era[task][title]={m:summarize(v.y,v[m]) for m in VARIANTS}
    shadow=shadow_accepts(predictions)
    target=analysis["challenge"];ci=bootstrap_anchor_brier(predictions)
    ok=all(target["H2_GROUP_RESIDUAL"][k]<target[control][k]
          for k in ("brier","log_loss")
          for control in ("H0_PRIOR","H1_RAW_TREND"))
    ok=bool(ok and ci["H2_GROUP_RESIDUAL"]["ci95"][0]>0 and all(
        per_era["challenge"][period]["H2_GROUP_RESIDUAL"]["brier"]<
        per_era["challenge"][period]["H0_PRIOR"]["brier"]
        for period in ("2021_2023","2024_2026")))
    shadow_values=[x["realized_net_relative_log"] for x in shadow]
    outcome=dict(status="PAIRED_PREQUENTIAL_G1_COMPLETED",gate_G1_primary="PASS" if ok else "FAIL",
       need_full_PIT_and_forward="YES",candidate_etfs=150,
       anchors_evaluated=int(predictions.anchor.nunique()),
       pair_rows=int(len(predictions)),past_data_source=39132785483,
       first_eval_anchor=str(predictions.signal.min()),last_eval_anchor=str(predictions.signal.max()),
       statistical_unit="chronological_nonoverlapping_21-session_anchor",
       asof_matured_label_invariant=True,
       ever_read_old_LM_predictions=False,
       hypotheses_frozen_before_evaluation=True,
       model_paired_economic_horizon_sessions=21,
       model_all_in_one_cost_hurdle_log=COST,
       uses_retrospective_survivor_universe=True,
       independent_test_data=False,
       scored_by_task=analysis,era_slices=per_era,
       primary_challenge_bootstrap=ci,
       shadow_H2_acceptance=dict(n=len(shadow),net_relative_log_mean=
         float(np.mean(shadow_values)) if shadow else None,
         net_relative_log_median=float(np.median(shadow_values)) if shadow else None,
         fraction_profitable=float(np.mean(np.array(shadow_values)>0)) if shadow else None,
         worst_log_relative=float(np.min(shadow_values)) if shadow else None,
         actions=shadow),
       source_roster_sha256=digest(P/"OASIS_TOP150.csv"),
       source_daily_portfolio_sha256=digest(P/"P3_OASIS_CRISIS_ACTIVE.csv"),
       caveats=["PIT/survivorship","same previously mined ETF sample",
                "shared pair labels dependent within anchor","unknown spreads","no live buy/sell",
                "no real prospective holdout"])
    predictions.to_csv(dest/"PREDICTIONS_FULL.csv",index=False)
    (dest/"RESULT.json").write_text(json.dumps(outcome,indent=2,allow_nan=False)+"\n")
    print("OASIS_G1_PAIRED_RESULT "+json.dumps(outcome,allow_nan=False),flush=True)

if __name__=="__main__":main()
