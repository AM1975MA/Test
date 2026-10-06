#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from xgboost import XGBRanker


LTR_CFG = {
    "objective": "rank:ndcg",
    "n_estimators": 400,
    "max_depth": 2,
    "learning_rate": 0.02,
    "subsample": 0.90,
    "colsample_bytree": 0.90,
    "min_child_weight": 12,
    "reg_lambda": 12.0,
    "reg_alpha": 0.2,
    "tree_method": "hist",
    "random_state": 101,
    "n_jobs": 2,
    "lambdarank_pair_method": "topk",
    "lambdarank_num_pair_per_sample": 10,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def monthly_cagr_proxy(x: pd.Series) -> float:
    r = pd.to_numeric(x, errors="coerce").dropna().to_numpy(float)
    if len(r) == 0 or np.any(r <= -1):
        return float("nan")
    return float(np.prod(1.0 + r) ** (12.0 / len(r)) - 1.0)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--frozen-source", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    frozen_source = Path(args.frozen_source).resolve()
    sys.path.insert(0, str(frozen_source / "src"))
    from etf_trader.ma3.producer import FEATURES_42

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    panel["exit_date_63"] = pd.to_datetime(panel.exit_date_63)

    required = list(FEATURES_42) + [
        "ticker", "signal_date", "exit_date_63",
        "target_relevance", "target_multi_rank", "fwd_ret_21",
    ]
    missing = [c for c in required if c not in panel.columns]
    if missing:
        raise RuntimeError(f"missing required panel columns: {missing}")

    pred_parts = []
    fit_audit = []
    for year in range(2011, 2027):
        cutoff = pd.Timestamp(f"{year}-01-01")
        next_cutoff = pd.Timestamp(f"{year + 1}-01-01")
        tr = panel[
            (panel.signal_date < cutoff)
            & (panel.exit_date_63 < cutoff)
            & panel.target_relevance.notna()
        ].copy()
        pr = panel[
            (panel.signal_date >= cutoff)
            & (panel.signal_date < next_cutoff)
        ].copy()
        if tr.empty or pr.empty:
            continue

        tr = tr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)
        pr = pr.sort_values(["signal_date", "ticker"]).reset_index(drop=True)

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[list(FEATURES_42)])
        xp = imp.transform(pr[list(FEATURES_42)])
        qid = pd.factorize(tr.signal_date, sort=True)[0]

        model = XGBRanker(**LTR_CFG)
        model.fit(
            xtr,
            tr.target_relevance.astype(int).to_numpy(),
            qid=qid,
            verbose=False,
        )
        pr["LTR_SCORE"] = model.predict(xp)
        pr = pr.sort_values(
            ["signal_date", "LTR_SCORE", "ticker"],
            ascending=[True, False, True],
        ).reset_index(drop=True)
        pr["LTR_RANK"] = pr.groupby("signal_date").cumcount() + 1
        n = pr.groupby("signal_date").ticker.transform("count").astype(float)
        pr["LTR_POSITION"] = np.where(
            n > 1, 1.0 - (pr["LTR_RANK"].astype(float) - 1.0) / (n - 1.0), 1.0
        )
        pred_parts.append(pr)

        maturity_ok = bool(
            (tr.signal_date < cutoff).all()
            and (tr.exit_date_63 < cutoff).all()
        )
        fit_audit.append({
            "year": year,
            "cutoff": str(cutoff.date()),
            "n_train": int(len(tr)),
            "n_predict": int(len(pr)),
            "max_train_exit63": str(tr.exit_date_63.max().date()),
            "maturity_ok": maturity_ok,
        })
        if not maturity_ok:
            raise RuntimeError(f"maturity gate failed for {year}")

    if not pred_parts:
        raise RuntimeError("no OOS retriever predictions generated")
    oos = pd.concat(pred_parts, ignore_index=True)
    fit_audit_df = pd.DataFrame(fit_audit)
    if not bool(fit_audit_df.maturity_ok.all()):
        raise RuntimeError("fit audit failed")

    pred = oos[
        ["signal_date", "ticker", "LTR_SCORE", "LTR_RANK", "LTR_POSITION"]
    ].copy()
    top5 = pred[pred.LTR_RANK <= 5].copy()
    top10 = pred[pred.LTR_RANK <= 10].copy()

    eval_rows = []
    for dt, g in oos[oos.signal_date >= pd.Timestamp("2017-01-01")].groupby(
        "signal_date", sort=True
    ):
        actual = g.dropna(subset=["fwd_ret_21"]).sort_values(
            "fwd_ret_21", ascending=False
        ).reset_index(drop=True)
        ranked = g.sort_values(
            ["LTR_SCORE", "ticker"], ascending=[False, True]
        ).reset_index(drop=True)
        if actual.empty or len(ranked) < 10:
            continue
        winner = str(actual.iloc[0].ticker)
        eval_rows.append({
            "signal_date": str(pd.Timestamp(dt).date()),
            "winner": winner,
            "top1": str(ranked.iloc[0].ticker),
            "top1_ret21": float(ranked.iloc[0].fwd_ret_21),
            "top1_is_winner": bool(str(ranked.iloc[0].ticker) == winner),
            "top5_contains_winner": bool(winner in set(ranked.head(5).ticker.astype(str))),
            "top10_contains_winner": bool(winner in set(ranked.head(10).ticker.astype(str))),
        })
    ev = pd.DataFrame(eval_rows)
    validation = {
        "n_periods": int(len(ev)),
        "top1_exact_winner_count": int(ev.top1_is_winner.sum()),
        "top5_winner_count": int(ev.top5_contains_winner.sum()),
        "top10_winner_count": int(ev.top10_contains_winner.sum()),
        "top1_exact_winner_rate": float(ev.top1_is_winner.mean()),
        "top5_winner_rate": float(ev.top5_contains_winner.mean()),
        "top10_winner_rate": float(ev.top10_contains_winner.mean()),
        "top1_21d_cagr_proxy": monthly_cagr_proxy(ev.top1_ret21),
    }

    expected = {
        "n_periods": 114,
        "top1_exact_winner_count": 10,
        "top5_winner_count": 32,
        "top10_winner_count": 47,
    }
    for key, value in expected.items():
        if validation[key] != value:
            raise RuntimeError(
                f"checkpoint validation mismatch for {key}: "
                f"{validation[key]} != {value}"
            )

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    pred.to_csv(out / "OOS_PREDICTIONS.csv", index=False)
    top5.to_csv(out / "TOP5.csv", index=False)
    top10.to_csv(out / "TOP10.csv", index=False)
    fit_audit_df.to_csv(out / "FIT_AUDIT.csv", index=False)
    (out / "CONFIG.json").write_text(json.dumps(LTR_CFG, indent=2) + "\n")
    (out / "VALIDATION.json").write_text(json.dumps(validation, indent=2) + "\n")

    files = [
        "OOS_PREDICTIONS.csv", "TOP5.csv", "TOP10.csv",
        "FIT_AUDIT.csv", "CONFIG.json", "VALIDATION.json",
    ]
    manifest = {
        "checkpoint": "retriever_ltr_v1_oos",
        "universe": "Original149 frozen",
        "prediction_start": str(pred.signal_date.min().date()),
        "prediction_end": str(pred.signal_date.max().date()),
        "rows": int(len(pred)),
        "signal_dates": int(pred.signal_date.nunique()),
        "top5_rows": int(len(top5)),
        "top10_rows": int(len(top10)),
        "join_key_for_downstream": ["signal_date", "ticker"],
        "downstream_rule": (
            "Join to frozen panel for features/labels and enforce label maturity "
            "before every downstream fit."
        ),
        "validation": validation,
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }
    (out / "CHECKPOINT_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n"
    )
    print(json.dumps(manifest, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
