#!/usr/bin/env python3
"""L10.E2 coherence-confirmed post-ML trajectory audit, no ML re-ranking.

Frozen CORRECTED Top3 -> veto ONLY incumbents with last-21D negative momentum
AND >10% drawdown from rolling 63D high -> substitute first unflagged rank4+
name in the SAME original frozen CORRECTED ML ordering. Fixed 50/30/20 weights.
Outcomes are for evaluation only. Exploratory, reused 2018-2026; no CAGR.
"""
from __future__ import annotations
import argparse,hashlib,json,math,sys
from pathlib import Path
import numpy as np
import pandas as pd

SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
W=np.array([.5,.3,.2])
def calculate_trajectory(close):
    assert close.index.is_monotonic_increasing and close.index.is_unique
    mom=np.log(close/close.shift(21))
    max63=close.rolling(63,min_periods=63).max()
    draw=close/max63-1
    e1_flag=(mom<0)&(draw<=-.10)
    daily=np.log(close).diff()
    gross=daily.abs().rolling(21,min_periods=21).sum()
    efficiency=mom.abs()/gross.where(gross>1e-12)
    flag=e1_flag&(efficiency>=0.45)
    available=mom.notna()&draw.notna()
    assert not (flag&~e1_flag).any().any()
    return mom,draw,flag&available,available,efficiency,e1_flag&available

def test_no_forward_look():
    idx=pd.bdate_range("2020-01-01",periods=200)
    k=np.arange(len(idx),dtype=float)
    close=pd.DataFrame({"X":100*np.exp(-.0005*k+.01*np.sin(k*.2)),
                        "Y":70*np.exp(.0003*k+.01*np.cos(k*.19))},index=idx)
    t=idx[150]
    a=calculate_trajectory(close)
    modified=close.copy()
    modified.loc[idx[151]:,"X"]*=10
    modified.loc[idx[151]:,"Y"]*=0.1
    b=calculate_trajectory(modified)
    for i in [0,1,2,3,4,5]:
        if i in [0,1,4]:
            np.testing.assert_allclose(a[i].loc[t],b[i].loc[t],rtol=0,atol=1e-12,equal_nan=True)
        else:
            assert a[i].loc[t].equals(b[i].loc[t])
    return True

