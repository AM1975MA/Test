"""Independent checks of saved model outputs, target metrics and temporal contracts."""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
from pathlib import Path
import json
import numpy as np,pandas as pd,joblib,xgboost as xgb
from sklearn.metrics import ndcg_score,brier_score_loss,log_loss
from recovery_core import atomic_json,valid_checkpoint,canonical_forecasts
from prepare import readcsv
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'results'

def independent_top_weights(scores):
    s=np.asarray(scores,float);cut=sorted(s,reverse=True)[1]
    hi=s>cut;tie=s==cut
    return (hi.astype(float)+tie*(2-hi.sum())/tie.sum())/2

def main():
    model_count=0;future_checks=0;maxerr=0.;maxmetric=0.;nmetric=0;input_checks=0
    for market in ['EU','USA']:
        labels=readcsv(ROOT/'inputs'/f'{market}_LAYER_LABELS.csv.gz')
        for year in range(2019,2027):
            d=joblib.load(ROOT/'inputs/annual'/f'{market}_{year}.joblib');cut=pd.Timestamp(year,1,1)
            good=[]
            for date,g in labels.groupby('signal_date'):
                if date<cut and g.TARGET.notna().all() and g.exit_date_63.notna().all() and (g.exit_date_63<cut).all():good.append(date)
            expected=labels[labels.signal_date.isin(good)].sort_values(['signal_date','ticker']).reset_index(drop=True)
            assert expected[['signal_date','ticker']].equals(d['train_keys'][['signal_date','ticker']])
            np.testing.assert_array_equal(expected.TARGET,d['y'])
            binary=[]
            for date,g in expected.groupby('signal_date',sort=True):
                y=g.TARGET.to_numpy();rank=(y[:,None]>y[None,:]).sum(1)+((y[:,None]==y[None,:]).sum(1)+1)/2
                binary.extend((rank/len(y)>.8).astype(int))
            np.testing.assert_array_equal(binary,d['binary']);input_checks+=1
            for seed in [101,211,307]:
                folder=ROOT/'models'/market/str(year)/str(seed);c=json.loads((folder/'COMPLETE.json').read_text());assert valid_checkpoint(folder,c['key'])
                imp=joblib.load(folder/'IMPUTER.joblib');xp=imp.transform(d['XP']);ref=readcsv(folder/'predictions.csv.gz');out=d['predict_keys'].copy()
                for family in ['ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']:
                    if family.startswith('ET'):model=joblib.load(folder/(family+'.joblib'))
                    else:
                        model={'XGB_REG':xgb.XGBRegressor,'XGB_CLASS':xgb.XGBClassifier,'XGB_RANK':xgb.XGBRanker}[family]();model.load_model(folder/(family+'.ubj'))
                    pred=model.predict_proba(xp)[:,1] if family.endswith('CLASS') else model.predict(xp)
                    out[family]=pred;model_count+=1
                    if year==2022 and seed==101:
                        altered=xp.copy();k=len(xp)//2;altered[k:]=0.123
                        again=model.predict_proba(altered)[:,1] if family.endswith('CLASS') else model.predict(altered)
                        np.testing.assert_array_equal(pred[:k],again[:k]);future_checks+=1
                out=canonical_forecasts(out)
                for col in ['ET_REG','XGB_REG','ET_CLASS','XGB_CLASS','XGB_RANK']:
                    err=float(np.max(abs(out[col]-ref[col])));maxerr=max(maxerr,err);assert err==0,(market,year,seed,col,err)
    # Recompute every saved ensemble native-target statistic from output arrays, not summaries.
    t=pd.read_csv(O/'TARGET_MONTHS.csv',parse_dates=['date']);t=t[t.seed=='MEAN3'];cache={}
    for row in t.itertuples(index=False):
        key=(row.market,row.variant)
        if key not in cache:cache[key]=readcsv(O/f'{row.market}_{row.variant}_MEAN3_OUTPUTS.csv.gz')
        f=cache[key];g=f[(f.signal_date==row.date)&np.isfinite(f.CURRENT)&np.isfinite(f.RETURN)]
        y=g.TARGET.to_numpy();s=g[row.stage].to_numpy();w=independent_top_weights(s)
        rank=(y[:,None]>y[None,:]).sum(1)+((y[:,None]==y[None,:]).sum(1)+1)/2
        checks={'ndcg2':ndcg_score(y[None,:],s[None,:],k=2),'ndcg5':ndcg_score(y[None,:],s[None,:],k=5),
                'selected_target':float(sum(w*y)),'target_regret':float(np.mean(sorted(y)[-2:])-sum(w*y)),
                'target_top_quintile_precision':float(sum(w*(rank/len(y)>.8))),
                'target_bottom_quintile_fraction':float(sum(w*(rank/len(y)<=.2)))}
        for k,v in checks.items():
            err=abs(v-getattr(row,k));maxmetric=max(maxmetric,err);nmetric+=1;assert err<1e-12,(key,row.date,k,err)
    # Verify each table summary using direct numpy aggregation.
    summary_checks=0
    for months,summary,keys in [('TARGET_MONTHS.csv','TARGET_SUMMARY.csv',['market','variant','seed','stage','period']),('OPPORTUNITY_MONTHS.csv','OPPORTUNITY_SUMMARY.csv',['market','variant','seed','stage','period','horizon']),('NATIVE_LEARNER_MONTHS.csv','NATIVE_LEARNER_SUMMARY.csv',['market','seed','learner','period']),('NATIVE_OPPORTUNITY_MONTHS.csv','NATIVE_OPPORTUNITY_SUMMARY.csv',['market','seed','learner','period','horizon']),('PROBABILITY_MONTHS.csv','PROBABILITY_SUMMARY.csv',['market','seed','predictor','period'])]:
        a=pd.read_csv(O/months);b=pd.read_csv(O/summary).set_index(keys)
        for key,g in a.groupby(keys):
            r=b.loc[key];assert int(r['months'])==g.date.nunique()
            for col in b.columns:
                if col=='months':continue
                arr=g[col].to_numpy(float);value=float(np.mean(arr[np.isfinite(arr)])) if np.isfinite(arr).any() else np.nan
                if np.isnan(value):assert np.isnan(r[col])
                else:assert abs(value-r[col])<1e-12
                summary_checks+=1
    # Original archived channels and full-support inference must not change between variants.
    return_checks=0
    for market in ['EU','USA']:
        base=readcsv(ROOT/'inputs'/f'{market}_R_RSI_DOMAIN_FORECASTS.csv.gz').sort_values(['signal_date','ticker']).reset_index(drop=True)
        for variant in ['ARCHIVED_REG','MATCHED_REG','ET_CLASS','XGB_CLASS','BOTH_CLASS','XGB_RANK','RANK_ONLY']:
            f=readcsv(O/f'{market}_{variant}_MEAN3_OUTPUTS.csv.gz').sort_values(['signal_date','ticker']).reset_index(drop=True)
            assert f[['signal_date','ticker']].equals(base[['signal_date','ticker']]);np.testing.assert_array_equal(f.RETURN,base.RETURN);return_checks+=1
    result={'new_models_reopened':model_count,'new_model_prediction_max_error':maxerr,'original_parity_refits':4,'annual_input_cohorts_independently_checked':input_checks,'future_inference_perturbations':future_checks,'ensemble_target_metric_values_independently_recomputed':nmetric,'metric_max_error':maxmetric,'table_summary_values_recomputed':summary_checks,'unchanged_return_and_inference_support_checks':return_checks,'new_portfolios':0,'review':'author verification, not independent external review; complete-cohort control covers this target, not all original market-data assumptions'}
    atomic_json(O/'VERIFIED_SUMMARY.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':main()
