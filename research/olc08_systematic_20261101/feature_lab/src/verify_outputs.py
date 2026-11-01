"""Reconstruct all fitted input contracts and selected stored forecasts independently.
No new candidate selection, no changes to trained predictions or portfolios.
"""
from bootstrap import *
from train_pack import annual_inputs,enrich,new_panel,reference,VARS,arr_hash,key_hash
from feature_blocks import PATH,SESSION,LEADERSHIP,leadership_block,prune_training
import pandas as pd,numpy as np,json,joblib,xgboost as xgb,time
from functools import lru_cache

@lru_cache(maxsize=16)
def original(market,year):return annual_inputs(market,'R_RSI_DOMAIN',year)

def reconstruct(a):
    market,year,variant=a['market'],a['year'],a['variant']
    tr,pr,cols,y,groups,ht,pp,hc,horizon=original(market,year)
    cols=a['return_columns'];hc=a['hybrid_columns']
    new=[x for x in cols if x not in tr.columns]
    tr=enrich(tr,new_panel(market,'RETURN'),new);pr=enrich(pr,new_panel(market,'RETURN'),new)
    hnew=[x for x in hc if x not in ht.columns]
    ht=enrich(ht,new_panel(market,'HYBRID'),hnew);pp=enrich(pp,new_panel(market,'HYBRID'),hnew)
    X=tr[cols].to_numpy(float);XP=pr[cols].to_numpy(float);X[~np.isfinite(X)]=np.nan;XP[~np.isfinite(XP)]=np.nan
    HX=ht[hc].to_numpy(float);HP=pp[hc].to_numpy(float);hy=ht.TARGET.to_numpy(float)
    return tr,pr,ht,pp,X,XP,y,groups,HX,HP,hy

