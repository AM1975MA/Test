"""Production behavior check, separate from independent references.

For three historical cutoffs and all 13 arms, perturb every price/availability/
liquidity input strictly after the cutoff. Re-run the prefix under delayed Open
and next-Close execution. Compare complete prior instructions, fills, account
values and both slot-state traces, including the cutoff's Close decision.
This file intentionally imports production; it is not a reconstruction oracle.
"""
from pathlib import Path
import gc
import hashlib
import importlib.util
import json
import sys
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits


def hash_value(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=True).encode()).hexdigest()


def capture(result, policy, cutoff):
    instructions = result['instructions']
    instructions = instructions[instructions.signal_idx <= cutoff].to_dict('records')
    decisions = []
    for row in result['decisions']:
        if row['k'] <= cutoff:
            decisions.append({key:value.tolist() if isinstance(value,np.ndarray) else value for key,value in row.items()})
    orders = result['orders']
    orders = orders[orders.execution_idx <= cutoff].to_dict('records')
    daily = result['daily']
    daily = daily[daily.k <= cutoff].to_dict('records')
    traces = [] if policy is None else [row for row in policy.trace if row['k'] <= cutoff]
    return {key:hash_value(value) for key,value in dict(instructions=instructions,decisions=decisions,orders=orders,daily=daily,traces=traces).items()}


def run(root):
    root = Path(root).resolve()
    freeze = json.loads((root/'docs/EXPERIMENT_FREEZE.json').read_text())
    for path,wanted in freeze['code_hashes'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest() == wanted
    sys.path.insert(0,str(root/'src'))
    from engine import simulate
    from signals import decision_mask
    from cluster_selectors import prepare_features
    from dedup_selectors import make_policy as selector
    from protection import ARMS, CONTROL_ARMS, prepare_timing_features, make_account_policy
    core_spec = importlib.util.spec_from_file_location('olc110_prefix_core',root/'source/src/core.py')
    core = importlib.util.module_from_spec(core_spec);core_spec.loader.exec_module(core)
    with np.load(root/'source/data/XETRA_EUR_ETF.npz',allow_pickle=False) as z:
        original = {key:z[key] for key in z.files}
    with np.load(root/'data/LIQUIDITY.npz',allow_pickle=False) as z:
        turnover = z['turnover']
    dates = pd.DatetimeIndex(original['dates'])
    cutoffs = ['2021-12-30','2024-12-30','2026-06-30']
    rows = []
    for cutoff_date in cutoffs:
        cutoff = int(dates.searchsorted(cutoff_date,side='right')-1)
        total = min(len(dates),cutoff+23)
        prior = {}
        for mutated in (False,True):
            panel = {key:(value[:total].copy() if value.ndim and len(value)==len(dates) else value.copy()) for key,value in original.items()}
            liquidity = turnover[:total].copy()
            if mutated:
                changed = total-cutoff-1
                panel['C'][cutoff+1:] *= np.linspace(.001,1000.,changed)[:,None]
                panel['O'][cutoff+1:] *= np.linspace(300.,.003,changed)[:,None]
                panel['observed'][cutoff+1:,::2] = False
                panel['open_observed'][cutoff+1:,1::2] = False
                liquidity[cutoff+1:,::2] = 0.
                liquidity[cutoff+1:,1::2] = 1e15
            f = prepare_timing_features(panel,prepare_features(panel,core,liquidity))
            monthly,weekly = decision_mask(panel['dates'],'MONTHLY'),decision_mask(panel['dates'],'WEEKLY')
            begin = int(pd.DatetimeIndex(panel['dates']).searchsorted('2020-03-02'))
            for arm in ARMS:
                for mode in ('LAG2_OPEN','NEXT_CLOSE'):
                    market = panel if mode=='LAG2_OPEN' else dict(panel,O=panel['C'],open_observed=panel['observed'])
                    base = selector(market,f,{},'DEDUP_DUAL_TREND_OPP')
                    scale = .5 if arm=='STATIC_HALF' else .75 if arm=='STATIC_75' else 1.
                    def control(k,current,base=base,scale=scale):
                        w,meta = base(k,current);return w*scale,meta
                    policy = None if arm in CONTROL_ARMS else make_account_policy(market,f,monthly,weekly,arm,begin-1)
                    result = simulate(market,f,control,weekly if arm=='REFRESH_WEEKLY' else monthly,legacy=core,account_policy=policy,
                                      lag=2 if mode=='LAG2_OPEN' else 0,end=str(dates[cutoff+1].date()))
                    fingerprint = capture(result,policy,cutoff)
                    key = (arm,mode)
                    if not mutated:
                        prior[key] = fingerprint
                    else:
                        assert fingerprint == prior[key], ('FUTURE_CHANGED_PREFIX',cutoff_date,arm,mode,fingerprint,prior[key])
                        rows.append(dict(cutoff=str(dates[cutoff].date()),cutoff_index=cutoff,arm=arm,execution_mode=mode,
                                         future_sessions_perturbed=total-cutoff-1,instruments=len(panel['names']),
                                         status='PASS',component_hashes=fingerprint))
                    del result,policy
            del f,panel,liquidity
            gc.collect()
        print(f'PASS prefix {cutoff_date}: 13 arms x 2 execution conventions',flush=True)
    for path,wanted in freeze['code_hashes'].items():
        assert hashlib.sha256((root/path).read_bytes()).hexdigest() == wanted
    report = dict(status='PASS_FUTURE_PERTURBATION_INVARIANCE',cutoffs=len(cutoffs),comparisons=len(rows),
                  arms=13,execution_modes=['LAG2_OPEN','NEXT_CLOSE'],
                  components=['immutable instructions','decision accounts/targets','completed orders','daily cash/NAV','daily slot state traces'],
                  production_imports=True,role='Explicit behavior test only; independent references import no production modules.',
                  financial_code_hashes=freeze['code_hashes'],results=rows)
    (root/'validation/PREFIX_CAUSALITY.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','cutoffs','comparisons','arms','execution_modes')},indent=2),flush=True)


if __name__=='__main__':
    with threadpool_limits(limits=1):
        run(Path(__file__).resolve().parents[1])
