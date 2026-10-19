#!/usr/bin/env python3
"""Source-exact ETF Trainer V2 EU48 using 12-month-causal new ranking.

Causal ADAPT4 scores reused unchanged; old/source MA3 score as control.
Neither model is fitted/tuned on performance. Original USA SPY/HYG/IEF risk
OR Europe-reference risk, same 1374 trading days and 48 legal EU ISIN.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from etf_trader.ma3 import producer,ddfirst,v6,highcagr24
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from isin_first2026.predict48.tournament import ROOT,price_data,monthly_data,rank,sha
from isin_first2026.v2_unrestricted48.run import (
   evaluate,risk_reference_euro48,v6_reference_europe)
from isin_first2026.v2_forensic48.ablate import calculate_score
from isin_first2026.v2_usref48.us_source_helpers import (
   dd_reference_us_market,v6_reference_us_market)
from isin_first2026.v2_usref48.original_us_references import asof_quotes
SRC=ROOT/"isin_first2026/predict48"
BASE=ROOT/"isin_first2026/v2_unrestricted48/results"
USBASE=ROOT/"isin_first2026/v2_usref48/results"
EXP=("ORIGINAL_MA3","MOM21","MOM126","RIDGE_RECENT36M")

def build_new_rank(cal,names):
    saved=pd.read_csv(SRC/"results/48_ETF_PREDICTIVE_SCORES_CHRONOLOGICAL.csv",
                      parse_dates=["signal_date"])
    weights=pd.read_csv(SRC/"online_results/CAUSAL_EXPERT_WEIGHTS_AT_EACH_SIGNAL.csv")
    assert len(weights)==65
    scores=[]
    for name in EXP:
        m=saved[saved.method==name].pivot(index="signal_date",columns="ticker",
               values="forecast_rank_score")
        x=m.reindex(index=cal.signal_date,columns=names).to_numpy(float)
        assert x.shape==(65,48)
        scores.append(np.vstack([rank(row) for row in x]))
    combo=[]
    for i,sd in enumerate(cal.signal_date):
        assert str(sd.date())==str(weights.signal_date.iloc[i])
        w=np.array([weights.iloc[i]["ADAPT4_"+x] for x in EXP],float)
        assert abs(w.sum()-1)<1e-10 and w.min()>=.10-1e-10
        combo.append(rank(np.einsum("k,kn->n",w,np.stack([x[i] for x in scores]))))
    adap=np.asarray(combo,float)
    # Independent reconstruction, actual old new-port Top5 by date and ISIN.
    old=pd.read_csv(SRC/"online_results/ONLINE_EXPERT_TOP5_ISIN_SELECTION.csv")
    old=old[old.method=="ADAPT_4_CAUSAL"]
    assert len(old)==65*5
    for i,sd in enumerate(cal.signal_date):
        found=[names[ix] for ix in np.argsort(-adap[i],kind="stable")[:5]]
        recorded=old[old.signal_date==str(sd.date())].sort_values("rank").ticker.to_list()
        assert found==recorded,(sd,found,recorded)
    return adap

def main(prep,usdata,fx,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    prep=Path(prep)
    mats,cat,source=load_ticker_csv_folder(prep/"raw_ticker_csv")
    master,names,Odf,Cdf=price_data(prep)
    assert set(names)==set(mats["Open"])
    # Keep all operations in source vendor price column order.
    names=list(mats["Open"].columns)
    frame,calfull=monthly_data(master,names,Odf,Cdf)
    cal=calfull[calfull.signal_date>=pd.Timestamp("2021-01-01")].reset_index(drop=True)
    assert len(cal)==65
    sourcepred=pd.read_csv(BASE/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv",
              parse_dates=["signal_date"])
    oldscore,et,xb,_=calculate_score(sourcepred,cal,names)
    leader=pd.read_csv(BASE/"ALL48_MONTHLY_LEADERS_AND_V2_INTERVENTIONS.csv")
    assert np.array_equal(np.asarray(names)[np.argmax(oldscore,axis=1)],leader.leader.to_numpy())
    newscores=build_new_rank(cal,names)
    source_pair={"MA3_ORIGINAL":oldscore,"ADAPT4":newscores}
    # All reference source download data are original previous US149 raw files.
    asof_quotes(usdata,mats["Open"].index,fx,out/"ORIGINAL_US_ASOF_REFERENCES")
    us=pd.read_csv(out/"ORIGINAL_US_ASOF_REFERENCES/US_USD_REFERENCE_FOR_ORIGINAL_DD_V6_WITH_PRIOR_DAY_SHIFT.csv",
         parse_dates=["date"]).set_index("date")
    assert us.index.equals(mats["Close"].index)
    risk_us=dd_reference_us_market(us)
    risk_eu_in=pd.read_csv(prep/"EURO_CORP_HY_RISK_ONLY.csv",parse_dates=["date"]).set_index("date")["Close"]
    idx=mats["Open"].index
    end=pd.Timestamp(cal.exit_date.max())
    O=mats["Open"].loc[:end][names]
    L=mats["Low"].loc[O.index,names]
    C=mats["Close"].loc[O.index,names]
    st=int(idx.get_loc(cal.entry_date.iloc[0]))
    en=int(idx.get_loc(cal.exit_date.iloc[-1]))
    days=idx[st:en+1]
    assert len(days)==1374 and days[0]==pd.Timestamp("2021-02-01") and days[-1]==pd.Timestamp("2026-07-01")
    old_market_state=ddfirst.market_state
    try:
        ddfirst.market_state=lambda closes:risk_reference_euro48(closes,risk_eu_in)
        risk_eur=np.asarray(ddfirst.sync_c95_m75_gross(C))[st:en+1]
        ddfirst.market_state=risk_us
        risk_usa=np.asarray(ddfirst.sync_c95_m75_gross(C))[st:en+1]
    finally:ddfirst.market_state=old_market_state
    eu_state=v6_reference_europe()
    usa_state=v6_reference_us_market(us["SPY"])
    ex=ddfirst.daily_execution_inputs(O,L,C)
    op,low,cl,pc,gap,ud1,uneg,UH,SA=[
         ex[k][st:en+1] for k in ("O","L","C","PC","gap","ud1","uneg","UH","SA")]
    zeros=np.zeros_like(UH,dtype=bool)
    zf=np.zeros_like(ud1,float)
    no_alternatives=np.full(len(days),-1,int)
    defensive1=names.index("IBCA.DE")
    defensive2=names.index("IBCN.DE")
    bmat,bok=producer.basket_arrays(pd.DataFrame(
         {"basket":[0]*48,"ticker":names}),names,n_baskets=1)
    assert bmat.shape==(1,48) and bok.all()
    metrics={};daily={"day":days};hold=[];interventions=[]
    for scorer,scores in source_pair.items():
        arr=producer.allocations_from_score(scores,cal,days,bmat,bok,continuous=True)
        assert arr.d1.shape==(1,1374)
        for state_name,rgross,market in (
                ("EU_REFERENCES",risk_eur,eu_state),
                ("ORIGINAL_US_SPY_HYG_IEF",risk_usa,usa_state)):
            g,leaderweights=highcagr24.apply_highcagr24(
                   rgross,arr.weight1,arr.margin)
            v2weights=leaderweights.copy()
            for j,row in enumerate(cal.itertuples(index=False)):
                a=int(days.searchsorted(row.entry_date))
                b=int(days.searchsorted(row.exit_date))
                p=int(arr.d1[0,a]);s=int(arr.d2[0,a])
                assert 0<=p<48 and 0<=s<48 and p!=s
                agree=bool(arr.margin[0,a]>=.03 and et[j,p]>et[j,s] and xb[j,p]>xb[j,s])
                if agree:
                    m=g[a:b]<.999999
                    v2weights[0,a:b][m]=1.
                changed=int((v2weights[0,a:b]>leaderweights[0,a:b]+1e-12).sum())
                interventions.append(dict(score=scorer,state=state_name,
                  signal_date=str(row.signal_date.date()),
                  leader=names[p],second=names[s],margin=float(arr.margin[0,a]),
                  top1_legal_isin=master.set_index("ticker").loc[names[p],"isin"],
                  agreement=agree,changed_days=changed))
                hold.append(dict(score=scorer,state=state_name,
                  signal_date=str(row.signal_date.date()),
                  leader=names[p],second=names[s]))
            state=market(C.loc[days,names],arr.d1,arr.d2,
                    arr.weight1,rgross,bil_ticker="IBCA.DE",shv_ticker="IBCN.DE")
            for variant in ("FULL_HYBRID24","FULL_V2","TOP2_NO_STOP_NO_RISK",
                 "TOP2_GROSS_DD_NO_STOPS"):
                if variant=="FULL_HYBRID24":
                    weights=leaderweights;gross=g;use_stop=True;use_alts=True
                elif variant=="FULL_V2":
                    weights=v2weights;gross=g;use_stop=True;use_alts=True
                elif variant=="TOP2_NO_STOP_NO_RISK":
                    weights=leaderweights;gross=np.ones_like(g);use_stop=False;use_alts=False
                else:
                    weights=v2weights;gross=g;use_stop=False;use_alts=False
                E,T,_,_=v6.simulate_with_alt(
                    arr.d1,arr.d2,weights,op,low,cl,pc,gap,
                    ud1 if use_stop else zf,
                    uneg if use_stop else zf,
                    UH if use_stop else zeros,
                    SA if use_stop else zeros,
                    defensive1,defensive2,gross,
                    state.alt_idx if use_alts else no_alternatives,
                    use_alts,.001)
                name=scorer+"_"+state_name+"_"+variant
                metrics[name]=evaluate(E,T,days)
                daily[name]=E[0]
                print("EU48_CAUSAL_EXPERT_V2_BACKTEST",name,
                      json.dumps(metrics[name]),flush=True)
    # Cross check same 48 EUR original MA3 V2 full daily source result EXACT.
    prior=pd.read_csv(BASE/"DAILY_NAV_DD_AND_V2_TRADING.csv")
    actual=daily["MA3_ORIGINAL_EU_REFERENCES_FULL_V2"]
    assert np.allclose(actual,prior["TrainerV2"].to_numpy(float),rtol=0,atol=1e-11)
    prior_us=json.loads((USBASE/"RESULT.json").read_text())["all_metrics"][
          "ORIGINAL_EU_SCORE_US_MARKET_EU_DEFENSE_V2"]
    actual_us=metrics["MA3_ORIGINAL_ORIGINAL_US_SPY_HYG_IEF_FULL_V2"]
    assert abs(prior_us["cagr"]-actual_us["cagr"])<1e-10
    assert abs(prior_us["maxdd"]-actual_us["maxdd"])<1e-10
    deltas={}
    for state in ("EU_REFERENCES","ORIGINAL_US_SPY_HYG_IEF"):
        for variant in ("FULL_HYBRID24","FULL_V2",
                 "TOP2_NO_STOP_NO_RISK","TOP2_GROSS_DD_NO_STOPS"):
            old=metrics["MA3_ORIGINAL_"+state+"_"+variant]
            new=metrics["ADAPT4_"+state+"_"+variant]
            deltas[state+"_"+variant]=dict(
                   cagr_gain_pp=100*(new["cagr"]-old["cagr"]),
                   maxdd_gain_pp=100*(new["maxdd"]-old["maxdd"]))
    pd.DataFrame(daily).to_csv(out/"SOURCE_ETFTRADER_V2_DAILY_OPEN_EUR_NAV_US_AND_EU_RISK.csv",index=False)
    pd.DataFrame(interventions).to_csv(out/"SOURCE_ETFTRADER_V2_ALL_MONTHLY_LEADERS_AND_INTERVENTIONS.csv",index=False)
    report=dict(
       status="EU48_CAUSAL_ADAPT4_REPLAY_IN_SOURCE_V2_WITH_ORIGINAL_US_SPY_HYG_IEF_COMPLETE",
       n_legal_europe_funds=48,n_american_candidates=0,
       first_trade="2021-02-01",last_trade="2026-07-01",
       n_months=65,n_daily_common_Europe_opens=1374,
       original_MA3_EU_source_V2_daily_parity_1e11=True,
       original_MA3_original_US_macro_reference_risk_CAGR_and_DD_parity_1e10=True,
       only_predictive_score_replaced_new_ADAPT4_from_asof_online_frozen=True,
       other_original_V2_cash_risk_and_stops_unchanged=True,
       full_V2_agreement_ET_XGB_old_source_predictions_always_validated=True,
       original_US_SPY_HYG_IEF_risk_reference_USD_derived_previous_bar=True,
       only_EUR_IBCA_IBCN_defensive_sleeve_tradeable_EUR_funds=True,
       no_US_fund_in_predictive_48_candidate_set=True,
       risk_reference_original_2026_survivor_fund_PIT_caveat=True,
       risk_intraday_vendor_HighLow_49_repair_caveat=True,
       all_exact_costed_economic_metrics=metrics,
       paired_rank_swap_economic_deltas=deltas,
       source_original_online_ADAPT4_predictions_sha=sha(
           SRC/"online_results/CAUSAL_EXPERT_WEIGHTS_AT_EACH_SIGNAL.csv"),
       source_original_MA3_rank_prediction_sha=sha(
           BASE/"MA3_HYBRID24_48_TICKER_PREDICTIONS.csv"),
       production_changed=False)
    (out/"RESULT.json").write_text(json.dumps(report,indent=2,allow_nan=False)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(sha(p)+"  "+str(p.relative_to(out))+"\n"
       for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("CAUSAL_ADAPT4_REAL_ETF_V2_USREF_FINAL",json.dumps(report),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--prep",required=True)
    p.add_argument("--us",required=True)
    p.add_argument("--fx",required=True)
    p.add_argument("--out",required=True)
    args=p.parse_args();main(args.prep,args.us,args.fx,args.out)
