from pathlib import Path
import sys,json
import numpy as np,pandas as pd
from scipy.special import logit
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'src'))
from prepare import read
from integration import build_scores
from portfolio_adapter import adapt_state
from vector_engine import simulate
from portfolio_metrics_parent import policy_args
from meta_fusion import predict_meta
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--oracle-root',type=Path,required=True);args=parser.parse_args()
original=args.oracle_root;checks=[];score_checks=[]
for market in ['EU','USA']:
    f=read(R/f'inputs/{market}_MEAN3_INPUTS.csv.gz');s=build_scores(f);saved=read(R/f'results/{market}_INTEGRATED_SCORES.csv.gz')
    for col in s:
        if col in ['signal_date','ticker','ARCHIVE_S101']:continue
        assert np.array_equal(s[col],saved[col],equal_nan=True),col
    score_checks.append({'market':market,'fixed_score_identity':True})
    ms=read(R/f'results/{market}_META_SCORES.csv.gz')
    f=f[['signal_date','ticker','RETURN','XGB_CLASS']].merge(s[['signal_date','ticker','MATCHED_REG']],on=['signal_date','ticker'])
    f['H_SIGNAL']=(f.MATCHED_REG-.475*f.RETURN)/.525;f['C_LOGIT']=logit(f.XGB_CLASS.clip(1e-6,1-1e-6))
    for year in range(2021,2027):
        for name in ['META2','META3']:
            m=json.loads((R/f'results/meta_models/{market}_{year}_{name}.json').read_text());g=f[(f.signal_date.dt.year==year)&np.isfinite(f[['RETURN','H_SIGNAL','C_LOGIT']]).all(1)]
            p=predict_meta(m,g[m['columns']].to_numpy());a=g[['signal_date','ticker']].assign(p=p).merge(ms[['signal_date','ticker',name]],on=['signal_date','ticker'])
            assert np.max(abs(a.p-a[name]))<1e-14
    q=dict(np.load(R/f'inputs/{market}_STATE_HALF.npz'));cal=read(R/f'inputs/{market}_CALENDAR.csv')
    for variant in ['MATCHED_REG','SPECIALIST20_MEMORY','META2','META3']:
        sc=ms if variant.startswith('META') else saved;st,events,_=adapt_state(q,cal,sc,variant)
        for policy in ['IMMEDIATE','DELAY3','PHASE5']:
            z=simulate(st,events,fee=.001,**policy_args(policy));key=f'{market}_{variant}_{policy}_FULL_C10'
            old=np.load(original/f'results/paths/{key}.npz')
            err=max(float(np.max(abs(z[k]-old[k]))) for k in z);assert err==0,(key,err)
            checks.append({'config':key,'max_array_error':err})
print(json.dumps({'clean_replayed_paths':len(checks),'exact_new_strategy_arrays':True,'reconstructed_meta_models':24,'fixed_score_checks':score_checks},indent=2))
(R/'RESTORE_VERIFICATION.json').write_text(json.dumps({'paths':checks,'meta_models':24,'scores':score_checks},indent=2))
