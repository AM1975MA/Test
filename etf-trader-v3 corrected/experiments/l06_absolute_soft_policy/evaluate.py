#!/usr/bin/env python3
"""V3 L06.5: one frozen calibrated absolute-loss soft risk budget intervention.

Objective: reduce portfolio weight allocated to actually severe future next-21D
ETF losses (<= -10%) while preserving winner/opportunity exposure and limiting
selection weight churn. No CAGR, next-open strategy P&L or new model fitting.

Input: explicitly out-of-year probability P(abs_loss10) from SUCCESSFUL L06.4
run 39671493979, never trained on evaluation-year labels. Original same-three
Tail Top3 holdings fixed, base weights (.5,.3,.2).
SINGLE frozen challenger: w_i = normalize(base_i * exp(-3 * p_abs_loss_i)).
Coefficient 3 is specified BEFORE evaluation and never tuned on OOS.
The entire 149-ETF OOS universe is used only to identify same three names;
all selected Top3 have calibrated p_abs_loss from L06.4. Evaluate 53 matured
month-ends 2022..2026, 500 canonical baskets. Month-level bootstrap.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd

BASE="TOP3_DECAY"
ALT="TOP3_ABSLOSS_EXP3"
BASE_W=np.array([.5,.3,.2],float)
ALPHA=3.0
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--risk",default="runs/v3_l06_ref")
    p.add_argument("--absolute",default="runs/v3_l06_abs_ref")
    p.add_argument("--l05",default="runs/v3_l05_reference")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l06_abs_policy")
    args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest()==SHA
    raw=pd.read_csv(args.baskets)
    raw.ticker=raw.ticker.astype(str).str.upper()
    bs=[g.ticker.tolist() for _,g in raw.sort_values(["basket","ticker"]).groupby("basket")]
    assert len(bs)==500 and all(len(x)==24 for x in bs)

    u=pd.read_csv(Path(args.risk)/"RISK_SCORES_OOS.csv",parse_dates=["signal_date"])
    a=pd.read_csv(Path(args.absolute)/"OOS_SELECTED_ETF_ABSOLUTE_LOSS.csv",parse_dates=["signal_date"])
    old=pd.read_csv(Path(args.l05)/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    assert len(u)==15198 and not u.duplicated(["signal_date","ticker"]).any()
    assert not a.duplicated(["signal_date","ticker"]).any()
    assert a.signal_date.nunique()==53
    pred=a[["signal_date","ticker","p_abs_loss","abs_loss10"]]
    universe=u.merge(pred,on=["signal_date","ticker"],how="left",validate="one_to_one")
    months=sorted(a.signal_date.unique())
    assert len(months)==53
    assert universe.ticker.nunique()==149

    prev={s:[None]*500 for s in (BASE,ALT)}
    rows=[]
    for date in months:
        g=universe.loc[universe.signal_date.eq(date)].sort_values("ticker").reset_index(drop=True)
        assert len(g)==149 and g.fwd_ret_21.notna().all()
        where={t:i for i,t in enumerate(g.ticker)}
        y=g.fwd_ret_21.to_numpy(float)
        score=g.TAIL_ELITE45.to_numpy(float)
        prob=g.p_abs_loss.to_numpy(float)
        holder={name:[] for name in (BASE,ALT)}
        for i,basket in enumerate(bs):
            idx=np.array([where[t] for t in basket],int)
            future=y[idx];tail=score[idx]
            rank_order=np.argsort(-tail,kind="stable")
            chosen=rank_order[:3]
            ids=idx[chosen]
            pval=prob[ids]
            if not np.isfinite(pval).all():raise RuntimeError(f"Calibration missing for selected ETF in {date}")
            assert np.all((pval>=0)&(pval<=1))
            test_w=BASE_W*np.exp(-ALPHA*pval)
            test_w=test_w/test_w.sum()
            assert np.isclose(test_w.sum(),1) and (test_w>0).all()
            trueorder=np.argsort(-future,kind="stable")
            true_best=int(trueorder[0])
            worst3=set(trueorder[-3:].tolist())
            rank_quality=np.empty(24,float)
            rank_quality[trueorder]=np.linspace(1,0,24)
            for name,w in ((BASE,BASE_W),(ALT,test_w)):
                positions={basket[int(chosen[k])]:float(w[k]) for k in range(3)}
                before=prev[name][i]
                churn=(np.nan if before is None else
                    float(sum(abs(positions.get(t,0)-before.get(t,0))
                    for t in set(positions)|set(before))/2))
                prev[name][i]=positions
                holder[name].append({
                  "best_in_top3":float(true_best in chosen),
                  "weight_on_best":float(w[np.flatnonzero(chosen==true_best)[0]]) if true_best in chosen else 0.,
                  "abs_loss10_weight":float(sum(w[k] for k,z in enumerate(chosen) if future[z]<=-.10)),
                  "basket_bottom3_weight":float(sum(w[k] for k,z in enumerate(chosen) if int(z) in worst3)),
                  "selected_rank_quality":float(np.dot(w,rank_quality[chosen])),
                  "weighted_oracle_regret21":float(future.max()-np.dot(w,future[chosen])),
                  "target_weight_churn":churn,
                  "max_position_weight":float(max(w)),
                  "effective_n_holdings":float(1/np.sum(w**2)),
                  "weight_shift_half_L1":float(np.abs(w-BASE_W).sum()/2)
                })
        for name in (BASE,ALT):
            vals=pd.DataFrame(holder[name]).mean(numeric_only=True,skipna=True)
            rows.append({"signal_date":date,"year":pd.Timestamp(date).year,
                "variant":name,"n_baskets":500,**vals.to_dict()})

    df=pd.DataFrame(rows)
    assert len(df)==53*2
    assert not df.duplicated(["variant","signal_date"]).any()
    baseline=df[df.variant==BASE].sort_values("signal_date").reset_index(drop=True)
    challenger=df[df.variant==ALT].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(baseline.signal_date,challenger.signal_date)
    # Prior frozen L05 source-level oracle: same Top3 Tail names and 50/30/20 weights.
    ref=old[(old.variant=="TOP3_DECAY")&old.signal_date.isin(months)].sort_values("signal_date").reset_index(drop=True)
    assert len(ref)==53
    pd.testing.assert_series_equal(baseline.signal_date,ref.signal_date)
    for akey,bkey in [
        ("weight_on_best","weighted_winner_capture"),
        ("basket_bottom3_weight","bottom_three_weight"),
        ("selected_rank_quality","weighted_true_rank_quality"),
        ("weighted_oracle_regret21","weighted_oracle_regret21")
    ]:
        # Use only fields present in the original L05 artifact.
        if bkey in ref:
            np.testing.assert_allclose(baseline[akey],ref[bkey],atol=2e-12,rtol=0)
    np.testing.assert_array_equal(baseline.best_in_top3,challenger.best_in_top3)

    metrics=["best_in_top3","weight_on_best","abs_loss10_weight",
        "basket_bottom3_weight","selected_rank_quality",
        "weighted_oracle_regret21","target_weight_churn",
        "max_position_weight","effective_n_holdings","weight_shift_half_L1"]
    df.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    summary=df.groupby("variant")[metrics].mean()
    summary.insert(0,"months",df.groupby("variant").size())
    summary.to_csv(out/"RESULTS.csv")
    df.groupby(["year","variant"],as_index=False)[metrics].mean().to_csv(out/"YEARLY.csv",index=False)
    intervals=[]
    for metric in metrics:
        delta=(challenger[metric]-baseline[metric]).to_numpy(float)
        if metric=="target_weight_churn":delta=delta[1:]
        assert np.isfinite(delta).all(),metric
        n=len(delta);reps=6000;block=6
        rng=np.random.default_rng(20261021)
        starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
        ix=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
        sims=delta[ix].mean(axis=1)
        intervals.append({
            "metric":metric,"mean_delta":float(delta.mean()),
            "ci95_low":float(np.quantile(sims,.025)),
            "ci95_high":float(np.quantile(sims,.975)),
            "bootstrap":"paired 6-month circular calendar blocks, 6000 samples"
        })
    pd.DataFrame(intervals).to_csv(out/"PAIRED_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps({
        "layer":"L06.5 calibrated absolute-loss soft weighting",
        "original_tail_expert":"unchanged prequential elite Tail45",
        "original_policy":"Top3 fixed 50/30/20, same tickers and 500 baskets",
        "risk_calibration_run":39671493979,
        "original_149_ETF_RISK_scores_run":39662062361,
        "original_L05_baseline_run":39661273577,
        "treatment":"normalize([.5,.3,.2] * exp(-3*p_abs_loss10))",
        "treatment_alpha_fixed_before_testing":3.0,
        "no_ETF_selection_change":True,"no_CAGR":True,"no_future_data_in_policy":True,
        "next21D_loss_event":"<= -10% actual ETF future return",
        "test_only_2022_2026_mature_months":len(months),
        "calendar_explored_not_independent":True},indent=2))
    print("V3_L06_5_ABSOLUTE_SOFT_POLICY\n"+summary.to_string(),flush=True)


if __name__=="__main__":
    main()