def monthly_block_delta(frame,trial,ref,reps=6000,block=6):
    d=(frame[trial]-frame[ref]).to_numpy(float)
    assert len(d)==101 and np.isfinite(d).all()
    rng=np.random.default_rng(20261022)
    starts=rng.integers(len(d),size=(reps,math.ceil(len(d)/block)))
    ind=((starts[:,:,None]+np.arange(block))%len(d)).reshape(reps,-1)[:,:len(d)]
    z=d[ind].mean(axis=1)
    return {"metric":trial.removeprefix("EDITED_"),"trial":trial,"control":ref,
      "delta":float(d.mean()),"ci95_low":float(np.quantile(z,.025)),
      "ci95_high":float(np.quantile(z,.975)),
      "months":len(d),"bootstrap_reps":reps,"block_months":block}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--scores",required=True)
    ap.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert test_no_forward_look()
    assert hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest()==SHA
    b=pd.read_csv(args.baskets)
    b.ticker=b.ticker.astype(str).str.upper()
    baskets=[g.ticker.tolist() for _,g in b.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(baskets)==500 and all(len(x)==24 for x in baskets)
    here=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(here/"src"))
    from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder
    mats,cats,manifest=load_ticker_csv_folder(args.raw)
    assert len(cats)==149
    close=mats["Close"].sort_index()
    mom,draw,flag,avail,coherence,e1flag=calculate_trajectory(close)
    raw_scores=pd.read_csv(args.scores,parse_dates=["signal_date"])
    scored=raw_scores.loc[raw_scores.variant.eq("CORRECTED"),
        ["signal_date","ticker","pred","fwd_ret_21"]].copy()
    scored.ticker=scored.ticker.astype(str).str.upper()
    assert len(scored)==15198 and scored.signal_date.nunique()==102
    assert scored.ticker.nunique()==149
    assert not scored.duplicated(["signal_date","ticker"]).any()
    monthly=[];audit=[];changes=[]
    for date in sorted(scored.signal_date.unique()):
        today=pd.Timestamp(date)
        rows=scored.loc[scored.signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        assert len(rows)==149 and not rows.pred.isna().any()
        if rows.fwd_ret_21.isna().any():
            assert rows.fwd_ret_21.isna().all()
            continue
        if today not in close.index:raise ValueError("MISSING_SIGNAL_PRICE_DATE:"+str(today))
        ticker=rows.ticker.tolist()
        observed_avail=avail.loc[today,ticker].to_numpy(bool)
        if not observed_avail.all():
            raise ValueError("MISSING_TRAJECTORY_HISTORY "+str(today)+" "+
                             str(np.array(ticker)[~observed_avail].tolist()))
        mm=mom.loc[today,ticker].to_numpy(float)
        dd=draw.loc[today,ticker].to_numpy(float)
        flags=flag.loc[today,ticker].to_numpy(bool)
        e1_flags=e1flag.loc[today,ticker].to_numpy(bool)
        eff=coherence.loc[today,ticker].to_numpy(float)
        assert np.isfinite(mm).all() and np.isfinite(dd).all()
        assert not np.any(flags&~e1_flags)
        y=rows.fwd_ret_21.to_numpy(float)
        pred=rows.pred.rank(method="average",pct=True).to_numpy(float)
        ind={v:i for i,v in enumerate(ticker)}
        basket_idx=np.array([[ind[t] for t in group] for group in baskets],dtype=int)
        yr=y[basket_idx];rank=pred[basket_idx];mask=flags[basket_idx]
        mask_e1=e1_flags[basket_idx]
        order=np.argsort(-rank,axis=1,kind="stable")
        ranks_fut=np.argsort(-yr,axis=1,kind="stable")
        quality=np.empty_like(yr)
        quality[np.arange(500)[:,None],ranks_fut]=np.linspace(1,0,24)
        future_best=np.argmax(yr,axis=1)
        unique_selection=set()
        month_data=[]
        for j in range(500):
            baseline=[int(v) for v in order[j,:3]]
            unique_selection.update(int(basket_idx[j,k]) for k in baseline)
            used=set(baseline)
            edited=list(baseline)
            replaced=[]
            for slot,old_pos in enumerate(baseline):
                if not mask[j,old_pos]:
                    continue
                # Only scan lower original ML ranking, never reorder untouched positions.
                for candidate in order[j,3:]:
                    candidate=int(candidate)
                    if candidate not in used and not mask[j,candidate]:
                        used.add(candidate)
                        edited[slot]=candidate
                        replaced.append((slot,old_pos,candidate))
                        break
            assert len(edited)==3 and len(set(edited))==3
            assert all((edited[k]==baseline[k]) or mask[j,baseline[k]] for k in range(3))
            e1_edited=list(baseline)
            e1_used=set(baseline)
            e1_replaced=[]
            for slot,old_pos in enumerate(baseline):
                if not mask_e1[j,old_pos]:
                    continue
                for candidate in order[j,3:]:
                    candidate=int(candidate)
                    if candidate not in e1_used and not mask_e1[j,candidate]:
                        e1_used.add(candidate)
                        e1_edited[slot]=candidate
                        e1_replaced.append((slot,old_pos,candidate))
                        break
            assert len(set(e1_edited))==3
            bottom=set(int(v) for v in ranks_fut[j,-3:])
            row={}
            for model,pick in [("BASE",baseline),("EDITED",edited),("E1",e1_edited)]:
                selected=np.array(pick,dtype=int)
                returns=yr[j,selected]
                row[model+"_loss10_weight"]=float(W@(returns<=-.10))
                row[model+"_weighted_rank"]=float(W@quality[j,selected])
                row[model+"_weighted_return21"]=float(W@returns)
                row[model+"_weighted_regret"]=float(yr[j].max()-W@returns)
                row[model+"_winner_weight"]=float(W@np.array([int(v==future_best[j]) for v in selected]))
                row[model+"_top3_winner"]=float(future_best[j] in selected)
                row[model+"_bottom3_weight"]=float(W@np.array([int(v in bottom) for v in selected]))
            row["flagged_original_weight"]=float(W@mask[j,baseline])
            row["e1_flagged_original_weight"]=float(W@mask_e1[j,baseline])
            row["e1_replacements_count"]=len(e1_replaced)
            row["e1_basket_edited"]=float(bool(e1_replaced))
            row["removed_original_weight"]=float(sum(W[s] for s,_,_ in replaced))
            row["removed_loss10_weight"]=float(sum(W[s]*int(yr[j,old]<=-.1) for s,old,_ in replaced))
            row["removed_positive_weight"]=float(sum(W[s]*int(yr[j,old]>0) for s,old,_ in replaced))
            row["removed_true_winner_weight"]=float(sum(W[s]*int(old==future_best[j]) for s,old,_ in replaced))
            row["replacement_loss10_weight"]=float(sum(W[s]*int(yr[j,new]<=-.1) for s,_,new in replaced))
            row["replacement_true_winner_weight"]=float(sum(W[s]*int(new==future_best[j]) for s,_,new in replaced))
            row["replacements_count"]=len(replaced)
            row["initial_flagged_count"]=int(sum(bool(mask[j,p]) for p in baseline))
            row["unfilled_flag_count"]=row["initial_flagged_count"]-len(replaced)
            row["basket_edited"]=float(bool(replaced))
            month_data.append(row)
            for slot,old_pos,new_pos in replaced:
                changes.append({"signal_date":str(today.date()),"basket":j,
                    "slot":slot+1,"previous_ETF":ticker[basket_idx[j,old_pos]],
                    "replacement_ETF":ticker[basket_idx[j,new_pos]],
                    "previous_21day_momentum":float(mm[basket_idx[j,old_pos]]),
                    "previous_63day_drawdown":float(dd[basket_idx[j,old_pos]]),
                    "rank_pct_previous":float(rank[j,old_pos]),
                    "rank_pct_replacement":float(rank[j,new_pos]),
                    "previous_future21_AUDIT_ONLY":float(yr[j,old_pos]),
                    "replacement_future21_AUDIT_ONLY":float(yr[j,new_pos])})
        unique=sorted(unique_selection)
        loss=(y[unique]<=-.1)
        flagged=flags[unique]
        unique_e1=e1_flags[unique]
        stat={
            "unique_selected_ETFs":len(unique),
            "unique_selected_flagged":int(flagged.sum()),
            "unique_selected_loss10":int(loss.sum()),
            "unique_flagged_loss10":int((flagged&loss).sum()),
            "unique_flagged_positive":int((flagged&(y[unique]>0)).sum()),
            "unique_flag_precision_loss10":float(loss[flagged].mean()) if flagged.any() else np.nan,
            "unique_unflag_loss10_rate":float(loss[~flagged].mean()) if (~flagged).any() else np.nan,
            "unique_loss10_recall_by_flag":float((flagged&loss).sum()/loss.sum()) if loss.sum() else np.nan,
            "unique_flag_rate":float(flagged.mean()),
            "unique_e1_flag_rate":float(unique_e1.mean()),
            "unique_e1_flag_precision_loss10":float(loss[unique_e1].mean()) if unique_e1.any() else np.nan,
            "unique_e1_flagged_future_positive":int((unique_e1&(y[unique]>0)).sum()),
            "unique_flagged_future_positive":int((flagged&(y[unique]>0)).sum()),
            "all_universe_flag_rate":float(flags.mean()),
        }
        d=pd.DataFrame(month_data)
        month={"signal_date":str(today.date()),"year":int(today.year),
               "n_baskets":len(d),"n_ETFs":len(ticker),
               "trajectory_coverage":float(observed_avail.mean()),
               **stat}
        month.update({k:float(d[k].mean()) for k in d.columns})
        monthly.append(month)
        for t,z1,z2,z3,z4,z5,z6 in zip(ticker,mm,dd,flags,y,eff,e1_flags):
            audit.append({"signal_date":str(today.date()),"ticker":t,
                "asof_log_momentum21":float(z1),"asof_drawdown_from63_high":float(z2),
                "trajectory_veto_flag":bool(z3),"e1_veto_flag":bool(z6),
                "coherence21":float(z5) if np.isfinite(z5) else None,
                "future_ret21_AUDIT_ONLY":float(z4)})
    f=pd.DataFrame(monthly).sort_values("signal_date").reset_index(drop=True)
    assert len(f)==101 and f.n_baskets.eq(500).all()
    assert f.trajectory_coverage.eq(1).all()
    metrics=["loss10_weight","weighted_rank","weighted_return21","weighted_regret",
             "winner_weight","top3_winner","bottom3_weight"]
    boots=[monthly_block_delta(f,"EDITED_"+metric,"BASE_"+metric) for metric in metrics]
    boots += [monthly_block_delta(f,"EDITED_"+metric,"E1_"+metric) for metric in metrics]
    pd.DataFrame(boots).to_csv(out/"PAIRED_MONTH_BOOTSTRAP.csv",index=False)
    f.to_csv(out/"TRAJECTORY_MONTHLY.csv",index=False)
    pd.DataFrame(audit).to_csv(out/"TRAJECTORY_ASOF_AUDIT.csv",index=False)
    pd.DataFrame(changes).to_csv(out/"TRAJECTORY_SUBSTITUTIONS.csv",index=False)
    columns=["BASE_"+m for m in metrics]+["EDITED_"+m for m in metrics]+["E1_"+m for m in metrics]+[
        "flagged_original_weight","e1_flagged_original_weight","e1_replacements_count","e1_basket_edited",
        "removed_original_weight","removed_loss10_weight",
        "removed_positive_weight","removed_true_winner_weight","replacement_loss10_weight",
        "replacement_true_winner_weight","replacements_count","initial_flagged_count",
        "unfilled_flag_count","basket_edited","unique_flag_precision_loss10",
        "unique_unflag_loss10_rate","unique_loss10_recall_by_flag","unique_flag_rate",
        "unique_e1_flag_rate","unique_e1_flag_precision_loss10",
        "unique_e1_flagged_future_positive","unique_flagged_future_positive",
        "all_universe_flag_rate"]
    pd.DataFrame({"metric":columns,"monthly_mean":[float(f[c].mean()) for c in columns],
                  "n_months_notnull":[int(f[c].notna().sum()) for c in columns]
                  }).to_csv(out/"TRAJECTORY_SUMMARY.csv",index=False)
    f.groupby("year")[columns].mean().to_csv(out/"TRAJECTORY_YEARLY.csv")
    (out/"MANIFEST.json").write_text(json.dumps({
       "layer":"L10.E2 ML postrank coherence-confirmed veto/frozen ML replacement",
       "source_raw_run":39482809691,"source_frozen_model_run":39700865721,
       "n_etf":149,"n_baskets":500,"basket_size":24,"n_mature_months":101,
       "basket_sha256":SHA,"selected_ranker_unchanged":"CORRECTED_PAIR127",
       "single_rule":"E1 negative momentum21 plus drawdown63 <=-.10, AND Kaufman efficiency21 >= .45; sole additional E2 condition",
       "prior_exact_E1_test":39742108852,"coherence_cutoff":0.45,
       "replacement":"only flagged original positions, first unflagged name ranked 4+ by original CORRECTED ML, else hold original",
       "same_slot_weights":[.5,.3,.2],"future_returns_exclusively_for_eval":True,
       "no_ML_refit":True,"no_general_analytic_reranking":True,"no_CAGR":True,
       "not_virgin_holdout":True,"original_V2_unchanged":True,
       "original_raw_source_count":manifest["tickers"],
       "synthetic_prefix_invariance_passed":True
    },indent=2))
    print("L10E2_SUMMARY\n"+pd.read_csv(out/"TRAJECTORY_SUMMARY.csv").to_string(index=False),flush=True)
    print("L10E2_BOOTSTRAP\n"+pd.DataFrame(boots).to_string(index=False),flush=True)
    print("L10E2_SUBSTITUTIONS",len(changes),flush=True)

if __name__=="__main__":
    main()
