"""Reconstruct PCA and independently certify all thirty projected optima; no learner fits."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from linear_pca_v1.basis import fit_basis
from linear_pca_v1.core import VARIANT,DISCARDED,THRESHOLD
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames
from paper_ltr_v2.replay import sha
from paper_ltr_v2.diagnostics_solver.verify_linear_stationarity import independent_gradient

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);ap.add_argument('--out',required=True)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    a=ap.parse_args();root=Path(a.candidate);result=json.loads((root/'RESULT.json').read_text())
    if result['variant']!=VARIANT or result['status']!='PAPER_LTR_V2_COMPLETE':raise ValueError('Candidate incomplete')
    panels={}
    for i in (1,2,3):
        path=Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet'
        if sha(path)!=result['input_sha256'][str(i)]:raise ValueError('Input changed')
        f=pd.read_parquet(path)
        for c in ('signal_date','exit_date_21'):f[c]=pd.to_datetime(f[c])
        panels[i]=f
    tables=[]
    for name in ('COMMON_PREDICTIONS.parquet','NATIVE_PREDICTIONS.parquet'):
        if sha(root/name)!=result['files_sha256'][name]:raise ValueError('Predictions changed')
        tables.append(pd.read_parquet(root/name))
    records=[]
    for year in range(2017,2027):
        trains,tests,common=annual_frames(panels,year)
        for i in (1,2,3):
            sub,_,_=v1.split_training(trains[i],year)
            meta=result['per_year'][str(year)]['transforms'][str(i)]
            if not (sub.exit_date_21<pd.Timestamp(year,1,1)).all():raise ValueError('Immature training')
            path=root/'models'/Path(meta['saved_models'][0]).name
            if sha(path)!=result['model_files_sha256'][path.relative_to(root).as_posix()]:raise ValueError('Model changed')
            with np.load(path,allow_pickle=False) as z:
                state={key:z[key].copy() for key in ('median','mean','scale')}
                w=z['w'].copy();beta=z['w_pc'].copy();basis=z['pca_basis'].copy();ev=z['pca_eigenvalues'].copy();k=int(z['pca_components'])
            learned=v1.fit_transform_state(v1.raw_matrix(sub))
            for key in state:np.testing.assert_array_equal(state[key],learned[key])
            x=v1.transform(v1.raw_matrix(sub),state);q,expected_ev,expected_k=fit_basis(x,threshold=THRESHOLD)
            expected_basis=q[:,expected_k:] if DISCARDED else q[:,:expected_k]
            if k!=expected_basis.shape[1]:raise ValueError('PCA dimension mismatch')
            np.testing.assert_allclose(ev,expected_ev,rtol=0,atol=1e-10)
            np.testing.assert_allclose(basis@basis.T,expected_basis@expected_basis.T,rtol=0,atol=1e-10)
            np.testing.assert_allclose(basis.T@basis,np.eye(k),rtol=0,atol=1e-12)
            np.testing.assert_allclose(w,basis@beta,rtol=0,atol=1e-14)
            gradient=independent_gradient(x@basis,beta,v1.decile_labels(sub),v1.query_indices(sub))
            residual=float(np.max(np.abs(gradient)))
            if residual>1e-7:raise ValueError('Projected gradient failed')
            for table,test in zip(tables,(common,tests[i])):
                f=table[(table.vintage.astype(int)==i)&(table.signal_date.dt.year==year)].sort_values(v1.KEYS).reset_index(drop=True)
                pd.testing.assert_frame_equal(f[v1.KEYS],test[v1.KEYS].reset_index(drop=True),check_exact=True)
                np.testing.assert_allclose(v1.transform(v1.raw_matrix(test),state)@w,f.pred,rtol=0,atol=1e-12)
            records.append(dict(year=year,repeat=i,components=k,variance_retained=float((ev[expected_k:] if DISCARDED else ev[:expected_k]).sum()/ev.sum()),
                                projected_gradient_inf=residual,full_rotation_error=meta['full_rotation_score_max_error'],PASS=True))
    if len(records)!=30:raise ValueError('Missing folds')
    report=dict(status=VARIANT+'_THIRTY_FOLDS_VERIFIED',all_PASS=True,records=records,
                maximum_projected_gradient=max(r['projected_gradient_inf'] for r in records),new_learner_fits=0,
                candidate_result_sha256=sha(root/'RESULT.json'))
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records'}))

if __name__=='__main__':main()
