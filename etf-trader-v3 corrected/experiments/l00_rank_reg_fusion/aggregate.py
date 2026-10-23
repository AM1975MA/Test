#!/usr/bin/env python3
"""Matched, calendar-block evaluation of two head types and causal basket fusion.

The 500 baskets overlap extensively: all bootstrap draws use calendar months,
never independently resampled ETF or basket observations.
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pandas as pd

ARMS_FEATURE=("CS_ADD250_MINMAX","CS_ADD250_ROBUST",
              "VOL_TREND_RESID","VOL_MARKET_RESID")
ARMS_REG=("REG_REL125","REG_REL101","REG_ABS125","REG_ABS101","REG_HUBER125")
FUSION_ARMS=("F1_TOP5_REL125","F2_GATE_REL125","F3_BLEND_REL125",
             "F3_BLEND_REL101","F3_BLEND_ABS125","F4_CAUSAL_BLEND_REL125")
ALPHAS=(0.0,0.25,0.5,0.75,1.0)

def read_shards(root, mode):
    scores, months, audits = [], [], []
    for shard in ("s1","s2","s3"):
        folder=Path(root)/mode/shard
        scores.append(pd.read_csv(folder/"OOS_SCORES.csv",parse_dates=["signal_date"]))
        months.append(pd.read_csv(folder/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"]))
        audits.extend(json.loads((folder/"FIT_AUDIT.json").read_text()))
    s=pd.concat(scores,ignore_index=True);m=pd.concat(months,ignore_index=True)
    assert not s.duplicated(["variant","signal_date","ticker"]).any(),mode
    assert not m.duplicated(["variant","signal_date"]).any(),mode
    assert set(s.variant)==({"CORRECTED"}|set(ARMS_FEATURE if mode=="feature" else ARMS_REG))
    assert set(m.variant)==set(s.variant)
    ctrl=m[m.variant=="CORRECTED"].sort_values("signal_date").reset_index(drop=True)
    assert len(ctrl)==101, ("MONTH_COUNT",mode,len(ctrl))
    for arm in sorted(set(s.variant)-{"CORRECTED"}):
        v=m[m.variant==arm].sort_values("signal_date").reset_index(drop=True)
        assert v.signal_date.equals(ctrl.signal_date),arm
        assert v.n_baskets.equals(ctrl.n_baskets),arm
        assert v.n_tickers.equals(ctrl.n_tickers),arm
    return s,m,audits

def metric_for_order(order,y):
    n=len(y)
    trueorder=np.argsort(-y,kind="stable")
    relevance=np.empty(n,dtype=float)
    relevance[trueorder]=np.linspace(1,0,n)
    top=order[:min(3,n)]
    discount=1/np.log2(np.arange(2,len(top)+2))
    ideal=np.sort(relevance)[::-1][:len(top)]
    ndcg=float(np.dot(relevance[top],discount)/np.dot(ideal,discount))
    winner=int(np.argmax(y))
    picked=int(order[0])
    return (float(winner==picked),float(winner in top),ndcg,
            float(y.max()-y[picked]),float(y[picked]-y.mean()),
            float(y[picked]<=-0.10),picked)

def causal_fusion(scores, membership):
    wide=scores.pivot(index=["signal_date","ticker"],columns="variant",values="pred")
    targets=scores[scores.variant=="CORRECTED"].set_index(["signal_date","ticker"]).fwd_ret_21
    wide=wide.join(targets,how="inner")
    assert wide.index.is_unique
    assert set(ARMS_FEATURE+ARMS_REG+("CORRECTED",)) <= set(wide)
    months, corrections=[],[]
    # One learned weight per decision date, fitted exclusively on >=60-day-old
    # matured earlier OOS prediction/realization aggregates.
    hist=[]
    for dt,frame in wide.groupby(level=0,sort=True):
        d=pd.Timestamp(dt)
        g=frame.reset_index(level=0,drop=True)
        g=g.dropna(subset=["fwd_ret_21","CORRECTED"]).sort_index()
        lookup={t:i for i,t in enumerate(g.index)}
        mat=g[["CORRECTED","REG_REL125","REG_REL101","REG_ABS125"]].to_numpy(float)
        assert np.isfinite(mat).all()
        pcts=pd.DataFrame(mat,columns=["base","rel","novol","abs"]).rank(pct=True).to_numpy(float)
        y=g.fwd_ret_21.to_numpy(float)
        before=[h for h in hist if (d-h[0]).days>=60]
        trailing=before[-36:]
        alpha=max(ALPHAS,key=lambda a:(np.mean([h[1][a] for h in trailing]), -abs(a-.75))) if len(trailing)>=24 else 0.75
        vals={v:[] for v in ("CORRECTED",)+FUSION_ARMS}
        alpha_scores={a:[] for a in ALPHAS}
        changed={v:[0,0,0] for v in FUSION_ARMS}
        for basket_id,names in membership.items():
            ids=np.array([lookup[t] for t in names if t in lookup],dtype=int)
            if len(ids)<2: continue
            yy=y[ids]
            bp,rp,np_,ap=pcts[ids].T
            # Consistent tie breaking: the input ticker index was sorted.
            original=np.argsort(-bp,kind="stable")
            candidate=original[:min(5,len(original))]
            f1=np.concatenate((candidate[np.argsort(-rp[candidate],kind="stable")], original[len(candidate):]))
            if rp[original[0]] < np.median(rp[candidate]):
                chosen=int(candidate[np.argmax(rp[candidate])])
                f2=np.concatenate(([chosen], original[original!=chosen]))
            else:
                f2=original
            f3=np.argsort(-(.75*bp+.25*rp),kind="stable")
            f3_nv=np.argsort(-(.75*bp+.25*np_),kind="stable")
            f3_abs=np.argsort(-(.75*bp+.25*ap),kind="stable")
            f4=np.argsort(-(alpha*bp+(1-alpha)*rp),kind="stable")
            ords={"CORRECTED":original,"F1_TOP5_REL125":f1,
                  "F2_GATE_REL125":f2,"F3_BLEND_REL125":f3,
                  "F3_BLEND_REL101":f3_nv,"F3_BLEND_ABS125":f3_abs,
                  "F4_CAUSAL_BLEND_REL125":f4}
            base_r=metric_for_order(original,yy)
            for key,order in ords.items():
                m=metric_for_order(order,yy)
                vals[key].append(m[:6])
                if key!="CORRECTED" and order[0]!=original[0]:
                    changed[key][0]+=1
                    changed[key][1]+=int(yy[order[0]]>yy[original[0]])
                    changed[key][2]+=int(yy[order[0]]<yy[original[0]])
            for a in ALPHAS:
                order=np.argsort(-(a*bp+(1-a)*rp),kind="stable")
                alpha_scores[a].append(metric_for_order(order,yy)[4])
        assert all(len(v)>0 for v in vals.values()),d
        hist.append((d,{a:float(np.mean(v)) for a,v in alpha_scores.items()}))
        for key,metric in vals.items():
            x=np.array(metric,float)
            rows={"variant":key,"signal_date":d,"year":d.year,
                  "n_baskets":len(metric),"basket_top1":x[:,0].mean(),
                  "basket_top3":x[:,1].mean(),"basket_ndcg3":x[:,2].mean(),
                  "basket_regret":x[:,3].mean(),
                  "basket_selected_excess":x[:,4].mean(),
                  "basket_loss10_top1":x[:,5].mean(),
                  "causal_alpha_rank":alpha if key=="F4_CAUSAL_BLEND_REL125" else np.nan,
                  "alpha_train_history_months":len(trailing) if key=="F4_CAUSAL_BLEND_REL125" else np.nan}
            months.append(rows)
        for key,counts in changed.items():
            corrections.append(dict(signal_date=d,variant=key,
                n_baskets=len(vals[key]),changed=counts[0],
                changes_better=counts[1],changes_worse=counts[2]))
        print("FUSION_EVALUATED",str(d.date()),"calibrated_alpha",alpha,"history",len(trailing),flush=True)
    m=pd.DataFrame(months);c=pd.DataFrame(corrections)
    # Compare exact basket membership/counts with original frozen baseline.
    counts=m.pivot(index="signal_date",columns="variant",values="n_baskets")
    assert (counts.nunique(axis=1)==1).all()
    return m,c

def block_bootstrap(monthly, baseline, metrics, n=2500, seed=231026):
    rng=np.random.default_rng(seed)
    results=[]
    ref=monthly[monthly.variant==baseline].set_index("signal_date").sort_index()
    for arm in sorted(set(monthly.variant)-{baseline}):
        test=monthly[monthly.variant==arm].set_index("signal_date").sort_index()
        assert test.index.equals(ref.index)
        nmonths=len(ref)
        for metric in metrics:
            delta=(test[metric]-ref[metric]).to_numpy(float)
            assert np.isfinite(delta).all(),(arm,metric)
            reps=np.empty(n)
            for i in range(n):
                starts=rng.integers(0,nmonths,size=(nmonths+5)//6)
                sample=np.concatenate([(np.arange(6)+s)%nmonths for s in starts])[:nmonths]
                reps[i]=delta[sample].mean()
            results.append(dict(variant=arm,metric=metric,estimate=delta.mean(),
                                ci025=np.quantile(reps,.025),ci975=np.quantile(reps,.975),
                                months=nmonths,block_length=6,bootstrap_draws=n))
    return pd.DataFrame(results)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",required=True)
    p.add_argument("--membership",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    fs,fm,fa=read_shards(a.root,"feature")
    rs,rm,ra=read_shards(a.root,"regression")
    fbase=fs[fs.variant=="CORRECTED"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    rbase=rs[rs.variant=="CORRECTED"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(fbase[["signal_date","ticker","fwd_ret_21","pred"]],
                                  rbase[["signal_date","ticker","fwd_ret_21","pred"]])
    scores=pd.concat((fs,rs[rs.variant!="CORRECTED"]),ignore_index=True)
    assert not scores.duplicated(["variant","signal_date","ticker"]).any()
    membership_df=pd.read_csv(a.membership)
    assert set(membership_df.columns)=={"basket","ticker"}
    assert membership_df.basket.nunique()==500
    assert (membership_df.groupby("basket").size()==24).all()
    membership={int(i):list(g.ticker) for i,g in membership_df.groupby("basket",sort=True)}
    fusion,corr=causal_fusion(scores,membership)
    assert fusion.signal_date.nunique()==101
    m=pd.concat([fm,rm[rm.variant!="CORRECTED"],fusion[fusion.variant!="CORRECTED"]],ignore_index=True)
    assert not m.duplicated(["variant","signal_date"]).any()
    score_metrics=["basket_top1","basket_top3","basket_ndcg3","basket_regret","basket_selected_excess"]
    baseline=fm[fm.variant=="CORRECTED"].sort_values("signal_date")
    matched_fusion=fusion[fusion.variant=="CORRECTED"].sort_values("signal_date")
    assert np.allclose(baseline[score_metrics],matched_fusion[score_metrics],atol=1e-11,rtol=0), "FUSION_BASELINE_MISMATCH"
    boot=block_bootstrap(m,"CORRECTED",score_metrics)
    monthly_summary=m.groupby("variant")[score_metrics].mean()
    monthly_summary.insert(0,"months",m.groupby("variant").size())
    monthly_summary.to_csv(out/"SUMMARY.csv")
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    boot.to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    yearly=m.groupby(["variant","year"])[score_metrics].mean().reset_index()
    yearly.to_csv(out/"YEARLY.csv",index=False)
    corr.to_csv(out/"FUSION_CORRECTIONS.csv",index=False)
    fusion.to_csv(out/"FUSION_MONTHLY.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(fa+ra,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "research_only":True,"months":101,"etfs":149,"baskets":500,
        "mature_train_only":True,"seeds":[101,202,303],
        "calendar_block_bootstrap_months":6,"not_virgin_holdout":True,
        "sources":["39482809691","39515716383"],"fusions":list(FUSION_ARMS),
        "causal_alpha_train_only_min_months":24,
        "causal_alpha_maturity_lag_calendar_days":60,
        "production_modified":False},indent=2))
    print("COMPLETE_RESULTS\n",monthly_summary.to_string(),flush=True)

if __name__=="__main__":
    main()
