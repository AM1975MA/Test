#!/usr/bin/env python3
"""OLC60: native upstream 42-feature learning for opportunity and persistence.

Only frozen original OLC14 Heads/Results archives; no market feeds, no layer overlay.
NO portfolio CAGR and no production changes. Labels are used for annual training
only when the entire 63-trading-day group matured before annual cutoff.
"""
from __future__ import annotations
import argparse, hashlib, io, json, os, warnings, zipfile
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
from sklearn.exceptions import ConvergenceWarning

HEADS_HASH = 'a8f2c1770dfdd329676293788180b96a92f79a598d1394a0aaaeb5d91346e458'
RESULT_HASH = '4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1'
PREFIX_H = 'olc14_fitted_ranking_20261101/parents/olc11/inputs/'
PREFIX_R = 'olc14_fitted_ranking_20261101/results/'


def hashfile(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for buf in iter(lambda:f.read(1024*1024),b''): h.update(buf)
    return h.hexdigest()


def read_gz(z,name):
    return pd.read_csv(io.BytesIO(z.read(name)),compression='gzip')


def labels_for(z,m):
    lab=read_gz(z,PREFIX_H+f'{m}_LAYER_LABELS.csv.gz')
    assert not lab.duplicated(['signal_date','ticker']).any()
    lab=lab[['signal_date','ticker','target_rank_21','target_rank_42','exit_date_63','fwd_ret_21','fwd_ret_42']].copy()
    lab['signal_date']=pd.to_datetime(lab['signal_date']).dt.strftime('%Y-%m-%d')
    lab['persist']=np.where(lab[['target_rank_21','target_rank_42']].notna().all(axis=1),((lab['target_rank_21']>=.8)&(lab['target_rank_42']>=.8)).astype(float),np.nan)
    lab['near']=np.where(lab['target_rank_21'].notna(),(lab['target_rank_21']>=.8).astype(float),np.nan)
    return lab


def asof_year(h, m, year):
    obj=joblib.load(io.BytesIO(h.read(PREFIX_H+f'annual/{m}_{year}.joblib')))
    for k in ['X','XP','train_keys','predict_keys','columns']:
        assert k in obj,(m,year,k)
    train=obj['train_keys'][['signal_date','ticker','exit_date_63']].copy()
    pred=obj['predict_keys'][['signal_date','ticker']].copy()
    train['signal_date']=pd.to_datetime(train['signal_date']).dt.strftime('%Y-%m-%d')
    pred['signal_date']=pd.to_datetime(pred['signal_date']).dt.strftime('%Y-%m-%d')
    obj['train_keys']=train;obj['predict_keys']=pred
    assert len(train)==len(obj['X']) and len(pred)==len(obj['XP'])
    assert len(obj['columns'])==42
    assert not train.duplicated(['signal_date','ticker']).any()
    assert not pred.duplicated(['signal_date','ticker']).any()
    assert pd.to_datetime(train['exit_date_63']).max()<pd.Timestamp(year,1,1)
    assert pd.to_datetime(train['signal_date']).max()<pd.Timestamp(year,1,1)
    assert pd.to_datetime(pred['signal_date']).dt.year.eq(year).all()
    return obj


def fit_and_predict(o,y):
    imputer=SimpleImputer(strategy='median',keep_empty_features=True)
    X=imputer.fit_transform(o['X'])
    XP=imputer.transform(o['XP'])
    scaler=StandardScaler()
    X=scaler.fit_transform(X)
    XP=scaler.transform(XP)
    assert np.isfinite(X).all() and np.isfinite(XP).all()
    if np.unique(y).size<2:
        raise ValueError('Training target has only one class')
    model=LogisticRegression(C=.1,solver='lbfgs',max_iter=350,tol=.001)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter('always',ConvergenceWarning)
        model.fit(X,y)
        nonconv=[x for x in w if issubclass(x.category,ConvergenceWarning)]
    p=model.predict_proba(XP)[:,1]
    assert p.min()>=0 and p.max()<=1
    return p, dict(train_positive=float(np.mean(y)),n_iter=int(model.n_iter_[0]),convergence_warnings=len(nonconv))


def top2_weights(scores):
    # OLC14 native topk_weights: expected membership on ties, never alphabetic tie-break.
    p=np.asarray(scores,float)
    assert len(p)>=2 and np.isfinite(p).all()
    threshold=np.sort(p)[-2]
    above=p>threshold
    equal=p==threshold
    w=above.astype(float)
    w[equal]=(2-above.sum())/equal.sum()
    return w/2


def month_selections(df):
    rows=[]
    for (m,date),g0 in df.groupby(['market','signal_date'],sort=True):
        g=g0[g0['ORIGINAL_CURRENT'].notna()].copy()
        g=g.sort_values('ticker').reset_index(drop=True)
        for method,col in [('B0_NATIVE','ORIGINAL_CURRENT'),('B0_FUSION_CONTEXT','ORIGINAL_FUSION'),('NEAR42X','pred_near'),('PERSIST42X','pred_persist')]:
            weights=top2_weights(g[col].to_numpy(float))
            assert abs(weights.sum()-1)<1e-12
            for idx,w in enumerate(weights):
                if w<=0:continue
                a=g.iloc[idx]
                rows.append(dict(market=m,signal_date=date,method=method,ticker=a['ticker'],weight=float(w),score=float(a[col]),
                   target_near=a['near'],target_persist=a['persist'],fwd_ret_21=a['fwd_ret_21'],fwd_ret_42=a['fwd_ret_42'],
                   target_rank_21=a['target_rank_21'],target_rank_42=a['target_rank_42']))
    return pd.DataFrame(rows)


def coverage_and_months(sel):
    months=[]
    for (m,d,method),g in sel.groupby(['market','signal_date','method'],sort=True):
        assert np.isclose(g.weight.sum(),1)
        def wm(col):
            if g[col].isna().any():return np.nan
            return float(np.dot(g.weight.to_numpy(),g[col].to_numpy(float)))
        months.append(dict(market=m,signal_date=d,year=int(str(d)[:4]),method=method,
            near_rate=wm('target_near'),persist_rate=wm('target_persist'),avg_21=wm('fwd_ret_21'),avg_42=wm('fwd_ret_42'),
            negative_21=float(np.dot(g.weight.to_numpy(),(g.fwd_ret_21<0).to_numpy(float))) if g.fwd_ret_21.notna().all() else np.nan))
    mm=pd.DataFrame(months).sort_values(['market','method','signal_date'])
    for (m,method),g in mm.groupby(['market','method']):
        order=g.sort_values('signal_date').index.tolist()
        prev=None
        for idx in order:
            d=mm.loc[idx,'signal_date']
            now=sel[(sel.market==m)&(sel.method==method)&(sel.signal_date==d)].set_index('ticker').weight.to_dict()
            mm.loc[idx,'overlap_prior']=np.nan if prev is None else sum(min(now.get(t,0),prev.get(t,0)) for t in set(now)|set(prev))
            prev=now
    return mm

def summary(sel,mm,pred):
    rows=[]
    for m in ['EU','USA']:
        for period,years in [('MAIN',list(range(2021,2025))),('LATE',[2025]),('FULL_2021_25',list(range(2021,2026)))]:
            d=mm[(mm.market==m)&mm.year.isin(years)].copy()
            for method,g in d.groupby('method'):
                def mn(col):return float(g[col].mean())
                rows.append(dict(market=m,period=period,method=method,nmonths=len(g),
                    nvalid_near=int(g.near_rate.notna().sum()),nvalid_persist=int(g.persist_rate.notna().sum()),
                    top2_near_hit=mn('near_rate'),top2_persist_hit=mn('persist_rate'),avg_fwd21=mn('avg_21'),
                    avg_fwd42=mn('avg_42'),pct_negative_fwd21=mn('negative_21'),selection_overlap=mn('overlap_prior')))
    return pd.DataFrame(rows)


def compute_model_metrics(d):
    out=[]
    for (m,year),g in d.groupby(['market',d['signal_date'].str[:4]]):
        if int(year)>2025 or int(year)<2021:continue
        for target in ['near','persist']:
            y=g[target];p=g[f'pred_{target}'];ok=y.notna()&p.notna()
            if ok.sum()<10 or y[ok].nunique()!=2: continue
            out.append(dict(market=m,year=int(year),target=target,n=int(ok.sum()),prevalence=float(y[ok].mean()),
                 auc=float(roc_auc_score(y[ok].astype(int),p[ok])),brier=float(brier_score_loss(y[ok].astype(int),p[ok])),
                 brier_constant=float(brier_score_loss(y[ok].astype(int),np.full(int(ok.sum()),y[ok].mean()))),
                 logloss=float(log_loss(y[ok].astype(int),p[ok]))))
    return pd.DataFrame(out)


def block_ci(mm,method,metric,m,years=(2021,2022,2023,2024),B=3000,seed=20261107):
    d=mm[(mm.market==m)&mm.year.isin(years)&mm.method.isin(['B0_NATIVE',method])].pivot(index='signal_date',columns='method',values=metric).dropna().sort_index()
    if not len(d):return dict(market=m,method=method,metric=metric,n=0)
    diff=d[method].to_numpy()-d['B0_NATIVE'].to_numpy();N=len(diff);rng=np.random.default_rng(seed)
    vals=[]
    for i in range(B):
        inds=[]
        while len(inds)<N:
            start=int(rng.integers(0,N));inds.extend((start+j)%N for j in range(6))
        vals.append(float(diff[np.asarray(inds[:N])].mean()))
    return dict(market=m,method=method,metric=metric,n=N,delta=float(diff.mean()),lo=float(np.quantile(vals,.025)),hi=float(np.quantile(vals,.975)))


def run(headzip,resultzip,outdir):
    assert hashfile(headzip)==HEADS_HASH,'Head source hash mismatch'
    assert hashfile(resultzip)==RESULT_HASH,'Result source hash mismatch'
    outdir=Path(outdir);outdir.mkdir(exist_ok=True,parents=True)
    fits=[];predictions=[]
    with zipfile.ZipFile(headzip) as zh, zipfile.ZipFile(resultzip) as zr:
        for m in ['EU','USA']:
            lab=labels_for(zh,m)
            scores=read_gz(zr,PREFIX_R+f'{m}_MEAN3_SCORES.csv.gz')
            assert not scores.duplicated(['signal_date','ticker']).any()
            for yr in range(2021,2026):
                obj=asof_year(zh,m,yr)
                tr=obj['train_keys'][['signal_date','ticker','exit_date_63']].copy()
                tr=tr.merge(lab[['signal_date','ticker','near','persist']],on=['signal_date','ticker'],how='left',validate='one_to_one')
                assert len(tr)==len(obj['train_keys'])
                assert tr[['near','persist']].notna().all().all()
                # The entire 63d group matured before the fit; extra guard against corrupted files.
                assert pd.to_datetime(tr.exit_date_63).max() < pd.Timestamp(yr,1,1)
                test=obj['predict_keys'][['signal_date','ticker']].copy()
                test['market']=m
                for target in ['near','persist']:
                    p,qa=fit_and_predict(obj,tr[target].astype(int).to_numpy())
                    assert qa['convergence_warnings']==0,(m,yr,target,qa)
                    test['pred_'+target]=p
                    fits.append(dict(market=m,year=yr,target=target,train_rows=len(tr),test_rows=len(test),
                               last_training_exit=str(pd.to_datetime(tr.exit_date_63).max()),**qa))
                predictions.append(test)
                print('FIT',m,yr,'train',len(tr),'eval',len(test),flush=True)
            # Compare each year's forecasts to fixed original upstream outputs on their native ticker/date support.
        allp=pd.concat(predictions,ignore_index=True)
        assert not allp.duplicated(['market','signal_date','ticker']).any()
        allrows=[]
        for m in ['EU','USA']:
            sub=allp[allp.market==m].copy()
            lab=labels_for(zh,m)
            scores=read_gz(zr,PREFIX_R+f'{m}_MEAN3_SCORES.csv.gz')
            sub=sub.merge(scores[['signal_date','ticker','ORIGINAL_CURRENT','ORIGINAL_FUSION','RETURN']],on=['signal_date','ticker'],how='left',validate='one_to_one')
            sub=sub.merge(lab[['signal_date','ticker','target_rank_21','target_rank_42','fwd_ret_21','fwd_ret_42','near','persist']],on=['signal_date','ticker'],how='left',validate='one_to_one')
            assert sub['ORIGINAL_CURRENT'].notna().all() and sub['pred_near'].notna().all() and sub['pred_persist'].notna().all()
            allrows.append(sub)
        panel=pd.concat(allrows,ignore_index=True)
    sel=month_selections(panel)
    mm=coverage_and_months(sel)
    sm=summary(sel,mm,panel)
    mb=compute_model_metrics(panel)
    boots=[]
    for m in ['EU','USA']:
        for method in ['NEAR42X','PERSIST42X']:
            for metric in ['near_rate','persist_rate','avg_21','avg_42']:
                boots.append(block_ci(mm,method,metric,m))
    bdf=pd.DataFrame(boots)
    allfits=pd.DataFrame(fits)
    panel.to_csv(outdir/'OLC60_PREDICTIONS.csv.gz',index=False,compression='gzip')
    sel.to_csv(outdir/'OLC60_TOP2_SELECTIONS.csv',index=False)
    mm.to_csv(outdir/'OLC60_MONTHLY_METRICS.csv',index=False)
    sm.to_csv(outdir/'OLC60_MAIN_SUMMARY.csv',index=False)
    mb.to_csv(outdir/'OLC60_DISCRIMINATION.csv',index=False)
    bdf.to_csv(outdir/'OLC60_PAIRED_BOOTSTRAP.csv',index=False)
    allfits.to_csv(outdir/'OLC60_FIT_QA.csv',index=False)
    audit=dict(sha256_heads=HEADS_HASH,sha256_results=RESULT_HASH,protocol_sha256=hashfile(Path(__file__).parent/'PROTOCOL_PRE_RESULTS.md'),
       code_sha256=hashfile(__file__),market_rows=panel.groupby('market').size().to_dict(),n_models=len(fits),
       no_training_maturity_violation=True,n_duplicate_keys=int(panel.duplicated(['market','signal_date','ticker']).sum()),
       root_42_features=True,original_main_unchanged=True,execution_engine_not_rerun=True)
    (outdir/'OLC60_QA.json').write_text(json.dumps(audit,indent=2))
    print('SUMMARY\n'+sm.to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    print('BOOT\n'+bdf.to_string(index=False,float_format=lambda x:f'{x:.4f}'))
    print('METRICS\n'+mb.to_string(index=False,float_format=lambda x:f'{x:.4f}'))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--heads',required=True);ap.add_argument('--results',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();run(a.heads,a.results,a.out)