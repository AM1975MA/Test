"""Post-OLC111 single-mechanism ablation; frozen fits, no new model training."""
from __future__ import annotations
import argparse
import datetime
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

SOURCE=Path(__file__).resolve().parents[2]/'olc111'
sys.path.insert(0,str(SOURCE/'src'))
import run_olc111 as previous
from research_pipeline import build_research_bundle,execution_panel,HEADS
from replay_engine import simulate

ARMS=('MEAN_ROTATION','PRICE_ROTATION','VIX_ROTATION','TERM_ROTATION')
SCENARIOS=previous.SCENARIOS


class RotationOverlay(previous.AccountPolicy):
    """Preserve invested monthly baseline rotation, delegate everything else."""
    def __init__(self,bundle,arm,fit_cache):
        if arm not in ARMS:raise ValueError('ROTATION_ARM')
        self.output_arm=arm
        super().__init__(bundle,arm.removesuffix('_ROTATION'),fit_cache)

    def __call__(self,k,current,context):
        scheduled_invested=(context['scheduled'] and not context['initial']
                            and float(np.sum(current))>1e-8)
        ready=(scheduled_invested and
               all(self.fit_cache.get(k)[head] is not None for head in HEADS))
        idle=context['pending'] is None and not context['queued']
        if ready and idle:
            row=self._record(k,current,context)
            row.update(model_ready_all=True,action='SCHEDULED',status='INVESTED_MONTHLY_ROTATION')
            self.trace.append(row)
            answer=dict(weights=np.array(self.bundle['targets'][k],copy=True),reason='SCHEDULED',
                        force=False,meta=dict(arm=self.output_arm,underlying_arm=self.arm,
                                             status='INVESTED_MONTHLY_ROTATION'))
        else:
            answer=super().__call__(k,current,context)
        self.trace[-1]['arm']=self.output_arm
        if answer is not None:
            answer['meta'].update(arm=self.output_arm,underlying_arm=self.arm)
        return answer


def verify_freeze(root):
    root=Path(root)
    freeze=json.loads((root/'docs/EXPERIMENT_FREEZE.json').read_text())
    for kind in ('code_hashes','input_hashes'):
        for path,digest in freeze[kind].items():
            if previous.sha(root/path)!=digest:raise ValueError('FREEZE_HASH_MISMATCH:'+path)
    if previous.sha(root/'docs/DESIGN_AND_PROTOCOL.md')!=freeze['protocol_sha256']:
        raise ValueError('FREEZE_PROTOCOL_MISMATCH')
    if freeze['arms']!=list(ARMS) or freeze['scenarios']!=list(SCENARIOS) or freeze['planned_paths']!=12:
        raise ValueError('FREEZE_MATRIX_MISMATCH')
    previous.verify_experiment_freeze(root.parent/'olc111')
    return freeze


def compare_mean_with_base(source,scenario,result,folder):
    """If no discretionary orders occur, preserved rotations must match BASE."""
    orders=result['orders']
    discretionary=orders.loc[orders.reason.isin(HEADS)]
    original=pd.read_csv(source/'results'/f'BASE__{scenario}'/'DAILY.csv.gz',float_precision='round_trip')
    current=result['daily']
    if len(original)!=len(current):raise AssertionError('BASELINE_ROW_COUNT')
    errors={}
    for column in ('nav_open','nav_close','cash','gross','positions'):
        errors[column]=float(np.max(np.abs(original[column].to_numpy(float)-current[column].to_numpy(float))))
    exact=max(errors.values())<1e-8
    if discretionary.empty and not exact:raise AssertionError(('MEAN_ROTATION_BASE_PARITY',errors))
    record=dict(scenario=scenario,discretionary_orders=len(discretionary),
                exact_baseline_parity=exact,max_difference=max(errors.values()),details=errors)
    previous._write_json(folder/'MEAN_BASE_REPLICATION.json',record)
    return record


