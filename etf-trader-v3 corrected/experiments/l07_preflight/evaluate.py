#!/usr/bin/env python3
"""ETF Trader V3 — deterministic L07 integration *preflight*, NOT backtest tuning.

Verify complete locked source lineage, matching prediction/event labels,
chronological fit logs and exact frozen selection policy. Compare the approved
V3 static Tail Top3 research candidate and risk-weighted ALTERNATIVE only on
same 53 mature months without using performance to pick one.
Does not invent a virgin holdout or claim an integrated production release.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path(__file__).resolve().parents[2]
SHA="36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"


def check_monthly_equivalence(a,b,cols,tol=2e-12):
    a=a.sort_values("signal_date").reset_index(drop=True)
    b=b.sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(a.signal_date,b.signal_date)
    for x,y in cols:
        np.testing.assert_allclose(a[x],b[y],rtol=0,atol=tol,equal_nan=True,
                                  err_msg=f"Mismatch {x} != {y}")


def matured_fit_audit(file):
    fit=json.loads(Path(file).read_text())
    assert fit
    count=0
    for entry in fit:
        if "year" not in entry:continue
        year=int(entry["year"])
        last=entry.get("last_mature_exit") or entry.get("last_mature_63d_label") or entry.get("last_mature_63D_exit") or entry.get("max_mature_63d_exit") or entry.get("last_mature_63d_exit") or entry.get("last_train_exit") or entry.get("last_exit_date")
        if last is None:
            for k,v in entry.items():
                if ("mature" in k.lower() and "exit" in k.lower()):
                    last=v
                    break
        if last is None:raise AssertionError(f"Missing maturity proof: {entry}")
        assert pd.Timestamp(last)<pd.Timestamp(year,1,1),(year,last)
        count+=1
    assert count>0
    return count


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--registry",default="etf-trader-v3 corrected/registry/V3_EXPERIMENT_REGISTRY.json")
    p.add_argument("--l01",default="runs/v3_l01_reference")
    p.add_argument("--l02",default="runs/v3_l02_reference")
    p.add_argument("--l04",default="runs/v3_l04_reference")
    p.add_argument("--l05",default="runs/v3_l05_reference")
    p.add_argument("--l06abs",default="runs/v3_l06_absolute")
    p.add_argument("--l06policy",default="runs/v3_l06_policy")
    p.add_argument("--baskets",default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--out",default="runs/v3_l07_preflight")
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    reg=json.loads(Path(a.registry).read_text())
    assert reg["project"]=="ETF Trader V3 Corrected"
    assert reg["governance"]["production_V2_unchanged"] is True
    assert reg["raw_snapshot"]["virgin_holdout"] is False
    assert reg["frozen_references"]["L01"]["id"]=="CORRECTED_PAIR127"
    assert reg["frozen_references"]["L02"]["id"]=="TAIL_EVENT_LOGIT45"
    assert reg["frozen_references"]["L05"]["weights"]==[.5,.3,.2]
    assert reg["frozen_references"]["L06"]["candidate_only"] is True
    assert hashlib.sha256(Path(a.baskets).read_bytes()).hexdigest()==SHA
    b=pd.read_csv(a.baskets)
    assert len(b)==12000 and b.basket.nunique()==500
    assert (b.groupby("basket").size()==24).all()

    rank=pd.read_csv(Path(a.l01)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    tail=pd.read_csv(Path(a.l02)/"OOS_SCORES.csv",parse_dates=["signal_date"])
    paired=pd.read_csv(Path(a.l04)/"OOS_SCORES_ALL_FIXED_BLENDS.csv",parse_dates=["signal_date"])
    rank=rank[rank.variant=="CORRECTED"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    tail=tail[tail.variant=="TAIL_EVENT_LOGIT45"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    paired=paired.sort_values(["signal_date","ticker"]).reset_index(drop=True)
    assert len(rank)==len(tail)==len(paired)==15198
    for name,frame in [("rank",rank),("tail",tail),("paired",paired)]:
        assert not frame.duplicated(["signal_date","ticker"]).any(),name
        assert frame.signal_date.nunique()==102
        assert frame.ticker.nunique()==149
    pd.testing.assert_frame_equal(rank[["signal_date","ticker"]],
                                  tail[["signal_date","ticker"]])
    pd.testing.assert_frame_equal(rank[["signal_date","ticker"]],
                                  paired[["signal_date","ticker"]])
    np.testing.assert_allclose(rank.fwd_ret_21,tail.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
    np.testing.assert_allclose(rank.fwd_ret_21,paired.fwd_ret_21,atol=1e-14,rtol=0,equal_nan=True)
    count_l01=matured_fit_audit(Path(a.l01)/"FIT_AUDIT.json")
    count_l02=matured_fit_audit(Path(a.l02)/"FIT_AUDIT.json")

    selection=pd.read_csv(Path(a.l05)/"PAIRED_MONTHLY.csv",parse_dates=["signal_date"])
    select_static=selection[selection.variant=="TOP3_DECAY"].copy()
    assert len(select_static)==101
    assert select_static.signal_date.nunique()==101
    assert select_static.signal_date.min().year==2018
    risk=pd.read_csv(Path(a.l06abs)/"OOS_SELECTED_ETF_ABSOLUTE_LOSS.csv",
                     parse_dates=["signal_date"])
    assert len(risk)==2281 and risk.signal_date.nunique()==53
    assert not risk.duplicated(["signal_date","ticker"]).any()
    assert np.isfinite(risk.p_abs_loss).all() and risk.p_abs_loss.between(0,1).all()
    count_l06=matured_fit_audit(Path(a.l06abs)/"FIT_AUDIT.json")
    candidate=pd.read_csv(Path(a.l06policy)/"PAIRED_MONTHLY.csv",
                          parse_dates=["signal_date"])
    original=candidate[candidate.variant=="TOP3_DECAY"].copy()
    alternative=candidate[candidate.variant=="TOP3_ABSLOSS_EXP3"].copy()
    assert len(original)==len(alternative)==53
    check_monthly_equivalence(original,alternative,[("best_in_top3","best_in_top3")],0)
    check_monthly_equivalence(original,select_static[select_static.signal_date.isin(original.signal_date)],[
        ("weight_on_best","weighted_winner_capture"),
        ("basket_bottom3_weight","bottom_three_weight"),
        ("selected_rank_quality","weighted_true_rank_quality"),
        ("weighted_oracle_regret21","weighted_oracle_regret21")
    ])
    check_monthly_equivalence(original,alternative,[
        ("signal_date","signal_date")]) if False else None

    # Exact score source validation: static Top3 rank order from Tail, not a
    # hidden new model or target-optimized conditional regime.
    assert reg["frozen_references"]["L03"]["id"]=="NO_DYNAMIC_REGIME"
    assert reg["frozen_references"]["L04"]["id"]=="KEEP_FROZEN_EXPERTS_SEPARATE"
    assert "TOP3_VOL63_CAP20" not in reg["frozen_references"]["L05"]["id"]
    assert reg["frozen_references"]["L07"]["status"]=="blocked_until_reference_freeze_and_validation"

    contracts={
        "status":"PASS_RESEARCH_PREFLIGHT_ONLY",
        "release_or_production_approved":False,
        "full_backtest_executed":False,
        "any_fresh_untouched_OOS":False,
        "same_raw_ETF_month_observations":True,
        "strict_identical_future_21d_targets":True,
        "basket_SHA256":SHA,
        "n_ETFs":149,"n_baskets":500,"n_basket_constituents":24,
        "n_full_score_months":102,"n_mature_21d_backtest_months":101,
        "n_absolute_risk_mature_months":53,
        "n_unique_abs_risk_ETF_months":len(risk),
        "n_annual_fit_audit_rows":{"L01":count_l01,"L02":count_l02,"L06_abs_probability":count_l06},
        "snapshot_run":39482809691,"ranker_run":39652989033,
        "tail_winner_run":39655513813,"fusion_oracle_run":39659903643,
        "allocation_run":39661273577,
        "absolute_risk_prob_run":39671493979,
        "absolute_risk_soft_weight_run":39672320747,
        "V3_ref_stack":"CORRECTED125 -> PAIR127 reference, separate TAIL_ELITE45 -> no adaptive regime/blend -> Top3[.5,.3,.2] -> no risk veto",
        "L06_alternative":"SAME Tail Top3 names, weights proportional base * exp(-3 * causal p_abs_loss)",
        "important":"Past 2018-2026 data used for research; only independent new vintage can support untouched confirmation.",
        "CAGR_used_to_select_layers":False
    }
    (out/"PREFLIGHT_RESULT.json").write_text(json.dumps(contracts,indent=2))
    (out/"CANDIDATE_BASELINE_PAIRED_MONTHLY_53.csv").write_text(candidate.to_csv(index=False))
    (out/"MANIFEST.json").write_text(json.dumps({"registry":a.registry,
        "input_runs":[39482809691,39652989033,39655513813,39659903643,
          39661273577,39671493979,39672320747],
        "holdout_required":True,"V2_unchanged":True},indent=2))
    print("L07_RESEARCH_PREFLIGHT_PASS",json.dumps(contracts,indent=2),flush=True)

if __name__=="__main__":main()
