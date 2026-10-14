"""Diagnostica degli audit ListNet già salvati: nessun fit né modifica input."""
import argparse
import collections
import hashlib
import json
from pathlib import Path

import numpy as np


def diagnose(path):
    path = Path(path)
    result = json.loads(path.read_text(encoding="utf-8"))
    audits = [s for year in result["per_year"].values()
              for transform in year["transforms"].values() for s in transform["seeds"]]
    capped = [s for s in audits if s["stop_reason"] == "max_epochs"]
    changes = {}
    for kind in ("train_loss", "validation_loss"):
        values = []
        for audit in capped:
            history = audit["history"]
            old, last = history[-11][kind], history[-1][kind]
            values.append((old - last) / old)
        changes[kind] = dict(count_improved=sum(x > 0 for x in values),
                            count=len(values), median_relative_improvement=float(np.median(values)))
    return dict(
        source_result_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        fits_executed=0, networks=len(audits),
        stop_reasons=dict(collections.Counter(s["stop_reason"] for s in audits)),
        best_epoch_zero=sum(s["best_epoch"] == 0 for s in audits),
        best_epoch_min_median_max=np.percentile([s["best_epoch"] for s in audits], [0, 50, 100]).tolist(),
        validation_relative_improvement_min_median_max=np.percentile(
            [(s["initial_validation_loss"]-s["best_validation_loss"])/s["initial_validation_loss"]
             for s in audits], [0, 50, 100]).tolist(),
        clipped_step_fraction=sum(s["clipped_steps"] for s in audits)/sum(s["optimizer_steps"] for s in audits),
        capped_last_ten_epochs=changes,
        repeat2_queries={year: dict(subtrain=v["transforms"]["2"]["subtrain_queries"],
                                   validation=v["transforms"]["2"]["validation_queries"])
                         for year, v in result["per_year"].items()},
        interpretation="Raggiungere il limite di epoche non dimostra underfit né un futuro aumento del CAGR.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--result", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(diagnose(args.result), indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(out.read_text(encoding="utf-8"))
