#!/usr/bin/env python3
"""V3 L06.2: single predeclared risk-weight policy test (NO hard ETF exclusions).

Input scores from SUCCESSFUL independent V3 L06 annual OOS training run
39662062361, artifact v3-l06-risk-standalone-results:
* Tail expert score frozen, already genuine annual 2018-26 OOS.
* p_bad OOS head fit on fully matured labels before each annual cutoff.
* Exact 149 ETF, 500x24 canonical baskets, same 101 matured forward-21D months.

Control: frozen L05 selection Top3 Tail scores, [0.5,0.3,0.2] fixed weights.
New SINGLE intervention: SAME three tickers, no veto or replacement,
    w_i = normalize(base_w_i * (1 - 0.5 * monthly_risk_percentile_i)).
Coefficient 0.5 chosen ex ante, no OOS tuning. No CAGR, PnL, model refit,
regime, score fusion or full-system risk layer.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

BASE = "TOP3_DECAY"
TREATMENT = "TOP3_SOFT_RISK50"
ALPHA = 0.50
BASE_WEIGHTS = np.array([0.5, 0.3, 0.2], dtype=float)
BASKET_SHA = "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"
METRICS = [
    "winner_in_selected3", "winner_weight", "future_bottom3_weight",
    "selected_rank_quality", "selected_oracle_regret21",
    "target_weight_churn", "effective_n_holdings", "max_position_weight",
    "weight_shift_L1_half"
]


def load_baskets(path, universe):
    path = Path(path)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == BASKET_SHA
    raw = pd.read_csv(path)
    assert {"basket", "ticker"} <= set(raw.columns)
    raw["ticker"] = raw["ticker"].astype(str).str.upper()
    assert not raw.duplicated(["basket", "ticker"]).any()
    assert set(raw.ticker) <= set(universe)
    baskets = [
        g.ticker.tolist()
        for _, g in raw.sort_values(["basket", "ticker"]).groupby("basket")
    ]
    assert len(baskets) == 500
    assert all(len(b) == 24 for b in baskets)
    return baskets


def soft_weights(risk_percentiles):
    """Positivity and mass preservation, ticker membership invariant."""
    assert risk_percentiles.shape == (3,)
    assert np.isfinite(risk_percentiles).all()
    assert np.min(risk_percentiles) >= 0 and np.max(risk_percentiles) <= 1
    w = BASE_WEIGHTS * (1.0 - ALPHA * risk_percentiles)
    assert (w > 0).all()
    w = w / w.sum()
    assert abs(w.sum() - 1) < 1e-12
    return w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default="runs/v3_l06_ref")
    ap.add_argument("--baskets", default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    ap.add_argument("--out", default="runs/v3_l06_soft")
    args = ap.parse_args()

    ref = Path(args.reference)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    scores = pd.read_csv(ref / "RISK_SCORES_OOS.csv", parse_dates=["signal_date"])
    previous = pd.read_csv(ref / "PAIRED_MONTHLY.csv", parse_dates=["signal_date"])

    assert len(scores) == 15198, len(scores)
    assert not scores.duplicated(["signal_date", "ticker"]).any()
    assert {"signal_date", "ticker", "TAIL_ELITE45", "p_bad",
            "risk_percentile", "target_rank_21", "fwd_ret_21"} <= set(scores.columns)
    assert set(previous.variant) == {BASE, "TOP3_DECAY_RISK85"}
    assert (scores["risk_percentile"].dropna().between(0, 1)).all()

    baskets = load_baskets(args.baskets, scores.ticker.unique())
    prior_positions = {name: [None] * len(baskets) for name in (BASE, TREATMENT)}
    rows = []
    risk_diagnostics = []
    all_members_identical = True

    for dt, g in scores.groupby("signal_date", sort=True):
        if g.fwd_ret_21.isna().any():
            continue
        g = g.sort_values("ticker").reset_index(drop=True)
        assert len(g) == 149
        score = g.TAIL_ELITE45.to_numpy(float)
        fwd = g.fwd_ret_21.to_numpy(float)
        risk = g.risk_percentile.to_numpy(float)
        where = {t: i for i, t in enumerate(g.ticker)}
        assert np.isfinite(np.c_[score, fwd, risk]).all()
        results = {name: [] for name in (BASE, TREATMENT)}

        # Only diagnostics; bottom events and future returns NOT used in allocation.
        selected_risk = []
        selected_is_future_bottom = []

        for i, basket in enumerate(baskets):
            ids = np.array([where[t] for t in basket], dtype=int)
            y = fwd[ids]
            pred = score[ids]
            predicted_risk = risk[ids]
            order = np.argsort(-pred, kind="stable")
            top3 = order[:3]
            assert len(top3) == 3

            best_rank = np.argsort(-y, kind="stable")
            true_best = int(best_rank[0])
            true_bottom3 = set(best_rank[-3:].tolist())
            quality = np.empty(24, dtype=float)
            quality[best_rank] = np.linspace(1, 0, 24)

            # The same, identical membership is used for both policies.
            w0 = BASE_WEIGHTS.copy()
            w1 = soft_weights(predicted_risk[top3])
            assert np.all(w1 > 0)
            assert np.isclose(w1.sum(), 1)
            all_members_identical &= bool(set(top3) == set(top3))
            for k, row in enumerate(top3):
                selected_risk.append(float(predicted_risk[row]))
                selected_is_future_bottom.append(int(int(row) in true_bottom3))

            for policy, weights in ((BASE, w0), (TREATMENT, w1)):
                positions = {
                    str(g.ticker.iloc[ids[top3[j]]]): float(weights[j]) for j in range(3)
                }
                last = prior_positions[policy][i]
                churn = np.nan if last is None else (
                    sum(abs(positions.get(t, 0) - last.get(t, 0))
                        for t in set(positions) | set(last)) / 2
                )
                prior_positions[policy][i] = positions

                best_weight = (
                    float(weights[np.flatnonzero(top3 == true_best)[0]])
                    if true_best in top3 else 0.0
                )
                bad_weight = float(sum(
                    weights[j] for j, ix in enumerate(top3)
                    if int(ix) in true_bottom3
                ))
                results[policy].append({
                    "winner_in_selected3": float(true_best in top3),
                    "winner_weight": best_weight,
                    "future_bottom3_weight": bad_weight,
                    "selected_rank_quality": float(np.dot(weights, quality[top3])),
                    "selected_oracle_regret21": float(y.max() - np.dot(weights, y[top3])),
                    "target_weight_churn": churn,
                    "effective_n_holdings": float(1 / np.sum(weights**2)),
                    "max_position_weight": float(np.max(weights)),
                    "weight_shift_L1_half": float(np.sum(np.abs(weights - BASE_WEIGHTS)) / 2)
                })

        # Report AP and ROC conditional upon *the 3 candidates the Tail actually picks*.
        # 500 overlapping baskets -> not independent, evaluate by calendar month.
        selected_risk = np.array(selected_risk)
        selected_is_future_bottom = np.array(selected_is_future_bottom)
        risk_diagnostics.append({
            "signal_date": dt,
            "selected_bottom3_event_rate": float(selected_is_future_bottom.mean()),
            "selected_bottom3_risk_AP": float(average_precision_score(
                selected_is_future_bottom, selected_risk)),
            "selected_bottom3_risk_AUC": float(roc_auc_score(
                selected_is_future_bottom, selected_risk))
        })

        for policy, values in results.items():
            table = pd.DataFrame(values)
            data = table.mean(numeric_only=True, skipna=True).to_dict()
            rows.append({"signal_date": dt, "year": int(dt.year), "variant": policy,
                         "n_baskets": len(baskets), **data})

    df = pd.DataFrame(rows)
    df.signal_date = pd.to_datetime(df.signal_date)
    assert all_members_identical
    assert len(df) == 101 * 2
    assert not df.duplicated(["signal_date", "variant"]).any()
    df.to_csv(out / "PAIRED_MONTHLY.csv", index=False)

    # Exact numerical oracle against the original L06 BASE portfolio; this
    # catches accidental changes to membership, target, rank or churn.
    observed = df[df.variant == BASE].sort_values("signal_date").reset_index(drop=True)
    control = previous[previous.variant == BASE].sort_values("signal_date").reset_index(drop=True)
    pd.testing.assert_series_equal(observed.signal_date, control.signal_date)
    for metric in METRICS[:6]:
        np.testing.assert_allclose(observed[metric], control[metric],
                                   rtol=0, atol=2e-12, equal_nan=True,
                                   err_msg=f"Baseline changed: {metric}")

    treatment = df[df.variant == TREATMENT].sort_values("signal_date").reset_index(drop=True)
    np.testing.assert_allclose(
        observed["winner_in_selected3"], treatment["winner_in_selected3"],
        atol=0, rtol=0, err_msg="Winner membership changed in weight-only experiment"
    )
    assert observed["weight_shift_L1_half"].eq(0).all()

    metric_means = df.groupby("variant")[METRICS].mean()
    metric_means.insert(0, "months", df.groupby("variant").size())
    metric_means.to_csv(out / "RESULTS.csv")
    df.groupby(["year", "variant"], as_index=False)[METRICS].mean().to_csv(
        out / "YEARLY.csv", index=False
    )
    diagnostics = pd.DataFrame(risk_diagnostics)
    diagnostics.to_csv(out / "CONDITIONAL_TOP3_RISK_SKILL.csv", index=False)
    (out / "CONDITIONAL_TOP3_RISK_SUMMARY.json").write_text(json.dumps({
        "months": len(diagnostics),
        "mean_selected_bottom3_event_rate": float(diagnostics.selected_bottom3_event_rate.mean()),
        "mean_conditional_AP": float(diagnostics.selected_bottom3_risk_AP.mean()),
        "mean_conditional_AUC": float(diagnostics.selected_bottom3_risk_AUC.mean()),
        "note": "Conditional candidate risk AP/AUC is diagnostic. 500 basket-selected instances overlap."
    }, indent=2))

    boot = []
    for metric in METRICS:
        diff = (treatment[metric] - observed[metric]).to_numpy(dtype=float)
        if metric == "target_weight_churn":
            diff = diff[1:]
        assert np.isfinite(diff).all()
        n = len(diff)
        rng = np.random.default_rng(20261021)
        block = 6
        reps = 6000
        starts = rng.integers(0, n, size=(reps, int(np.ceil(n / block))))
        index = ((starts[:, :, None] + np.arange(block)) % n).reshape(reps, -1)[:, :n]
        sample = diff[index].mean(axis=1)
        boot.append({
            "arm": TREATMENT, "reference": BASE, "metric": metric,
            "delta": float(diff.mean()),
            "ci95_low": float(np.quantile(sample, 0.025)),
            "ci95_high": float(np.quantile(sample, 0.975)),
            "bootstrap": "paired signal month, circular 6-month blocks, 6000 reps"
        })
    pd.DataFrame(boot).to_csv(out / "PAIRED_BOOTSTRAP.csv", index=False)

    manifest = {
        "date": "2026-10-21", "layer": "L06.2 risk weighting only",
        "single_treatment": "Top3 same tickers, weights proportional to base *(1-0.50*prior predicted bad-risk percentile)",
        "risk_probability_source": "fully prior-fitted annual OOS 45-field logistic risk score, run 39662062361",
        "expert_score_source": "unchanged frozen Tail45 from 39655513813",
        "source_raw": "149 ETF / 500 canonical baskets",
        "original_control_exactly_reproduced": True,
        "model_training": "none (risk model fully frozen)",
        "no_exclusions_or_replacements": True,
        "future_labels_not_used_by_policy": True,
        "no_CAGR_or_portfolio_PnL": True,
        "month_count_mature_forward21": len(observed),
        "already_researched_historical_calendar_not_untouched_holdout": True,
        "require_production_independent_confirmation": True
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))
    print("L06_2_SOFT_RISK_RESULT\\n" + metric_means.to_string(), flush=True)
    print("L06_2_CONDITIONAL_RISK_RESULT\\n" + diagnostics.drop(
        columns=["signal_date"]).mean().to_string(), flush=True)


if __name__ == "__main__":
    main()
