"""Confronti fissati V2: audit indipendente dai checkpoint, nessun fit."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from paper_ltr_v2.audit import sha,audit_artifact,budget_gate
from paper_ltr_v1.summarize import common_truth,stability,ordered
from compact21_predictive_v2.metrics import evaluate,paired_compare
KEYS=['vintage','signal_date','ticker']

def reduction_gate(candidate,baseline):
    if candidate is None or baseline is None:return False
    if not np.isfinite([candidate,baseline]).all() or min(candidate,baseline)<0:return False
    return candidate==0 if baseline==0 else candidate<=.75*baseline

def load_artifact(directory):
    root=Path(directory);result=json.loads((root/'RESULT.json').read_text(encoding='utf-8'))
    if set(result.get('per_year',{}))!=set(map(str,range(2017,2027))):raise ValueError('Anni incompleti')
    frames={}
    for name in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet'):
        path=root/name
        if sha(path)!=result.get('files_sha256',{}).get(name):raise ValueError('Hash predizioni non corrispondente')
        frames[name]=ordered(pd.read_parquet(path))
        if set(frames[name].vintage)!= {'1','2','3'}:raise ValueError('Acquisizioni mancanti')
    return result,frames

def comparison(candidate_frames,base_frames,truth):
    cn=candidate_frames['NATIVE_PREDICTIONS.parquet'];bn=base_frames['NATIVE_PREDICTIONS.parquet']
    cc=candidate_frames['COMMON_PREDICTIONS.parquet'];bc=base_frames['COMMON_PREDICTIONS.parquet']
    for a,b in ((cn,bn),(cc,bc)):
        if not ordered(a)[KEYS].equals(ordered(b)[KEYS]):raise ValueError('Supporto candidato/riferimento diverso')
    cq=evaluate(common_truth(cn,truth),quality_exit_cutoff='2026-07-01')
    bq=evaluate(common_truth(bn,truth),quality_exit_cutoff='2026-07-01')
    cs={'native':stability(cn),'common':stability(cc)};bs={'native':stability(bn),'common':stability(bc)}
    c=cq['aggregate_by_date'];b=bq['aggregate_by_date']
    checks=dict(rank_mad_common_reduction_ge25pct=reduction_gate(cs['common']['aggregate']['rank_mad'],bs['common']['aggregate']['rank_mad']),
        native_top1_reduction_ge25pct=reduction_gate(cs['native']['aggregate']['top1_disagreement'],bs['native']['aggregate']['top1_disagreement']),
        native_ordered_top2_not_worse=cs['native']['aggregate']['ordered_top2_disagreement']<=bs['native']['aggregate']['ordered_top2_disagreement'],
        top1_quality_ge95pct=c['top1_realized_percentile']>=.95*b['top1_realized_percentile'],
        ndcg5_ge95pct=c['ndcg5']>=.95*b['ndcg5'],precision5_ge95pct=c['top5_overlap']>=.95*b['top5_overlap'])
    return dict(checks=checks,descriptive_screen_PASS=all(checks.values()),candidate_quality=cq,reference_quality=bq,
                candidate_stability=cs,reference_stability=bs,
                paired_quality=paired_compare(cq,bq,n_bootstrap=20000,seed=20261012,block_lengths=(3,1,6)))

def summarize(candidate,original,baseline,diagnostic,panel_dirs):
    cr,cf=load_artifact(candidate);orr,of=load_artifact(original);br,bf=load_artifact(baseline)
    if cr.get('variant') not in ('BUDGET300','LINEAR','LINEAR_NUMERICAL_REPAIR') or cr.get('status')!='PAPER_LTR_V2_COMPLETE':raise ValueError('Variante/stato V2 non valido')
    if orr.get('status')!='PAPER_LTR_V1_COMPLETE' or br.get('status')!='COMPACT21_PREDICTIVE_V2_COMPLETE' or br.get('variant')!='BASE':raise ValueError('Riferimenti non completi')
    if br.get('ALL_DETERMINISM_PASS') is not True or br.get('LEGACY_PARITY_PASS') is not True:raise ValueError('BASE non verificata')
    if any(r.get('input_sha256')!=br['input_sha256'] for r in (cr,orr)):raise ValueError('Input misti')
    da=json.loads(Path(diagnostic).read_text(encoding='utf-8'))
    if da.get('status')!='PAPER_LTR_V2_NOFIT_AUDIT_COMPLETE' or da.get('result_sha256')!=sha(Path(original)/'RESULT.json') or da.get('input_sha256')!=cr['input_sha256']:
        raise ValueError('Audit fase zero non corrispondente')
    ca=audit_artifact(panel_dirs,candidate);oa=audit_artifact(panel_dirs,original)
    if oa['validation_records']!=da['validation_records']:raise ValueError('Audit originale non riproducibile')
    truth=bf['NATIVE_PREDICTIONS.parquet']
    vs_base=comparison(cf,bf,truth);vs_original=comparison(cf,of,truth)
    integrity={};bg=None
    if cr['variant']=='BUDGET300':
        old=[r for r in oa['validation_records'] if r['stop_reason']=='max_epochs']
        selected={r['key'] for r in old};new=[r for r in ca['validation_records'] if r['key'] in selected]
        bg=budget_gate(old,new)
        metas=[meta for year in cr['per_year'].values() for meta in year['transforms'].values()]
        integrity=dict(prefix100_PASS=all(meta.get('prefix100_PASS') is True for meta in metas),
                       reuse_original_PASS=all(meta.get('reuse_original_PASS') is True for meta in metas))
    else:
        metas=[meta for year in cr['per_year'].values() for meta in year['transforms'].values()]
        integrity=dict(solver_convergence_PASS=all(meta.get('solver_convergence_PASS') is True for meta in metas))
    return dict(status='PAPER_LTR_V2_FIXED_RECIPE_COMPARISON_COMPLETE',variant=cr['variant'],input_sha256=cr['input_sha256'],
        vs_BASE=vs_base,vs_original_LISTNET=vs_original,budget_diagnostic=bg,integrity=integrity,
        scientific_screen_PASS=all(integrity.values()) and vs_base['descriptive_screen_PASS'] and (bg is None or bg['PASS']),
        audit_candidate=ca,numerical_repair=cr.get('numerical_repair'),production_adoption=False,automatic_replay=False,new_fits_executed=0,
        evidence_sha256={k:sha(p) for k,p in [('candidate',Path(candidate)/'RESULT.json'),('original',Path(original)/'RESULT.json'),('BASE',Path(baseline)/'RESULT.json'),('diagnostic',diagnostic)]},
        interpretation='Confronto di due ricette fissate su dati già esposti; non politica nested e non holdout intatto. Replay economici diagnostici autorizzati anche con gate fallito.')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for name in ('candidate','original','baseline','diagnostic','out'):ap.add_argument('--'+name,required=True)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    args=ap.parse_args();result=summarize(args.candidate,args.original,args.baseline,args.diagnostic,{i:getattr(args,f'r{i}') for i in (1,2,3)})
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],variant=result['variant'],scientific_screen_PASS=result['scientific_screen_PASS']),ensure_ascii=False))

if __name__=='__main__':main()
