"""Test a cluster prior in the original U27 USA ranker and execution engine."""

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "u27"))
from run27 import leg_correlation, isolation_rules, previous
import verify24 as previous_verification

import numpy as np
import pandas as pd

SCENARIOS = ((15, 0), (30, 0), (15, 1), (30, 1))
RULES = {
    "U27": (0.00, "RESTORED", "RIDGE", "RANK"),
    "RIDGE05": (0.05, "RESTORED", "RIDGE", "RANK"),
    "RIDGE10": (0.10, "RESTORED", "RIDGE", "RANK"),
    "RIDGE20": (0.20, "RESTORED", "RIDGE", "RANK"),
    "MOM10": (0.10, "RESTORED", "MOM21", "RANK"),
    "RIDGE10_ORIGINAL": (0.10, "ORIGINAL", "RIDGE", "RANK"),
    "RAW10": (0.10, "RESTORED", "RIDGE", "RAW"),
    "RIDGE01": (0.01, "RESTORED", "RIDGE", "RANK"),
    "RIDGE02": (0.02, "RESTORED", "RIDGE", "RANK"),
}
EVALUATION = pd.Timestamp("2021-10-01")


def load_frozen_inputs(folder):
    scores = pd.read_csv(folder / "TICKER_SCORES.csv", parse_dates=["signal_date"],
                         float_precision="round_trip")
    members = pd.read_csv(folder / "GROUP_MEMBERS.csv", parse_dates=["signal_date"], dtype={"cluster_id": str})
    cluster = pd.read_csv(folder / "GROUP_PREDICTIONS.csv",
                          parse_dates=["day", "close_cutoff", "member_cutoff", "latest_label"],
                          dtype={"cluster": str}, float_precision="round_trip")
    assert not scores.duplicated(["signal_date", "ticker"]).any()
    assert not members.duplicated(["signal_date", "ticker"]).any()
    assert not cluster.duplicated(["day", "source", "cluster"]).any()
    return scores, members, cluster


def score_group(forecast, key):
    assert len(forecast) == 8 and np.isfinite(forecast[key]).all()
    return (forecast.set_index("cluster")[key].rank(method="average") - 1) / (len(forecast) - 1) - 0.5


def build_plans(q, inputs, until=None):
    scores, members, clusters = inputs
    dates = pd.DatetimeIndex(q["dates"])
    ticker = q["tickers"]
    indices = {t: i for i, t in enumerate(ticker)}
    events = np.flatnonzero(q["events"])
    pair = np.stack([q["d1"][0], q["d2"][0]], axis=1)
    plans = {name: pair.copy() for name in RULES}
    decisions, panel = [], []
    for start, stop in zip(events, np.r_[events[1:], len(dates)]):
        day = dates[start]
        if day < EVALUATION or start == len(dates) - 1:
            continue
        if until is not None and day > until:
            break
        prior = dates[start - 1]
        signal = scores[scores.signal_date.eq(prior)].sort_values(
            ["native_score", "ticker"], ascending=[False, True]
        ).copy()
        assert len(signal) >= 2 and set(signal.ticker) <= set(indices)
        original = signal.ticker.head(2).tolist()
        assert original == ticker[pair[start]].tolist(), (day, original, ticker[pair[start]])
        signal["base_rank"] = np.linspace(1.0, 0.0, len(signal))
        spread = float(signal.native_score.quantile(0.90) - signal.native_score.quantile(0.10))
        assert spread > 0
        signal["raw_scaled"] = (signal.native_score - float(signal.native_score.median())) / spread
        for name, (weight, version, key, scale) in RULES.items():
            f = clusters[clusters.day.eq(day) & clusters.source.eq(version)]
            assert (f.close_cutoff == prior).all() and (f.latest_label < day).all()
            member_date, = f.member_cutoff.unique()
            assert pd.Timestamp(member_date) <= prior
            m = members[members.signal_date.eq(member_date)].set_index("ticker").cluster_id
            frame = signal.copy()
            frame["cluster"] = frame.ticker.map(m)
            boosts = frame.cluster.map(score_group(f, key)).fillna(0.0)
            frame["cluster_rank"] = boosts
            frame["combined"] = frame["base_rank" if scale == "RANK" else "raw_scaled"] + weight * boosts
            sorted_frame = frame.sort_values(["combined", "native_score", "ticker"], ascending=[False, False, True])
            picked = sorted_frame.head(2)
            pick = picked.ticker.tolist()
            selected_ids = [indices[t] for t in pick]
            plans[name][start:stop] = selected_ids
            native_ids = pair[start]
            best_cluster = score_group(f, key).idxmax()
            # Outcomes belong only to the audit, after the decision is fixed.
            end = min(stop, len(dates) - 1)
            old_hold = np.mean(q["O"][end, native_ids] / q["O"][start, native_ids] - 1)
            new_hold = np.mean(q["O"][end, selected_ids] / q["O"][start, selected_ids] - 1)
            decisions.append(dict(
                date=day, signal_date=prior, membership_date=member_date, latest_fit_label=f.latest_label.iloc[0],
                mode=name, coefficient=weight, ticker_count=len(signal), no_cluster=int(frame.cluster.isna().sum()),
                original_a=original[0], original_b=original[1], selected_a=pick[0], selected_b=pick[1],
                cluster_a=picked.cluster.iloc[0], cluster_b=picked.cluster.iloc[1], best_cluster=best_cluster,
                outside_best=int((picked.cluster != best_cluster).sum()),
                changed_legs=len(set(original) - set(pick)), old_gross=float(old_hold),
                new_gross=float(new_hold), gross_delta=float(new_hold - old_hold),
            ))
            panel.append(frame.assign(date=day, mode=name, selected=frame.ticker.isin(pick)))
    return plans, pd.DataFrame(decisions), pd.concat(panel, ignore_index=True)


