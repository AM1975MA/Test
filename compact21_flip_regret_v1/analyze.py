"""Read-only score-margin / forward-return choice-difference diagnostic for Original149."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "vendor/etf_trader_v2/src")]

from compact21_semidev_v1.run import FROZEN_TI
from compact21_semidev_v1.view import sha

KEYS = ["signal_date", "ticker"]
VARIANTS = ("BASE_NATIVE", "OWN_X_R2_Y", "R2_X_OWN_Y")
PAIRS = ((1, 2), (1, 3), (2, 3))
EVAL_END = pd.Timestamp("2026-06-30")
OUTCOME_END = pd.Timestamp("2026-07-01")
N_DATES = 114
N_ROWS_PER_VINTAGE = 16986


def top_choice(group):
    """Return Top1 with deterministic score-desc, ticker-asc ties, IQR normalized margin."""
    g = group.sort_values(["pred", "ticker"], ascending=[False, True], kind="mergesort")
    if len(g) < 2 or not np.isfinite(g.pred.to_numpy(dtype=float)).all():
        raise ValueError("Need at least two finite scores")
    first, second = g.iloc[0], g.iloc[1]
    q75, q25 = np.quantile(g.pred.to_numpy(float), [.75, .25])
    iqr = float(q75 - q25)
    raw = float(first.pred - second.pred)
    if raw < 0:
        raise ValueError("Invalid sorted score margin")
    return {"ticker": str(first.ticker), "raw_margin": raw,
            "norm_margin": raw / iqr if iqr > 0 else None,
            "score_iqr": iqr}


def pair_record(choice1, choice2, outcomes):
    """Read original same-vintage future outcomes ONLY after maturity gate."""
    flip = choice1["ticker"] != choice2["ticker"]
    margins = [choice1["norm_margin"], choice2["norm_margin"]]
    margin = None if any(x is None for x in margins) else min(margins)
    result = {"flip": bool(flip), "min_norm_margin": margin,
              "weak_margin_0p10": None if margin is None else margin <= 0.1,
              "strong_margin_0p10": None if margin is None else margin > 0.1,
              "weak_margin_0p05": None if margin is None else margin <= 0.05,
              "weak_margin_0p20": None if margin is None else margin <= 0.2,
              "both_future_returns_mature": False,
              "abs_forward_return_difference_pp": None,
              "signed_forward_return_difference_pp": None}
    if not flip:
        return result
    a = outcomes.loc[choice1["ticker"]]
    b = outcomes.loc[choice2["ticker"]]
    if (pd.notna(a.exit_date_21) and pd.notna(b.exit_date_21)
            and a.exit_date_21 > a.signal_date and b.exit_date_21 > b.signal_date
            and a.exit_date_21 <= OUTCOME_END and b.exit_date_21 <= OUTCOME_END
            and pd.notna(a.fwd_ret_21) and pd.notna(b.fwd_ret_21)
            and np.isfinite(float(a.fwd_ret_21)) and np.isfinite(float(b.fwd_ret_21))):
        delta = 100.0 * (float(a.fwd_ret_21) - float(b.fwd_ret_21))
        result.update(both_future_returns_mature=True,
                      abs_forward_return_difference_pp=abs(delta),
                      signed_forward_return_difference_pp=delta)
    return result


def original_year_vectors(annual_root):
    pieces = []
    hashes = {}
    for year in range(2017, 2027):
        root = annual_root / f"attribution-{year}"
        rp, pp = root / "RESULT.json", root / "PREDICTIONS.parquet"
        record = json.loads(rp.read_text())
        if (record.get("status") != "COMPACT21_TRAINING_SOURCE_ATTRIBUTION_V1_COMPLETE"
                or record.get("year") != year or record.get("production_adoption") is not False
                or record.get("prediction_file_sha256") != sha(pp)):
            raise ValueError(f"Unverified original training attribution evidence: {year}")
        hashes[str(year)] = {"result_sha256": sha(rp), "predictions_sha256": sha(pp),
                             "source_files_sha256": record["source_files_sha256"]}
        frame = pd.read_parquet(pp)
        if frame.duplicated(KEYS + ["variant", "vintage"]).any():
            raise ValueError("Duplicate annual prediction key")
        if not pd.to_datetime(frame.signal_date).dt.year.eq(year).all():
            raise ValueError("Incorrect prediction year")
        pieces.append(frame)
    all_vectors = pd.concat(pieces, ignore_index=True)
    all_vectors.signal_date = pd.to_datetime(all_vectors.signal_date)
    if all_vectors.signal_date.max() > EVAL_END or all_vectors.signal_date.nunique() != N_DATES:
        raise ValueError("Original monthly inference cutoff/coverage differs")
    for variant in VARIANTS:
        m = all_vectors.variant.eq(variant)
        for vintage in (1, 2, 3):
            s = all_vectors.loc[m & all_vectors.vintage.eq(vintage)]
            if len(s) != N_ROWS_PER_VINTAGE or s[KEYS].isna().any().any() or not np.isfinite(s.pred.to_numpy()).all():
                raise ValueError("Wrong original inference coverage/score")
    return all_vectors, hashes


def reconstruct(vectors, panel, reference):
    if sha(panel / "TI_COMPACT.parquet") != FROZEN_TI["2"]:
        raise ValueError("Not the frozen Repeat2 source")
    original = pd.read_parquet(panel / "TI_COMPACT.parquet")
    original.signal_date = pd.to_datetime(original.signal_date)
    original.exit_date_21 = pd.to_datetime(original.exit_date_21)
    need = KEYS + ["fwd_ret_21", "target_rank_21", "exit_date_21"]
    if any(x not in original.columns for x in need):
        raise ValueError("Original source lacks matured forward-open return evidence")
    outcomes = original.loc[original.signal_date.isin(vectors.signal_date.unique()), need].copy()
    if outcomes.duplicated(KEYS).any():
        raise ValueError("Original source has duplicate outcome keys")
    common = vectors.loc[vectors.variant.eq(VARIANTS[0]) & vectors.vintage.eq(2), KEYS]
    if len(outcomes.merge(common, on=KEYS, how="right", indicator=True).query("_merge != 'both'")):
        raise ValueError("Common score keys absent from original outcomes")
    z = vectors.merge(outcomes, on=KEYS, how="left", validate="many_to_one", indicator=True)
    if not z["_merge"].eq("both").all():
        raise ValueError("Not all score rows joined Repeat2 outcomes")
    z = z.drop(columns="_merge")
    ref = json.loads((reference / "SUMMARY.json").read_text())
    if ref["status"] != "ATTRIBUTION_DIAGNOSTIC_COMPLETE" or ref["total_months"] != N_DATES:
        raise ValueError("Wrong independently recovered original report")
    choices = []
    pair_records = []
    for (variant, date), d in z.groupby(["variant", "signal_date"], sort=True):
        if variant not in VARIANTS:
            continue
        panels = {}
        base = d.loc[d.vintage.eq(2)].set_index("ticker")
        if len(base) < 2:
            raise ValueError("Empty original fixed Repeat2 outcome panel")
        for vintage in (1, 2, 3):
            g = d.loc[d.vintage.eq(vintage)]
            if len(g) != len(base) or set(g.ticker) != set(base.index):
                raise ValueError("Vintage inference keys differ")
            c = top_choice(g)
            o = base.loc[c["ticker"]]
            mature = (pd.notna(o.exit_date_21) and o.exit_date_21 > date
                      and o.exit_date_21 <= OUTCOME_END
                      and pd.notna(o.fwd_ret_21) and np.isfinite(float(o.fwd_ret_21))
                      and pd.notna(o.target_rank_21))
            c.update({"variant": variant, "signal_date": date, "vintage": vintage,
                      "mature": bool(mature),
                      "observed_forward_return_pct": 100.0 * float(o.fwd_ret_21) if mature else None,
                      "observed_target_percentile": float(o.target_rank_21) if mature else None})
            panels[vintage] = c
            choices.append(c)
        for v, w in PAIRS:
            stat = pair_record(panels[v], panels[w], base)
            stat.update(variant=variant, signal_date=date, pair=f"{v}-{w}",
                        first_ticker=panels[v]["ticker"], second_ticker=panels[w]["ticker"])
            pair_records.append(stat)
    c, p = pd.DataFrame(choices), pd.DataFrame(pair_records)
    summary = {"status": "FLIP_REGRET_DESCRIPTIVE_COMPLETE", "dates": N_DATES,
               "original_source_run": 37150436612,
               "attribution_run": 37916159772,
               "original_independent_recovery_run": 37931212920,
               "development_data_only": True, "portfolio_cagr_computed": False,
               "production_adoption": False, "original_outcome_sha256": FROZEN_TI["2"],
               "variants": {}}
    for variant in VARIANTS:
        q = p.loc[p.variant.eq(variant)]
        zc = c.loc[c.variant.eq(variant)]
        if len(q) != 3 * N_DATES or len(zc) != 3 * N_DATES:
            raise ValueError("Incomplete date/pair attribution")
        pair_flip = {}
        for pair, gp in q.groupby("pair"):
            f = gp.loc[gp.flip]
            pair_flip[pair] = {"count": len(gp), "flips": len(f), "rate": float(gp.flip.mean())}
        expected = ref["models"][variant]["pairs"]
        for pair, m in pair_flip.items():
            if not np.isclose(m["rate"], expected[pair]["top1_disagreement_fraction"], atol=1e-12, rtol=0):
                raise ValueError("Physical Top1 recomputation disagrees with frozen evidence")
        flipped = q.loc[q.flip]
        eligible = flipped.loc[flipped.both_future_returns_mature]
        margins = flipped.min_norm_margin.dropna()
        quality = zc.loc[zc.mature]
        if not quality.empty and not quality.signal_date.nunique() >= 1:
            raise ValueError("Invalid quality support")
        summary["variants"][variant] = {
            "total_pairs": int(len(q)),
            "total_flips": int(len(flipped)),
            "top1_flip_fraction": float(q.flip.mean()),
            "pairs": pair_flip,
            "flip_margin_observable": len(margins),
            "flip_weak_fraction_among_valid_0p10": float((margins <= 0.1).mean()) if len(margins) else None,
            "flip_weak_fraction_among_valid_0p05": float((margins <= 0.05).mean()) if len(margins) else None,
            "flip_weak_fraction_among_valid_0p20": float((margins <= 0.2).mean()) if len(margins) else None,
            "flip_strong_margin_count": int((margins > 0.1).sum()),
            "flip_mature_forward_return_count": int(len(eligible)),
            "flip_abs_forward_return_diff_median_pp": float(eligible.abs_forward_return_difference_pp.median()) if len(eligible) else None,
            "flip_abs_forward_return_diff_p90_pp": float(eligible.abs_forward_return_difference_pp.quantile(.90)) if len(eligible) else None,
            "flip_abs_forward_return_diff_gt1pp_fraction": float((eligible.abs_forward_return_difference_pp > 1).mean()) if len(eligible) else None,
            "flip_abs_forward_return_diff_gt5pp_fraction": float((eligible.abs_forward_return_difference_pp > 5).mean()) if len(eligible) else None,
            "mature_top1_observation_count": int(len(quality)),
            "mature_top1_mean_forward_return_pct": float(quality.observed_forward_return_pct.mean()) if len(quality) else None,
            "mature_top1_mean_realized_percentile": float(quality.observed_target_percentile.mean()) if len(quality) else None,
            "by_year": {str(year): {
                "flip_fraction": float(y.flip.mean()),
                "flips": int(y.flip.sum()), "date_pair_count": len(y)}
                for year, y in q.groupby(q.signal_date.dt.year)}
        }
    return c, p, summary


def main():
    parser = argparse.ArgumentParser()
    for arg in ("annuals", "repeat2", "reference", "out"):
        parser.add_argument("--" + arg, type=Path, required=True)
    a = parser.parse_args()
    if a.out.exists() and any(a.out.iterdir()):
        raise ValueError("Output must be fresh")
    a.out.mkdir(parents=True, exist_ok=True)
    vectors, hashes = original_year_vectors(a.annuals)
    choices, pairs, summary = reconstruct(vectors, a.repeat2, a.reference)
    summary["yearly_artifact_sha256"] = hashes
    summary["preregistration_sha256"] = sha(ROOT/"compact21_flip_regret_v1/PREREGISTRATION.md")
    summary["source_sha256"] = sha(ROOT/"compact21_flip_regret_v1/analyze.py")
    (a.out/"SUMMARY.json").write_text(json.dumps(summary, indent=2, allow_nan=False)+"\n")
    choices.to_csv(a.out/"TOP1_CHOICES.csv", index=False)
    pairs.to_csv(a.out/"TOP1_FLIP_PAIRS.csv", index=False)
    report=["# Compact21 Top1 flip / realized return gap diagnostic", "",
      "Validated 114 monthly dates (three source pairs); independent original BASE parity.",
      "Scores were evaluated on identical Repeat2 inference features. Return gaps are ex-post 21-session return differences, **not CAGR**.",
      "", "| Variant | Disagreement | Weak-margin flips (<= 0.1 IQR) | Clear-margin flips | Mature flip pairs | Absolute return gap, median (pp) | Absolute return gap, p90 (pp) |",
      "|---|---:|---:|---:|---:|---:|---:|"]
    for name,x in summary["variants"].items():
        report.append(f"| {name} | {x['top1_flip_fraction']:.2%} ({x['total_flips']}/{x['total_pairs']}) | "
                      f"{x['flip_weak_fraction_among_valid_0p10']:.2%} | {x['flip_strong_margin_count']} | "
                      f"{x['flip_mature_forward_return_count']} | "
                      f"{x['flip_abs_forward_return_diff_median_pp']:.3f} | "
                      f"{x['flip_abs_forward_return_diff_p90_pp']:.3f} |")
    report += ["", "## Per-pair BASE Top1 disagreement"]
    for k,x in summary["variants"]["BASE_NATIVE"]["pairs"].items():
        report.append(f"- {k}: {x['flips']}/{x['count']} = {x['rate']:.2%}")
    report += ["", "## Interpretation rule",
               "No margin threshold was tuned. If most flips have clear margins, a simple near-tie-only filter is not a comprehensive solution; if near-margin events concentrate, the cause still requires causal stability and quality testing.",
               "Realized return gaps are an *ex-post* descriptive diagnostic; they do not prove that any algorithm can identify the better choice ahead of time. Do not infer portfolio CAGR, taxes, turnover, MaxDD, or live gains.",
               "Raw date-level evidence is retained in TOP1_CHOICES.csv and TOP1_FLIP_PAIRS.csv."]
    (a.out/"SUMMARY.md").write_text("\n".join(report)+"\n")
    print((a.out/"SUMMARY.md").read_text(), flush=True)


if __name__ == "__main__":
    main()
