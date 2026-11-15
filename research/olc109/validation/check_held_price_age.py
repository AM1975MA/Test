"""Descriptive observation age, including every closing state and final day."""
from pathlib import Path
import json
import numpy as np
import pandas as pd


def run(root):
    root = Path(root)
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        dates, observed = z["dates"], z["observed"]
        names = z["names"]
    latest = np.maximum.accumulate(np.where(observed, np.arange(len(dates))[:, None], -1), axis=0)
    calendar = dates.astype("datetime64[D]").astype(np.int64)
    ages = calendar[:, None] - calendar[np.maximum(latest, 0)]
    summary = []
    for stage, directory, output in ((1, "results", "validation"), (2, "results_stage2", "validation/stage2"),
                                     (3, "results_stage3", "validation/stage3")):
        records = []
        for folder in sorted((root / directory).glob("*__*")):
            if not (folder / "METRICS.json").exists():
                continue
            daily = pd.read_csv(folder / "DAILY.csv.gz", float_precision="round_trip")
            orders = pd.read_csv(folder / "ORDERS.csv.gz", float_precision="round_trip")
            fills = {int(k): g for k, g in orders.groupby("execution_idx")}
            units = np.zeros(len(names))
            detail = dict(max_held_price_age_calendar_days=0, held_sessions_with_stale_close=0,
                          held_sessions_with_price_age_over5=0, close_states_checked=0,
                          individual_held_closing_marks_checked=0, final_close_included=True)
            for bar in daily.itertuples(index=False):
                if bar.k in fills:
                    for fill in fills[bar.k].itertuples(index=False):
                        units[int(fill.j)] += float(fill.quantity) * (1 if fill.side == "BUY" else -1)
                ids = np.flatnonzero(units > 1e-10)
                assert len(ids) == bar.positions, ("CLOSE_HOLDING_COUNT", folder.name, bar.k)
                held_ages = ages[bar.k, ids]
                detail["max_held_price_age_calendar_days"] = max(detail["max_held_price_age_calendar_days"], int(held_ages.max(initial=0)))
                detail["held_sessions_with_stale_close"] += int(np.any(held_ages > 0))
                detail["held_sessions_with_price_age_over5"] += int(np.any(held_ages > 5))
                detail["close_states_checked"] += 1
                detail["individual_held_closing_marks_checked"] += len(ids)
            assert detail["close_states_checked"] == len(daily)
            arm, scenario = folder.name.split("__")
            records.append(dict(path_id=folder.name, arm=arm, scenario=scenario, **detail))
        output_path = root / output
        output_path.mkdir(parents=True, exist_ok=True)
        frame = pd.DataFrame(records)
        frame.to_csv(output_path / "HELD_PRICE_AGE_ALL_CLOSES.csv", index=False)
        summary.append(dict(stage=stage, paths=len(records), closing_states=int(frame.close_states_checked.sum()),
                            held_marks=int(frame.individual_held_closing_marks_checked.sum()),
                            maximum_age_calendar_days=int(frame.max_held_price_age_calendar_days.max()),
                            held_sessions_with_age_over5=int(frame.held_sessions_with_price_age_over5.sum())))
    result = dict(status="COMPLETE_DESCRIPTIVE_PRICE_AGE_AUDIT", stages=summary,
                  interpretation="Observation age is a vendor-price quality diagnostic; it does not certify contemporaneous tradability.")
    (root / "validation/PRICE_AGE_QA.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
