"""Read-only eight-arm ETF ranking and full V2 replay factorial."""
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from paper_ltr_v2.replay import read_frame,write_state,load_compare,one,sha
from paper_ltr_v2.summarize_replay import metrics
from compact21_tail_factorial_v1.source import verify_archives,load_titanium,load_ensemble,verify_exact_original
from compact21_tail_factorial_v1.replay import replay
from compact21_tail_factorial_v1.score import titanium_score
from compact21_tail_factorial_v1.diagnostics import monthly_quality,fixed_5050
def arm_name(l,t,h):return f"{'B' if l=='BASE' else 'R'}_T{t}_H{h}"
ARMS=[(l,t,h) for l in ("BASE","RETURN_RANK_NDCG") for t in (0,1) for h in (0,1)]
def main():
    p=argparse.ArgumentParser()
    for key in ("raw","cache","archive","base","rank","out"):p.add_argument("--"+key,required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError("Fresh output path required")
    out.mkdir(parents=True)
    verify_archives(a.base,a.rank)
    tables={}
    for learner,path in (("BASE",Path(a.base)),("RETURN_RANK_NDCG",Path(a.rank)/"RETURN_RANK_NDCG")):
        tables[learner]=pd.read_parquet(path/"NATIVE_PREDICTIONS.parquet")
    rows=[];signals=[];years=[];fixed=[]
    for vintage in (1,2,3):
        src=Path(a.archive)/f"v2replay-RETURN_RANK_NDCG-r{vintage}"
        prior=json.loads((src/"RESULT.json").read_text())
        if (prior.get("repeat")!=vintage or prior["audit"]["baseline_replay"]["PASS"] is not True
            or prior["audit"]["input_linkage"]["PASS"] is not True):
            raise ValueError("Unverified original canonical V2")
        raw=Path(a.raw)/f"_repeat{vintage}"
        compare=load_compare(raw)
        tickers=compare.load_universe(raw).ticker.tolist()
        if len(tickers)!=149:raise ValueError("Expected exactly 149 economic ETFs")
        opens=compare.load_ticker_csv_folder(raw)[0]["Open"].reindex(columns=tickers)
        panel_path=one(Path(a.cache)/f"r{vintage}","RAW_FEATURE_PANEL.pkl")
        for learner,t_on,h_on in ARMS:
            name=arm_name(learner,t_on,h_on)
            tit=load_titanium(src,learner,t_on)
            ensemble=load_ensemble(src,tit)
            cal=tit[["signal_date","entry_date","exit_date"]].drop_duplicates().sort_values("signal_date").reset_index(drop=True)
            if len(cal)!=114:raise ValueError("Missing monthly decisions")
            inputs=ensemble.rename(columns={"ET_TAIL":"ET_RANK","XGB_TAIL":"XGB_RANK"})
            score=(compare.stage19.score_matrix(inputs,cal,tickers) if h_on else
                   titanium_score(ensemble,cal.signal_date,tickers))
            if not np.isfinite(score).all():raise ValueError("Missing factorial score")
            label=tables[learner]
            mask=label.vintage.astype(str).eq(str(vintage))
            qs=monthly_quality(score,cal,tickers,label[mask])
            signals.extend(dict(arm=name,vintage=vintage,**q) for q in qs)
            fx=fixed_5050(cal,score,tickers,opens)
            fixed.append(dict(arm=name,vintage=vintage,**fx))
            state=write_state(out/name/f"r{vintage}",raw,tickers,tit,ensemble,panel_path)
            met=replay(compare,state,bool(h_on))
            actual,dates=metrics(state["base"]/"FULL_UNIVERSE_PATH.npz")
            for key in ("cagr","maxdd","sharpe","terminal_equity"):
                if abs(actual[key]-met["v2_full_universe"][key])>1e-12:
                    raise ValueError("Independent economic replay metric differs")
            if t_on and h_on:
                ref=src/("baseline_control" if learner=="BASE" else "candidate")
                verify_exact_original(state["base"]/"FULL_UNIVERSE_PATH.npz",ref)
            with np.load(state["base"]/"FULL_UNIVERSE_PATH.npz",allow_pickle=False) as z:
                logret=np.diff(np.log(np.r_[1.,z["equity"][0]]))
                for year in range(2017,2027):
                    years.append(dict(arm=name,vintage=vintage,year=year,
                        return_pct=100*float(np.expm1(logret[dates.year==year].sum()))))
            rows.append(dict(arm=name,learner=learner,titanium_tail=t_on,ma3_tail=h_on,
                vintage=vintage,cagr=actual["cagr"],maxdd=actual["maxdd"],
                sharpe=actual["sharpe"],turnover=met["v2_full_universe"]["annualized_turnover"]))
            print(json.dumps(dict(arm=name,vintage=vintage,cagr=actual["cagr"],
                selection_return=float(np.mean([x["ret"] for x in qs if x["mature"]])))),flush=True)
    pd.DataFrame(rows).to_csv(out/"ECONOMICS.csv",index=False)
    pd.DataFrame(signals).to_csv(out/"MONTHLY_QUALITY.csv",index=False)
    pd.DataFrame(years).to_csv(out/"ANNUAL_RETURN.csv",index=False)
    pd.DataFrame(fixed).to_csv(out/"FIXED_5050.csv",index=False)
    print("ALL_24_FACTORIAL_REPLAYS_COMPLETE",flush=True)
if __name__=="__main__":main()
