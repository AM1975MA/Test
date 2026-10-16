"""Verify replay metrics and compare PCA95 with unchanged annual LINEAR."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from paper_ltr_v2.summarize_replay import metrics,checked_leaders,dispersion,selections,gates
from paper_ltr_v2.replay import sha
VARIANT='DISPERSION_SWITCH'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--replays',required=True);ap.add_argument('--candidate',required=True);ap.add_argument('--annual',required=True);ap.add_argument('--audit',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    audit=json.loads(Path(a.audit).read_text());candidate=Path(a.candidate);result=json.loads((candidate/'RESULT.json').read_text())
    if not audit['all_PASS'] or audit['candidate_result_sha256']!=sha(candidate/'RESULT.json'):raise ValueError('Unlinked model audit')
    rows={};leaders={};verification=[];annual_rows=[];calendar=None;hashes={}
    for variant in ('LINEAR_NUMERICAL_REPAIR','LINEAR_PCA_DISCARDED',VARIANT):
        rows[variant]=[];leaders[variant]=[]
        for i in (1,2,3):
            root=Path(a.replays)/f'v2replay-{variant}-r{i}';r=json.loads((root/'RESULT.json').read_text())
            if r['variant']!=variant or r['repeat']!=i or not r['audit']['baseline_replay']['PASS']:raise ValueError('Unverified replay')
            path=root/'candidate/FULL_UNIVERSE_PATH.npz';m,dates=metrics(path)
            error=max(abs(m[key]-r['candidate']['v2_full_universe'][key]) for key in m)
            if error>1e-12:raise ValueError('Economic metrics mismatch')
            if calendar is None:calendar=dates
            elif not calendar.equals(dates):raise ValueError('Calendar mismatch')
            f=checked_leaders(root/'candidate/DAILY_LEADERS.csv',dates)
            rows[variant].append(dict(repeat=i,**r['candidate']['v2_full_universe']));leaders[variant].append(f)
            hashes[f'{variant}/{i}']=sha(path);verification.append(error)
            with np.load(path,allow_pickle=False) as z:lr=np.diff(np.r_[0.,np.log(z['equity'][0])])
            for year in range(2017,2027):annual_rows.append(dict(variant=variant,download=i,year=year,net_return=float(np.expm1(lr[dates.year==year].sum()))))
    disp={v:dispersion(rr) for v,rr in rows.items()};select={v:selections(ll) for v,ll in leaders.items()}
    v=VARIANT;b='LINEAR_NUMERICAL_REPAIR'
    # Reuse unchanged economic guardrail definitions, paired against annual LINEAR.
    checks=gates(rows[v],rows[b],disp[v],disp[b],select[v],select[b])
    reference=json.loads((Path(a.annual)/'RESULT.json').read_text())
    quality=result['predictive']['aggregate_by_date']
    reference_quality=reference['predictive']['aggregate_by_date']
    quality_checks={name:quality[name]>=.95*reference_quality[name] for name in ('top1_realized_percentile','ndcg5')}
    report=dict(status=VARIANT+'_THREE_DOWNLOAD_COMPARISON_COMPLETE',metrics=rows,dispersion=disp,
                selection_disagreement=select,annual_reference_gates=checks,
                model_audit_sha256=sha(a.audit),path_sha256=hashes,maximum_metric_error=max(verification),production_adoption=False,
                predictive_candidate=quality,predictive_reference=reference_quality,predictive_quality_checks=quality_checks)
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2)+'\n')
    pd.DataFrame(annual_rows).to_csv(out/'ANNUAL_RETURNS.csv',index=False)
    pd.DataFrame([dict(variant=v,**r) for v,rr in rows.items() for r in rr]).to_csv(out/'METRICS.csv',index=False)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
