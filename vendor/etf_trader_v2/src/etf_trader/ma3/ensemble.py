"""Compatibility wrapper for the promoted Hybrid24 MA3 producer.

The single authoritative implementation is :mod:`etf_trader.ma3.hybrid_producer`.
This module keeps the clean-room ensemble runner/API stable without duplicating
model logic.
"""
from __future__ import annotations

from .hybrid_producer import (
    ET_MODEL_KW,
    XGB_MODEL_KW,
    XGB_WEIGHT,
    fit_hybrid_producer,
)

ET_KW = ET_MODEL_KW
XGB_KW = XGB_MODEL_KW
XGB_ALPHA = XGB_WEIGHT


def fit_ensemble_producer(panel, tit_r, ticker_order, *, start_year=2017, end_year=2026, n_jobs=1):
    return fit_hybrid_producer(
        panel,
        tit_r,
        ticker_order,
        start_year=start_year,
        end_year=end_year,
        et_n_jobs=n_jobs,
        xgb_n_jobs=n_jobs,
    )
