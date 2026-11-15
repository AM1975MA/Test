#!/usr/bin/env python3
"""Independent, bounded audit of the recorded accounts and their quote inputs.

No strategy/engine imports, simulated orders, input repairs, or source downloads.
Quantities are accumulated from the recorded ORDERS, preserving roundoff. The
1e-10 unit threshold is used only for economic exposure/staleness descriptions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PRIOR = ROOT.parent / "olc108"
OUT = ROOT / "validation/source_execution"
EPS = 1e-10


def digest(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def num(x):
    try:
        y = float(x)
        return y if np.isfinite(y) else None
    except (TypeError, ValueError):
        return None


def clean(x):
    if isinstance(x, dict):
        return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, np.ndarray):
        return clean(x.tolist())
    if isinstance(x, (np.integer, np.bool_)):
        return x.item()
    if isinstance(x, (float, np.floating)):
        return float(x) if np.isfinite(x) else None
    return x


def ratio(a, b):
    return a / b - 1 if np.isfinite(a) and np.isfinite(b) and b > 0 else np.nan


def save_csv(rows, name, columns=None):
    d = pd.DataFrame(rows, columns=columns)
    d.to_csv(OUT / name, index=False)
    return d


def run(directories):
    OUT.mkdir(parents=True, exist_ok=True)
    source = ROOT / "source/data/XETRA_EUR_ETF.npz"
    panel = np.load(source, allow_pickle=False)
    dates = pd.DatetimeIndex(panel["dates"])
    ds = dates.strftime("%Y-%m-%d").to_numpy()
    date_i = {d: i for i, d in enumerate(ds)}
    names = panel["names"].astype(str)
    name_i = {s: j for j, s in enumerate(names)}
    cover = pd.read_csv(ROOT / "data/UNIVERSE_COVERAGE.csv")
    coverage = cover.drop_duplicates("isin").set_index("isin")
    v3file = PRIOR / "results/V3_SOURCE_SCOPE_CHECK.json"
    v3 = json.loads(v3file.read_text())
    quarantine = set(v3["quarantined_instruments"])
    prior_used = {(x["isin"], x["date"]) for x in v3["v3_actual_account_uses_of_existing_flags"]}
    prior_fills = defaultdict(int)
    for x in v3["v3_actual_account_uses_of_existing_flags"]:
        prior_fills[(x["isin"],x["date"])] += x["fill_count"]
    frozen_file = PRIOR / "superseded_v2/results/V2_HELD_SOURCE_REVIEW.csv"
    frozen = pd.read_csv(frozen_file)
    inputs = {str(source.relative_to(ROOT)): digest(source), str(v3file): digest(v3file), str(frozen_file): digest(frozen_file)}
    paths = []
    all_isins = set()
    for directory in directories:
        for metric in sorted((ROOT / directory).glob("*/METRICS.json")):
            d = metric.parent
            orders = pd.read_csv(d / "ORDERS.csv.gz")
            daily = pd.read_csv(d / "DAILY.csv.gz")
            if len(orders):
                all_isins.update(orders.ticker.astype(str))
            paths.append((directory, d.name, d, orders, daily))
            for f in [metric, d / "ORDERS.csv.gz", d / "DAILY.csv.gz", d / "DECISIONS.npz", d / "DECISIONS.csv"]:
                inputs[str(f.relative_to(ROOT))] = digest(f)
    expected_path_counts = {"results":110,"results_stage2":50,"results_stage3":40}
    actual_path_counts = {directory:sum(p[0]==directory for p in paths) for directory in directories}
    for directory in directories:
        if directory in expected_path_counts:
            assert actual_path_counts[directory] == expected_path_counts[directory], f"Incomplete matrix {directory}: {actual_path_counts[directory]}"
    assert paths, "No completed paths"
    assert all_isins <= set(names), "Unknown recorded instrument"
    assert not (all_isins & quarantine), "Quarantined recorded instrument"
    priority = frozen[frozen.symbol.isin(["IQSE.DE","F703.DE","UEQU.DE"]) & frozen.positive_volume_gap_flag]
    priority_isins = set(priority["isin"]) & set(names)
    isins = sorted(all_isins | priority_isins)
    gj = np.array([name_i[s] for s in isins])
    gmap = {s: q for q, s in enumerate(isins)}
    C = panel["C"][:, gj]
    O = panel["O"][:, gj]
    obs = panel["observed"][:, gj]
    opobs = panel["open_observed"][:, gj]
    T, N = C.shape
    last = np.maximum.accumulate(np.where(obs, np.arange(T)[:, None], -1), axis=0)
    # Input C contains only accepted observations. Reconstruct its causal carry
    # explicitly; never substitute an invalid raw source row for a missing Close.
    C = np.where(last >= 0, C[np.maximum(last,0), np.arange(N)[None,:]], np.nan)
    dayn = dates.values.astype("datetime64[D]").astype(int)
    age = np.where(last >= 0, dayn[:, None] - dayn[np.maximum(last, 0)], -1)
    raw = {}
    event = {}
    accepted_panel_raw_mismatches = []
    flags_by_isin = {s: d for s, d in frozen[frozen["isin"].isin(isins)].groupby("isin")}
    missing_raw = []
    for s in isins:
        q = gmap[s]
        sym = str(coverage.loc[s, "symbol"])
        file = PRIOR / "data/prices" / f"{sym}.csv.gz"
        if not file.exists():
            missing_raw.append(str(file))
            continue
        inputs[str(file)] = digest(file)
        r = pd.read_csv(file)
        assert not r.date.duplicated().any(), f"Duplicate raw dates {s}"
        raw[s] = r.set_index("date")
        r["factor"] = r.adj_close / r.close
        r["raw_ret"] = r.close / r.close.shift() - 1
        r["adj_ret"] = r.adj_close / r.adj_close.shift() - 1
        r["factor_ret"] = r.factor / r.factor.shift() - 1
        r["raw_open_jump"] = r.open / r.close.shift() - 1
        r["adjusted_open_jump"] = r.adj_open / r.adj_close.shift() - 1
        fr = {str(z.date): z for z in flags_by_isin.get(s, pd.DataFrame()).itertuples(index=False)}
        for row in r.itertuples(index=False):
            dt = str(row.date)
            if dt not in date_i:
                continue
            k = date_i[dt]
            if obs[k,q] and (not np.isfinite(row.adj_close) or abs(C[k,q]-row.adj_close) > 1e-8):
                accepted_panel_raw_mismatches.append(dict(isin=s,date=dt,field="Close",panel=num(C[k,q]),raw=num(row.adj_close)))
            if opobs[k,q] and (not np.isfinite(row.adj_open) or abs(O[k,q]-row.adj_open) > 1e-8):
                accepted_panel_raw_mismatches.append(dict(isin=s,date=dt,field="Open",panel=num(O[k,q]),raw=num(row.adj_open)))
            fl = []
            if abs(row.factor_ret) > .1:
                fl.append("RAW_ADJUSTED_FACTOR_CHANGE_GT10PCT")
            if abs(row.adj_ret) > .3:
                fl.append("SOURCE_ADJUSTED_CLOSE_RETURN_GT30PCT")
            if abs(row.raw_open_jump) > .3:
                fl.append("SOURCE_RAW_OPEN_JUMP_GT30PCT")
            if abs(row.adjusted_open_jump) > .3:
                fl.append("SOURCE_ADJUSTED_OPEN_JUMP_GT30PCT")
            pc_ret = ratio(C[k, q], C[k-1, q]) if k else np.nan
            po_ret = ratio(O[k, q], C[k-1, q]) if k else np.nan
            if obs[k, q] and abs(pc_ret) > .3:
                fl.append("ACCEPTED_CLOSE_RETURN_GT30PCT")
            if opobs[k, q] and abs(po_ret) > .3:
                fl.append("ACCEPTED_OPEN_JUMP_GT30PCT")
            old = fr.get(dt)
            if not fl and old is None:
                continue
            event[(s, dt)] = dict(
                isin=s, symbol=sym, date=dt, k=k,
                provider_name=str(coverage.loc[s, "provider_name"]),
                old_flag=old is not None,
                frozen_flags=str(old.source_flags) if old else "",
                old_review_status=str(old.review_status) if old else "",
                fresh_material_flags="|".join(fl),
                material=bool(fl or (old and (bool(old.positive_volume_gap_flag) or old.review_status == "PRIMARY_CORROBORATION_REQUIRED"))),
                used_in_prior_v3=(s, dt) in prior_used,
                prior_v3_fill_count=prior_fills[(s,dt)],
                raw_open=num(row.open), raw_close=num(row.close), adj_open=num(row.adj_open), adj_close=num(row.adj_close),
                volume=num(row.volume), raw_return=num(row.raw_ret), adjusted_return=num(row.adj_ret),
                factor_change=num(row.factor_ret), raw_open_jump=num(row.raw_open_jump),
                adjusted_open_jump=num(row.adjusted_open_jump), accepted_close_return=num(pc_ret), accepted_open_jump=num(po_ret),
                close_observed=bool(obs[k, q]), open_observed=bool(opobs[k, q]),
                source_observed=bool(row.observed), valid_geometry=bool(row.valid_geometry),
                dividend=num(row.dividend), split_ratio=num(row.split_ratio),
                source_price_csv=str(file),
            )
    assert not missing_raw, missing_raw
    events_by_isin = defaultdict(list)
    for e in event.values():
        events_by_isin[e["isin"]].append(e)

    summaries, stale_rows, order_rows, usages, histories = [], [], [], [], []
    source_mismatches = []
    reconstruction_checks = []
    for path_number, (directory, pid, d, orders, daily) in enumerate(paths, 1):
        stage = "stage1" if directory == "results" else directory
        pkey = f"{directory}/{pid}"
        units = np.zeros((T, N), dtype=float)
        fills = defaultdict(list)
        cash = np.zeros(T)
        cash_level = 10000.
        if len(orders):
            for order_index, row in orders.iterrows():
                k, q = int(row.execution_idx), gmap[str(row.ticker)]
                assert ds[k] == row.execution_date == row.date
                assert row.side in ("BUY", "SELL")
                units[k, q] += float(row.quantity) * (1 if row.side == "BUY" else -1)
                cash[k] += -float(row.notional)-float(row.cost) if row.side == "BUY" else float(row.notional)-float(row.cost)
                fills[(str(row.ticker), k)].append(row)
                rr = raw[str(row.ticker)].loc[str(row.execution_date)]
                turnover = float(rr.close) * float(rr.volume)
                participation = float(row.notional) / turnover if np.isfinite(turnover) and turnover > 0 else np.nan
                ordrec = dict(stage=stage, path_id=pid, order_row=order_index, isin=str(row.ticker), symbol=str(coverage.loc[row.ticker, "symbol"]),
                    date=str(row.execution_date), side=row.side, notional_eur=float(row.notional),
                    raw_close=float(rr.close), raw_volume=float(rr.volume), raw_day_turnover_eur=turnover,
                    participation_ratio=participation, ratio_ge_10pct=bool(participation >= .1), ratio_ge_100pct=bool(participation >= 1),
                    open_observed=bool(opobs[k, q]), close_observed=bool(obs[k, q]),
                    raw_geometry_valid=bool(rr.valid_geometry), adjusted_open=float(O[k, q]), fill_price=float(row.price))
                order_rows.append(ordrec)
                if not opobs[k, q] or not np.isfinite(O[k, q]) or abs(float(row.price)-O[k, q]) > 1e-9:
                    source_mismatches.append({"path":pkey, "date":str(row.execution_date), "isin":str(row.ticker), "reason":"FILL_VS_ACCEPTED_OPEN"})
        units = np.cumsum(units, axis=0)
        cash = cash_level + np.cumsum(cash)
        before = np.vstack([np.zeros((1, N)), units[:-1]])
        ks = daily.k.to_numpy(dtype=int)
        assert (ds[ks] == daily.date.to_numpy()).all()
        economic = units[ks] > EPS
        values = units[ks] * C[ks]
        stale = economic & (age[ks] > 5)
        dust = (units[ks] != 0) & (np.abs(units[ks]) <= EPS)
        fallback_mask = (before[ks] > EPS) & ~opobs[ks]
        fallback_source = last[np.maximum(ks-1,0)]
        fallback_age = dayn[ks,None] - dayn[np.maximum(fallback_source,0)]
        fallback_ages = fallback_age[fallback_mask]
        for i, q in np.argwhere(stale):
            k = ks[i]
            stale_rows.append(dict(stage=stage, path_id=pid, date=ds[k], isin=isins[q], symbol=str(coverage.loc[isins[q], "symbol"]),
                units=float(units[k,q]), value_eur=float(values[i,q]), account_nav_close=float(daily.nav_close.iloc[i]),
                nav_share=float(values[i,q]/daily.nav_close.iloc[i]), age_calendar_days=int(age[k,q]), last_observed_date=ds[last[k,q]], close_observed=bool(obs[k,q])))
        with np.load(d / "DECISIONS.npz", allow_pickle=False) as z:
            decision = {key:z[key] for key in z.files}
        dec = pd.read_csv(d / "DECISIONS.csv")
        dks = decision["k"].astype(int)
        # The initial signal can precede the account start: its units are zero.
        ref_units = decision["units"][:, gj]
        udiff = float(np.max(np.abs(units[dks]-ref_units))) if len(dks) else 0.
        cdiff = float(np.max(np.abs(cash[dks]-decision["cash"]))) if len(dks) else 0.
        all_columns_outside = np.ones(len(names), dtype=bool)
        all_columns_outside[gj] = False
        outside_units_max = float(np.max(np.abs(decision["units"][:, all_columns_outside]))) if all_columns_outside.any() else 0.
        nav = cash[ks] + np.nansum(units[ks] * C[ks], axis=1)
        navdiff = float(np.max(np.abs(nav-daily.nav_close.to_numpy())))
        reconstruction_checks.append(dict(stage=stage, path_id=pid, units_max_abs_difference=udiff,
            cash_max_abs_difference=cdiff, close_nav_max_abs_difference=navdiff, units_outside_recorded_isins_max=outside_units_max,
            min_reconstructed_units=float(units.min()), max_dust_value_eur=float(np.nanmax(np.where(dust,np.abs(values),0.)))))

        traded = set(orders.ticker.astype(str)) if len(orders) else set()
        path_use_count = 0
        new_use_count = 0
        for s in sorted(traded):
            q = gmap[s]
            for e in events_by_isin[s]:
                k = e["k"]
                if k > ks[-1]:
                    continue
                close_idx = ks[(last[ks, q] == k) & (units[ks, q] > EPS)] if obs[k, q] else np.array([],dtype=int)
                prev_idx = np.maximum(ks-1,0)
                fallback_idx = ks[(~opobs[ks,q]) & (before[ks,q] > EPS) & (last[prev_idx,q] == k)] if obs[k,q] else np.array([],dtype=int)
                opening = bool(opobs[k,q] and before[k,q] > EPS)
                fs = fills.get((s,k),[])
                if fs or opening or len(close_idx) or len(fallback_idx):
                    path_use_count += 1
                    new_use_count += int(not e["used_in_prior_v3"])
                    # Economic day attribution from the held account; no counterfactual run.
                    price_before = C[k-1,q] if k else np.nan
                    price_open = O[k,q] if opobs[k,q] else price_before
                    overnight = before[k,q]*(price_open-price_before)
                    intraday = units[k,q]*(C[k,q]-price_open)
                    usages.append(dict(stage=stage,path_id=pid,**e,
                        units_before=float(before[k,q]),units_after=float(units[k,q]),
                        opening_mark=opening,close_mark_on_date=bool(k in close_idx),
                        close_mark_sessions_including_carry=int(len(close_idx)),
                        opening_fallback_sessions=int(len(fallback_idx)),
                        last_close_carry_use=ds[close_idx[-1]] if len(close_idx) else None,
                        fill_count=len(fs),fill_notional_eur=float(sum(x.notional for x in fs)),
                        new_execution_use_vs_v3=bool(fs and not e["prior_v3_fill_count"]),
                        overnight_asset_pnl_eur=float(overnight),intraday_asset_pnl_eur=float(intraday),
                        asset_day_pnl_before_costs_eur=float(overnight+intraday)))
        meta = [json.loads(x) for x in dec.meta_json]
        for h, k in enumerate(dks):
            selected = set(np.flatnonzero(decision["raw_weights"][h] > EPS))
            selected.update(meta[h].get("selected_indices",[]))
            for j in selected:
                s = names[j]
                if s not in events_by_isin:
                    continue
                q = gmap[s]
                for e in events_by_isin[s]:
                    ek=e["k"]
                    if not e["material"] or not e["close_observed"] or not max(0,k-252) <= ek <= k:
                        continue
                    endpoints = [horizon for horizon in [0,21,63,126,252] if k >= horizon and last[k-horizon,q] == ek]
                    histories.append(dict(stage=stage,path_id=pid,isin=s,symbol=e["symbol"],date=e["date"],signal_date=ds[k],
                        panel_sessions_since_event=int(k-ek),source_flags=e["frozen_flags"],fresh_material_flags=e["fresh_material_flags"],
                        raw_target_weight=float(decision["raw_weights"][h,j]),
                        known_prior_v3_account_event=e["used_in_prior_v3"],
                        accepted_close_feature_endpoint_horizons="|".join(map(str,endpoints)),
                        accepted_close_in_63_return_window=bool(ek >= k-63),
                        accepted_close_in_126_return_window=bool(ek >= k-126),
                        accepted_close_in_200_sma_window=bool(ek >= k-199)))
        po = [r for r in order_rows if r["stage"]==stage and r["path_id"]==pid]
        ratios = np.array([r["participation_ratio"] for r in po],float)
        invalid_den = int((~np.isfinite(ratios)).sum())
        sa = age[ks][economic]
        summaries.append(dict(stage=stage,path_id=pid,orders=len(orders),traded_isins=len(traded),
            economically_held_asset_sessions=int(economic.sum()),maximum_held_close_age_days=int(sa.max()) if len(sa) else 0,
            stale_asset_sessions_gt5=int(stale.sum()),stale_account_sessions_gt5=int(stale.any(axis=1).sum()),
            maximum_stale_value_eur=float(np.nanmax(np.where(stale,values,0.))),
            maximum_stale_nav_share=float(np.nanmax(np.where(stale,values/daily.nav_close.to_numpy()[:,None],0.))),
            opening_fallback_asset_sessions=int(fallback_mask.sum()),
            maximum_opening_fallback_close_age_days=int(fallback_ages.max()) if len(fallback_ages) else 0,
            opening_fallback_asset_sessions_gt5=int((fallback_mask & (fallback_age>5)).sum()),
            dust_asset_sessions=int(dust.sum()),invalid_participation_denominators=invalid_den,
            orders_participation_ge10pct=int(np.sum(ratios >= .1)),orders_participation_ge100pct=int(np.sum(ratios >= 1)),
            max_participation_ratio=float(np.nanmax(ratios)) if len(ratios) else 0.,
            median_participation_ratio=float(np.nanmedian(ratios)) if len(ratios) else 0.,
            direct_frozen_or_threshold_event_uses=path_use_count,new_vs_v3_global_event_uses=new_use_count))
        if path_number % 20 == 0:
            print(f"Audited {path_number}/{len(paths)} paths", flush=True)

    sd = save_csv(summaries, "PATH_SOURCE_EXECUTION_SUMMARY.csv")
    save_csv(stale_rows, "HELD_STALENESS_EVENTS.csv.gz", columns=["stage","path_id","date","isin","symbol","units","value_eur","account_nav_close","nav_share","age_calendar_days","last_observed_date","close_observed"])
    od = save_csv(order_rows, "EXECUTION_PARTICIPATION.csv.gz")
    ed = save_csv(sorted(event.values(), key=lambda x:(x["isin"],x["date"])), "SOURCE_EVENT_CATALOGUE.csv")
    eu = save_csv(usages, "ACTUAL_SOURCE_EVENT_USE.csv")
    hd = save_csv(histories, "SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv")
    rc = save_csv(reconstruction_checks, "RECONSTRUCTION_CHECKS.csv")
    unique_used = sorted({(e["isin"],e["date"]) for e in usages})
    new_unique_used = sorted(set(unique_used)-prior_used)
    new_material_used = [key for key in new_unique_used if event[key]["material"]]
    detail = []
    for s, dt in unique_used:
        ev = event[(s,dt)]
        uu = [r for r in usages if r["isin"]==s and r["date"]==dt]
        detail.append({**ev, "paths":len(uu), "arms":sorted({r["path_id"].split("__")[0] for r in uu}),
            "fills":sum(r["fill_count"] for r in uu), "path_stages":sorted({r["stage"] for r in uu}),
            "max_abs_asset_day_pnl_eur":max(abs(r["asset_day_pnl_before_costs_eur"]) for r in uu)})
    summary = dict(
        status=("FAIL_RECORDED_ACCOUNT_OR_OPEN_SOURCE_MISMATCH" if source_mismatches or accepted_panel_raw_mismatches or rc.close_nav_max_abs_difference.max() > 1e-6 or rc.units_max_abs_difference.max() > 1e-7 else
            "COMPLETED_BOUND_AUDIT_REQUIRES_MATERIAL_EVENT_ADJUDICATION" if new_material_used else
            "PASS_BOUNDED_NO_NEW_MATERIAL_SOURCE_EVENT_ACCOUNT_USE"),
        created_utc=datetime.now(timezone.utc).isoformat(),
        directories=directories, expected_stage1_paths=110, paths_checked=len(paths),
        expected_path_counts={k:expected_path_counts.get(k) for k in directories},actual_directory_path_counts=actual_path_counts,
        stage_path_counts=sd.groupby("stage").size().to_dict(),
        panel_assets=len(names),panel_sessions=T,panel_sha256=digest(source),
        economic_units_threshold=EPS,
        quarantined_isins=sorted(quarantine),quarantined_panel_hits=sorted(set(names)&quarantine),quarantined_order_hits=sorted(all_isins&quarantine),
        orders_checked=len(od),actual_traded_isins=len(all_isins),scanned_instruments_including_priority_open_cases=len(isins),
        input_and_recorded_result_sha256=inputs,
        invalid_fill_source_events=source_mismatches,
        accepted_panel_vs_raw_price_mismatches=accepted_panel_raw_mismatches,
        audit_script_sha256=digest(Path(__file__)),
        maximum_units_reconstruction_difference=rc.units_max_abs_difference.max(),
        maximum_cash_reconstruction_difference=rc.cash_max_abs_difference.max(),
        maximum_close_nav_reconstruction_difference=rc.close_nav_max_abs_difference.max(),
        maximum_numeric_dust_value_eur=rc.max_dust_value_eur.max(),
        maximum_held_close_age_days=int(sd.maximum_held_close_age_days.max()),
        maximum_opening_fallback_close_age_days=int(sd.maximum_opening_fallback_close_age_days.max()),
        opening_fallback_asset_path_sessions_gt5=int(sd.opening_fallback_asset_sessions_gt5.sum()),
        stale_asset_path_sessions_gt5=int(sd.stale_asset_sessions_gt5.sum()),
        paths_with_stale_gt5=int((sd.stale_asset_sessions_gt5>0).sum()),
        orders_participation_ge10pct=int(od.ratio_ge_10pct.sum()),orders_participation_ge100pct=int(od.ratio_ge_100pct.sum()),
        maximum_participation_ratio=od.participation_ratio.max(),
        invalid_participation_denominators=int(sd.invalid_participation_denominators.sum()),
        source_flags_on_actually_traded_isins=sum(e["isin"] in all_isins for e in event.values()),
        material_source_flags_on_actually_traded_isins=sum(e["material"] and e["isin"] in all_isins for e in event.values()),
        bounded_source_event_catalogue_rows=len(event),bounded_material_source_event_rows=int(ed.material.sum()),
        source_event_path_uses=len(usages),unique_source_events_used=len(unique_used),
        new_unique_source_events_used_vs_v3_global=[list(x) for x in new_unique_used],
        new_unique_material_source_events_used_vs_v3_global=[list(x) for x in new_material_used],
        new_execution_uses_of_previously_unfilled_events=[{k:r[k] for k in ["stage","path_id","isin","symbol","date","fill_count","fill_notional_eur","used_in_prior_v3","prior_v3_fill_count"]} for r in usages if r["new_execution_use_vs_v3"]],
        priority_open_event_checks=[dict(isin=str(r.isin),symbol=r.symbol,date=r.date,
            traded_any_date=str(r.isin) in all_isins,
            accepted_open=bool(opobs[date_i[r.date],gmap[str(r.isin)]]),
            accepted_close=bool(obs[date_i[r.date],gmap[str(r.isin)]]),
            direct_use_paths=sum(x["isin"]==str(r.isin) and x["date"]==r.date for x in usages),
            selected_close_history_rows=sum(x["isin"]==str(r.isin) and x["date"]==r.date for x in histories))
            for r in priority.itertuples(index=False) if r.date in date_i and str(r.isin) in gmap],
        actual_source_event_summary=detail,
        selected_material_flag_history_rows=len(histories),
        scope_limits=[
            "Reconstructed quantities and cash exclusively from recorded fills; did not import the engine or simulate counterfactual accounts.",
            "Economic holding/staleness descriptions use units >1e-10. Raw cumulative units, including roundoff residuals, remain in reconstruction and NAV checks.",
            "Participation is order EUR notional divided by that day's raw EUR close times the venue's full-day volume. It is an ex-post descriptive proxy, not opening depth, spread, impact, or total ETF liquidity.",
            "The accepted Open mask depends on the completed day's positive volume, an ex-post source convention; adjustment-factor point-in-time availability is not certified.",
            "Bounded quote scan covers histories of instruments actually traded in these accounts, plus all frozen source flags for those instruments; not a new universe-wide audit or independent certification of every quote.",
            "Direct event use traces accepted source Open and Close provenance, including Close carry and opening fallback. A discarded raw observation is not treated as used merely because the instrument was held that date.",
            "Selected-history records are conservative 253-session lineage of accepted Close, not causal proof of ranking influence. Open-only anomalies do not make their normal Close invalid. Non-selected group members are not fully replayed here.",
            "New versus V3 compares unique ISIN/date direct use with the completed V3 source audit across its 76 paths, not a paired effect estimate.",
            "No outcome-based correction or deletion, input mutation, new source download, trade, automation, or remote publication was performed."
        ])
    (OUT / "SOURCE_EXECUTION_AUDIT.json").write_text(json.dumps(clean(summary),indent=2,allow_nan=False)+"\n")
    print(json.dumps(clean({k:summary[k] for k in ["status","paths_checked","stage_path_counts","orders_checked","actual_traded_isins","maximum_units_reconstruction_difference","maximum_cash_reconstruction_difference","maximum_close_nav_reconstruction_difference","maximum_held_close_age_days","stale_asset_path_sessions_gt5","orders_participation_ge10pct","orders_participation_ge100pct","maximum_participation_ratio","unique_source_events_used","new_unique_source_events_used_vs_v3_global","selected_material_flag_history_rows"]}),indent=2))
    print("ACTUAL_EVENT_SUMMARY")
    for ev in detail:
        print(json.dumps(clean({k:ev[k] for k in ["isin","symbol","date","frozen_flags","fresh_material_flags","material","used_in_prior_v3","paths","fills","max_abs_asset_day_pnl_eur"]})))


if __name__ == "__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--results",nargs="+",default=["results"])
    args=ap.parse_args()
    run(args.results)
