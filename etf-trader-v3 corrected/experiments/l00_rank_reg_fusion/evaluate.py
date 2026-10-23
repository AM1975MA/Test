#!/usr/bin/env python3
"""L00 controlled feature and regression ablations, same frozen 149 ETF / 500 baskets.

Research ONLY: chronological annual refits on fully matured 21-day outcomes.
Original Compact125 and previous V2/production are NEVER modified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from xgboost import XGBRanker, XGBRegressor

HERE = Path(__file__).resolve().parent
V3 = HERE.parents[1]
ROOT = V3.parent
sys.path.insert(0, str(V3 / "experiments" / "l00_cs_add171"))
sys.path.insert(0, str(V3 / "src"))
import importlib.util
_source = V3 / "experiments" / "l00_cs_add171" / "evaluate.py"
_spec = importlib.util.spec_from_file_location("cs2_eval_reference", _source)
_reference = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reference)
freeze_data = _reference.freeze_data
scores_for_month = _reference.scores_for_month
v3 = _reference.v3
SEEDS = _reference.SEEDS
BASKET_SHA = _reference.BASKET_SHA
from normalize import normalize_same_day, unit_contract
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

VOL_BASE = {
    "vol21", "vol63", "vol126", "downvol21", "downvol63",
    "downvol126", "vol_ratio_21_126", "gkvol21",
}
ALL = list(v3.F2D_FEATURES)
NO_VOL = [c for c in ALL if c.split("_pct")[0].split("_dev")[0] not in VOL_BASE]
FEATURE_ARMS = ("CS_ADD250_MINMAX", "CS_ADD250_ROBUST",
                "VOL_TREND_RESID", "VOL_MARKET_RESID")
REG_ARMS = ("REG_REL125", "REG_REL101", "REG_ABS125", "REG_ABS101",
            "REG_HUBER125")

def robust_date_z(df: pd.DataFrame, names: list[str]) -> pd.DataFrame:
    out = df.copy()
    for name in names:
        x = pd.to_numeric(df[name], errors="raise").replace([np.inf, -np.inf], np.nan)
        group = df["signal_date"]
        median = x.groupby(group, sort=False).transform("median")
        mad = (x - median).abs().groupby(group, sort=False).transform("median")
        z = ((x - median) / (1.4826 * mad.replace(0, np.nan))).clip(-5, 5) / 5
        # Degenerate groups are deliberately neutral; original NaNs remain NaN.
        out[name] = z.where(mad.gt(0), 0.0).where(x.notna())
    return out

def add_volatility_features(panel: pd.DataFrame, raw_dir: str) -> pd.DataFrame:
    mats, cats, _ = load_ticker_csv_folder(raw_dir)
    assert len(cats) == 149
    C = mats["Close"].loc[mats["Close"].index >= pd.Timestamp("2011-01-01")]
    close = np.log(C.where(C > 0))
    lr = close.diff()
    if "SPY" not in lr:
        raise ValueError("Frozen market proxy SPY required")
    time = pd.Series(np.arange(len(C), dtype=float), index=C.index)
    dates = pd.DatetimeIndex(panel.signal_date.unique())
    out = panel.copy()
    for h in (21, 63, 126):
        yavg = close.rolling(h, min_periods=h).mean()
        var_y = close.rolling(h, min_periods=h).var(ddof=0)
        tavg = time.rolling(h, min_periods=h).mean()
        cov_xy = close.mul(time, axis=0).rolling(h, min_periods=h).mean() - yavg.mul(tavg, axis=0)
        # RMS log-price residual of an OLS linear trend including an intercept;
        # this is NOT another name for log-return standard deviation.
        trend_rms = (var_y - cov_xy.pow(2) / ((h*h-1)/12.0)).clip(lower=0).pow(.5)
        corr_mkt = lr.rolling(h, min_periods=h).corr(lr["SPY"])
        vol = lr.rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)
        # Idiosyncratic return-volatility from OLS return~intercept+SPY return.
        market_resid = vol * (1 - corr_mkt.pow(2).clip(upper=1)).clip(lower=0).pow(.5)
        for prefix, wide in (("trend_rms", trend_rms), ("mktresid_vol", market_resid)):
            name = f"{prefix}{h}"
            b = wide.reindex(dates).stack(dropna=False).rename(name).reset_index()
            b.columns = ["signal_date", "ticker", name]
            out = out.merge(b, on=["signal_date", "ticker"], how="left",
                            sort=False, validate="one_to_one")
    assert len(out) == len(panel)
    return out

def build_feature_arms(panel: pd.DataFrame, raw: str):
    unchanged = panel[ALL].copy()
    scaled = normalize_same_day(panel, ALL)
    robust = robust_date_z(panel, ALL)
    out = add_volatility_features(panel, raw)
    for original in ALL:
        for pre, frame in (("csmm_", scaled), ("csrob_", robust)):
            out[pre + original] = frame[original].to_numpy(dtype=float)
            assert np.array_equal(out[pre + original].isna(), unchanged[original].isna())
    pd.testing.assert_frame_equal(out[ALL], unchanged)
    assert len(NO_VOL) == 101, (len(NO_VOL), sorted(set(ALL)-set(NO_VOL)))
    assert len(ALL) == 125
    # SAME-DAY-only data processing is tested on independent dates/row shuffling.
    unit_contract()
    a = {
        "CS_ADD250_MINMAX": ALL + ["csmm_" + c for c in ALL],
        "CS_ADD250_ROBUST": ALL + ["csrob_" + c for c in ALL],
        "VOL_TREND_RESID": ALL + [f"trend_rms{h}" for h in (21,63,126)],
        "VOL_MARKET_RESID": ALL + [f"mktresid_vol{h}" for h in (21,63,126)],
    }
    assert len(a["CS_ADD250_MINMAX"]) == len(a["CS_ADD250_ROBUST"]) == 250
    assert len(a["VOL_TREND_RESID"]) == len(a["VOL_MARKET_RESID"]) == 128
    return out, a

def build_regression_arms(panel: pd.DataFrame):
    assert len(ALL) == 125 and len(NO_VOL) == 101, (len(ALL), len(NO_VOL))
    return panel, {
        "REG_REL125": ALL, "REG_REL101": NO_VOL,
        "REG_ABS125": ALL, "REG_ABS101": NO_VOL,
        "REG_HUBER125": ALL,
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mode", choices=("feature", "regression"), required=True)
    p.add_argument("--raw", default="etf_trader_raw")
    p.add_argument("--baskets", default="regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv")
    p.add_argument("--prior", default="runs/v2_corrected_oracle")
    p.add_argument("--years", default="2018,2019,2020")
    p.add_argument("--out", required=True)
    args = p.parse_args()
    years = [int(x) for x in args.years.split(",")]
    assert len(years) == len(set(years)) and years and set(years) <= set(range(2018,2027))
    assert hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest() == BASKET_SHA
    original, panel, valid, baskets = freeze_data(args.raw, args.baskets)
    if args.mode == "feature":
        panel, arms = build_feature_arms(panel, args.raw)
    else:
        panel, arms = build_regression_arms(panel)
    controls = pd.read_csv(Path(args.prior) / "OOS_SCORES.csv", parse_dates=["signal_date"])
    controls = controls[(controls.variant == "CORRECTED") & (controls.signal_date.dt.year.isin(years))].copy()
    assert len(controls) > 500
    rows = [controls]
    months = []
    for _, group in controls.groupby("signal_date", sort=True):
        m = scores_for_month(group, baskets)
        if m:
            months.append(dict(variant="CORRECTED", **m))
    params = dict(v3.COMPACT_PARAMS, max_depth=0, grow_policy="lossguide", max_leaves=127)
    audits = []
    for year in years:
        cutoff = pd.Timestamp(year,1,1)
        train = (original.signal_date.ge(pd.Timestamp("2012-01-01")) &
                 original.signal_date.lt(cutoff) &
                 original.exit_date_21.lt(cutoff) &
                 original.target_rank_21.notna() & valid)
        test = original.signal_date.dt.year.eq(year) & valid
        tr = panel.loc[train].sort_values(["signal_date", "ticker"])
        te = panel.loc[test].sort_values(["signal_date", "ticker"])
        assert tr.signal_date.nunique() >= 60 and not te.empty
        assert tr.exit_date_21.max() < cutoff
        groups = tr.groupby("signal_date", sort=True).size().to_numpy()
        assert groups.sum() == len(tr)
        y_rank = np.rint(100 * tr.target_rank_21.to_numpy(float)).astype(int)
        log_ret = np.log1p(tr.fwd_ret_21.clip(lower=-.95).astype(float))
        y_abs = 100 * log_ret.clip(-.25,.25).to_numpy(float)
        y_rel = 100 * (log_ret - log_ret.groupby(tr.signal_date).transform("median")).clip(-.25,.25).to_numpy(float)
        assert np.isfinite(y_abs).all() and np.isfinite(y_rel).all()
        for arm, names in arms.items():
            X = tr[names].replace([np.inf,-np.inf],np.nan)
            Xt = te[names].replace([np.inf,-np.inf],np.nan)
            config = dict(params)
            if args.mode == "feature":
                model_class, label = XGBRanker, y_rank
            else:
                model_class = XGBRegressor
                config.update(objective="reg:squarederror",eval_metric="rmse")
                label = y_rel if "REL" in arm or "HUBER" in arm else y_abs
                if "HUBER" in arm:
                    config.update(objective="reg:pseudohubererror",eval_metric="mae",huber_slope=1.0)
            preds = []
            for seed in SEEDS:
                model = model_class(**config, random_state=seed)
                if args.mode == "feature":
                    model.fit(X, label, group=groups, verbose=False)
                else:
                    model.fit(X, label, verbose=False)
                preds.append(model.predict(Xt))
            current = te[["signal_date","ticker","fwd_ret_21"]].copy()
            current["pred"] = np.mean(preds, axis=0)
            current.insert(0, "variant", arm)
            assert np.isfinite(current.pred.to_numpy()).all()
            rows.append(current)
            for _, g in current.groupby("signal_date", sort=True):
                m = scores_for_month(g, baskets)
                if m:
                    months.append(dict(variant=arm, **m))
            audits.append({"arm": arm, "year": year, "mode": args.mode,
                           "features": len(names), "seeds": list(SEEDS),
                           "last_mature_exit": str(tr.exit_date_21.max()),
                           "train_months": int(tr.signal_date.nunique()),
                           "train_rows": len(tr), "test_rows": len(te),
                           "params": config})
            print("FIT_OK",args.mode,arm,year,len(names),len(te),flush=True)
    scores = pd.concat(rows, ignore_index=True)
    m = pd.DataFrame(months)
    scores["signal_date"] = pd.to_datetime(scores.signal_date)
    m["signal_date"] = pd.to_datetime(m.signal_date)
    assert not scores.duplicated(["variant","signal_date","ticker"]).any()
    assert not m.duplicated(["variant","signal_date"]).any()
    b = scores[scores.variant=="CORRECTED"].sort_values(["signal_date","ticker"]).reset_index(drop=True)
    for arm in arms:
        t = scores[scores.variant==arm].sort_values(["signal_date","ticker"]).reset_index(drop=True)
        pd.testing.assert_frame_equal(t[["signal_date","ticker"]], b[["signal_date","ticker"]])
        np.testing.assert_allclose(t.fwd_ret_21, b.fwd_ret_21, rtol=0, atol=1e-14, equal_nan=True)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    scores.to_csv(out/"OOS_SCORES.csv",index=False)
    m.to_csv(out/"PAIRED_MONTHLY.csv",index=False)
    (out/"FIT_AUDIT.json").write_text(json.dumps(audits,indent=2))
    (out/"MANIFEST.json").write_text(json.dumps({
        "mode": args.mode, "arms": arms, "years": years,
        "raw_run": 39482809691, "baseline_run": 39515716383,
        "basket_sha256": BASKET_SHA, "seeds": list(SEEDS),
        "labels": "matured next-open 21-day, annual expanding fit",
        "asof_crosssectional_only": True, "original_125_preserved": True,
        "not_virgin_holdout": True, "no_production_change": True},indent=2))

if __name__ == "__main__":
    main()
