"""All monthly state/input/gradient/inference checks, without fitting."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v1 import learner as v1
from paper_ltr_monthly_v1.core import MONTHS,mature_frame,split_at,fingerprints,sha
from paper_ltr_v2.diagnostics_solver.verify_linear_stationarity import independent_gradient

def verify_month_fingerprints(result,panel,repeat):
    if set(result.get('per_month',{}))!=set(MONTHS):raise ValueError('Monthly folds incomplete')
    records={}
    for month in MONTHS:
        train=mature_frame(panel,month+'-01');sub,val,_=split_at(train,month+'-01')
        actual=fingerprints(train,sub,val);expected=result['per_month'][month]['transforms'][str(repeat)]
        if any(expected.get(k)!=value for k,value in actual.items()):raise ValueError('Monthly fingerprints differ')
        records[month]=actual
    return dict(PASS=True,months=records)

def audit(candidate,panel_dirs,annual_root):
    from paper_ltr_v1.run import annual_frames
    root=Path(candidate);annual_root=Path(annual_root)
    result=json.loads((root/'RESULT.json').read_text(encoding='utf-8'))
    annual=json.loads((annual_root/'RESULT.json').read_text(encoding='utf-8'))
    if result['variant']!='LINEAR_MONTHLY' or result['status']!='PAPER_LTR_V2_COMPLETE':raise ValueError('Monthly run incomplete')
    panels={}
    for i in (1,2,3):
        p=Path(panel_dirs[i])/'TI_COMPACT.parquet'
        if sha(p)!=result['input_sha256'][str(i)]:raise ValueError('Input hash differs')
        f=pd.read_parquet(p)
        for c in ('signal_date','exit_date_21'):f[c]=pd.to_datetime(f[c])
        panels[i]=f
    forecast={}
    for name in ('COMMON_PREDICTIONS.parquet','NATIVE_PREDICTIONS.parquet'):
        if sha(root/name)!=result['files_sha256'][name]:raise ValueError('Prediction file changed')
        forecast[name]=pd.read_parquet(root/name)
    frames={y:annual_frames(panels,y) for y in range(2017,2027)}
    records=[];cached=0
    for month in MONTHS:
        year=int(month[:4]);_,tests,common=frames[year]
        for i in (1,2,3):
            train=mature_frame(panels[i],month+'-01');sub,val,start=split_at(train,month+'-01')
            meta=result['per_month'][month]['transforms'][str(i)]
            if any(meta.get(k)!=value for k,value in fingerprints(train,sub,val).items()):raise ValueError('Fold differs')
            path=root/'models'/Path(meta['saved_models'][0]).name
            if sha(path)!=result['model_files_sha256'][path.relative_to(root).as_posix()]:raise ValueError('Checkpoint hash differs')
            state=v1.fit_transform_state(v1.raw_matrix(sub))
            with np.load(path,allow_pickle=False) as z:
                w=z['w'].copy()
                if list(z['feature_names'])!=list(v1.FEATURES):raise ValueError('Feature order differs')
                for key,value in state.items():
                    if not np.array_equal(z[key],value) or v1.array_hash(value)!=meta['learned_state_hashes'][key]:raise ValueError('Training-only preprocessing differs')
                if v1.array_hash(w)!=meta['seeds'][0]['parameter_sha256']['w']:raise ValueError('Parameters differ')
            x=v1.transform(v1.raw_matrix(sub),state)
            if v1.array_hash(x)!=meta['fit_matrix_sha256']:raise ValueError('Transformed training differs')
            gradient=independent_gradient(x,w,v1.decile_labels(sub),v1.query_indices(sub))
            norm=float(np.max(np.abs(gradient)))
            if norm>1e-7 or abs(norm-meta['seeds'][0]['gradient_inf_norm'])>1e-12:raise ValueError('Independent stationarity failed')
            for j,(name,test) in enumerate(zip(('COMMON_PREDICTIONS.parquet','NATIVE_PREDICTIONS.parquet'),(common,tests[i]))):
                test=test[test.signal_date.dt.to_period('M').astype(str)==month].reset_index(drop=True)
                expected=v1.transform(v1.raw_matrix(test),state)@w
                f=forecast[name];f=f[(f.vintage.astype(str)==str(i))&(pd.to_datetime(f.signal_date).dt.to_period('M').astype(str)==month)].sort_values(v1.KEYS).reset_index(drop=True)
                if not f[v1.KEYS].equals(test[v1.KEYS]):raise ValueError('Inference keys differ')
                if not np.allclose(f.pred.to_numpy(),expected,rtol=0,atol=1e-12):raise ValueError('Checkpoint inference differs')
                if v1.array_hash(f.pred.to_numpy(float))!=meta['prediction_sha256'][j]:raise ValueError('Inference hash differs')
            if month.endswith('-01'):
                old=annual['per_year'][str(year)]['transforms'][str(i)]
                original=annual_root/'models'/Path(old['saved_models'][0]).name
                if sha(path)!=sha(original):raise ValueError('January model was not reused exactly')
                cached+=1
            records.append(dict(month=month,repeat=i,gradient_inf_norm=norm,PASS=True,
                reused_january=month.endswith('-01'),max_train_exit=train.exit_date_21.max().isoformat(),
                validation_start=start.isoformat(),max_subtrain_exit=sub.exit_date_21.max().isoformat()))
    if len(records)!=342 or cached!=30:raise ValueError('Unexpected state counts')
    return dict(status='MONTHLY_342_STATES_INDEPENDENTLY_VERIFIED',all_PASS=True,records=records,
        states=342,cached_january=30,new_fits_executed=0,maximum_residual=max(r['gradient_inf_norm'] for r in records),
        input_sha256=result['input_sha256'],result_sha256=sha(root/'RESULT.json'),checker_sha256=sha(__file__))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--candidate',required=True);ap.add_argument('--annual',required=True)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--out',required=True);a=ap.parse_args()
    r=audit(a.candidate,{i:getattr(a,f'r{i}') for i in (1,2,3)},a.annual)
    out=Path(a.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:r[k] for k in ('status','all_PASS','states','cached_january','maximum_residual')}))

if __name__=='__main__':main()
