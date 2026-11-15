"""Reproduce the frozen OLC109 account grid without production imports."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

from account_reference import SCENARIOS, audit_account, prepare_panel
from signal_reference import (ARMS, STAGE2_ARMS, STAGE3_ARMS, InstructionVerifier, independent_features,
                              schedules, target_from_data, stage2_target_from_data, stage3_target_from_data, verify_snapshots)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def baseline_comparisons(root, previous, results):
    rows = []
    for arm, old_arm in (("PASSIVE", "PASSIVE"), ("LEADERS", "LEADERS"), ("DUAL21", "DUAL_SELECTIVE_21")):
        for scenario in SCENARIOS:
            old = previous / "results/XETRA_EUR_ETF" / f"{old_arm}__MONTHLY__RAW__{scenario}"
            new = results / f"{arm}__{scenario}"
            if not (old / "METRICS.json").exists():
                rows.append(dict(arm=arm, scenario=scenario, status="PREVIOUS_PATH_NOT_AVAILABLE"))
                continue
            max_difference = 0.
            for filename in ("DAILY.csv.gz", "ORDERS.csv.gz", "INSTRUCTIONS.csv.gz"):
                a, b = pd.read_csv(old / filename, float_precision="round_trip"), pd.read_csv(new / filename, float_precision="round_trip")
                assert list(a.columns) == list(b.columns) and a.shape == b.shape, ("BASELINE_SHAPE", arm, scenario, filename)
                for col in a:
                    if pd.api.types.is_numeric_dtype(a[col]):
                        difference = np.max(np.abs(a[col].to_numpy(dtype=float) - b[col].to_numpy(dtype=float)), initial=0.)
                        assert np.allclose(a[col], b[col], rtol=0, atol=1e-8, equal_nan=True), ("BASELINE_NUMERIC", arm, scenario, filename, col, difference)
                        max_difference = max(max_difference, difference)
                    else:
                        assert a[col].fillna("").tolist() == b[col].fillna("").tolist(), ("BASELINE_LABEL", arm, scenario, filename, col)
            with np.load(old / "DECISIONS.npz", allow_pickle=False) as a, np.load(new / "DECISIONS.npz", allow_pickle=False) as b:
                assert set(a.files) == set(b.files)
                for key in a.files:
                    assert np.allclose(a[key], b[key], rtol=0, atol=1e-8), ("BASELINE_DECISIONS", arm, scenario, key)
            rows.append(dict(arm=arm, scenario=scenario, status="PASS_IDENTICAL_FINANCIAL_PATH", max_absolute_difference=float(max_difference)))
    return rows


def source_liquidity_checks(root, previous, panel, turnover, selected):
    manifest = json.loads((root / "data/LIQUIDITY_MANIFEST.json").read_text())
    assert manifest["input_panel_sha256"] == digest(root / "source/data/XETRA_EUR_ETF.npz")
    assert manifest["output_sha256"] == digest(root / "data/LIQUIDITY.npz")
    sources = {row["isin"]: row for row in manifest["sources"]}
    names = list(map(str, panel["names"]))
    assert set(sources) == set(names)
    seeded = np.random.default_rng(109).choice(len(names), size=min(48, len(names)), replace=False)
    checked = sorted(set(map(int, seeded)) | set(map(int, selected)) | {0, len(names) - 1, int(panel["benchmark"])})
    dates = pd.DatetimeIndex(panel["dates"])
    rows = []
    for j in checked:
        source = sources[names[j]]
        path = previous / source["price_file"]
        assert digest(path) == source["sha256"], ("LIQUIDITY_SOURCE_HASH", names[j])
        frame = pd.read_csv(path, usecols=["date", "close", "volume"])
        frame["date"] = pd.to_datetime(frame["date"])
        assert not frame.date.duplicated().any()
        frame = frame.set_index("date").reindex(dates)
        product = frame["close"].to_numpy() * frame["volume"].to_numpy()
        expected = np.where(panel["observed"][:, j] & np.isfinite(product) & (product >= 0), product, 0.)
        assert np.array_equal(turnover[:, j], expected), ("RAW_CLOSE_TIMES_VOLUME", names[j])
        rows.append(dict(isin=names[j], symbol=source["symbol"], sessions_checked=len(dates),
                         selected_in_any_target=j in selected, zero_sessions=int((expected == 0).sum()),
                         source_sha256=source["sha256"], status="PASS"))
    return rows


def run(root, previous, results_directory="results", output_directory="validation"):
    root, previous = Path(root).resolve(), Path(previous).resolve()
    results, output = root / results_directory, root / output_directory
    output.mkdir(parents=True, exist_ok=True)
    started = datetime.datetime.now(datetime.timezone.utc).isoformat()
    stage2 = results_directory == "results_stage2"
    stage3 = results_directory == "results_stage3"
    freeze_name = "STAGE3_FREEZE.json" if stage3 else "STAGE2_FREEZE.json" if stage2 else "PROTOCOL_FREEZE.json"
    protocol_name = "STAGE3_PROTOCOL.md" if stage3 else "STAGE2_PROTOCOL.md" if stage2 else "DESIGN_AND_PROTOCOL.md"
    arms = STAGE3_ARMS if stage3 else STAGE2_ARMS if stage2 else ARMS
    selector = stage3_target_from_data if stage3 else stage2_target_from_data if stage2 else target_from_data
    snapshot_prefix = "STAGE3_" if stage3 else "STAGE2_" if stage2 else ""
    count = 40 if stage3 else 50 if stage2 else 110
    freeze = json.loads((root / "docs" / freeze_name).read_text())
    manifest = json.loads((results / "RUN_MANIFEST.json").read_text())
    assert digest(root / "docs" / protocol_name) == freeze["protocol_sha256"] == manifest["protocol_sha256"]
    assert freeze["planned_unique_paths"] == manifest["planned_unique_paths"] == count
    assert manifest["completed_paths"] == count and "end_utc" in manifest, "RUN_NOT_COMPLETE"
    for path, recorded_hash in manifest["code_hashes"].items():
        assert digest(root / path) == recorded_hash, ("FROZEN_CODE_CHANGED", path)
    for path, recorded_hash in manifest["data_hashes"].items():
        assert digest(root / path) == recorded_hash, ("FROZEN_DATA_CHANGED", path)
    assert digest(root / f"data/{snapshot_prefix}SNAPSHOTS.json.gz") == manifest["snapshot_sha256"]
    assert digest(root / f"data/{snapshot_prefix}REP_CORRELATIONS.npz") == manifest["correlation_sha256"]
    assert digest(root / "source/data/XETRA_EUR_ETF.npz") == "14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96"
    expected = {f"{arm}__{scenario}" for arm in arms for scenario in SCENARIOS}
    found = {p.parent.name for p in results.glob("*/METRICS.json")}
    assert found == expected, ("ACCOUNT_GRID", expected - found, found - expected)
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        panel = {key: z[key] for key in z.files}
    assert np.array_equal(panel["names"], np.sort(panel["names"])), "INPUT_ISIN_ORDER"
    prepared = prepare_panel(panel)
    with np.load(root / "data/LIQUIDITY.npz", allow_pickle=False) as z:
        assert np.array_equal(z["dates"], panel["dates"]) and np.array_equal(z["names"], panel["names"])
        turnover = z["turnover"]
    print("Rebuilding features and complete-link clusters from data", flush=True)
    f = independent_features(panel, prepared, turnover)
    f["turnover"] = np.where(panel["observed"], turnover, 0.)
    monthly, weekly, keys = schedules(panel["dates"])
    snapshots, groups = verify_snapshots(root, panel["names"], f, keys, snapshot_prefix)
    pd.DataFrame(groups).to_csv(output / "INDEPENDENT_GROUP_CONDITIONS.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    targets, selected = {}, set()
    for arm in arms:
        for k in keys if arm != "PASSIVE" else keys[:1]:
            targets[(arm, k)] = selector(panel, f, snapshots[k], arm, k)
            selected.update(targets[(arm, k)][1]["selected_indices"])
    print(f"Reconstructed {len(keys)} snapshots, {len(groups)} groups, {len(targets)} raw selection targets", flush=True)
    baseline = [] if (stage2 or stage3) else baseline_comparisons(root, previous, results)
    pd.DataFrame(baseline).to_csv(output / "BASELINE_REPLICATION.csv", index=False)
    source_checks = source_liquidity_checks(root, previous, panel, turnover, selected)
    pd.DataFrame(source_checks).to_csv(output / "LIQUIDITY_SOURCE_CHECKS.csv", index=False)
    reconstruction, attribution, annual, participation, held_quality = [], [], [], [], []
    for seq, path_id in enumerate(sorted(expected), 1):
        arm, scenario = path_id.split("__")
        folder = results / path_id
        meta = json.loads((folder / "METRICS.json").read_text())
        assert meta["path_id"] == path_id and meta["arm"] == arm and meta["scenario"] == scenario
        # Preserve each serialized binary64 quantity: default C-parser rounding
        # can erase an economically immaterial but strict-positive pending dust.
        daily, orders, instructions, decisions = [pd.read_csv(folder / filename, float_precision="round_trip") for filename in
                    ("DAILY.csv.gz", "ORDERS.csv.gz", "INSTRUCTIONS.csv.gz", "DECISIONS.csv")]
        with np.load(folder / "DECISIONS.npz", allow_pickle=False) as z:
            arrays = {key: z[key] for key in z.files}
        checker = InstructionVerifier(arm, f, monthly, weekly, targets, decisions, arrays, instructions)
        quality = dict(max_held_price_age_calendar_days=0, held_sessions_with_stale_close=0,
                       held_sessions_with_price_age_over5=0, close_states_checked=0)
        def state_check(k, units, cash):
            checker(k, units, cash)
            if k < keys[0] + 1:
                return
            ids = np.flatnonzero(units > 1e-10)
            ages = f["age"][k, ids]
            quality["max_held_price_age_calendar_days"] = max(quality["max_held_price_age_calendar_days"], int(ages.max(initial=0)))
            quality["held_sessions_with_stale_close"] += int(np.any(ages > 0))
            quality["held_sessions_with_price_age_over5"] += int(np.any(ages > 5))
            quality["close_states_checked"] += 1
        summary, pnl, years = audit_account(prepared, daily, orders, instructions, meta, state_checker=state_check)
        summary.update(checker.finish())
        assert summary["deferred_sessions_reconstructed"] == meta["deferred_sessions"], ("DEFERRED_SESSION_COUNT", path_id, summary["deferred_sessions_reconstructed"], meta["deferred_sessions"])
        assert summary["trading_days"] == meta["trading_days"]
        assert np.isclose(summary["trading_days_per_year"], meta["trading_days_per_year"], rtol=0, atol=1e-12)
        assert np.isclose(summary["average_gross"], meta["mean_exposure"], rtol=0, atol=1e-12)
        summary["numeric_target_pass"] = bool(summary["cagr"] >= .30 and summary["maxdd_sampled"] >= -.25 and summary["calmar"] >= 1)
        summary["current_cagr_target_pass"] = bool(summary["cagr"] >= .30)
        summary["operational_pass"] = bool(summary["trading_days_per_year"] <= 24)
        summary["full_target_pass"] = summary["numeric_target_pass"] and summary["operational_pass"]
        assert summary["numeric_target_pass"] == meta["numeric_target_pass"]
        assert summary["operational_pass"] == meta["operational_pass"]
        identity = dict(path_id=path_id, arm=arm, scenario=scenario)
        reconstruction.append(dict(identity, **summary))
        attribution.extend(dict(identity, **row) for row in pnl)
        annual.extend(dict(identity, **row) for row in years)
        held_quality.append(dict(identity, **quality, excludes_final_close_only=True))
        if len(orders):
            kk, jj = orders.execution_idx.to_numpy(int), orders.j.to_numpy(int)
            volumes = turnover[kk, jj]
            ratios = np.divide(orders.notional.to_numpy(float), volumes, out=np.full(len(orders), np.nan), where=volumes > 0)
            for i, row in enumerate(orders.to_dict("records")):
                participation.append(dict(identity, date=row["date"], ticker=row["ticker"], side=row["side"],
                                          notional=row["notional"], raw_traded_eur=float(volumes[i]),
                                          traded_value_participation=float(ratios[i])))
        print(f"PASS {seq}/{len(expected)} {path_id}: {summary['orders']} sized orders, {summary['instructions_independently_derived']} signals", flush=True)
    recon = pd.DataFrame(reconstruction)
    recon.to_csv(output / "INDEPENDENT_RECONSTRUCTIONS.csv", index=False)
    pd.DataFrame(attribution).to_csv(output / "HOLDINGS_PNL_ATTRIBUTION.csv", index=False)
    pd.DataFrame(annual).to_csv(output / "INDEPENDENT_ANNUAL_RETURNS.csv", index=False)
    pd.DataFrame(participation).to_csv(output / "TRADE_PARTICIPATION.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    pd.DataFrame(held_quality).to_csv(output / "HELD_PRICE_AGE.csv", index=False)
    annual_actual = pd.read_csv(results / "ANNUAL_RETURNS.csv", float_precision="round_trip")
    annual_reference = pd.DataFrame(annual)
    joined = annual_reference.merge(annual_actual, on=["path_id", "arm", "scenario", "year"], suffixes=("_reference", "_reported"), validate="one_to_one")
    assert len(joined) == len(annual_actual) == len(annual_reference)
    assert np.allclose(joined.annual_return_reference, joined.annual_return_reported, rtol=0, atol=1e-10)
    qa = dict(status=f"PASS_{count}_INDEPENDENT_ACCOUNT_AND_SIGNAL_RECONSTRUCTIONS", started_utc=started,
              finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), paths=len(recon),
              protocol_sha256=freeze["protocol_sha256"], adaptive_stage=stage2 or stage3, complete_grid=True, frozen_code_and_inputs_unchanged=True,
              independently_rebuilt_snapshots=len(snapshots), independently_rebuilt_groups=len(groups),
              independently_derived_raw_targets=len(targets), independently_derived_instructions=int(recon.instructions_independently_derived.sum()),
              independently_derived_reduction_signals=int(recon.reduction_signals_independently_derived.sum()),
              order_timestamps_checked=int(recon.order_timestamps_checked.sum()),
              order_quantities_checked=int(recon.order_quantities_independently_checked.sum()),
              numerical_residue_only_deferred_sessions=int(recon.numerical_residue_only_deferred_sessions.sum()),
              financial_csv_float_parser="round_trip",
              max_nav_cash_error=float(recon.max_nav_cash_error.max()),
              max_per_order_cost_error=float(recon.max_per_order_cost_error.max()),
              max_daily_pnl_attribution_error=float(recon.max_daily_pnl_attribution_error.max()),
              available_prior_baselines_reproduced=sum(row["status"].startswith("PASS") for row in baseline),
              unavailable_prior_baselines=sum(row["status"] == "PREVIOUS_PATH_NOT_AVAILABLE" for row in baseline),
              source_liquidity_instruments_checked=len(source_checks), source_liquidity_rows_checked=sum(row["sessions_checked"] for row in source_checks),
              numeric_target_passes=int(recon.numeric_target_pass.sum()), full_target_passes=int(recon.full_target_pass.sum()),
              current_cagr_target_passes=int(recon.current_cagr_target_pass.sum()),
              current_cagr_base_passes=int((recon.current_cagr_target_pass & recon.scenario.eq("BASE")).sum()),
              accounting_imports_production_code=False, selector_reference_imports_production_code=False,
              limitations=["Current catalogue survivorship and historical product status are not certified.",
                           "The vendor opening mask uses positive completed-day volume retrospectively.",
                           "Adjusted-price factor vintage is not certified point-in-time.",
                           "Cash interest is zero; taxes are excluded; units are fractional economic units.",
                           "Open/close sampled drawdown does not measure every intraday low.",
                           "A common SciPy complete-link library is used with independently derived Pearson matrices.",
                           "Trade participation is descriptive and does not certify broker liquidity or realized slippage."])
    (output / "INDEPENDENT_QA.json").write_text(json.dumps(qa, indent=2) + "\n")
    print(json.dumps(qa, indent=2), flush=True)
    return qa


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--previous", default=str(Path(__file__).resolve().parents[2] / "olc108"))
    parser.add_argument("--results-directory", default="results")
    parser.add_argument("--output-directory", default="validation")
    args = parser.parse_args()
    with threadpool_limits(limits=1):
        run(args.root, args.previous, args.results_directory, args.output_directory)
