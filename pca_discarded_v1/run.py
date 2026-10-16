"""Frozen-weight retained/discarded PCA audit; zero training and no portfolio replay."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from paper_ltr_v1 import learner as v1
from compact21_predictive_v2.metrics import evaluate,paired_compare
from pca_discarded_v1.decomposition import split_weights,energy_split

ANNUAL_SHA='19d178f977f435eb3433b23f6b16113bb9ff6ea623b079a4742cb04312ee132f'
PCA_SHA='2e86e889906c6dd07e1290af6cc513f8d8e8b132a9784c915389efba0b64efa0'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def prediction_frame(test,score,repeat):
    names=v1.KEYS+['target_rank_21','exit_date_21','fwd_ret_21']
    f=test[names].copy().rename(columns={'fwd_ret_21':'target_ret_21'})
    f['pred']=score;f['vintage']=repeat
    return f

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--annual',required=True);ap.add_argument('--pca',required=True);ap.add_argument('--out',required=True)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    a=ap.parse_args();old=Path(a.annual);pca=Path(a.pca);out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    if sha(old/'RESULT.json')!=ANNUAL_SHA or sha(pca/'RESULT.json')!=PCA_SHA:raise ValueError('Wrong completed reference')
    original=json.loads((old/'RESULT.json').read_text());reduced=json.loads((pca/'RESULT.json').read_text())
    references=[]
    for folder,result in ((old,original),(pca,reduced)):
        path=folder/'NATIVE_PREDICTIONS.parquet'
        if sha(path)!=result['files_sha256'][path.name]:raise ValueError('Reference predictions changed')
        references.append(pd.read_parquet(path))
    frames={name:[] for name in ('FULL_FROZEN','RETAINED_FROZEN','DISCARDED_FROZEN','PCA95_REFIT')}
    folds=[];date_rows=[];input_hashes={}
    for i in (1,2,3):
        panel_path=Path(getattr(a,f'r{i}'))/'TI_COMPACT.parquet';input_hashes[str(i)]=sha(panel_path)
        if input_hashes[str(i)]!=original['input_sha256'][str(i)] or input_hashes[str(i)]!=reduced['input_sha256'][str(i)]:raise ValueError('Changed frozen panel')
        panel=pd.read_parquet(panel_path)
        for c in ('signal_date','exit_date_21'):panel[c]=pd.to_datetime(panel[c])
        valid=panel[v1.FEATURES].notna().sum(axis=1)>=30
        for year in range(2017,2027):
            cutoff=pd.Timestamp(year,1,1)
            train=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)&panel.target_rank_21.notna()&valid].sort_values(v1.KEYS).reset_index(drop=True)
            sub,_,_=v1.split_training(train,year)
            test=panel[(panel.signal_date.dt.year==year)&(panel.signal_date<='2026-06-30')&valid].sort_values(v1.KEYS).reset_index(drop=True)
            om=original['per_year'][str(year)]['transforms'][str(i)];pm=reduced['per_year'][str(year)]['transforms'][str(i)]
            if v1.keys_hash(train)!=om['train_keys_sha256'] or v1.keys_hash(sub)!=om['subtrain_keys_sha256']:raise ValueError('Wrong training cohort')
            paths=[old/'models'/Path(om['saved_models'][0]).name,pca/'models'/Path(pm['saved_models'][0]).name]
            for path,folder,result in zip(paths,(old,pca),(original,reduced)):
                if sha(path)!=result['model_files_sha256'][path.relative_to(folder).as_posix()]:raise ValueError('Model changed')
            with np.load(paths[0],allow_pickle=False) as z:
                state={k:z[k].copy() for k in ('median','mean','scale')};w=z['w'].copy()
            with np.load(paths[1],allow_pickle=False) as z:
                basis=z['pca_basis'].copy();wr=z['w'].copy()
                for k in state:np.testing.assert_array_equal(state[k],z[k])
            keep,discard=split_weights(w,basis)
            x=v1.transform(v1.raw_matrix(sub),state)
            if v1.array_hash(x)!=om['fit_matrix_sha256']:raise ValueError('Standardized fit matrix mismatch')
            energy=energy_split(x,v1.query_indices(sub),basis)
            norm_fraction=float(discard@discard/(w@w))
            folds.append(dict(year=year,download=i,discarded_coefficient_norm_fraction=norm_fraction,**energy))
            xt=v1.transform(v1.raw_matrix(test),state)
            scores={'FULL_FROZEN':xt@w,'RETAINED_FROZEN':xt@keep,'DISCARDED_FROZEN':xt@discard,'PCA95_REFIT':xt@wr}
            np.testing.assert_allclose(scores['FULL_FROZEN'],scores['RETAINED_FROZEN']+scores['DISCARDED_FROZEN'],atol=1e-12,rtol=0)
            for kind,ref in zip(('FULL_FROZEN','PCA95_REFIT'),references):
                f=ref[(ref.vintage.astype(int)==i)&(ref.signal_date.dt.year==year)].sort_values(v1.KEYS).reset_index(drop=True)
                pd.testing.assert_frame_equal(f[v1.KEYS],test[v1.KEYS],check_exact=True)
                np.testing.assert_allclose(f.pred,scores[kind],rtol=0,atol=1e-12)
            for kind,score in scores.items():frames[kind].append(prediction_frame(test,score,i))
            for date,g in test.groupby('signal_date',sort=True):
                ix=g.index.to_numpy();ss={k:s[ix] for k,s in scores.items()}
                center={k:s-s.mean() for k,s in ss.items()}
                vf=float(np.mean(center['FULL_FROZEN']**2));vk=float(np.mean(center['RETAINED_FROZEN']**2));vd=float(np.mean(center['DISCARDED_FROZEN']**2))
                cov=float(np.mean(center['RETAINED_FROZEN']*center['DISCARDED_FROZEN']))
                if abs(vf-vk-vd-2*cov)>1e-12:raise ValueError('Within-date score variance mismatch')
                date_rows.append(dict(signal_date=str(date),download=i,full_score_variance=vf,retained_score_variance=vk,discarded_score_variance=vd,twice_covariance=2*cov,
                                      full_discarded_rank_corr=float(pd.Series(ss['FULL_FROZEN']).rank().corr(pd.Series(ss['DISCARDED_FROZEN']).rank())),
                                      full_retained_rank_corr=float(pd.Series(ss['FULL_FROZEN']).rank().corr(pd.Series(ss['RETAINED_FROZEN']).rank()))))
            print(f'NOFIT_DECOMPOSITION_PASS {year}/{i}',flush=True)
    qualities={}
    for name,parts in frames.items():
        f=pd.concat(parts,ignore_index=True);f.to_parquet(out/(name+'.parquet'),index=False)
        qualities[name]=evaluate(f,quality_exit_cutoff='2026-07-01')
    paired={}
    for candidate,base in [('RETAINED_FROZEN','FULL_FROZEN'),('DISCARDED_FROZEN','FULL_FROZEN'),('DISCARDED_FROZEN','RETAINED_FROZEN')]:
        full=paired_compare(qualities[candidate],qualities[base],block_lengths=(6,12),n_bootstrap=3000,seed=20261016)
        paired[candidate+'__minus__'+base]=dict(paired_dates=full['paired_dates'],difference=full['difference'],
            bootstrap={b:{key:{k:v for k,v in x.items() if k in ('lower','upper','valid_draws')} for key,x in f['intervals_95pct'].items() if x is not None and key in ('top1_realized_percentile','ndcg5','rank_ic')} for b,f in full['bootstrap'].items()},
            interpretation='Exploratory, unadjusted95%calendar-block intervals; vintages averaged by date; no independent confirmation')
    pd.DataFrame(folds).to_csv(out/'TRAINING_ENERGY.csv',index=False)
    pd.DataFrame(date_rows).to_csv(out/'WITHIN_DATE_SCORES.csv',index=False)
    report=dict(status='PCA_DISCARDED_NOFIT_COMPLETE',new_learner_fits=0,no_portfolio_replay=True,
                references=dict(annual_result_sha256=ANNUAL_SHA,pca_result_sha256=PCA_SHA),input_sha256=input_hashes,
                quality={k:v['aggregate_by_date'] for k,v in qualities.items()},
                quality_per_year={k:v['per_year'] for k,v in qualities.items()},paired_exploratory=paired,
                coefficients_discarded_mean_fraction=float(np.mean([r['discarded_coefficient_norm_fraction'] for r in folds])),
                training_energy_mean={key:float(np.mean([r[key] for r in folds])) for key in ('fraction_retained_total','fraction_retained_within','fraction_retained_between')},
                temporal_information='Each score uses only training-fitted basis/coefficients and its own historical features at signal',
                interpretation='Discarded frozen coefficients were learned jointly with retained coordinates; this is not a model trained only on discarded directions. No new CAGR measured.')
    (out/'SUMMARY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'],quality=report['quality'],training_energy_mean=report['training_energy_mean']),indent=2))

if __name__=='__main__':main()
