#!/usr/bin/env python3
"""Matched fee-aware economics for frozen E4 versus frozen original ML and E3.

Inputs: frozen original CORRECTED scores, certified adjusted OHLCV, exact
audited E3/E4 substitute records from successful 39752940429 and 39828627036.
No ML refit, calibration, thresholds or signal changes in this script.
Portfolio next-open, source-only L07 executor, one-way cost=10bps,
same 500 baskets x 24, Top3 weights 50/30/20.
Period ends at 2026-06-01 because last fully label-mature E3 signal is May29:
do NOT silently extend with unavailable June30 E3 decisions.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
WEIGHT=np.array([.5,.3,.2])
FEE=.001
WINDOWS={"2018_TO_MAY2026":("2018-02-01","2026-06-01"),
         "2022_TO_MAY2026":("2022-02-01","2026-06-01")}
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--raw",required=True)
    ap.add_argument("--scores",required=True)
    ap.add_argument("--baskets",required=True)
    ap.add_argument("--e3-substitutions",required=True)
    ap.add_argument("--e3-manifest",required=True)
    ap.add_argument("--e4-substitutions",required=True)
    ap.add_argument("--e4-manifest",required=True)
    ap.add_argument("--out",required=True)
    z=ap.parse_args();out=Path(z.out);out.mkdir(parents=True,exist_ok=True)
    assert hashlib.sha256(Path(z.baskets).read_bytes()).hexdigest()==SHA
    v3=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(v3/"src"))
    from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder,load_baskets
    from etf_trader_v3.source_only.statistics import metrics
    source=v3/"experiments"/"l07_integrated"/"evaluate.py"
    spec=importlib.util.spec_from_file_location("L07_FROZEN_ECON",source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    replay=module.replay
    manifest=json.loads(Path(z.e3_manifest).read_text())
    assert manifest["n_etfs"]==149 and manifest["n_baskets"]==500
    assert manifest["full_label_maturity_gate"] and manifest["frozen_scores_run"]==39700865721
    e4manifest=json.loads(Path(z.e4_manifest).read_text())
    assert e4manifest["n_etfs"]==149 and e4manifest["n_baskets"]==500
    assert e4manifest["frozen_e3_run"]==39752940429
    assert e4manifest["frozen_scores_run"]==39700865721
    assert e4manifest["full_label_maturity_gate"] and e4manifest["original_E3_pair_predictions_unchanged"]
    assert e4manifest["E3_and_E1_metrics_reproduced"]
    assert e4manifest["n_E4_changed_basket_slots"]==158
    mats,cats,rawaudit=load_ticker_csv_folder(z.raw)
    bs=load_baskets(z.baskets,cats)
    assert len(bs)==500 and all(len(g)==24 for g in bs)
    f=pd.read_csv(z.scores,parse_dates=["signal_date"])
    f=f.loc[f.variant.eq("CORRECTED"),["signal_date","ticker","pred","fwd_ret_21"]].copy()
    f.ticker=f.ticker.astype(str).str.upper()
    assert len(f)==15198 and f.signal_date.nunique()==102
    substitutions=pd.read_csv(z.e3_substitutions,parse_dates=["signal_date"])
    assert len(substitutions)==manifest["n_replaced_basket_slot_events"]
    assert not substitutions.duplicated(["signal_date","basket","slot"]).any()
    assert ((substitutions.slot>=1)&(substitutions.slot<=3)).all()
    e4sub=pd.read_csv(z.e4_substitutions,parse_dates=["signal_date"])
    assert len(e4sub)==158
    assert not e4sub.duplicated(["signal_date","basket","slot"]).any()
    assert ((e4sub.slot>=1)&(e4sub.slot<=3)).all()
    dtlist=sorted(f.signal_date.unique())
    mature=[date for date in dtlist if f[f.signal_date.eq(date)].fwd_ret_21.notna().all()]
    assert len(mature)==101 and pd.Timestamp(mature[-1])==pd.Timestamp("2026-05-29")
    assert pd.Timestamp(mature[0])==pd.Timestamp("2018-01-31")
    assert set(substitutions.signal_date).issubset(set(mature))
    assert set(e4sub.signal_date).issubset(set(mature))
    opens=mats["Open"].sort_index()
    dates=opens.index;columns=list(opens.columns)
    lookup={ticker:i for i,ticker in enumerate(columns)}
    member=np.array([[lookup[t] for t in group] for group in bs],int)
    assert member.shape==(500,24)
    plans={"CORRECTED_TOP3":{},"E3_REVIEW_TOP3":{},"E4_CALIBRATED_TOP3":{}}
    submitted=0;submitted_e4=0
    for date in mature:
        g=f.loc[f.signal_date.eq(date)].sort_values("ticker")
        assert len(g)==149 and g.ticker.nunique()==149
        sig=pd.Timestamp(date)
        pos=int(dates.searchsorted(sig,side="right"))
        assert pos<len(dates) and dates[pos]>sig
        score=g.set_index("ticker").pred.rank(method="average",pct=True)
        pct=score.reindex(columns).to_numpy(float)
        assert np.isfinite(pct).all()
        order=np.argsort(-pct[member],axis=1,kind="stable")
        base=np.take_along_axis(member,order[:,:3],axis=1).copy()
        edited=base.copy();edited_e4=base.copy()
        changes=substitutions.loc[substitutions.signal_date.eq(sig)]
        submitted+=len(changes)
        for rr in changes.itertuples(index=False):
            basket=int(rr.basket);slot=int(rr.slot)-1
            assert rr.incumbent==columns[base[basket,slot]]
            successor=lookup[str(rr.challenger)]
            assert successor in member[basket]
            edited[basket,slot]=successor
        changes_e4=e4sub.loc[e4sub.signal_date.eq(sig)]
        submitted_e4+=len(changes_e4)
        for rr in changes_e4.itertuples(index=False):
            basket=int(rr.basket);slot=int(rr.slot)-1
            assert rr.incumbent==columns[base[basket,slot]]
            successor=lookup[str(rr.challenger)]
            assert successor in member[basket]
            edited_e4[basket,slot]=successor
        assert (edited[:,0]!=edited[:,1]).all() and (edited[:,0]!=edited[:,2]).all() and (edited[:,1]!=edited[:,2]).all()
        assert (edited_e4[:,0]!=edited_e4[:,1]).all() and (edited_e4[:,0]!=edited_e4[:,2]).all() and (edited_e4[:,1]!=edited_e4[:,2]).all()
        for arm,choices in [("CORRECTED_TOP3",base),("E3_REVIEW_TOP3",edited),("E4_CALIBRATED_TOP3",edited_e4)]:
            w=np.zeros((500,149),float)
            for slot in range(3):
                w[np.arange(500),choices[:,slot]]+=WEIGHT[slot]
            assert np.allclose(w.sum(axis=1),1)
            plans[arm][pos]=w
    assert submitted==len(substitutions) and submitted_e4==len(e4sub)
    cards=[];annual=[];daily=[];deltas=[]
    for label,(start,end) in WINDOWS.items():
        outputs={}
        for arm in ["CORRECTED_TOP3","E3_REVIEW_TOP3","E4_CALIBRATED_TOP3"]:
            day,nav,turn,n_reb=replay(plans[arm],mats,start,end,FEE)
            stats=metrics(nav,turn)
            cards.append(dict(window=label,arm=arm,cost_one_way_bps=10,
                    days=len(day),n_rebalances=n_reb,**stats))
            outputs[arm]=(day,nav,turn)
            avg=nav.mean(axis=0)
            frame=pd.DataFrame({"date":day,"window":label,"arm":arm,
                     "aggregate_nav":avg,"mean_turnover":turn.mean(axis=0)})
            daily.append(frame)
            prior=1.
            for year,g in frame.groupby(frame.date.dt.year):
                annual.append({"window":label,"arm":arm,"year":int(year),
                         "annual_nav_return":float(g.aggregate_nav.iloc[-1]/prior-1)})
                prior=float(g.aggregate_nav.iloc[-1])
            print("E4_ECON",label,arm,stats["aggregate_cagr"],stats["aggregate_maxdd"],
                  "mean_CAGR",stats["mean_cagr"],"turnover",stats["mean_annualized_gross_turnover"],flush=True)
        # Replay E3 itself on the same signal dates: must reproduce its original
        # economic study to machine precision, no silent calendar differences.
        expected_e3={"2018_TO_MAY2026":(0.15650410951308125,0.15613229879534463),
                     "2022_TO_MAY2026":(0.21434619905689933,0.20982310238012247)}
        b0=next(q for q in cards if q["window"]==label and q["arm"]=="CORRECTED_TOP3")
        e3=next(q for q in cards if q["window"]==label and q["arm"]=="E3_REVIEW_TOP3")
        np.testing.assert_allclose([b0["aggregate_cagr"],e3["aggregate_cagr"]],
             expected_e3[label],rtol=0,atol=1e-10)
        for trial in ["E3_REVIEW_TOP3","E4_CALIBRATED_TOP3"]:
            dates_base,nav_base,_=outputs["CORRECTED_TOP3"]
            dates_test,nav_test,_=outputs[trial]
            assert dates_base.equals(dates_test)
            log_base=np.diff(np.log(np.column_stack([np.ones(500),nav_base])),axis=1)
            log_test=np.diff(np.log(np.column_stack([np.ones(500),nav_test])),axis=1)
            diff=(log_test-log_base).mean(axis=0)
            reps=3000;block=21;N=len(diff)
            rng=np.random.default_rng(20261022)
            ix=((rng.integers(0,N,size=(reps,int(np.ceil(N/block))))[:,:,None]
                +np.arange(block))%N).reshape(reps,-1)[:,:N]
            boot=diff[ix].mean(axis=1)*252
            deltas.append(dict(window=label,trial=trial,control="CORRECTED_TOP3",
                 n_common_days=N,annualized_paired_log_alpha=float(252*diff.mean()),
                 bootstrap_ci95_low=float(np.quantile(boot,.025)),
                 bootstrap_ci95_high=float(np.quantile(boot,.975)),
                 blocks_trading_days=block,bootstrap_reps=reps))
    pd.DataFrame(cards).to_csv(out/"ECONOMIC_SCORECARD.csv",index=False)
    pd.DataFrame(annual).to_csv(out/"ECONOMIC_YEARLY.csv",index=False)
    pd.concat(daily,ignore_index=True).to_csv(out/"ECONOMIC_DAILY_NAV.csv",index=False)
    pd.DataFrame(deltas).to_csv(out/"PAIRED_BLOCK_BOOTSTRAP.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
         experimental_E3_run=39752940429,
         exact_original_E3_actions_replayed=len(substitutions),
         exact_original_E4_actions_replayed=len(e4sub),
         experimental_E4_run=39828627036,
         OOT_calibrator_refitted_for_economics=False,
         benchmark="CORRECTED frozen 127-leaf Top3",
         same_top3_policy=True,weights=[.5,.3,.2],
         next_open_source_L07_executor=True,fees_one_way_bps=10,
         source_frozen_raw=39482809691,source_frozen_scores=39700865721,
         n_etfs=149,n_baskets=500,n_months=101,
         last_mature_signal="2026-05-29",economic_end="2026-06-01",
         window_dates=WINDOWS,retrospective_history_previously_explored=True,
         E3_model_retrained_for_economics=False,production_changed=False),indent=2)+"\n")
    print("E4_ECONOMIC_PAIRED",pd.DataFrame(deltas).to_string(index=False),flush=True)

if __name__=="__main__":main()
