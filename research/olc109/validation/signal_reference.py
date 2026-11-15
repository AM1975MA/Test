"""Independent OLC109 feature, clustering and signal reconstruction.

Only standard numerical libraries are imported. There are no production
strategy, feature, engine or core imports in this file.
"""
from __future__ import annotations
import gzip
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform

ARMS = ("PASSIVE", "LEADERS", "DUAL21", "LIQ_LEADERS", "LIQ_DUAL21",
        "CLUSTER_LEADERS", "CLUSTER_DUAL21", "CLUSTER_TREND", "CLUSTER_SLOW",
        "CLUSTER_SLOW_RVOL", "CLUSTER_SLOW_DUAL21", "CLUSTER_DUAL_RESID",
        "CLUSTER_DUAL_REVERT", "CLUSTER_LEADERS4", "CLUSTER_DUAL4",
        "CLUSTER_DUAL_CASH", "CLUSTER_DUAL_RISK15", "CLUSTER_DUAL_RISK20",
        "CLUSTER_DUAL_EXIT63", "CLUSTER_SLOW_EXIT63", "CLUSTER_DUAL_PEERS2",
        "CLUSTER_DUAL_TRAIL15")

STAGE2_ARMS = ("DEDUP_LEADERS", "DEDUP_DUAL21", "DEDUP_DUAL_PEERS2", "DEDUP_DUAL_TREND_OPP",
               "DEDUP_DUAL_RISK15", "DEDUP_DUAL_RISK20", "DEDUP_DUAL_EXIT63", "DEDUP_DUAL_TRAIL15",
               "CLUSTER_PEERS2_RISK15", "CLUSTER_PEERS2_RISK20")

STAGE3_ARMS = ("HORIZON63", "HORIZON126", "HORIZON252", "CAPITAL_3H", "CAPITAL_3H_TILT",
               "HORIZON63_TOP1", "HORIZON126_TOP1", "HORIZON252_TOP1")


def independent_features(panel, prepared, turnover):
    c = pd.DataFrame(prepared["C"])
    observations = np.asarray(panel["observed"], bool)
    dates = pd.DatetimeIndex(panel["dates"])
    ret = np.asarray(prepared["returns"])
    features = {"C": c.to_numpy(), "returns": ret}
    for window in (21, 63, 126, 252):
        features[f"m{window}"] = np.log(c / c.shift(window)).to_numpy()
    for window in (63, 200):
        features[f"sma{window}"] = c.rolling(window, min_periods=window).mean().to_numpy()
    features["peak63"] = c.rolling(63, min_periods=63).max().to_numpy()
    features["vol"] = np.maximum(pd.DataFrame(ret).rolling(63, min_periods=50).std(ddof=1).to_numpy() * np.sqrt(252), .01)
    features["b21"] = features["m21"]
    features["a21"] = np.log(c.shift(21) / c.shift(126)).to_numpy() / 5
    features["accel21"] = features["b21"] - features["a21"]
    features["slow"] = .5 * (252 / 105 * (features["m126"] - features["m21"]) +
                              252 / 231 * (features["m252"] - features["m21"]))
    latest = np.maximum.accumulate(np.where(observations, np.arange(len(c))[:, None], -1), axis=0)
    calendar_days = dates.to_numpy().astype("datetime64[D]").astype(np.int64)
    ages = calendar_days[:, None] - calendar_days[np.maximum(latest, 0)]
    recent = pd.DataFrame(observations.astype(int)).rolling(253, min_periods=253).sum().to_numpy()
    score = (4 * features["m63"] + 2 * features["m126"] + features["m252"]) / (3 * features["vol"])
    features["eligible"] = ((recent >= 241) & (observations.cumsum(axis=0) >= 253)
                            & (ages <= 5) & np.isfinite(score))
    assert np.asarray(turnover).shape == c.shape
    assert np.isfinite(turnover).all() and np.min(turnover) >= 0
    masked_turnover = np.where(observations, turnover, 0.)
    features["adv63"] = pd.DataFrame(masked_turnover).rolling(63, min_periods=63).median().to_numpy()
    features["liquid"] = features["eligible"] & observations & (features["adv63"] >= 100000)
    features["age"] = ages
    return features


