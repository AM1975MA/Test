#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

KS = (1, 2, 3, 5, 10)
META_FEATURES = [
    "margin12", "margin23", "score_std",
    "base_diff", "tail_diff", "et_diff", "xgb_diff",
    "et_order", "xgb_order", "both_order",
]


def annualize_monthly(rets: pd.Series) -> float:
    x = pd.to_numeric(rets, errors="coerce").dropna().to_numpy(float)
    if not len(x) or np.any(x <= -1.0):
        return float("nan")
    return float(np.prod(1.0 + x) ** (12.0 / len(x)) - 1.0)


def reconstruct(pred_path: Path, panel_path: Path) -> pd.DataFrame:
    pred = pd.read_csv(pred_path, parse_dates=["signal_date"])
    panel = pd.read_pickle(panel_path)
    panel["signal_date"] = pd.to_datetime(panel["signal_date"])
    panel["exit_date_21"] = pd.to_datetime(panel["exit_date_21"])

    pred = pred.sort_values(["ticker", "signal_date"]).copy()
    first = pred.groupby("ticker")["TAIL_HYBRID"].transform("first")
    lag1 = pred.groupby("ticker")["TAIL_HYBRID"].shift(1).fillna(first)
    lag2 = pred.groupby("ticker")["TAIL_HYBRID"].shift(2).fillna(first)
    smooth = 0.40 * pred["TAIL_HYBRID"] + 0.30 * lag1 + 0.30 * lag2
    pred["SCORE"] = 0.475 * pred["BASE"] + 0.525 * np.power(np.clip(smooth, 0.0, 1.0), 1.10)

    keep = [
        "signal_date", "ticker", "fwd_ret_21", "fwd_ret_42", "fwd_ret_63",
        "exit_date_21", "target_rank_21", "target_rank_42", "target_rank_63",
    ]
    out = panel[keep].copy()
    out["CORRECTED_TARGET"] = (
        0.45 * np.power(out["target_rank_21"], 1.5)
        + 0.35 * np.power(out["target_rank_42"], 1.5)
        + 0.20 * np.power(out["target_rank_63"], 1.5)
    )
    return pred.merge(out, on=["signal_date", "ticker"], how="left", validate="one_to_one")


