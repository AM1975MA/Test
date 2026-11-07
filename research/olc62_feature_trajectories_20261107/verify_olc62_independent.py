#!/usr/bin/env python3
"""Independent OLC62 tie-out, including native rank-lag reconstruction on sampled fits.

Does not call the experiment's lag builder, selector, monthly reducer, or trainer.
"""
from pathlib import Path
import io,zipfile,hashlib,json,sys
import joblib,lightgbm as lgb,numpy as np,pandas as pd

SRC='olc14_fitted_ranking_20261101/parents/olc11/inputs/annual/'
ARM={'B0_NATIVE':'ORIGINAL_CURRENT','B0_FUSION_CONTEXT':'ORIGINAL_FUSION',
     'OLC61_ECON21':'pred_ECON21','OLC62_TRAJECTORY42':'pred_TRAJECTORY42'}
VALS=['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive']

def panel_tieout(base,dir):
    original=pd.read_csv(base,compression='gzip')
    output=pd.read_csv(dir/'OLC62_PREDICTIONS.csv.gz',compression='gzip')
    keys=['market','signal_date','ticker']
    assert len(original)==len(output)==18099
    assert not output.duplicated(keys).any()
    old=original.merge(output,on=keys,how='outer',indicator=True,validate='one_to_one',suffixes=('_old','_new'))
    assert len(old)==18099 and (old._merge=='both').all()
    errors={}
    for col in original.columns:
        if col in keys:continue
        if col not in output:raise AssertionError('Missing original value '+col)
        lhs=old[col+'_old'].to_numpy(dtype=float);rhs=old[col+'_new'].to_numpy(dtype=float)
        assert np.array_equal(np.isnan(lhs),np.isnan(rhs))
        err=float(np.nanmax(np.abs(lhs-rhs)))
        assert err<=1e-12,(col,err)
        errors[col]=err
    assert np.isfinite(output.pred_TRAJECTORY42).all()
    return output,errors

def independent_tieout(panel,selected,monthly):
    keys=['market','signal_date','method','ticker']
    assert not selected.duplicated(keys).any()
    recs=[];met=[]
    for (market,date),g0 in panel.groupby(['market','signal_date']):
        g=g0.sort_values('ticker').reset_index(drop=True)
        for method,scorecol in ARM.items():
            s=g[scorecol].to_numpy(dtype=float)
            # Independently select top two with the legacy fractional ties rule.
            cutoff=np.sort(s)[-2]
            more=np.flatnonzero(s>cutoff)
            equal=np.flatnonzero(s==cutoff)
            assert len(more)<=2 and len(equal)>=1
            weights=np.zeros(len(s))
            weights[more]=.5
            weights[equal]=(2-len(more))/(2*len(equal))
            assert abs(weights.sum()-1)<1e-12
            for i in np.flatnonzero(weights>0):
                recs.append(dict(market=market,signal_date=date,method=method,ticker=g.loc[i,'ticker'],weight=float(weights[i])))
            item=dict(market=market,signal_date=date,method=method)
            for v in VALS:
                vals=g[v].to_numpy(dtype=float)
                item[v]=np.nan if np.isnan(vals[weights>0]).any() else float(np.sum(vals[weights>0]*weights[weights>0]))
            met.append(item)
    rec=pd.DataFrame(recs);calc=pd.DataFrame(met)
    sel=selected.merge(rec,on=keys,how='outer',validate='one_to_one',indicator=True,suffixes=('_record','_check'))
    assert len(sel)==len(selected)==len(rec) and (sel._merge=='both').all()
    selerr=float(np.max(np.abs(sel.weight_record-sel.weight_check)))
    assert selerr<1e-12
    mm=monthly.merge(calc,on=['market','signal_date','method'],how='outer',validate='one_to_one',indicator=True,suffixes=('_record','_check'))
    assert len(mm)==4*2*60 and (mm._merge=='both').all()
    errors={}
    for v in VALS:
        a=mm[v+'_record'].to_numpy(dtype=float);b=mm[v+'_check'].to_numpy(dtype=float)
        assert np.array_equal(np.isnan(a),np.isnan(b))
        err=float(np.nanmax(np.abs(a-b)))
        assert err<1e-10,(v,err)
        errors[v]=err
    return {'selection_weight_max_err':selerr,'monthly_max_err':errors,'monthly_events':len(mm),'selection_rows':len(sel)}