def schedules(dates):
    dates = pd.DatetimeIndex(dates)
    month = np.zeros(len(dates), bool)
    week = np.zeros(len(dates), bool)
    for k in range(len(dates) - 1):
        month[k] = (dates[k].year, dates[k].month) != (dates[k + 1].year, dates[k + 1].month)
        week[k] = dates[k].isocalendar()[:2] != dates[k + 1].isocalendar()[:2]
    begin = int(dates.searchsorted("2020-03-02"))
    finish = int(dates.searchsorted("2026-10-30", side="right"))
    keys = [begin - 1] + [k for k in range(begin, finish - 1) if month[k]]
    return month, week, keys


def percentiles(values):
    values = np.asarray(values, float)
    return np.array([(np.sum(values < v) + (np.sum(values == v) + 1) / 2) / len(values)
                     for v in values])


def reconstruct_snapshot(names, f, k):
    ids = np.flatnonzero(f["liquid"][k])
    if not len(ids):
        return {"k": k, "groups": [], "rep_corr": np.zeros((0, 0)), "eligible_count": 0}, []
    block = f["returns"][k - 125:k + 1, ids]
    assert block.shape[0] == 126 and np.isfinite(block).all()
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.corrcoef(block, rowvar=False) if len(ids) > 1 else np.ones((1, 1))
    corr = np.nan_to_num(corr, nan=0.)
    corr = np.clip((corr + corr.T) / 2, -1., 1.)
    np.fill_diagonal(corr, 1.)
    if len(ids) > 1:
        distance = 1 - corr
        np.fill_diagonal(distance, 0.)
        # A separately computed Pearson matrix feeds the standard complete-link
        # primitive; membership and economic conditions are checked below.
        labels = fcluster(linkage(squareform(distance), method="complete"), t=.15, criterion="distance")
    else:
        labels = np.ones(1, int)
    groups, details = [], []
    for label in sorted(set(labels)):
        local = np.flatnonzero(labels == label)
        members = ids[local]
        member_names = [str(names[j]) for j in members]
        rep = min(members, key=lambda j: (-f["adv63"][k, j], str(names[j])))
        stats = {key: float(np.median(f[feature][k, members])) for key, feature in
                 (("annual", "m252"), ("m63", "m63"), ("slow", "slow"), ("b21", "b21"),
                  ("a21", "a21"), ("accel21", "accel21"), ("vol63", "vol"))}
        above63 = bool(f["C"][k, rep] > f["sma63"][k, rep])
        above200 = bool(f["C"][k, rep] > f["sma200"][k, rep])
        g = dict(gid=min(member_names), members=members.tolist(), representative=int(rep),
                 size=len(members), **stats, above63=above63, above200=above200,
                 median_turnover=float(f["adv63"][k, rep]))
        g["trend"] = bool(stats["annual"] > 0 and stats["m63"] > 0 and above200)
        g["slow_rvol"] = g["slow"] / max(g["vol63"], .05)
        within = corr[np.ix_(local, local)]
        minimum = float(within.min())
        assert minimum >= .85 - 1e-11, ("COMPLETE_LINK_MEMBER_CORRELATION", k, g["gid"], minimum)
        assert f["adv63"][k, rep] == max(f["adv63"][k, members])
        assert np.array_equal(np.median(f["turnover"][k - 62:k + 1, members], axis=0), f["adv63"][k, members])
        groups.append(g)
        details.append(dict(k=k, gid=g["gid"], representative=str(names[rep]), size=len(members),
                            median_turnover=g["median_turnover"], minimum_member_correlation=minimum,
                            observations126=126, current_observed=True))
    groups.sort(key=lambda g: g["gid"])
    location = {int(j): i for i, j in enumerate(ids)}
    reps = [location[g["representative"]] for g in groups]
    return dict(k=int(k), groups=groups, rep_corr=corr[np.ix_(reps, reps)], eligible_count=len(ids)), details


def verify_snapshots(root, names, f, keys, prefix=""):
    root = Path(root)
    with gzip.open(root / f"data/{prefix}SNAPSHOTS.json.gz", "rt") as h:
        recorded = {int(s["k"]): s for s in json.load(h)}
    assert set(recorded) == set(keys), "SNAPSHOT_SCHEDULE"
    rebuilt, group_details = {}, []
    with np.load(root / f"data/{prefix}REP_CORRELATIONS.npz", allow_pickle=False) as correlations:
        for k in keys:
            s, details = reconstruct_snapshot(names, f, k)
            actual = recorded[k]
            assert s["eligible_count"] == actual["eligible_count"], ("LIQUID_ELIGIBLE_COUNT", k)
            assert len(s["groups"]) == len(actual["groups"]), ("GROUP_COUNT", k)
            for a, b in zip(s["groups"], actual["groups"]):
                assert a.keys() == b.keys()
                for field in a:
                    if isinstance(a[field], float):
                        assert np.isclose(a[field], b[field], rtol=1e-10, atol=1e-11), ("GROUP_FEATURE", k, a["gid"], field)
                    else:
                        assert a[field] == b[field], ("GROUP_IDENTITY", k, a["gid"], field)
            assert np.allclose(s["rep_corr"], correlations[f"k_{k}"], rtol=0, atol=1e-11), ("REPRESENTATIVE_CORRELATIONS", k)
            rebuilt[k] = s
            group_details.extend(details)
    return rebuilt, group_details