def replay(q, plans, output, published):
    baseline_pair = np.stack([q["d1"][0], q["d2"][0]], axis=1)
    assert np.array_equal(baseline_pair, plans["U27"])
    dates = pd.DatetimeIndex(q["dates"])
    begin = dates.get_loc(EVALUATION)
    summaries, monthly, annual, curves, checks = [], [], [], [], []
    base_nav = {}
    for name, pair in plans.items():
        alt = dict(q, d1=pair[:, 0][None, :], d2=pair[:, 1][None, :])
        signals = previous.signals(alt, "USA")
        corr = isolation_rules(alt, leg_correlation(alt))["CORR70"].astype(int)
        for bps, lag in SCENARIOS:
            directory = output / "accounts" / f"{name}_{bps}_L{lag}"
            directory.mkdir(exist_ok=True, parents=True)
            previous.OUT = previous_verification.OUT = directory
            risk_mode = np.r_[corr[0], corr[:-1]] if lag else corr
            state = dict(alt, risk_mode=risk_mode)
            summary, report, _ = previous.run(
                "USA", "PROFIT_RAMP", bps, lag, state, signals, save=True
            )
            info = SimpleNamespace(market="USA", rule="PROFIT_RAMP", bps=bps, lag=lag)
            qa = previous_verification.replay(info, state)
            nav = report["ledger"][:, 0]
            fields = dict(mode=name, bps=bps, lag=lag)
            if name == "U27":
                base_nav[bps, lag] = nav
                reference = published[(published.bps == bps) & (published.lag == lag)]
                if len(reference):
                    rr = reference.iloc[0]
                    np.testing.assert_allclose([summary["cagr"], summary["maxdd"]], [rr.cagr, rr.maxdd],
                                               rtol=0, atol=1e-12)
                    assert summary["orders"] == rr.orders
            else:
                np.testing.assert_array_equal(nav[:begin+1], base_nav[bps, lag][:begin+1])
            active = previous.metrics(dates[begin:], nav[begin:])
            summaries.append(dict(fields, active_cagr=active["cagr"], active_maxdd=active["maxdd"],
                                  full_cagr=summary["cagr"], full_maxdd=summary["maxdd"],
                                  orders=summary["orders"], stops=summary["stops"],
                                  cost_currency=summary["cost_currency"], terminal_capital=summary["final_capital"]))
            mo = previous.months(dates, nav)
            returns = mo[mo.index >= pd.Period(EVALUATION, "M")]
            assert len(returns) == 57
            monthly.extend(dict(fields, month=str(month), ret=value) for month, value in returns.items())
            yr = (1 + returns).groupby(returns.index.year).prod() - 1
            annual.extend(dict(fields, year=int(year), ret=value) for year, value in yr.items())
            curves.append(pd.DataFrame(dict(fields, date=dates, nav=nav)))
            checks.append(dict(fields, **qa))
    return (pd.DataFrame(summaries), pd.DataFrame(monthly), pd.DataFrame(annual),
            pd.concat(curves, ignore_index=True), checks)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--inputs", type=Path, default=HERE / "inputs")
    cli.add_argument("--results", type=Path, default=HERE / "results")
    cli.add_argument("--state", type=Path, default=HERE.parent / "u23" / "inputs" / "USA_STATE.npz")
    cli.add_argument("--reference", type=Path, default=HERE.parent / "u27" / "results" / "SUMMARY.csv")
    args = cli.parse_args()
    args.results.mkdir(exist_ok=True, parents=True)
    q = previous.load(args.state)
    inputs = load_frozen_inputs(args.inputs)
    plans, choices, scores = build_plans(q, inputs)
    assert choices.groupby("mode").size().eq(57).all()
    cut_dates = pd.DatetimeIndex(["2022-08-01", "2024-02-01", "2025-09-02"])
    for date in cut_dates:
        short = (inputs[0][inputs[0].signal_date < date], inputs[1], inputs[2][inputs[2].day <= date])
        truncated, _, _ = build_plans(q, short, until=date)
        end = pd.DatetimeIndex(q["dates"]).searchsorted(date, side="right")
        for label in RULES:
            np.testing.assert_array_equal(plans[label][:end], truncated[label][:end])
    published = pd.read_csv(args.reference).query("market == 'USA' and rule == 'CORR70'")
    assert len(published) == 3
    summary, monthly, annual, daily, audit = replay(q, plans, args.results, published)
    tables = dict(SUMMARY=summary, MONTHLY=monthly, ANNUAL=annual, DAILY=daily, CHOICES=choices,
                  CANDIDATE_SCORES=scores)
    for name, table in tables.items():
        suffix = ".csv.gz" if name.endswith("SCORES") or name == "DAILY" else ".csv"
        table.to_csv(args.results / f"{name}{suffix}", index=False)
    qa = dict(status="PASS", original_pairs_matched=57, tested_accounts=len(summary),
              original_ledger_metric_matches=len(published), past_only_checks=len(cut_dates),
              independent_order_replay=audit)
    (args.results / "QA.json").write_text(json.dumps(qa, indent=2) + "\n")
    print("CLUSTER_SOFT_QA_PASS", len(summary), len(choices), flush=True)


if __name__ == "__main__":
    main()
