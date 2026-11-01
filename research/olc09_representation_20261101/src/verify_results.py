"""Independent audits of saved batches, prior controls, inference and portfolio values."""
from bridge import *
from schema import canonical_matrix
from train_models import CONFIGS,effective_parameters
from replay_models import ARCHIVE,source
import numpy as np,pandas as pd,xgboost as xgb,joblib,json
OUT=ROOT/'results'

def main():
    inputs={};checks=[];forecast_checks=[];future_checks=[]
    for m in ['EU','USA']:
        for y in range(2019,2027):inputs[m,y]=joblib.load(ROOT/'cache'/f'{m}_{y}.joblib')
    for folder in sorted((ROOT/'models').glob('*/*/*')):
        if not folder.is_dir():continue
        mark=json.loads((folder/'COMPLETE.json').read_text());assert valid_checkpoint(folder,mark['key'])
        a=json.loads((folder/'audit.json').read_text());m=a['market'];y=a['year'];c=a['config'];cfg=CONFIGS[c];d=inputs[m,y]
        X,XP=d['matrices'][cfg['pack']]
        if cfg['reverse']:X=X[:,::-1];XP=XP[:,::-1]
        assert [arr_hash(X),arr_hash(XP),arr_hash(d['y'])]==a['actual_input_hashes']
        assert a['input_metadata']['train_keys']==d['metadata']['train_keys']
        assert (pd.to_datetime(d['train_exits'])<pd.Timestamp(y,1,1)).all()
        e,x=effective_parameters(cfg,X.shape[1]);assert e==a['parameters_ET'] and x==a['parameters_XGB']
        p=pd.read_csv(folder/'predictions.csv.gz',parse_dates=['signal_date','source_date'],float_precision='round_trip')
        ref=d['reference'];assert p[['signal_date','ticker']].equals(ref[['signal_date','ticker']])
        for col in ['RETURN_RAW','RETURN']:np.testing.assert_allclose(p[col],ref[col],rtol=0,atol=0,equal_nan=True)
        assert (p.source_date.dropna()<=p.loc[p.source_date.notna(),'signal_date']).all()
        checks.append({'market':m,'config':c,'year':y,'train_rows':len(X),'test_rows':len(XP),'features':X.shape[1],'train_last_exit':str(pd.to_datetime(d['train_exits']).max()),'checkpoint_verified':True})
        if y==2022 and c in ['FIXED_PATH_S101','ALL_CORE_S101','REVERSE42_S101']:
            z=joblib.load(folder/'ET.joblib');et=z['model'];imp=z['imputer'];gb=xgb.XGBRegressor();gb.load_model(folder/'HYBRID_XGB.ubj')
            test=imp.transform(XP);h=d['predict_keys'].copy();h['ET_RAW']=et.predict(test);h['XGB_RAW']=gb.predict(test)
            h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
            rebuilt=ref.drop(columns=['ET','ET_RAW','XGB','XGB_RAW']).merge(h,on=['signal_date','ticker'],how='outer',validate='one_to_one')
            rebuilt=canonical_forecasts(rebuilt.sort_values(['signal_date','ticker']).reset_index(drop=True))
            for col in ['ET','XGB','ET_RAW','XGB_RAW']:
                err=float(np.nanmax(abs(rebuilt[col]-p[col])));assert err==0
                forecast_checks.append(dict(market=m,config=c,year=y,field=col,max_error=err))
            later=d['predict_keys'].signal_date.to_numpy()>=np.datetime64('2022-09-01');early=~later
            altered=XP.copy();altered[later]=12345.
            altered=imp.transform(altered)
            for learner,model in [('ET',et),('XGB',gb)]:
                err=float(np.max(abs(model.predict(test)[early]-model.predict(altered)[early])));assert err==0
                future_checks.append(dict(market=m,config=c,year=y,learner=learner,previous_prediction_error=err,scope='future inference rows changed; source-feature and training-lineage checks separate'))
    assert len(checks)==272
    pd.DataFrame(checks).to_csv(OUT/'ANNUAL_FIT_VERIFICATION.csv',index=False)
    pd.DataFrame(forecast_checks).to_csv(OUT/'SAVED_MODEL_RELOAD_CHECKS.csv',index=False)
    pd.DataFrame(future_checks).to_csv(OUT/'FUTURE_INFERENCE_CHECKS.csv',index=False)
    control=[]
    for m in ['EU','USA']:
        for v,parentname in ARCHIVE.items():
            for fee in [10,30]:
                for policy in ['IMMEDIATE','DELAY3','PHASE5']:
                    paths=[PARENT/'results'/sub/f'{m}_{parentname}_{policy}_C{fee}.npz' for sub in ['paths','null_paths']]
                    exists=[p for p in paths if p.exists()]
                    if not exists:continue
                    new=np.load(OUT/'paths'/f'{m}_{v}_{policy}_C{fee}.npz',allow_pickle=False);old=np.load(exists[0],allow_pickle=False)
                    errs={k:float(np.max(abs(new[k]-old[k]))) for k in ['nav','primary_units','defensive_units','targets','ledger','free_cash']}
                    assert max(errs.values())==0
                    control.append(dict(market=m,variant=v,policy=policy,fee=fee,max_array_error=max(errs.values())))
    pd.DataFrame(control).to_csv(OUT/'EXACT_PARENT_CONTROLS.csv',index=False)
    assert len(control)==48
    summary=json.loads((OUT/'REPLAY_SUMMARY.json').read_text())
    summary.update(new_models=544,baseline_control_refits=4,verified_annual_batches=len(checks),authenticated_batch_files=sum(len(json.loads(p.read_text())['files']) for p in (ROOT/'models').glob('*/*/*/COMPLETE.json')),exact_parent_control_paths=len(control),reload_model_checks=len(forecast_checks),future_inference_checks=len(future_checks),canonical_input_alias_order_checks=32,review='Author review, not independent external reviewer.',limitations='Reused historical cohorts and source assumptions; no newly certified total-return, delisting, spread or real execution.')
    atomic_json(OUT/'VERIFIED_SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
