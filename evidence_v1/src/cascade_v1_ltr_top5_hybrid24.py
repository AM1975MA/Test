#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

EVAL_START = pd.Timestamp("2017-01-01")
EVAL_END = pd.Timestamp("2026-07-01")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stats(r: pd.Series) -> dict:
    x = pd.to_numeric(r, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0 or np.any(x <= -1):
        return {"n": int(len(x))}
    equity = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(equity)
    dd = equity / peak - 1.0
    cagr = float(equity[-1] ** (12.0 / len(x)) - 1.0)
    vol = float(np.std(x, ddof=1) * np.sqrt(12.0)) if len(x) > 1 else float("nan")
    sharpe = (
        float(np.mean(x) / np.std(x, ddof=1) * np.sqrt(12.0))
        if len(x) > 1 and np.std(x, ddof=1) > 0
        else float("nan")
    )
    mdd = float(np.min(dd))
    calmar = float(cagr / abs(mdd)) if mdd < 0 else float("inf")
    return {
        "n": int(len(x)),
        "cagr": cagr,
        "annualized_vol": vol,
        "sharpe_rf0": sharpe,
        "max_drawdown": mdd,
        "calmar": calmar,
        "positive_period_rate": float(np.mean(x > 0)),
        "worst_period": float(np.min(x)),
        "best_period": float(np.max(x)),
        "mean_period_return": float(np.mean(x)),
    }


def summarize(monthly: pd.DataFrame) -> dict:
    n = len(monthly)
    retrievable = monthly[monthly.top5_contains_global_winner]
    return {
        "n": int(n),
        "ltr_top1": stats(monthly.ltr_top1_ret21),
        "hybrid24_only": stats(monthly.hybrid24_only_ret21),
        "cascade": stats(monthly.cascade_ret21),
        "ltr_top1_exact_winner_count": int(monthly.ltr_top1_is_global_winner.sum()),
        "ltr_top1_exact_winner_rate": float(monthly.ltr_top1_is_global_winner.mean()),
        "hybrid24_only_exact_winner_count": int(monthly.hybrid24_only_is_global_winner.sum()),
        "hybrid24_only_exact_winner_rate": float(monthly.hybrid24_only_is_global_winner.mean()),
        "cascade_exact_winner_count": int(monthly.cascade_is_global_winner.sum()),
        "cascade_exact_winner_rate": float(monthly.cascade_is_global_winner.mean()),
        "top5_contains_global_winner_count": int(monthly.top5_contains_global_winner.sum()),
        "top5_contains_global_winner_rate": float(monthly.top5_contains_global_winner.mean()),
        "cascade_conditional_hit_count_when_retrievable": int(retrievable.cascade_is_global_winner.sum()),
        "cascade_conditional_hit_rate_when_retrievable": (
            float(retrievable.cascade_is_global_winner.mean()) if len(retrievable) else float("nan")
        ),
        "cascade_equals_ltr_top1_rate": float((monthly.cascade_ticker == monthly.ltr_top1_ticker).mean()),
        "cascade_equals_hybrid24_only_rate": float((monthly.cascade_ticker == monthly.hybrid24_only_ticker).mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", required=True)
    ap.add_argument("--ltr-checkpoint", required=True)
    ap.add_argument("--hybrid24-checkpoint", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    panel = pd.read_pickle(args.panel).copy()
    panel["signal_date"] = pd.to_datetime(panel.signal_date)
    if "fwd_ret_21" not in panel.columns:
        raise RuntimeError("panel missing fwd_ret_21")
    ret = panel[["signal_date", "ticker", "fwd_ret_21"]].copy()
    ret["ticker"] = ret.ticker.astype(str)

    ltr_cp = Path(args.ltr_checkpoint)
    top5 = pd.read_csv(ltr_cp / "TOP5.csv")
    full = pd.read_csv(ltr_cp / "OOS_PREDICTIONS.csv")
    for df in (top5, full):
        df["signal_date"] = pd.to_datetime(df.signal_date)
        df["ticker"] = df.ticker.astype(str)

    if len(top5) != 930 or top5.signal_date.nunique() != 186:
        raise RuntimeError(f"frozen LTR Top5 mismatch rows={len(top5)} dates={top5.signal_date.nunique()}")
    sizes = top5.groupby("signal_date").size()
    if sizes.nunique() != 1 or int(sizes.iloc[0]) != 5:
        raise RuntimeError("frozen LTR checkpoint is not exactly Top5 per date")

    hcp = Path(args.hybrid24_checkpoint)
    hyb = pd.read_csv(hcp / "OOS_SCORES.csv")
    hyb["signal_date"] = pd.to_datetime(hyb.signal_date)
    hyb["ticker"] = hyb.ticker.astype(str)
    req_h = {"signal_date", "ticker", "HYBRID24_SCORE"}
    if not req_h.issubset(hyb.columns):
        raise RuntimeError(f"Hybrid24 checkpoint missing {sorted(req_h-set(hyb.columns))}")
    if hyb.signal_date.nunique() != 114:
        raise RuntimeError(f"Hybrid24 checkpoint expected 114 dates, got {hyb.signal_date.nunique()}")
    if hyb.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError("Hybrid24 checkpoint has duplicate keys")
    if not np.isfinite(pd.to_numeric(hyb.HYBRID24_SCORE, errors="coerce")).all():
        raise RuntimeError("Hybrid24 checkpoint contains non-finite score")

    top5j = top5.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    fullj = full.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    hybj = hyb.merge(ret, on=["signal_date", "ticker"], how="left", validate="one_to_one")

    hscore = hyb[["signal_date", "ticker", "HYBRID24_SCORE"]]
    top5j = top5j.merge(hscore, on=["signal_date", "ticker"], how="left", validate="one_to_one")
    if top5j.loc[(top5j.signal_date >= EVAL_START) & (top5j.signal_date < EVAL_END), "HYBRID24_SCORE"].isna().any():
        raise RuntimeError("one or more frozen LTR Top5 names lack Hybrid24 OOS score")

    full_by_date = {dt: g.copy() for dt, g in fullj.groupby("signal_date", sort=True)}
    hyb_by_date = {dt: g.copy() for dt, g in hybj.groupby("signal_date", sort=True)}

    rows = []
    for dt, g in top5j.groupby("signal_date", sort=True):
        if dt < EVAL_START or dt >= EVAL_END:
            continue
        g = g.dropna(subset=["fwd_ret_21", "HYBRID24_SCORE"]).copy()
        if len(g) != 5:
            raise RuntimeError(f"{dt}: incomplete mature Top5 join")

        ltr_ranked = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        cascade_ranked = g.sort_values(["HYBRID24_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)

        fg = full_by_date.get(dt)
        hg = hyb_by_date.get(dt)
        if fg is None or hg is None:
            raise RuntimeError(f"{dt}: missing comparator universe")
        fg = fg.dropna(subset=["fwd_ret_21"]).copy()
        hg = hg.dropna(subset=["fwd_ret_21", "HYBRID24_SCORE"]).copy()
        if fg.empty or hg.empty:
            raise RuntimeError(f"{dt}: empty comparator universe")
        if set(fg.ticker) != set(hg.ticker):
            raise RuntimeError(f"{dt}: LTR and Hybrid24 candidate universes differ")

        actual = fg.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        h24_ranked = hg.sort_values(["HYBRID24_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)

        global_winner = str(actual.iloc[0].ticker)
        ltr_t = str(ltr_ranked.iloc[0].ticker)
        cas_t = str(cascade_ranked.iloc[0].ticker)
        h24_t = str(h24_ranked.iloc[0].ticker)
        names = set(g.ticker.astype(str))

        rows.append({
            "signal_date": dt,
            "global_winner": global_winner,
            "ltr_top1_ticker": ltr_t,
            "ltr_top1_ret21": float(ltr_ranked.iloc[0].fwd_ret_21),
            "hybrid24_only_ticker": h24_t,
            "hybrid24_only_ret21": float(h24_ranked.iloc[0].fwd_ret_21),
            "cascade_ticker": cas_t,
            "cascade_ret21": float(cascade_ranked.iloc[0].fwd_ret_21),
            "cascade_hybrid24_score": float(cascade_ranked.iloc[0].HYBRID24_SCORE),
            "ltr_top1_is_global_winner": bool(ltr_t == global_winner),
            "hybrid24_only_is_global_winner": bool(h24_t == global_winner),
            "cascade_is_global_winner": bool(cas_t == global_winner),
            "top5_contains_global_winner": bool(global_winner in names),
            "top5_names_ltr_order": "|".join(ltr_ranked.ticker.astype(str).tolist()),
            "top5_names_hybrid24_order": "|".join(cascade_ranked.ticker.astype(str).tolist()),
        })

    monthly = pd.DataFrame(rows).sort_values("signal_date").reset_index(drop=True)
    if len(monthly) != 114 or monthly.signal_date.nunique() != 114:
        raise RuntimeError(f"expected 114 evaluation dates, got {len(monthly)}")

    full_summary = summarize(monthly)
    pre_summary = summarize(monthly[monthly.signal_date < pd.Timestamp("2023-01-01")])
    post_summary = summarize(monthly[monthly.signal_date >= pd.Timestamp("2023-01-01")])

    # Fail closed against already-certified frozen Retriever LTR v1 evidence.
    expected_ltr_cagr = 0.220630708412056
    expected_ltr_hits = 10
    expected_top5_hits = 32
    if not np.isclose(full_summary["ltr_top1"]["cagr"], expected_ltr_cagr, rtol=0, atol=1e-12):
        raise RuntimeError(f"LTR Top1 CAGR mismatch {full_summary['ltr_top1']['cagr']} != {expected_ltr_cagr}")
    if full_summary["ltr_top1_exact_winner_count"] != expected_ltr_hits:
        raise RuntimeError("LTR Top1 exact-winner checkpoint mismatch")
    if full_summary["top5_contains_global_winner_count"] != expected_top5_hits:
        raise RuntimeError("LTR Top5 containment checkpoint mismatch")

    cas = full_summary["cascade"]
    ltr = full_summary["ltr_top1"]
    h24 = full_summary["hybrid24_only"]
    advance = bool(
        cas["cagr"] > ltr["cagr"]
        and cas["cagr"] > h24["cagr"]
        and full_summary["cascade_exact_winner_count"] > full_summary["ltr_top1_exact_winner_count"]
        and full_summary["cascade_exact_winner_count"] >= full_summary["hybrid24_only_exact_winner_count"]
    )

    result = {
        "line": "Evidence V1",
        "test": "cascade_v1_ltr_top5_hybrid24",
        "status": "DEVELOPMENT_EVIDENCE_ADVANCE" if advance else "DEVELOPMENT_EVIDENCE_REJECTED",
        "universe": "Original149 frozen; burned development set only",
        "architecture": "frozen Retriever LTR v1 Top5 -> highest canonical frozen Hybrid24 OOS score inside Top5",
        "training": "none; both checkpoints are frozen and no model is refit",
        "evaluation": "114 monthly 21d open-to-open forward-return periods, 2017-01-31 through 2026-06-30",
        "comparators": "frozen LTR Top1 and Hybrid24-only Top1 selector on identical dates/candidate universe/returns",
        "primary_advancement_rule": (
            "Cascade full-window CAGR must strictly exceed both frozen LTR Top1 and Hybrid24-only selector CAGR; "
            "cascade exact-global-winner count must strictly exceed LTR Top1 and must be no lower than Hybrid24-only. "
            "Subperiods and other risk metrics are diagnostic only."
        ),
        "full": full_summary,
        "2017_2022": pre_summary,
        "2023_2026": post_summary,
        "decision": (
            "ADVANCE architecture to a newly frozen disjoint Holdout-B before any promotion claim"
            if advance else
            "REJECT cascade on burned Original149; close Evidence V1 architecture search without Top10/layer/blend variants"
        ),
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    monthly.to_csv(out / "MONTHLY.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(result, indent=2) + "\n")
    manifest = {
        "test": "cascade_v1_ltr_top5_hybrid24",
        "files_sha256": {name: sha256_file(out / name) for name in ["MONTHLY.csv", "SUMMARY.json"]},
    }
    (out / "RESULT_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
