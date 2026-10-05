"""Signed rank attribution for the frozen feature/label factorial design.

No labels, realized returns, fitting, or financial outcomes are read here.
Contributions describe algorithm responses on constructed fixed training
interventions, not economic causal effects. Feature and label contributions
sum to the total rank change; interaction is a separate diagnostic and must
not be added again. Nonnegative MAD contrasts are not additive attributions.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd

CELLS = ("AA", "BA", "AB", "BB")
CONTRASTS = {
    "AA-BA": ("AA", "BA", "feature_at_labels_A"),
    "AB-BB": ("AB", "BB", "feature_at_labels_B"),
    "AA-AB": ("AA", "AB", "labels_at_features_A"),
    "BA-BB": ("BA", "BB", "labels_at_features_B"),
    "AA-BB": ("AA", "BB", "total"),
}


def _finite_mean(values):
    finite = [float(value) for value in values if value is not None and math.isfinite(value)]
    return float(np.mean(finite)) if finite else None


def _validate(frame, date_col, ticker_col, expected_keys):
    required = {date_col, ticker_col, *("pred" + cell for cell in CELLS)}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing factorial columns: {sorted(required - set(frame.columns))}")
    if frame.empty:
        raise ValueError("Empty factorial inference coverage")
    z = frame[list(required)].copy()
    keys = [date_col, ticker_col]
    if z[keys].isna().any().any():
        raise ValueError("Missing factorial inference keys")
    z[date_col] = pd.to_datetime(z[date_col], errors="raise")
    if z[date_col].isna().any() or z[date_col].dt.tz is not None:
        raise ValueError("Invalid or timezone-aware factorial dates")
    if not z[date_col].eq(z[date_col].dt.normalize()).all():
        raise ValueError("Factorial dates must be normalized session dates")
    z[ticker_col] = z[ticker_col].astype(str)
    if z[ticker_col].str.strip().eq("").any() or z.duplicated(keys).any():
        raise ValueError("Empty or duplicate factorial keys")
    for cell in CELLS:
        column = "pred" + cell
        z[column] = pd.to_numeric(z[column], errors="raise")
        if not np.isfinite(z[column].to_numpy(float)).all():
            raise ValueError(f"Nonfinite predictions in cell {cell}")
    z = z.sort_values(keys).reset_index(drop=True)
    if expected_keys is not None:
        e = expected_keys.copy()
        if not set(keys).issubset(e) or e[keys].isna().any().any():
            raise ValueError("Invalid expected factorial coverage")
        e[date_col] = pd.to_datetime(e[date_col], errors="raise")
        e[ticker_col] = e[ticker_col].astype(str)
        if e.duplicated(keys).any() or not z[keys].equals(e[keys].sort_values(keys).reset_index(drop=True)):
            raise ValueError("Factorial coverage differs from expected keys")
    return z


def evaluate_factorial(frame, date_col="signal_date", ticker_col="ticker", tolerance=1e-12, expected_keys=None):
    """Return retained row effects and equal-date factorial summaries.

    Input: one aligned inference row per date/ticker with predAA, predBA,
    predAB, predBB. Extra columns are ignored, including future outcomes.
    Signed effects use average-tie percentile ranks within each date; selected
    winners and Top5 sets use descending score then ascending ticker.
    Optional expected_keys certifies that no complete inference row is lost.
    Spearman is undefined (None) if either ranking vector is constant.
    """
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("Identity tolerance must be positive and finite")
    z = _validate(frame, date_col, ticker_col, expected_keys)
    retained = []
    per_date = []
    for date, g in z.groupby(date_col, sort=True):
        g = g.sort_values(ticker_col).reset_index(drop=True)
        n = len(g)
        if n < 2:
            raise ValueError("Factorial query requires at least two tickers")
        ranks = {cell: g["pred"+cell].rank(method="average", pct=True).to_numpy(float) for cell in CELLS}
        orders = {cell: g.sort_values(["pred"+cell, ticker_col], ascending=[False, True], kind="stable").index.to_numpy() for cell in CELLS}
        aa, ba, ab, bb = (ranks[cell] for cell in CELLS)
        feature = .5 * ((ba-aa) + (bb-ab))
        label = .5 * ((ab-aa) + (bb-ba))
        interaction = bb-ba-ab+aa
        total = bb-aa
        residual = feature+label-total
        max_residual = float(np.max(np.abs(residual)))
        if max_residual > tolerance:
            raise ValueError("Signed feature plus label attribution identity failed")
        cancellations = (np.abs(feature)+np.abs(label)-np.abs(total)) > tolerance
        exact_cancellations = cancellations & (np.abs(total) <= tolerance)
        for index in range(n):
            retained.append({date_col: pd.Timestamp(date).isoformat(), ticker_col: str(g.loc[index, ticker_col]),
                **{"rank"+cell: float(ranks[cell][index]) for cell in CELLS},
                "signed_feature": float(feature[index]), "signed_label": float(label[index]),
                "interaction": float(interaction[index]), "total_rank_change": float(total[index]),
                "identity_residual": float(residual[index]), "cancellation": bool(cancellations[index]),
                "exact_total_cancellation": bool(exact_cancellations[index])})
        contrast_results = {}
        for name, (first, second, interpretation) in CONTRASTS.items():
            a, b = ranks[first], ranks[second]
            oa, ob = orders[first], orders[second]
            top_a = set(g.loc[oa[:min(5,n)], ticker_col])
            top_b = set(g.loc[ob[:min(5,n)], ticker_col])
            rho = float(np.corrcoef(a, b)[0,1]) if np.ptp(a) > 0 and np.ptp(b) > 0 else None
            contrast_results[name] = dict(rank_mad=float(np.mean(np.abs(b-a))), spearman=rho,
                top1_flip=float(oa[0] != ob[0]), top5_jaccard=len(top_a & top_b)/len(top_a | top_b),
                top1_a=str(g.loc[oa[0], ticker_col]), top1_b=str(g.loc[ob[0], ticker_col]),
                intervention=interpretation)
        effects = dict(feature_mean_abs=float(np.mean(np.abs(feature))),
            label_mean_abs=float(np.mean(np.abs(label))), interaction_mean_abs=float(np.mean(np.abs(interaction))),
            total_mean_abs=float(np.mean(np.abs(total))),
            feature_mean_signed=float(feature.mean()), label_mean_signed=float(label.mean()),
            interaction_mean_signed=float(interaction.mean()), total_mean_signed=float(total.mean()),
            cancellation_fraction=float(cancellations.mean()), exact_total_cancellation_fraction=float(exact_cancellations.mean()),
            identity_max_abs=max_residual)
        ties = {cell: dict(tied_rows=int(g["pred"+cell].duplicated(keep=False).sum()),
            top1_tie_count=int(g["pred"+cell].eq(g.loc[orders[cell][0], "pred"+cell]).sum()),
            top5_boundary_tie_count=int(g["pred"+cell].eq(g.loc[orders[cell][min(5,n)-1], "pred"+cell]).sum())) for cell in CELLS}
        per_date.append({date_col: pd.Timestamp(date).isoformat(), "n_tickers": n,
            "contrasts": contrast_results, "effects": effects, "ties": ties})
    aggregate = {"contrasts": {}, "effects": {metric: _finite_mean(d["effects"][metric] for d in per_date)
        for metric in per_date[0]["effects"]}}
    for name in CONTRASTS:
        aggregate["contrasts"][name] = {metric: _finite_mean(d["contrasts"][name][metric] for d in per_date)
            for metric in ("rank_mad", "spearman", "top1_flip", "top5_jaccard")}
        aggregate["contrasts"][name]["defined_spearman_dates"] = sum(d["contrasts"][name]["spearman"] is not None for d in per_date)
        aggregate["contrasts"][name]["dates"] = len(per_date)
    return dict(rank_effects=retained, per_date=per_date, aggregate=aggregate,
        coverage=dict(rows=len(z), dates=len(per_date), shared_four_cell_keys=True),
        identity=dict(PASS=True, tolerance=float(tolerance), max_abs=max(d["effects"]["identity_max_abs"] for d in per_date)),
        weighting="Each inference date has equal weight; each ticker has equal weight within its date.",
        rank_policy="Per-date average-tie percentile ranks; Top1 and Top5 sorted by descending score, ascending ticker.",
        attribution="Feature + label equals BB-AA; interaction is a separate contrast, not another additive contribution.",
        interpretation="Constructed training-intervention responses, not economic causal attribution; no percentage shares are assigned.")
