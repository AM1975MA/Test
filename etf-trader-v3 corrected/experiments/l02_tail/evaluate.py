#!/usr/bin/env python3
"""V3 L02 Tail objective validation: exact 60 vs 45 unique Tail fields.

Competing arms differ ONLY by removal of 15 numerically identical aliases.
Same Ridge(alpha=30), median imputer, scaler, 63D mature targets, annual
prequential training, source, baskets, samples and signal dates.
No score fusion, Compact refit, regime, allocator, risk or CAGR.
"""
from __future__ import annotations
import argparse,json,sys,hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from sklearn.metrics import average_precision_score,roc_auc_score
from scipy.stats import spearmanr
HERE=Path(__file__).resolve().parent
V3=HERE.parents[1];ROOT=V3.parent
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only import kernel as k
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets

PAIR_ALIASES=(
 ("ma_gap200_rank","sma_ratio_200_rank"),
 ("downvol_21_rank","downvol21_rank"),
 ("vol_21_rank","vol21_rank"),
 ("vol126_rank","vol_126_rank"),
 ("vol63_rank","vol_63_rank"),
 ("downvol_63_rank","downvol63_rank"),
 ("ret_126_rank","mom126_rank"),
 ("mom21_rank","ret_21_rank"),
 ("kurt_63_rank","kurt63_rank"),
 ("sma_ratio_50_rank","ma_gap50_rank"),
 ("ret_63_rank","mom63_rank"),
 ("mom42_rank","ret_42_rank"),
 ("efficiency126_rank","eff_126_rank"),
 ("acc_21_63_broad_rank","acc_mom_21_63_rank"),
 ("mom_126_21_rank","mom126_ex21_rank"))
ALL60=k.TAIL_FEATURES
DROP={p[1] for p in PAIR_ALIASES}
UNIQUE45=[n for n in ALL60 if n not in DROP]
assert len(ALL60)==60 and len(UNIQUE45)==45 and len(DROP)==15

def read_original(raw,baskets):
    assert hashlib.sha256(Path(baskets).read_bytes()).hexdigest()==(
       "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e")
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149
    mats={f:x.loc[x.index>=pd.Timestamp("2011-01-01")] for f,x in mats.items()}
    bs=load_baskets(baskets,cats)
    assert len(bs)==500 and all(len(x)==24 for x in bs)
    k.ALL_TICKERS=sorted(cats)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c)
                        for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,_,tail,_=k.build_features(mats)
    tail=tail[tail.signal_date.isin(dates)].reset_index(drop=True)
    tail=k.add_labels(tail,mats["Open"],dates)
    assert not tail[["signal_date","ticker"]].duplicated().any()
    audit=[]
    for a,b in PAIR_ALIASES:
        left=tail[a].to_numpy(float);right=tail[b].to_numpy(float)
        same=np.isclose(left,right,rtol=0,atol=0,equal_nan=True)
        if not same.all():raise RuntimeError(f"Not an identical Tail alias: {a},{b}")
        audit.append({"canonical":a,"duplicate_removed":b,"exact_same":True,
                      "n_rows":len(left)})
    valid=tail[ALL60].notna().sum(axis=1)>=12
    assert valid.any()
    return tail,bs,valid,audit

