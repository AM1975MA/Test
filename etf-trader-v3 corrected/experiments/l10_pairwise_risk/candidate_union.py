#!/usr/bin/env python3
"""L10.C preregistered candidate-recall diagnostic; no training, no CAGR, no trading.
Frozen CORRECTED Top3 + distinct Top5 Top3 vs baseline Top3 plus equal count
of next-best CORRECTED names. Each 500-basket month contributes ONE data point.
"""
import argparse,hashlib,json,math
from pathlib import Path
import numpy as np,pandas as pd
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"

def boot(v,reps=6000,block=6):
    rng=np.random.default_rng(20261022);n=len(v)
    ix=((rng.integers(n,size=(reps,math.ceil(n/block)))[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    z=np.asarray(v)[ix].mean(axis=1)
    return dict(delta=float(np.mean(v)),ci95_low=float(np.quantile(z,.025)),ci95_high=float(np.quantile(z,.975)))

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--scores",required=True);a.add_argument("--baskets",required=True);a.add_argument("--out",required=True)
    a=a.parse_args();dst=Path(a.out);dst.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    b=pd.read_csv(a.baskets);b.ticker=b.ticker.astype(str).str.upper()
    bs=[g.ticker.tolist() for _,g in b.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(bs)==500 and all(len(q)==24 for q in bs)
    df=pd.read_csv(a.scores,parse_dates=["signal_date"])
    def read(name):
        f=df[df.variant.eq(name)][["signal_date","ticker","pred","fwd_ret_21"]].copy()
        assert len(f)==15198 and f.signal_date.nunique()==102
        assert not f.duplicated(["signal_date","ticker"]).any()
        return f
    old,new=read("CORRECTED"),read("L10_TOP5_PAIR127")
    months=[]
    for date in sorted(old.signal_date.unique()):
        x=old[old.signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        z=new[new.signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        assert len(x)==len(z)==149
        pd.testing.assert_series_equal(x.ticker,z.ticker)
        np.testing.assert_allclose(x.fwd_ret_21,z.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
        if x.fwd_ret_21.isna().any():
            assert x.fwd_ret_21.isna().all()
            continue
        lookup={k:i for i,k in enumerate(x.ticker)}
        ix=np.array([[lookup[t] for t in basket] for basket in bs])
        yy=x.fwd_ret_21.to_numpy(float)[ix]
        a1=x.pred.rank(method="average",pct=True).to_numpy(float)[ix]
        a2=z.pred.rank(method="average",pct=True).to_numpy(float)[ix]
        r1=np.argsort(-a1,axis=1,kind="stable")
        r2=np.argsort(-a2,axis=1,kind="stable")
        best=np.argmax(yy,axis=1)
        realized_order=np.argsort(-yy,axis=1,kind="stable")
        quality=np.empty_like(yy);quality[np.arange(500)[:,None],realized_order]=np.linspace(1,0,24)
        data=[]
        for j in range(500):
            base=[int(i) for i in r1[j,:3]]
            extra=[int(i) for i in r2[j,:3] if i not in base]
            match=[int(i) for i in r1[j,3:3+len(extra)]]
            assert len(set(base+extra))==len(set(base+match))==3+len(extra)
            winner=int(best[j]);bottom=set(map(int,realized_order[j,-3:]))
            def avg(items,fn):
                return float(np.mean([fn(i) for i in items])) if items else np.nan
            data.append({
                "baseline_recall":float(winner in base),
                "union_recall":float(winner in base+extra),
                "matched_recall":float(winner in base+match),
                "new_winner_recall":float(winner in extra),
                "matched_extra_winner_recall":float(winner in match),
                "added_count":len(extra),
                "new_loss10_fraction":avg(extra,lambda i:float(yy[j,i]<=-.10)),
                "matched_loss10_fraction":avg(match,lambda i:float(yy[j,i]<=-.10)),
                "new_rank_quality":avg(extra,lambda i:quality[j,i]),
                "matched_rank_quality":avg(match,lambda i:quality[j,i]),
                "new_21d_return":avg(extra,lambda i:yy[j,i]),
                "matched_21d_return":avg(match,lambda i:yy[j,i]),
                "new_bottom3_fraction":avg(extra,lambda i:float(i in bottom)),
                "matched_bottom3_fraction":avg(match,lambda i:float(i in bottom)),
            })
        frame=pd.DataFrame(data)
        item={"signal_date":str(pd.Timestamp(date).date()),"year":int(date.year),"n_baskets":500,"n_baskets_with_extra":int((frame.added_count>0).sum())}
        item.update({c:float(frame[c].mean()) for c in frame.columns})
        months.append(item)
    m=pd.DataFrame(months);assert len(m)==101
    m.to_csv(dst/"CANDIDATE_MONTHLY.csv",index=False)
    metrics=["baseline_recall","union_recall","matched_recall","added_count","new_loss10_fraction","matched_loss10_fraction","new_rank_quality","matched_rank_quality","new_21d_return","matched_21d_return","new_bottom3_fraction","matched_bottom3_fraction"]
    summary={c:float(m[c].mean()) for c in metrics}
    (dst/"CANDIDATE_SUMMARY.json").write_text(json.dumps(summary,indent=2))
    contrasts=[
        ("union_vs_matched_recall","union_recall","matched_recall"),
        ("union_vs_baseline_recall","union_recall","baseline_recall"),
        ("new_vs_matched_loss10","new_loss10_fraction","matched_loss10_fraction"),
        ("new_vs_matched_rank_quality","new_rank_quality","matched_rank_quality"),
        ("new_vs_matched_return21","new_21d_return","matched_21d_return"),
        ("new_vs_matched_bottom3","new_bottom3_fraction","matched_bottom3_fraction"),
    ]
    z=[]
    for label,tr,ct in contrasts:
        v=(m[tr]-m[ct]).to_numpy()
        assert np.isfinite(v).all()
        z.append({"contrast":label,**boot(v)})
    pd.DataFrame(z).to_csv(dst/"CANDIDATE_BOOTSTRAP.csv",index=False)
    m.groupby("year")[metrics].mean().to_csv(dst/"CANDIDATE_YEARLY.csv")
    (dst/"MANIFEST.json").write_text(json.dumps({
      "case":"L10.C", "frozen_model_source_run":39700865721,
      "baseline_model":"CORRECTED","proposal_model":"L10_TOP5_PAIR127",
      "ETF":149,"baskets":500,"mature_months":101,
      "matched_control":"CORRECTED Top3 plus same number next highest CORRECTED scores",
      "no_retraining_or_execution":True,"historical_reuse_not_virgin":True},indent=2))
    print("L10C_COMPLETE",json.dumps(summary),pd.DataFrame(z).to_string(index=False),flush=True)
if __name__=="__main__":main()
