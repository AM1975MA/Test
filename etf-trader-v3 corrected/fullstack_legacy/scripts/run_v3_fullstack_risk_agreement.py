#!/usr/bin/env python3
"""V3 full-stack isolated risk-sleeve experiment: original ETF_TRAINER_V2 producer agreement versus added V3 Pair127 confirmation.

The productive DAG is restricted to raw ETF OHLCV, universe/category metadata,
and repository source. Canonical 500x24 baskets are regenerated deterministically
from universe metadata; historical basket membership, dynamic cluster membership,
scores, paths, models, and checkpoint metrics are not consumed.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.baskets import build_canonical_baskets, BASKET_SEED
from etf_trader.ma3 import producer, ddfirst, v6, highcagr24
from etf_trader.ma3.ensemble import fit_ensemble_producer, ET_KW, XGB_KW, XGB_ALPHA

CANONICAL_BASKET_SHA256 = "36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for block in iter(lambda: fp.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def aggregate_sha256(paths: list[Path], base: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(paths, key=lambda p: str(p.relative_to(base)).lower()):
        rel = str(path.relative_to(base)).replace("\\", "/")
        h.update(rel.encode("utf-8")); h.update(b"\0")
        h.update(sha256(path).encode("ascii")); h.update(b"\n")
    return h.hexdigest()


def run(cmd: list[str]) -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def environment_identity() -> dict[str, str]:
    packages = {}
    for name in ("numpy", "pandas", "scikit-learn", "xgboost", "numba", "pyarrow"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "NOT_INSTALLED"
    return {"python": platform.python_version(), **packages}


def metrics(equity: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    lr = np.diff(np.log(np.column_stack([np.ones(equity.shape[0]), equity])), axis=1)[:, mask]
    r = np.expm1(lr)
    n = lr.shape[1]
    cagr = np.expm1(lr.sum(axis=1) * 252 / n)
    eq = np.exp(np.cumsum(lr, axis=1))
    peak = np.maximum.accumulate(np.column_stack([np.ones(equity.shape[0]), eq]), axis=1)[:, 1:]
    dd = (eq / peak - 1).min(axis=1)
    sd = r.std(axis=1, ddof=1)
    sharpe = np.divide(r.mean(axis=1) * np.sqrt(252), sd, out=np.zeros_like(sd), where=sd > 0)
    return {
        "cagr": float(cagr.mean()),
        "median_cagr": float(np.median(cagr)),
        "p10_cagr": float(np.quantile(cagr, .10)),
        "p05_cagr": float(np.quantile(cagr, .05)),
        "maxdd": float(dd.mean()),
        "p10dd": float(np.quantile(dd, .10)),
        "p05dd": float(np.quantile(dd, .05)),
        "worst": float(dd.min()),
        "sharpe": float(sharpe.mean()),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--raw", help="prepared universe.csv + per-ticker OHLCV CSV directory")
    src.add_argument("--matrix-dir", help="OPEN/HIGH/LOW/CLOSE/VOLUME parquet directory")
    ap.add_argument("--universe", default="data/ETF_UNIVERSE.csv",
                    help="universe/category metadata used with --matrix-dir")
    ap.add_argument("--output", default="artifact/ma3_highcagr24_ensemble_source_only")
    ap.add_argument("--n-jobs", type=int, default=2)
    ap.add_argument("--xgb-workers", type=int, default=3)
    ap.add_argument("--xgb-threads-per-worker", type=int, default=1)
    ap.add_argument("--v3-pair-scores", required=True, help="frozen 2018+ CORRECTED OOS scores, not outcomes")
    args = ap.parse_args()

    out = Path(args.output)
    if not out.is_absolute():
        out = ROOT / out
    if out.exists() and any(out.iterdir()):
        raise RuntimeError(f"output is non-empty: {out}; clean-room run requires an empty directory")
    out.mkdir(parents=True, exist_ok=True)

    if args.matrix_dir:
        raw = out / "raw_ticker_csv"
        universe = Path(args.universe)
        if not universe.is_absolute():
            universe = (ROOT / universe).resolve()
        run([
            sys.executable, str(ROOT / "scripts/prepare_matrix_raw_to_ticker_csv.py"),
            "--matrix-dir", str(Path(args.matrix_dir).resolve()),
            "--universe", str(universe),
            "--output", str(raw),
        ])
        matrix_files = [Path(args.matrix_dir).resolve() / f"{x}.parquet" for x in ("OPEN", "HIGH", "LOW", "CLOSE", "VOLUME")]
        raw_identity = {
            "mode": "matrix_parquet",
            "files": {p.name: sha256(p) for p in matrix_files},
            "universe_sha256": sha256(universe),
        }
    else:
        raw = Path(args.raw).resolve()
        files = sorted(raw.glob("*.csv"))
        raw_identity = {
            "mode": "ticker_csv",
            "file_count": len(files),
            "aggregate_sha256": aggregate_sha256(files, raw),
        }

    mats, cats, raw_manifest = load_ticker_csv_folder(raw)
    tickers = list(map(str, mats["Open"].columns))
    ti = {t: i for i, t in enumerate(tickers)}
    for required in ("SPY", "BIL", "SHV"):
        if required not in ti:
            raise RuntimeError(f"{required} missing from raw universe")

    # Canonical baskets are generated from source logic, not loaded from membership history.
    universe_meta = pd.read_csv(raw / "universe.csv")
    membership = build_canonical_baskets(universe_meta, tickers)
    basket_path = out / "GENERATED_CANONICAL_BASKETS.csv"
    membership.to_csv(basket_path, index=False)
    basket_sha = sha256(basket_path)
    if basket_sha != CANONICAL_BASKET_SHA256:
        raise RuntimeError(f"basket reconstruction parity failed: {basket_sha}")

    # Fresh upstream DAG inside this run.
    tit = out / "titanium"
    panel_dir = out / "ma3_panel"
    run([
        sys.executable, str(ROOT / "scripts/build_tit_r_source_only.py"),
        "--data", str(raw), "--output", str(tit),
        "--xgb-workers", str(args.xgb_workers),
        "--xgb-threads-per-worker", str(args.xgb_threads_per_worker),
    ])
    run([
        sys.executable, str(ROOT / "scripts/build_ma3_panel_source_only.py"),
        "--data", str(raw), "--cluster-data", str(raw), "--output", str(panel_dir),
    ])

    # Explicit causal audits of freshly generated upstream state.
    titanium_audit_records = 0
    titanium_maturity_safe = True
    for path in sorted((tit / "annual_models").glob("fit_audit_*.json")):
        for row in json.loads(path.read_text(encoding="utf-8")):
            titanium_audit_records += 1
            titanium_maturity_safe &= pd.Timestamp(row["max_exit"]) < pd.Timestamp(row["fit_date"])
    cluster_audit = pd.read_csv(panel_dir / "CLUSTER_SOURCE_DATE_AUDIT.csv")
    cluster_source_causal = bool(
        (pd.to_datetime(cluster_audit["window_end"]) <= pd.to_datetime(cluster_audit["signal_date"])).all()
        and cluster_audit["max_source_date_le_signal"].all()
        and cluster_audit["matching_used_only_previous_membership"].all()
    )
    if not titanium_maturity_safe or not cluster_source_causal:
        raise RuntimeError("fresh upstream causal audit failed")

    tit_df = pd.read_csv(tit / "TIT_R_SOURCE_ONLY.csv", parse_dates=["signal_date", "entry_date", "exit_date"])
    panel = pd.read_pickle(panel_dir / "RAW_FEATURE_PANEL.pkl")
    t0 = time.time()
    p = fit_ensemble_producer(panel, tit_df, tickers, n_jobs=args.n_jobs)
    fit_seconds = time.time() - t0
    if not bool(p.fit_audit["maturity_ok"].all()):
        raise RuntimeError("ensemble maturity audit failed")
    p.predictions.to_csv(out / "ENSEMBLE_TAIL_OOS.csv", index=False)
    # One preregistered variable: 25% frozen V3 Pair127 ranked score
    # substitutes for V2 original Titanium BASE, before the same Hybrid24
    # tail smoothing, dynamic Top2, DD-first, V6 and HighCAGR24.
    # Do not read prospective target or label columns from V3 inputs.
    v3 = pd.read_csv(args.v3_pair_scores, parse_dates=["signal_date"])
    assert set(["signal_date","ticker","variant","pred"]).issubset(v3)
    v3 = v3.loc[v3.variant.eq("CORRECTED"),["signal_date","ticker","pred"]].copy()
    assert len(v3) == 149 * 102
    assert v3.ticker.nunique() == 149 and v3.signal_date.nunique() == 102
    assert not v3.duplicated(["signal_date","ticker"]).any()
    if not np.isfinite(v3.pred.to_numpy(float)).all():
        raise ValueError("V3 frozen score contains nonfinite signal")
    caldates = list(pd.to_datetime(p.calendar["signal_date"]))
    assert p.score.shape == p.base.shape == (len(caldates), len(tickers))
    if not np.isfinite(p.score).all() or not np.isfinite(p.base).all():
        raise ValueError("V2 base and tail must be finite")
    by_date = {pd.Timestamp(day):grp for day,grp in v3.groupby("signal_date")}
    new_base = np.asarray(p.base,dtype=float).copy()
    pair_rank_full = np.asarray(p.base,dtype=float).copy()
    pair_available=np.zeros(len(caldates),dtype=bool)
    upgraded_dates=[]
    for idx, day in enumerate(caldates):
        if day not in by_date:continue # V2 unchanged if no V3 OOS data
        grp=by_date[day]
        ranked=grp.set_index("ticker")["pred"].rank(method="average",pct=True)
        if not ranked.index.is_unique or set(ranked.index)!=set(tickers):
            raise AssertionError("V3 ticker universe mismatch on "+str(day))
        v3_rank=ranked.reindex(tickers).to_numpy(float)
        assert np.isfinite(v3_rank).all()
        new_base[idx]=.75*p.base[idx]+.25*v3_rank
        pair_rank_full[idx]=v3_rank
        pair_available[idx]=True
        upgraded_dates.append(str(day.date()))
    assert len(upgraded_dates)>=95 and upgraded_dates[0]>="2018-01-01"
    v3_score = p.score + .475*(new_base-p.base)
    assert np.isfinite(v3_score).all()
    assert np.allclose(v3_score[:len(caldates)-len(upgraded_dates)],
                       p.score[:len(caldates)-len(upgraded_dates)], atol=0,rtol=0)
    pd.DataFrame({"signal_date":caldates,
        "v3_causal_oos_available":[str(d.date()) in set(upgraded_dates) for d in caldates],
        "original_base_mean":p.base.mean(axis=1),
        "new_base_mean":new_base.mean(axis=1),
        "original_final_score_mean":p.score.mean(axis=1),
        "v3_final_score_mean":v3_score.mean(axis=1)}).to_csv(
            out/"V3_BASE_FUSION_AUDIT.csv",index=False)
    p.fit_audit.to_csv(out / "ENSEMBLE_FIT_AUDIT.csv", index=False)

    BM, BOK = producer.basket_arrays(membership, tickers, n_baskets=500)
    Odf = mats["Open"].reindex(columns=tickers).ffill().bfill()
    Ldf = mats["Low"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    Cdf = mats["Close"].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)

    end = pd.Timestamp(p.calendar["exit_date"].max())
    start = pd.Timestamp(p.calendar["entry_date"].min())
    Odf = Odf.loc[:end]; Ldf = Ldf.reindex(Odf.index); Cdf = Cdf.reindex(Odf.index)
    st = int(Odf.index.get_loc(start)); en = int(Odf.index.get_loc(end)); ds = Odf.index[st:en + 1]

    gross = np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en + 1], dtype=float)
    ex = ddfirst.daily_execution_inputs(Odf, Ldf, Cdf)
    O, L, C, PC, gap, ud1, uneg, UH, SA = [ex[k][st:en + 1] for k in ("O", "L", "C", "PC", "gap", "ud1", "uneg", "UH", "SA")]
    alloc = producer.allocations_from_score(p.score, p.calendar, ds, BM, BOK, continuous=True)
    alloc_v3 = producer.allocations_from_score(v3_score, p.calendar, ds, BM, BOK, continuous=True)
    assert alloc_v3.d1.shape == alloc.d1.shape == (500,len(ds))
    assert np.all((alloc_v3.weight1>=0)&(alloc_v3.weight1<=1))
    noalt = np.full_like(alloc.d1, -1, np.int16)
    ones = np.ones(len(ds), dtype=float)

    Eraw, Traw, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], ones, noalt, False, .001,
    )
    s6 = v6.build_v6_state(Cdf.loc[ds, tickers], alloc.d1, alloc.d2, alloc.weight1, gross)
    Edd, Tdd, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross, noalt, False, .001,
    )
    Ev6, Tv6, _, _ = v6.simulate_with_alt(
        alloc.d1, alloc.d2, alloc.weight1, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross, s6.alt_idx, True, .001,
    )
    gross24, weight24 = highcagr24.apply_highcagr24(gross, alloc.weight1, alloc.margin)
    E24, T24, X24, Aw24 = v6.simulate_with_alt(
        alloc.d1, alloc.d2, weight24, O, L, C, PC, gap, ud1, uneg, UH, SA,
        ti["BIL"], ti["SHV"], gross24, s6.alt_idx, True, .001,
    )
    # The same risk states and physics as V2, recomputed per selected names.
    v6_state_v3=v6.build_v6_state(Cdf.loc[ds, tickers],
        alloc_v3.d1,alloc_v3.d2,alloc_v3.weight1,gross)
    gross_v3,weight_v3=highcagr24.apply_highcagr24(
        gross,alloc_v3.weight1,alloc_v3.margin)
    Ev3,Tv3,Xv3,Awv3=v6.simulate_with_alt(
        alloc_v3.d1,alloc_v3.d2,weight_v3,O,L,C,PC,gap,ud1,uneg,UH,SA,
        ti["BIL"],ti["SHV"],gross_v3,v6_state_v3.alt_idx,True,.001)
    assert E24.shape == Ev3.shape == (500,len(ds))
    assert np.isfinite(Ev3).all() and np.isfinite(Tv3).all()

    # Original ETF_TRAINER_V2 risk-sleeve conviction action, with all actual
    # original baseline V2 final holdings and source-generated ET / XGB scores.
    et=(p.predictions.pivot(index="signal_date",columns="ticker",values="ET_TAIL")
             .reindex(index=caldates,columns=tickers).to_numpy(float))
    xgb=(p.predictions.pivot(index="signal_date",columns="ticker",values="XGB_TAIL")
             .reindex(index=caldates,columns=tickers).to_numpy(float))
    assert et.shape==xgb.shape==p.base.shape
    assert np.isfinite(et).all() and np.isfinite(xgb).all()
    agree_models=np.zeros_like(alloc.d1,dtype=bool)
    agree_three=np.zeros_like(alloc.d1,dtype=bool)
    for m,row in enumerate(p.calendar.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)))
        e=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=len(ds) or e<=a:continue
        first=alloc.d1[:,a].astype(int)
        second=alloc.d2[:,a].astype(int)
        assert np.all(first>=0) and np.all(second>=0)
        agreed=(et[m,first]>et[m,second])&(xgb[m,first]>xgb[m,second])
        agreed_v3=agreed & ((pair_rank_full[m,first]>pair_rank_full[m,second]) if pair_available[m] else True)
        agree_models[:,a:e]=agreed[:,None]
        agree_three[:,a:e]=agreed_v3[:,None]
    riskoff=(gross24[None,:]<.999)
    eligible=riskoff&(alloc.margin>=.03)
    action_v2=eligible&agree_models
    action_v3=eligible&agree_three
    assert np.all(~action_v3|action_v2) # third confirmation strict subset
    w_stage19=weight24.copy()
    w_stage19[action_v2]=1.0
    w_v3confirm=weight24.copy()
    w_v3confirm[action_v3]=1.0
    assert np.allclose(gross24,gross_v3)  # the same macro gross independent of picks
    E_stage19,T_stage19,_,_=v6.simulate_with_alt(
        alloc.d1,alloc.d2,w_stage19,O,L,C,PC,gap,ud1,uneg,UH,SA,
        ti["BIL"],ti["SHV"],gross24,s6.alt_idx,True,.001)
    E_v3confirm,T_v3confirm,_,_=v6.simulate_with_alt(
        alloc.d1,alloc.d2,w_v3confirm,O,L,C,PC,gap,ud1,uneg,UH,SA,
        ti["BIL"],ti["SHV"],gross24,s6.alt_idx,True,.001)
    assert E_stage19.shape==E_v3confirm.shape==E24.shape
    assert np.isfinite(E_stage19).all() and np.isfinite(E_v3confirm).all()
    pd.DataFrame({"date":ds,
       "riskoff_fraction":riskoff[0].astype(float),
       "risk_eligible_baskets":eligible.sum(axis=0),
       "et_xgb_agreement_actions_baskets":action_v2.sum(axis=0),
       "three_model_confirmed_actions_baskets":action_v3.sum(axis=0)}).to_csv(
       out/"MODEL_AGREEMENT_DAILY_AUDIT.csv",index=False)

    periods = {
        "pre2020": ds < pd.Timestamp("2020-01-01"),
        "2020_2022": (ds >= pd.Timestamp("2020-01-01")) & (ds < pd.Timestamp("2023-01-01")),
        "dev_daily": ds < pd.Timestamp("2023-01-01"),
        "holdout_daily": ds >= pd.Timestamp("2023-01-01"),
        "full": np.ones(len(ds), dtype=bool),
        "common2018plus": ds>=pd.Timestamp("2018-02-01"),
        "common2022plus": ds>=pd.Timestamp("2022-02-01"),
    }
    result = {
        "status": "SOURCE_ONLY_ENSEMBLE_REBUILD_COMPLETE",
        "certification": "CLEAN_CURRENT_RAW_PASS",
        "selection": {
            "extra_trees": "configuration selected on 2011-2016 walk-forward",
            "xgb": "configuration selected on 2011-2016 engine benchmark",
            "alpha_xgb": {"value": XGB_ALPHA, "selected_on": "2017-2022 validation only"},
            "holdout": "2023-2026 not used for parameter selection",
        },
        "producer": {
            "target": "0.45*r21^1.5 + 0.35*r42^1.5 + 0.20*r63^1.5",
            "extra_trees": ET_KW,
            "xgb": XGB_KW,
            "alpha_xgb": XGB_ALPHA,
            "tail_smoothing": [0.40, 0.30, 0.30],
            "tail_power": 1.10,
            "base_tail": [0.475, 0.525],
        },
        "fit_seconds": fit_seconds,
        "calendar": {"start": str(ds.min().date()), "end": str(ds.max().date()), "days": int(len(ds))},
        "metrics": {},
        "risk_sleeve_agreement":{
            "original_ETF_TRAINER_V2_action":"Risk-off gross <1 plus original Top1/2 margin >=.03 plus ET/XGB original agreement",
            "v3_added_condition":"Frozen V3 Pair127 as third confirmation of same original Top1/2, no new ranking",
            "gross_and_v6_risk_reference_identical":True,
            "all_riskoff_proposals_asof":int(eligible.sum()),
            "ETF_TRAINER_V2_risk_sleeve_actions_asof":int(action_v2.sum()),
            "V3_three_model_risk_sleeve_actions_asof":int(action_v3.sum()),
            "v3_actions_strict_subset":True,
            "no_frozen_ranker_refit":True},
        "v3_pair25": {"source_run":39700865721,
            "predeclared_fraction_of_v2_base":0.25,
            "v2_base_fraction":0.75,
            "original_tail_and_smoothing_unchanged":True,
            "ddfirst_v6_highcagr24_all_enabled":True,
            "v3_updated_months":len(upgraded_dates),
            "v3_first_signal":upgraded_dates[0],
            "v3_last_signal":upgraded_dates[-1]},
        "turnover_ann": {
            "raw": float(Traw.mean() * 252),
            "ddfirst": float(Tdd.mean() * 252),
            "v6": float(Tv6.mean() * 252),
            "highcagr24": float(T24.mean() * 252),
        },
        "contract": {
            "productive_inputs": ["raw ETF OHLCV", "universe/category metadata", "repository source"],
            "historical_scores_consumed": False,
            "historical_paths_consumed": False,
            "historical_cluster_membership_consumed": False,
            "historical_basket_membership_consumed": False,
            "basket_membership_generated_from_source": True,
            "basket_seed": BASKET_SEED,
            "basket_sha256": basket_sha,
            "cluster_seed": 26072026,
            "titanium_maturity_safe": bool(titanium_maturity_safe),
            "titanium_audit_records": titanium_audit_records,
            "cluster_source_causal": bool(cluster_source_causal),
            "ensemble_maturity_safe": bool(p.fit_audit["maturity_ok"].all()),
        },
        "raw_identity": raw_identity,
        "raw_manifest": raw_manifest,
        "environment": environment_identity(),
    }
    for name, mask in periods.items():
        result["metrics"][name] = {
            "raw": metrics(Eraw, mask),
            "ddfirst": metrics(Edd, mask),
            "v6": metrics(Ev6, mask),
            "highcagr24": metrics(E24, mask),
            "v3_hybrid_pair25": metrics(Ev3, mask),
            "etf_trainer_v2_risk_conviction": metrics(E_stage19, mask),
            "v3_three_model_risk_conviction": metrics(E_v3confirm, mask),
        }

    (out / "RESULT.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    np.savez_compressed(
        out / "PATH.npz",
        dates=ds.values, equity=E24, turnover=T24, exposure=X24, alt_weight=Aw24,
        d1=alloc.d1, d2=alloc.d2, wg=weight24, margin=alloc.margin,
        v3_equity=Ev3, v3_turnover=Tv3, v3_d1=alloc_v3.d1,
        etf_trainer_v2_equity=E_stage19, v3_three_model_equity=E_v3confirm,
        etf_trainer_v2_turnover=T_stage19,v3_three_model_turnover=T_v3confirm,
        v3_d2=alloc_v3.d2, v3_wg=weight_v3, v3_margin=alloc_v3.margin,
        global_gross=gross24, alt_idx=s6.alt_idx, tickers=np.asarray(tickers, dtype=object),
    )
    print(json.dumps({
        "status": result["status"],
        "full_highcagr24": result["metrics"]["full"]["highcagr24"],
        "holdout_highcagr24": result["metrics"]["holdout_daily"]["highcagr24"],
        "turnover_ann": result["turnover_ann"]["highcagr24"],
        "v3_pair25_full":result["metrics"]["full"]["v3_hybrid_pair25"],
        "v2_original_full":result["metrics"]["full"]["highcagr24"],
        "v3_pair25_common2018":result["metrics"]["common2018plus"]["v3_hybrid_pair25"],
        "v2_original_common2018":result["metrics"]["common2018plus"]["highcagr24"],
        "v2_trainer_conviction_full":result["metrics"]["full"]["etf_trainer_v2_risk_conviction"],
        "v3_three_model_conviction_full":result["metrics"]["full"]["v3_three_model_risk_conviction"],
        "v2_trainer_conviction_later":result["metrics"]["holdout_daily"]["etf_trainer_v2_risk_conviction"],
        "v3_three_model_conviction_later":result["metrics"]["holdout_daily"]["v3_three_model_risk_conviction"],
        "contract": result["contract"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
