"""Verify every downloaded artifact, rebuild the analysis, then export evidence.

No model fitting. Requires a complete successful cloud run's artifact manifest.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil
import sys
import zipfile
import numpy as np
import pandas as pd

WORK=Path(__file__).resolve().parents[1]
ROOT=WORK/'repo'
sys.path[:0]=[str(ROOT),str(ROOT/'vendor/etf_trader_v2/src')]
from compact21_rbf_ridge_v1 import summarize as module
from compact21_semidev_v1.summarize import exact_frame


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_archives(directory,manifest,run,commit):
    directory=Path(directory);raw=json.loads(Path(manifest).read_text())
    artifacts=raw['artifacts']
    expected={f'rbf-ridge-{year}' for year in range(2017,2027)}|{'rbf-ridge-validation','rbf-ridge-summary'}
    if len(artifacts)!=len(expected) or {a['name'] for a in artifacts}!=expected:
        raise ValueError('Missing, duplicate or unexpected run artifacts')
    verified=[]
    for artifact in artifacts:
        name=artifact['name'];archive=directory/(name+'.zip');extracted=directory/name
        digest=artifact.get('digest','')
        if not digest.startswith('sha256:') or sha(archive)!=digest[7:]:
            raise ValueError('Artifact ZIP digest differs: '+name)
        origin=artifact.get('workflow_run',{})
        if origin and (origin.get('id')!=run or origin.get('head_sha')!=commit):
            raise ValueError('Artifact belongs to a different source/run')
        if artifact.get('expired') is not False:raise ValueError('Artifact expiration state unavailable/expired')
        files=set()
        with zipfile.ZipFile(archive) as retained:
            if retained.testzip() is not None:raise ValueError('ZIP CRC failure: '+name)
            for member in retained.infolist():
                if member.is_dir():continue
                relative=PurePosixPath(member.filename)
                if relative.is_absolute() or '..' in relative.parts or '\\' in member.filename or ':' in member.filename:
                    raise ValueError('Invalid artifact member path')
                if member.filename in files:raise ValueError('Duplicate artifact archive member')
                files.add(member.filename)
                physical=extracted.joinpath(*relative.parts)
                if not physical.is_file() or physical.read_bytes()!=retained.read(member):
                    raise ValueError('Extracted artifact differs from verified ZIP: '+member.filename)
        physical_files={p.relative_to(extracted).as_posix() for p in extracted.rglob('*') if p.is_file()}
        if physical_files!=files:raise ValueError('Extracted artifact has missing/extra files')
        verified.append(dict(name=name,id=artifact['id'],digest=digest,zip_sha256=sha(archive),
            zip_crc_PASS=True,extracted_member_bytes_exact=True,members=len(files),origin_retained=origin))
    return verified


def compare_json(cloud,local,path='',differences=None):
    if differences is None:differences=[]
    if path.endswith('/path') or path=='/files_sha256':return differences
    if type(cloud)!=type(local):raise ValueError('Derived JSON type differs: '+path)
    if isinstance(cloud,dict):
        if set(cloud)!=set(local):raise ValueError('Derived JSON schema differs: '+path)
        for key in cloud:compare_json(cloud[key],local[key],path+'/'+key,differences)
    elif isinstance(cloud,list):
        if len(cloud)!=len(local):raise ValueError('Derived JSON list coverage differs: '+path)
        for i,(a,b) in enumerate(zip(cloud,local)):compare_json(a,b,path+'/'+str(i),differences)
    elif isinstance(cloud,float):
        if not np.isfinite(cloud) or not np.isfinite(local) or abs(cloud-local)>1e-14:
            raise ValueError('Derived numeric evidence differs: '+path)
        if cloud!=local:differences.append(dict(path=path,absolute_difference=abs(cloud-local)))
    elif cloud!=local:raise ValueError('Derived evidence differs: '+path)
    return differences


def source_evidence(result,root):
    """Verify retained Linux source bytes; disclose separately collected imports."""
    retained={}
    for relative,digest in result['contract']['sources'].items():
        data=(root/relative).read_bytes()
        if hashlib.sha256(data).hexdigest()==digest:mode='literal_bytes'
        elif hashlib.sha256(data.replace(b'\r\n',b'\n')).hexdigest()==digest:mode='canonical_LF_source_serialization'
        else:raise ValueError('Local verifier source differs from retained fit source: '+relative)
        retained[relative]=dict(sha256=digest,verification=mode)
    extras={}
    for relative in ('compact21_predictive_v2/metrics.py','compact21_predictive_v2/summarize.py',
            'compact21_predictive_v2/additive.py','compact21_learner_swap_v1/run_benchmark.py',
            'compact21_semidev_v1/summarize.py','compact21_blockbag_v1/summarize.py'):
        if relative not in retained:raise ValueError('Missing registered verifier dependency: '+relative)
        extras[relative]=dict(canonical_LF_sha256=hashlib.sha256((root/relative).read_bytes().replace(b'\r\n',b'\n')).hexdigest(),
            recorded_in_job_source_contract=relative in retained,
            scope='Independently checked local verifier dependency against its retained annual job source fingerprint.')
    prereg=hashlib.sha256((root/'compact21_rbf_ridge_v1/PREREGISTRATION.md').read_bytes().replace(b'\r\n',b'\n')).hexdigest()
    if prereg!=result['contract']['preregistration_sha256']:raise ValueError('Frozen registration differs')
    if prereg!='326153a69d82f25e2570b8691b000ed312216eeaa603c2e0e7edd3c4133acc94':
        raise ValueError('Prospectively frozen RBF registration differs')
    return dict(retained_sources_verified=retained,additional_verifier_dependency_inventory=extras,
        preregistration_sha256=prereg,fit_hashes_or_prediction_bytes_normalized=False)


def verify_prerequisite(directory,out):
    path=Path(directory)/'rbf-ridge-validation'/'PREREQUISITE_VALIDATION.json'
    prerequisite=json.loads(path.read_text())
    if prerequisite.get('prerequisite_run')!=37512359380 or prerequisite.get('conditional_launch_PASS') is not True:
        raise ValueError('RBF conditional launch lacks valid prerequisite evidence')
    summary=Path(out)/'BLOCKBAG_V1_SUMMARY.json'
    if not summary.is_file():raise ValueError('Independently verified BLOCKBAG summary required before exporting fallback')
    if sha(summary)!=prerequisite.get('summary_sha256'):raise ValueError('BLOCKBAG prerequisite summary hash differs')
    result=json.loads(summary.read_text())
    if result.get('status')!='COMPACT21_BLOCKBAG_V1_SUMMARY_COMPLETE' or any(result.get(key) is not True for key in (
            'all_controls_reproduced','all_weighted_ones_controls_PASS','all_independent_refits_PASS')):
        raise ValueError('BLOCKBAG prerequisite integrity failure')
    if result['models']['BASE_BLOCKBAG']['gate']['STABLE_WITH_CONSERVED_QUALITY'] is not False:
        raise ValueError('Fallback conditional launch should not have occurred')
    return dict(**prerequisite,validation_file_sha256=sha(path),local_verified_summary_sha256=sha(summary))


def export(directory,manifest,reference,ti,out,independent,run,commit):
    artifacts=verify_archives(directory,manifest,run,commit)
    prerequisite=verify_prerequisite(directory,out)
    cloud_path=Path(directory)/'rbf-ridge-summary'
    cloud=json.loads((cloud_path/'SUMMARY.json').read_text())
    provenance_sources=source_evidence(cloud,ROOT)
    # Recompute all audits, vectors, bootstrap and decisions from annual evidence.
    rebuilt=module.summarize(directory,reference,independent,{v:Path(ti)/f'r{v}' for v in (1,2,3)})
    differences=compare_json(cloud,rebuilt)
    for name in module.FILES[:2]:
        actual=pd.read_parquet(cloud_path/name);expected=pd.read_parquet(Path(independent)/name)
        exact_frame(actual,expected,list(actual.columns),'Cloud/independent aggregate vectors')
        if sha(cloud_path/name)!=cloud['files_sha256'][name]:raise ValueError('Cloud aggregate file identity differs')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    exported=[]
    for name in module.FILES[:2]:
        target='RBF_RIDGE_'+name;shutil.copyfile(cloud_path/name,out/target);exported.append(target)
    shutil.copyfile(cloud_path/'SUMMARY.json',out/'RBF_RIDGE_V1_SUMMARY.json');exported.append('RBF_RIDGE_V1_SUMMARY.json')
    metrics=[];pairs=[];years=[];vintages=[];state_rows=[]
    for model,value in cloud['models'].items():
        metrics.append(dict(model=model,**value['predictive']['aggregate_by_date'],
            common_rank_mad=value['common_stability']['mean']['rank_mad'],
            native_top1_disagreement=value['native_stability']['mean']['top1_disagreement']))
        for scope in ('common','native'):
            for pair,stat in value[scope+'_stability']['pairs'].items():
                pairs.append(dict(model=model,scope=scope,pair=pair,**stat['mean'],**stat['coverage']))
            for pair,stat in value[scope+'_stability_diagnostics'].items():
                for year,row in stat['by_year'].items():years.append(dict(model=model,scope=scope,pair=pair,year=int(year),**row))
        q=pd.DataFrame(value['predictive']['per_date'])
        for vintage,g in q.groupby('vintage',sort=True):
            row={'model':model,'vintage':vintage,'mature_dates':len(g)}
            for key in value['predictive']['aggregate_by_date']:
                values=pd.to_numeric(g[key],errors='raise');row[key]=float(values.mean()) if values.notna().any() else None
            vintages.append(row)
    for name,rows in (('RBF_RIDGE_METRICS.csv',metrics),('RBF_RIDGE_STABILITY_PAIRS.csv',pairs),
            ('RBF_RIDGE_STABILITY_BY_YEAR.csv',years),('RBF_RIDGE_QUALITY_BY_VINTAGE.csv',vintages)):
        pd.DataFrame(rows).to_csv(out/name,index=False);exported.append(name)
    decisions=cloud['models'][module.VARIANT]['gate']
    (out/'RBF_RIDGE_GATES.json').write_text(json.dumps(decisions,indent=2,allow_nan=False)+'\n');exported.append('RBF_RIDGE_GATES.json')
    runtime={};state_artifacts={}
    for year in module.YEARS:
        job=json.loads((Path(directory)/f'rbf-ridge-{year}'/'RESULT.json').read_text())['per_year'][str(year)]
        runtime[str(year)]=dict(candidate_first_fit_seconds=sum(job['fit_seconds'].values()),
            original_control_seconds=sum(v['fit_seconds'] for v in job['legacy_control'].values()),
            ridge_control_seconds=sum(v['fit_seconds'] for v in job['ridge_control'].values()),
            independent_candidate_refit_seconds_retained=False)
        annual=Path(directory)/f'rbf-ridge-{year}'
        state_artifacts[str(year)]={name:sha(annual/name) for name in ('FITTED_STATES.npz','SEED_PREDICTIONS.npz')}
        with np.load(annual/'FITTED_STATES.npz',allow_pickle=False) as states:
            for vintage in (1,2,3):
                audit=job['transforms'][str(vintage)]
                for parameter,fingerprint in audit['learned_state_hashes'].items():
                    value=states[f'v{vintage}_{parameter}']
                    state_rows.append(dict(year=year,vintage=vintage,parameter=parameter,array_sha256=fingerprint,
                        dtype=str(value.dtype),shape=json.dumps(list(value.shape)),
                        source_npz_sha256=state_artifacts[str(year)]['FITTED_STATES.npz']))
    pd.DataFrame(state_rows).to_csv(out/'RBF_RIDGE_FITTED_STATE_FINGERPRINTS.csv',index=False)
    exported.append('RBF_RIDGE_FITTED_STATE_FINGERPRINTS.csv')
    p=dict(status='INDEPENDENT_RECONSTRUCTION_PASS',run=run,commit=commit,
        artifact_manifest_sha256=sha(manifest),artifacts=artifacts,source_verification=provenance_sources,
        retained_prediction_arrays_exact=True,all_annual_controls_reproduced=True,all_ridge_controls_PASS=True,
        all_independent_refits_PASS=True,all_retained_fitted_state_hashes_PASS=cloud['all_retained_fitted_state_hashes_PASS'],
        all_seed_mean_vectors_exact=cloud['all_seed_mean_vectors_exact'],
        registry=cloud['registry'],runtime=runtime,state_artifacts=state_artifacts,
        fitted_state_fingerprints=len(state_rows),conditional_prerequisite=prerequisite,
        derived_json_max_roundoff=max((x['absolute_difference'] for x in differences),default=0),
        derived_json_comparison_tolerance=1e-14,derived_json_roundoff_entries=differences,
        gate_booleans_exact=True,production_adoption=False,negative_feedback_changed=False,
        files_sha256={name:sha(out/name) for name in exported})
    (out/'RBF_RIDGE_PROVENANCE.json').write_text(json.dumps(p,indent=2,allow_nan=False)+'\n')
    return p


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--results',type=Path,default=WORK/'rbf-results')
    p.add_argument('--manifest',type=Path)
    p.add_argument('--reference',type=Path,default=WORK/'predictive-v2')
    p.add_argument('--ti',type=Path,default=WORK/'ti')
    p.add_argument('--out',type=Path,default=WORK.parent/'outputs')
    p.add_argument('--independent',type=Path,default=WORK/'rbf-independent')
    p.add_argument('--run',type=int,required=True)
    p.add_argument('--commit',default='f6cd13a6e868abadc1c77970200672ab052c2a57')
    a=p.parse_args();manifest=a.manifest or a.results/'MANIFEST.json'
    result=export(a.results,manifest,a.reference,a.ti,a.out,a.independent,a.run,a.commit)
    print(json.dumps(dict(status=result['status'],run=result['run'],max_roundoff=result['derived_json_max_roundoff'],artifacts_verified=len(result['artifacts'])),indent=2))
