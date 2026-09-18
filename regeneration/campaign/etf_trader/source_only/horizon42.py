"""Source-only horizon family: H21 baseline, H42 challenger, and multi-horizon ensemble.

No historical scores/selections are consumed. Every annual model is fitted on
rows whose label exit date is strictly before the January-1 fit cutoff.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from xgboost import XGBRanker


def fit_predict(k, compact, tail, macro, mfeatures, extra, out, years=range(2017,2027)):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    frame=compact.merge(extra,on=["signal_date","ticker"],validate="one_to_one")
    predictions=[]; audit=[]
    for year in years:
        cached=out/f"scores_{year}.csv"
        cutoff=pd.Timestamp(year,1,1)
        valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
        te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(["signal_date","ticker"])
        if te.empty:
            continue
        o=te[["signal_date","ticker","entry_date","exit_date"]].copy()

        for horizon in (21,42,63):
            target=f"target_rank_{horizon}"
            exit_col=f"exit_date_{horizon}"
            train=frame[
                (frame.signal_date<cutoff)
                &(frame[exit_col]<cutoff)
                &frame[target].notna()
                &valid
            ].sort_values(["signal_date","ticker"])
            if train.signal_date.nunique()<60:
                raise RuntimeError(f"insufficient training history for {year} H{horizon}")
            if not (train[exit_col]<cutoff).all():
                raise RuntimeError(f"label maturity violation {year} H{horizon}")
            y=(train[target]*100).round().astype(int)
            groups=train.groupby("signal_date",sort=True).size().to_numpy()
            pp=[]
            for seed in k.COMPACT_SEEDS:
                model=XGBRanker(**k.COMPACT_PARAMS,random_state=seed)
                model.fit(
                    train[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan),
                    y,group=groups,verbose=False
                )
                pp.append(model.predict(te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
            o[f"compact{horizon}"]=np.mean(pp,axis=0)
            audit.append({
                "year":year,"model":f"compact{horizon}","train_rows":len(train),
                "max_exit":str(train[exit_col].max()),"fit_date":str(cutoff),
                "maturity_safe":bool(train[exit_col].max()<cutoff),
            })

        tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tv]
        tte=tail[(tail.signal_date.dt.year==year)&tv]
        tm=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=30.))
        tm.fit(ttr[k.TAIL_FEATURES],ttr.y_tailmix)
        tp=tte[["signal_date","ticker"]].copy()
        tp["tail"]=tm.predict(tte[k.TAIL_FEATURES])
        o=o.merge(tp,on=["signal_date","ticker"],validate="one_to_one")

        mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year==year]
        mm=make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=50.))
        mm.fit(mtr[mfeatures],mtr.target_rank)
        q=mte[["signal_date","macro_category"]].copy()
        q["raw"]=mm.predict(mte[mfeatures])
        q["z"]=q.groupby("signal_date").raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
        rec=[]
        for dt,g in q.groupby("signal_date"):
            g=g.sort_values(["z","macro_category"],ascending=[False,True])
            rec.append({"signal_date":dt,"top_macro":g.iloc[0].macro_category,
                        "macro_gap":float(g.iloc[0].z-g.iloc[1].z)})
        o=o.merge(pd.DataFrame(rec),on="signal_date")
        o["macro_category"]=o.ticker.map(k.TICKER_CATEGORY)
        audit.extend([
            {"year":year,"model":"tail","max_exit":str(ttr.exit_date_63.max()),"fit_date":str(cutoff),
             "maturity_safe":bool(ttr.exit_date_63.max()<cutoff)},
            {"year":year,"model":"macro","max_exit":str(mtr.label_exit_date_63.max()),"fit_date":str(cutoff),
             "maturity_safe":bool(mtr.label_exit_date_63.max()<cutoff)},
        ])
        o.to_csv(cached,index=False)
        predictions.append(o)
        (out/f"fit_audit_{year}.json").write_text(
            json.dumps([a for a in audit if a["year"]==year],indent=2)+"\n"
        )
    return pd.concat(predictions,ignore_index=True)


def variants(pred):
    p=pred.copy()
    for col in ["compact21","compact42","compact63","tail"]:
        p[col]=p.groupby("signal_date")[col].rank(method="average",pct=True)

    condition=(p.macro_category==p.top_macro)&(p.macro_gap>=.75)
    bonus=.15*(condition&(p["tail"]>=.8))

    compact_tri=.60*p.compact21+.20*p.compact42+.20*p.compact63
    raw={
        "baseline":.70*p.compact21+.30*p["tail"]+bonus,
        "h42_tail":.70*p.compact42+.30*p["tail"]+bonus,
        "tri_60_20_20_tail":.70*compact_tri+.30*p["tail"]+bonus,
        "compact42_only":p.compact42,
    }
    panels={}
    for name,v in raw.items():
        q=p[["signal_date","ticker"]].copy()
        q["score"]=v.groupby(p.signal_date).rank(method="average",pct=True)
        panels[name]=q
    return panels
