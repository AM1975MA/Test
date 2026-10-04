#!/usr/bin/env python3
import argparse,json,os
from pathlib import Path
VARIANTS=('BASE','Q4','ORDINAL','ECON1BP','Q4_ECON1BP','SCALE','SCALE_ECON1BP')
def summarize(root):
    rows={}
    for p in Path(root).rglob('*.json'):
        q=json.loads(p.read_text())
        if q.get('status')=='COMPACT21_STABILITY_V1_BENCHMARK_COMPLETE':
            if q['variant'] in rows: raise ValueError('Duplicate variant result')
            rows[q['variant']]=q
    if set(rows)!=set(VARIANTS): raise ValueError(f'Incomplete variants: {set(rows)}')
    baseline=rows['BASE']
    if any(q['years']!=baseline['years'] or q['input_sha256']!=baseline['input_sha256'] or q['environment']!=baseline['environment'] for q in rows.values()): raise ValueError('Mismatched benchmark provenance')
    b=rows['BASE']['aggregate']; table=[];eligible=[]
    for v in VARIANTS:
        q=rows[v];a=q['aggregate'];s=a['common_inference'];bs=b['common_inference']
        improve=1-s['rank_mean_abs']/bs['rank_mean_abs'] if bs['rank_mean_abs'] else 0
        checks={'rank_mad_reduction_ge25pct':improve>=.25,'common_top1_not_worse':s['top1_disagreement_fraction']<=bs['top1_disagreement_fraction'],'spearman_not_worse':s['mean_daily_spearman']>=bs['mean_daily_spearman'],'native_top1_not_worse':a['native_inference']['top1_disagreement_fraction']<=b['native_inference']['top1_disagreement_fraction'],'quality_ndcg5_ge95pct':a['quality']['ndcg5']>=.95*b['quality']['ndcg5'],'maturity':q['ALL_MATURITY_PASS'],'determinism':q['ALL_DETERMINISM_PASS']}
        ok=v!='BASE' and all(checks.values())
        if ok:eligible.append(v)
        table.append({'variant':v,'rank_mad_reduction_pct':100*improve,'aggregate':a,'checks':checks,'ADVANCE_FULL_REPLAY':ok})
    full=['BASE','Q4','Q4_LEGACY']+[v for v in eligible if v!='Q4']
    return {'status':'COMPACT21_STABILITY_V1_BENCHMARK_SUMMARY','ranking':table,'eligible':eligible,'full_matrix':{'include':[{'variant':v,'repeat':i} for v in full for i in (1,2,3)]},'models':rows}
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    q=summarize(a.inputs);p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(q,indent=2)+'\n')
    print(json.dumps(q['ranking'],indent=2))
    if os.getenv('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:f.write('matrix='+json.dumps(q['full_matrix'],separators=(',',':'))+'\n')
if __name__=='__main__':main()