def target_from_data(panel, f, snapshot, arm, k):
    names = np.asarray(panel["names"])
    weights = np.zeros(len(names))
    if arm == "PASSIVE":
        weights[int(panel["benchmark"])] = 1
        return weights, dict(selected_indices=[int(panel["benchmark"])], opportunity_used=False)
    if arm in ("LEADERS", "DUAL21", "LIQ_LEADERS", "LIQ_DUAL21"):
        pool = np.flatnonzero(f["liquid" if arm.startswith("LIQ_") else "eligible"][k])
        leaders = sorted(pool, key=lambda j: (-f["m252"][k, j], str(names[j])))[:2]
        chosen, used = list(leaders), False
        if arm.endswith("DUAL21") and len(leaders) == 2:
            rb, ra = percentiles(f["b21"][k, pool]), percentiles(f["a21"][k, pool])
            emerging = [j for i, j in enumerate(pool) if j not in leaders and f["b21"][k, j] > 0
                        and rb[i] >= 2 / 3 and ra[i] < 2 / 3 and f["accel21"][k, j] > 0
                        and f["C"][k, j] > f["sma63"][k, j]]
            emerging.sort(key=lambda j: (-f["accel21"][k, j], str(names[j])))
            if emerging and f["b21"][k, emerging[0]] > f["b21"][k, leaders[-1]]:
                chosen[-1], used = emerging[0], True
        if chosen:
            weights[chosen] = 1 / len(chosen)
        return weights, dict(selected_indices=list(map(int, chosen)), opportunity_used=used)
    groups, corr = snapshot["groups"], snapshot["rep_corr"]
    slots = 4 if arm in ("CLUSTER_LEADERS4", "CLUSTER_DUAL4") else 2
    pool = [i for i, g in enumerate(groups) if (arm != "CLUSTER_DUAL_PEERS2" or g["size"] >= 2)
            and (("SLOW" not in arm and arm != "CLUSTER_TREND") or g["trend"])]
    score = "slow_rvol" if arm == "CLUSTER_SLOW_RVOL" else "slow" if "SLOW" in arm else "annual"
    ranked = sorted(pool, key=lambda i: (-groups[i][score], groups[i]["gid"]))
    leaders = []
    for i in ranked:
        if all(corr[i, j] <= .85 + 1e-12 for j in leaders):
            leaders.append(i)
        if len(leaders) == slots:
            break
    chosen, used, challenger = list(leaders), False, None
    if "DUAL" in arm and pool and len(leaders) == slots:
        rb = percentiles([groups[i]["b21"] for i in pool])
        ra = percentiles([groups[i]["a21"] for i in pool])
        candidates = [i for pos, i in enumerate(pool) if i not in leaders and groups[i]["b21"] > 0
                      and rb[pos] >= 2 / 3 and ra[pos] < 2 / 3 and groups[i]["accel21"] > 0
                      and groups[i]["above63"]]
        candidates.sort(key=lambda i: (-groups[i]["accel21"], groups[i]["gid"]))
        for candidate in candidates:
            if all(corr[candidate, j] <= .85 + 1e-12 for j in leaders[:-1]):
                challenger = candidate
                if groups[candidate]["b21"] > groups[leaders[-1]]["b21"]:
                    chosen[-1], used = candidate, True
                break
    ids = [groups[i]["representative"] for i in chosen]
    weights[ids] = 1 / slots
    if arm == "CLUSTER_DUAL_RESID" and len(ids) == 2:
        b = int(panel["benchmark"])
        residual_vol = []
        for j in ids:
            samples = f["returns"][k - 125:k + 1, [b, j]]
            samples = samples[np.isfinite(samples).all(axis=1)]
            if len(samples) < 100:
                value = f["vol"][k, j]
            else:
                design = np.column_stack([np.ones(len(samples)), samples[:, 0]])
                coefficients = np.linalg.lstsq(design, samples[:, 1], rcond=None)[0]
                residual = samples[:, 1] - design @ coefficients
                value = np.std(residual, ddof=1) * np.sqrt(252)
            residual_vol.append(max(value, .05))
        inverse = 1 / np.array(residual_vol)
        first = min(.75, max(.25, inverse[0] / inverse.sum()))
        weights[ids] = first, 1 - first
    if arm == "CLUSTER_DUAL_REVERT" and len(ids) == 2:
        first, second = f["m21"][k, ids]
        weights[ids] = (.65, .35) if first < second else (.35, .65) if first > second else (.5, .5)
    if arm == "CLUSTER_DUAL_CASH":
        weights[(f["C"][k] <= f["sma200"][k]) | (f["m63"][k] <= 0)] = 0
    if arm.endswith("EXIT63") or arm.endswith("TRAIL15"):
        weights[exit_mask(f, k, arm)] = 0
    for pos, i in enumerate(chosen):
        assert all(corr[i, j] <= .85 + 1e-12 for j in chosen[:pos])
    return weights, dict(selected_indices=ids, opportunity_used=used,
                         selected_group_ids=[groups[i]["gid"] for i in chosen],
                         leader_group_ids=[groups[i]["gid"] for i in leaders],
                         challenger_group_id=groups[challenger]["gid"] if challenger is not None else None)


