"""Descriptive loss/rebound forensics of frozen OLC109 accounts.

No strategies are fitted, simulated or selected. Orders are replayed as immutable
facts. Ex-post episode boundaries and forward price changes are OUTPUT LABELS;
all reported features end at their explicit information_close_idx. This file
imports no OLC109 implementation and writes only to its own output directory.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2] / "olc109"
ARM = "DEDUP_DUAL_TREND_OPP"
SCENARIOS = ["BASE", "ZERO_COST", "DOUBLE_COST", "LAG1", "LAG2"]
INPUTS: set[Path] = set()


def read_csv(path):
    path = Path(path)
    INPUTS.add(path)
    return pd.read_csv(path, float_precision="round_trip")


def read_json(path):
    path = Path(path)
    INPUTS.add(path)
    return json.loads(path.read_text())


def save(name, rows):
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    frame.to_csv(HERE / name, index=False, float_format="%.17g")
    return frame


def load_inputs():
    path = ROOT / "source/data/XETRA_EUR_ETF.npz"
    INPUTS.add(path)
    with np.load(path, allow_pickle=False) as z:
        p = {key: z[key] for key in z.files}
    path = ROOT / "data/LIQUIDITY.npz"
    INPUTS.add(path)
    with np.load(path, allow_pickle=False) as z:
        assert np.array_equal(p["names"], z["names"])
        assert np.array_equal(p["dates"], z["dates"])
        p["turnover"] = z["turnover"]
    p["dates"] = pd.DatetimeIndex(p["dates"])
    p["valid_c"] = p["observed"] & np.isfinite(p["C"]) & (p["C"] > 0)
    p["valid_o"] = p["open_observed"] & np.isfinite(p["O"]) & (p["O"] > 0)
    p["C"] = pd.DataFrame(np.where(p["valid_c"], p["C"], np.nan)).ffill().to_numpy()
    cov = read_csv(ROOT / "data/UNIVERSE_COVERAGE.csv").set_index("isin")
    p["names_long"] = {
        str(n): str(cov.loc[n, "provider_name"]) if n in cov.index else str(n)
        for n in p["names"]
    }
    return p


def date(p, k):
    return str(p["dates"][int(k)].date()) if k is not None else None


def features(p):
    c = pd.DataFrame(p["C"])
    lr = np.log(c / c.shift())
    f = {f"m{h}": (c / c.shift(h) - 1).to_numpy() for h in (5, 21, 63, 126, 252)}
    f.update({f"above_sma{h}": (c / c.rolling(h, min_periods=h).mean() - 1).to_numpy()
              for h in (20, 63, 200)})
    f["vol21"] = (lr.rolling(21, min_periods=21).std(ddof=1) * np.sqrt(252)).to_numpy()
    f["vol63"] = (lr.rolling(63, min_periods=50).std(ddof=1) * np.sqrt(252)).to_numpy()
    f["vol21_over_vol63"] = np.divide(f["vol21"], f["vol63"],
        out=np.full_like(f["vol21"], np.nan), where=f["vol63"] > 0)
    f["dd63"] = (c / c.rolling(63, min_periods=63).max() - 1).to_numpy()
    f["r1"] = (c / c.shift() - 1).to_numpy()
    obs = p["observed"]
    count = pd.DataFrame(obs).rolling(253, min_periods=253).sum().to_numpy()
    last = np.maximum.accumulate(np.where(obs, np.arange(len(c))[:, None], -1), axis=0)
    ordinal = p["dates"].values.astype("datetime64[D]").astype(int)
    age = ordinal[:, None] - ordinal[np.maximum(last, 0)]
    adv = pd.DataFrame(np.where(obs, p["turnover"], 0.)).rolling(63, min_periods=63).median().to_numpy()
    eligible = ((count >= math.ceil(.95 * 253)) & (np.cumsum(obs, axis=0) >= 253)
        & (age <= 5) & np.isfinite(f["m252"]) & np.isfinite(f["m126"])
        & np.isfinite(f["m63"]) & np.isfinite(f["vol63"]) & obs & (adv >= 100000))
    f["liquid_eligible"] = eligible
    f["adv63"] = adv
    f["age_days"] = age
    breadth = []
    b = int(p["benchmark"])
    for k in range(len(c)):
        ids = np.flatnonzero(eligible[k])
        rec = dict(k=k, date=date(p, k), eligible_count=len(ids), benchmark=str(p["names"][b]))
        for key in ("r1", "m5", "m21", "above_sma20", "above_sma63"):
            values = f[key][k, ids]
            rec[f"eligible_fraction_negative_{key}"] = float(np.mean(values < 0)) if len(ids) else np.nan
            rec[f"eligible_median_{key}"] = float(np.median(values)) if len(ids) else np.nan
            rec[f"benchmark_{key}"] = float(f[key][k, b])
        breadth.append(rec)
    f["breadth"] = pd.DataFrame(breadth).set_index("k", drop=False)
    return f


FEATURE_KEYS = ["m5", "m21", "m63", "m126", "m252", "above_sma20", "above_sma63", "above_sma200",
                "vol21", "vol63", "vol21_over_vol63", "dd63", "adv63", "age_days"]


def feature_row(p, f, k, j):
    return {"information_close_idx": int(k), "information_close_date": date(p, k),
            "ticker": str(p["names"][j]), "name": p["names_long"][str(p["names"][j])],
            **{key: float(f[key][k, j]) for key in FEATURE_KEYS}}


def reconstruct(p, arm, scenario):
    folder = ROOT / "results_stage2" / f"{arm}__{scenario}"
    daily = read_csv(folder / "DAILY.csv.gz")
    orders = read_csv(folder / "ORDERS.csv.gz")
    metrics = read_json(folder / "METRICS.json")
    decisions = read_csv(folder / "DECISIONS.csv")
    instructions = read_csv(folder / "INSTRUCTIONS.csv.gz")
    ids = np.sort(orders.j.unique().astype(int))
    loc = {int(j): i for i, j in enumerate(ids)}
    unit = np.zeros(len(ids))
    cash = 10000.
    n = len(daily)
    qopen, qclose = np.zeros((n, len(ids))), np.zeros((n, len(ids)))
    gap, day, fees = np.zeros_like(qopen), np.zeros_like(qopen), np.zeros_like(qopen)
    no, nc = np.zeros(n), np.zeros(n)
    by_k = {int(k): frame for k, frame in orders.groupby("execution_idx", sort=False)}
    max_self = 0.
    for t, row in enumerate(daily.itertuples()):
        k = int(row.k)
        qopen[t] = unit
        opening = np.where(p["valid_o"][k, ids], p["O"][k, ids], p["C"][k - 1, ids])
        opening = np.nan_to_num(opening, nan=0.)
        previous = np.nan_to_num(p["C"][k - 1, ids], nan=0.)
        closing = np.nan_to_num(p["C"][k, ids], nan=0.)
        gap[t] = unit * (opening - previous)
        no[t] = cash + unit @ opening
        for order in by_k.get(k, pd.DataFrame()).itertuples():
            col = loc[int(order.j)]
            assert p["valid_o"][k, int(order.j)], "UNACCEPTED_OPEN"
            assert abs(order.price - p["O"][k, int(order.j)]) < 1e-10
            sign = 1 if order.side == "BUY" else -1
            unit[col] += sign * order.quantity
            cash -= sign * order.notional + order.cost
            fees[t, col] += order.cost
        unit = np.maximum(unit, 0.)
        cash = max(cash, 0.)
        qclose[t] = unit
        day[t] = unit * (closing - opening)
        nc[t] = cash + unit @ closing
        previous_nav = nc[t - 1] if t else 10000.
        max_self = max(max_self, abs(nc[t] - previous_nav - (gap[t] + day[t] - fees[t]).sum()))
    max_nav = max(np.max(np.abs(no - daily.nav_open)), np.max(np.abs(nc - daily.nav_close)))
    assert max_nav < 1e-7, (arm, scenario, max_nav)
    assert max_self < 1e-7
    event_gross = np.zeros((2 * n + 1, len(ids)))
    event_fees = np.zeros_like(event_gross)
    event_gross[1::2], event_gross[2::2] = gap, day
    event_fees[2::2] = fees
    event_nav = np.r_[10000., np.column_stack([no, nc]).ravel()]
    event_k = np.r_[daily.k.iloc[0] - 1, np.repeat(daily.k.to_numpy(), 2)]
    event_phase = np.concatenate([["Initial"], np.tile(["Open", "Close"], n)])
    sampled_dd = float((event_nav / np.maximum.accumulate(event_nav) - 1).min())
    assert abs(sampled_dd - metrics["maxdd_sampled"]) < 1e-11
    attr = read_csv(ROOT / "validation/stage2/HOLDINGS_PNL_ATTRIBUTION.csv")
    attr = attr[attr.path_id == f"{arm}__{scenario}"].set_index("ticker")
    max_attr = 0.
    for col, j in enumerate(ids):
        name = str(p["names"][j])
        max_attr = max(max_attr, abs((gap + day - fees)[:, col].sum() - attr.loc[name, "net_pnl"]))
    assert max_attr < 1e-7
    return dict(arm=arm, scenario=scenario, daily=daily, orders=orders, metrics=metrics,
        decisions=decisions, instructions=instructions, ids=ids, loc=loc, qopen=qopen, qclose=qclose,
        gap=gap, day=day, fees=fees, event_gross=event_gross, event_fees=event_fees,
        event_nav=event_nav, event_k=event_k, event_phase=event_phase,
        qa=dict(path_id=f"{arm}__{scenario}", max_nav_error=max_nav,
                max_daily_pnl_error=max_self, max_attribution_error=max_attr,
                sampled_dd=sampled_dd, orders=len(orders)))


def episodes(p, a, basis="sampled"):
    if basis == "sampled":
        x, ks, phases = a["event_nav"], a["event_k"], a["event_phase"]
    else:
        x = np.r_[10000., a["daily"].nav_close]
        ks = np.r_[a["daily"].k.iloc[0] - 1, a["daily"].k]
        phases = np.concatenate([["Initial"], np.repeat("Close", len(a["daily"]))])
    peak, trough, active = 0, 0, False
    rows = []

    def append(recovery):
        end = len(x) - 1 if recovery is None else recovery
        rows.append(dict(arm=a["arm"], scenario=a["scenario"], basis=basis,
            peak_event=peak, trough_event=trough, recovery_event=recovery,
            peak_idx=int(ks[peak]), trough_idx=int(ks[trough]), recovery_idx=int(ks[recovery]) if recovery is not None else None,
            peak_date=date(p, ks[peak]), peak_phase=phases[peak],
            trough_date=date(p, ks[trough]), trough_phase=phases[trough],
            recovery_date=date(p, ks[recovery]) if recovery is not None else None,
            recovery_phase=phases[recovery] if recovery is not None else None,
            peak_nav=float(x[peak]), trough_nav=float(x[trough]), drawdown=float(x[trough]/x[peak]-1),
            loss_eur=float(x[trough]-x[peak]),
            decline_elapsed_sessions=int(ks[trough]-ks[peak]),
            recovery_elapsed_sessions=int(ks[recovery]-ks[trough]) if recovery is not None else None,
            underwater_elapsed_sessions=int(ks[end]-ks[peak]),
            underwater_calendar_days=int((p["dates"][ks[end]]-p["dates"][ks[peak]]).days),
            recovered=recovery is not None))
    for i in range(1, len(x)):
        if x[i] >= x[peak]:
            if active:
                append(i)
            peak = trough = i
            active = False
        else:
            active = True
            if x[i] < x[trough]:
                trough = i
    if active:
        append(None)
    return pd.DataFrame(rows).sort_values("drawdown").reset_index(drop=True)


def next_valid_open(p, k, j, strict=True):
    start = k + 1 if strict else k
    ix = np.flatnonzero(p["valid_o"][start:, j])
    return int(start + ix[0]) if len(ix) else None


def event_features(p, f, a, eps):
    contributions, snapshots, recovery, warnings, phase_pnl, recovery_attr = [], [], [], [], [], []
    weekly_keys=p["dates"].isocalendar()
    weekly_keys=(weekly_keys.year*100+weekly_keys.week).to_numpy()
    monthly_keys=p["dates"].year*12+p["dates"].month
    weekly=np.r_[weekly_keys[:-1]!=weekly_keys[1:],False]
    monthly=np.r_[monthly_keys[:-1]!=monthly_keys[1:],False]
    for rank, ep in enumerate(eps.head(10).to_dict("records"), 1):
        first, last = int(ep["peak_event"]), int(ep["trough_event"])
        gross = a["event_gross"][first + 1:last + 1].sum(axis=0)
        fee = a["event_fees"][first + 1:last + 1].sum(axis=0)
        net = gross - fee
        assert abs(net.sum() - ep["loss_eur"]) < 1e-7
        event_ids=np.arange(first+1,last+1)
        is_open=a["event_phase"][event_ids]=="Open"
        phase_pnl.append(dict(episode_rank=rank,peak_date=ep["peak_date"],trough_date=ep["trough_date"],
            gap_pnl=float(a["event_gross"][event_ids[is_open]].sum()),
            intraday_gross_pnl=float(a["event_gross"][event_ids[~is_open]].sum()),
            fees=float(fee.sum()),net_pnl=float(net.sum()),peak_nav=ep["peak_nav"]))
        main = np.argsort(net)[:min(5, len(net))]
        if ep["recovered"]:
            rec_event=int(ep["recovery_event"])
            recgross=a["event_gross"][last+1:rec_event+1].sum(axis=0)
            recfees=a["event_fees"][last+1:rec_event+1].sum(axis=0)
            recnet=recgross-recfees
            row_at_trough=(last-1)//2
            trough_units=a["qopen"][row_at_trough] if ep["trough_phase"]=="Open" else a["qclose"][row_at_trough]
            assert abs(recnet.sum()-(a["event_nav"][rec_event]-ep["trough_nav"]))<1e-7
            for col in np.flatnonzero(np.abs(recnet)>1e-8):
                j=int(a["ids"][col])
                recovery_attr.append(dict(episode_rank=rank,trough_date=ep["trough_date"],recovery_date=ep["recovery_date"],
                    ticker=str(p["names"][j]),name=p["names_long"][str(p["names"][j])],
                    held_at_trough=bool(trough_units[col]>1e-8),gross_pnl=float(recgross[col]),costs=float(recfees[col]),
                    net_pnl=float(recnet[col]),contribution_to_trough_nav=float(recnet[col]/ep["trough_nav"])))
        for col in np.flatnonzero(np.abs(net) > 1e-8):
            j = int(a["ids"][col])
            contributions.append(dict(episode_rank=rank, peak_date=ep["peak_date"], trough_date=ep["trough_date"],
                ticker=str(p["names"][j]), name=p["names_long"][str(p["names"][j])],
                gross_pnl=float(gross[col]), costs=float(fee[col]), net_pnl=float(net[col]),
                contribution_to_peak_nav=float(net[col]/ep["peak_nav"])))
        for label, k, phase in [("peak_available_close", ep["peak_idx"], ep["peak_phase"]),
                                ("trough_close", ep["trough_idx"], "Close")]:
            k = int(k) - (1 if phase == "Open" else 0)
            for col in main:
                if net[col] >= 0:
                    continue
                j = int(a["ids"][col])
                snapshots.append(dict(episode_rank=rank, snapshot=label, net_episode_pnl=float(net[col]),
                    **feature_row(p, f, k, j)))
        # Same-ETF rebound diagnostics for the two largest episode losses.
        # Restrict each asset low to CLOSES ON WHICH IT WAS ACTUALLY HELD.
        # Otherwise a fund sold in June could incorrectly be labelled by a
        # September low that has no relationship to the original loss episode.
        for col in main[:2]:
            j = int(a["ids"][col])
            lo, hi = int(ep["peak_idx"]), int(ep["trough_idx"])
            held_rows=np.flatnonzero((a["daily"].k.to_numpy()>=lo)&(a["daily"].k.to_numpy()<=hi)
                &(a["qclose"][:,col]>1e-8))
            if not len(held_rows):
                continue
            held_ks=a["daily"].k.to_numpy()[held_rows].astype(int)
            low = int(held_ks[np.nanargmin(p["C"][held_ks,j])])
            end = min(low + 63, len(p["dates"]) - 1)
            row = dict(episode_rank=rank, ticker=str(p["names"][j]), name=p["names_long"][str(p["names"][j])],
                ex_post_asset_low_date=date(p, low), ex_post_asset_low_idx=low,
                low_definition="minimum Close while held inside portfolio decline",
                first_held_close_in_decline=date(p,held_ks[0]),last_held_close_in_decline=date(p,held_ks[-1]),
                portfolio_trough_date=ep["trough_date"],
                rebound_5=p["C"][low+5,j]/p["C"][low,j]-1 if low+5<len(p["dates"]) else np.nan,
                rebound_21=p["C"][low+21,j]/p["C"][low,j]-1 if low+21<len(p["dates"]) else np.nan,
                rebound_63=p["C"][low+63,j]/p["C"][low,j]-1 if low+63<len(p["dates"]) else np.nan,
                available_followup_sessions=end-low)
            for key in ("m5", "m21", "above_sma20", "above_sma63", "m126"):
                qualifies = np.flatnonzero(f[key][low:end+1, j] > 0)
                s = low + int(qualifies[0]) if len(qualifies) else None
                row[key+"_first_positive_date"] = date(p, s)
                row[key+"_sessions_from_low"] = s-low if s is not None else None
                row[key+"_rise_already_occurred"] = p["C"][s,j]/p["C"][low,j]-1 if s is not None else np.nan
                if s is not None:
                    for lag in (0,1,2):
                        exe=next_valid_open(p,s+lag,j)
                        row[f"{key}_entry_lag{lag}_date"]=date(p,exe)
                        row[f"{key}_rise_at_entry_lag{lag}"]=p["O"][exe,j]/p["C"][low,j]-1 if exe is not None else np.nan
            recovery.append(row)
            conditions={"m5_negative":f["m5"][:,j]<0,"m21_negative":f["m21"][:,j]<0,
                "below_sma20":f["above_sma20"][:,j]<0,
                "EXIT63":(f["above_sma63"][:,j]<0)&(f["m21"][:,j]<0),
                "TRAIL15":f["dd63"][:,j]<=-.15,"vol21_gt_vol63":f["vol21_over_vol63"][:,j]>1}
            # Event selection is retrospective, but the flag at s uses <=s.
            for condition,flag in conditions.items():
                for cadence in ("DAILY","WEEKLY_nonmonthly"):
                    usable=held_ks[flag[held_ks]]
                    if cadence.startswith("WEEKLY"):
                        usable=usable[weekly[usable]&~monthly[usable]]
                    s=int(usable[0]) if len(usable) else None
                    rec=dict(episode_rank=rank,ticker=str(p["names"][j]),condition=condition,cadence=cadence,
                        first_signal_close=date(p,s),first_signal_idx=s,
                        sessions_after_portfolio_peak=s-lo if s is not None else None,
                        original_last_held_close_in_decline=date(p,held_ks[-1]),
                        ex_post_asset_low_while_held=date(p,low))
                    if s is not None:
                        for lag in (0,1,2):
                            exe=next_valid_open(p,s+lag,j)
                            rec[f"exit_lag{lag}_date"]=date(p,exe)
                            rec[f"exit_lag{lag}_price"]=p["O"][exe,j] if exe is not None else np.nan
                            rec[f"asset_low_return_from_exit_lag{lag}"]=p["C"][low,j]/p["O"][exe,j]-1 if exe is not None and exe<=low else np.nan
                    warnings.append(rec)
    save("EPISODE_CONTRIBUTIONS.csv", contributions)
    save("EPISODE_FEATURE_SNAPSHOTS.csv", snapshots)
    save("ASSET_REBOUND_TIMING.csv", recovery)
    save("CAUSAL_FLAG_TIMING_WITHIN_EXPOST_EPISODES.csv",warnings)
    save("EPISODE_GAP_INTRADAY_FEES.csv",phase_pnl)
    save("RECOVERY_CONTRIBUTIONS.csv",recovery_attr)


def daily_diagnostics(p, f, a):
    dayrows, holdingrows = [], []
    net = a["gap"] + a["day"] - a["fees"]
    for t, row in enumerate(a["daily"].itertuples()):
        k = int(row.k)
        prior_nav = a["daily"].nav_close.iloc[t-1] if t else 10000.
        q = a["qopen"][t]
        ids = a["ids"]
        prev_val = q * np.nan_to_num(p["C"][k-1, ids], nan=0.)
        weights = prev_val/prior_nav
        held = np.flatnonzero(prev_val > 1e-6)
        r = dict(date=date(p,k), k=k, information_close_date=date(p,k-1), information_close_idx=k-1,
            portfolio_return=float(row.nav_close/prior_nav-1), gap_return=float(a["gap"][t].sum()/prior_nav),
            intraday_gross_return=float(a["day"][t].sum()/prior_nav), fee_return=float(a["fees"][t].sum()/prior_nav),
            prior_gross=float(weights.sum()), prior_positions=len(held),
            both_prior_holdings_fall=bool(len(held)>=2 and np.all(f["r1"][k, ids[held]]<0)))
        for key in FEATURE_KEYS:
            r["prior_weighted_"+key] = float(weights[held] @ f[key][k-1, ids[held]])
        for key in ("m5", "m21", "m126", "m252", "above_sma20", "above_sma63", "above_sma200"):
            r["prior_weight_share_positive_"+key] = float(weights[held] @ (f[key][k-1,ids[held]]>0))
        r["prior_weight_share_vol21_gt_vol63"] = float(weights[held] @ (f["vol21_over_vol63"][k-1, ids[held]]>1))
        b = f["breadth"].loc[k-1].to_dict()
        r.update({"prior_"+key:value for key,value in b.items() if key not in ("k","date")})
        b = f["breadth"].loc[k].to_dict()
        r.update({"realized_"+key:value for key,value in b.items() if key not in ("k","date")})
        dayrows.append(r)
        involved = np.flatnonzero((a["qopen"][t]>1e-8)|(a["qclose"][t]>1e-8))
        for col in involved:
            j = int(ids[col])
            holdingrows.append(dict(date=date(p,k), k=k, prior_weight=float(weights[col]),
                net_pnl=float(net[t,col]), gross_pnl=float((a["gap"]+a["day"])[t,col]),
                contribution=float(net[t,col]/prior_nav), realized_close_return=float(f["r1"][k,j]),
                **feature_row(p,f,k-1,j)))
    d = save("DAILY_CAUSAL_DIAGNOSTICS.csv", dayrows)
    h = save("HELD_ASSET_CAUSAL_DIAGNOSTICS.csv", holdingrows)
    worst = d.nsmallest(20, "portfolio_return").copy()
    worst["ex_post_loss_rank"] = np.arange(1,len(worst)+1)
    save("WORST_20_PORTFOLIO_DAYS.csv", worst)
    save("WORST_20_DAYS_HOLDINGS.csv", h[h.k.isin(worst.k)])
    stats=[]
    for label, frame in [("all_days_with_positions",d[d.prior_positions>0]),("worst20_days",worst),
                         ("worst20_days_2021_onward",d[d.date>="2021-01-01"].nsmallest(20,"portfolio_return"))]:
        r=dict(sample=label,days=len(frame),mean_return=frame.portfolio_return.mean(),
            both_prior_holdings_fall_share=frame.both_prior_holdings_fall.mean())
        for key in [c for c in d if c.startswith("prior_weight_share") or c.startswith("prior_weighted_")
                    or c.startswith("realized_eligible_fraction_negative")]:
            r[key+"_mean"]=frame[key].mean()
        stats.append(r)
    save("LOSS_FEATURE_DESCRIPTIVE_SUMMARY.csv",stats)
    return d,h


def worst_windows(p, f, a):
    x=np.r_[10000.,a["daily"].nav_close]
    rets=x[21:]/x[:-21]-1
    selected=[]
    for r in np.argsort(rets):
        end=int(r+21);start=end-21
        if all(end<=s or start>=e for s,e in selected):
            selected.append((start,end))
        if len(selected)==10:
            break
    rows,contrib,snapshots=[],[],[]
    for rank,(start,end) in enumerate(selected,1):
        ks=int(a["daily"].k.iloc[0]-1+start);ke=ks+21
        pnl=(a["gap"]+a["day"]-a["fees"])[start:end].sum(axis=0)
        assert abs(pnl.sum()-(x[end]-x[start]))<1e-7
        rows.append(dict(rank=rank,start_close_date=date(p,ks),end_close_date=date(p,ke),
            start_idx=ks,end_idx=ke,return_21=float(x[end]/x[start]-1),net_pnl=float(pnl.sum())))
        for col in np.argsort(pnl)[:3]:
            if pnl[col]>=0:
                continue
            j=int(a["ids"][col])
            contrib.append(dict(rank=rank,ticker=str(p["names"][j]),net_pnl=float(pnl[col]),
                contribution=float(pnl[col]/x[start])))
            snapshots.append(dict(rank=rank,snapshot="window_start_close",**feature_row(p,f,ks,j)))
            # Entry signal is causal even when the asset was selected within the window.
            buys=a["orders"][(a["orders"].j==j)&(a["orders"].side=="BUY")&(a["orders"].execution_idx<=ke)]
            if len(buys):
                b=buys.iloc[-1]
                snapshots.append(dict(rank=rank,snapshot="latest_buy_signal_before_window_end",entry_execution_date=b.date,
                    **feature_row(p,f,int(b.signal_idx),j)))
    save("WORST_21_SESSION_WINDOWS_NONOVERLAPPING.csv",rows)
    save("TAIL_WINDOW_CONTRIBUTIONS.csv",contrib)
    save("TAIL_WINDOW_CAUSAL_FEATURES.csv",snapshots)


def guard_diagnostics(p, f, guard, dual):
    rows, blocks=[] ,[]
    ins=guard["instructions"].set_index("instruction_id")
    monthly=guard["instructions"][guard["instructions"].reason.isin(["INITIAL","SCHEDULED"])]
    # Exclude incidental small forced trims of the other retained asset.
    for r in guard["orders"][guard["orders"].reason=="TREND_REDUCE"].itertuples():
        target=json.loads(ins.loc[r.instruction_id,"target_weights"])
        if target[int(r.j)]>1e-12:
            continue
        j,k,s=int(r.j),int(r.execution_idx),int(r.signal_idx)
        m=monthly[monthly.signal_idx>s]
        ns=int(m.iloc[0].signal_idx) if len(m) else None
        no=next_valid_open(p,ns,j) if ns is not None else None
        end=no if no is not None else len(p["dates"])-1
        end_price=p["O"][end,j] if no is not None else p["C"][end,j]
        curve=p["C"][k:end+1,j]/r.price-1
        after=guard["orders"][(guard["orders"].j==j)&(guard["orders"].side=="BUY")&(guard["orders"].execution_idx>k)]
        rec=dict(arm=guard["arm"],signal_date=date(p,s),exit_date=date(p,k),exit_idx=k,
            exit_price=r.price,exit_notional=r.notional,exit_cost=r.cost,
            next_monthly_signal_date=date(p,ns),next_monthly_open_date=date(p,no),
            sessions_locked_out=(no-k) if no is not None else None,
            price_return_until_next_monthly_open=float(end_price/r.price-1),
            max_close_rise_before_next_monthly=float(np.nanmax(curve)),
            max_close_fall_before_next_monthly=float(np.nanmin(curve)),
            marked_sold_quantity_pnl_until_next_monthly=float(r.quantity*(end_price-r.price)),
            next_same_asset_buy_date=after.iloc[0].date if len(after) else None,
            **feature_row(p,f,s,j))
        for h in (5,21):
            endh=min(k+h,len(p["dates"])-1)
            rec[f"price_return_{h}_sessions_after_exit"]=p["C"][endh,j]/r.price-1
        rows.append(rec)
    for r in guard["decisions"].itertuples():
        meta=json.loads(r.meta_json)
        selected=meta["selected_indices"]
        blocked=set(selected)-set(meta["invested_indices"])
        nxt=monthly[monthly.signal_idx>r.signal_idx]
        end_signal=int(nxt.iloc[0].signal_idx) if len(nxt) else None
        for j in blocked:
            k=next_valid_open(p,int(r.signal_idx),j)
            end=next_valid_open(p,end_signal,j) if end_signal is not None else None
            if k is None:
                continue
            blocks.append(dict(arm=guard["arm"],decision_date=r.signal_date,
                excluded_open_date=date(p,k),next_monthly_open_date=date(p,end),
                raw_open_to_open_return=(p["O"][end,j]/p["O"][k,j]-1) if end is not None else None,
                **feature_row(p,f,int(r.signal_idx),j)))
    # Realized whole-account monthly returns use final close of preceding month.
    comp=pd.DataFrame({"date":pd.to_datetime(dual["daily"].date),"dual":dual["daily"].nav_close,
        "guard":guard["daily"].nav_close})
    month=comp.groupby(comp.date.dt.to_period("M"),sort=True).last()
    month["dual_return"]=month.dual/np.r_[10000.,month.dual.to_numpy()[:-1]]-1
    month["guard_return"]=month.guard/np.r_[10000.,month.guard.to_numpy()[:-1]]-1
    month["guard_minus_dual_return"]=month.guard_return-month.dual_return
    month["arm"]=guard["arm"]
    return rows,blocks,month.reset_index(drop=True)


def lag_decomposition(p, accounts):
    base=accounts["BASE"]
    rows=[]
    for scenario in SCENARIOS:
        a=accounts[scenario]
        d=a["daily"]
        r=np.log(d.nav_close.to_numpy()/np.r_[10000.,d.nav_close.to_numpy()[:-1]])
        b=base["daily"]
        rb=np.log(b.nav_close.to_numpy()/np.r_[10000.,b.nav_close.to_numpy()[:-1]])
        temp=pd.DataFrame({"date":pd.to_datetime(d.date),"log_return":r,"base_log_return":rb})
        for period, frame in temp.groupby(temp.date.dt.to_period("M")):
            rows.append(dict(scenario=scenario,month=str(period),
                monthly_return=float(np.expm1(frame.log_return.sum())),
                base_monthly_return=float(np.expm1(frame.base_log_return.sum())),
                log_return_gap_vs_base=float((frame.log_return-frame.base_log_return).sum())))
    save("CANDIDATE_SCENARIO_MONTHLY_RETURN_GAPS.csv",rows)


def position_periods(p,a):
    rows=[]
    final_k=int(a["daily"].k.iloc[-1])
    for j,orders in a["orders"].groupby("j",sort=True):
        j=int(j);units=0.;active=None
        for r in orders.itertuples():
            if active is None:
                assert r.side=="BUY"
                active=dict(ticker=str(p["names"][j]),name=p["names_long"][str(p["names"][j])],
                    entry_date=r.date,entry_idx=int(r.execution_idx),entry_price=r.price,
                    buy_notional=0.,sell_notional=0.,costs=0.,orders=0)
            units+=r.quantity if r.side=="BUY" else -r.quantity
            active["buy_notional" if r.side=="BUY" else "sell_notional"]+=r.notional
            active["costs"]+=r.cost;active["orders"]+=1
            if units<1e-8:
                units=0.
                active.update(exit_or_mark_date=r.date,exit_idx=int(r.execution_idx),closed=True,
                    remaining_mark=0.,exit_or_mark_price=r.price)
                rows.append(active);active=None
        if active is not None:
            active.update(exit_or_mark_date=date(p,final_k),exit_idx=final_k,closed=False,
                remaining_mark=float(units*p["C"][final_k,j]),exit_or_mark_price=float(p["C"][final_k,j]))
            rows.append(active)
    for r in rows:
        r["net_pnl"]=r["sell_notional"]+r["remaining_mark"]-r["buy_notional"]-r["costs"]
        r["elapsed_sessions"]=r["exit_idx"]-r["entry_idx"]
    assert abs(sum(r["net_pnl"] for r in rows)-(a["daily"].nav_close.iloc[-1]-10000))<1e-7
    save("HELD_POSITION_EPISODES.csv",rows)


def main():
    p=load_inputs()
    f=features(p)
    candidate={s:reconstruct(p,ARM,s) for s in SCENARIOS}
    dual=reconstruct(p,"DEDUP_DUAL21","BASE")
    guards=[reconstruct(p,a,"BASE") for a in ("DEDUP_DUAL_EXIT63","DEDUP_DUAL_TRAIL15")]
    summary=[]; all_ep=[]
    for s,a in candidate.items():
        summary.append({key:a["metrics"][key] for key in ("path_id","cagr","end_equity","maxdd_close","maxdd_sampled",
            "worst_21_sessions","costs","orders","mean_exposure","trading_days_per_year")})
        for basis in ("sampled","close"):
            all_ep.append(episodes(p,a,basis))
    save("CANDIDATE_FIVE_SCENARIOS.csv",summary)
    save("EXISTING_CONTROLS_SUMMARY.csv",[{key:a["metrics"][key] for key in ("path_id","cagr","end_equity",
        "maxdd_close","maxdd_sampled","costs","orders","mean_exposure","trading_days_per_year")}
        for a in [dual]+guards])
    save("DRAWDOWN_EPISODES_ALL_SCENARIOS.csv",pd.concat(all_ep,ignore_index=True))
    eps=episodes(p,candidate["BASE"])
    save("BASE_LARGEST_DRAWDOWNS.csv",eps.head(15))
    event_features(p,f,candidate["BASE"],eps)
    daily_diagnostics(p,f,candidate["BASE"])
    worst_windows(p,f,candidate["BASE"])
    exits,blocks,monthly=[],[],[]
    for guard in guards:
        e,b,m=guard_diagnostics(p,f,guard,dual)
        exits.extend(e);blocks.extend(b);monthly.append(m)
    save("EXISTING_GUARD_EXITS_AND_LOCKOUT.csv",exits)
    save("EXISTING_GUARD_MONTHLY_BLOCKED_ENTRIES.csv",blocks)
    save("EXISTING_GUARD_MONTHLY_COMPARISON_VS_DUAL21.csv",pd.concat(monthly,ignore_index=True))
    lag_decomposition(p,candidate)
    position_periods(p,candidate["BASE"])
    save("ACCOUNT_RECONSTRUCTION_QA.csv",[a["qa"] for a in list(candidate.values())+[dual]+guards])
    save("UNIVERSE_BREADTH.csv",f["breadth"].loc[candidate["BASE"]["daily"].k].reset_index(drop=True))
    frozen=read_json(ROOT/"results_stage2/RUN_MANIFEST.json")
    manifest={str(path.relative_to(ROOT)):hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(INPUTS)}
    matches={key:manifest[key]==value for key,value in frozen["data_hashes"].items()}
    assert all(matches.values()), "FROZEN_SOURCE_DATA_CHANGED"
    (HERE/"SOURCE_MANIFEST.json").write_text(json.dumps({"immutable_source_root":str(ROOT),"source_sha256":manifest,
        "script_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dataset_hashes_match_stage2_frozen_manifest":matches,
        "no_fitted_strategy":True,"ex_post_labels_are_outputs_only":True,
        "benchmark":str(p["names"][int(p["benchmark"])]),
        "benchmark_name":p["names_long"][str(p["names"][int(p["benchmark"])])]},indent=2)+"\n")
    print("Independent reconstruction passed for 8 existing accounts.")
    print(eps.head(10)[["drawdown","peak_date","peak_phase","trough_date","trough_phase","recovery_date",
        "decline_elapsed_sessions","recovery_elapsed_sessions","underwater_elapsed_sessions"]].to_string(index=False))


if __name__=="__main__":
    main()
