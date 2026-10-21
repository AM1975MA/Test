#!/usr/bin/env python3
"""V3 L05.2: single, predeclared volatility-aware Top3 budget.

One policy change only: same 3 frozen Tail45 ETF selections and [0.5,.3,.2]
reference, use completed past-63-trading-session close-to-close log-return
volatility (minimum 21 returns), bounded multiplier [0.8,1.2]:
  w_new = normalize(base_w * clip((median_top3_vol/vol_i)**0.5,0.8,1.2)).
No fitted parameters or CAGR, no ETF replacement, no Tail, regime or risk head
refit; same original 500x24 and 101 matured forward-21D signal months.
Constituent-only vol score feature available at or before month-end.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np,pandas as pd

HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
BASE="TOP3_DECAY"
TEST="TOP3_VOL63_CAP20"
BASE_W=np.array([.5,.3,.2],float)
EXPO=.5
LOW=.8
HIGH=1.2
METRICS=["weighted_future_rank","future_bottom3_weight","weight_on_future_best",
 "future_abs_loss10_weight","weighted_oracle_regret21","target_weight_churn",
 "max_weight","effective_n_positions","weight_shift_half_L1"]

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--predictions",default="runs/v3_l04_reference/OOS_SCORES_ALL_FIXED_BLENDS.csv")
    p.add_argument("--prior",default="runs/v3_l05_reference")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l05_vol")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    raw=pd.read_csv(a.baskets);raw.ticker=raw.ticker.astype(str).str.upper()
    groups=[g.ticker.tolist() for _,g in raw.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(groups)==500 and all(len(x)==24 for x in groups)
    scores=pd.read_csv(a.predictions,parse_dates=["signal_date"])
    assert len(scores)==15198
    assert not scores.duplicated(["signal_date","ticker"]).any()
    mats,cats,_=load_ticker_csv_folder(a.raw)
    assert len(cats)==149
    close=mats["Close"].loc[mats["Close"].index>=pd.Timestamp("2011-01-01")]
    lr=np.log(close.where(close>0)).diff()
    vol=(lr.rolling(63,min_periods=21).std(ddof=0)*np.sqrt(252))
    # Vol is point-in-time and computed only through the selected signal close.
    if len(vol.index)<250:raise RuntimeError("Insufficient full raw history")
    prev={a:[None]*500 for a in [BASE,TEST]}
    rows=[];imputed=0;total_selected=0
    for dt,g in scores.groupby("signal_date",sort=True):
        if g.fwd_ret_21.isna().any():continue
        gg=g.sort_values("ticker").reset_index(drop=True)
        assert len(gg)==149
        if dt not in vol.index:raise RuntimeError(f"Signal date not in close panel: {dt}")
        vol_at=vol.loc[dt].reindex(gg.ticker).to_numpy(float)
        # ETF with insufficient 21 prior returns receives cross-market median
        # past-only volatility, not forward filled or a future observation.
        available=vol_at[np.isfinite(vol_at)&(vol_at>1e-8)]
        assert len(available)>=40
        fallback=float(np.median(available))
        invalid=~np.isfinite(vol_at)|(vol_at<=1e-8)
        imputed+=int(invalid.sum());total_selected+=len(vol_at)
        vol_at[invalid]=fallback
        y=gg.fwd_ret_21.to_numpy(float)
        score=gg.TAIL_ELITE45.to_numpy(float)
        where={t:i for i,t in enumerate(gg.ticker)}
        bypolicy={k:[] for k in [BASE,TEST]}
        for j,basket in enumerate(groups):
            index=np.array([where[t] for t in basket],int)
            yy=y[index];ss=score[index]
            order=np.argsort(-ss,kind="stable")
            chosen=order[:3];ids=index[chosen]
            rawv=vol_at[ids]
            mult=np.clip((np.median(rawv)/rawv)**EXPO,LOW,HIGH)
            updated=BASE_W*mult;updated/=updated.sum()
            assert np.isclose(updated.sum(),1) and np.all(updated>0)
            true=np.argsort(-yy,kind="stable")
            best=int(true[0]);bottom=set(true[-3:].tolist())
            quality=np.empty(24,float);quality[true]=np.linspace(1,0,24)
            for policy,w in [(BASE,BASE_W),(TEST,updated)]:
                positions={basket[int(chosen[k])]:float(w[k]) for k in range(3)}
                before=prev[policy][j]
                churn=np.nan if before is None else float(sum(abs(positions.get(t,0)-before.get(t,0))
                    for t in set(positions)|set(before))/2)
                prev[policy][j]=positions
                bypolicy[policy].append({
                    "weighted_future_rank":float(np.dot(w,quality[chosen])),
                    "future_bottom3_weight":float(sum(w[k] for k,id in enumerate(chosen) if int(id) in bottom)),
                    "weight_on_future_best":float(w[np.flatnonzero(chosen==best)[0]]) if best in chosen else 0.,
                    "future_abs_loss10_weight":float(sum(w[k] for k,id in enumerate(chosen) if yy[id]<=-.10)),
                    "weighted_oracle_regret21":float(yy.max()-np.dot(w,yy[chosen])),
                    "target_weight_churn":churn,"max_weight":float(w.max()),
                    "effective_n_positions":float(1/sum(w*w)),
                    "weight_shift_half_L1":float(np.abs(w-BASE_W).sum()/2)})
        for name,items in bypolicy.items():
            row=pd.DataFrame(items).mean(numeric_only=True,skipna=True).to_dict()
            rows.append({"variant":name,"signal_date":dt,"year":int(dt.year),**row})
    df=pd.DataFrame(rows)
    assert len(df)==101*2 and not df.duplicated(["variant","signal_date"]).any()
    base=df[df.variant==BASE].sort_values("signal_date").reset_index(drop=True)
    new=df[df.variant==TEST].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(base.signal_date,new.signal_date)
    old=pd.read_csv(Path(a.prior)/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    ref=old[old.variant==BASE].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(base.signal_date,ref.signal_date)
    for name,original in [("weighted_future_rank","weighted_true_rank_quality"),
                           ("future_bottom3_weight","bottom_three_weight"),
                           ("weight_on_future_best","weighted_winner_capture"),
                           ("weighted_oracle_regret21","weighted_oracle_regret21")]:
        if original in ref.columns:
            np.testing.assert_allclose(base[name],ref[original],rtol=0,atol=2e-12)
    summary=df.groupby("variant")[METRICS].mean()
    summary.insert(0,"months",df.groupby("variant").size())
    df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary.to_csv(out/"RESULTS.csv")
    df.groupby(["year","variant"],as_index=False)[METRICS].mean().to_csv(out/"YEARLY.csv",index=False)
    bs=[]
    for field in METRICS:
        d=(new[field]-base[field]).to_numpy(float)
        if field=="target_weight_churn":d=d[1:]
        assert np.isfinite(d).all()
        n=len(d);rng=np.random.default_rng(20261021);reps=5000;block=6
        start=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
        ind=((start[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
        x=d[ind].mean(axis=1)
        bs.append({"metric":field,"delta":float(d.mean()),
          "ci95_low":float(np.quantile(x,.025)),"ci95_high":float(np.quantile(x,.975))})
    pd.DataFrame(bs).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
     "layer":"L05.2 volatility diversification standalone", "source_raw":39482809691,
     "frozen_tail_source":39659903643,"frozen_selection_reference":39661273577,
     "volatility_lookback":63,"min_history":21,"capped_multiplier":[.8,1.2],
     "exponent":.5,"same_holdings_in_both_policies":True,
     "n_signal_months":101,"mean_missing_vol_fraction":imputed/total_selected,
     "costs_not_modeled_here":True,"no_CAGR":True,
     "holdout":"2018-26 already explored; exploratory"},indent=2))
    print("L05_VOL_RESULTS\n"+summary.to_string(),flush=True)

if __name__=="__main__":main()
