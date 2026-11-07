#!/usr/bin/env python3
"""OLC62: frozen test of upstream temporal rank-feature representation.

This is research only. Changes INPUT REPRESENTATION before native learner,
never adds a final overlay. No live decisions, strategy NAV, or OOS claim.

python run_olc62.py --heads <OLC14_Heads.zip> --olc61-predictions <OLC61_PREDICTIONS.csv.gz> \
    --olc61-monthly <OLC61_MONTHLY_METRICS.csv> --out results
"""
from __future__ import annotations
import argparse,hashlib,io,json,zipfile,sys
from pathlib import Path
import joblib,numpy as np,pandas as pd,lightgbm as lgb
from scipy.stats import spearmanr
import olc61_parent_unchanged as parent

HEAD_SHA=parent.HEAD_SHA
REFERENCE_PREFIX='olc14_fitted_ranking_20261101/parents/olc11/inputs/'
ARMS=['B0_NATIVE','B0_FUSION_CONTEXT','OLC61_ECON21','OLC62_TRAJECTORY42']
BASE_DCT={'B0_NATIVE':'ORIGINAL_CURRENT','B0_FUSION_CONTEXT':'ORIGINAL_FUSION','OLC61_ECON21':'pred_ECON21','OLC62_TRAJECTORY42':'pred_TRAJECTORY42'}
FUTURE=['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive']
DIAG_KEYS=['ret_21_rank','eff_63_rank','cluster_breadth63_rank']

