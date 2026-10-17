"""Independent audit and source-aligned counterfactual contrasts."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from paper_ltr_v2.summarize_replay import metrics
from paper_ltr_v2.replay import sha

NAMES=["H_H","R_R","H_R","R_H","H_HALF","R_HALF","ET_ONLY","XGB_ONLY","RIDGE_ONLY"]
def main():
    p=argparse.ArgumentParser();p.add_argument("--root",required=True)
    root=Path(p.parse_args().root)
    eco=pd.read_csv(root/"ECONOMICS.csv")
    mon=pd.read_csv(root/"MONTHLY_QUALITY.csv")
    ann=pd.read_csv(root/"ANNUAL_RETURN.csv")
    simple=pd.read_csv(root/"FIXED_5050.csv")
    if len(eco)!=27 or set(eco.policy)!=set(NAMES):
        raise ValueError("Missing precommitted 27 paths")
    if len(mon)!=27*114 or len(mon[mon.mature])!=27*113:
        raise ValueError("Missing source-aligned maturity dates")
    if eco.groupby("policy").vintage.nunique().ne(3).any():raise ValueError("Source loss")
    if len(ann)!=270 or len(simple)!=15:raise ValueError("Missing precommitted comparison table")
    derived=[];daily={}
    for policy in NAMES:
        g=eco[eco.policy.eq(policy)].sort_values("vintage")
        s=mon[mon.policy.eq(policy)&mon.mature]
        by_vintage=[];calendar=None
        for v in (1,2,3):
            x=root/policy/f"r{v}"/"FULL_UNIVERSE_PATH.npz"
            obs,dates=metrics(x)
            saved=g[g.vintage.eq(v)]
            if len(saved)!=1:raise ValueError("Missing source comparison")
            for metric in ("cagr","maxdd","sharpe","terminal_equity"):
                if abs(float(saved[metric].iloc[0])-obs[metric])>1e-12:
                    raise ValueError("Independent equity numerical audit mismatch")
            with np.load(x,allow_pickle=False) as z:
                d1=z["d1"][0].astype(int)
                d2=z["d2"][0].astype(int)
                wg=z["weight1"][0].astype(float)
                if len(d1)!=2366 or np.any((d1<0)|(d1>=149)) or np.any((d2<0)|(d2>=149)):
                    raise ValueError("Unexpected original149 daily holdings")
                if calendar is None:calendar=dates
                elif not calendar.equals(dates):raise ValueError("Different daily markets")
                by_vintage.append(d1)
        d=np.column_stack(by_vintage)
        diff=float(np.mean(np.any(d!=d[:,[0]],axis=1)))
        daily[policy]=diff
        derived.append(dict(policy=policy,selector=g.selector.iloc[0],weight_source=g.weight_source.iloc[0],
            mean_cagr=float(g.cagr.mean()),cagr_span_pp=100*float(g.cagr.max()-g.cagr.min()),
            mean_maxdd=float(g.maxdd.mean()),mean_sharpe=float(g.sharpe.mean()),
            mean_turnover=float(g.annualized_turnover.mean()),
            source_cagr=[float(n) for n in g.cagr],
            daily_source_top1_disagreement=diff,
            standalone_top1_21d=float(s.ret.mean()),standalone_regret_21d=float(s.regret.mean()),
            exact_winner_rate=float(s.exact_hit.mean()),actual_top5_hit=float(s.top5_hit.mean()),
            top5_overlap=float(s.overlap.mean())))
    summary=pd.DataFrame(derived)
    summary.drop(columns="source_cagr").to_csv(root/"AGGREGATE.csv",index=False)
    prior={r["policy"]:r for r in derived}
    # Counterfactual 2x2 repeated with same raw and all original risk:
    # This matrix contains selector × independent weight-schedule interventions.
    contrasts=dict(
        R_vs_H_when_weight_H_cagr_pp=100*(prior["R_H"]["mean_cagr"]-prior["H_H"]["mean_cagr"]),
        R_vs_H_when_weight_R_cagr_pp=100*(prior["R_R"]["mean_cagr"]-prior["H_R"]["mean_cagr"]),
        weight_R_vs_H_given_selector_H_cagr_pp=100*(prior["H_R"]["mean_cagr"]-prior["H_H"]["mean_cagr"]),
        weight_R_vs_H_given_selector_R_cagr_pp=100*(prior["R_R"]["mean_cagr"]-prior["R_H"]["mean_cagr"]),
        interaction_in_CAGR_pp=100*(prior["R_R"]["mean_cagr"]-prior["R_H"]["mean_cagr"]
            -prior["H_R"]["mean_cagr"]+prior["H_H"]["mean_cagr"]),
        R_vs_H_under_fixed_half_V2_cagr_pp=100*(prior["R_HALF"]["mean_cagr"]-prior["H_HALF"]["mean_cagr"]),
        R_vs_H_standalone_21d_pp=100*(prior["R_R"]["standalone_top1_21d"]-prior["H_H"]["standalone_top1_21d"]),
        fixed_monthly_H_cagr=float(simple[simple.policy.eq("H_H")].cagr.mean()),
        fixed_monthly_R_cagr=float(simple[simple.policy.eq("R_R")].cagr.mean()))
    meta=json.loads((root/"MANIFEST.json").read_text())
    if meta["reference_R_T0_H1_exact_path_parity"] is not True:
        raise ValueError("Canonical base parity not certified")
    result=dict(status="TAIL_ONLY_AND_WEIGHT_MEDIATION_COMPLETE",
        reference_original_run=39058118631,replayed_original149=True,
        canonical_R_T0_H1_all_daily_arrays_exact_PARITY=True,
        all_27_daily_full_V2_replays_PASS=True,
        full_independent_equity_recomputation_PASS=True,
        days_per_source=2366,sources=3,monthly_signals=114,mature_monthly_signals=113,
        models=derived,paired_counterfactuals=contrasts,
        fixed_half_diagnostics=[dict(policy=p,
            cagr_mean=float(simple[simple.policy.eq(p)].cagr.mean())) for p in ("H_H","R_R","ET_ONLY","XGB_ONLY","RIDGE_ONLY")],
        years=ann.to_dict(orient="records"),protocol_sha256=meta["protocol_sha256"],
        no_new_training=True,production_unchanged=True,
        caveat="Repeatedly studied 2017-2026 Yahoo source revisions not independent. Borrowed source weights and margins are artificial but valid replay interventions, not forecasted deployable allocation policies.")
    (root/"SUMMARY.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(summary.drop(columns="source_cagr").round(6).to_string(index=False),flush=True)
    print(json.dumps(contrasts,indent=2),flush=True)
if __name__=="__main__":main()
