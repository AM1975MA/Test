"""Three fixed lookback horizons, chosen before observing candidate outcomes."""
from __future__ import annotations

import hashlib
import json

WINDOWS = {"ROLL6": 6, "ROLL10": 10, "ROLL15": 15}


def manifest():
    assert WINDOWS == {"ROLL6": 6, "ROLL10": 10, "ROLL15": 15}
    return {name: {"years": years,
                   "start_rule": "signal_date >= January 1 of fit_year - years",
                   "end_rule": "signal_date and actual exit_date_21 < January 1 of fit_year"}
            for name, years in WINDOWS.items()}


def manifest_sha256():
    return hashlib.sha256(json.dumps(manifest(), sort_keys=True, separators=(",", ":")).encode()).hexdigest()
