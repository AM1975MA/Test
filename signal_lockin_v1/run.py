"""Frozen annual PLS12 / coherence+PLS12 audit; no source download."""
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from signal_lockin_v1.core import VARIANTS,fit
from paper_ltr_v1 import learner as v1
from paper_ltr_v1.run import annual_frames,verified_baseline
from paper_ltr_monthly_v1.run import ANNUAL_SHA,write
from compact21_predictive_v2.metrics import evaluate,paired_compare
from compact21_predictive_v2.run import numerical_gate,predictions_frame
from paper_ltr_v2.replay import sha

def compare_keys(actual,reference):
    aa=actual.assign(vintage=actual.vintage.astype(str)).sort_values(['vintage',*v1.KEYS]).reset_index(drop=True)
    bb=reference.assign(vintage=reference.vintage.astype(str)).sort_values(['vintage',*v1.KEYS]).reset_index(drop=True)
    pd.testing.assert_frame_equal(aa[['vintage',*v1.KEYS]],bb[['vintage',*v1.KEYS]],check_exact=True)

def monthly_top1_disagreement(common):
    # Common ETF cohort and a single signal date have three independently fitted sources.
    f=common.copy();f['vintage']=f.vintage.astype(str)
    rows=[]
    for (date,repeat),g in f.groupby(['signal_date','vintage'],sort=True):
        winner=g.sort_values(['pred','ticker'],ascending=[False,True],kind='stable').iloc[0].ticker
        rows.append((date,repeat,winner))
    ranks=pd.DataFrame(rows,columns=['date','vintage','winner'])
    counts=ranks.groupby('date').agg(vintages=('vintage','nunique'),different=('winner','nunique'))
    if not (counts.vintages==3).all():raise ValueError('Missing source for shared date')
    return dict(any_top1=float((counts.different>1).mean()),dates=int(len(counts)))

