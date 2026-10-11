"""Recover completed baseline evidence; never rerun completed model tests."""
import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from history_window_v1.contract import selection_disagreement

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--audits',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    audits=[json.loads(p.read_text()) for p in sorted(Path(a.audits).rglob('RESULT.json'))]
    assert len(audits)==3 and all(r['status']=='INFEASIBLE_2017_WITH_UNCHANGED_V2' for r in audits)
    expected=json.loads(Path('gap_analysis/results/yfinance_repeatability_replay_v1/RESULT.json').read_text())['replays']
    recovered=[];leaders=[]
    for i in (1,2,3):
        root=Path(a.baseline)/f'learner-meta-full-BASE-r{i}'
        paths=list(root.rglob('RESULT_BASE.json'));lp=list(root.rglob('DAILY_LEADERS_BASE.csv'))
        assert len(paths)==len(lp)==1
        r=json.loads(paths[0].read_text());m=r['v2_full_universe']
        assert r['candidate_count']==149 and r['sessions']==2366
        for key in ('cagr','maxdd','sharpe'): assert abs(m[key]-expected[i-1][key])<1e-12,(i,key,m[key],expected[i-1][key])
        recovered.append({'repeat':i,'start':r['start'],'end':r['end'],'sessions':r['sessions'],**m})
        leaders.append(pd.read_csv(lp[0]))
    cagrs=[r['cagr'] for r in recovered]
    result={'status':'THREE_SOURCE_HISTORY_WINDOW_REJECTED_AT_FEASIBILITY_GATE','baseline_recovery_run':37934815636,'baseline_original_run':37195399755,'raw_run':37121749852,'baseline':recovered,'baseline_dispersion':{'mean_cagr':float(np.mean(cagrs)),'cagr_span_pp':float(np.ptp(cagrs)*100),'cagr_population_std_pp':float(np.std(cagrs,ddof=0)*100)},'baseline_daily_selection_disagreement':selection_disagreement(leaders),'candidate_audits':audits,'candidate_metrics':None,'candidate_selection_disagreement':None,'full_comparison_completed':False,'decision':'KEEP_ORIGINAL_HISTORY','decision_scope':'Operational feasibility of requested unchanged model over complete 2017-2026. No assertion that original history outperforms 2011/2012 on an unmeasured comparable backtest.'}
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    (out/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n')
    pd.DataFrame(recovered).to_csv(out/'BASELINE_METRICS.csv',index=False)
    print(json.dumps({k:v for k,v in result.items() if k!='candidate_audits'},indent=2))

if __name__=='__main__':main()
