#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

EXPECTED_N_PERIODS = 114
EXPECTED_CANDIDATES = 72


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_spearman(x: pd.Series, y: pd.Series) -> float:
    r = spearmanr(x, y, nan_policy="omit").statistic
    return float(r) if np.isfinite(r) else float("nan")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    p = pd.read_csv(args.predictions, parse_dates=["signal_date"])
    req = {"signal_date", "ticker", "LTR_SCORE", "fwd_ret_21"}
    if not req.issubset(p.columns):
        raise RuntimeError(f"missing columns: {sorted(req-set(p.columns))}")
    if p.duplicated(["signal_date", "ticker"]).any():
        raise RuntimeError("duplicate signal_date/ticker keys")

    monthly = []
    bucket_rows = []
    for dt, g0 in p.groupby("signal_date", sort=True):
        g = g0.dropna(subset=["LTR_SCORE", "fwd_ret_21"]).copy()
        if len(g) != EXPECTED_CANDIDATES:
            continue
        gs = g.sort_values(["LTR_SCORE", "ticker"], ascending=[False, True]).reset_index(drop=True)
        gr = g.sort_values(["fwd_ret_21", "ticker"], ascending=[False, True]).reset_index(drop=True)
        gs["score_rank"] = np.arange(1, len(gs)+1)
        winner = str(gr.iloc[0].ticker)
        loser = str(gr.iloc[-1].ticker)
        score_names = gs.ticker.astype(str).tolist()
        wrank = score_names.index(winner) + 1
        lrank = score_names.index(loser) + 1
        realized_top10 = set(gr.head(10).ticker.astype(str))
        realized_bottom10 = set(gr.tail(10).ticker.astype(str))
        score_top10 = set(gs.head(10).ticker.astype(str))

        monthly.append({
            "signal_date": dt,
            "winner": winner,
            "loser": loser,
            "winner_score_rank": wrank,
            "loser_score_rank": lrank,
            "winner_hit1": wrank <= 1,
            "winner_hit5": wrank <= 5,
            "winner_hit10": wrank <= 10,
            "loser_hit1": lrank <= 1,
            "loser_hit5": lrank <= 5,
            "loser_hit10": lrank <= 10,
            "both_extremes_in_top5": wrank <= 5 and lrank <= 5,
            "both_extremes_in_top10": wrank <= 10 and lrank <= 10,
            "score_ret_spearman": safe_spearman(g.LTR_SCORE, g.fwd_ret_21),
            "score_absret_spearman": safe_spearman(g.LTR_SCORE, g.fwd_ret_21.abs()),
            "universe_absret_mean": float(g.fwd_ret_21.abs().mean()),
            "top1_absret_mean": float(gs.head(1).fwd_ret_21.abs().mean()),
            "top5_absret_mean": float(gs.head(5).fwd_ret_21.abs().mean()),
            "top10_absret_mean": float(gs.head(10).fwd_ret_21.abs().mean()),
            "score_top10_realized_top10_overlap": int(len(score_top10 & realized_top10)),
            "score_top10_realized_bottom10_overlap": int(len(score_top10 & realized_bottom10)),
        })

        for b in range(12):
            lo = b * 6 + 1
            hi = lo + 5
            z = gs.iloc[b*6:(b+1)*6]
            bucket_rows.append({
                "signal_date": dt,
                "bucket": b + 1,
                "score_rank_lo": lo,
                "score_rank_hi": hi,
                "mean_ret21": float(z.fwd_ret_21.mean()),
                "median_ret21": float(z.fwd_ret_21.median()),
                "mean_abs_ret21": float(z.fwd_ret_21.abs().mean()),
                "positive_rate": float((z.fwd_ret_21 > 0).mean()),
                "extreme_loss_rate_le_minus10pct": float((z.fwd_ret_21 <= -0.10).mean()),
                "extreme_gain_rate_ge_plus10pct": float((z.fwd_ret_21 >= 0.10).mean()),
            })

    m = pd.DataFrame(monthly)
    b = pd.DataFrame(bucket_rows)
    if len(m) != EXPECTED_N_PERIODS:
        raise RuntimeError(f"expected {EXPECTED_N_PERIODS} periods, got {len(m)}")
    if len(b) != EXPECTED_N_PERIODS * 12:
        raise RuntimeError("bucket row count mismatch")

    random = {
        "top1": EXPECTED_N_PERIODS * (1 / EXPECTED_CANDIDATES),
        "top5": EXPECTED_N_PERIODS * (5 / EXPECTED_CANDIDATES),
        "top10": EXPECTED_N_PERIODS * (10 / EXPECTED_CANDIDATES),
    }

    def capture(prefix: str) -> dict:
        out = {}
        for k in (1, 5, 10):
            obs = int(m[f"{prefix}_hit{k}"].sum())
            exp = random[f"top{k}"]
            out[f"top{k}_hits"] = obs
            out[f"top{k}_random_expected"] = exp
            out[f"top{k}_enrichment"] = float(obs / exp)
        return out

    bucket_summary = (
        b.groupby(["bucket", "score_rank_lo", "score_rank_hi"], as_index=False)
         .agg(
             mean_ret21=("mean_ret21", "mean"),
             median_of_monthly_median_ret21=("median_ret21", "median"),
             mean_abs_ret21=("mean_abs_ret21", "mean"),
             positive_rate=("positive_rate", "mean"),
             extreme_loss_rate_le_minus10pct=("extreme_loss_rate_le_minus10pct", "mean"),
             extreme_gain_rate_ge_plus10pct=("extreme_gain_rate_ge_plus10pct", "mean"),
         )
    )

    summary = {
        "line": "Evidence V3",
        "diagnostic": "ltr_tail_symmetry",
        "status": "DIAGNOSTIC_ONLY_NO_ADVANCEMENT_GATE",
        "n_periods": int(len(m)),
        "candidates_per_period": EXPECTED_CANDIDATES,
        "winner_capture": capture("winner"),
        "loser_capture": capture("loser"),
        "both_extremes": {
            "top5_months": int(m.both_extremes_in_top5.sum()),
            "top10_months": int(m.both_extremes_in_top10.sum()),
        },
        "score_relationships": {
            "mean_spearman_score_vs_return": float(m.score_ret_spearman.mean()),
            "median_spearman_score_vs_return": float(m.score_ret_spearman.median()),
            "positive_month_rate_score_vs_return": float((m.score_ret_spearman > 0).mean()),
            "mean_spearman_score_vs_abs_return": float(m.score_absret_spearman.mean()),
            "median_spearman_score_vs_abs_return": float(m.score_absret_spearman.median()),
            "positive_month_rate_score_vs_abs_return": float((m.score_absret_spearman > 0).mean()),
        },
        "absolute_return_concentration": {
            "universe_mean_abs_ret21": float(m.universe_absret_mean.mean()),
            "top1_mean_abs_ret21": float(m.top1_absret_mean.mean()),
            "top5_mean_abs_ret21": float(m.top5_absret_mean.mean()),
            "top10_mean_abs_ret21": float(m.top10_absret_mean.mean()),
            "top1_vs_universe_ratio": float(m.top1_absret_mean.mean() / m.universe_absret_mean.mean()),
            "top5_vs_universe_ratio": float(m.top5_absret_mean.mean() / m.universe_absret_mean.mean()),
            "top10_vs_universe_ratio": float(m.top10_absret_mean.mean() / m.universe_absret_mean.mean()),
        },
        "top10_tail_overlap": {
            "mean_realized_top10_names": float(m.score_top10_realized_top10_overlap.mean()),
            "mean_realized_bottom10_names": float(m.score_top10_realized_bottom10_overlap.mean()),
            "months_more_positive_than_negative_tail_names": int((m.score_top10_realized_top10_overlap > m.score_top10_realized_bottom10_overlap).sum()),
            "months_more_negative_than_positive_tail_names": int((m.score_top10_realized_bottom10_overlap > m.score_top10_realized_top10_overlap).sum()),
            "months_equal_tail_counts": int((m.score_top10_realized_bottom10_overlap == m.score_top10_realized_top10_overlap).sum()),
        },
        "interpretation_rule": "Descriptive only. Do not select K, thresholds, buckets, directions or trading rules on Dev72 from this diagnostic.",
    }

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    m.to_csv(out / "MONTHLY.csv", index=False)
    b.to_csv(out / "BUCKET_MONTHLY.csv", index=False)
    bucket_summary.to_csv(out / "BUCKET_SUMMARY.csv", index=False)
    (out / "SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n")
    files = ["MONTHLY.csv", "BUCKET_MONTHLY.csv", "BUCKET_SUMMARY.csv", "SUMMARY.json"]
    (out / "RESULT_MANIFEST.json").write_text(json.dumps({
        "diagnostic": "ltr_tail_symmetry",
        "files_sha256": {name: sha256_file(out / name) for name in files},
    }, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    print(bucket_summary.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
