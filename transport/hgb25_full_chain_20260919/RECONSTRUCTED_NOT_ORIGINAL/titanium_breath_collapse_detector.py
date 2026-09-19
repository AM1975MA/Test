#!/usr/bin/env python3
"""RECONSTRUCTED — NOT ORIGINAL HISTORICAL SOURCE.

Clean-room reconstruction of the missing 2026-08-24 Titanium breath/collapse
helper. This file is intentionally and permanently marked as reconstructed.
It must never be presented as the recovered historical source.

Reconstruction anchors:
- historical DD state laboratory feature vocabulary;
- historical two-close HGB consumer contract;
- historical BREATH/COLLAPSE leader-only semantics;
- historical replay threshold 0.834412501765974 (stored in the consumer).
"""
from __future__ import annotations

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SOURCE_STATUS = "RECONSTRUCTED_NOT_ORIGINAL"
RECONSTRUCTION_DATE = "2026-09-19"

# Exact vocabulary recovered from titanium_dd_state_lab.py.
BASE_FEATURES = [
    "entry_dd", "trigger_overshoot", "days_since_entry",
    "leader_r1", "leader_r3", "leader_r5", "leader_r10", "leader_r21",
    "leader_accel_3_10", "leader_dd21", "leader_dd63", "leader_vol5",
    "leader_vol20", "leader_downfrac5", "leader_atr20", "leader_gap",
    "leader_volume_z20", "leader_vs_ma20", "leader_vs_ma50",
    "sat_r3", "sat_r5", "sat_r10", "sat_r21",
    "rel_r3", "rel_r5", "rel_r10", "rel_r21",
    "spy_r5", "spy_r21", "spy_dd63", "spy_vs_ma200",
    "hyg_ief_r10", "breadth5", "breadth21", "cross_down1",
    "entry_leader_m21", "entry_leader_m63", "entry_leader_dd63",
    "entry_rel_m21", "entry_spy_vs200", "entry_breadth21",
]

# Score-date state, reconstructed from the downstream two-close contract.
SCORE_FEATURES = [
    "score_leader_r1", "score_leader_r3", "score_leader_r5",
    "score_leader_r10", "score_leader_r21", "score_leader_dd21",
    "score_leader_dd63", "score_leader_vol5", "score_leader_vol20",
    "score_leader_vs_ma20", "score_leader_vs_ma50",
    "score_spy_r5", "score_spy_r21", "score_spy_dd63",
    "score_spy_vs_ma200", "score_hyg_ief_r10",
    "score_breadth5", "score_breadth21", "score_cross_down1",
]


def model_specs(features: list[str] | None = None) -> dict[str, object]:
    """Return the reconstructed historical model-family contract."""
    _ = features
    return {
        "LOGIT": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            StandardScaler(),
            LogisticRegression(
                C=0.25, class_weight="balanced", max_iter=3000,
                random_state=17,
            ),
        ),
        "HGB": make_pipeline(
            SimpleImputer(strategy="median", add_indicator=True),
            HistGradientBoostingClassifier(
                learning_rate=0.055,
                max_iter=180,
                max_leaf_nodes=15,
                min_samples_leaf=24,
                l2_regularization=1.5,
                random_state=17,
            ),
        ),
    }
