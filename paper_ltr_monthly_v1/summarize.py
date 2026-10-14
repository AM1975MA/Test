"""Monthly-vs-annual research decision, using verified predictions and paths."""
import argparse
import json
from pathlib import Path
import numpy as np
from paper_ltr_monthly_v1.core import sha

def main():
    from paper_ltr_v2.summarize import load_artifact,comparison
    from paper_ltr_v2.summarize_replay import summarize
    ap=argparse.ArgumentParser()
    for name in ('candidate','annual','baseline','audit','replays','v1-replays','out'):ap.add_argument('--'+name,required=True)
    a=ap.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    cr,cf=load_artifact(a.candidate);ar,af=load_artifact(a.annual);br,bf=load_artifact(a.baseline)
    audit=json.loads(Path(a.audit).read_text())
    if not audit['all_PASS'] or audit['result_sha256']!=sha(Path(a.candidate)/'RESULT.json'):raise ValueError('Audit not bound to candidate')
    if cr['input_sha256']!=ar['input_sha256'] or cr['input_sha256']!=br['input_sha256']:raise ValueError('Different inputs')
    vs_annual=comparison(cf,af,bf['NATIVE_PREDICTIONS.parquet'])
    vs_base=comparison(cf,bf,bf['NATIVE_PREDICTIONS.parquet'])
    predictive=dict(variant='LINEAR_MONTHLY',vs_annual=vs_annual,vs_BASE=vs_base,
        integrity=audit,source_hashes=dict(candidate=sha(Path(a.candidate)/'RESULT.json'),annual=sha(Path(a.annual)/'RESULT.json')))
    (out/'PREDICTIVE.json').write_text(json.dumps(predictive,indent=2)+'\n',encoding='utf-8')
    e=summarize(a.replays,a.v1_replays,('LINEAR_NUMERICAL_REPAIR','LINEAR_MONTHLY'))
    cm=e['metrics']['LINEAR_MONTHLY'];am=e['metrics']['LINEAR_NUMERICAL_REPAIR']
    cd=e['dispersion']['LINEAR_MONTHLY'];ad=e['dispersion']['LINEAR_NUMERICAL_REPAIR']
    cs=e['selection_disagreement']['LINEAR_MONTHLY'];ass=e['selection_disagreement']['LINEAR_NUMERICAL_REPAIR']
    cq=vs_annual['candidate_quality']['aggregate_by_date'];aq=vs_annual['reference_quality']['aggregate_by_date']
    checks=dict(mean_cagr_ge_annual=cd['mean_cagr']>=ad['mean_cagr'],
        each_cagr_ge95pct_annual=all(c['cagr']>=.95*b['cagr'] for c,b in zip(cm,am)),
        mean_maxdd_ge_annual=cd['mean_maxdd']>=ad['mean_maxdd'],
        each_maxdd_within2pp_annual=all(c['maxdd']>=b['maxdd']-.02 for c,b in zip(cm,am)),
        mean_sharpe_ge95pct_annual=cd['mean_sharpe']>=.95*ad['mean_sharpe'],
        cagr_span_not_worse=cd['cagr_span_pp']<=ad['cagr_span_pp'],
        top1_disagreement_not_worse=cs['top1_any_fraction']<=ass['top1_any_fraction'],
        top2_ordered_not_worse=cs['top2_ordered_any_fraction']<=ass['top2_ordered_any_fraction'],
        top1_quality_ge95pct_annual=cq['top1_realized_percentile']>=.95*aq['top1_realized_percentile'],
        ndcg5_ge95pct_annual=cq['ndcg5']>=.95*aq['ndcg5'],
        precision5_ge95pct_annual=cq['top5_overlap']>=.95*aq['top5_overlap'],
        at_least_one_strict_improvement=(cd['mean_cagr']>ad['mean_cagr'] or cd['mean_maxdd']>ad['mean_maxdd'] or cd['cagr_span_pp']<ad['cagr_span_pp'] or cs['top1_any_fraction']<ass['top1_any_fraction']))
    checks={k:bool(v) for k,v in checks.items()}
    weights={}
    for variant in ('LINEAR_NUMERICAL_REPAIR','LINEAR_MONTHLY'):
        data=[]
        for i in (1,2,3):
            with np.load(Path(a.replays)/f'v2replay-{variant}-r{i}'/'candidate/FULL_UNIVERSE_PATH.npz',allow_pickle=False) as z:
                data.append({k:z[k][0].copy() for k in ('d1','d2','weight1')})
        pairs={}
        for i,j in ((0,1),(0,2),(1,2)):
            x,y=data[i],data[j]
            same=(x['d1']==y['d1'])&(x['d2']==y['d2'])&(x['d1']>=0)&(x['d2']>=0)
            delta=np.abs(x['weight1'][same]-y['weight1'][same])
            pairs[f'{i+1}-{j+1}']=dict(same_pair_sessions=int(same.sum()),different_weight_sessions=int((delta>1e-12).sum()),
                mean_abs_weight_difference=float(delta.mean()) if len(delta) else None)
        weights[variant]=pairs
    e.update(monthly_vs_annual=dict(checks=checks,PASS=all(checks.values()),production_adoption=False),
        observed_weight_sensitivity=weights,monthly_protocol_sha256=cr['preregistration_sha256'],
        monthly_audit_sha256=sha(a.audit),no_new_control_fits=True)
    (out/'ECONOMIC.json').write_text(json.dumps(e,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(dispersion=e['dispersion'],monthly_vs_annual=e['monthly_vs_annual']),indent=2))

if __name__=='__main__':main()
