"""Only 48 ISIN mechanical S3B cluster sizing adapter.

Original 149: 7 dynamic x minimum8 + bond sleeve>=8 (requires >=64).
Actual 48: 41 dynamic, 7 government. Maintain original KMeans, PCA,
assignment, causal membership, seed, but use 5 dynamic + 1 defensive,
minimum4 while retaining .NO FUTURE LABELS.
"""
from __future__ import annotations
from functools import wraps
from etf_trader.source_only import a4_cluster_destination as cl

def enable():
    assert cl.N_CLUSTERS==8 and cl.N_DYNAMIC_CLUSTERS==7
    assert cl.MIN_CLUSTER_SIZE==8 and cl.MIN_CLUSTER_OBS==168
    assert cl.DEFENSIVE_CATEGORY=="C05_BONDS_CASH_CREDIT"
    base_assign=cl.balanced_kmeans_assignment
    base_persist=cl.persistent_cluster_mapping
    @wraps(base_assign)
    def assign(z,n_clusters=5,seed=cl.DEFAULT_SEED,max_iter=20,*,min_cluster_size=4,max_cluster_size=30):
        return base_assign(z,n_clusters=n_clusters,seed=seed,max_iter=max_iter,
                           min_cluster_size=min_cluster_size,max_cluster_size=max_cluster_size)
    @wraps(base_persist)
    def persist(members_temp,previous_members,centers,n_dynamic_clusters=5):
        return base_persist(members_temp,previous_members,centers,
                            n_dynamic_clusters=n_dynamic_clusters)
    cl.N_CLUSTERS=6
    cl.N_DYNAMIC_CLUSTERS=5
    cl.MIN_CLUSTER_SIZE=4
    cl.balanced_kmeans_assignment=assign
    cl.persistent_cluster_mapping=persist
    return {"s3b_original_clusters":8,"s3b_original_dynamic":7,
       "s3b_ported_total":cl.N_CLUSTERS,"s3b_ported_dynamic":cl.N_DYNAMIC_CLUSTERS,
       "min_cluster_149":8,"min_cluster_EU48":4,"source_KMeans_seed":cl.DEFAULT_SEED,
       "min_valid_252_window_bars":cl.MIN_CLUSTER_OBS}
