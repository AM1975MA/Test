"""Pure read-only source-backed stage and realized-path audit (no new models)."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
from paper_ltr_v2.summarize_replay import metrics

STAGES=("COMPACT21","TITANIUM","PRE_ALLOCATION")
CUTOFF=pd.Timestamp("2026-07-01")
SOURCES=(1,2,3)
EXPECTED_CANDIDATE="RETURN_RANK_NDCG"

def sha(p):
    h=hashlib.sha256()
    with Path(p).open("rb") as f:
        for chunk in iter(lambda:f.read(1<<20),b""):h.update(chunk)
    return h.hexdigest()

def check_exact_keys(a,b,fields=("signal_date","ticker")):
    aa=a[list(fields)].sort_values(list(fields)).reset_index(drop=True)
    bb=b[list(fields)].sort_values(list(fields)).reset_index(drop=True)
    if aa.duplicated().any() or bb.duplicated().any() or not aa.equals(bb):
        raise ValueError("Different, missing or duplicate forecast keys")

def load_predictions(root,variant,expected_status):
    folder=Path(root);result=json.loads((folder/"RESULT.json").read_text())
    if result.get("variant")!=variant or result.get("status")!=expected_status:
        raise ValueError("Predictive archive variant or status wrong")
    if set(result.get("per_year",{}))!=set(map(str,range(2017,2027))):
        raise ValueError("Incomplete annual predictive period")
    if variant==EXPECTED_CANDIDATE and result.get("ALL_MATURITY_PASS") is not True:
        raise ValueError("Candidate was not fully label-mature")
    tables={}
    for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
        file=folder/name
        if result.get("files_sha256",{}).get(name)!=sha(file):
            raise ValueError("Unverified immutable parquet "+name)
        f=pd.read_parquet(file)
        f["signal_date"]=pd.to_datetime(f["signal_date"])
        f["vintage"]=f["vintage"].astype(str)
        if f.duplicated(["vintage","signal_date","ticker"]).any():
            raise ValueError("Duplicate prediction key")
        tables[name]=f
    return result,tables

def numeric_frame(frame,column):
    f=frame[["signal_date","ticker",column]].copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    if f.duplicated(["signal_date","ticker"]).any():
        raise ValueError("Stage has duplicate key")
    if not np.isfinite(f[column].to_numpy(float)).all():
        raise ValueError("Stage contains nonfinite scores")
    return f.sort_values(["signal_date","ticker"]).reset_index(drop=True)

def preallocation(ensemble):
    """Exact frozen stage19.score_matrix, chronological tail lags."""
    f=ensemble.copy()
    f["signal_date"]=pd.to_datetime(f["signal_date"])
    for col in ("BASE","ET_TAIL","XGB_TAIL","TAIL_HYBRID"):
        if col not in f:raise ValueError("Missing original ensemble channel "+col)
    if len(f.groupby("signal_date").size().unique())!=1:
        raise ValueError("Unequal monthly cohort size")
    idx=sorted(f.signal_date.unique())
    tickers=sorted(f.ticker.unique())
    if len(idx)!=114 or len(tickers)!=149 or len(f)!=114*149:
        raise ValueError("Not original monthly Original149 full coverage")
    piv={col:f.pivot(index="signal_date",columns="ticker",values=col).reindex(index=idx,columns=tickers)
        for col in ("BASE","ET_TAIL","XGB_TAIL")}
    if any(not np.isfinite(z.to_numpy(float)).all() for z in piv.values()):
        raise ValueError("Missing preallocation cohort")
    tail=.6*piv["ET_TAIL"]+.4*piv["XGB_TAIL"]
    lag1=pd.concat([tail.iloc[[0]],tail.iloc[:-1]],ignore_index=True)
    lag2=pd.concat([tail.iloc[[0]],tail.iloc[[0]],tail.iloc[:-2]],ignore_index=True)
    lag1.index=tail.index;lag2.index=tail.index
    smooth=.4*tail+.3*lag1+.3*lag2
    score=.475*piv["BASE"]+.525*np.power(np.clip(smooth,0,1),1.10)
    z=score.stack().rename("score").reset_index().rename(columns={"level_0":"signal_date","level_1":"ticker"})
    return numeric_frame(z,"score")

def leaders(frame,col):
    x=frame.sort_values(["signal_date",col,"ticker"],ascending=[True,False,True],kind="stable")
    return {pd.Timestamp(date):list(g.ticker.iloc[:5]) for date,g in x.groupby("signal_date",sort=True)}

def one_stage(vintage,stage,b,c,lab):
    check_exact_keys(b,c)
    label=lab.set_index(["signal_date","ticker"])
    a=leaders(b,b.columns[-1]);z=leaders(c,c.columns[-1])
    if set(a)!=set(z) or len(a)!=114:raise ValueError("Stage calendar truncated")
    records=[]
    for day in sorted(a):
        x,y=a[day],z[day]
        if len(x)!=5 or len(y)!=5:raise ValueError("Top5 incomplete")
        rows=[]
        for ticker in (x[0],y[0]):
            try:r=label.loc[(day,ticker)]
            except KeyError as e:raise ValueError("Missing realized label") from e
            mature=pd.notna(r["exit_date_21"]) and pd.Timestamp(r["exit_date_21"])<=CUTOFF
            rows.append((bool(mature),float(r["target_ret_21"]) if mature else None,
                float(r["target_rank_21"]) if mature else None))
        if rows[0][0]!=rows[1][0]:raise ValueError("Maturity differs by selected ticker")
        records.append(dict(vintage=vintage,signal_date=day.strftime("%Y-%m-%d"),year=day.year,
            stage=stage,base_top1=x[0],candidate_top1=y[0],
            top1_switched=x[0]!=y[0],top5_overlap_fraction=len(set(x)&set(y))/5.,
            mature=rows[0][0],base_future_return=rows[0][1],
            candidate_future_return=rows[1][1],base_realized_percentile=rows[0][2],
            candidate_realized_percentile=rows[1][2],
            selection_return_delta=(rows[1][1]-rows[0][1]) if rows[0][0] else None))
    return records

def monthly_merge_parity(replay,base_comp,cand_comp):
    annual=pd.read_csv(replay/"candidate"/"ANNUAL_PREDICTIONS.csv",float_precision="round_trip")
    annual["signal_date"]=pd.to_datetime(annual.signal_date)
    f=numeric_frame(annual,"compact21")
    g=numeric_frame(cand_comp,"pred")
    check_exact_keys(f,g)
    if not np.allclose(f.compact21.to_numpy(float),g.pred.to_numpy(float),rtol=0,atol=1e-12):
        raise ValueError("V2 replay was not fed exact candidate Compact21 predictions")

def pairwise_source_disagreement(tables):
    dates=sorted(set.intersection(*(set(x) for x in tables.values())))
    if not dates or any(len(x)!=len(dates) for x in tables.values()):
        raise ValueError("Inconsistent dates between vintages")
    n=sum(len({tables[v][day][0] for v in SOURCES})>1 for day in dates)
    return dict(queries=len(dates),top1_any_disagreement_fraction=n/len(dates))

def run(inputs,out):
    root=Path(inputs);out=Path(out)
    if out.exists() and any(out.iterdir()):raise ValueError("Output directory must be fresh")
    out.mkdir(parents=True)
    base_result,base=load_predictions(root/"base","BASE","COMPACT21_PREDICTIVE_V2_COMPLETE")
    rank_result,rank=load_predictions(root/"predictive"/"RETURN_RANK_NDCG",
                                      "RETURN_RANK_NDCG","PAPER_LTR_V2_COMPLETE")
    if base_result.get("input_sha256")!=rank_result.get("input_sha256"):
        raise ValueError("BASE and return-rank provenance differ")
    for key in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
        check_exact_keys(base[key],rank[key],("vintage","signal_date","ticker"))
    labelcols=("target_rank_21","target_ret_21","exit_date_21")
    bb=base["NATIVE_PREDICTIONS.parquet"].sort_values(["vintage","signal_date","ticker"]).reset_index(drop=True)
    cc=rank["NATIVE_PREDICTIONS.parquet"].sort_values(["vintage","signal_date","ticker"]).reset_index(drop=True)
    for name in labelcols:
        x,y=bb[name],cc[name]
        if name=="exit_date_21":x=pd.to_datetime(x);y=pd.to_datetime(y)
        if not x.equals(y):raise ValueError("Compared models have different future labels")
    stage_all=[];daily_all=[];years_all=[];paths={}
    source_top1={k:{} for k in STAGES}
    for i in SOURCES:
        path=root/"economic"/f"v2replay-RETURN_RANK_NDCG-r{i}"
        result=json.loads((path/"RESULT.json").read_text())
        if result.get("status")!="PAPER_LTR_V2_CACHE_REPLAY_COMPLETE" or result.get("variant")!=EXPECTED_CANDIDATE or result.get("repeat")!=i:
            raise ValueError("Uncertified replay identity")
        audit=result.get("audit",{})
        if not all((audit["input_linkage"]["PASS"],audit["baseline_replay"]["PASS"],
            audit["candidate_keys_exact_PASS"],audit["other_models_reused_unchanged"])):
            raise ValueError("Original source and unchanged replay parity not certified")
        nativeb=bb[bb.vintage.eq(str(i))].copy()
        nativec=cc[cc.vintage.eq(str(i))].copy()
        if set(nativeb.signal_date.dt.year)!=set(range(2017,2027)):
            raise ValueError("Missing annual Compact21 inference")
        nativeb["exit_date_21"]=pd.to_datetime(nativeb.exit_date_21)
        monthly_merge_parity(path,nativeb,nativec)
        stage_inputs={
            "COMPACT21":(numeric_frame(nativeb,"pred"),numeric_frame(nativec,"pred")),
        }
        tit={}
        ens={}
        for target,folder in (("BASE","baseline_control"),("CANDIDATE","candidate")):
            t=pd.read_csv(path/folder/"TIT_R_SOURCE_ONLY.csv",float_precision="round_trip")
            tit[target]=numeric_frame(t,"TIT_R")
            e=pd.read_csv(path/folder/"ENSEMBLE_TAIL_OOS.csv",float_precision="round_trip")
            e["signal_date"]=pd.to_datetime(e.signal_date)
            ens[target]=e
        stage_inputs["TITANIUM"]=(tit["BASE"],tit["CANDIDATE"])
        stage_inputs["PRE_ALLOCATION"]=(preallocation(ens["BASE"]),preallocation(ens["CANDIDATE"]))
        unmodified=("ET_TAIL","XGB_TAIL","TAIL_HYBRID")
        old=ens["BASE"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        new=ens["CANDIDATE"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        check_exact_keys(old,new)
        if any(not np.array_equal(old[col].to_numpy(float),new[col].to_numpy(float)) for col in unmodified):
            raise ValueError("Other portfolio ensemble signals changed")
        # The only preallocator difference MUST be .475 times Titanium score movement.
        l=stage_inputs["PRE_ALLOCATION"]
        check_exact_keys(*l)
        titb,titc=stage_inputs["TITANIUM"]
        check_exact_keys(titb,titc)
        dscore=l[1].score.to_numpy(float)-l[0].score.to_numpy(float)
        dtitanium=titc.TIT_R.to_numpy(float)-titb.TIT_R.to_numpy(float)
        max_mechanical_error=float(np.max(np.abs(dscore-.475*dtitanium)))
        if max_mechanical_error>1e-12:
            raise ValueError(f"Stage19 exact score identity failed: {max_mechanical_error}")
        for stage,(b,c) in stage_inputs.items():
            rows=one_stage(i,stage,b,c,nativeb)
            stage_all.extend(rows)
            source_top1[stage][i]={pd.Timestamp(r["signal_date"]):[r["base_top1"],r["candidate_top1"]] for r in rows}
        source_paths={}
        for target,folder,field in (("BASE","baseline_control","baseline"),("RANK","candidate","candidate")):
            x=np.load(path/folder/"FULL_UNIVERSE_PATH.npz",allow_pickle=False)
            observed,dates=metrics(path/folder/"FULL_UNIVERSE_PATH.npz")
            expected=result[field]["v2_full_universe"]
            error=max(abs(observed[key]-float(expected[key])) for key in observed)
            if error>1e-12:raise ValueError("Original equity path metrics mismatch")
            if x["equity"].shape!=(1,2366) or x["d1"].shape!=(1,2366):
                raise ValueError("Unexpected canonical daily path dimensions")
            source_paths[target]={key:x[key].copy() for key in x.files}
            source_paths[target]["calendar"]=dates
        b=source_paths["BASE"];c=source_paths["RANK"]
        if not b["calendar"].equals(c["calendar"]):raise ValueError("Different source daily calendars")
        paths[str(i)]=dict(
            base_cagr=float(result["baseline"]["v2_full_universe"]["cagr"]),
            rank_cagr=float(result["candidate"]["v2_full_universe"]["cagr"]),
            baseline_maxdd=float(result["baseline"]["v2_full_universe"]["maxdd"]),
            rank_maxdd=float(result["candidate"]["v2_full_universe"]["maxdd"]),
            baseline_sharpe=float(result["baseline"]["v2_full_universe"]["sharpe"]),
            rank_sharpe=float(result["candidate"]["v2_full_universe"]["sharpe"]),
            stage19_delta_identity_max_abs=max_mechanical_error)
        beq=b["equity"][0].astype(float);ceq=c["equity"][0].astype(float)
        diff=np.diff(np.log(np.r_[1.,ceq]))-np.diff(np.log(np.r_[1.,beq]))
        if abs(float(diff.sum())-float(np.log(ceq[-1]/beq[-1])))>1e-12:
            raise ValueError("Log equity difference is not additive")
        for k,date in enumerate(b["calendar"]):
            same_d1=bool(b["d1"][0,k]==c["d1"][0,k])
            same_d2=bool(b["d2"][0,k]==c["d2"][0,k])
            case="same_top1_top2" if same_d1 and same_d2 else (
                "same_top1_changed_top2" if same_d1 else "different_top1")
            daily_all.append(dict(vintage=i,date=pd.Timestamp(date).strftime("%Y-%m-%d"),
                year=int(date.year),d1_switched=not same_d1,
                d2_switched=not same_d2,ordered_pair_switched=not(same_d1 and same_d2),
                alt_switched=bool(b["alt_idx"][0,k]!=c["alt_idx"][0,k]),
                weight_abs_delta=float(abs(c["weight1"][0,k]-b["weight1"][0,k])),
                margin_abs_delta=float(abs(c["margin"][0,k]-b["margin"][0,k])),
                turnover_delta=float(c["turnover"][0,k]-b["turnover"][0,k]),
                log_equity_delta=float(diff[k]),case=case))
        for year in range(2017,2027):
            year_entries=[z for z in daily_all if z["vintage"]==i and z["year"]==year]
            years_all.append(dict(vintage=i,year=year,days=len(year_entries),
                log_equity_advantage=float(sum(z["log_equity_delta"] for z in year_entries)),
                return_advantage_factor=float(np.expm1(sum(z["log_equity_delta"] for z in year_entries)))))
    stage=pd.DataFrame(stage_all)
    daily=pd.DataFrame(daily_all)
    yearly=pd.DataFrame(years_all)
    stage.to_csv(out/"MONTHLY_STAGE_TRANSITIONS.csv",index=False)
    daily.to_csv(out/"DAILY_PATH_ACCOUNTING.csv",index=False)
    yearly.to_csv(out/"ANNUAL_LOG_ADVANTAGE.csv",index=False)
    stage_summary={}
    for name in STAGES:
        subset=stage[stage.stage==name]
        good=subset[subset.mature]
        sources={}
        for i in SOURCES:
            s=subset[subset.vintage==i]
            g=good[good.vintage==i]
            sources[str(i)]=dict(
                top1_change_fraction=float(s.top1_switched.mean()),
                monthly_top5_overlap=float(s.top5_overlap_fraction.mean()),
                base_chosen_return=float(g.base_future_return.mean()),
                candidate_chosen_return=float(g.candidate_future_return.mean()),
                return_delta=float(g.selection_return_delta.mean()))
        stage_summary[name]=dict(source=sources,
            months=len(subset),mature_evaluations=len(good),
            top1_switch_fraction=float(subset.top1_switched.mean()),
            top5_overlap=float(subset.top5_overlap_fraction.mean()),
            mean_base_chosen_return=float(good.base_future_return.mean()),
            mean_candidate_chosen_return=float(good.candidate_future_return.mean()),
            mean_chosen_return_difference=float(good.selection_return_delta.mean()))
    daily_summary={}
    for i,g in daily.groupby("vintage"):
        groups={case:float(rows.log_equity_delta.sum()) for case,rows in g.groupby("case")}
        daily_summary[str(i)]=dict(
            sessions=len(g),changed_top1=float(g.d1_switched.mean()),
            changed_top2=float(g.d2_switched.mean()),
            changed_either=float(g.ordered_pair_switched.mean()),
            changed_v6_alternative=float(g.alt_switched.mean()),
            mean_abs_first_weight_delta=float(g.weight_abs_delta.mean()),
            fraction_first_weight_delta_over_1pp=float((g.weight_abs_delta>.01).mean()),
            mean_abs_margin_delta=float(g.margin_abs_delta.mean()),
            mean_turnover_delta=float(g.turnover_delta.mean()),
            delta_log_equity=float(g.log_equity_delta.sum()),
            noncausal_delta_log_equity_partition=groups)
    # Cross-vintage monthly Top1 disagreement. Three vintages, each containing
    # a BASE and candidate ticker for an identical 114-date calendar.
    stability={}
    for st,src in source_top1.items():
        dates=sorted(set.intersection(*(set(x) for x in src.values())))
        if len(dates)!=114:raise ValueError("Cross-vintage monthly dates differ")
        stability[st]=dict(months=len(dates),
            BASE_fraction=sum(len({src[i][date][0] for i in SOURCES})>1 for date in dates)/len(dates),
            RETURN_RANK_fraction=sum(len({src[i][date][1] for i in SOURCES})>1 for date in dates)/len(dates))
    summary=dict(status="COMPACT21_RETURN_RANK_STAGE_ATTRIBUTION_COMPLETE",
        source_runs=dict(BASE=37229180477,RETURN_RANK=39031200131),
        predeclared_protocol_sha256=sha(Path(__file__).with_name("PROTOCOL.md")),
        stages=stage_summary,monthly_cross_vintage_disagreement=stability,
        daily=daily_summary,equity_paths=paths,
        aggregate=dict(mean_base_cagr=float(np.mean([v["base_cagr"] for v in paths.values()])),
            mean_rank_cagr=float(np.mean([v["rank_cagr"] for v in paths.values()])),
            observed_portfolio_cagr_advantage_pp=100*float(np.mean([v["rank_cagr"]-v["base_cagr"] for v in paths.values()])),
            sessions_per_source=2366,
            all_baseline_parities_PASS=True,
            exact_stage19_formula_PASS=True,
            unchanged_external_ensemble_signals_PASS=True,
            forward_targets_used_only_for_evaluation=True),
        definitions=dict(log_equity_partition="Contemporaneous path-dependent descriptive accounting, NOT causal selection versus risk attribution",
            CAGR="Geometric annualized return of full 2366-session V2 portfolio",
            benchmark_caveat="Three correlated Yahoo revisions of repeatedly reused 2017-2026 history; no statistical independent validation"),
        new_models_trained=0,new_replays_run=0,production_adoption=False)
    (out/"REPORT.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps(dict(status=summary["status"],stages={
        s:dict(changed=q["top1_switch_fraction"],base_future_return=q["mean_base_chosen_return"],
              rank_future_return=q["mean_candidate_chosen_return"]) for s,q in stage_summary.items()},
        daily=daily_summary,aggregate=summary["aggregate"]),indent=2),flush=True)
    return summary

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--inputs",required=True);p.add_argument("--out",required=True)
    a=p.parse_args();run(a.inputs,a.out)
