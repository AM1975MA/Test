"""Demonstrate and prevent a deferred-counter CSV parsing mismatch."""
from pathlib import Path
import inspect
import json
import sys
import numpy as np
import pandas as pd
import account_reference as reference


def run(root):
    root = Path(root)
    folder = root / "results_stage2/DEDUP_DUAL_EXIT63__DOUBLE_COST"
    meta = json.loads((folder / "METRICS.json").read_text())
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        panel = reference.prepare_panel({key: z[key] for key in z.files})
    code = reference.audit_account.__code__
    line = next(i for i, text in enumerate(Path(reference.__file__).read_text().splitlines(), 1)
                if text.strip() == "deferred += 1")
    results = []
    for precision in (None, "round_trip"):
        events = []
        def trace(frame, event, arg):
            if frame.f_code is code and event == "line" and frame.f_lineno == line:
                state = frame.f_locals
                ids = np.flatnonzero(state["missing"])
                events.append(dict(date=state["day"], instruction_id=state["pending"]["instruction_id"],
                                   isins=[panel["names"][j] for j in ids], units=state["units"][ids].tolist(),
                                   execution_target=state["executable_target"][ids].tolist(),
                                   marked_eur=(state["units"][ids] * state["mark"][ids]).tolist()))
            return trace
        tables = [pd.read_csv(folder / name, float_precision=precision)
                  for name in ("DAILY.csv.gz", "ORDERS.csv.gz", "INSTRUCTIONS.csv.gz")]
        sys.settrace(trace)
        try:
            summary, _, _ = reference.audit_account(panel, *tables, meta)
        finally:
            sys.settrace(None)
        results.append(dict(parser=precision or "pandas_default", deferred=summary["deferred_sessions_reconstructed"],
                            reported_deferred=meta["deferred_sessions"], max_nav_error=summary["max_nav_cash_error"], events=events))
    assert results[0]["deferred"] == 0 and results[1]["deferred"] == results[1]["reported_deferred"] == 1
    assert results[1]["events"][0]["date"] == "2022-12-12"
    assert results[1]["events"][0]["isins"] == ["FR0010405431"]
    assert results[1]["events"][0]["units"][0] <= 1e-10
    output = dict(status="PASS_CSV_ROUND_TRIP_PENDING_REGRESSION", results=results,
                  financial_implementation_changed=False, financial_results_changed=False,
                  correction="Parse serialized financial binary64 values with float_precision='round_trip'; retain strict pending and economic-position tests.")
    (root / "validation/CSV_PRECISION_REGRESSION.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
