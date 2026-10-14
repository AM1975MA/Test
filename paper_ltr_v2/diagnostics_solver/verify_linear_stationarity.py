"""Independent gradient certificate for saved linear models; never fits."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as v1

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def independent_gradient(x,w,labels,groups,l2=.001):
    residual=np.zeros(len(x),dtype=np.float64)
    for ix in groups:
        s=x[ix]@w;s=s-s.max();p=np.exp(s);p/=p.sum()
        q=np.exp(labels[ix].astype(float)-labels[ix].max());q/=q.sum()
        residual[ix]=(p-q)/len(groups)
    return x.T@residual+l2*w

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--candidate',required=True)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--out',required=True)
    args=ap.parse_args();root=Path(args.candidate)
    result=json.loads((root/'RESULT.json').read_text(encoding='utf-8'))
    assert result['variant']=='LINEAR_NUMERICAL_REPAIR' and result['status']=='PAPER_LTR_V2_COMPLETE'
    panels={}
    for i in (1,2,3):
        path=Path(getattr(args,f'r{i}'))/'TI_COMPACT.parquet'
        assert sha(path)==result['input_sha256'][str(i)]
        f=pd.read_parquet(path)
        for key in ('signal_date','exit_date_21'):f[key]=pd.to_datetime(f[key])
        panels[i]=f
    records=[]
    for year in range(2017,2027):
        cutoff=pd.Timestamp(year,1,1)
        for i in (1,2,3):
            f=panels[i];valid=f[v1.FEATURES].notna().sum(axis=1)>=30
            train=f[(f.signal_date<cutoff)&(f.exit_date_21<cutoff)&f.target_rank_21.notna()&valid].sort_values(v1.KEYS).reset_index(drop=True)
            sub,_,_=v1.split_training(train,year)
            meta=result['per_year'][str(year)]['transforms'][str(i)]
            assert v1.keys_hash(train)==meta['train_keys_sha256']
            assert v1.keys_hash(sub)==meta['subtrain_keys_sha256']
            assert len(meta['saved_models'])==len(meta['seeds'])==1
            path=root/'models'/Path(meta['saved_models'][0]).name
            assert sha(path)==result['model_files_sha256'][path.relative_to(root).as_posix()]
            with np.load(path,allow_pickle=False) as z:
                state={key:z[key] for key in ('median','mean','scale')};w=z['w']
                for key,value in state.items():assert v1.array_hash(value)==meta['learned_state_hashes'][key]
                assert v1.array_hash(w)==meta['seeds'][0]['parameter_sha256']['w']
                x=v1.transform(v1.raw_matrix(sub),state)
                assert v1.array_hash(x)==meta['fit_matrix_sha256']
                g=independent_gradient(x,w,v1.decile_labels(sub),v1.query_indices(sub))
            norm=float(np.max(np.abs(g)));declared=meta['seeds'][0]['gradient_inf_norm']
            assert np.isfinite(norm) and norm<=1e-7
            assert abs(norm-declared)<=1e-12
            records.append(dict(year=year,repeat=i,gradient_inf_norm=norm,declared=declared,
                                absolute_difference=abs(norm-declared),model_sha256=sha(path),PASS=True))
    assert len(records)==30
    report=dict(status='THIRTY_LINEAR_GRADIENTS_INDEPENDENTLY_VERIFIED',
        variant=result['variant'],records=records,all_PASS=True,new_fits_executed=0,
        maximum_residual=max(r['gradient_inf_norm'] for r in records),
        maximum_difference=max(r['absolute_difference'] for r in records),
        result_sha256=sha(root/'RESULT.json'),input_sha256=result['input_sha256'],
        numerical_repair=result['numerical_repair'],checker_sha256=sha(__file__),
        numpy=np.__version__)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('status','maximum_residual','maximum_difference','new_fits_executed')}))

if __name__=='__main__':main()
