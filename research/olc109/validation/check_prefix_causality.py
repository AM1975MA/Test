"""Production behavior test, separate from independent account reconstruction."""
from pathlib import Path
import importlib.util
import json
import sys
import gc
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits


def run(root):
    root = Path(root)
    sys.path.insert(0, str(root / "src"))
    import cluster_selectors as cs
    import dedup_selectors as ds
    import horizon_selectors as hs
    policies = ([(arm, cs.make_policy) for arm in cs.ARMS] + [(arm, ds.make_policy) for arm in ds.ARMS]
                + [(arm, hs.make_policy) for arm in hs.ARMS])
    spec = importlib.util.spec_from_file_location("prefix_test_core", root / "source/src/core.py")
    core = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(core)
    with np.load(root / "source/data/XETRA_EUR_ETF.npz", allow_pickle=False) as z:
        panel = {key: z[key] for key in z.files}
    with np.load(root / "data/LIQUIDITY.npz", allow_pickle=False) as z:
        turnover = z["turnover"]
    dates = pd.DatetimeIndex(panel["dates"])
    keys = [int(dates.searchsorted(date, side="right") - 1) for date in ("2020-02-28", "2022-12-30", "2024-12-30")]
    results = []
    for k in keys:
        length = min(len(dates), k + 22)
        prefix = {name: (value[:k + 1].copy() if value.ndim and value.shape[0] == len(dates) else value.copy()) for name, value in panel.items()}
        f = cs.prepare_features(prefix, core, turnover[:k + 1])
        original = cs.build_snapshot(prefix, f, k)
        weights = {arm: factory(prefix, f, {k: original}, arm)(k, np.zeros(len(panel["names"])))[0] for arm, factory in policies}
        del f
        gc.collect()
        extended = {name: (value[:length].copy() if value.ndim and value.shape[0] == len(dates) else value.copy()) for name, value in panel.items()}
        # Price, volume, and observation changes strictly after the signal.
        extended["C"][k + 1:] *= np.linspace(.001, 1000., length - k - 1)[:, None]
        extended["O"][k + 1:] *= 300.
        extended["observed"][k + 1:, ::2] = False
        extended["open_observed"][k + 1:, 1::2] = False
        future_turnover = turnover[:length].copy()
        future_turnover[k + 1:, ::2] = 0.
        future_turnover[k + 1:, 1::2] = 1e15
        f = cs.prepare_features(extended, core, future_turnover)
        mutated = cs.build_snapshot(extended, f, k)
        assert original["groups"] == mutated["groups"], ("FUTURE_CHANGED_CLUSTER", k)
        assert np.array_equal(original["rep_corr"], mutated["rep_corr"]), ("FUTURE_CHANGED_CORRELATION", k)
        for arm, factory in policies:
            actual = factory(extended, f, {k: mutated}, arm)(k, np.zeros(len(panel["names"])))[0]
            assert np.array_equal(actual, weights[arm]), ("FUTURE_CHANGED_TARGET", k, arm)
        results.append(dict(signal_date=str(dates[k].date()), signal_idx=k,
                            instruments=len(panel["names"]), arms_checked=len(policies),
                            groups=len(original["groups"]), future_sessions_changed=length - k - 1, status="PASS"))
        del f, original, mutated, weights, prefix, extended, future_turnover
        gc.collect()
    output = dict(status="PASS_REAL_PANEL_PREFIX_INVARIANCE", dates_checked=len(results),
                  target_vectors_checked=len(results) * len(policies), results=results,
                  imports_production_code=True, role="Behavior test only; independent account and selection references import no production modules.")
    (root / "validation/PREFIX_CAUSALITY.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    with threadpool_limits(limits=1):
        run(Path(__file__).resolve().parents[1])
