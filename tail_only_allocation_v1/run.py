"""Run fixed Tail-only ablation and independent selector/weight interventions."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from paper_ltr_v2.replay import read_frame,write_state,load_compare,one,sha
from paper_ltr_v2.summarize_replay import metrics
from compact21_tail_factorial_v1.source import verify_exact_original
from compact21_tail_factorial_v1.diagnostics import monthly_quality,fixed_5050
from tail_only_allocation_v1.scores import score_channel,ridge_tail_only
from tail_only_allocation_v1.intervene import run_replay

POLICIES=(
    ("H_H","H","H",True),("R_R","R","R",True),
    ("H_R","H","R",True),("R_H","R","H",True),
    ("H_HALF","H","HALF",True),("R_HALF","R","HALF",True),
    ("ET_ONLY","ET","ET",False),("XGB_ONLY","XGB","XGB",False),
    ("RIDGE_ONLY","RIDGE","RIDGE",False),
)
def run(opts):
    output=Path(opts.out)
    if output.exists() and any(output.iterdir()):raise ValueError("Output must be new")
    output.mkdir(parents=True)
    source=Path(opts.original)
    original_factors=pd.read_csv(source/"ECONOMICS.csv")
    original_fixed=pd.read_csv(source/"FIXED_5050.csv")
    if len(original_factors)!=24:raise ValueError("Preceding full factorial not certified")
    rows=[];qualities=[];simple=[];yearlies=[]
    for vintage in (1,2,3):
        original=source/"R_T0_H1"/f"r{vintage}"
        record=json.loads((original/"RESULT.json").read_text())
        if record.get("candidate_count")!=149 or record.get("sessions")!=2366:
            raise ValueError("Prior R + MA3 path missing canonical universe")
        raw=Path(opts.raw)/f"_repeat{vintage}"
        compare=load_compare(raw)
        tickers=compare.load_universe(raw).ticker.tolist()
        if len(tickers)!=149:raise ValueError("Not Original149")
        r_tit=read_frame(original/"TIT_R_SOURCE_ONLY.csv")
        ens=read_frame(original/"ENSEMBLE_TAIL_OOS.csv")
        cal=r_tit[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
        if len(cal)!=114:raise ValueError("Monthly original calendar not 114")
        annual=read_frame(one(Path(opts.cache)/f"r{vintage}","ANNUAL_PREDICTIONS.csv"))
        scores=dict(
            H=score_channel(ens,cal,tickers,"HYBRID"),
            ET=score_channel(ens,cal,tickers,"ET"),
            XGB=score_channel(ens,cal,tickers,"XGB"),
            RIDGE=ridge_tail_only(annual,cal,tickers),
            R=compare.stage19.score_matrix(
                ens.rename(columns={"ET_TAIL":"ET_RANK","XGB_TAIL":"XGB_RANK"}),cal,tickers))
        reference_fixed=original_fixed[
            original_fixed.arm.eq("R_T0_H1")&original_fixed.vintage.eq(vintage)]
        opens=compare.load_ticker_csv_folder(raw)[0]["Open"].reindex(columns=tickers)
        check_simple=fixed_5050(cal,scores["R"],tickers,opens)
        if len(reference_fixed)!=1 or abs(float(reference_fixed.cagr.iloc[0])-check_simple["cagr"])>1e-12:
            raise ValueError("Original 50/50 comparator not exactly reproduced")
        panel=one(Path(opts.cache)/f"r{vintage}","RAW_FEATURE_PANEL.pkl")
        labels=pd.read_parquet(Path(opts.rank)/"RETURN_RANK_NDCG"/"NATIVE_PREDICTIONS.parquet")
        labels=labels[labels.vintage.astype(str).eq(str(vintage))]
        if labels.signal_date.nunique()!=114:raise ValueError("Missing forward-quality dates")
        for policy,selector,weights,agreement in POLICIES:
            selected=scores[selector]
            borrowed=(selected if weights in (selector,"HALF") else scores[weights])
            quality=monthly_quality(selected,cal,tickers,labels)
            qualities.extend(dict(vintage=vintage,policy=policy,selector=selector,**item) for item in quality)
            if weights==selector:
                fixed=fixed_5050(cal,selected,tickers,opens)
                simple.append(dict(vintage=vintage,policy=policy,**fixed))
            destination=output/policy/f"r{vintage}"
            state=write_state(destination,raw,tickers,r_tit,ens,panel)
            outcome=run_replay(compare,state,selected,borrowed,
                force_equal_weight=weights=="HALF",ma3_agreement=agreement,
                monthly_dates=cal.signal_date)
            path=state["base"]/"FULL_UNIVERSE_PATH.npz"
            met,dates=metrics(path)
            for key in ("cagr","maxdd","sharpe","terminal_equity"):
                if abs(float(outcome["v2_full_universe"][key])-met[key])>1e-12:
                    raise ValueError("Equity path metric mismatch "+policy)
            if policy=="R_R":
                verify_exact_original(path,original)
                expected=original_factors[
                    original_factors.arm.eq("R_T0_H1")&original_factors.vintage.eq(vintage)]
                if len(expected)!=1 or abs(float(expected.cagr.iloc[0])-met["cagr"])>1e-12:
                    raise ValueError("Archived R+MA3 canonical benchmark differs")
            with np.load(path,allow_pickle=False) as data:
                chosen_top1=data["d1"][0].copy();chosen_top2=data["d2"][0].copy()
                first_weight=data["weight1"][0].copy()
                logret=np.diff(np.log(np.r_[1.,data["equity"][0]]))
                for year in range(2017,2027):
                    yearlies.append(dict(vintage=vintage,policy=policy,year=year,
                        simple_return=float(np.expm1(logret[dates.year==year].sum()))))
            rows.append(dict(vintage=vintage,policy=policy,selector=selector,
                weight_source=weights,ma3_agreement=agreement,
                cagr=met["cagr"],maxdd=met["maxdd"],sharpe=met["sharpe"],
                terminal_equity=met["terminal_equity"],
                annualized_turnover=outcome["v2_full_universe"]["annualized_turnover"],
                daily_top1_id_sha256=__import__("hashlib").sha256(chosen_top1.tobytes()).hexdigest(),
                daily_top2_id_sha256=__import__("hashlib").sha256(chosen_top2.tobytes()).hexdigest(),
                daily_weight_sha256=__import__("hashlib").sha256(first_weight.tobytes()).hexdigest()))
            print(json.dumps(dict(vintage=vintage,policy=policy,
                cagr=met["cagr"],top1_21d=float(np.mean([q["ret"] for q in quality if q["mature"]])))),flush=True)
    pd.DataFrame(rows).to_csv(output/"ECONOMICS.csv",index=False)
    pd.DataFrame(qualities).to_csv(output/"MONTHLY_QUALITY.csv",index=False)
    pd.DataFrame(yearlies).to_csv(output/"ANNUAL_RETURN.csv",index=False)
    pd.DataFrame(simple).to_csv(output/"FIXED_5050.csv",index=False)
    (output/"MANIFEST.json").write_text(json.dumps(dict(status="27_VERIFIED_FULL_V2_REPLAYS",
        policies=[p[0] for p in POLICIES],source_revisions=3,
        canonical_replay_original_RUN=39058118631,
        protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        no_new_fits=True,reference_R_T0_H1_exact_path_parity=True),indent=2)+"\n")
    print("ALL_PURE_TAIL_AND_ALLOCATION_INTERVENTIONS_COMPLETE",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for field in ("original","raw","cache","rank","out"):p.add_argument("--"+field,required=True)
    run(p.parse_args())
