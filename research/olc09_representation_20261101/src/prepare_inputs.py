"""Freeze matched annual matrices and reproduce saved baselines before interventions."""
from bridge import *
from schema import canonical_matrix,column_parameters
import numpy as np,pandas as pd,joblib,xgboost as xgb,json,time
from sklearn.ensemble import ExtraTreesRegressor
CACHE=ROOT/'cache';CACHE.mkdir(exist_ok=True)
OUT=ROOT/'results'

def main():
    rows=[];parity=[];start=time.time()
    for market in ['EU','USA']:
        extra=parent_train.new_panel(market,'HYBRID')
        nulls={s:permute_block(extra,PATH_COLS,s,market) for s in [7101,7102,7103]}
        reference=parent_train.reference(market)
        for year in range(2019,2027):
            tr,pr,cols,y,groups,ht,pp,hc,_=annual_inputs(market,'R_RSI_DOMAIN',year)
            original_train=ht[hc];original_predict=pp[hc]
            ctrain=canonical_matrix(original_train,CORE,ALIASES);cpredict=canonical_matrix(original_predict,CORE,ALIASES)
            # Reordered inputs and explicitly declared extra aliases must map to identical matrices.
            for frame,expected in [(original_train,ctrain),(original_predict,cpredict)]:
                copied=frame.copy();copied['synthetic_alias']=copied[CORE[0]]
                transformed=canonical_matrix(copied.loc[:,list(reversed(copied.columns))],CORE,dict(ALIASES,synthetic_alias=CORE[0]))
                np.testing.assert_array_equal(transformed,expected)
            ptrain=parent_train.enrich(ht,extra,PATH_COLS);ppredict=parent_train.enrich(pp,extra,PATH_COLS)
            Xpath=canonical_matrix(ptrain[CORE+PATH_COLS],CORE+PATH_COLS)
            Ppath=canonical_matrix(ppredict[CORE+PATH_COLS],CORE+PATH_COLS)
            matrices={'CORE':(ctrain,cpredict),'PATH':(Xpath,Ppath),'REF42':(original_train.to_numpy(float),original_predict.to_numpy(float))}
            for seed,e in nulls.items():
                a=parent_train.enrich(ht,e,PATH_COLS);b=parent_train.enrich(pp,e,PATH_COLS)
                matrices[f'NULL{seed}']=(canonical_matrix(a[CORE+PATH_COLS],CORE+PATH_COLS),canonical_matrix(b[CORE+PATH_COLS],CORE+PATH_COLS))
            z=parent_bootstrap.PARENT/'fits'/market/'BASE'/str(year)
            checkpoint=json.loads((z/'COMPLETE.json').read_text());assert valid_checkpoint(z,checkpoint['key'])
            saved=joblib.load(z/'ET.joblib');imp=saved['imputer'];et=saved['model'];gb=xgb.XGBRegressor();gb.load_model(z/'HYBRID_XGB.ubj')
            h=pp[['signal_date','ticker']].copy();xp=imp.transform(matrices['REF42'][1])
            h['ET_RAW']=et.predict(xp);h['XGB_RAW']=gb.predict(xp)
            h['ET']=h.groupby('signal_date').ET_RAW.rank(pct=True);h['XGB']=h.groupby('signal_date').XGB_RAW.rank(pct=True)
            h=canonical_forecasts(h)
            ref=reference[reference.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker']).reset_index(drop=True)
            c=ref.merge(h,on=['signal_date','ticker'],how='left',suffixes=('_ref',''),validate='one_to_one')
            errors={}
            for k in ['ET_RAW','XGB_RAW','ET','XGB']:
                assert np.array_equal(c[k].isna(),c[k+'_ref'].isna())
                errors[k]=float(np.nanmax(abs(c[k]-c[k+'_ref'])))
                assert errors[k]==0,(market,year,k,errors[k])
            parity.append(dict(market=market,year=year,source_saved_forecast_errors=errors))
            if year==2022:
                xx=imp.transform(matrices['REF42'][0]);yy=ht.TARGET.to_numpy(float)
                et2=ExtraTreesRegressor(n_jobs=1,**ET_MODEL_KW).fit(xx,yy)
                gb2=xgb.XGBRegressor(n_jobs=1,**XGB_MODEL_KW).fit(xx,yy)
                assert np.array_equal(et2.predict(xp),et.predict(xp))
                assert np.array_equal(gb2.predict(xp),gb.predict(xp))
                parity[-1]['actual_refitted_models']=2;parity[-1]['refit_error']=0.
            hashes={k:[arr_hash(a),arr_hash(b)] for k,(a,b) in matrices.items()}
            for kind,oldv in [('CORE','H_UNIQUE'),('PATH','H_PATH')]:
                oldaudit=json.loads((PARENT/'models'/market/oldv/str(year)/'audit.json').read_text())
                assert hashes[kind]==oldaudit['hybrid_input_hashes'][:2]
                assert key_hash(ht)==oldaudit['hybrid_train_keys']
            payload={'matrices':matrices,'y':ht.TARGET.to_numpy(float),'predict_keys':pp[['signal_date','ticker']].copy(),'reference':ref,'train_dates':ht.signal_date.to_numpy(),'train_exits':ht.exit_date_63.to_numpy(),'metadata':{'market':market,'year':year,'columns42':list(hc),'columns39':CORE,'path_columns':PATH_COLS,'train_keys':key_hash(ht),'predict_keys':key_hash(pp),'target_hash':arr_hash(ht.TARGET.to_numpy(float)),'matrix_hashes':hashes,'last_label_exit':str(ht.exit_date_63.max()),'last_signal':str(ht.signal_date.max()),'cutoff':str(pd.Timestamp(year,1,1)),'n_train':len(ht),'n_predict':len(pp)}}
            dest=CACHE/f'{market}_{year}.joblib';joblib.dump(payload,dest,compress=3)
            rows.append(dict(**payload['metadata'],cache_sha256=sha256(dest),cache_bytes=dest.stat().st_size))
            atomic_json(OUT/'INPUT_AUDIT.json',rows);atomic_json(OUT/'BASELINE_PARITY.json',parity)
            print('VERIFIED_INPUT',market,year,len(ht),len(pp),'elapsed',round(time.time()-start,1),flush=True)
    atomic_json(ROOT/'checkpoints/01_INPUTS.json',{'status':'complete','annual_batches':len(rows),'canonical_reorder_alias_matrix_checks':len(rows)*2,'baseline_saved_models_read':len(rows)*2,'actual_baseline_models_refit':4,'new_candidate_models':0,'verified_parent_files':4026,'input_audit_sha256':sha256(OUT/'INPUT_AUDIT.json'),'baseline_parity_sha256':sha256(OUT/'BASELINE_PARITY.json')})
if __name__=='__main__':main()
