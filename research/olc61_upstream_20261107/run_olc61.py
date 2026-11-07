#!/usr/bin/env python3
"""OLC61: three PREREGISTERED LambdaRank learners on original 42 native features.

Training: expanding-year 2021-25, only GROUP-MATURE 63d source labels.
Forecasts and Top2: X/XP original OLC14, without late score overlays.
Evaluation: frozen monthly 21/42-day STATIC opportunity diagnostics only.
No OLC19 replay, broker fills or live decisions.
"""
from __future__ import annotations
import argparse, hashlib, io, json, sys, time, zipfile
from pathlib import Path
import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import ndcg_score

HEAD_SHA='a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458'
RESULT_SHA='4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1'
PH='olc14_fitted_ranking_20261101/parents/olc11/inputs/'
PR='olc14_fitted_ranking_20261101/results/'
THRESH=np.array([-300.,-100.,0.,100.,300.])
ARMS=['ECON21','STAY2','ECO_STAY']
MODEL_ARGS=dict(objective='lambdarank',n_estimators=180,learning_rate=.04,num_leaves=7,
    min_child_samples=80,reg_lambda=10,max_bin=127,lambdarank_truncation_level=10,
    label_gain=[0,1,3,7,15,31],n_jobs=2,deterministic=True,force_col_wise=True,
    verbosity=-1,random_state=611)
BASES={'B0_NATIVE':'ORIGINAL_CURRENT','B0_FUSION_CONTEXT':'ORIGINAL_FUSION'}

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()

def gzip_df(z,name):return pd.read_csv(io.BytesIO(z.read(name)),compression='gzip')

def labels(z,market):
    df=gzip_df(z,PH+market+'_LAYER_LABELS.csv.gz')
    assert not df.duplicated(['signal_date','ticker']).any()
    df['signal_date']=pd.to_datetime(df.signal_date).dt.strftime('%Y-%m-%d')
    # A historical label is usable only if both horizons are actually observed.
    r1=df.fwd_ret_21.to_numpy(dtype=float)
    r42=df.fwd_ret_42.to_numpy(dtype=float)
    ok=np.isfinite(r1)&np.isfinite(r42)&(r1>-1)&(r42>-1)
    l1=np.full(len(df),np.nan);l2=np.full(len(df),np.nan)
    l1[ok]=np.log1p(r1[ok]);l2[ok]=np.log1p(r42[ok])-l1[ok]
    df['l1']=l1;df['l2']=l2
    med1=df.groupby('signal_date',sort=False)['l1'].transform('median')
    med2=df.groupby('signal_date',sort=False)['l2'].transform('median')
    df['g1_bp']=1e4*(df.l1-med1)
    df['g2_bp']=1e4*(df.l2-med2)
    df['ECON21']=df.g1_bp
    df['STAY2']=np.minimum(df.g1_bp,df.g2_bp)
    df['ECO_STAY']=.70*df.g1_bp+.30*df.STAY2
    for arm in ARMS:
        df['rel_'+arm]=np.where(df[arm].notna(),np.digitize(df[arm].to_numpy(),THRESH,right=True),np.nan)
    df['near']=np.where(df.target_rank_21.notna(),(df.target_rank_21>=.8).astype(float),np.nan)
    df['persist']=np.where(df[['target_rank_21','target_rank_42']].notna().all(axis=1),
        ((df.target_rank_21>=.8)&(df.target_rank_42>=.8)).astype(float),np.nan)
    df['disjoint_positive']=np.where(df[['g1_bp','g2_bp']].notna().all(axis=1),
        ((df.g1_bp>0)&(df.g2_bp>0)).astype(float),np.nan)
    return df

def annual(z,market,year,sourcecols):
    o=joblib.load(io.BytesIO(z.read(PH+f'annual/{market}_{year}.joblib')))
    assert len(o['columns'])==42 and o['columns']==sourcecols
    assert len(o['train_keys'])==len(o['X']) and len(o['predict_keys'])==len(o['XP'])
    tr=o['train_keys'].copy();te=o['predict_keys'].copy()
    for a in [tr,te]:a['signal_date']=pd.to_datetime(a.signal_date).dt.strftime('%Y-%m-%d')
    assert not tr.duplicated(['signal_date','ticker']).any()
    assert not te.duplicated(['signal_date','ticker']).any()
    assert pd.to_datetime(tr.exit_date_63).max()<pd.Timestamp(year,1,1)
    assert pd.to_datetime(te.signal_date).dt.year.eq(year).all()
    assert o['X'].shape[1]==42 and o['XP'].shape[1]==42
    return o,tr,te

