"""Prospectively fixed feature masks. The canonical 125-column schema stays intact."""
from __future__ import annotations

import hashlib
import json
from etf_trader.source_only.kernel import F2D_FEATURES

FEATURES = tuple(F2D_FEATURES)


def _family(stems, suffixes=("", "_pct", "_dev")):
    return tuple(f"{stem}{suffix}" for stem in stems for suffix in suffixes)


MASKS = {
    # Only family where source-repeat missing-mask flips have been observed.
    "DOWNVOL9": _family(("downvol21", "downvol63", "downvol126")),
    # Cross-sectional median/MAD transformation may magnify small source revisions.
    "ROBUST_DEV33": tuple(f for f in FEATURES if f.endswith("_dev")),
    # Per-date cross-sectional rank can jump discretely near ties.
    "CROSS_SECTION_PCT46": tuple(f for f in FEATURES if f.endswith("_pct")),
    # Fixed compact set from source-only drift diagnostics, not predictive outcomes.
    "HIGH_NOISE_COMPACT": (
        *_family(("downvol21", "downvol63", "downvol126", "vol_ratio_21_126", "skew63", "kurt63")),
        *_family(("sign_entropy63", "positive_frac63"), ("", "_pct")),
    ),
}


def mask_manifest():
    assert len(FEATURES) == 125 and len(set(FEATURES)) == 125
    assert [len(MASKS[k]) for k in MASKS] == [9, 33, 46, 22]
    for name, columns in MASKS.items():
        if len(set(columns)) != len(columns) or not set(columns).issubset(FEATURES):
            raise ValueError(f"Invalid mask {name}")
    return {name: {"masked_columns": list(columns),
                   "masked_columns_sha256": hashlib.sha256(json.dumps(list(columns), separators=(",", ":")).encode()).hexdigest(),
                   "retained_count": len(FEATURES)-len(columns)}
            for name, columns in MASKS.items()}


if __name__ == "__main__":
    print(json.dumps(mask_manifest(), indent=2))
