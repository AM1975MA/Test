"""Independent numeric checks plus native-source parity and real-data future perturbations."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from sklearn.metrics import ndcg_score
from integration import build_scores,VARIANTS
from prepare import read
from meta_fusion import fit_meta,mature_groups
from scipy.special import logit
R=Path(__file__).resolve().parents[1];O=R/'results';I=R/'inputs'

def main():
    score=read(O/'ALL_SCORECARD.csv');checks=[];count=0
    for key,g in score.groupby('config',sort=False):
        market=g.market.iloc[0];q=np.load(I/f'{market}_STATE_HALF.npz');z=np.load(O/f'paths/{key}.npz');dates=pd.DatetimeIndex(z['dates']);valuation=dates[1:]
        nav=z['nav'];capital=(z['primary_units'][:-1]*q['O'][1:]).sum(1)+(z['defensive_units'][:-1]*q['O'][1:]).sum(1)+z['free_cash'][:-1]
        nav_err=float(np.max(np.abs(capital-nav[:-1])));assert nav_err<1e-10
        prev=np.r_[1.,nav[:-2]];daily=nav[:-1]/prev-1.;metric_error=0.
        for row in g.itertuples(index=False):
            if row.period=='FULL':lo,hi=valuation[0],valuation[-1]
            elif row.period=='PRE2025':lo,hi=pd.Timestamp('2019-02-01'),pd.Timestamp('2024-12-31')
            elif row.period=='ACTIVE2021_2024':lo,hi=pd.Timestamp('2021-01-01'),pd.Timestamp('2024-12-31')
            elif row.period=='CRASH2020':lo,hi=pd.Timestamp('2020-02-01'),pd.Timestamp('2020-03-31')
            elif row.period=='LATE2021_2023':lo,hi=pd.Timestamp('2021-11-01'),pd.Timestamp('2023-12-31')
            else:lo,hi=pd.Timestamp(int(row.period),1,1),pd.Timestamp(int(row.period),12,31)
            mask=(valuation>=lo)&(valuation<=hi);returns=daily[mask];wealth=np.cumprod(1+returns);peak=np.maximum.accumulate(np.r_[1.,wealth])[1:]
            vals={'cagr':float(wealth[-1]**(252/len(returns))-1),'annual_log':float(np.log(wealth[-1])*252/len(returns)),'maxdd':float(np.min(wealth/peak-1)),'period_return':float(wealth[-1]-1)}
            assert mask.sum()==row.n and str(valuation[mask][0].date())==row.first_valuation and str(valuation[mask][-1].date())==row.last_valuation
            metric_error=max(metric_error,max(abs(vals[k]-getattr(row,k)) for k in vals));count+=len(vals)
        assert metric_error<1e-10,(key,metric_error)
        checks.append({'config':key,'intervals':len(nav)-1,'NAV_error':nav_err,'metric_error':metric_error})
    pd.DataFrame(checks).to_csv(O/'INDEPENDENT_PORTFOLIO_CHECKS.csv',index=False)
    prefix=[];native_checks=0;max_rank_error=0.
    for market in ['EU','USA']:
        f=read(I/f'{market}_MEAN3_INPUTS.csv.gz');scores=build_scores(f);label=read(I/f'{market}_LAYER_LABELS.csv.gz')
        for cutoff in [pd.Timestamp('2022-12-31'),pd.Timestamp('2024-12-31')]:
            altered=f.copy();late=altered.signal_date>cutoff
            for col in ['RETURN','ET_REG','XGB_REG','XGB_CLASS','ARCH_ET','ARCH_XGB']:altered.loc[late,col]=.321
            other=build_scores(altered);past=scores.signal_date<=cutoff
            pd.testing.assert_frame_equal(scores.loc[past].reset_index(drop=True),other.loc[past].reset_index(drop=True))
            prefix.append({'market':market,'cutoff':str(cutoff.date()),'all_fixed_scores_unchanged':True})
        for seed in ['MEAN3','101','211','307']:
            s=read(O/f'{market}_INTEGRATED_SCORES.csv.gz') if seed=='MEAN3' else build_scores(read(I/f'{market}_S{seed}_INPUTS.csv.gz'))
            d=s.merge(label,on=['signal_date','ticker']);old=read(O/'LAYER_MONTHS.csv');old=old[(old.market==market)&(old.seed.astype(str)==seed)&(old.period=='PRE2025')]
            for date,g in d.groupby('signal_date'):
                g=g[np.isfinite(g[VARIANTS]).all(1)]
                if len(g)<20 or not np.isfinite(g.TARGET).all() or g.exit_date_63.isna().any() or not(pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and g.exit_date_63.max()<pd.Timestamp('2025-01-01')):continue
                for variant in VARIANTS:
                    row=old[(old.date==date)&(old.variant==variant)]
                    if row.empty:continue
                    a=ndcg_score(g.TARGET.to_numpy()[None,:],g[variant].to_numpy()[None,:],k=2,ignore_ties=False)
                    er=abs(a-row.ndcg2.iloc[0]);assert er<1e-12;max_rank_error=max(max_rank_error,er);native_checks+=1
        # Real-data learned-fusion refit with modified current/future outcomes.
        f=f[['signal_date','ticker','RETURN','XGB_CLASS']].merge(scores[['signal_date','ticker','MATCHED_REG']],on=['signal_date','ticker']).merge(label,on=['signal_date','ticker'])
        f['H_SIGNAL']=(f.MATCHED_REG-.475*f.RETURN)/.525;f['C_LOGIT']=logit(f.XGB_CLASS.clip(1e-6,1-1e-6));f=f[np.isfinite(f[['RETURN','H_SIGNAL','C_LOGIT']]).all(1)]
        for year in [2022,2025]:
            perturbed=f.copy();future=perturbed.exit_date_63>=pd.Timestamp(year,1,1);perturbed.loc[future,'TARGET']=1.-perturbed.loc[future,'TARGET']
            a=mature_groups(f,year);b=mature_groups(perturbed,year);pd.testing.assert_frame_equal(a,b)
            cols=['RETURN','H_SIGNAL','C_LOGIT'];y=(a.groupby('signal_date').TARGET.rank(method='average',pct=True)>.8).astype(float).to_numpy()
            trained=fit_meta(a[cols].to_numpy(),y,a.signal_date.to_numpy());saved=json.loads((O/f'meta_models/{market}_{year}_META3.json').read_text())
            err=max(abs(np.asarray(trained['coef'])-saved['coef']));assert err<1e-12
            prefix.append({'market':market,'year':year,'future_label_refit_equal':True,'max_coef_error':float(err)})
    (O/'PREFIX_CHECKS.json').write_text(json.dumps(prefix,indent=2))
    summary={'portfolio_paths':len(checks),'accounting_intervals':sum(c['intervals'] for c in checks),'independent_metrics':count,'max_NAV_error':max(c['NAV_error'] for c in checks),'max_metric_error':max(c['metric_error'] for c in checks),'sklearn_NDCG_checks':native_checks,'max_NDCG_error':max_rank_error,'real_future_perturbation_checks':len(prefix),'base_model_fits':0,'meta_fits':24,'self_review_not_independent':True}
    (O/'VERIFIED_SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
