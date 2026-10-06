"""Frozen original-feature BASE query-weight block bagging annual cloud trial."""
from __future__ import annotations
import argparse
import copy
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/"vendor/etf_trader_v2/src")]
from etf_trader.source_only import kernel as k
from compact21_learner_swap_v1 import learners
from compact21_learner_swap_v1.run_benchmark import evaluation_coverage, score_gap, compare_native
from compact21_predictive_v2.run import numerical_gate, predictions_frame
from compact21_predictive_v2.summarize import normalized_numeric
from compact21_semidev_v1.run import (select_original_frames, original_controls, source_gate,
    retained_slice, compare_retained, FROZEN_TI)
from compact21_semidev_v1.view import sha
from ranker_stability_v1.run_ranker_benchmark_full import load, stability, quality

LINE = "COMPACT21_BLOCKBAG_V1"
VARIANT = "BASE_BLOCKBAG"
KEYS = ["signal_date", "ticker"]
PAIRS = ((1,2),(1,3),(2,3))
RECIPE = {"bags": 4, "block_length_queries": 3, "noncircular": True,
          "weight_rng_seed": 20261005, "seed_sequence": "[20261005, year, bag_index_0_to_3]",
          "group_weights": "query occurrence bincount; no cohort row duplication",
          "quantile_sketch": "original unweighted full cohort",
          "aggregation": "canonical seed mean; four bag mean float64 then cast canonical float32",
          "seed_models": 12, "baseline_seed_models": 3}


