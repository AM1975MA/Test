"""Compare existing candidate/reference curves; no fit or new market replay.
Historical exploratory comparison after prior inspection, not independent validation.
Run in the original analysis environment with the downloaded reconciliation ZIP.
"""
from pathlib import Path
from zipfile import ZipFile
import io
import numpy as np
import pandas as pd
ROOT=Path(__file__).parent
ARCHIVE=Path('/mnt/data/ETF_Trader_Component_Reconciliation_20261031.zip')
with ZipFile(ARCHIVE) as outer:
    paths=ZipFile(io.BytesIO(outer.read('results/ALL_384_POLICY_PATHS.zip')))
    def logs(arm,mask):
        data=[]; dates=None
        for v in [1,2,3]:
            with np.load(io.BytesIO(paths.read(f'policy_paths/{arm}/r{v}/{mask:02d}.npz')),allow_pickle=False) as z:
                nav=z['nav'];ds=z['dates']
                assert np.isfinite(nav).all() and np.all(nav>0)
                if dates is not None: assert np.array_equal(ds,dates)
                dates=ds;data.append(np.diff(np.log(np.r_[1.,nav])))
        return np.asarray(data),dates
    candidate,ds=logs('R_T0_H1',62)
    contrasts=[('BASE_ORIGINAL','B_T1_H1',63),('BASE_EQUAL_HALF','B_T1_H1',62),('RH_NATIVE_WEIGHTS','R_T0_H1',63)]
    result=[]
    for label,arm,mask in contrasts:
        ref,dates=logs(arm,mask);assert np.array_equal(ds,dates)
        x=(candidate-ref).mean(axis=0);n=len(x)
        for block in [21,63]:
            rng=np.random.default_rng(20261031);reps=10000;full,rem=divmod(n,block)
            ext=np.r_[x,x[:block]];cs=np.r_[0.,ext.cumsum()];starts=np.arange(n)
            sums=cs[starts+block]-cs[starts]
            draws=[]
            for a in range(0,reps,250):
                cnt=min(250,reps-a)
                means=sums[rng.integers(0,n,size=(cnt,full))].sum(axis=1)
                if rem:
                    r=rng.integers(0,n,size=cnt);means+=cs[r+rem]-cs[r]
                draws.extend(means/n*25200)
            low,high=np.quantile(draws,[.025,.975])
            result.append(dict(candidate='R_HALF',reference=label,block_sessions=block,sessions=n,seed=20261031,resamples=reps,mean_annual_log_difference_pp=x.mean()*25200,ci95_low_pp=low,ci95_high_pp=high,status='post_selection_historical_diagnostic_no_multiple_research_correction'))
    pd.DataFrame(result).to_csv(ROOT/'candidate_contrasts.csv',index=False)
    metrics=pd.read_csv(io.BytesIO(outer.read('results/ARCHIVED_51_PATHS_RECONCILIATION.csv')))
    records=[]
    for lab,fam,arm in [('BASE originale','factorial','B_T1_H1'),('R+H pesi propri','mediation','R_R'),('R+H 50/50','mediation','R_HALF'),('R+H pesi Hybrid','mediation','R_H')]:
        g=metrics[(metrics.family==fam)&(metrics.arm==arm)]
        records.append(dict(strategy=lab,cagr_mean_pct=g.cagr.mean()*100,maxdd_mean_pct=g.maxdd.mean()*100,cagr_min_pct=g.cagr.min()*100,cagr_max_pct=g.cagr.max()*100))
    policies=pd.read_csv(io.BytesIO(outer.read('results/POLICY_FACTORIAL.csv')))
    g=policies[(policies.arm=='B_T1_H1')&(policies['mask']==62)]
    records.append(dict(strategy='BASE 50/50',cagr_mean_pct=g.cagr.mean()*100,maxdd_mean_pct=g.maxdd.mean()*100,cagr_min_pct=g.cagr.min()*100,cagr_max_pct=g.cagr.max()*100))
    pd.DataFrame(records).to_csv(ROOT/'candidate_metrics.csv',index=False)
    print(pd.DataFrame(records).round(5).to_string(index=False))
    print('\n',pd.DataFrame(result).round(5).to_string(index=False))