def weights2(x):
    v=np.asarray(x,float)
    assert len(v)>=2 and np.isfinite(v).all()
    pivot=np.partition(v,-2)[-2];big=v>pivot;ties=v==pivot
    w=big.astype(float);w[ties]=(2-big.sum())/ties.sum()
    assert np.all(w>=0) and np.isclose(w.sum(),2)
    return w/2

def fitted_group_train(o,tr,lab,arm):
    q=tr.merge(lab[['signal_date','ticker','exit_date_63','rel_'+arm]],on=['signal_date','ticker'],how='left',validate='one_to_one',suffixes=('_parent','_true'))
    assert len(q)==len(tr)
    assert q['rel_'+arm].notna().all(), 'training has unlabeled row: '+arm
    # Explicit grouped ordering for LightGBM queries: no group crosses query boundary.
    keys=tr[['signal_date','ticker']].copy()
    order=keys.sort_values(['signal_date','ticker'],kind='mergesort').index.to_numpy()
    query=keys.iloc[order]['signal_date'].to_numpy()
    grp=pd.Series(query).groupby(query,sort=False).size().to_numpy(dtype=int)
    assert len(np.unique(query))==len(grp) and grp.sum()==len(order)
    X=np.array(o['X'][order],dtype=np.float32,copy=True)
    X[~np.isfinite(X)]=np.nan
    y=q['rel_'+arm].to_numpy(dtype=int)[order]
    assert y.min()>=0 and y.max()<=5
    return X,y,grp,dict(nmonths=len(grp),ntraining=len(order),levels={str(i):int((y==i).sum()) for i in range(6)})

def month_selections(panel):
    out=[]
    metrics=['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive']
    score_cols={**BASES,**{arm:'pred_'+arm for arm in ARMS}}
    for (market,dt),g in panel.groupby(['market','signal_date'],sort=True):
        g=g.sort_values('ticker').reset_index(drop=True)
        for method,col in score_cols.items():
            ww=weights2(g[col].to_numpy(float))
            pos=np.flatnonzero(ww>0)
            for i in pos:
                a=g.iloc[i]
                out.append(dict(market=market,signal_date=dt,method=method,ticker=a.ticker,
                   weight=float(ww[i]),score=float(a[col]),**{c:float(a[c]) for c in metrics},
                   target_rank_21=float(a.target_rank_21),target_rank_42=float(a.target_rank_42)))
    return pd.DataFrame(out)

def monthly(sel):
    out=[]
    for (market,dt,method),g in sel.groupby(['market','signal_date','method'],sort=True):
        assert np.isclose(g.weight.sum(),1.)
        def wmean(k):
            if g[k].isna().any():return float('nan')
            return float(np.dot(g.weight.to_numpy(float),g[k].to_numpy(float)))
        out.append(dict(market=market,signal_date=dt,year=int(dt[:4]),method=method,
            n_selected=len(g),**{k:wmean(k) for k in ['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive']},
            negative21=float(np.dot(g.weight,(g.fwd_ret_21<0))) if g.fwd_ret_21.notna().all() else np.nan))
    return pd.DataFrame(out).sort_values(['market','signal_date','method']).reset_index(drop=True)

def summarize(mm):
    rows=[]
    for (m,method),g in mm.groupby(['market','method']):
        for period,years in [('MAIN',[2021,2022,2023,2024]),('LATE',[2025]),('FULL',[2021,2022,2023,2024,2025])]:
            s=g[g.year.isin(years)]
            assert len(s)==len(years)*12,(m,method,period,len(s))
            rows.append(dict(market=m,method=method,period=period,months=len(s),
              **{k:float(s[k].mean()) for k in ['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive','negative21']}))
    return pd.DataFrame(rows)