def main():
    ap=argparse.ArgumentParser()
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--annual',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args()
    annual_root=Path(a.annual)
    if sha(annual_root/'RESULT.json')!=ANNUAL_SHA:raise ValueError("Changed annual reference")
    annual=json.loads((annual_root/'RESULT.json').read_text())
    if annual.get('status')!='PAPER_LTR_V2_COMPLETE' or annual.get('variant')!='LINEAR_NUMERICAL_REPAIR':
        raise ValueError('Noncanonical LINEAR control')
    numeric=numerical_gate()
    panels={};hashes={}
    for i in (1,2,3):
        path=Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet'
        hashes[str(i)]=sha(path)
        panels[i]=pd.read_parquet(path)
        for c in ('signal_date','exit_date_21'):panels[i][c]=pd.to_datetime(panels[i][c])
    if hashes!=annual['input_sha256']:raise ValueError('Frozen panel hash drift')
    _,base_audit=verified_baseline(a.baseline,hashes,panels)
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Non-empty output')
    out.mkdir(parents=True,exist_ok=True)
    control_native=pd.read_parquet(annual_root/'NATIVE_PREDICTIONS.parquet')
    control_common=pd.read_parquet(annual_root/'COMMON_PREDICTIONS.parquet')
    if sha(annual_root/'NATIVE_PREDICTIONS.parquet')!=annual['files_sha256']['NATIVE_PREDICTIONS.parquet']:
        raise ValueError('Control native hash')
    if sha(annual_root/'COMMON_PREDICTIONS.parquet')!=annual['files_sha256']['COMMON_PREDICTIONS.parquet']:
        raise ValueError('Control common hash')
    controlled_quality=evaluate(control_native,quality_exit_cutoff='2026-07-01')
    control_stability=monthly_top1_disagreement(control_common)
    result={'status':'RUNNING','input_sha256':hashes,'control_sha256':ANNUAL_SHA,
            'baseline':base_audit,'numeric_contract':numeric,
            'preregistration_sha256':sha(ROOT/'signal_lockin_v1/PROTOCOL.md'),
            'sources':{p.name:sha(p) for p in sorted((ROOT/'signal_lockin_v1').glob('*.py'))},
            'quality_control':controlled_quality['aggregate_by_date'],
            'stability_control':control_stability,'variants':{},'production_adoption':False}
    (out/'INPUT_CONTRACT.json').write_text(json.dumps(result,indent=2)+'\n')
    summary={}
    for variant in VARIANTS:
        folder=out/variant;folder.mkdir()
        native=[];common=[];quality=[];metas={};diagnostics=[]
        info=dict(status='RUNNING',variant=variant,per_year={},input_sha256=hashes,
                  annual_reference={'run':38580178650,'result_sha256':ANNUAL_SHA},
                  numerical_repair=annual['numerical_repair'],baseline=base_audit,
                  numeric_contract=numeric,preregistration_sha256=result['preregistration_sha256'],
                  new_fits_executed=0,production_adoption=False)
        write(folder,info)
        try:
            for year in range(2017,2027):
                trains,tests,shared=annual_frames(panels,year)
                bysource={}
                for i in (1,2,3):
                    preds,meta,diags=fit(trains[i],[shared,tests[i]],year,i,folder,annual_root,annual,variant)
                    pc,pn=preds
                    bysource[str(i)]=meta
                    native.append(predictions_frame(tests[i],pn,i))
                    frame=shared[v1.KEYS].copy();frame['pred']=pc;frame['vintage']=i;common.append(frame)
                    quality.append(predictions_frame(shared,pc,i))
                    info['new_fits_executed']+=1
                    if diags is not None:
                        diags['download']=i;diags['subtrain_year']=year;diagnostics.append(diags)
                    print(json.dumps({'variant':variant,'year':year,'source':i,'gradient':meta['projected_independent_gradient_inf']}),flush=True)
                info['per_year'][str(year)]=dict(transforms=bysource,maturity_PASS=True)
                pd.concat(native,ignore_index=True).to_parquet(folder/'NATIVE_PREDICTIONS.parquet',index=False)
                pd.concat(common,ignore_index=True).to_parquet(folder/'COMMON_PREDICTIONS.parquet',index=False)
                write(folder,info)
            if info['new_fits_executed']!=30:raise ValueError('Wrong fit count')
            pn=pd.concat(native,ignore_index=True);pc=pd.concat(common,ignore_index=True)
            compare_keys(pn,control_native);compare_keys(pc,control_common)
            if diagnostics:
                pd.concat(diagnostics,ignore_index=True).to_csv(folder/'COHERENCE_2026_SUBTRAIN.csv',index=False)
            fit_quality=evaluate(pn,quality_exit_cutoff='2026-07-01')
            fit_stability=monthly_top1_disagreement(pc)
            paired=paired_compare(fit_quality,controlled_quality,block_lengths=(6,12),
                                  n_bootstrap=3000,seed=20261016)
            qm=fit_quality['aggregate_by_date'];bc=controlled_quality['aggregate_by_date']
            stable=fit_stability['any_top1']<=control_stability['any_top1']+1e-12
            preserved=(qm['top1_realized_percentile']>=.95*bc['top1_realized_percentile']
                       and qm['ndcg5']>=.95*bc['ndcg5'])
            gate=bool(preserved and stable)
            info.update(status='PAPER_LTR_V2_COMPLETE',ALL_MATURITY_PASS=True,
                predictive=fit_quality,predictive_common_repeat2=evaluate(pd.concat(quality,ignore_index=True),
                       quality_exit_cutoff='2026-07-01'),
                stability=fit_stability,paired_quality=paired,
                quality_gate_pass=bool(preserved),stability_gate_pass=bool(stable),
                economic_replay_gate_pass=gate,
                files_sha256={n:sha(folder/n) for n in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet')},
                model_files_sha256={p.relative_to(folder).as_posix():sha(p)
                                    for p in sorted((folder/'models').glob('*.npz'))})
            write(folder,info)
            summary[variant]=dict(status='COMPLETE',quality=qm,monthly_stability=fit_stability,
                                  quality_gate_pass=bool(preserved),stability_gate_pass=bool(stable),
                                  economic_replay_gate_pass=gate,paired_quality=paired['difference'])
        except Exception as e:
            info.update(status='SIGNAL_LOCKIN_FAILED',failure=str(e))
            write(folder,info);raise
    result.update(status='SIGNAL_LOCKIN_PREDICTIVE_COMPLETE',variants=summary,
                  reported_no_portfolio_cagr=True,source_revisions_correlated=True,
                  repeated_development_period_not_independent=True)
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],
           'baseline':result['quality_control'],
           'variants':summary},indent=2),flush=True)

if __name__=='__main__':main()