def run(root,resume=False):
    root=Path(root).resolve();source=root.parent/'olc111'
    freeze=verify_freeze(root);freeze_sha=previous.sha(root/'docs/EXPERIMENT_FREEZE.json')
    source_freeze_sha=previous.sha(source/'docs/EXPERIMENT_FREEZE.json')
    results=root/'results';results.mkdir(exist_ok=True)
    manifest_path=results/'RUN_MANIFEST.json'
    if manifest_path.exists():
        if not resume:raise FileExistsError('Use resume under unchanged freeze')
        manifest=json.loads(manifest_path.read_text())
        if manifest['freeze_sha256']!=freeze_sha:raise ValueError('RUN_FREEZE_MISMATCH')
    else:
        manifest=dict(start_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            freeze_sha256=freeze_sha,source_study_freeze_sha256=source_freeze_sha,
            code_hashes=freeze['code_hashes'],input_hashes=freeze['input_hashes'],
            arms=list(ARMS),scenarios=list(SCENARIOS),planned_paths=12,completed_paths=0,
            adaptive_after_olc111=True,pristine_holdout=False,new_model_fits=0,
            primary_arm='PRICE_ROTATION',single_change='preserve_invested_monthly_baseline_rotation')
    previous._write_json(manifest_path,manifest)
    scores=[];annual=[];common=[];drawdowns=[];replications=[]
    with threadpool_limits(limits=1):
        bundle=build_research_bundle(source,resume=True)
        cache=previous.MonthlyFitCache(bundle['bank'],bundle['panel']['dates'],bundle['begin'],
                                      folder=source/'results/FITS',provenance=source_freeze_sha)
        cutoffs=np.unique(cache.cutoffs[bundle['begin']-1:len(bundle['panel']['dates'])-1])
        for cutoff in cutoffs:
            if not (source/'results/FITS'/f'FIT_{cutoff:06d}.json.gz').exists():
                raise ValueError('SAVED_MODEL_MISSING_REFIT_FORBIDDEN')
        readiness=cache.prepare()
        old_readiness=json.loads((source/'results/FIT_READINESS.json').read_text())
        if readiness!=old_readiness:raise AssertionError('READINESS_CHANGED')
        previous._write_json(results/'FIT_READINESS.json',readiness)
        print('Using saved OLC111 fits; no model is retrained',flush=True)
        for arm in ARMS:
            for scenario,(ticket,impact,fill) in SCENARIOS.items():
                folder=results/f'{arm}__{scenario}'
                if resume and (folder/'METRICS.json').exists():
                    for name in ('DAILY.csv.gz','ORDERS.csv.gz','INSTRUCTIONS.csv.gz','DECISIONS.npz',
                                 'DECISIONS_META.json.gz','POLICY_TRACE.csv.gz'):
                        if not (folder/name).exists():raise ValueError('INCOMPLETE_SAVED_PATH')
                    metrics=json.loads((folder/'METRICS.json').read_text())
                    daily=pd.read_csv(folder/'DAILY.csv.gz',float_precision='round_trip')
                    if arm=='MEAN_ROTATION':
                        replications.append(json.loads((folder/'MEAN_BASE_REPLICATION.json').read_text()))
                else:
                    callback=RotationOverlay(bundle,arm,cache)
                    panel=execution_panel(bundle['panel'],fill)
                    result=simulate(panel,bundle['f'],lambda k,w:bundle['targets'][k],bundle['monthly'],
                        legacy=bundle['core'],account_policy=callback,allow_scheduled_hold=True,
                        ticket=ticket,impact=impact,start=str(panel['dates'][bundle['begin']].date()),
                        end=str(panel['dates'][-1].date()))
                    metrics=previous.summarize_path(bundle,arm,scenario,result,readiness)
                    metrics.update(source_model_arm=arm.removesuffix('_ROTATION'),new_model_fits=0,
                                   adaptive_after_olc111=True)
                    previous.save_path(folder,result,callback.trace,metrics)
                    daily=result['daily']
                    if arm=='MEAN_ROTATION':
                        replications.append(compare_mean_with_base(source,scenario,result,folder))
                scores.append(metrics)
                annual.extend(previous.annual_rows(bundle,daily,arm,scenario))
                drawdowns.extend(previous.drawdown_rows(daily,arm,scenario))
                segment=previous.performance_window(bundle['core'],daily,
                                                    start_idx=readiness['postwarmup_start_idx'])
                common.append(dict(path_id=f'{arm}__{scenario}',arm=arm,scenario=scenario,**segment))
                previous._csv(pd.DataFrame(scores),results/'SCORES.csv')
                manifest.update(completed_paths=len(scores),completed_path_ids=[r['path_id'] for r in scores])
                previous._write_json(manifest_path,manifest)
                print(f'{len(scores)}/12 {arm}__{scenario}: CAGR {metrics["cagr"]:.6f}, DD {metrics["maxdd_sampled"]:.6f}',flush=True)
        previous._csv(pd.DataFrame(annual),results/'ANNUAL_RETURNS.csv')
        previous._csv(pd.DataFrame(common),results/'COMMON_POST_WARMUP.csv')
        previous._csv(pd.DataFrame(drawdowns),results/'DRAWDOWN_EPISODES.csv')
        previous._write_json(results/'MEAN_BASE_REPLICATION.json',replications)
    verify_freeze(root)
    manifest.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),completed_paths=12)
    previous._write_json(manifest_path,manifest)
    return manifest


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();run(args.root,args.resume)