def bootstrap(mm,benchmark='B0_FUSION_CONTEXT',B=4000,seed=611):
    rows=[]
    rng=np.random.default_rng(seed)
    for m in ['EU','USA']:
        main=mm[(mm.market==m)&mm.year.between(2021,2024)]
        for metric in ['fwd_ret_21','fwd_ret_42','persist']:
            wide=main.pivot(index='signal_date',columns='method',values=metric).sort_index()
            assert len(wide)==48 and wide.notna().all().all()
            for arm in ARMS:
                delta=(wide[arm]-wide[benchmark]).to_numpy()
                idx=np.empty((B,len(delta)),dtype=np.int32)
                for i in range(B):
                    starts=rng.integers(0,len(delta),size=(len(delta)+5)//6)
                    idx[i]=np.concatenate([(s+np.arange(6))%len(delta) for s in starts])[:len(delta)]
                means=delta[idx].mean(axis=1)
                rows.append(dict(market=m,arm=arm,metric=metric,n=len(delta),delta_mean=float(delta.mean()),
                     ci_lower=float(np.quantile(means,.025)),ci_upper=float(np.quantile(means,.975)),positive_months=int((delta>0).sum())))
    return pd.DataFrame(rows)

def audit_olc60_baseline(sel,ref_csv):
    parent=pd.read_csv(ref_csv)
    keep=parent[parent.method.isin(['B0_NATIVE','B0_FUSION_CONTEXT'])][['market','signal_date','method','ticker','weight','score']].copy()
    ours=sel[sel.method.isin(['B0_NATIVE','B0_FUSION_CONTEXT'])][['market','signal_date','method','ticker','weight','score']].copy()
    keys=['market','signal_date','method','ticker']
    comb=keep.merge(ours,on=keys,validate='one_to_one',how='outer',indicator=True,suffixes=('_old','_new'))
    assert (comb._merge=='both').all(),comb._merge.value_counts().to_dict()
    err_w=float((comb.weight_old-comb.weight_new).abs().max())
    assert err_w<1e-12, f'OLC60 weight mismatch max_error={err_w}; examples='+str(comb[(comb.weight_old-comb.weight_new).abs()>1e-12].head(3).to_dict('records'))
    err_s=float((comb.score_old-comb.score_new).abs().max())
    assert err_s<1e-12, f'OLC60 score mismatch max_error={err_s}'
    return dict(matched_rows=len(comb),max_abs_score_diff=float(np.max(np.abs(comb.score_old-comb.score_new))),
             max_abs_weight_diff=float(np.max(np.abs(comb.weight_old-comb.weight_new))))

def main(heads,results,olc60sel,out):
    assert sha(heads)==HEAD_SHA and sha(results)==RESULT_SHA,'immutable input digest mismatch'
    d=Path(out);d.mkdir(parents=True,exist_ok=True);(d/'models').mkdir(exist_ok=True)
    fits=[];panels=[];firstschema=None
    with zipfile.ZipFile(heads) as zh,zipfile.ZipFile(results) as zr:
        for m in ['EU','USA']:
            lab=labels(zh,m)
            source_schema=None;forecasts=[]
            for yr in range(2021,2026):
                # Column contract remains identical for each year within market.
                obj=joblib.load(io.BytesIO(zh.read(PH+f'annual/{m}_{yr}.joblib')))
                if source_schema is None:source_schema=obj['columns']
                o,tr,te=annual(zh,m,yr,source_schema)
                XP=np.array(o['XP'],dtype=np.float32,copy=True);XP[~np.isfinite(XP)]=np.nan
                sub=te[['signal_date','ticker']].copy();sub['market']=m
                for arm in ARMS:
                    X,y,groups,stats=fitted_group_train(o,tr,lab,arm)
                    model_path=d/'models'/f'{m}_{yr}_{arm}.txt'
                    if model_path.exists():
                        # Reuse exactly the immutable model already fitted during this run after a QA-only failure.
                        ranker=lgb.Booster(model_file=str(model_path))
                        scores=ranker.predict(XP,num_threads=2)
                        rp=lgb.Booster(model_file=str(model_path)).predict(XP,num_threads=2)
                        nround=ranker.current_iteration()
                    else:
                        ranker=lgb.LGBMRanker(**MODEL_ARGS)
                        ranker.fit(X,y,group=groups)
                        scores=ranker.predict(XP,num_threads=2)
                        ranker.booster_.save_model(str(model_path))
                        rp=lgb.Booster(model_file=str(model_path)).predict(XP,num_threads=2)
                        nround=ranker.booster_.current_iteration()
                    assert np.isfinite(scores).all()
                    maxerr=float(np.max(np.abs(scores-rp)))
                    assert maxerr<1e-10
                    sub['pred_'+arm]=scores
                    fits.append(dict(market=m,year=yr,arm=arm,last_matured_exit=str(pd.to_datetime(tr.exit_date_63).max().date()),
                        feature_count=len(source_schema),prediction_rows=len(sub),model_parity_error=maxerr,
                        num_boosted_rounds=nround,**stats))
                forecasts.append(sub)
                print(f'fit {m} {yr}, n_train={len(tr)}, n_predict={len(te)}',flush=True)
            forecasts=pd.concat(forecasts,ignore_index=True)
            assert not forecasts.duplicated(['market','signal_date','ticker']).any()
            sc=gzip_df(zr,PR+m+'_MEAN3_SCORES.csv.gz')
            expect_cols=['signal_date','ticker',*BASES.values()]
            forecasts=forecasts.merge(sc[expect_cols],on=['signal_date','ticker'],how='left',validate='one_to_one')
            lab_cols=['signal_date','ticker','fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive','target_rank_21','target_rank_42']
            forecasts=forecasts.merge(lab[lab_cols],on=['signal_date','ticker'],how='left',validate='one_to_one')
            assert forecasts[list(BASES.values())].notna().all().all()
            assert forecasts[['pred_'+a for a in ARMS]].notna().all().all()
            panels.append(forecasts)
    panel=pd.concat(panels,ignore_index=True)
    assert not panel.duplicated(['market','signal_date','ticker']).any()
    sel=month_selections(panel)
    qa=audit_olc60_baseline(sel,olc60sel)
    mm=monthly(sel)
    sm=summarize(mm)
    boots=bootstrap(mm)
    fy=mm[(mm.year>=2021)&(mm.year<=2025)].groupby(['market','method','year'])[['fwd_ret_21','fwd_ret_42','near','persist','disjoint_positive']].mean().reset_index()
    # Negative month risk, wider uncertainty and exhaustive all-variant presentation.
    pd.DataFrame(fits).to_csv(d/'OLC61_FIT_QA.csv',index=False)
    panel.to_csv(d/'OLC61_PREDICTIONS.csv.gz',index=False,compression='gzip')
    sel.to_csv(d/'OLC61_TOP2_SELECTIONS.csv',index=False)
    mm.to_csv(d/'OLC61_MONTHLY_METRICS.csv',index=False)
    sm.to_csv(d/'OLC61_SUMMARY.csv',index=False)
    boots.to_csv(d/'OLC61_BLOCK_BOOTSTRAP.csv',index=False)
    fy.to_csv(d/'OLC61_ANNUAL.csv',index=False)
    report=dict(source_hash_heads=HEAD_SHA,source_hash_results=RESULT_SHA,
        protocol_sha=sha(Path(__file__).parent/'PROTOCOL_PRE_RESULTS.md'),code_sha=sha(__file__),
        number_models=len(fits),forecast_rows=len(panel),
        per_market=panel.groupby('market').size().to_dict(),
        monthly_events=len(mm),same_support=True,baseline_parity=qa,
        all_models_reload_predict_equal=True,all_training_groups_mature=True,
        trade_engine_rerun=False,main_modified=False)
    (d/'OLC61_QA.json').write_text(json.dumps(report,indent=2,ensure_ascii=False))
    print('MAIN SUMMARY:',flush=True)
    print(sm[sm.period=='MAIN'].to_string(index=False,float_format=lambda a:f'{a:.5f}'),flush=True)
    print('BOOTSTRAP',flush=True)
    print(boots.to_string(index=False,float_format=lambda a:f'{a:.5f}'),flush=True)
    print('QA',json.dumps(report,indent=2),flush=True)
    return 0

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--heads',required=True);ap.add_argument('--results',required=True)
    ap.add_argument('--olc60-selections',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args()
    sys.exit(main(args.heads,args.results,args.olc60_selections,args.out))