def query_weights(n, year):
    if n < 3:
        raise ValueError("At least three training queries required")
    weights = []
    for bag in range(4):
        rng = np.random.default_rng(np.random.SeedSequence([20261005, year, bag]))
        starts = rng.integers(0, n-3+1, size=(n+2)//3)
        sampled = (starts[:, None]+np.arange(3)[None, :]).ravel()[:n]
        weights.append(np.bincount(sampled, minlength=n).astype(np.float64))
    return np.stack(weights)


def query_contract(trains, year):
    original = trains[1][KEYS].reset_index(drop=True)
    for i in (2,3):
        pd.testing.assert_frame_equal(original, trains[i][KEYS].reset_index(drop=True), check_exact=True)
    groups = trains[1].groupby("signal_date", sort=True).size()
    dates = groups.index.to_numpy(dtype="datetime64[ns]")
    if not (np.diff(groups.index.to_period("M").asi8) == 1).all():
        raise ValueError("Training calendar gap cannot be bridged by block sampling")
    sizes = groups.to_numpy(dtype=np.int64)
    weights = query_weights(len(dates), year)
    if not (weights.sum(axis=1) == len(dates)).all():
        raise ValueError("Invalid sampled query count")
    keys_hash = hashlib.sha256(original.to_csv(index=False, lineterminator="\n").encode()).hexdigest()
    audit = {"recipe": RECIPE, "same_keys_all_vintages": True, "query_count": len(dates),
             "query_dates_sha256": learners.array_hash(dates),
             "group_sizes_sha256": learners.array_hash(sizes),
             "weights_sha256": learners.array_hash(weights),
             "bag_weights_sha256": [learners.array_hash(w) for w in weights],
             "train_keys_sha256_lf": {str(i): keys_hash for i in (1,2,3)}}
    return dates, sizes, weights, audit


def weighted_fit(train, tests, year, tmp, tag, weights):
    cutoff = learners.validate(train, tests, year)
    X = learners.matrix(train); T = [learners.matrix(z) for z in tests]
    y = (train.target_rank_21.clip(0,1)*100).round().astype(int).to_numpy()
    groups = train.groupby("signal_date", sort=True).size().to_numpy()
    weights = np.asarray(weights, dtype=np.float64)
    if weights.shape != groups.shape or not np.isfinite(weights).all() or (weights<0).any() or weights.sum()<=0:
        raise ValueError("Invalid ranking query weights")
    params = dict(k.COMPACT_PARAMS); rounds=int(params.pop("n_estimators")); params.pop("n_jobs",None)
    meta = {"kind": "BASE", "feature_transform": "identity", "target": "canonical_round_rank_times_100",
        "train_matrix_sha256": learners.array_hash(X.to_numpy()), "train_labels_sha256": learners.array_hash(y),
        "fit_matrix_sha256": learners.array_hash(X.to_numpy()), "train_groups_sha256": learners.array_hash(groups),
        "train_rows": len(train), "test_matrix_sha256": [learners.array_hash(t.to_numpy()) for t in T],
        "test_fit_matrix_sha256": [learners.array_hash(t.to_numpy()) for t in T], "feature_names": list(k.F2D_FEATURES),
        "cutoff": cutoff.isoformat(), "max_signal_date": train.signal_date.max().isoformat(),
        "max_exit_date_21": train.exit_date_21.max().isoformat(), "maturity_PASS": True,
        "learned_state_hashes": {}, "seed_prediction_sha256": {},
        "model_params": dict(params,n_estimators=rounds,threads=1,seeds=list(k.COMPACT_SEEDS)),
        "group_weights_sha256": learners.array_hash(weights)}
    tmp = Path(tmp); tmp.mkdir(parents=True, exist_ok=True)
    data = tmp/f"{tag}.npz"
    np.savez(data, Xtr=X.to_numpy(), Xte=pd.concat(T).to_numpy(), y=y, groups=groups, group_weights=weights)
    byseed=[]; start=time.perf_counter()
    for seed in k.COMPACT_SEEDS:
        out=tmp/f"{tag}_{seed}.npy"
        subprocess.run([sys.executable,str(Path(__file__).with_name("weighted_worker.py")),
            "--data",str(data),"--seed",str(seed),"--threads","1","--rounds",str(rounds),
            "--params-json",json.dumps(params),"--output",str(out)],check=True,capture_output=True,text=True)
        p=np.load(out, allow_pickle=False); byseed.append(p)
        meta["seed_prediction_sha256"][str(seed)] = learners.array_hash(p)
    pred=np.mean(byseed,axis=0); ans=[]; pos=0
    for t in T:
        ans.append(pred[pos:pos+len(t)]); pos+=len(t)
    if any(len(p)!=len(t) or not np.isfinite(p).all() for p,t in zip(ans,T)):
        raise ValueError("Invalid weighted predictions")
    meta["prediction_sha256"]=[learners.array_hash(p) for p in ans]
    return ans,meta,y,time.perf_counter()-start


def aggregate_bags(values):
    a=np.asarray(values)
    return np.mean(a,axis=0,dtype=np.float64).astype(a.dtype)


def ensemble_fit(train, tests, year, tmp, tag, weights):
    predictions=[]; bags={}; seconds=0
    for b,w in enumerate(weights):
        p,a,_,elapsed=weighted_fit(train,tests,year,tmp,f"{tag}_bag{b}",w)
        predictions.append(p); bags[str(b)]=a; seconds+=elapsed
    bag_vectors=np.stack([np.concatenate(p) for p in predictions])
    np.save(Path(tmp)/f"{tag}_bag_predictions.npy",bag_vectors)
    result=[aggregate_bags([p[j] for p in predictions]) for j in range(len(tests))]
    audit=copy.deepcopy(bags["0"])
    audit.update(kind=VARIANT, bags=bags, model_params={"recipe": RECIPE, "canonical": bags["0"]["model_params"]},
        group_weights_sha256=[a["group_weights_sha256"] for a in bags.values()],
        bag_prediction_sha256={b:a["prediction_sha256"] for b,a in bags.items()},
        seed_prediction_sha256={}, prediction_sha256=[learners.array_hash(p) for p in result])
    return result,audit,seconds


def weighted_controls(trains, tests, common, year, reference, native_reference, common_reference, scratch):
    controls={}; audits={}; native=[]; common_frames=[]
    for i in (1,2,3):
        n=trains[i].signal_date.nunique()
        p,a,_,elapsed=weighted_fit(trains[i],[common,tests[i]],year,scratch,f"ones_{year}_{i}",np.ones(n,dtype=np.float64))
        old=reference["per_year"][str(year)]["transforms"][str(i)]
        without_weight={name:value for name,value in a.items() if name!="group_weights_sha256"}
        if without_weight!=old:
            raise ValueError("All-ones weighted worker complete audit differs from canonical BASE")
        if any(aggregate_bags([v]*4).tobytes()!=v.tobytes() for v in p):
            raise ValueError("All-ones four-bag aggregate differs from canonical BASE")
        native.append(compare_retained(tests[i],p[1],retained_slice(native_reference,year,i),True))
        common_frames.append(compare_retained(common,p[0],retained_slice(common_reference,year,i),False))
        audits[str(i)]=a
        controls[str(i)]={"common_bytes_exact":True,"native_bytes_exact":True,"learned_audit_exact":True,
                          "four_bag_aggregate_bytes_exact":True,"fit_seconds":elapsed}
    return controls,audits,pd.concat(native,ignore_index=True),pd.concat(common_frames,ignore_index=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year",type=int,required=True,choices=range(2017,2027))
    for name in ("r1","r2","r3","reference","out"):
        parser.add_argument("--"+name,type=Path,required=True)
    a=parser.parse_args(); numeric=numerical_gate()
    if a.out.exists() and any(a.out.iterdir()): raise ValueError("Output must be fresh")
    a.out.mkdir(parents=True,exist_ok=True)
    paths={i:getattr(a,f"r{i}") for i in (1,2,3)}
    hashes={str(i):sha(paths[i]/"TI_COMPACT.parquet") for i in paths}
    if hashes!=FROZEN_TI: raise ValueError("Wrong original TI snapshots")
    reference_path=a.reference/"RESULT.json"; reference=json.loads(reference_path.read_text())
    if reference.get("status")!="COMPACT21_PREDICTIVE_V2_COMPLETE" or reference.get("variant")!="BASE" or reference.get("input_sha256")!=hashes:
        raise ValueError("Wrong retained original BASE")
    if normalized_numeric(numeric)!=normalized_numeric(reference["numeric_contract"]): raise ValueError("Numeric profile mismatch")
    canonical_sources=source_gate(reference)
    for name in ("NATIVE_PREDICTIONS.parquet","COMMON_PREDICTIONS.parquet"):
        if reference.get("files_sha256",{}).get(name)!=sha(a.reference/name): raise ValueError("Reference file hash mismatch")
    native_reference=pd.read_parquet(a.reference/"NATIVE_PREDICTIONS.parquet")
    common_reference=pd.read_parquet(a.reference/"COMMON_PREDICTIONS.parquet")
    frames={i:load(paths[i]) for i in paths}; trains,tests,common=select_original_frames(frames,a.year)
    dates,sizes,weights,wa=query_contract(trains,a.year)
    np.savez(a.out/"WEIGHTS.npz",query_dates=dates,group_sizes=sizes,weights=weights)
    sources={p.relative_to(ROOT).as_posix():sha(p) for p in sorted(Path(__file__).parent.glob("*.py"))}
    sources.update(canonical_sources)
    for p in ("compact21_semidev_v1/run.py","compact21_semidev_v1/view.py"):
        sources[p]=sha(ROOT/p)
    result={"status":"RUNNING","line":LINE,"variant":VARIANT,"years":[a.year],"input_sha256":hashes,
        "per_year":{},"numeric_contract":numeric,"python":sys.version,"sources":sources,"fit_sources":canonical_sources,
        "environment":{n:importlib.metadata.version(n) for n in ("numpy","pandas","scikit-learn","xgboost","lightgbm","scipy","pyarrow")},
        "baseline_input_contract":reference["input_contract"],
        "preregistration_sha256":sha(Path(__file__).with_name("PREREGISTRATION.md")),
        "input_contract":{"line":LINE,"original_ti_sha256":hashes,"signal_cutoff":"2026-06-30",
            "quality_exit_cutoff":"2026-07-01","common_inference_repeat":2,"train_cohorts":"original_native_frozen",
            "changed_columns":[],"recipe":RECIPE,"ref_base_result_sha256":sha(reference_path),
            "reference_prediction_sha256":reference["files_sha256"]},
        "negative_feedback_changed":False,"portfolio_evaluation":False,"production_adoption":False}
    (a.out/"INPUT_CONTRACT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    pcs={}; pns={}; audits={}; times={}; refits={}; native=[]; common_frames=[]; bag_vectors={}
    with tempfile.TemporaryDirectory() as td:
        scratch=Path(td)
        controls,control_audits,cn,cc=original_controls(trains,tests,common,a.year,reference,native_reference,common_reference,scratch)
        wc,wca,wn,wcom=weighted_controls(trains,tests,common,a.year,reference,native_reference,common_reference,scratch)
        # All six controls have passed before any candidate is fitted.
        for name,frame in (("CONTROL_NATIVE_PREDICTIONS",cn),("CONTROL_COMMON_PREDICTIONS",cc),
                           ("WEIGHTED_CONTROL_NATIVE_PREDICTIONS",wn),("WEIGHTED_CONTROL_COMMON_PREDICTIONS",wcom)):
            frame.to_parquet(a.out/(name+".parquet"),index=False)
        (a.out/"CONTROL_GATE.json").write_text(json.dumps({"PASS":True,"legacy":controls,"weighted":wc},indent=2)+"\n")
        for i in (1,2,3):
            p,audit,elapsed=ensemble_fit(trains[i],[common,tests[i]],a.year,scratch,f"bag_{a.year}_{i}",weights)
            again,again_audit,_=ensemble_fit(trains[i],[common,tests[i]],a.year,scratch,f"refit_{a.year}_{i}",weights)
            if audit!=again_audit or any(x.dtype!=y.dtype or x.tobytes()!=y.tobytes() for x,y in zip(p,again)):
                raise ValueError("Independent candidate refit differs")
            retained_bags=np.load(scratch/f"bag_{a.year}_{i}_bag_predictions.npy",allow_pickle=False)
            refit_bags=np.load(scratch/f"refit_{a.year}_{i}_bag_predictions.npy",allow_pickle=False)
            if retained_bags.dtype!=refit_bags.dtype or retained_bags.tobytes()!=refit_bags.tobytes():
                raise ValueError("Independent bag prediction vectors differ")
            bag_vectors[f"predictions_{i}"]=retained_bags
            pcs[i],pns[i]=p; audits[str(i)]=audit; times[str(i)]=elapsed
            refits[str(i)]={"common_bytes_exact":True,"native_bytes_exact":True,"learned_audit_exact":True,
                "refit_audit":again_audit,"prediction_sha256":again_audit["prediction_sha256"]}
            native.append(predictions_frame(tests[i],pns[i],i)); common_frames.append(common[KEYS].assign(pred=pcs[i],vintage=i))
    qualities={}
    for i in (1,2,3):
        mask=(tests[i].target_rank_21.notna() & tests[i].exit_date_21.notna() & tests[i].exit_date_21.le(pd.Timestamp("2026-07-01"))).to_numpy()
        if not mask.any(): raise ValueError("Empty annual mature quality")
        qualities[str(i)]=quality(tests[i].loc[mask],pns[i][mask])
    result["per_year"][str(a.year)]={"quality":qualities,"evaluation_coverage":evaluation_coverage(trains,tests,common),
        "common_inference":{f"{i}-{j}":stability(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
        "native_inference":compare_native(tests,pns),"common_score_gap":{f"{i}-{j}":score_gap(common[KEYS],pcs[i],pcs[j]) for i,j in PAIRS},
        "transforms":audits,"fit_seconds":times,"determinism_PASS":True,"legacy_control":controls,
        "control_transforms":control_audits,"weighted_control":wc,"weighted_control_transforms":wca,
        "independent_refits":refits,"weights_audit":wa}
    pd.concat(native,ignore_index=True).to_parquet(a.out/"NATIVE_PREDICTIONS.parquet",index=False)
    pd.concat(common_frames,ignore_index=True).to_parquet(a.out/"COMMON_PREDICTIONS.parquet",index=False)
    np.savez(a.out/"BAG_PREDICTIONS.npz",**bag_vectors)
    result.update(ALL_DETERMINISM_PASS=True,LEGACY_PARITY_PASS=True,WEIGHTED_PARITY_PASS=True)
    result["files_sha256"]={p.name:sha(p) for p in a.out.iterdir() if p.suffix in (".parquet",".npz")}
    result["status"]=LINE+"_COMPLETE"
    (a.out/"RESULT.json").write_text(json.dumps(result,indent=2,allow_nan=False)+"\n")
    print(json.dumps({"year":a.year,"variant":VARIANT,"status":result["status"],"legacy_parity":True,"weighted_parity":True}),flush=True)


if __name__=="__main__": main()
