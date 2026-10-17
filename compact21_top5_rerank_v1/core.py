"""Deterministic, zero-fit BASE top-five-constrained economic reranking."""
from __future__ import annotations
import numpy as np
import pandas as pd

VARIANT="ECON_TOP5_RERANK"
KEYS=("vintage","signal_date","ticker")
TOP_K=5

def ordered(frame, score):
    return frame.sort_values([score,"ticker"],ascending=[False,True],kind="mergesort")

def rerank(base,layer):
    """Same keys, same BASE score multiset, same BASE top5 members per query."""
    required=set(KEYS)|{"pred"}
    if not required.issubset(base) or not required.issubset(layer):
        raise ValueError("Missing forecast source or score")
    a=base.copy();b=layer.copy()
    for f in (a,b):
        f["vintage"]=f["vintage"].astype(str)
        f["signal_date"]=pd.to_datetime(f["signal_date"],errors="raise")
        if f[list(KEYS)].isna().any().any() or f.duplicated(list(KEYS)).any():
            raise ValueError("Duplicate or missing score keys")
        if not np.isfinite(f.pred.to_numpy(float)).all():
            raise ValueError("Nonfinite source score")
        f.sort_values(list(KEYS),inplace=True,kind="stable")
        f.reset_index(drop=True,inplace=True)
    if not a[list(KEYS)].equals(b[list(KEYS)]):
        raise ValueError("BASE and economic layer forecast coverage differ")
    a["_layer_pred"]=b.pred.to_numpy(float)
    a["_output"]=a.pred.to_numpy(float)
    group_audit=[]
    for (vintage,date),index in a.groupby(["vintage","signal_date"],sort=True).indices.items():
        ix=np.asarray(index,int)
        g=a.iloc[ix].copy()
        n=min(len(g),TOP_K)
        best_base=ordered(g,"pred").iloc[:n]
        best_layer=ordered(best_base,"_layer_pred")
        # The original BASE top-five numerical raw scores, placed in order of
        # the economic layer *only* among the exact original BASE top-five tickers.
        raw_scores=best_base.pred.to_numpy(float)
        row_for_ticker=dict(zip(g.ticker.to_list(),ix.tolist()))
        chosen=[row_for_ticker[t] for t in best_layer.ticker]
        a.loc[chosen,"_output"]=raw_scores
        out=a.iloc[ix][["ticker","_output"]].rename(columns={"_output":"pred"})
        if not np.array_equal(np.sort(out.pred.to_numpy(float)),np.sort(g.pred.to_numpy(float))):
            raise ValueError("Changed original BASE score multiset")
        expected_top=set(best_base.ticker)
        actual_top=set(ordered(out,"pred").iloc[:n].ticker)
        if expected_top!=actual_top:
            raise ValueError("Promoted non-BASE-Top5 ETF into top five")
        outside=g.loc[~g.ticker.isin(expected_top)]
        if not np.array_equal(a.loc[outside.index,"_output"].to_numpy(float),
                              outside.pred.to_numpy(float)):
            raise ValueError("Changed score of original below-Top5 ETF")
        orig=str(best_base.ticker.iloc[0])
        new=str(ordered(out,"pred").ticker.iloc[0])
        group_audit.append(dict(vintage=vintage,date=pd.Timestamp(date).strftime("%Y-%m-%d"),
            n_tickers=len(g),topk=n,base_top1=orig,candidate_top1=new,
            top1_changed=(orig!=new),
            changed_score_count=int(np.sum(g.pred.to_numpy(float)!=out.pred.to_numpy(float))),
            only_top5_permutation=True,score_multiset_preserved=True))
    result=a.drop(columns=["pred","_layer_pred"]).rename(columns={"_output":"pred"})
    result=result[base.columns.to_list()].copy()
    # Replayer uses integer vintage (1,2,3). Restore source-native schema;
    # string normalization above is only for deterministic cross-archive joins.
    result["vintage"]=result["vintage"].astype(base["vintage"].dtype)
    return result,group_audit