def exit_mask(f, k, arm):
    if arm.endswith("EXIT63"):
        return (f["C"][k] < f["sma63"][k]) & (f["m21"][k] < 0)
    assert arm.endswith("TRAIL15")
    return f["C"][k] / f["peak63"][k] - 1 <= -.15


def stage2_target_from_data(panel, f, snapshot, arm, k):
    """Reconstruct the declared adaptive stage without importing its policy."""
    if arm.startswith("CLUSTER_PEERS2_"):
        return target_from_data(panel, f, snapshot, "CLUSTER_DUAL_PEERS2", k)
    names = np.asarray(panel["names"])
    mask = f["liquid"][k].copy()
    if arm == "DEDUP_DUAL_PEERS2":
        allowed = {int(j) for g in snapshot["groups"] if g["size"] >= 2 for j in g["members"]}
        mask &= np.array([j in allowed for j in range(len(names))])
    ids = np.flatnonzero(mask)
    def compatible(a, b):
        block = f["returns"][k - 125:k + 1, [a, b]]
        assert block.shape == (126, 2) and np.isfinite(block).all()
        norm = np.linalg.norm(block - np.mean(block, axis=0), axis=0)
        correlation = 0. if norm.prod() <= 1e-14 else float(np.corrcoef(block, rowvar=False)[0, 1])
        return correlation <= .85 + 1e-12
    order = sorted(ids, key=lambda j: (-f["m252"][k, j], str(names[j])))
    leaders = []
    for j in order:
        if not leaders or compatible(leaders[0], j):
            leaders.append(int(j))
        if len(leaders) == 2:
            break
    selected, used, challenger = list(leaders), False, None
    if arm != "DEDUP_LEADERS" and len(ids):
        recent, previous = percentiles(f["b21"][k, ids]), percentiles(f["a21"][k, ids])
        opportunities = []
        for i, j in enumerate(ids):
            if j in leaders or f["b21"][k, j] <= 0 or recent[i] < 2 / 3 or previous[i] >= 2 / 3:
                continue
            if f["accel21"][k, j] <= 0 or f["C"][k, j] <= f["sma63"][k, j]:
                continue
            if arm == "DEDUP_DUAL_TREND_OPP" and (f["m252"][k, j] <= 0 or f["m63"][k, j] <= 0
                                                    or f["C"][k, j] <= f["sma200"][k, j]):
                continue
            opportunities.append(int(j))
        opportunities.sort(key=lambda j: (-f["accel21"][k, j], str(names[j])))
        if len(leaders) == 2:
            for j in opportunities:
                if compatible(leaders[0], j):
                    challenger = j
                    if f["b21"][k, j] > f["b21"][k, leaders[1]]:
                        selected[-1], used = j, True
                    break
    weights = np.zeros(len(names))
    weights[selected] = .5
    if arm.endswith("EXIT63") or arm.endswith("TRAIL15"):
        weights[exit_mask(f, k, arm)] = 0
    assert len(selected) <= 2 and (len(selected) < 2 or compatible(*selected))
    return weights, dict(selected_indices=selected, opportunity_used=used, leader_indices=leaders,
                         challenger=challenger, eligible_count=int(len(ids)))