def independent_model_replay(heads,pred,dir,market,year):
    with zipfile.ZipFile(heads) as z:
        cur=joblib.load(io.BytesIO(z.read(SRC+f'{market}_{year}.joblib')))
        old=joblib.load(io.BytesIO(z.read(SRC+f'{market}_{year-1}.joblib')))
    cols=cur['columns'];assert cols==old['columns'] and len(cols)==42
    te=cur['predict_keys'][['signal_date','ticker']].copy()
    te['signal_date']=pd.to_datetime(te.signal_date).dt.strftime('%Y-%m-%d')
    te['month']=te.signal_date.str[:7]
    store=[]
    for keys,a in [(cur['train_keys'],cur['X']),(old['predict_keys'],old['XP']),(cur['predict_keys'],cur['XP'])]:
        k=keys[['signal_date','ticker']].copy().reset_index(drop=True)
        k['signal_date']=pd.to_datetime(k.signal_date).dt.strftime('%Y-%m-%d')
        z=pd.concat([k,pd.DataFrame(a,columns=cols)],axis=1)
        z['month']=z.signal_date.str[:7]
        store.append(z)
    hist=pd.concat(store,ignore_index=True).drop_duplicates(['ticker','month'])
    deltas=[]
    for lag in (1,3):
        lookup=te[['ticker','month']].copy()
        lookup['month']=(pd.PeriodIndex(lookup.month,freq='M')-lag).astype(str)
        hist0=hist[['ticker','month',*cols]]
        mx=lookup.merge(hist0,on=['ticker','month'],how='left',sort=False,validate='many_to_one')
        assert len(mx)==len(te)
        current=np.asarray(cur['XP'],dtype=np.float32)
        older=mx[cols].to_numpy(dtype=np.float32)
        deltas.append(current-older)
        assert all(pd.Period(m,freq='M')<pd.Period(n,freq='M') for m,n in zip(lookup.month,te.month))
    feature=np.column_stack([cur['XP'],*deltas]).astype(np.float32)
    feature[~np.isfinite(feature)]=np.nan
    booster=lgb.Booster(model_file=str(dir/'models'/f'{market}_{year}_TRAJECTORY42.txt'))
    scores=booster.predict(feature,num_threads=2)
    check=te.assign(market=market,pred_rebuilt=scores).merge(
        pred[['market','signal_date','ticker','pred_TRAJECTORY42']],on=['market','signal_date','ticker'],
        how='left',validate='one_to_one')
    assert check.pred_TRAJECTORY42.notna().all()
    err=float((check.pred_rebuilt-check.pred_TRAJECTORY42).abs().max())
    assert err<1e-9,(market,year,err)
    return {'market':market,'year':year,'rows':len(check),'max_abs_prediction_error':err}

def main():
    root=Path(__file__).resolve().parent
    d=root/'results'
    parent=root.parent/'OLC61_Upstream_20261107'/'results'/'OLC61_PREDICTIONS.csv.gz'
    heads=root.parent/'etf_source'/'OLC14_Heads_Checkpoint_20261101.zip'
    output,fields=panel_tieout(parent,d)
    stat=independent_tieout(output,pd.read_csv(d/'OLC62_TOP2_SELECTIONS.csv'),pd.read_csv(d/'OLC62_MONTHLY_METRICS.csv'))
    fits=pd.read_csv(d/'OLC62_FIT_QA.csv')
    assert len(fits)==10 and all(pd.to_datetime(fits.last_training_exit_date_63)<pd.to_datetime(fits.fit_cutoff))
    assert np.isclose(fits.max_abs_repeat_feature_conflict,0).all()
    samples=[]
    for m,y in [('EU',2021),('EU',2025),('USA',2021),('USA',2025)]:
        samples.append(independent_model_replay(heads,output,d,m,y))
    check={'verification':'PASS','total_forecasts':len(output),'parent_panel_max_errors':fields,
           'selected_months':stat,'model_and_lag_replay_samples':samples,
           'historical_overlap_integrity':True,'training_maturity':True,'no_new_oos':True}
    (d/'OLC62_INDEPENDENT_QA.json').write_text(json.dumps(check,indent=2,ensure_ascii=False))
    print(json.dumps(check,indent=2))

if __name__=='__main__':main()