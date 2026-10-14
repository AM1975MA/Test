"""Monthly LINEAR walk-forward on three frozen Original149 downloads."""
import argparse
import json
import sys
from pathlib import Path
import pandas as pd
from paper_ltr_monthly_v1.core import MONTHS,VARIANT,sha,fit_month

ROOT=Path(__file__).resolve().parents[1]
ANNUAL_SHA='19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f'

def write(out,result):
    pending=out/'RESULT.pending.json'
    pending.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    pending.replace(out/'RESULT.json')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--annual',required=True);ap.add_argument('--baseline',required=True)
    ap.add_argument('--out',required=True);args=ap.parse_args()
    from paper_ltr_v1 import learner as v1
    from paper_ltr_v1.run import annual_frames,verified_baseline
    from compact21_predictive_v2.run import numerical_gate,predictions_frame
    from compact21_predictive_v2.metrics import evaluate
    from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
    numeric=numerical_gate()
    annual_root=Path(args.annual);annual=json.loads((annual_root/'RESULT.json').read_text(encoding='utf-8'))
    if sha(annual_root/'RESULT.json')!=ANNUAL_SHA or annual['variant']!='LINEAR_NUMERICAL_REPAIR' or annual['status']!='PAPER_LTR_V2_COMPLETE':raise ValueError('Wrong annual reference')
    if annual['numerical_repair']['repair_source_sha256']!=sha(solver.__file__):raise ValueError('Solver changed')
    if annual['sources']['paper_ltr_v1/learner.py']!=sha(v1.__file__):raise ValueError('Original recipe changed')
    panels={};hashes={}
    for i in (1,2,3):
        path=Path(getattr(args,f'r{i}'))/'TI_COMPACT.parquet';hashes[str(i)]=sha(path)
        f=pd.read_parquet(path)
        for c in ('signal_date','exit_date_21'):f[c]=pd.to_datetime(f[c])
        panels[i]=f
    if hashes!=annual['input_sha256']:raise ValueError('Changed frozen inputs')
    _,base_audit=verified_baseline(args.baseline,hashes,panels)
    names=('COMMON_PREDICTIONS.parquet','NATIVE_PREDICTIONS.parquet')
    original=[]
    for name in names:
        if sha(annual_root/name)!=annual['files_sha256'][name]:raise ValueError('Annual predictions changed')
        original.append(pd.read_parquet(annual_root/name))
    out=Path(args.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new')
    out.mkdir(parents=True,exist_ok=True)
    result=dict(status='LINEAR_MONTHLY_RUNNING',variant=VARIANT,per_month={},per_year={},
        input_sha256=hashes,preregistration_sha256=sha(Path(__file__).with_name('PREREGISTRATION.md')),
        annual_reference=dict(run=38580178650,result_sha256=ANNUAL_SHA),baseline=base_audit,
        numerical_repair=annual['numerical_repair'],numeric_contract=numeric,
        sources={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')},
        source_solver_sha256=sha(solver.__file__),feature_recipe_sha256=sha(v1.__file__),
        new_fits_executed=0,cached_january_states=0,production_adoption=False)
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    native=[];common_frames=[];common_quality=[]
    try:
        annual_data={year:annual_frames(panels,year) for year in range(2017,2027)}
        for month in MONTHS:
            year=int(month[:4]);_,annual_tests,annual_common=annual_data[year]
            tests={i:f[f.signal_date.dt.to_period('M').astype(str)==month].reset_index(drop=True) for i,f in annual_tests.items()}
            common=annual_common[annual_common.signal_date.dt.to_period('M').astype(str)==month].reset_index(drop=True)
            if common.empty or any(t.empty for t in tests.values()):raise ValueError('Empty monthly inference')
            metas={}
            for i in (1,2,3):
                predictions,meta=fit_month(panels[i],[common,tests[i]],month,i,out,annual_root,annual,original)
                pc,pn=predictions;metas[str(i)]=meta
                native.append(predictions_frame(tests[i],pn,i))
                cc=common[v1.KEYS].copy();cc['pred']=pc;cc['vintage']=i;common_frames.append(cc)
                common_quality.append(predictions_frame(common,pc,i))
                result['new_fits_executed']+=meta['new_seed_fits'];result['cached_january_states']+=meta['reused_seeds']
            result['per_month'][month]=dict(transforms=metas,maturity_PASS=True)
            if month.endswith('-01'):result['per_year'][str(year)]=dict(transforms=metas,maturity_PASS=True)
            pd.concat(native,ignore_index=True).to_parquet(out/names[1],index=False)
            pd.concat(common_frames,ignore_index=True).to_parquet(out/names[0],index=False)
            write(out,result)
            print(json.dumps(dict(month=month,new_fits=result['new_fits_executed'],cached=result['cached_january_states'])),flush=True)
        for actual,reference in zip((pd.concat(common_frames,ignore_index=True),pd.concat(native,ignore_index=True)),original):
            a=actual.assign(vintage=actual.vintage.astype(str)).sort_values(['vintage',*v1.KEYS])
            b=reference.assign(vintage=reference.vintage.astype(str)).sort_values(['vintage',*v1.KEYS])
            if not a[['vintage',*v1.KEYS]].reset_index(drop=True).equals(b[['vintage',*v1.KEYS]].reset_index(drop=True)):raise ValueError('Coverage differs from annual')
        if result['new_fits_executed']!=312 or result['cached_january_states']!=30:raise ValueError('Unexpected fit count')
        result.update(status='PAPER_LTR_V2_COMPLETE',ALL_MATURITY_PASS=True,
            predictive=evaluate(pd.concat(native,ignore_index=True),quality_exit_cutoff='2026-07-01'),
            predictive_common_repeat2=evaluate(pd.concat(common_quality,ignore_index=True),quality_exit_cutoff='2026-07-01'),
            files_sha256={name:sha(out/name) for name in names},
            model_files_sha256={p.relative_to(out).as_posix():sha(p) for p in sorted((out/'models').glob('*.npz'))})
        write(out,result)
        print(json.dumps(dict(status=result['status'],new_fits=312,cached=30)),flush=True)
    except Exception as exc:
        result.update(status='LINEAR_MONTHLY_FAILED',failure=str(exc));write(out,result);raise

if __name__=='__main__':main()
