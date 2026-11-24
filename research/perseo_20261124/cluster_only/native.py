"""Diagnostic cluster-only per-market refits using the same recipes and cutoffs."""

import argparse
from pathlib import Path

from experiment import BASELINES, MODELS, MODEL_COLUMNS, estimated_models, history, selection

import numpy as np
import pandas as pd


def fit_native(panel, previous):
    predictions, audits = [], []
    for (family, market), groups in panel[panel.family.ne("ECONOMIC_EU")].groupby(["family", "market"]):
        scored_days = set(previous.loc[(previous.family == family) & (previous.market == market), "day"])
        dates = sorted(scored_days)
        checks = set(dates[i] for i in (len(dates)//3, len(dates)//2, len(dates)*3//4))
        for day, rows in groups[groups.day.isin(dates)].groupby("day"):
            past = history(groups, day)
            if past.month.nunique() < 24:
                continue
            assert past.label_end.max() < day
            x = rows[list(MODEL_COLUMNS)].to_numpy()
            models = estimated_models(past)
            scored = rows.copy()
            for name, model in models.items():
                scored[f"{name}_NATIVE"] = model.predict(x)
            if day in checks:
                perturbed = groups.copy()
                perturbed.loc[perturbed.label_end >= day, "forward_rank"] = 87.5
                repeat = estimated_models(history(perturbed, day))
                for name, model in repeat.items():
                    np.testing.assert_array_equal(scored[f"{name}_NATIVE"].to_numpy(), model.predict(x))
            predictions.append(scored)
            audits.append(dict(
                family=family, market=market, day=day, latest_label=past.label_end.max(),
                months=past.month.nunique(), samples=len(past), label_perturbation=day in checks,
            ))
    return pd.concat(predictions), pd.DataFrame(audits)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path(__file__).resolve().parent / "results")
    root = parser.parse_args().results
    dates = ["day", "label_end"]
    panel = pd.read_csv(root / "SNAPSHOT_PANEL.csv.gz", parse_dates=dates)
    common = pd.read_csv(root / "MONTHLY_PICKS.csv", parse_dates=["day"])
    predicted, audit = fit_native(panel, common)
    names = tuple(f"{name}_NATIVE" for name in MODELS)
    scored = selection(predicted, methods=names)
    predicted.to_csv(root / "NATIVE_SCORED_CLUSTERS.csv.gz", index=False)
    scored.to_csv(root / "NATIVE_MONTHLY_PICKS.csv", index=False)
    audit.to_csv(root / "NATIVE_FIT_CUTOFFS.csv", index=False)
    print("NATIVE_QA_PASS", len(predicted), len(audit), audit.label_perturbation.sum(), flush=True)


if __name__ == "__main__":
    main()
