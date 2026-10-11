import argparse,json
from pathlib import Path
import numpy as np
import pandas as pd
from history_window_v1.contract import selection_disagreement

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--inputs',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    baseline=json.loads(Path('history_window_v1/results/SUMMARY.json').read_text())
    rows=[];leaders=[]
    for i in (1,2,3):
        root=Path(a.inputs)/f'history-full-repeat-{i}'
        p=list(root.rglob('RESULT.json'));ls=list(root.rglob('DAILY_LEADERS.csv'))
        assert len(p)==len(ls)==1,(root,p,ls)
        r=json.loads(p[0].read_text());b=baseline['baseline'][i-1]
        assert all(r[k]==b[k] for k in ('sessions','start','end'))
        assert r['history_experiment']['all_annual_folds']==list(range(2017,2027))
        rows.append({'repeat':i,**r['v2_full_universe']})
        leaders.append(pd.read_csv(ls[0]))
    cs=[r['cagr'] for r in rows];sel=selection_disagreement(leaders)
    ds={'mean_cagr':float(np.mean(cs)),'cagr_span_pp':float(np.ptp(cs)*100),'cagr_population_std_pp':float(np.std(cs)*100),'mean_maxdd':float(np.mean([r['maxdd'] for r in rows])),'mean_sharpe':float(np.mean([r['sharpe'] for r in rows]))}
    bd=baseline['baseline_dispersion'];bs=baseline['baseline_daily_selection_disagreement']
    bdd=float(np.mean([r['maxdd'] for r in baseline['baseline']]));bsh=float(np.mean([r['sharpe'] for r in baseline['baseline']]))
    checks={'cagr_span_reduced_at_least25pct':ds['cagr_span_pp']<=.75*bd['cagr_span_pp'],'top1_any_disagreement_improved':sel['top1_any_fraction']<bs['top1_any_fraction'],'ordered_top2_any_not_worse':sel['top2_ordered_any_fraction']<=bs['top2_ordered_any_fraction'],'mean_cagr_at_least95pct_baseline':ds['mean_cagr']>=.95*bd['mean_cagr'],'each_source_cagr_at_least95pct_baseline':all(r['cagr']>=.95*b['cagr'] for r,b in zip(rows,baseline['baseline'])),'mean_maxdd_not_worse_more_than2pp':ds['mean_maxdd']>=bdd-.02,'mean_sharpe_at_least95pct_baseline':ds['mean_sharpe']>=.95*bsh}
    result={'status':'THREE_SOURCE_COMPLETE_2017_2026_HISTORY_COMPARISON','candidate':rows,'candidate_dispersion':ds,'candidate_selection_disagreement':sel,'baseline':baseline['baseline'],'baseline_dispersion':bd,'baseline_selection_disagreement':bs,'checks':checks,'all_gates_pass':all(checks.values()),'decision':'ADOPT_2011_2012_RESEARCH_CANDIDATE' if all(checks.values()) else 'KEEP_ORIGINAL_HISTORY','training_gate_relaxation':{'old':60,'new':58,'user_authorized':True,'maturity_unchanged':True},'production_changed':False,'caveat':'Already examined Original149 and correlated frozen acquisitions; recommendation is research evidence, not independent future validation or production promotion.'}
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True);(out/'COMPARISON.json').write_text(json.dumps(result,indent=2)+'\n')
    pd.DataFrame(rows).to_csv(out/'CANDIDATE_METRICS.csv',index=False)
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