def top_tail_summary(df: pd.DataFrame, label: str, n_candidates: int) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    valid21 = [d for d, g in df.groupby("signal_date") if len(g) == n_candidates and g["fwd_ret_21"].notna().all()]
    validt = [d for d, g in df.groupby("signal_date") if len(g) == n_candidates and g["CORRECTED_TARGET"].notna().all()]

    rows21 = []
    for d, g in df[df.signal_date.isin(valid21)].groupby("signal_date"):
        p = g.sort_values("SCORE", ascending=False).reset_index(drop=True)
        r = g.sort_values("fwd_ret_21", ascending=False).reset_index(drop=True)
        rank21 = g.set_index("ticker")["fwd_ret_21"].rank(ascending=False, method="first")
        predrank = g.set_index("ticker")["SCORE"].rank(ascending=False, method="first")
        row = {
            "signal_date": d,
            "exit_date_21": p.loc[0, "exit_date_21"],
            "top1": p.loc[0, "ticker"], "top2": p.loc[1, "ticker"],
            "r1": float(p.loc[0, "fwd_ret_21"]), "r2": float(p.loc[1, "fwd_ret_21"]),
            "margin12": float(p.loc[0, "SCORE"] - p.loc[1, "SCORE"]),
            "margin23": float(p.loc[1, "SCORE"] - p.loc[2, "SCORE"]),
            "score_std": float(g["SCORE"].std(ddof=0)),
            "base_diff": float(p.loc[0, "BASE"] - p.loc[1, "BASE"]),
            "tail_diff": float(p.loc[0, "TAIL_HYBRID"] - p.loc[1, "TAIL_HYBRID"]),
            "et_diff": float(p.loc[0, "ET_TAIL"] - p.loc[1, "ET_TAIL"]),
            "xgb_diff": float(p.loc[0, "XGB_TAIL"] - p.loc[1, "XGB_TAIL"]),
            "et_order": float(p.loc[0, "ET_TAIL"] > p.loc[1, "ET_TAIL"]),
            "xgb_order": float(p.loc[0, "XGB_TAIL"] > p.loc[1, "XGB_TAIL"]),
            "both_order": float((p.loc[0, "ET_TAIL"] > p.loc[1, "ET_TAIL"]) and (p.loc[0, "XGB_TAIL"] > p.loc[1, "XGB_TAIL"])),
            "top1_real_rank21": float(rank21.loc[p.loc[0, "ticker"]]),
            "actual_best_pred_rank21": float(predrank.loc[r.loc[0, "ticker"]]),
        }
        for k in KS:
            ps = set(p.head(k).ticker)
            rs = set(r.head(k).ticker)
            row[f"precision21_at_{k}"] = len(ps & rs) / k
            row[f"best21_in_pred_{k}"] = float(r.loc[0, "ticker"] in ps)
        rows21.append(row)
    D21 = pd.DataFrame(rows21).sort_values("signal_date").reset_index(drop=True)

    rowst = []
    for d, g in df[df.signal_date.isin(validt)].groupby("signal_date"):
        p = g.sort_values("SCORE", ascending=False).reset_index(drop=True)
        r = g.sort_values("CORRECTED_TARGET", ascending=False).reset_index(drop=True)
        realrank = g.set_index("ticker")["CORRECTED_TARGET"].rank(ascending=False, method="first")
        predrank = g.set_index("ticker")["SCORE"].rank(ascending=False, method="first")
        row = {
            "signal_date": d,
            "top1_real_rank_target": float(realrank.loc[p.loc[0, "ticker"]]),
            "actual_best_pred_rank_target": float(predrank.loc[r.loc[0, "ticker"]]),
        }
        for k in KS:
            ps = set(p.head(k).ticker)
            rs = set(r.head(k).ticker)
            row[f"precision_target_at_{k}"] = len(ps & rs) / k
            row[f"best_target_in_pred_{k}"] = float(r.loc[0, "ticker"] in ps)
        rowst.append(row)
    DT = pd.DataFrame(rowst).sort_values("signal_date").reset_index(drop=True)

    ics21 = []
    icst = []
    for d, g in df.groupby("signal_date"):
        if len(g) == n_candidates and g["fwd_ret_21"].notna().all():
            ics21.append(g["SCORE"].corr(g["fwd_ret_21"], method="spearman"))
        if len(g) == n_candidates and g["CORRECTED_TARGET"].notna().all():
            icst.append(g["SCORE"].corr(g["CORRECTED_TARGET"], method="spearman"))

    q = pd.qcut(D21["margin12"], 5, duplicates="drop")
    mc = []
    for interval, x in D21.groupby(q, observed=True):
        mc.append({
            "margin_bin": str(interval), "n": int(len(x)), "margin_mean": float(x.margin12.mean()),
            "p_top1_beats_top2": float((x.r1 > x.r2).mean()),
            "mean_r1_minus_r2": float((x.r1 - x.r2).mean()),
            "mean_top1_real_rank21": float(x.top1_real_rank21.mean()),
        })
    margin = pd.DataFrame(mc)

    current_w = 0.60 + 0.40 * np.minimum(D21.margin12 / 0.13, 1.0) ** 2
    summary = {
        "label": label,
        "candidate_count": n_candidates,
        "months_21": int(len(D21)),
        "months_corrected_target": int(len(DT)),
        "spearman_ic21_mean": float(np.mean(ics21)),
        "spearman_ic21_median": float(np.median(ics21)),
        "spearman_ic21_positive_fraction": float(np.mean(np.asarray(ics21) > 0)),
        "spearman_ic_target_mean": float(np.mean(icst)),
        "top1_real_rank21_mean": float(D21.top1_real_rank21.mean()),
        "top1_real_rank21_median": float(D21.top1_real_rank21.median()),
        "actual_best_pred_rank21_mean": float(D21.actual_best_pred_rank21.mean()),
        "actual_best_pred_rank21_median": float(D21.actual_best_pred_rank21.median()),
        "p_top1_beats_top2": float((D21.r1 > D21.r2).mean()),
        "margin_vs_r1_minus_r2_spearman": float(D21.margin12.corr(D21.r1 - D21.r2, method="spearman")),
        "top1_monthly_fwd21_cagr_approx": annualize_monthly(D21.r1),
        "top2_monthly_fwd21_cagr_approx": annualize_monthly(D21.r2),
        "equal_top1_top2_cagr_approx": annualize_monthly(0.5 * D21.r1 + 0.5 * D21.r2),
        "current_margin_mix_cagr_approx": annualize_monthly(current_w * D21.r1 + (1.0 - current_w) * D21.r2),
    }
    for k in KS:
        summary[f"precision21_at_{k}"] = float(D21[f"precision21_at_{k}"].mean())
        summary[f"best21_in_pred_{k}"] = float(D21[f"best21_in_pred_{k}"].mean())
        summary[f"random_best_hit_{k}"] = float(k / n_candidates)
        summary[f"precision_target_at_{k}"] = float(DT[f"precision_target_at_{k}"].mean())
        summary[f"best_target_in_pred_{k}"] = float(DT[f"best_target_in_pred_{k}"].mean())
    return summary, D21, margin