def stage3_target_from_data(panel, f, snapshot, arm, k):
    """Independent horizon selection and convex capital combination."""
    names = np.asarray(panel["names"])
    eligible = np.flatnonzero(f["liquid"][k] & (f["m252"][k] > 0) & (f["m63"][k] > 0)
                             & (f["C"][k] > f["sma200"][k]))
    group_for = {j: g["gid"] for g in snapshot["groups"] for j in g["members"]}
    corr_cache = {}
    def correlation(a, b):
        pair = tuple(sorted((int(a), int(b))))
        if pair not in corr_cache:
            samples = f["returns"][k - 125:k + 1, list(pair)]
            assert samples.shape == (126, 2) and np.isfinite(samples).all()
            centered = samples - samples.mean(axis=0)
            denominator = np.linalg.norm(centered[:, 0]) * np.linalg.norm(centered[:, 1])
            corr_cache[pair] = 0. if denominator <= 1e-14 else float(np.corrcoef(samples, rowvar=False)[0, 1])
        return corr_cache[pair]
    def basket(horizon, count):
        order = sorted(eligible, key=lambda j: (-f[f"m{horizon}"][k, j], str(names[j])))
        picked = []
        for candidate in order:
            if any(group_for[candidate] == group_for[old] or correlation(candidate, old) > .85 + 1e-12 for old in picked):
                continue
            picked.append(int(candidate))
            if len(picked) == count:
                break
        weights = np.zeros(len(names))
        weights[picked] = 1 / count
        details = dict(horizon=horizon, slots=count, selected_indices=picked,
                       selected_group_ids=[group_for[j] for j in picked], eligible_count=len(eligible))
        return weights, details
    if arm.startswith("HORIZON"):
        horizon = int(arm.split("_")[0][len("HORIZON"):])
        target, details = basket(horizon, 1 if arm.endswith("_TOP1") else 3)
        return target, dict(details, opportunity_used=False)
    parts = [basket(h, 3) for h in (63, 126, 252)]
    recent = [float(np.mean(f["b21"][k, info["selected_indices"]])) if info["selected_indices"] else 0.
              for _, info in parts]
    prior = [float(np.mean(f["a21"][k, info["selected_indices"]])) if info["selected_indices"] else 0.
             for _, info in parts]
    acceleration = np.array(recent) - np.array(prior)
    capital = np.full(3, 1 / 3)
    tilted = False
    if arm == "CAPITAL_3H_TILT" and all(len(info["selected_indices"]) == 3 for _, info in parts):
        candidates = np.flatnonzero((np.array(recent) > 0) & (acceleration > 0))
        if len(candidates):
            winners = candidates[acceleration[candidates] == np.max(acceleration[candidates])]
            capital[:] = .25
            capital[winners] += .25 / len(winners)
            tilted = True
    assert np.isclose(capital.sum(), 1) and np.all(capital >= .25)
    # Accumulate directly, independently of the production matrix product.
    target = sum(float(capital[i]) * parts[i][0] for i in range(3))
    equal = sum(weights for weights, _ in parts) / 3
    assert np.isclose(target.sum(), equal.sum(), rtol=0, atol=1e-12), "TILT_GROSS_CHANGED"
    selected = np.flatnonzero(target > 0).tolist()
    assert selected == np.flatnonzero(equal > 0).tolist(), "TILT_UNION_CHANGED"
    group_weight = {}
    for j in selected:
        group_weight[group_for[j]] = group_weight.get(group_for[j], 0.) + target[j]
    assert max(group_weight.values(), default=0.) <= 1 / 3 + 1e-12, "COMPOSITE_GROUP_CAP"
    for pos, j in enumerate(selected):
        for old in selected[:pos]:
            if correlation(j, old) > .85 + 1e-12:
                assert target[j] + target[old] <= 1 / 3 + 1e-12, "COMPOSITE_CORRELATED_PAIR_CAP"
    return target, dict(selected_indices=selected, opportunity_used=tilted, sleeve_weights=capital.tolist(),
                         sleeves=[info for _, info in parts], eligible_count=len(eligible))


def portfolio_sigma(f, k, weights):
    ids = np.flatnonzero(weights > 0)
    if not len(ids):
        return 0.
    sample = f["returns"][k - 62:k + 1, ids]
    sample = sample[np.isfinite(sample).all(axis=1)]
    if len(sample) < 50:
        covariance = np.diag(np.maximum(f["vol"][k, ids], .01) ** 2)
    else:
        covariance = np.atleast_2d(np.cov(sample, rowvar=False, ddof=1)) * 252
    return float(np.sqrt(max(0., weights[ids] @ covariance @ weights[ids])))


