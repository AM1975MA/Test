"""Thirty annual PCA95 fits; all existing annual controls reused."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from linear_pca_v1.core import fit,VARIANT,DISCARDED
from paper_ltr_monthly_v1.run import ANNUAL_SHA,write
from paper_ltr_v2.replay import sha

def main():
    ap=argparse.ArgumentParser()
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--annual',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    from paper_ltr_v1 import learner as v1
    from paper_ltr_v1.run import annual_frames,verified_baseline
    from compact21_predictive_v2.run import numerical_gate,predictions_frame
    from compact21_predictive_v2.metrics import evaluate
    from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
    numeric=numerical_gate()
    annual_root=Path(a.annual);annual=json.loads((annual_root/'RESULT.json').read_text())
    if sha(annual_root/'RESULT.json')!=ANNUAL_SHA:raise ValueError('Wrong annual reference')
    if annual['sources']['paper_ltr_v1/learner.py']!=sha(v1.__file__) or annual['numerical_repair']['repair_source_sha256']!=sha(solver.__file__):raise ValueError('Recipe changed')
    panels={};hashes={}
    for i in (1,2,3):
        path=Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet';hashes[str(i)]=sha(path)
        f=pd.read_parquet(path)
        for c in ('signal_date','exit_date_21'):f[c]=pd.to_datetime(f[c])
        panels[i]=f
    if hashes!=annual['input_sha256']:raise ValueError('Changed frozen inputs')
    _,base_audit=verified_baseline(a.baseline,hashes,panels)
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new')
    out.mkdir(parents=True,exist_ok=True)
    result=dict(status='PCA95_RUNNING',variant=VARIANT,per_year={},input_sha256=hashes,
                annual_reference=dict(result_sha256=ANNUAL_SHA,run=38580178650),baseline=base_audit,
                preregistration_sha256=sha(Path(__file__).with_name('RESIDUAL_PROTOCOL.md' if DISCARDED else 'PREREGISTRATION.md')),
                numerical_repair=annual['numerical_repair'],numeric_contract=numeric,new_fits_executed=0,
                sources={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')},production_adoption=False)
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(result,indent=2)+'\n')
    native=[];common_frames=[];common_quality=[];subspaces=[]
    names=('COMMON_PREDICTIONS.parquet','NATIVE_PREDICTIONS.parquet')
    try:
        for year in range(2017,2027):
            trains,tests,common=annual_frames(panels,year);metas={};bases={}
            for i in (1,2,3):
                predictions,meta=fit(trains[i],[common,tests[i]],year,i,out,annual_root,annual)
                pc,pn=predictions;metas[str(i)]=meta
                native.append(predictions_frame(tests[i],pn,i))
                cc=common[v1.KEYS].copy();cc['pred']=pc;cc['vintage']=i;common_frames.append(cc)
                common_quality.append(predictions_frame(common,pc,i))
                result['new_fits_executed']+=1
                with np.load(meta['saved_models'][0],allow_pickle=False) as z:bases[i]=z['pca_basis'].copy()
                print(json.dumps(dict(year=year,repeat=i,components=meta['pca_components'],variance=meta['pca_variance_retained'],gradient=meta['projected_independent_gradient_inf'])),flush=True)
            for i,j in ((1,2),(1,3),(2,3)):
                b,c=bases[i],bases[j];sing=np.linalg.svd(b.T@c,compute_uv=False)
                distance=float(np.sqrt(max(0.,(b.shape[1]+c.shape[1]-2*np.sum(sing**2))/(b.shape[1]+c.shape[1]))))
                subspaces.append(dict(year=year,pair=f'{i}-{j}',components1=b.shape[1],components2=c.shape[1],
                                      normalized_projector_distance=distance,max_principal_angle_deg=float(np.degrees(np.arccos(np.clip(sing.min(),0,1))))))
            result['per_year'][str(year)]=dict(transforms=metas,maturity_PASS=True)
            pd.concat(native,ignore_index=True).to_parquet(out/names[1],index=False)
            pd.concat(common_frames,ignore_index=True).to_parquet(out/names[0],index=False)
            write(out,result)
        for name,actual in zip(names,(pd.concat(common_frames,ignore_index=True),pd.concat(native,ignore_index=True))):
            ref=pd.read_parquet(annual_root/name)
            ka=actual.assign(vintage=actual.vintage.astype(str)).sort_values(['vintage',*v1.KEYS])
            kb=ref.assign(vintage=ref.vintage.astype(str)).sort_values(['vintage',*v1.KEYS])
            pd.testing.assert_frame_equal(ka[['vintage',*v1.KEYS]].reset_index(drop=True),kb[['vintage',*v1.KEYS]].reset_index(drop=True),check_exact=True)
        pd.DataFrame(subspaces).to_csv(out/'SUBSPACES.csv',index=False)
        result.update(status='PAPER_LTR_V2_COMPLETE',ALL_MATURITY_PASS=True,
                      predictive=evaluate(pd.concat(native,ignore_index=True),quality_exit_cutoff='2026-07-01'),
                      predictive_common_repeat2=evaluate(pd.concat(common_quality,ignore_index=True),quality_exit_cutoff='2026-07-01'),
                      files_sha256={name:sha(out/name) for name in names},
                      model_files_sha256={p.relative_to(out).as_posix():sha(p) for p in sorted((out/'models').glob('*.npz'))})
        write(out,result)
    except Exception as exc:
        result.update(status='PCA95_FAILED',failure=str(exc));write(out,result);raise

if __name__=='__main__':main()
