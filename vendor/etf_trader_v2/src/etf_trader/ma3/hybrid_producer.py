"""Source-only hybrid MA3 producer selected on current raw without historical derived inputs.

The hybrid combines two annual maturity-safe models trained on the same 42
source-generated MA3 features and the same corrected target:
- OLD_HC ExtraTrees rank: 60%
- XGB_B regression rank: 40%

Model-family screening used 2011-2016. The 60/40 blend was selected on the
2017-2022 signal-period validation set. The 2023+ holdout was not used to
select the blend weight.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.impute import SimpleImputer
from xgboost import XGBRegressor

from .producer import FEATURES_42

TARGET_POWER = 1.5
TARGET_WEIGHTS = (0.45, 0.35, 0.20)
ET_WEIGHT = 0.60
XGB_WEIGHT = 0.40

ET_MODEL_KW = dict(
    n_estimators=120,
    max_features=0.4,
    min_samples_leaf=20,
    max_depth=8,
    random_state=101,
)

XGB_MODEL_KW = dict(
    n_estimators=400,
    max_depth=2,
    learning_rate=0.02,
    subsample=0.90,
    colsample_bytree=0.90,
    min_child_weight=12,
    reg_lambda=12,
    reg_alpha=0.2,
    objective="reg:squarederror",
    tree_method="hist",
    random_state=101,
)

TAIL_LAG_WEIGHTS = (0.40, 0.30, 0.30)
TAIL_POWER = 1.10
BASE_WEIGHT = 0.475
TAIL_WEIGHT = 0.525


@dataclass(frozen=True)
class HybridProducerResult:
    predictions: pd.DataFrame
    calendar: pd.DataFrame
    score: np.ndarray
    base: np.ndarray
    tail: np.ndarray
    et_tail: np.ndarray
    xgb_tail: np.ndarray
    fit_audit: pd.DataFrame


def corrected_target(panel: pd.DataFrame) -> pd.Series:
    r21 = panel["target_rank_21"].astype(float)
    r42 = panel["target_rank_42"].astype(float)
    r63 = panel["target_rank_63"].astype(float)
    w21, w42, w63 = TARGET_WEIGHTS
    return (
        w21 * r21.pow(TARGET_POWER)
        + w42 * r42.pow(TARGET_POWER)
        + w63 * r63.pow(TARGET_POWER)
    )


def fit_hybrid_producer(
    panel: pd.DataFrame,
    tit_r: pd.DataFrame,
    ticker_order: Sequence[str],
    *,
    feature_cols: Sequence[str] = FEATURES_42,
    start_year: int = 2017,
    end_year: int = 2026,
    et_n_jobs: int = 1,
    xgb_n_jobs: int = 1,
) -> HybridProducerResult:
    """Fit the two model families annually with strict label maturity.

    No previously generated score, model, path or cluster-membership artifact
    is accepted by this function. Both components are refit from the supplied
    source-generated feature panel.
    """
    df = panel.copy()
    df["signal_date"] = pd.to_datetime(df["signal_date"])
    df["exit_date_63"] = pd.to_datetime(df["exit_date_63"])

    missing = [c for c in feature_cols if c not in df.columns]
    if missing:
        raise KeyError(f"missing hybrid-producer features: {missing}")

    df["HYBRID_TARGET"] = corrected_target(df)

    schedule = tit_r.copy()
    for c in ("signal_date", "entry_date", "exit_date"):
        schedule[c] = pd.to_datetime(schedule[c])
    if "TIT_R" not in schedule.columns:
        raise KeyError("TIT_R column missing from source-generated Titanium schedule")

    cal = (
        schedule[["signal_date", "entry_date", "exit_date"]]
        .drop_duplicates()
        .sort_values("signal_date")
        .reset_index(drop=True)
    )
    base = schedule[["signal_date", "ticker", "TIT_R"]].copy()

    outs = []
    audit = []

    for yr in range(start_year, end_year + 1):
        cutoff = pd.Timestamp(f"{yr}-01-01")
        next_cutoff = pd.Timestamp(f"{yr + 1}-01-01")

        tr = df[
            (df["signal_date"] < cutoff)
            & (df["exit_date_63"] < cutoff)
            & df["HYBRID_TARGET"].notna()
        ].copy()

        pr = df[
            (df["signal_date"] >= cutoff)
            & (df["signal_date"] < next_cutoff)
            & df["signal_date"].isin(cal["signal_date"])
        ].copy().reset_index(drop=True)

        if pr.empty:
            continue
        if tr.empty:
            raise RuntimeError(f"no maturity-safe training rows for {yr}")

        imp = SimpleImputer(strategy="median")
        xtr = imp.fit_transform(tr[list(feature_cols)])
        xp = imp.transform(pr[list(feature_cols)])
        y = tr["HYBRID_TARGET"].to_numpy(float)

        et = ExtraTreesRegressor(n_jobs=et_n_jobs, **ET_MODEL_KW)
        et.fit(xtr, y)

        xgb_cfg = dict(XGB_MODEL_KW)
        xgb_cfg["n_jobs"] = xgb_n_jobs
        xb = XGBRegressor(**xgb_cfg)
        xb.fit(xtr, y)

        pr["ET_RAW"] = et.predict(xp)
        pr["XGB_RAW"] = xb.predict(xp)

        pr["ET_TAIL"] = pr.groupby("signal_date")["ET_RAW"].rank(
            pct=True, method="average"
        )
        pr["XGB_TAIL"] = pr.groupby("signal_date")["XGB_RAW"].rank(
            pct=True, method="average"
        )
        pr["TAIL_HYBRID"] = (
            ET_WEIGHT * pr["ET_TAIL"] + XGB_WEIGHT * pr["XGB_TAIL"]
        )

        outs.append(
            pr[
                [
                    "signal_date",
                    "ticker",
                    "ET_TAIL",
                    "XGB_TAIL",
                    "TAIL_HYBRID",
                ]
            ]
        )
        audit.append(
            {
                "year": yr,
                "n_train": int(len(tr)),
                "n_predict": int(len(pr)),
                "max_train_signal": str(tr["signal_date"].max().date()),
                "max_train_exit63": str(tr["exit_date_63"].max().date()),
                "cutoff": str(cutoff.date()),
                "maturity_ok": bool(
                    (tr["signal_date"] < cutoff).all()
                    and (tr["exit_date_63"] < cutoff).all()
                ),
            }
        )

    if not outs:
        raise RuntimeError("hybrid producer generated no predictions")

    pred = (
        pd.concat(outs, ignore_index=True)
        .merge(
            base,
            on=["signal_date", "ticker"],
            how="inner",
            validate="one_to_one",
        )
        .rename(columns={"TIT_R": "BASE"})
    )

    tickers = list(map(str, ticker_order))
    dates = pd.DatetimeIndex(cal["signal_date"])

    def pivot(col: str) -> np.ndarray:
        return (
            pred.pivot(index="signal_date", columns="ticker", values=col)
            .reindex(index=dates, columns=tickers)
            .to_numpy(float)
        )

    base_arr = pivot("BASE")
    tail = pivot("TAIL_HYBRID")
    et_tail = pivot("ET_TAIL")
    xgb_tail = pivot("XGB_TAIL")

    lag1 = np.vstack([tail[:1], tail[:-1]])
    lag2 = np.vstack([tail[:1], tail[:1], tail[:-2]])
    a0, a1, a2 = TAIL_LAG_WEIGHTS
    smooth = a0 * tail + a1 * lag1 + a2 * lag2
    transformed = np.power(np.clip(smooth, 0.0, 1.0), TAIL_POWER)

    score = BASE_WEIGHT * base_arr + TAIL_WEIGHT * transformed

    return HybridProducerResult(
        pred,
        cal,
        score,
        base_arr,
        tail,
        et_tail,
        xgb_tail,
        pd.DataFrame(audit),
    )