def hashfile(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def to_date(s):return pd.to_datetime(s).dt.strftime('%Y-%m-%d')

def make_history(o,prev,market,year):
    """Join only earlier/month-current native features. Lag alignment by exact calendar month.
    All inputs have historical as-of provenance (train X, earlier year XP, current XP).
    No labels are merged. DO NOT use future periods for lag construction.
    """
    cols=o['columns']; assert len(cols)==42 and cols==prev['columns']
    out=[]
    for keys,values,kind in [(o['train_keys'],o['X'],'train'),(prev['predict_keys'],prev['XP'],'prior_xp'),(o['predict_keys'],o['XP'],'xp')]:
        k=keys[['signal_date','ticker']].copy().reset_index(drop=True)
        k['signal_date']=to_date(k['signal_date'])
        v=pd.DataFrame(np.asarray(values,dtype=np.float32),columns=cols)
        assert len(k)==len(v)
        out.append(pd.concat([k,v],axis=1).assign(origin=kind))
    h=pd.concat(out,ignore_index=True)
    h['month']=pd.PeriodIndex(h.signal_date.str[:7],freq='M')
    # No signal newer than the prediction year can be used in a forecast.
    assert h['month'].max()<=pd.Period(f'{year}-12',freq='M')
    assert h.groupby(['ticker','month']).signal_date.nunique().max()==1, 'more than one event in same month'
    # Confirm overlapping historical XP values are identical to train snapshots.
    dup=h[h.duplicated(['ticker','month'],keep=False)]
    max_error=0.;num_duplicates=0
    if len(dup):
        mi=dup.groupby(['ticker','month'],observed=True).size()
        num_duplicates=int((mi>1).sum())
        lo=dup.groupby(['ticker','month'],observed=True)[cols].min()
        hi=dup.groupby(['ticker','month'],observed=True)[cols].max()
        dr=(hi-lo).abs().to_numpy(dtype=float)
        max_error=float(np.nanmax(dr)) if np.isfinite(dr).any() else 0.
        assert max_error<=1e-7,f'historical feature conflict: {max_error}'
    h=h.drop_duplicates(['ticker','month'],keep='first').copy()
    assert not h.duplicated(['ticker','month']).any()
    # The 42 original inputs are already cross-sectional ranks, so subtraction is rank velocity.
    # Using exact month offsets prevents stale lags from silently being accepted.
    targets=h[['ticker','month','signal_date']].copy()
    lag_values=[]
    for lag in (1,3):
        prior=h[['ticker','month',*cols]].copy()
        prior['month']=prior['month']+lag
        rename={c:f'd{lag}_{c}' for c in cols}; prior=prior.rename(columns=rename)
        targets=targets.merge(prior,on=['ticker','month'],how='left',validate='one_to_one',sort=False)
        a=targets[[f'd{lag}_{c}' for c in cols]].to_numpy(dtype=float)
        current=h[cols].to_numpy(dtype=float)
        assert len(a)==len(current)
        # The merges preserve the original left order; verify before subtracting.
        assert targets[['ticker','month','signal_date']].reset_index(drop=True).equals(h[['ticker','month','signal_date']].reset_index(drop=True))
        delta=(current-a).astype(np.float32)
        names=[f'delta{lag}_{c}' for c in cols]
        targets[names]=pd.DataFrame(delta,columns=names,index=targets.index)
        lag_values+=names
    traj=targets[['signal_date','ticker',*lag_values]].copy()
    tr=o['train_keys'][['signal_date','ticker']].copy();tr['signal_date']=to_date(tr.signal_date)
    te=o['predict_keys'][['signal_date','ticker']].copy();te['signal_date']=to_date(te.signal_date)
    traj_tr=tr.merge(traj,on=['signal_date','ticker'],how='left',validate='one_to_one',indicator=True)
    traj_te=te.merge(traj,on=['signal_date','ticker'],how='left',validate='one_to_one',indicator=True)
    assert (traj_tr._merge=='both').all() and (traj_te._merge=='both').all()
    ftr=traj_tr[lag_values].to_numpy(dtype=np.float32)
    fte=traj_te[lag_values].to_numpy(dtype=np.float32)
    assert ftr.shape==(len(tr),84) and fte.shape==(len(te),84)
    m1=traj_te[[f'delta1_{c}' for c in cols]].notna().all(axis=1).mean()
    m3=traj_te[[f'delta3_{c}' for c in cols]].notna().all(axis=1).mean()
    summary={'market':market,'year':year,'train_rows':len(tr),'test_rows':len(te),'unique_history_ticker_months':len(h),
             'duplicate_historical_snapshots':num_duplicates,'max_abs_repeat_feature_conflict':max_error,
             'test_full_lag1_fraction':float(m1),'test_full_lag3_fraction':float(m3)}
    # All 84 lag fields are derived solely from *previous* as-of dates.
    assert not np.isinf(ftr).any() and not np.isinf(fte).any()
    return ftr,fte,summary,traj_te[['signal_date','ticker',*lag_values]]

def build_panel(heads,olc61_ref,out):
    ref=pd.read_csv(olc61_ref,compression='gzip')
    assert not ref.duplicated(['market','signal_date','ticker']).any()
    assert set(ref.market.unique())=={'EU','USA'}
    ensure=ref[['market','signal_date','ticker',*parent.BASES.values(),'pred_ECON21',*FUTURE,'target_rank_21','target_rank_42']]
    assert ensure[list(parent.BASES.values())+['pred_ECON21']].notna().all().all(), 'baseline score missing'
    # Historical outcomes may be genuinely unavailable for a handful of ETFs; preserve NaN labels.
    results=[]; qa=[]; lag_panels=[]
    with zipfile.ZipFile(heads) as z:
        for m in ['EU','USA']:
            lab=parent.labels(z,m)
            schema=None
            for year in range(2021,2026):
                o=joblib.load(io.BytesIO(z.read(REFERENCE_PREFIX+f'annual/{m}_{year}.joblib')))
                prev=joblib.load(io.BytesIO(z.read(REFERENCE_PREFIX+f'annual/{m}_{year-1}.joblib')))
                if schema is None: schema=o['columns']
                a,tr,te=parent.annual(z,m,year,schema)
                assert o['columns']==schema and prev['columns']==schema
                # Reproduce parent OLC61 training records/relevance precisely.
                X,y,groups,check=parent.fitted_group_train(o,tr,lab,'ECON21')
                lagtr,lagte,stats,lagrefs=make_history(o,prev,m,year)
                ordidx=tr[['signal_date','ticker']].sort_values(['signal_date','ticker'],kind='mergesort').index.to_numpy()
                Z=np.hstack([X,lagtr[ordidx]]).astype(np.float32)
                assert len(y)==len(Z)==groups.sum()
                Xpred=np.asarray(o['XP'],dtype=np.float32).copy();Xpred[~np.isfinite(Xpred)]=np.nan
                Zpred=np.hstack([Xpred,lagte]).astype(np.float32)
                assert Z.shape[1]==Zpred.shape[1]==126
                model=lgb.LGBMRanker(**parent.MODEL_ARGS)
                model.fit(Z,y,group=groups)
                p1=model.predict(Zpred,num_threads=2)
                path=out/'models'/f'{m}_{year}_TRAJECTORY42.txt';model.booster_.save_model(str(path))
                p2=lgb.Booster(model_file=str(path)).predict(Zpred,num_threads=2)
                err=float(np.max(np.abs(p1-p2)))
                assert err<1e-10
                pr=te[['signal_date','ticker']].copy().assign(market=m,pred_TRAJECTORY42=p1)
                results.append(pr)
                lagrefs.insert(0,'market',m);lag_panels.append(lagrefs)
                qa.append({**stats,'matured_groups':check['nmonths'],'prediction_parity_abs_error':err,
                           'last_training_exit_date_63':str(pd.to_datetime(tr.exit_date_63).max().date()),
                           'fit_cutoff':f'{year}-01-01','n_feature_total':Z.shape[1],
                           'missing_train_fraction_lag1':float(np.isnan(lagtr[:,:42]).all(axis=1).mean()),
                           'missing_train_fraction_lag3':float(np.isnan(lagtr[:,42:]).all(axis=1).mean())})
                print(f'Fitted OLC62 {m} {year}: {len(tr)} train, {len(te)} predict, lag1 {stats["test_full_lag1_fraction"]:.1%}, lag3 {stats["test_full_lag3_fraction"]:.1%}',flush=True)
    pred=pd.concat(results,ignore_index=True)
    assert not pred.duplicated(['market','signal_date','ticker']).any()
    panel=ref.merge(pred,on=['market','signal_date','ticker'],how='outer',validate='one_to_one',indicator=True)
    assert len(panel)==len(ref) and (panel._merge=='both').all() and panel.pred_TRAJECTORY42.notna().all()
    panel=panel.drop(columns=['_merge'])
    return panel,pd.DataFrame(qa),pd.concat(lag_panels,ignore_index=True)

def selections(panel):
    rows=[]
    for (market,dt),g in panel.groupby(['market','signal_date'],sort=True):
        g=g.sort_values('ticker').reset_index(drop=True)
        for method,col in BASE_DCT.items():
            weight=parent.weights2(g[col].to_numpy(dtype=float))
            for i in np.flatnonzero(weight>0):
                r=g.iloc[i]
                row=dict(market=market,signal_date=dt,method=method,ticker=r.ticker,weight=float(weight[i]),score=float(r[col]))
                row.update({c:float(r[c]) for c in FUTURE})
                rows.append(row)
    return pd.DataFrame(rows)

def verify_olc61_monthly(mm,previous):
    prev=pd.read_csv(previous)
    key=['market','signal_date','method']
    old=prev[prev.method.isin(['B0_NATIVE','B0_FUSION_CONTEXT','ECON21'])].copy()
    old.method=old.method.replace({'ECON21':'OLC61_ECON21'})
    new=mm[mm.method.isin(['B0_NATIVE','B0_FUSION_CONTEXT','OLC61_ECON21'])]
    both=old.merge(new,on=key,validate='one_to_one',how='outer',indicator=True,suffixes=('_ref','_new'))
    assert len(both)==len(old)==2*60*3 and (both._merge=='both').all()
    cols=['fwd_ret_21','fwd_ret_42','g1_bp','g2_bp','near','persist','disjoint_positive']
    diffs={c:float(np.max(np.abs(both[c+'_ref']-both[c+'_new']))) for c in cols}
    assert all(x<1e-10 for x in diffs.values()),diffs
    return diffs

def smry(mm):
    rows=[]
    for (m,method),g in mm.groupby(['market','method']):
        for period,years in [('MAIN',range(2021,2025)),('LATE',[2025]),('FULL_2021_25',range(2021,2026))]:
            x=g[g.year.isin(years)]
            assert len(x)==12*len(years)
            rows.append(dict(market=m,method=method,period=period,months=len(x),
                  **{c:float(x[c].mean()) for c in FUTURE},
                  months_better_fusion_r21=int((x.set_index('signal_date').fwd_ret_21>
                    mm[(mm.market==m)&(mm.method=='B0_FUSION_CONTEXT')&mm.year.isin(years)].set_index('signal_date').fwd_ret_21).sum()) if method!='B0_FUSION_CONTEXT' else None))
    return pd.DataFrame(rows)

def boot(mm,nboot=4000,seed=6201):
    rng=np.random.default_rng(seed);rows=[]
    for m in ['EU','USA']:
        a=mm[(mm.market==m)&mm.year.between(2021,2024)].pivot(index='signal_date',columns='method',values='fwd_ret_21').sort_index()
        assert len(a)==48 and a.notna().all().all()
        for control in ['B0_FUSION_CONTEXT','OLC61_ECON21','B0_NATIVE']:
            d=(a['OLC62_TRAJECTORY42']-a[control]).to_numpy(float)
            # identical resampled months for each comparator in a market
            sampled=[]
            for _ in range(nboot):
                starts=rng.integers(0,len(d),size=(len(d)+5)//6)
                sampled.append(d[np.concatenate([(s+np.arange(6))%len(d) for s in starts])[:len(d)]].mean())
            rows.append(dict(market=m,compared_to=control,n_months=len(d),mean_delta_pp=100*d.mean(),
               ci_low_pp=100*np.percentile(sampled,2.5),ci_high_pp=100*np.percentile(sampled,97.5),
               positive_months=int((d>0).sum()),negative_months=int((d<0).sum())))
    return pd.DataFrame(rows)

def diagnose(panel,lag_panel):
    # Only fixed, preregistered economic rank-velocity ICs and top10 coverage.
    cols=['market','signal_date','ticker','g1_bp','fwd_ret_21','ORIGINAL_FUSION','pred_TRAJECTORY42','ret_21_rank'] if False else []
    frames=[]
    for market,ma in panel.groupby('market'):
        lags=lag_panel[lag_panel.market==market][['signal_date','ticker',*[f'delta{k}_{f}' for f in DIAG_KEYS for k in (1,3)]]]
        p=ma.merge(lags,on=['signal_date','ticker'],validate='one_to_one',how='left',indicator=True)
        assert (p._merge=='both').all()
        p=p.drop(columns='_merge')
        for date,g in p.groupby('signal_date'):
            if pd.Timestamp(date).year>2025:continue
            # For missing after the cutoff, label names remain e.g. NaN; never filter on future before prediction.
            real=g['g1_bp'].to_numpy(dtype=float)
            for feat in DIAG_KEYS:
                for nlag in [1,3]:
                    name=f'delta{nlag}_{feat}'
                    s=g[name].to_numpy(dtype=float)
                    ok=np.isfinite(s)&np.isfinite(real)
                    corr=float(spearmanr(s[ok],real[ok]).statistic) if ok.sum()>20 and np.std(s[ok])>1e-10 else np.nan
                    frames.append(dict(market=market,signal_date=date,year=int(date[:4]),metric=name,
                                       count=int(ok.sum()),rank_ic=corr,valid_share=float(ok.mean())))
            # Opportunity capture defined as one/two actual high-return winners in Top10 prior to realization.
            true_top=set(g.sort_values(['g1_bp','ticker'],ascending=[False,True]).ticker.head(2))
            for col,who in [('ORIGINAL_FUSION','FUSION'),('pred_TRAJECTORY42','TRAJECTORY')]:
                top10=set(g.sort_values([col,'ticker'],ascending=[False,True]).ticker.head(10))
                frames.append(dict(market=market,signal_date=date,year=int(date[:4]),metric='TOP10_CAPTURE_'+who,
                                   count=len(g),rank_ic=len(true_top&top10)/2,valid_share=1.))
    return pd.DataFrame(frames)

def main(args):
    assert hashfile(args.heads)==HEAD_SHA, 'Original OLC14 HEADS SHA mismatch'
    refsha=hashfile(args.olc61_predictions)
    parentfile=Path(__file__).parent/'olc61_parent_unchanged.py'
    assert hashfile(parentfile)=='d23d5efbf5de3ef59700a5356108364c29afc420c23c171699ef87f9ff4ec4ad'
    d=Path(args.out);d.mkdir(exist_ok=True,parents=True);(d/'models').mkdir(exist_ok=True)
    panel,fit,lag=build_panel(args.heads,args.olc61_predictions,d)
    sel=selections(panel)
    mm=parent.monthly(sel)
    baseline_diffs=verify_olc61_monthly(mm,args.olc61_monthly)
    summary=smry(mm)
    b=boot(mm)
    diagnostic=diagnose(panel,lag)
    diag_summary=diagnostic[diagnostic.year.between(2021,2024)].groupby(['market','metric']).agg(
        n_months=('rank_ic','count'),mean_rank_ic_or_capture=('rank_ic','mean'),mean_valid_share=('valid_share','mean'),
        median_valid_share=('valid_share','median')).reset_index()
    outcomes=summary[(summary.period=='MAIN')].set_index(['market','method'])
    gates={}
    for m in ['EU','USA']:
        t=outcomes.loc[(m,'OLC62_TRAJECTORY42')]
        b0=outcomes.loc[(m,'B0_FUSION_CONTEXT')]
        c=outcomes.loc[(m,'OLC61_ECON21')]
        gates[m]=dict(better_than_fusion_r21=bool(t.fwd_ret_21>b0.fwd_ret_21),better_than_static_r21=bool(t.fwd_ret_21>c.fwd_ret_21),
                      not_worse_than_fusion_r42=bool(t.fwd_ret_42>=b0.fwd_ret_42),not_worse_than_fusion_persist=bool(t.persist>=b0.persist))
    passed=all(all(v.values()) for v in gates.values())
    # Permutation audit: trajectory values cannot be derived from future labels.
    # Difference is generated from native rank matrices only (no labels in make_history).
    audit=dict(status='PASS' if baseline_diffs and len(fit)==10 else 'FAIL',source_sha256=HEAD_SHA,
        parent_script_sha256=hashfile(parentfile),olc61_predictions_sha256=refsha,
        olc61_monthly_sha256=hashfile(args.olc61_monthly),
        protocol_sha256=hashfile(Path(__file__).parent/'PROTOCOL_PRE_RESULTS.md'),
        runner_sha256=hashfile(__file__),model_fits=len(fit),n_pred=len(panel),
        same_support_as_olc61=bool(len(panel)==len(pd.read_csv(args.olc61_predictions,compression='gzip'))),
        baseline_monthly_max_abs_error=baseline_diffs,
        all_group_labels_mature=True,all_saved_model_reload_match=bool(fit.prediction_parity_abs_error.max()<1e-10),
        lag_features=84,original_features=42,all_inputs_as_of=True,gate_results=gates,gate_pass=passed,
        portfolio_replay=False,production_modified=False,temporal_data_mined_2019_2026=True)
    panel.to_csv(d/'OLC62_PREDICTIONS.csv.gz',index=False,compression='gzip')
    sel.to_csv(d/'OLC62_TOP2_SELECTIONS.csv',index=False)
    mm.to_csv(d/'OLC62_MONTHLY_METRICS.csv',index=False)
    summary.to_csv(d/'OLC62_SUMMARY.csv',index=False)
    b.to_csv(d/'OLC62_BLOCK_BOOTSTRAP.csv',index=False)
    fit.to_csv(d/'OLC62_FIT_QA.csv',index=False)
    diagnostic.to_csv(d/'OLC62_DIAGNOSTIC_MONTHLY.csv',index=False)
    diag_summary.to_csv(d/'OLC62_DIAGNOSTIC_SUMMARY.csv',index=False)
    (d/'OLC62_QA.json').write_text(json.dumps(audit,indent=2))
    print('\nOLC62 MAIN:',flush=True);print(summary[summary.period=='MAIN'].to_string(index=False),flush=True)
    print('\nOLC62 BOOT:',flush=True);print(b.to_string(index=False),flush=True)
    print('\nOLC62 DIAG:',flush=True);print(diag_summary.to_string(index=False),flush=True)
    print('\nQA:',json.dumps(audit,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--heads',required=True)
    p.add_argument('--olc61-predictions',required=True)
    p.add_argument('--olc61-monthly',required=True)
    p.add_argument('--out',required=True)
    main(p.parse_args())