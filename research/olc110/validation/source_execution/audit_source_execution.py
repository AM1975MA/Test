#!/usr/bin/env python3
"""Independent OLC110 source/execution audit adapted from the OLC109 audit.

Read-only on inputs/results. No production imports, strategy replay, quote repair,
counterfactual deletion, downloads, or live orders. NEXT_CLOSE uses accepted Close
quotes and reports Close pretrade marks, never hypothetical Open executions.
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
OUT = ROOT / "validation/source_execution"
PREVIOUS = ROOT.parent / "olc109"
RAW_ROOT = ROOT.parent / "olc108"
EPS = 1e-10
EXPECTED_PROTOCOL = "aca685d1d228f857c48fd1a4aafc45170a847765e84352c932943c541d119740"
INPUTS = {}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def track(path):
    path = Path(path).resolve()
    INPUTS[str(path)] = sha(path)
    return path


def csv(path, **kwargs):
    return pd.read_csv(track(path), float_precision="round_trip", **kwargs)


def js(path):
    return json.loads(track(path).read_text())


def clean(x):
    if isinstance(x, dict): return {str(k): clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)): return [clean(v) for v in x]
    if isinstance(x, np.ndarray): return clean(x.tolist())
    if isinstance(x, (np.integer, np.bool_)): return x.item()
    if isinstance(x, (float, np.floating)): return float(x) if np.isfinite(x) else None
    return x


def write_json(name, value):
    (OUT / name).write_text(json.dumps(clean(value), indent=2, allow_nan=False) + "\n")


def save(name, rows, columns=None):
    d = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows, columns=columns)
    d.to_csv(OUT/name, index=False, float_format="%.17g",
        compression={"method":"gzip", "mtime":0} if name.endswith(".gz") else None)
    return d


def textstr(value):
    return "" if pd.isna(value) else str(value)


def selected_indices(meta):
    result = set(meta.get("selected_indices", []))
    result.update(meta.get("selection", {}).get("selected_indices", []))
    for slot in meta.get("slots", []):
        for field in ("asset", "primary"):
            if slot.get(field) is not None: result.add(int(slot[field]))
    return result


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = js(ROOT/"results/RUN_MANIFEST.json")
    freeze = js(ROOT/"docs/EXPERIMENT_FREEZE.json")
    assert manifest["completed_paths"] == manifest["planned_paths"] == 78 and manifest.get("end_utc"), "MATRIX_NOT_COMPLETE"
    assert sha(track(ROOT/"docs/DESIGN_AND_PROTOCOL.md")) == EXPECTED_PROTOCOL == manifest["protocol_sha256"]
    assert freeze["protocol_sha256"] == EXPECTED_PROTOCOL
    assert len(freeze["arms"]) == 13 and len(freeze["scenarios"]) == 6
    for name, value in manifest["input_hashes"].items(): assert sha(track(ROOT/name)) == value
    for name, value in manifest["code_hashes"].items(): assert sha(track(ROOT/name)) == value
    assert manifest["input_hashes"] == freeze["input_hashes"]
    assert manifest["code_hashes"] == freeze["code_hashes"]
    for path in sorted((ROOT/"results").rglob("*")):
        if path.is_file(): track(path)
    with np.load(track(ROOT/"source/data/XETRA_EUR_ETF.npz"), allow_pickle=False) as z:
        panel = {k:z[k] for k in z.files}
    with np.load(track(ROOT/"data/LIQUIDITY.npz"), allow_pickle=False) as z:
        assert np.array_equal(z["dates"], panel["dates"]) and np.array_equal(z["names"], panel["names"])
        liquidity = z["turnover"]
    cover = csv(ROOT/"data/UNIVERSE_COVERAGE.csv").drop_duplicates("isin").set_index("isin")
    series_quarantine = js(ROOT/"data/SOURCE_SERIES_QUARANTINE.json")
    bars_quarantine = js(ROOT/"data/SOURCE_BAR_QUARANTINE.json")
    for name in ("SOURCE_SERIES_QUARANTINE.json","SOURCE_BAR_QUARANTINE.json"):
        assert sha(track(ROOT/"data"/name)) == sha(track(PREVIOUS/"data"/name)), "QUARANTINE_CHANGED"
    track(ROOT/"data/LIQUIDITY_MANIFEST.json")
    old_uses = csv(PREVIOUS/"validation/source_execution/ACTUAL_SOURCE_EVENT_USE.csv")
    old_orders = csv(PREVIOUS/"validation/source_execution/EXECUTION_PARTICIPATION.csv.gz")
    old_catalog = csv(PREVIOUS/"validation/source_execution/SOURCE_EVENT_CATALOGUE.csv")
    old_adjudication = js(PREVIOUS/"validation/source_execution/EVENT_ADJUDICATION.json")
    track(PREVIOUS/"validation/source_execution/audit_source_execution.py")
    track(PREVIOUS/"validation/source_execution/finalize_audit_notes.py")
    old_set = set(zip(old_uses["isin"].astype(str), old_uses.date.astype(str)))
    old_fill_count = old_uses.groupby(["isin","date"]).fill_count.sum().to_dict()
    old_traded = set(old_orders["isin"].astype(str))
    v3 = js(RAW_ROOT/"results/V3_SOURCE_SCOPE_CHECK.json")
    v3_set = {(r["isin"],r["date"]) for r in v3["v3_actual_account_uses_of_existing_flags"]}
    frozen = csv(RAW_ROOT/"superseded_v2/results/V2_HELD_SOURCE_REVIEW.csv")
    track(RAW_ROOT/"data/ADJUSTMENT_ANOMALIES_REVIEW.csv")
    track(RAW_ROOT/"superseded_v2/results/POINT_EVENT_SOURCE_REVIEW.validation.json")
    dates = pd.DatetimeIndex(panel["dates"]); ds = dates.strftime("%Y-%m-%d").to_numpy()
    date_i = {s:k for k,s in enumerate(ds)}; names = panel["names"].astype(str)
    name_i = {s:j for j,s in enumerate(names)}; T = len(dates)
    assert not set(names) & set(series_quarantine)
    paths=[]; traded_all=set(); selected_all=set()
    expected = {f"{a}__{s}" for a in freeze["arms"] for s in freeze["scenarios"]}
    actual = {p.parent.name for p in (ROOT/"results").glob("*/METRICS.json")}
    assert actual == expected, ("MATRIX_MEMBERS", sorted(actual^expected))
    for pid in sorted(expected):
        folder=ROOT/"results"/pid; metric=js(folder/"METRICS.json")
        orders=csv(folder/"ORDERS.csv.gz"); daily=csv(folder/"DAILY.csv.gz")
        decisions=csv(folder/"DECISIONS.csv")
        with np.load(track(folder/"DECISIONS.npz"),allow_pickle=False) as z:
            selected=set(np.flatnonzero(np.any(z["raw_weights"]>EPS,axis=0)))
        meta=[json.loads(s) for s in decisions.meta_json]
        trace=csv(folder/"POLICY_TRACE.csv.gz") if (folder/"POLICY_TRACE.csv.gz").exists() else None
        traded=set(orders.ticker.astype(str)); traded_all |= traded
        for m in meta: selected.update(selected_indices(m))
        if trace is not None:
            for field in ("primary_isin","asset_isin"):
                selected.update(name_i[s] for s in trace[field].dropna().astype(str).unique())
        selected_all.update(names[list(selected)])
        paths.append(dict(pid=pid,folder=folder,metrics=metric,orders=orders,daily=daily,decisions=decisions,
            meta=meta,trace=trace,traded=traded))
    assert traded_all <= set(names) and selected_all <= set(names)
    assert not (traded_all|selected_all)&set(series_quarantine)
    priority=frozen[frozen.symbol.isin(["IQSE.DE","F703.DE","UEQU.DE"])&frozen.positive_volume_gap_flag]
    isins=sorted(traded_all|selected_all|(set(priority["isin"])&set(names)))
    gmap={s:q for q,s in enumerate(isins)}; gj=np.array([name_i[s] for s in isins]); N=len(isins)
    obs=panel["observed"][:,gj]&np.isfinite(panel["C"][:,gj])&(panel["C"][:,gj]>0)
    opobs=panel["open_observed"][:,gj]&np.isfinite(panel["O"][:,gj])&(panel["O"][:,gj]>0)
    O=panel["O"][:,gj]; rawC=panel["C"][:,gj]
    last=np.maximum.accumulate(np.where(obs,np.arange(T)[:,None],-1),axis=0)
    C=np.where(last>=0,rawC[np.maximum(last,0),np.arange(N)[None,:]],np.nan)
    dayn=dates.values.astype("datetime64[D]").astype(int)
    age=np.where(last>=0,dayn[:,None]-dayn[np.maximum(last,0)],-1)
    raw={}; events={}; price_bad=[]; liquidity_bad=[]; rawchecks=[]
    oldflags={s:d.set_index("date") for s,d in frozen[frozen["isin"].isin(isins)].groupby("isin")}
    for s in isins:
        q=gmap[s]; j=name_i[s]; symbol=str(cover.loc[s,"symbol"])
        path=RAW_ROOT/"data/prices"/f"{symbol}.csv.gz"; r=csv(path)
        assert not r.date.duplicated().any(), ("DUPLICATE_RAW_DATE",s)
        r["factor"]=r.adj_close/r.close
        r["factor_return"]=r.factor/r.factor.shift()-1
        r["raw_return"]=r.close/r.close.shift()-1
        r["adjusted_return"]=r.adj_close/r.adj_close.shift()-1
        r["raw_open_jump"]=r.open/r.close.shift()-1
        r["adjusted_open_jump"]=r.adj_open/r.adj_close.shift()-1
        r["intraday_return"]=r.adj_close/r.adj_open-1
        raw[s]=r.set_index("date")
        ralign=raw[s].reindex(ds)
        expected_turnover=(ralign.close*ralign.volume).to_numpy()
        expected_turnover=np.where(obs[:,q]&np.isfinite(expected_turnover)&(expected_turnover>=0),expected_turnover,0.)
        turnover_error=np.abs(liquidity[:,j]-expected_turnover)
        bad=np.flatnonzero(turnover_error>np.maximum(1e-6,np.abs(expected_turnover)*1e-12))
        for k in bad: liquidity_bad.append(dict(isin=s,date=ds[k],error=turnover_error[k]))
        rawchecks.append(dict(isin=s,symbol=symbol,raw_csv_sha256=INPUTS[str(path.resolve())],
            raw_rows=len(r),panel_turnover_rows=T,max_turnover_error=float(turnover_error.max()),
            newly_traded_vs_olc109=s in traded_all and s not in old_traded,
            traded=s in traded_all,selected_or_monitored=s in selected_all))
        for row in r.itertuples(index=False):
            dt=str(row.date)
            if dt not in date_i: continue
            k=date_i[dt]
            if obs[k,q] and (not np.isfinite(row.adj_close) or abs(rawC[k,q]-row.adj_close)>1e-8):
                price_bad.append(dict(isin=s,date=dt,field="Close",panel=rawC[k,q],raw=row.adj_close))
            if opobs[k,q] and (not np.isfinite(row.adj_open) or abs(O[k,q]-row.adj_open)>1e-8):
                price_bad.append(dict(isin=s,date=dt,field="Open",panel=O[k,q],raw=row.adj_open))
            pc=C[k,q]/C[k-1,q]-1 if k and np.isfinite(C[k-1,q]) else np.nan
            po=O[k,q]/C[k-1,q]-1 if k and np.isfinite(C[k-1,q]) else np.nan
            flags=[]
            for yes,label in [(abs(row.factor_return)>.1,"FACTOR_CHANGE_GT10PCT"),
                (abs(row.adjusted_return)>.3,"SOURCE_ADJUSTED_CLOSE_GT30PCT"),
                (abs(row.raw_open_jump)>.3,"SOURCE_RAW_OPEN_JUMP_GT30PCT"),
                (abs(row.adjusted_open_jump)>.3,"SOURCE_ADJUSTED_OPEN_JUMP_GT30PCT"),
                (obs[k,q] and abs(pc)>.3,"ACCEPTED_CLOSE_GT30PCT"),
                (opobs[k,q] and abs(po)>.3,"ACCEPTED_OPEN_JUMP_GT30PCT")]:
                if yes: flags.append(label)
            old=oldflags[s].loc[dt] if s in oldflags and dt in oldflags[s].index else None
            if not flags and old is None: continue
            old_material=old is not None and (bool(old.positive_volume_gap_flag) or old.review_status=="PRIMARY_CORROBORATION_REQUIRED")
            material=bool(flags or old_material)
            close_flag=bool(abs(row.factor_return)>.1 or (obs[k,q] and abs(pc)>=.25))
            open_flag=bool(abs(row.raw_open_jump)>=.25 or abs(row.adjusted_open_jump)>=.25 or (old_material and abs(row.intraday_return)>=.25))
            events[(s,dt)]=dict(isin=s,symbol=symbol,date=dt,k=k,provider_name=str(cover.loc[s,"provider_name"]),
                old_flag=old is not None,frozen_flags=textstr(old.source_flags) if old is not None else "",
                old_review_status=textstr(old.review_status) if old is not None else "",
                primary_evidence_note=textstr(old.primary_evidence_note) if old is not None else "",
                fresh_material_flags="|".join(flags),material=material,
                material_close_component=close_flag,material_open_component=open_flag,
                used_in_prior_v3=(s,dt) in v3_set,used_in_olc109=(s,dt) in old_set,
                prior_olc109_fill_count=int(old_fill_count.get((s,dt),0)),
                raw_open=row.open,raw_close=row.close,adj_open=row.adj_open,adj_close=row.adj_close,
                volume=row.volume,raw_return=row.raw_return,adjusted_return=row.adjusted_return,
                factor_change=row.factor_return,raw_open_jump=row.raw_open_jump,adjusted_open_jump=row.adjusted_open_jump,
                accepted_close_return=pc,accepted_open_jump=po,intraday_return=row.intraday_return,
                close_observed=bool(obs[k,q]),open_observed=bool(opobs[k,q]),
                source_observed=bool(row.observed),valid_geometry=bool(row.valid_geometry),
                dividend=row.dividend,split_ratio=row.split_ratio,source_price_csv=str(path))
    by_isin=defaultdict(list)
    for e in events.values(): by_isin[e["isin"]].append(e)
    pathrows=[]; orderrows=[]; uses=[]; history=[]; stale=[]; fallbackrows=[]; reconstruction=[]; fillbad=[]
    for number,a in enumerate(paths,1):
        pid=a["pid"]; m=a["metrics"]; orders=a["orders"]; daily=a["daily"]
        with np.load(a["folder"]/"DECISIONS.npz",allow_pickle=False) as z:
            snap={key:z[key] for key in ("units","cash","k","raw_weights")}
        mode="CLOSE" if m["scenario"]=="NEXT_CLOSE" else "OPEN"
        assert m["fill"]==mode
        X=rawC if mode=="CLOSE" else O; valid=obs if mode=="CLOSE" else opobs
        units=np.zeros((T,N)); cashflows=np.zeros(T); fills=defaultdict(list); localorders=[]
        for oi,r in orders.iterrows():
            k=int(r.execution_idx);q=gmap[str(r.ticker)];s=str(r.ticker)
            assert ds[k]==r.date==r.execution_date
            units[k,q]+=float(r.quantity)*(1 if r.side=="BUY" else -1)
            cashflows[k]+=(-r.notional-r.cost) if r.side=="BUY" else (r.notional-r.cost)
            fills[(s,k)].append(r)
            rr=raw[s].loc[r.execution_date];turn=float(rr.close*rr.volume)
            participation=float(r.notional/turn) if np.isfinite(turn) and turn>0 else np.nan
            rec=dict(path_id=pid,arm=m["arm"],scenario=m["scenario"],execution_quote=mode,
                order_row=int(oi),isin=s,symbol=str(cover.loc[s,"symbol"]),date=r.date,
                signal_date=r.signal_date,execution_idx=k,signal_idx=int(r.signal_idx),due_idx=int(r.due_idx),
                reason=r.reason,side=r.side,quantity=r.quantity,notional_eur=r.notional,cost_eur=r.cost,
                raw_close=rr.close,raw_volume=rr.volume,raw_day_turnover_eur=turn,
                participation_ratio=participation,ratio_ge_10pct=participation>=.1,ratio_ge_100pct=participation>=1,
                open_observed=bool(opobs[k,q]),close_observed=bool(obs[k,q]),raw_geometry_valid=bool(rr.valid_geometry),
                accepted_execution_price=X[k,q],fill_price=r.price)
            orderrows.append(rec);localorders.append(rec)
            if not valid[k,q] or not np.isfinite(X[k,q]) or abs(r.price-X[k,q])>1e-9:
                fillbad.append(dict(path_id=pid,date=r.date,isin=s,reason="FILL_VS_ACCEPTED_"+mode))
            if rr.volume<=0: fillbad.append(dict(path_id=pid,date=r.date,isin=s,reason="NONPOSITIVE_SOURCE_VOLUME"))
        units=np.cumsum(units,axis=0);cash=10000.+np.cumsum(cashflows)
        before=np.vstack([np.zeros((1,N)),units[:-1]]);cash_before=np.r_[10000.,cash[:-1]]
        ks=daily.k.to_numpy(int);assert np.array_equal(ds[ks],daily.date.to_numpy())
        economic=units[ks]>EPS;values=units[ks]*C[ks]
        stale_mask=economic&(age[ks]>5)
        fallback=(before[ks]>EPS)&~valid[ks]
        prevsource=last[np.maximum(ks-1,0)]
        fbage=dayn[ks,None]-dayn[np.maximum(prevsource,0)]
        for i,q in np.argwhere(stale_mask):
            k=ks[i];stale.append(dict(path_id=pid,scenario=m["scenario"],date=ds[k],isin=isins[q],
                age_days=int(age[k,q]),value_eur=values[i,q],nav_share=values[i,q]/daily.nav_close.iloc[i],source_date=ds[last[k,q]]))
        for i,q in np.argwhere(fallback):
            k=ks[i];fallbackrows.append(dict(path_id=pid,scenario=m["scenario"],execution_quote=mode,date=ds[k],
                isin=isins[q],age_days=int(fbage[i,q]),source_date=ds[prevsource[i,q]],
                value_eur=before[k,q]*C[k-1,q]))
        marks=np.where(valid[ks],X[ks],C[np.maximum(ks-1,0)])
        nav_pre=cash_before[ks]+np.nansum(before[ks]*marks,axis=1)
        nav_close=cash[ks]+np.nansum(units[ks]*C[ks],axis=1)
        dks=snap["k"].astype(int)
        recon=dict(path_id=pid,execution_quote=mode,
            max_units_error=float(np.max(np.abs(units[dks]-snap["units"][:,gj]))),
            max_cash_error=float(np.max(np.abs(cash[dks]-snap["cash"]))),
            max_pretrade_mark_nav_error=float(np.max(np.abs(nav_pre-daily.nav_open))),
            max_close_nav_error=float(np.max(np.abs(nav_close-daily.nav_close))),
            min_cumulative_units=float(units.min()),
            max_numeric_dust_value=float(np.nanmax(np.where((np.abs(units[ks])<=EPS)&(units[ks]!=0),np.abs(values),0.))))
        reconstruction.append(recon)
        localuses=[]
        for s in sorted(a["traded"]):
            q=gmap[s]
            for e in by_isin[s]:
                k=e["k"]
                if k>ks[-1]: continue
                close_ix=ks[(last[ks,q]==k)&(units[ks,q]>EPS)] if obs[k,q] else np.array([],int)
                fb_ix=ks[(~valid[ks,q])&(before[ks,q]>EPS)&(last[np.maximum(ks-1,0),q]==k)] if obs[k,q] else np.array([],int)
                execmark=bool(valid[k,q] and before[k,q]>EPS); fs=fills.get((s,k),[])
                if not (len(close_ix) or len(fb_ix) or execmark or fs): continue
                previous=C[k-1,q] if k else np.nan
                quote=X[k,q] if valid[k,q] else previous
                pre_pnl=before[k,q]*(quote-previous);post_pnl=units[k,q]*(C[k,q]-quote)
                prior_account_nav=cash_before[k]+np.nansum(before[k]*C[k-1]) if k else 10000.
                closeused=bool(len(close_ix) or len(fb_ix) or (mode=="CLOSE" and (execmark or fs)))
                openused=bool(mode=="OPEN" and (execmark or fs))
                rec=dict(path_id=pid,arm=m["arm"],scenario=m["scenario"],execution_quote=mode,**e,
                    units_before=before[k,q],units_after=units[k,q],source_open_used=openused,source_close_used=closeused,
                    execution_mark=execmark,open_mark=bool(mode=="OPEN" and execmark),
                    close_pretrade_mark=bool(mode=="CLOSE" and execmark),close_mark_sessions_including_carry=len(close_ix),
                    execution_fallback_sessions=len(fb_ix),fill_count=len(fs),
                    open_fill_count=len(fs) if mode=="OPEN" else 0,close_fill_count=len(fs) if mode=="CLOSE" else 0,
                    fill_notional_eur=float(sum(r.notional for r in fs)),
                    new_execution_use_vs_olc109=bool(fs and not e["prior_olc109_fill_count"]),
                    new_close_execution_type_vs_olc109=bool(fs and mode=="CLOSE"),
                    pretrade_asset_pnl_eur=pre_pnl,posttrade_asset_pnl_eur=post_pnl,
                    asset_day_pnl_before_costs_eur=pre_pnl+post_pnl,
                    prior_account_nav_eur=prior_account_nav,
                    asset_day_pnl_prior_nav_share=(pre_pnl+post_pnl)/prior_account_nav,
                    material_flagged_component_used=bool((e["material_open_component"] and openused) or
                                                        (e["material_close_component"] and closeused)))
                uses.append(rec);localuses.append(rec)
        # Include every recorded decision and each daily assigned/base-slot
        # monitoring row, not merely monthly positive-weight targets.
        selected_by_k=defaultdict(lambda:defaultdict(set));weight_by_k={}
        for h,k in enumerate(dks):
            for j in np.flatnonzero(snap["raw_weights"][h]>EPS): selected_by_k[int(k)][int(j)].add("POSITIVE_RAW_TARGET")
            for j in selected_indices(a["meta"][h]): selected_by_k[int(k)][int(j)].add("RECORDED_SELECTION_OR_SLOT")
            weight_by_k[int(k)]={int(j):float(snap["raw_weights"][h,j]) for j in np.flatnonzero(snap["raw_weights"][h]>EPS)}
        if a["trace"] is not None:
            for r in a["trace"].itertuples():
                for key in ("primary_index","asset_index"):
                    val=getattr(r,key)
                    if pd.notna(val): selected_by_k[int(r.k)][int(val)].add("DAILY_MONITORED_"+key.upper())
        for k,selection in selected_by_k.items():
            for j,roles in selection.items():
                s=names[j];q=gmap[s]
                oldest_source=last[max(0,k-252),q]
                for e in by_isin[s]:
                    ek=e["k"]
                    if not e["material"] or not e["close_observed"] or not max(0,oldest_source)<=ek<=k: continue
                    endpoints=[h for h in (0,1,5,10,21,63,126,252) if k>=h and last[k-h,q]==ek]
                    windows={f"in_sma{h}":bool(last[max(0,k-h+1),q]<=ek<=k) for h in (10,21,63,200)}
                    history.append(dict(path_id=pid,arm=m["arm"],scenario=m["scenario"],isin=s,symbol=e["symbol"],
                        date=e["date"],signal_date=ds[k],signal_idx=k,roles="|".join(sorted(roles)),
                        raw_target_weight=weight_by_k.get(k,{}).get(j,np.nan),
                        signal_close_observed=bool(obs[k,q]),source_flags=e["frozen_flags"],fresh_material_flags=e["fresh_material_flags"],
                        material_close_component=e["material_close_component"],material_open_component=e["material_open_component"],
                        accepted_close_feature_endpoint_horizons="|".join(map(str,endpoints)),
                        in_sigma21_price_window=bool(last[max(0,k-21),q]<=ek<=k),
                        in_corr126_price_window=bool(last[max(0,k-126),q]<=ek<=k),**windows))
        ratios=np.array([r["participation_ratio"] for r in localorders]); ages=age[ks][economic];fbages=fbage[fallback]
        pathrows.append(dict(path_id=pid,arm=m["arm"],scenario=m["scenario"],execution_quote=mode,
            cagr=m["cagr"],end_equity=m["end_equity"],mean_exposure=m["mean_exposure"],orders=len(orders),
            traded_isins=len(a["traded"]),new_traded_isins_vs_olc109=len(a["traded"]-old_traded),
            held_asset_sessions=int(economic.sum()),maximum_held_close_age_days=int(ages.max()) if len(ages) else 0,
            stale_asset_sessions_gt5=int(stale_mask.sum()),execution_fallback_asset_sessions=int(fallback.sum()),
            maximum_execution_fallback_close_age_days=int(fbages.max()) if len(fbages) else 0,
            execution_fallback_asset_sessions_gt5=int((fbages>5).sum()),
            invalid_participation_denominators=int((~np.isfinite(ratios)).sum()),
            invalid_geometry_participation_denominators=sum(not r["raw_geometry_valid"] for r in localorders),
            orders_participation_ge10pct=int((ratios>=.1).sum()),orders_participation_ge100pct=int((ratios>=1).sum()),
            maximum_participation_ratio=float(np.nanmax(ratios)) if len(ratios) else 0,
            direct_source_event_uses=len(localuses),new_source_event_uses_vs_olc109=sum(not r["used_in_olc109"] for r in localuses),
            material_component_event_uses=sum(r["material_flagged_component_used"] for r in localuses)))
        if number%13==0: print(f"Source audit {number}/78 paths",flush=True)
    ps=save("PATH_SOURCE_EXECUTION_SUMMARY.csv",pathrows)
    od=save("EXECUTION_PARTICIPATION.csv.gz",orderrows)
    ed=save("SOURCE_EVENT_CATALOGUE.csv",sorted(events.values(),key=lambda e:(e["isin"],e["date"])))
    eu=save("ACTUAL_SOURCE_EVENT_USE.csv",uses)
    hd=save("SELECTED_FEATURE_HISTORY_MATERIAL_FLAGS.csv",history)
    rc=save("RECONSTRUCTION_CHECKS.csv",reconstruction)
    save("HELD_STALENESS_EVENTS.csv.gz",stale,columns=["path_id","scenario","date","isin","age_days","value_eur","nav_share","source_date"])
    save("EXECUTION_FALLBACK_MARKS.csv.gz",fallbackrows)
    save("RAW_SOURCE_LIQUIDITY_CHECKS.csv",rawchecks)
    save("LARGEST_EXECUTION_PARTICIPATION.csv",od.nlargest(50,"participation_ratio"))
    new_isins=[]
    for s in sorted(traded_all-old_traded):
        oo=od[od["isin"]==s]
        new_isins.append(dict(isin=s,symbol=cover.loc[s,"symbol"],name=cover.loc[s,"provider_name"],orders=len(oo),
            paths=oo.path_id.nunique(),first_execution=oo.date.min(),last_execution=oo.date.max(),
            material_event_uses=sum(r["isin"]==s and r["material"] for r in uses)))
    save("NEW_TRADED_ISINS_VS_OLC109.csv",new_isins,columns=["isin","symbol","name","orders","paths","first_execution","last_execution","material_event_uses"])
    priorityrows=[]
    for r in priority.itertuples():
        if r.date not in date_i or r.isin not in gmap: continue
        uu=eu[(eu["isin"]==r.isin)&(eu.date==r.date)]
        hh=hd[(hd["isin"]==r.isin)&(hd.date==r.date)]
        k=date_i[r.date];q=gmap[r.isin]
        priorityrows.append(dict(isin=r.isin,symbol=r.symbol,date=r.date,traded_any_date=r.isin in traded_all,
            open_observed=bool(opobs[k,q]),close_observed=bool(obs[k,q]),direct_event_paths=len(uu),
            source_open_use_paths=int(uu.source_open_used.sum()),source_close_use_paths=int(uu.source_close_used.sum()),
            open_fills=int(uu.open_fill_count.sum()),close_fills=int(uu.close_fill_count.sum()),history_rows=len(hh)))
    save("PRIORITY_OPEN_EVENT_CHECKS.csv",priorityrows)
    unique_used=set(zip(eu["isin"],eu.date));new_used=unique_used-old_set
    new_material=sorted(key for key in new_used if events[key]["material"])
    new_types=eu[eu.new_execution_use_vs_olc109|eu.new_close_execution_type_vs_olc109]
    save("NEW_EVENT_EXECUTION_TYPES_VS_OLC109.csv",new_types)
    errors=bool(fillbad or price_bad or liquidity_bad or rc.max_close_nav_error.max()>1e-6 or
        rc.max_pretrade_mark_nav_error.max()>1e-6 or rc.max_units_error.max()>1e-7 or rc.max_cash_error.max()>1e-6)
    status="FAIL_SOURCE_OR_ACCOUNT_RECONSTRUCTION" if errors else "BOUNDED_CHECKS_PASS_EVENT_ADJUDICATION_PENDING"
    # Detect any mutation during the read-only audit, including financial result files.
    changed=[path for path,value in INPUTS.items() if sha(path)!=value]
    assert not changed, ("INPUT_CHANGED_DURING_AUDIT",changed)
    summary=dict(status=status,created_utc=datetime.now(timezone.utc).isoformat(),paths_checked=len(paths),
        matrix_complete=True,protocol_sha256=EXPECTED_PROTOCOL,primary_arm="EXIT21_STAGED_FRESHW",
        scenarios=freeze["scenarios"],arms=freeze["arms"],panel_assets=len(names),panel_sessions=T,
        orders_checked=len(od),actual_traded_isins=len(traded_all),selected_or_monitored_isins=len(selected_all),
        scanned_instruments=len(isins),new_traded_isins_vs_olc109=sorted(traded_all-old_traded),
        source_event_catalogue_rows=len(ed),material_source_event_rows=int(ed.material.sum()),
        source_event_path_uses=len(eu),unique_source_events_used=len(unique_used),
        new_unique_source_events_used_vs_olc109=[list(key) for key in sorted(new_used)],
        new_unique_material_source_events_used_vs_olc109=[list(key) for key in new_material],
        selected_material_history_rows=len(hd),invalid_fill_source_events=fillbad,
        accepted_panel_raw_mismatches=price_bad,liquidity_mismatches=liquidity_bad,
        max_units_reconstruction_error=rc.max_units_error.max(),max_cash_reconstruction_error=rc.max_cash_error.max(),
        max_pretrade_mark_nav_error=rc.max_pretrade_mark_nav_error.max(),max_close_nav_reconstruction_error=rc.max_close_nav_error.max(),
        max_numeric_dust_value=rc.max_numeric_dust_value.max(),
        maximum_held_close_age_days=int(ps.maximum_held_close_age_days.max()),stale_asset_path_sessions_gt5=len(stale),
        maximum_execution_fallback_close_age_days=int(ps.maximum_execution_fallback_close_age_days.max()),
        execution_fallback_asset_sessions_gt5=int(ps.execution_fallback_asset_sessions_gt5.sum()),
        orders_participation_ge10pct=int(od.ratio_ge_10pct.sum()),orders_participation_ge100pct=int(od.ratio_ge_100pct.sum()),
        maximum_participation_ratio=od.participation_ratio.max(),invalid_participation_denominators=int(ps.invalid_participation_denominators.sum()),
        invalid_geometry_participation_denominators=int(ps.invalid_geometry_participation_denominators.sum()),
        quarantined_panel_hits=sorted(set(names)&set(series_quarantine)),quarantined_order_hits=sorted(traded_all&set(series_quarantine)),
        quarantine_hashes_unchanged=True,input_and_result_sha256=INPUTS,audit_script_sha256=sha(__file__),
        scope_limits=["No strategy or engine import, new simulation, source repair, outcome-based deletion, download, or external mutation.",
            "NEXT_CLOSE uses accepted Close quotes; nav_open is its pre-fee Close mark. NEXT_CLOSE does not observe Open or intraday drawdown.",
            "Participation divides EUR notional by the venue's full-day raw Close times volume; neither opening nor closing auction capacity is certified.",
            "Source histories cover traded and recorded-selected/monitored identities plus priority events, not every rejected contender or the entire fund catalogue.",
            "Daily slot lineage is broader than prior OLC109 monthly-only selected-history joins; counts are not directly comparable.",
            "Selected history is potential source lineage, not a measured causal ranking effect. Open-only anomalies do not contaminate normal Close-based features by identity alone.",
            "Current catalogue, missing delisted funds, retrospective adjustment factors, and completed-day volume gating retain the original point-in-time limitations.",
            "Related scenarios and paths repeat economic events; pooled order counts are not independent samples."])
    write_json("SOURCE_EXECUTION_AUDIT.json",summary)
    print(json.dumps(clean({k:summary[k] for k in ("status","paths_checked","orders_checked","actual_traded_isins",
        "new_traded_isins_vs_olc109","max_pretrade_mark_nav_error","max_close_nav_reconstruction_error",
        "maximum_held_close_age_days","orders_participation_ge10pct","orders_participation_ge100pct",
        "maximum_participation_ratio","new_unique_material_source_events_used_vs_olc109")}),indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.parse_args();run()
