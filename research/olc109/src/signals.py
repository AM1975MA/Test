"""OLC107 predeclared selectors. All scores use completed historical closes."""
from __future__ import annotations
import numpy as np
import pandas as pd

ARMS = ("PASSIVE", "LEADERS", "EMERGING_ONLY", "LEADER_FAST", "LEADER_EMERGING", "DUAL_SELECTIVE",
        "EMERGING_ONLY_21", "LEADER_FAST_21", "LEADER_EMERGING_21", "DUAL_SELECTIVE_21")

def compute_features(panel, legacy):
    f = legacy.features(panel)
    c = pd.DataFrame(f["C"])
    b = np.log(c / c.shift(63)).to_numpy()
    a = (np.log(c.shift(63) / c.shift(252)) / 3.).to_numpy()
    eligible = f["eligible"]
    f.update(b=b, a=a, acceleration=b-a,
             rank_b=pd.DataFrame(np.where(eligible, b, np.nan)).rank(axis=1, pct=True, method="average").to_numpy(),
             rank_a=pd.DataFrame(np.where(eligible, a, np.nan)).rank(axis=1, pct=True, method="average").to_numpy(),
             sma126=c.rolling(126, min_periods=126).mean().to_numpy())
    f["fast_eligible"] = eligible & (b > 0.) & (f["rank_b"] >= 2./3.) & (f["C"] > f["sma126"])
    f["emerging_eligible"] = f["fast_eligible"] & (f["rank_a"] < 2./3.) & (f["acceleration"] > 0.)
    b21 = f["m21"]
    a21 = (np.log(c.shift(21) / c.shift(126)) / 5.).to_numpy()
    f.update(b21=b21, a21=a21, acceleration21=b21-a21,
             rank_b21=pd.DataFrame(np.where(eligible, b21, np.nan)).rank(axis=1, pct=True, method="average").to_numpy(),
             rank_a21=pd.DataFrame(np.where(eligible, a21, np.nan)).rank(axis=1, pct=True, method="average").to_numpy(),
             sma63=c.rolling(63, min_periods=63).mean().to_numpy())
    f["fast_eligible21"] = eligible & (b21 > 0.) & (f["rank_b21"] >= 2./3.) & (f["C"] > f["sma63"])
    f["emerging_eligible21"] = f["fast_eligible21"] & (f["rank_a21"] < 2./3.) & (f["acceleration21"] > 0.)
    return f

def pick(panel, f, k, arm, current_weights=None):
    if arm not in ARMS:
        raise ValueError("UNKNOWN_ARM")
    names = np.asarray(panel["names"])
    weights = np.zeros(len(names))
    original_arm = arm
    horizon = 21 if arm.endswith("_21") else 63
    suffix = "21" if horizon == 21 else ""
    if horizon == 21:
        arm = arm[:-3]
    def ranked(mask, score):
        ids = np.flatnonzero(mask & np.isfinite(score))
        return sorted(ids.tolist(), key=lambda j: (-float(score[j]), str(names[j])))
    leaders = ranked(f["eligible"][k], f["m252"][k])[:2]
    excluded = np.ones(len(names), dtype=bool)
    excluded[leaders] = False
    b = f["b" + suffix]
    fast = ranked(f["fast_eligible" + suffix][k] & excluded, b[k])
    emerging = ranked(f["emerging_eligible" + suffix][k] & excluded, f["acceleration" + suffix][k])
    used = False
    selected = []
    if arm == "PASSIVE":
        selected = [int(panel["benchmark"])]
        weights[selected] = 1.
    elif arm == "LEADERS":
        selected = leaders
        if selected:
            weights[selected] = 1. / len(selected)
    elif arm == "EMERGING_ONLY":
        selected = emerging[:2]
        weights[selected] = .5
        used = bool(selected)
    elif leaders:
        # All paired arms retain the strongest annual leader. A qualified
        # challenger replaces the second slot; otherwise the second leader stays.
        selected = leaders.copy()
        challenger = None
        if len(leaders) == 2:
            if arm == "LEADER_FAST" and fast:
                challenger = fast[0]
            elif arm == "LEADER_EMERGING" and emerging:
                challenger = emerging[0]
                used = True
            elif arm == "DUAL_SELECTIVE" and emerging:
                e, old = emerging[0], leaders[1]
                if b[k, e] > b[k, old] and (horizon == 21 or f["m21"][k, e] > f["m21"][k, old]):
                    challenger = e
                    used = True
            if challenger is not None:
                selected[1] = challenger
        weights[selected] = 1. / len(selected)
    metadata = dict(arm=original_arm, horizon=horizon, eligible_count=int(f["eligible"][k].sum()),
                    leader_indices=leaders, fast_indices=fast, emerging_indices=emerging,
                    selected_indices=selected, selected_names=[str(names[j]) for j in selected],
                    opportunity_used=used, challenger_available=bool(emerging),
                    strongest_emerging=(int(emerging[0]) if emerging else None))
    return weights, metadata

def make_policy(panel, f, arm):
    return lambda k, current_weights: pick(panel, f, k, arm, current_weights)

def decision_mask(dates, cadence, passive=False):
    dates = pd.DatetimeIndex(dates)
    out = np.zeros(len(dates), dtype=bool)
    if passive:
        return out
    if cadence == "MONTHLY":
        keys = dates.year * 12 + dates.month
    elif cadence == "WEEKLY":
        iso = dates.isocalendar()
        keys = (iso.year * 100 + iso.week).to_numpy()
    else:
        raise ValueError("UNKNOWN_CADENCE")
    out[:-1] = np.asarray(keys[:-1]) != np.asarray(keys[1:])
    return out