def score_tail_month(g,baskets):
    g=g.dropna(subset=["pred","y_tailmix","fwd_ret_21"]).sort_values(
        ["pred","ticker"],ascending=[False,True])
    if len(g)<30:return None
    p=g.pred.to_numpy(float);y=g.y_tailmix.to_numpy(float)
    raw=g.fwd_ret_21.to_numpy(float)
    elites=y>=np.quantile(y,.9)
    if not np.any(elites) or np.all(elites):return None
    order=np.argsort(-p,kind="stable")
    chosen=set(order[:min(15,len(order))])
    top15_recall=float(np.sum(elites[list(chosen)])/np.sum(elites))
    top15_precision=float(np.mean(elites[list(chosen)]))
    ic=float(spearmanr(p,y).statistic) if np.unique(p).size>=4 else np.nan
    pr=float(average_precision_score(elites.astype(int),p))
    roc=float(roc_auc_score(elites.astype(int),p))
    lookup={name:i for i,name in enumerate(g.ticker)}
    z=[]
    for basket in baskets:
        ids=np.array([lookup[t] for t in basket if t in lookup],int)
        if len(ids)<2:continue
        pp=p[ids];yy=y[ids];rr=raw[ids]
        best=int(np.argmax(yy));selected=int(np.argmax(pp))
        top3=set(np.argsort(-pp,kind="stable")[:3])
        # Failure metric: selects a future 21-day bottom-decile ETF within basket.
        bottom=float(rr[selected]<=np.quantile(rr,.1))
        z.append((float(best==selected),float(best in top3),
                  float(yy.max()-yy[selected]),bottom))
    if not z:return None
    m=np.array(z,float)
    return {"signal_date":str(g.signal_date.iloc[0].date()),
            "year":int(g.signal_date.iloc[0].year),
            "n_tickers":len(g),"n_baskets":len(z),
            "tail_event_rate":float(np.mean(elites)),
            "tail_event_ap":pr,"tail_event_auc":roc,
            "tail_elite_recall_top15":top15_recall,
            "tail_elite_precision_top15":top15_precision,
            "tail_rank_ic":ic,
            "basket_tail_top1":float(m[:,0].mean()),
            "basket_tail_top3":float(m[:,1].mean()),
            "basket_tail_regret":float(m[:,2].mean()),
            "basket_bottom_decile_false_selection":float(m[:,3].mean())}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--years",default="2018,2019,2020")
    p.add_argument("--out",default="runs/v3_l02_tail")
    a=p.parse_args()
    years=[int(y) for y in a.years.split(",")]
    assert years and set(years)<=set(range(2018,2027))
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    tail,baskets,valid,duplicates=read_original(a.raw,a.baskets)
    (out/"DUPLICATE_ALIAS_AUDIT.json").write_text(json.dumps(duplicates,indent=2))
    records=[];scores=[];fits=[]
    for year in years:
        cutoff=pd.Timestamp(year,1,1)
        trmask=(tail.signal_date.ge(pd.Timestamp("2012-01-01"))&
            tail.signal_date.lt(cutoff)&tail.exit_date_63.lt(cutoff)&
            tail.y_tailmix.notna()&valid)
        temask=tail.signal_date.dt.year.eq(year)&valid
        tr=tail.loc[trmask].sort_values(["signal_date","ticker"])
        te=tail.loc[temask].sort_values(["signal_date","ticker"])
        assert tr.signal_date.nunique()>=50 and len(te)>0
        assert tr.exit_date_63.max()<cutoff
        for arm,fields in (("TAIL_FULL60",ALL60),("TAIL_DEDUP45",UNIQUE45)):
            model=make_pipeline(
                SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=30.))
            model.fit(tr[fields],tr.y_tailmix)
            frame=te[["signal_date","ticker","y_tailmix","fwd_ret_21"]].copy()
            frame["pred"]=model.predict(te[fields])
            frame.insert(0,"variant",arm)
            scores.append(frame)
            for _,g in frame.groupby("signal_date",sort=True):
                m=score_tail_month(g,baskets)
                if m is not None:records.append({"variant":arm,**m})
            fits.append({"variant":arm,"year":year,"features":fields,
                "n_features":len(fields),"max_mature_exit":str(tr.exit_date_63.max()),
                "train_dates":int(tr.signal_date.nunique()),"train_rows":len(tr),
                "test_rows":len(te),"model":"Ridge(alpha=30), median imputer, standard scaler",
                "layer_L01_ranker_untouched":True})
            print("V3_L02_FIT",year,arm,len(tr),len(te),flush=True)
    long=pd.concat(scores,ignore_index=True)
    monthly=pd.DataFrame(records)
    long["signal_date"]=pd.to_datetime(long.signal_date,format="mixed")
    monthly["signal_date"]=pd.to_datetime(monthly.signal_date,format="mixed")
    assert not long[["variant","signal_date","ticker"]].duplicated().any()
    assert not monthly[["variant","signal_date"]].duplicated().any()
    ref=monthly[monthly.variant=="TAIL_FULL60"].sort_values("signal_date").reset_index(drop=True)
    challenger=monthly[monthly.variant=="TAIL_DEDUP45"].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(ref.signal_date,challenger.signal_date)
    akey=long[long.variant=="TAIL_FULL60"].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    bkey=long[long.variant=="TAIL_DEDUP45"].sort_values(
        ["signal_date","ticker"]).reset_index(drop=True)
    pd.testing.assert_frame_equal(akey[["signal_date","ticker","y_tailmix"]],
                                  bkey[["signal_date","ticker","y_tailmix"]])
    monthly.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    long.to_csv(out/"OOS_SCORES.csv",index=False)
    summary=monthly.groupby("variant").mean(numeric_only=True).drop(columns=["year"],errors="ignore")
    summary.insert(0,"months",monthly.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    (out/"FIT_AUDIT.json").write_text(json.dumps(fits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L02 independent Tail",
        "arms":["TAIL_FULL60","TAIL_DEDUP45"],
        "only_change":"Remove 15 precisely verified duplicate Tail input aliases",
        "target":"tailmix = .6 rank21**4 + .25 rank42**4 + .15 rank63**4",
        "train_exit_maturity":"exit_date_63 < fit Jan1 cutoff",
        "evaluation_label":"same y_tailmix, same month/ETF universe",
        "no_cagr":True,"no_compact_retraining":True,
        "no_macro_blend_allocation_risk":True,
        "snapshot_run":39482809691,"historical_calendar_explored_not_virgin":True},indent=2))
    print("V3_L02_RESULTS\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
