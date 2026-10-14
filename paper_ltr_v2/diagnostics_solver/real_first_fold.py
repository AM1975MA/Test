"""Training-only reproduction of the failed first fold, never a portfolio test."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as v1
from paper_ltr_v2.diagnostics_solver.synthetic_audit import traced_solver

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--panel',required=True)
    ap.add_argument('--original',required=True)
    ap.add_argument('--failed',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args()
    assert np.__version__=='2.3.5', 'Frozen numeric version required'
    assert platform.python_version().startswith('3.13.')
    original=json.loads(Path(args.original).read_text(encoding='utf-8'))
    failed=json.loads(Path(args.failed).read_text(encoding='utf-8'))
    assert failed['status']=='PAPER_LTR_V2_FAILED'
    assert sha(args.panel)==original['input_sha256']['1']==failed['input_sha256']['1']
    assert sha(v1.__file__)==original['sources']['paper_ltr_v1/learner.py']
    old=original['per_year']['2017']['transforms']['1']
    frame=pd.read_parquet(args.panel)
    for c in ('signal_date','exit_date_21'):frame[c]=pd.to_datetime(frame[c])
    cutoff=pd.Timestamp('2017-01-01')
    valid=frame[v1.FEATURES].notna().sum(axis=1)>=30
    train=frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)&frame.target_rank_21.notna()&valid].sort_values(v1.KEYS).copy()
    sub,val,_=v1.split_training(train,2017)
    state=v1.fit_transform_state(v1.raw_matrix(sub))
    x=v1.transform(v1.raw_matrix(sub),state)
    labels=v1.decile_labels(sub);groups=v1.query_indices(sub)
    fingerprints=dict(train_keys_sha256=v1.keys_hash(train),
        train_matrix_sha256=v1.array_hash(v1.raw_matrix(train)),
        train_labels_sha256=v1.array_hash(v1.decile_labels(train)),
        subtrain_keys_sha256=v1.keys_hash(sub),validation_keys_sha256=v1.keys_hash(val),
        fit_matrix_sha256=v1.array_hash(x),
        validation_matrix_sha256=v1.array_hash(v1.transform(v1.raw_matrix(val),state)))
    assert all(old[k]==v for k,v in fingerprints.items()),'Original fold fingerprints differ'
    result=traced_solver(x,labels,groups)
    result.update(scope='Reproduction of failed first-fold training only; no out-of-sample scoring or CAGR',
        variant='ORIGINAL_LINEAR_DIAGNOSTIC_NOT_A_NEW_MODEL',
        original_failure=failed['failure'],
        identity_PASS=True,year=2017,repeat=1,rows=len(x),features=x.shape[1],queries=len(groups),
        fingerprints=fingerprints,input_sha256=sha(args.panel),original_result_sha256=sha(args.original),
        failed_result_sha256=sha(args.failed),
        python=platform.python_version(),numpy=np.__version__,
        environment={k:os.environ.get(k) for k in ('NPY_DISABLE_CPU_FEATURES','OPENBLAS_CORETYPE','OPENBLAS_NUM_THREADS')},
        sources_sha256={str(p):sha(p) for p in (Path(v1.__file__).relative_to(Path.cwd()),Path('paper_ltr_v2/learner.py'),Path(__file__).relative_to(Path.cwd()),Path('paper_ltr_v2/diagnostics_solver/synthetic_audit.py'))})
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    (out/'REAL_FIRST_FOLD.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('success','error','identity_PASS','rows','features','queries','last_accepted_pair_iteration','skipped_pairs','minimum_residual','terminal_fixed_metric_local_contraction_radius') if k in result},indent=2))

if __name__=='__main__':main()
