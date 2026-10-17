#!/usr/bin/env python3
"""Explicitly scaled 60-ETF source-only MA3 cluster construction.

Why separate from the original source? Original A4 requires seven dynamic clusters
of >=8 plus one defensive cluster of >=8: at least 64 candidates, so cannot
mathematically accept the geographically clean EUR60 cohort. Keep the original
implementation untouched in Git. Reduce to six dynamic groups of >=8 and one
European-sovereign group of >=7, predeclared before any European refit outcomes.
"""
from __future__ import annotations
import runpy,sys
from pathlib import Path
import etf_trader.source_only.a4_cluster_destination as a4

REPO=Path(__file__).resolve().parents[1]
LEGACY=REPO/"europe120/eu120_retrain/build_ma3_panel_causal.py"
EXPECTED=dict(N_CLUSTERS=8,N_DYNAMIC_CLUSTERS=7,MIN_CLUSTER_SIZE=8,
              DEFENSIVE_CATEGORY="C05_BONDS_CASH_CREDIT")
for name,old in EXPECTED.items():
    if getattr(a4,name)!=old:
        raise ValueError(f"Upstream source changed {name}: {getattr(a4,name)!r} instead of {old!r}")

a4.N_CLUSTERS=7
a4.N_DYNAMIC_CLUSTERS=6
a4.MIN_CLUSTER_SIZE=7
a4.DEFENSIVE_CATEGORY="EU_SOVEREIGN"
native_mapping=a4.persistent_cluster_mapping

def europe_six_dynamic_mapping(members_temp,previous_members,centers,*,n_dynamic_clusters=6):
    if n_dynamic_clusters!=6 or len(members_temp)!=6:
        raise ValueError("Europe-only 60 ETF cluster cardinality drift")
    return native_mapping(members_temp,previous_members,centers,n_dynamic_clusters=6)

a4.persistent_cluster_mapping=europe_six_dynamic_mapping
native_balance=a4.balanced_kmeans_assignment

def europe_scaled_capacity(z,n_clusters,seed,max_iter=20,*,min_cluster_size=7,max_cluster_size=30):
    if n_clusters!=6:
        raise ValueError("EUROPE60 six dynamic clusters required")
    return native_balance(z,n_clusters,seed,max_iter,
        min_cluster_size=7,max_cluster_size=30)

a4.balanced_kmeans_assignment=europe_scaled_capacity
print("EUROPE_ONLY_CLUSTER_ADAPTATION: 6 x >=7 dynamic + 1 x >=7 euro sovereign",flush=True)
sys.path.insert(0,str(REPO/"europe120/eu120_retrain"))
runpy.run_path(str(LEGACY),run_name="__main__")