class InstructionVerifier:
    def __init__(self, arm, f, monthly, weekly, targets, decisions, arrays, instructions):
        self.arm, self.f, self.monthly, self.weekly, self.targets = arm, f, monthly, weekly, targets
        self.decisions = {int(r["signal_idx"]): r for r in decisions.to_dict("records")}
        self.arrays = arrays
        self.rows = {int(k): i for i, k in enumerate(arrays["k"])}
        assert set(self.rows) == set(self.decisions), "DECISION_ARRAY_SCHEDULE"
        self.instructions = {int(r["signal_idx"]): r for r in instructions.to_dict("records")}
        assert len(self.instructions) == len(instructions), "DUPLICATE_SIGNAL_CLOSE"
        self.begin_signal = int(arrays["k"][0])
        self.risk = .15 if arm.endswith("RISK15") else .20 if arm.endswith("RISK20") else None
        self.guarded = arm.endswith("EXIT63") or arm.endswith("TRAIL15")
        self.checked = self.monthly_checked = self.reductions_checked = 0
        self.seen = set()

    def __call__(self, k, units, cash):
        wealth = float(cash + np.nansum(units * self.f["C"][k]))
        current = np.nan_to_num(units * self.f["C"][k], nan=0.) / wealth
        scheduled = k == self.begin_signal or (self.arm != "PASSIVE" and self.monthly[k])
        reason, raw, target = None, None, None
        if scheduled:
            reason = "INITIAL" if k == self.begin_signal else "SCHEDULED"
            raw, expected_meta = self.targets[(self.arm, k)]
            target = raw.copy()
            if self.risk is not None:
                target *= min(1., self.risk / max(portfolio_sigma(self.f, k, raw), 1e-12))
            assert k in self.decisions and k in self.rows, ("MISSING_SCHEDULED_DECISION", self.arm, k)
            pos = self.rows[k]
            for key, expected in (("units", units), ("current_weights", current), ("raw_weights", raw), ("weights", target)):
                assert np.allclose(self.arrays[key][pos], expected, rtol=1e-10, atol=1e-9), ("DECISION_STATE_OR_TARGET", self.arm, k, key)
            assert np.isclose(self.arrays["cash"][pos], cash, rtol=1e-10, atol=1e-7), ("DECISION_CASH", self.arm, k)
            actual_meta = json.loads(self.decisions[k]["meta_json"])
            for field, expected in expected_meta.items():
                assert actual_meta[field] == expected, ("SELECTION_METADATA", self.arm, k, field, expected, actual_meta[field])
            self.monthly_checked += 1
        else:
            assert k not in self.decisions, ("UNSCHEDULED_DECISION", self.arm, k)
            if self.guarded and self.weekly[k]:
                triggered = (current > 1e-10) & exit_mask(self.f, k, self.arm)
                if triggered.any():
                    raw, target = current.copy(), current.copy()
                    target[triggered] = 0
                    reason = "TREND_REDUCE"
            if reason is None and self.risk is not None and current.sum() > 0:
                sigma = portfolio_sigma(self.f, k, current)
                if sigma > 1.25 * self.risk:
                    raw = current.copy()
                    target = raw * self.risk / sigma
                    reason = "VOL_REDUCE"
        if reason is None:
            assert k not in self.instructions, ("UNEXPECTED_INSTRUCTION", self.arm, k)
        else:
            assert k in self.instructions, ("MISSING_INSTRUCTION", self.arm, k, reason)
            row = self.instructions[k]
            assert row["reason"] == reason, ("INSTRUCTION_REASON", self.arm, k, reason)
            for field, value in (("raw_weights", raw), ("target_weights", target)):
                assert np.allclose(np.array(json.loads(row[field])), value, rtol=1e-10, atol=1e-10), ("INSTRUCTION_TARGET_FROM_DATA", self.arm, k, field)
            if scheduled:
                assert row["instruction_id"] == self.decisions[k]["instruction_id"]
            else:
                self.reductions_checked += 1
            self.seen.add(k)
            self.checked += 1

    def finish(self):
        assert self.seen == set(self.instructions), "UNVISITED_INSTRUCTION"
        assert self.monthly_checked == len(self.decisions), "UNVISITED_DECISION"
        return dict(instructions_independently_derived=self.checked,
                    scheduled_decisions_independently_derived=self.monthly_checked,
                    reduction_signals_independently_derived=self.reductions_checked)
