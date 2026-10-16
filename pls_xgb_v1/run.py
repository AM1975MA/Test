"""Three-arm matched-subtraining XGBRanker experiment on frozen Original149."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from etf_trader.source_only import kernel as k
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames,verified_baseline
from paper_ltr_monthly_v1.run import ANNUAL_SHA,write
from compact21_predictive_v2.metrics import evaluate,paired_compare
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from paper_ltr_v2.replay import sha
from pls_xgb_v1.core import VARIANTS,fit

def verify_keys(actual,reference):
    a=actual.assign(vintage=actual.vintage.astype(str)).sort_values(['vintage',*v1.KEYS]).reset_index(drop=True)
    b=reference.assign(vintage=reference.vintage.astype(str)).sort_values(['vintage',*v1.KEYS]).reset_index(drop=True)
    pd.testing.assert_frame_equal(a[['vintage',*v1.KEYS]],b[['vintage',*v1.KEYS]],check_exact=True)

def disagreement(common):
    out=[]
    for (date,repeat),g in common.groupby(['signal_date','vintage'],sort=True):
        best=g.sort_values(['pred','ticker'],ascending=[False,True],kind='stable').iloc[0]
        out.append((date,repeat,best['ticker']))
    z=pd.DataFrame(out,columns=['date','repeat','ticker'])
    q=z.groupby('date').agg(repeats=('repeat','nunique'),winners=('ticker','nunique'))
    if not (q.repeats==3).all():raise ValueError('Wrong shared calendar')
    return {'any_top1':float((q.winners>1).mean()),'dates':int(len(q))}

def main():
    ap=argparse.ArgumentParser()
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--annual',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    annual_path=Path(a.annual)
    if sha(annual_path/'RESULT.json')!=ANNUAL_SHA:raise ValueError('Wrong frozen annual LINEAR')
    annual=json.loads((annual_path/'RESULT.json').read_text())
    if annual['status']!='PAPER_LTR_V2_COMPLETE' or annual['variant']!='LINEAR_NUMERICAL_REPAIR':
        raise ValueError('Incorrect control')
    numeric=numerical_gate()
    panels={};hashes={}
    for i in (1,2,3):
        file=Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet'
        hashes[str(i)]=sha(file)
        panels[i]=pd.read_parquet(file)
        for column in ('signal_date','exit_date_21'):
            panels[i][column]=pd.to_datetime(panels[i][column])
    if hashes!=annual['input_sha256']:raise ValueError('Changed frozen sources')
    _,audited_base=verified_baseline(a.baseline,hashes,panels)
    original=pd.read_parquet(annual_path/'NATIVE_PREDICTIONS.parquet')
    original_common=pd.read_parquet(annual_path/'COMMON_PREDICTIONS.parquet')
    for name in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet'):
        if sha(annual_path/name)!=annual['files_sha256'][name]:raise ValueError('LINEAR result digest mismatch')
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be fresh')
    out.mkdir(exist_ok=True,parents=True)
    result=dict(status='RUNNING',variants=list(VARIANTS),input_sha256=hashes,
                annual_sha256=ANNUAL_SHA,baseline=audited_base,
                numerical_contract=numeric,preregistration_sha256=sha(ROOT/'pls_xgb_v1/PROTOCOL.md'),
                sources={p.name:sha(p) for p in sorted((ROOT/'pls_xgb_v1').glob('*.py'))},
                new_xgb_seed_fits=0,production_adoption=False)
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(result,indent=2)+'\n')
    native={v:[] for v in VARIANTS};common={v:[] for v in VARIANTS}
    meta={v:{} for v in VARIANTS}
    try:
        for year in range(2017,2027):
            trains,tests,shared=annual_frames(panels,year)
            for v in VARIANTS:meta[v][str(year)]={}
            for i in (1,2,3):
                fitted=fit(trains[i],[shared,tests[i]],year,i,out,annual)
                for v,(preds,audit) in fitted.items():
                    pc,pn=preds
                    native[v].append(predictions_frame(tests[i],pn,i))
                    frame=shared[v1.KEYS].copy();frame['pred']=pc;frame['vintage']=i
                    common[v].append(frame)
                    meta[v][str(year)][str(i)]=audit
                    result['new_xgb_seed_fits']+=3
            result['year_complete']=year
            (out/'PROGRESS.json').write_text(json.dumps({'year':year,'fits':result['new_xgb_seed_fits']})+'\n')
            print(json.dumps({'year':year,'xgb_seed_fits':result['new_xgb_seed_fits']}),flush=True)
        summaries={}
        linear_qual=evaluate(original,quality_exit_cutoff='2026-07-01')
        for v in VARIANTS:
            folder=out/v;folder.mkdir()
            nat=pd.concat(native[v],ignore_index=True)
            com=pd.concat(common[v],ignore_index=True)
            verify_keys(nat,original);verify_keys(com,original_common)
            nat.to_parquet(folder/'NATIVE_PREDICTIONS.parquet',index=False)
            com.to_parquet(folder/'COMMON_PREDICTIONS.parquet',index=False)
            qual=evaluate(nat,quality_exit_cutoff='2026-07-01')
            stable=disagreement(com)
            info=dict(status='PAPER_LTR_V2_COMPLETE',variant=v,
                input_sha256=hashes,baseline=audited_base,per_year={y:dict(transforms=content,maturity_PASS=True) for y,content in meta[v].items()},
                new_xgb_seed_fits=90,ALL_MATURITY_PASS=True,production_adoption=False,
                predictive=qual,stability=stable,
                files_sha256={name:sha(folder/name) for name in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet')},
                xgb_recipe=k.COMPACT_PARAMS,seeds=k.COMPACT_SEEDS,
                preregistration_sha256=result['preregistration_sha256'],
                model_files_sha256={p.relative_to(out).as_posix():sha(p) for p in sorted((out/'models').glob('*_'+v+'.npz'))})
            write(folder,info)
            summaries[v]=dict(prediction=qual['aggregate_by_date'],stability=stable,
                years=qual['per_year'],files_sha256=info['files_sha256'])
        candidates={}
        matched_folder=out/'XGB125_MATCHED'
        matched_native=pd.read_parquet(matched_folder/'NATIVE_PREDICTIONS.parquet')
        matched_qual=evaluate(matched_native,quality_exit_cutoff='2026-07-01')
        for v in ('XGB_PLS12','XGB_PLS12_COHERENCE'):
            candidate=evaluate(pd.read_parquet(out/v/'NATIVE_PREDICTIONS.parquet'),quality_exit_cutoff='2026-07-01')
            diff=paired_compare(candidate,matched_qual,block_lengths=(6,12),n_bootstrap=1000,seed=20261017)
            candidates[v]=dict(relative_to='XGB125_MATCHED',quality_difference=diff['difference'],
                ci6={m:diff['bootstrap']['6']['intervals_95pct'][m] for m in ('top1_realized_percentile','ndcg5','rank_ic')},
                interpretation='Exploratory, not independent validation')
        report=dict(status='PLS_XGB_PREDICTIVE_COMPLETE',source_only=True,
            new_xgb_seed_fits=result['new_xgb_seed_fits'],variants=summaries,
            comparisons=candidates,linear_control=linear_qual['aggregate_by_date'],
            linear_control_stability=disagreement(original_common),
            reference_note='BASE XGB125 on full mature training is archived separately, matched XGB125 uses exact PLS subtraining and preprocessing',
            no_future_labels_in_basis=True,not_independent_historical_holdout=True,
            production_adoption=False)
        (out/'SUMMARY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'status':report['status'],'fits':report['new_xgb_seed_fits'],
             'quality':{v:report['variants'][v]['prediction'] for v in VARIANTS},
             'stability':{v:report['variants'][v]['stability'] for v in VARIANTS}},indent=2),flush=True)
    except Exception as error:
        result.update(status='FAILED',failure=str(error))
        (out/'FAILURE.json').write_text(json.dumps(result,indent=2)+'\n')
        raise

if __name__=='__main__':main()
