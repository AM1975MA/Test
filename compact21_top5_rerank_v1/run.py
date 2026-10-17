"""Read-only recombination of two historically OOS Compact21 archives."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from compact21_top5_rerank_v1.core import VARIANT,KEYS,TOP_K,rerank
from compact21_predictive_v2.metrics import evaluate,paired_compare
from pls_xgb_v1.run import verify_keys,disagreement
from paper_ltr_v2.replay import sha

TABLES=("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet")

def load_archive(root,expected_variant,expected_status):
    path=Path(root);result=json.loads((path/"RESULT.json").read_text())
    if result.get("status")!=expected_status or result.get("variant")!=expected_variant:
        raise ValueError("Historical research prediction archive identity mismatch")
    if set(result.get("per_year",{}))!=set(map(str,range(2017,2027))):
        raise ValueError("10-year OOS contract incomplete")
    if expected_variant!="BASE" and result.get("ALL_MATURITY_PASS") is not True:
        raise ValueError("Economic layer annual target maturity not certified")
    frames={}
    for name in TABLES:
        p=path/name
        if result.get("files_sha256",{}).get(name)!=sha(p):
            raise ValueError("Unverified original prediction byte hash "+str(p))
        frames[name]=pd.read_parquet(p)
    return result,frames

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--base",required=True)
    p.add_argument("--old-layer",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Fresh output directory required")
    original,b=load_archive(a.base,"BASE","COMPACT21_PREDICTIVE_V2_COMPLETE")
    economic,e=load_archive(a.old_layer,"ECON_LAYER_OOS30","PAPER_LTR_V2_COMPLETE")
    if original.get("ALL_DETERMINISM_PASS") is not True or original.get("LEGACY_PARITY_PASS") is not True:
        raise ValueError("BASE parity/determinism not certified")
    if economic.get("layer_trainings")!=24 or economic.get("base_fallbacks")!=6:
        raise ValueError("Original economic OOS training provenance changed")
    if original.get("input_sha256")!=economic.get("input_sha256"):
        raise ValueError("BASE source identity differs from economic layer")
    for year in range(2017,2027):
        for vintage in ("1","2","3"):
            original_detail=economic["per_year"][str(year)]["transforms"][vintage]
            for key in ("train_keys_sha256","subtrain_keys_sha256","validation_keys_sha256",
                        "train_matrix_sha256","train_labels_sha256"):
                if not original_detail.get(key):
                    raise ValueError("Incomplete original annual raw-source linkage")
            if original_detail.get("baseline_model_retraining") is not False or original_detail.get("layer_prediction_determinism_PASS") is not True:
                raise ValueError("Original economic meta predictor not independently certified")
            trained=original_detail["meta_learning"]["fallback"] is False
            if (year<=2018 and trained) or (year>=2019 and not trained):
                raise ValueError("Unexpected per-year economic layer OOS availability")
    out.mkdir(parents=True)
    maps={};audits={}
    for name in TABLES:
        verify_keys(e[name],b[name])
        if name=="NATIVE_PREDICTIONS.parquet":
            bb=b[name].assign(vintage=b[name].vintage.astype(str)).sort_values(list(KEYS)).reset_index(drop=True)
            ee=e[name].assign(vintage=e[name].vintage.astype(str)).sort_values(list(KEYS)).reset_index(drop=True)
            for col in ("target_rank_21","target_ret_21","exit_date_21"):
                if col not in bb or col not in ee:
                    raise ValueError("Missing immutable realized label "+col)
                x=bb[col];y=ee[col]
                if col=="exit_date_21":x=pd.to_datetime(x);y=pd.to_datetime(y)
                if not x.equals(y):raise ValueError("Different realized label from original BASE")
        table,group_checks=rerank(b[name],e[name])
        verify_keys(table,b[name])
        # Explicitly preserve each early-year BASE fallback.
        table_year=pd.to_datetime(table.signal_date).dt.year
        mask=table_year<=2018
        left=table.loc[mask].sort_values(list(KEYS)).pred.to_numpy(float)
        right=b[name].assign(vintage=b[name].vintage.astype(str)).loc[
            pd.to_datetime(b[name].signal_date).dt.year<=2018].sort_values(list(KEYS)).pred.to_numpy(float)
        if not np.array_equal(left,right):
            raise ValueError("Early BASE fallback no longer exact")
        maps[name]=table
        audits[name]=group_checks
    folder=out/VARIANT;folder.mkdir()
    for name in TABLES:maps[name].to_parquet(folder/name,index=False)
    base_qa=evaluate(b[TABLES[0]],quality_exit_cutoff="2026-07-01")
    candidate_qa=evaluate(maps[TABLES[0]],quality_exit_cutoff="2026-07-01")
    if base_qa["coverage"]!=candidate_qa["coverage"]:
        raise ValueError("Prediction outcome coverage changed")
    paired=paired_compare(candidate_qa,base_qa,block_lengths=(3,6,12),
                          n_bootstrap=1000,seed=20261017)
    base_stability=disagreement(b[TABLES[1]])
    candidate_stability=disagreement(maps[TABLES[1]])
    summaries={}
    for name in TABLES:
        detail=audits[name]
        summaries[name]=dict(month_source_queries=len(detail),
             top1_changed=int(sum(rec["top1_changed"] for rec in detail)),
             top1_changed_fraction=float(np.mean([rec["top1_changed"] for rec in detail])),
             score_reassignments=int(sum(rec["changed_score_count"] for rec in detail)),
             preserved_all_base_top5=True,preserved_all_below5=True,
             preserved_all_score_multisets=True)
    manifest=dict(status="PAPER_LTR_V2_COMPLETE",variant=VARIANT,
        per_year=economic["per_year"],input_sha256=original["input_sha256"],
        ALL_MATURITY_PASS=True,baseline_model_retraining=False,layer_fits=0,
        base_result_sha256=sha(Path(a.base)/"RESULT.json"),
        old_layer_result_sha256=sha(Path(a.old_layer)/"RESULT.json"),
        protocol_sha256=sha(ROOT/"compact21_top5_rerank_v1/PROTOCOL.md"),
        purely_score_permutation=True,original_layer_fit_reused=True,
        topk=TOP_K,predictive=candidate_qa,stability=candidate_stability,
        inference_audits=summaries,production_adoption=False,
        files_sha256={name:sha(folder/name) for name in TABLES})
    (folder/"RESULT.json").write_text(json.dumps(manifest,indent=2,allow_nan=False)+"\n")
    summary=dict(status="TOP5_RERANK_PREDICTIVE_COMPLETE",variant=VARIANT,
        base_predictive=base_qa["aggregate_by_date"],
        old_layer_predictive=economic["predictive"]["aggregate_by_date"],
        candidate_predictive=candidate_qa["aggregate_by_date"],
        primary="top1_return_regret_vs_topdecile_mean",paired_vs_base=paired,
        base_stability=base_stability,candidate_stability=candidate_stability,
        audits=summaries,source_vintages_correlated=True,archive_scores_reused=True,
        base_seed_fits=0,new_layer_fits=0,production_adoption=False,
        historical_data_reused=True)
    (out/"SUMMARY.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps({key:summary[key] for key in
        ("status","base_predictive","old_layer_predictive","candidate_predictive",
         "base_stability","candidate_stability","audits")},indent=2),flush=True)
if __name__=="__main__":main()
