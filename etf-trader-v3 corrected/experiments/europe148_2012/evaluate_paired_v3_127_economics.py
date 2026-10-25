#!/usr/bin/env python3
"""One-account matched native EUR real-economic US149/EU148 V3 127 ranks.

Exact calendar and cost engine imported from existing frozen momentum controls
(no different economic engine). As-of and benchmark use original US and EU
universe sources. Evaluate not select parameters, report all Top1/3/5.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import pandas as pd,numpy as np
from scipy.stats import spearmanr
from paired_us149_eu148_controls import load_raw,compute_nav
START="2018-01-01";END="2026-07-01";LAST="2026-05-31"

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--us",required=True);p.add_argument("--eu",required=True)
    p.add_argument("--fx",required=True);p.add_argument("--heads",required=True)
    p.add_argument("--control",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    us=pd.read_csv(Path(a.us)/"universe.csv")
    eu=pd.read_csv(Path(a.eu)/"EU148_VERIFIED_LEGAL_ISIN_CATALOG.csv")
    assert len(us)==149 and len(eu)==148
    Uo,Uc,Uv=load_raw(a.us,us,"US149")
    Eo,Ec,Ev=load_raw(Path(a.eu)/"raw_ticker_csv",eu,"EU148")
    joint=Uo["SPY"].dropna().index.intersection(Eo["DE0002635307"].dropna().index).sort_values()
    joint=joint[(joint>=pd.Timestamp("2012-01-01"))&(joint<=pd.Timestamp(END))]
    assert joint[-1]==pd.Timestamp(END) and len(joint)>3200
    fx=pd.read_csv(a.fx,parse_dates=["date"]).set_index("date").Close.reindex(joint).ffill()
    assert fx.loc["2018-01-01":].notna().all()
    USopen=Uo.reindex(joint).div(fx,axis=0)
    EUopen=Eo.reindex(joint)
    UV=Uv.reindex(joint)
    EV=Ev.reindex(joint)
    date_ser=pd.Series(joint,index=joint)
    ss=date_ser.loc[START:LAST]
    dates=ss.groupby(ss.index.to_period("M")).last().tolist()
    assert len(dates)==101 and dates[0]==pd.Timestamp("2018-01-31") and dates[-1]==pd.Timestamp("2026-05-29")
    qlist=[];audits=[]
    for market in ("US149","EU148"):
        for y in range(2018,2027):
            pfile=Path(a.heads)/market/str(y)/"PAIRED_127_PREDICTIONS.csv"
            pafit=Path(a.heads)/market/str(y)/"FIT_AUDIT.json"
            d=pd.read_csv(pfile,parse_dates=["signal_date","entry_date","exit_date_21"])
            assert set(d.market)=={market} and set(d.variant)=={"V3_LEAF127"}
            assert d.signal_date.dt.year.eq(y).all()
            qlist.append(d)
            audits.append(json.loads(pafit.read_text()))
    q=pd.concat(qlist,ignore_index=True)
    assert q.market.nunique()==2 and len(q)>25000
    assert not q.duplicated(["market","signal_date","ticker"]).any()
    assert q.groupby("market").signal_date.nunique().eq(101).all()
    assert all(x["last_train_exit"]<x["mature_label_cutoff"] for x in audits)
    assert all(x["features"]==125 for x in audits)
    score=[];navs=[];trades=[];skills=[];choices=[]
    for market,op,vol,cohort,universe in (
       ("US149",USopen,UV,us,set(us.ticker)),
       ("EU148",EUopen,EV,eu,set(eu.ticker))):
        qq=q[q.market.eq(market)]
        restricted=(set(cohort.loc[cohort.macro_category.str.startswith(("C01","C02","C03")),"ticker"])
                    if market=="US149" else
                    set(cohort.loc[cohort.macro_category.str.startswith("EU_EQUITY"),"ticker"]))
        for scope,allow in (("FULL",universe),("EQUITY",restricted)):
            picks={};skillvals=[]
            for date in dates:
                g=qq.loc[qq.signal_date.eq(date)&qq.ticker.isin(allow)].copy()
                assert len(g)>=20,(market,date,len(g))
                g=g.sort_values(["pred","ticker"],ascending=[False,True])
                picks[date]=list(g.ticker)
                actual=g.dropna(subset=["fwd_ret_21"])
                assert len(actual)>=20
                top1=g.iloc[0]
                best=actual.sort_values("fwd_ret_21",ascending=False).iloc[0]
                ic=float(spearmanr(actual.pred,actual.fwd_ret_21).statistic)
                hit1=int(top1.ticker==best.ticker)
                hit3=int(best.ticker in set(g.head(3).ticker))
                excess=float(top1.fwd_ret_21-actual.fwd_ret_21.mean()) if pd.notna(top1.fwd_ret_21) else np.nan
                skillvals.append(dict(market=market,scope=scope,signal_date=str(date.date()),
                      n_eligible=len(g),n_mature=len(actual),spearman=ic,
                      top1=str(top1.ticker),winner=str(best.ticker),top1_hit=hit1,top3_hit=hit3,
                      top1_excess_fwd21=excess))
            m=pd.DataFrame(skillvals)
            skills.append(dict(market=market,scope=scope,months=len(m),
                n_first=int(m.n_eligible.iloc[0]),n_last=int(m.n_eligible.iloc[-1]),
                spearman_mean=float(m.spearman.mean()),top1_hit=int(m.top1_hit.sum()),
                top3_hit=int(m.top3_hit.sum()),
                top1_excess_fwd21_mean=float(m.top1_excess_fwd21.mean())))
            choices.append(m)
            for n in (1,3,5):
                rr,nv,tr=compute_nav(op,vol,dates,picks,joint,dates,market,scope,"V3_LEAF127",n)
                score.append(rr);navs.append(nv);trades.append(tr)
                print("STRICT_PAIRED_V3_NATIVE127",market,scope,"TOP",n,
                      "CAGR_EUR",rr["cagr_eur"],"MAXDD",rr["max_dd"],flush=True)
    controls=pd.read_csv(Path(a.control)/"PARITY_STRATEGY_CAGR_EUR.csv")
    controls=controls[(controls.variant.eq("MOM252")&controls.top_n.isin((1,3,5)))|
                      (controls.segment.eq("PASSIVE"))]
    sc=pd.DataFrame(score)
    benchmarks=controls[controls.segment.eq("PASSIVE")].set_index("market").cagr_eur.to_dict()
    for market in ("US149","EU148"):
        assert market in benchmarks
    sc["passive_home_cagr_eur"]=sc.market.map(benchmarks)
    sc["alpha_vs_passive_pp"]=100*(sc.cagr_eur-sc.passive_home_cagr_eur)
    mom=controls[controls.variant.eq("MOM252")]
    md={}
    for r in mom.itertuples():
        md[(r.market,r.top_n)]=r.cagr_eur
    sc["mom252_full_cagr_eur"]=[md[(row.market,row.top_n)] for row in sc.itertuples()]
    sc["delta_vs_mom252_full_pp"]=100*(sc.cagr_eur-sc.mom252_full_cagr_eur)
    sc.to_csv(out/"PAIRED_V3_127_ECONOMIC_SCORECARD.csv",index=False)
    pd.concat(navs,ignore_index=True).to_csv(out/"PAIRED_V3_127_DAILY_NAV_EUR.csv",index=False)
    pd.concat(trades,ignore_index=True).to_csv(out/"PAIRED_V3_127_REAL_TRADES.csv",index=False)
    pd.DataFrame(skills).to_csv(out/"PAIRED_V3_127_RANKING_SKILL.csv",index=False)
    pd.concat(choices,ignore_index=True).to_csv(out/"PAIRED_V3_127_MONTHLY_SKILL.csv",index=False)
    pd.DataFrame(audits).to_json(out/"PAIRED_V3_127_FIT_AUDIT.json",orient="records",indent=2)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
       native_V3_127=True,annual_refits_per_market=9,
       paired_common_calendar=True,paired_months=101,fees_one_way_bps=10,
       EURUSD_asof_prior_US_close=True,all_returns_in_EUR=True,
       all_model_price_features_in_native_USD_EUR=True,
       both_markets_mature_21_joint_days_labels=True,
       risk_layers_not_reenabled=True,
       meta_trees_not_reenabled=True,
       dataset_snapshot_2026_survivorship_bias=True,
       OOS_sample_prior_tuning_not_independent_holdout=True
    ),indent=2))
    print("PAIRED_V3_127_EUR_ECONOMICS_PASS",sc.to_string(index=False),flush=True)
    print("PAIRED_V3_127_RANK_SKILL_PASS",pd.DataFrame(skills).to_string(index=False),flush=True)
if __name__=="__main__":main()
