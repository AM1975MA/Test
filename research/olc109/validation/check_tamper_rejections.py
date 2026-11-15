"""Negative controls: reject materially forged ledgers, including balanced ones."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from account_reference import audit_account, prepare_panel


def run(root):
    root = Path(root)
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        panel = prepare_panel({k: z[k] for k in z.files})
    outcomes = []
    def account(name):
        folder = root / "results" / name
        return ([pd.read_csv(folder / file, float_precision="round_trip") for file in ("DAILY.csv.gz", "ORDERS.csv.gz", "INSTRUCTIONS.csv.gz")],
                json.loads((folder / "METRICS.json").read_text()))
    frames, meta = account("PASSIVE__BASE")
    audit_account(panel, *frames, meta)
    outcomes.append(dict(test="unchanged_control", status="PASS_ACCEPTED"))
    def reject(name, frames, metadata, expected):
        try:
            audit_account(panel, *frames, metadata)
        except AssertionError as exc:
            actual = str(exc)
            assert expected in actual, ("WRONG_REJECTION_CAUSE", name, expected, actual)
            outcomes.append(dict(test=name, status="PASS_REJECTED", rejection=actual))
        else:
            raise AssertionError(("TAMPER_ACCEPTED", name))
    # A coherent, long-only, self-financed passive account invests only 80% of
    # the required amount. Every reported cash/NAV is regenerated to reconcile.
    # The quantity rule must reject it before relying on terminal metrics.
    daily, orders, instructions = [f.copy(deep=True) for f in frames]
    trade = orders.iloc[0]
    quantity = float(trade.quantity) * .8
    amount = quantity * float(trade.price)
    cost = meta["ticket"] + meta["impact_bps"] / 10000 * amount
    cash = 10000 - amount - cost
    j = int(trade.j)
    orders.loc[0, ["quantity", "notional", "cost"]] = [quantity, amount, cost]
    for i, row in daily.iterrows():
        k = int(row.k)
        price = panel["O"][k, j] if panel["valid_o"][k, j] else panel["C"][k - 1, j]
        close_value = quantity * panel["C"][k, j]
        daily.loc[i, ["cash", "nav_open", "nav_close", "gross"]] = [cash, 10000 if i == 0 else cash + quantity * price,
                                                                     cash + close_value, close_value / (cash + close_value)]
    reject("balanced_wrong_target_quantity", [daily, orders, instructions], meta, "ORDER_VALUE_VS_TARGET")
    daily, orders, instructions = [f.copy(deep=True) for f in frames]
    orders.loc[0, "cost"] += 1
    reject("forged_fee", [daily, orders, instructions], meta, "ORDER_VALUE_VS_TARGET")
    daily, orders, instructions = [f.copy(deep=True) for f in frames]
    weights = json.loads(instructions.loc[0, "target_weights"])
    weights[j] = .8
    instructions.loc[0, "target_weights"] = json.dumps(weights)
    instructions.loc[0, "gross_target"] = .8
    reject("instruction_altered_without_orders", [daily, orders, instructions], meta, "ORDER_VALUE_VS_TARGET")
    lag_frames, lag_meta = account("PASSIVE__LAG2")
    daily, orders, instructions = [f.copy(deep=True) for f in lag_frames]
    orders.loc[0, ["date", "execution_date", "execution_idx"]] = [daily.iloc[0].date, daily.iloc[0].date, int(daily.iloc[0].k)]
    reject("fill_before_instruction_matures", [daily, orders, instructions], lag_meta, "ORDER_WITHOUT_PENDING_TARGET")
    daily, orders, instructions = [f.copy(deep=True) for f in lag_frames]
    instructions.loc[0, "due_idx"] -= 1
    reject("shortened_lag", [daily, orders, instructions], lag_meta, "WRONG_TARGET_DUE_DATE")
    dual_frames, dual_meta = account("CLUSTER_DUAL21__LAG2")
    daily, orders, instructions = [f.copy(deep=True) for f in dual_frames]
    row = orders.index[orders.instruction_id > 0][0]
    orders.loc[row, "instruction_id"] -= 1
    reject("stale_instruction_identity", [daily, orders, instructions], dual_meta, "ORDER_NOT_FROM_LATEST_MATURED_TARGET")
    result = dict(status="PASS_ALL_NEGATIVE_CONTROLS", positive_controls=1, negative_controls=len(outcomes) - 1, outcomes=outcomes)
    (root / "validation/TAMPER_CONTROLS.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    run(Path(__file__).resolve().parents[1])