def verify():
    started=time.time();rows=[];files=0;models=0;prediction_rows=[]
    for market in ['EU','USA']:
      for year in range(2019,2027):
        for variant in VARS:
          f=ROOT/'models'/market/variant/str(year)
          marker=json.loads((f/'COMPLETE.json').read_text());assert valid_checkpoint(f,marker['key'])
          a=json.loads((f/'audit.json').read_text())
          for name,sha in a['source_hashes'].items():assert sha256(ROOT/'src'/name)==sha
          tr,pr,ht,pp,X,XP,y,groups,HX,HP,hy=reconstruct(a)
          assert [arr_hash(x) for x in [X,XP,y,groups]]==a['return_input_hashes']
          assert [arr_hash(x) for x in [HX,HP,hy]]==a['hybrid_input_hashes']
          assert key_hash(tr)==a['return_train_keys'] and key_hash(ht)==a['hybrid_train_keys']
          assert key_hash(pr)==a['return_predict_keys'] and key_hash(pp)==a['hybrid_predict_keys']
          cut=pd.Timestamp(year,1,1)
          assert tr.exit_date_21.max()<cut and ht.exit_date_63.max()<cut
          assert (tr.source_date<=tr.signal_date).all() and (pr.source_date<=pr.signal_date).all()
          assert (ht.source_date<=ht.signal_date).all() and (pp.source_date<=pp.signal_date).all()
          b=json.loads((PARENT/'fits'/market/'BASE'/str(year)/'audit.json').read_text())
          assert a['return_input_hashes'][2:]==b['return_matrices'][2:]
          assert a['hybrid_input_hashes'][2]==b['hybrid_matrices'][2]
          files+=len(marker['files']);models+=len(a['trained_models'])
          rows.append({'market':market,'variant':variant,'year':year,'input_hashes_equal':True,'matched_rows_and_labels':True,'strict_maturity':True,'checkpoint_files_verified':len(marker['files'])})
          if year==2022 and variant in ['R_SESSION','R_PRUNE_ALL','H_UNIQUE','H_PATH']:
            stored=pd.read_csv(f/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip')
            ref=reference(market);pred=ref[ref.signal_date.dt.year.eq(year)].copy()
            if variant.startswith('R_'):
              d=xgb.QuantileDMatrix(X,label=y,nthread=1);d.set_group(groups);dt=xgb.QuantileDMatrix(XP,ref=d,nthread=1)
              values=[]
              for seed in [101,202,303]:
                m=xgb.Booster();m.load_model(f/f'RETURN_{seed}.ubj');values.append(m.predict(dt))
              out=pr[['signal_date','ticker']].copy();out['RETURN_RAW']=np.mean(values,axis=0);out['RETURN']=out.groupby('signal_date').RETURN_RAW.rank(pct=True)
              pred=pred.drop(columns=['RETURN_RAW','RETURN']).merge(out,on=['signal_date','ticker'],how='outer',validate='one_to_one')
            else:
              pack=joblib.load(f/'ET.joblib');imp=pack['imputer'];z=imp.transform(HP)
              et=pack['model'];gb=xgb.XGBRegressor();gb.load_model(f/'HYBRID_XGB.ubj')
              out=pp[['signal_date','ticker']].copy();out['ET_RAW']=et.predict(z);out['XGB_RAW']=gb.predict(z)
              out['ET']=out.groupby('signal_date').ET_RAW.rank(pct=True);out['XGB']=out.groupby('signal_date').XGB_RAW.rank(pct=True)
              pred=pred.drop(columns=['ET_RAW','ET','XGB_RAW','XGB']).merge(out,on=['signal_date','ticker'],how='outer',validate='one_to_one')
            pred=canonical_forecasts(pred.sort_values(['signal_date','ticker']).reset_index(drop=True))
            assert pred[['signal_date','ticker']].equals(stored[['signal_date','ticker']])
            errors={c:float(np.nanmax(abs(pred[c]-stored[c]))) for c in ['RETURN_RAW','RETURN','ET_RAW','ET','XGB_RAW','XGB']}
            assert max(errors.values())==0,errors
            prediction_rows.append({'market':market,'variant':variant,'year':year,'max_prediction_error':0.,'model_reload_not_refit':True})
        print('VERIFIED_INPUTS',market,year,flush=True)
    temporal=[];redundancy=[]
    for market in ['EU','USA']:
        cp=pd.read_pickle(ROOT/'inputs'/f'{market}_RSI_COMPACT.pkl')
        original_features=leadership_block(cp)
        for cut in [pd.Timestamp('2020-12-31'),pd.Timestamp('2024-12-31')]:
            mask=cp.signal_date<=cut
            subset=cp.loc[mask].copy();out=leadership_block(subset)
            pd.testing.assert_frame_equal(out,original_features.loc[mask])
            altered=cp.copy();altered.loc[~mask,'mom21']=123456.;altered.loc[~mask,'mom63']=-654321.
            pd.testing.assert_frame_equal(original_features.loc[mask],leadership_block(altered).loc[mask])
            temporal.append({'market':market,'cutoff':str(cut.date()),'prefix_equality':True,'future_rank_perturbation_equality':True})
        for year in [2021,2026]:
            tr,_,cols,*_=original(market,year)
            kept,log=prune_training(tr,cols)
            recorded=json.loads((ROOT/'models'/market/'R_PRUNE'/str(year)/'audit.json').read_text())
            assert kept==recorded['return_columns'] and log==recorded['pruning']
            enriched=enrich(tr,new_panel(market,'RETURN'),PATH+SESSION+LEADERSHIP)
            corr=enriched[cols+PATH+SESSION+LEADERSHIP].corr(method='spearman',min_periods=300)
            for feature in PATH+SESSION+LEADERSHIP:
                scores=corr.loc[feature,cols].abs().dropna()
                partner=scores.idxmax()
                redundancy.append({'market':market,'training_cutoff':f'{year}-01-01','new_feature':feature,'most_correlated_old':partner,'abs_spearman':float(scores.max()),'scope':'diagnostic only; no outcome-based input selection'})
    pd.DataFrame(rows).to_csv(ROOT/'results/INDEPENDENT_FIT_CHECKS.csv',index=False)
    pd.DataFrame(prediction_rows).to_csv(ROOT/'results/MODEL_RELOAD_CHECKS.csv',index=False)
    pd.DataFrame(redundancy).to_csv(ROOT/'results/NEW_OLD_TRAIN_REDUNDANCY.csv',index=False)
    result={'fit_batches_checked':len(rows),'model_files_count':models,'hashed_checkpoint_files':files,'model_reload_predictions_checked':len(prediction_rows),'model_reload_max_error':0.,'real_leadership_prefix_checks':temporal,'pruning_recomputed_train_only':4,'new_old_redundancy_rows':len(redundancy),'sample_scope':'Eight 2022 batches reloaded for forecasts, no full refit during this audit; all 176 input/label matrices and maturity audited.','seconds':round(time.time()-started,1)}
    atomic_json(ROOT/'results/INDEPENDENT_VERIFICATION.json',result);print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':verify()
