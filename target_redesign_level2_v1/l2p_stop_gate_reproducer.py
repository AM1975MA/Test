#!/usr/bin/env python3
"""Reproduce L2-P's exact two-condition stop ablation on frozen L2-N/L2-O.
Requires (i) original TIFF/Yahoo input titanium-repeat-2.zip in /mnt/data;
(ii) L2-N's l2n_full_replay.py; (iii) L2-O's l2o_forensic_replay.py.
Full executed source, ledger and 15-file ZIP are delivered with L2P results.
No fitting and no edits to the production repository.
"""
import sys, inspect
from pathlib import Path
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path("/mnt/data")
sys.path[:0]=[str(ROOT/"l2n_risk"),str(ROOT/"l2o_forensics")]
import l2n_full_replay as canonical
import l2o_forensic_replay as independent

def ablate_only_market_gate(fn):
    src=inspect.getsource(fn)
    orig=[
        "and p1 and (sysm or ud1[k]>=.55)",
        "and p2 and (sysm or ud1[k]>=.55)",
    ]
    assert all(src.count(s)==1 for s in orig), "Canonical code drift"
    patched=src.replace(orig[0],"and p1").replace(orig[1],"and p2")
    assert patched.replace("and p1:",orig[0]+":").replace("and p2:",orig[1]+":")==src
    env=dict(np=np,pd=pd,njit=njit)
    exec(patched,env)
    return env[fn.__name__]

def main():
    t,mats,cal,ds,d1,d2,w,margin,g,alt,ex,base_eq,base_t=independent.get_state()
    assert len(ds)==2366
    original=canonical.metrics(base_eq[None,:])
    assert abs(original["cagr"]-0.3084370492564604)<1e-10
    args=(d1,d2,w,*ex,t.index("BIL"),t.index("SHV"),g[None,:],g,alt,True,.001)
    sim=ablate_only_market_gate(canonical.simulate_arch.py_func)
    eq,tv,_,_=sim(*args)
    cash=ablate_only_market_gate(independent.replay_traced)
    e2,t2,ledger,assets,stops=cash(ds,t,None,d1[0],d2[0],w[0],g,g,alt[0],ex,
                                    t.index("BIL"),t.index("SHV"))
    assert np.max(np.abs(eq[0]-e2))<1e-8
    assert np.max(np.abs(tv[0]-t2))<1e-9
    assert np.max(np.abs(ledger.pnl_residual))<1e-8
    outcome=canonical.metrics(eq)
    print("Original full-V2:",original)
    print("L2-P single-name stop:",outcome)
    print("Stops:",len(stops),"annual turnover:",float(tv.mean()*252))
    assert len(stops)==48
    assert outcome["cagr"]<.95*original["cagr"]
    assert outcome["maxdd"]<original["maxdd"]
    print("NO_GO: fails CAGR and drawdown gates; audit PASS")

if __name__=="__main__":main()