def walkforward_meta(train_rows: pd.DataFrame, test_rows: pd.DataFrame, min_train: int = 24) -> tuple[dict, pd.DataFrame]:
    train_rows = train_rows.sort_values("signal_date").copy()
    test_rows = test_rows.sort_values("signal_date").copy()
    out = []
    for _, row in test_rows.iterrows():
        matured = train_rows[train_rows["exit_date_21"] < row.signal_date].copy()
        if len(matured) < min_train or matured.assign(y=(matured.r1 > matured.r2).astype(int)).y.nunique() < 2:
            continue
        X = matured[META_FEATURES].to_numpy(float)
        y = (matured.r1 > matured.r2).astype(int).to_numpy()
        model = make_pipeline(StandardScaler(), LogisticRegression(C=0.3, max_iter=2000, solver="lbfgs"))
        model.fit(X, y)
        p = float(model.predict_proba(row[META_FEATURES].to_numpy(float).reshape(1, -1))[0, 1])
        chosen = float(row.r1 if p >= 0.5 else row.r2)
        soft = float(p * row.r1 + (1.0 - p) * row.r2)
        out.append({"signal_date": row.signal_date, "p_top1": p, "y": int(row.r1 > row.r2), "chosen_ret": chosen, "soft_ret": soft, "r1": row.r1, "r2": row.r2})
    o = pd.DataFrame(out)
    if o.empty:
        return {"n": 0}, o
    return {
        "n": int(len(o)),
        "accuracy": float(((o.p_top1 >= 0.5).astype(int) == o.y).mean()),
        "corr_probability_with_r1_minus_r2": float(o.p_top1.corr(o.r1 - o.r2, method="spearman")),
        "hard_router_cagr_approx": annualize_monthly(o.chosen_ret),
        "soft_probability_mix_cagr_approx": annualize_monthly(o.soft_ret),
        "top1_cagr_same_window": annualize_monthly(o.r1),
        "top2_cagr_same_window": annualize_monthly(o.r2),
        "equal_mix_cagr_same_window": annualize_monthly(0.5 * o.r1 + 0.5 * o.r2),
    }, o


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pred149", type=Path, required=True)
    ap.add_argument("--panel149", type=Path, required=True)
    ap.add_argument("--pred70", type=Path, required=True)
    ap.add_argument("--panel70", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    d149 = reconstruct(args.pred149, args.panel149)
    d70 = reconstruct(args.pred70, args.panel70)
    s149, m149, c149 = top_tail_summary(d149, "original149_fresh", 149)
    s70, m70, c70 = top_tail_summary(d70, "holdout70_fresh", 70)

    own149, own149_rows = walkforward_meta(m149, m149)
    own70, own70_rows = walkforward_meta(m70, m70)
    transfer149to70, transfer_rows = walkforward_meta(m149, m70)

    result = {
        "status": "HYBRID24_TOP_TAIL_DIAGNOSTIC_COMPLETE",
        "producer": "canonical Hybrid24, unchanged",
        "original149": s149,
        "holdout70": s70,
        "walkforward_meta_top1_vs_top2": {
            "original149_self_walkforward": own149,
            "holdout70_self_walkforward_diagnostic_burned": own70,
            "train_original149_apply_holdout70": transfer149to70,
            "note": "Meta models are diagnostics only. Each prediction uses only labels whose 21d exit date is before the current signal date. The 149->70 lane never trains on Holdout70 outcomes.",
        },
    }
    (args.out / "SUMMARY.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    m149.to_csv(args.out / "MONTHLY_149.csv", index=False)
    m70.to_csv(args.out / "MONTHLY_70.csv", index=False)
    c149.to_csv(args.out / "MARGIN_CALIBRATION_149.csv", index=False)
    c70.to_csv(args.out / "MARGIN_CALIBRATION_70.csv", index=False)
    own149_rows.to_csv(args.out / "META_149_SELF.csv", index=False)
    own70_rows.to_csv(args.out / "META_70_SELF.csv", index=False)
    transfer_rows.to_csv(args.out / "META_149_TO_70.csv", index=False)
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
