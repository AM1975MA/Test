"""OLC31 G2 — frozen annual prequential calibration, NO trading/backtesting.
Protocol: CHECKPOINT_G2_PRE_OUTCOME.md (remote commit 670546a828d85f9b4ce044239b38bb2573252c99).
B1 FUSION only vs B2 FUSION + nine original raw score inputs; equal support.
"""
from __future__ import annotations
import json,io,zipfile
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from g0_source_parity import OUT,ARCH
from g1_raw_gap_diagnostics import build_market,FEATURES

MIN_MONTH_QUALITY=.95
ALPHA=10.0

def dataset():
    with zipfile.ZipFile(ARCH['OLC08']) as z08,zipfile.ZipFile(ARCH['OLC19']) as z19,zipfile.ZipFile(ARCH['OLC20']) as z20:
        parts=[]
        for m in ['EU','USA']:
            d=build_market(m,z08,z19,z20)
            d.insert(0,'market',m)
            d['signal_date']=pd.to_datetime(d.signal_date)
            d['exit_date']=pd.to_datetime(d.exit_date)
            cover=d.groupby('signal_date',sort=True)['label_valid'].transform('mean')
            d['month_quality']=cover
            d['eligible_label']=d.label_valid&(cover>=MIN_MONTH_QUALITY)
            d['r_abs_bp']=np.where(d.eligible_label,d.r_o2o*1e4,np.nan)
            gmed=d.groupby('signal_date').r_abs_bp.transform('median')
            d['r_rel_bp']=d.r_abs_bp-gmed
            # FUSION ranking among all currently scored ETF, NOT on future outcome availability
            d=d.sort_values(['signal_date','FUSION','ticker'],ascending=[True,False,True],kind='stable')
            d['auth_rank']=d.groupby('signal_date').cumcount()+1
            parts.append(d)
    d=pd.concat(parts,ignore_index=True)
    assert not d.duplicated(['market','signal_date','ticker']).any()
    return d

def weights_market_month(d):
    # Exactly half the total mass in each market and equal weight to each date
    counts=d.groupby(['market','signal_date']).size();months=d.groupby('market').signal_date.nunique()
    w=d.apply(lambda r:0.5/(months.loc[r.market]*counts.loc[(r.market,r.signal_date)]),axis=1).to_numpy(float)
    assert np.isclose(w.sum(),1.,atol=1e-12)
    assert np.isclose(w[d.market.eq('EU')].sum(),.5,atol=1e-12)
    assert np.isclose(w[d.market.eq('USA')].sum(),.5,atol=1e-12)
    return w*len(d) # mean sample weight = 1 as frozen

def training(d,year):
    cutoff=pd.Timestamp(year,1,1)
    cols=FEATURES
    train=d[(d.signal_date<cutoff)&(d.exit_date<cutoff)&d.eligible_label].copy()
    train=train[np.isfinite(train[cols]).all(axis=1)&np.isfinite(train.r_abs_bp)&np.isfinite(train.r_rel_bp)]
    if any(train[train.market==m].signal_date.nunique()<12 for m in ['EU','USA']):return None
    assert (train.exit_date<cutoff).all()
    return train

def fit(train,features,ycol):
    x=train[features].to_numpy(float);y=train[ycol].to_numpy(float);w=weights_market_month(train)
    scaler=StandardScaler().fit(x,sample_weight=w)
    mod=Ridge(alpha=ALPHA).fit(scaler.transform(x),y,sample_weight=w)
    assert np.max(abs(scaler.mean_-np.average(x,weights=w,axis=0)))<1e-8
    return scaler,mod

def ensure_future_labels_do_not_affect_train():
    d=pd.DataFrame({'market':['EU']*12+['USA']*12,'signal_date':pd.to_datetime(['2020-11-30']*24),'exit_date':pd.to_datetime(['2020-12-31']*24),'eligible_label':[True]*24,'r_abs_bp':list(np.arange(12))+list(np.arange(12)),'r_rel_bp':list(np.arange(12))+list(np.arange(12))})
    for f in FEATURES:d[f]=np.arange(24)*.01
    # Synthetic mature/immature boundary: 2021 Jan 1 excludes all rows finishing Jan 1.
    d2=d.copy();d2.loc[[0,12],'exit_date']=pd.Timestamp('2021-01-01');d2.loc[[0,12],'r_abs_bp']=10**9
    assert (d2.exit_date<pd.Timestamp('2021-01-01')).sum()==22

def main():
    ensure_future_labels_do_not_affect_train()
    d=dataset();OUT.mkdir(parents=True,exist_ok=True)
    outputs=[];audits=[]
    for year in range(2021,2027):
        train=training(d,year)
        audit={'year':year,'train_available':train is not None,'train_rows':int(len(train)) if train is not None else 0,'train_months':{m:int(train[train.market==m].signal_date.nunique()) for m in ['EU','USA']} if train is not None else {},'last_maturity':str(train.exit_date.max()) if train is not None else None}
        test=d[(d.signal_date.dt.year==year)&d.eligible_label].copy()
        test=test[np.isfinite(test[FEATURES]).all(axis=1)&np.isfinite(test.r_abs_bp)&np.isfinite(test.r_rel_bp)]
        if train is not None and len(test):
            for ycol in ['r_abs_bp','r_rel_bp']:
                for name,cols in [('B1',['FUSION']),('B2',FEATURES)]:
                    scaler,mod=fit(train,cols,ycol)
                    test[f'{ycol}_{name}']=mod.predict(scaler.transform(test[cols].to_numpy(float)))
                test[f'{ycol}_B0']=float(np.median(train[ycol]))
            outputs.append(test[['market','signal_date','entry_date','exit_date','ticker','auth_rank','r_abs_bp','r_rel_bp',*['r_abs_bp_'+x for x in ['B0','B1','B2']],*['r_rel_bp_'+x for x in ['B0','B1','B2']]]].copy())
            audit['test_rows']=len(test)
        audits.append(audit)
    assert len(outputs)==6
    pred=pd.concat(outputs,ignore_index=True)
    # Same complete-case support for B1/B2 by construction.
    for target in ['r_abs_bp','r_rel_bp']:
        for model in ['B1','B2']:
            assert pred[target+'_'+model].notna().all()
            pred[target+'_'+model+'_sqerr']=(pred[target]-pred[target+'_'+model])**2
            pred[target+'_'+model+'_abserr']=(pred[target]-pred[target+'_'+model]).abs()
    pred.to_csv(OUT/'10_G2_ALL_OOF_PREDICTIONS.csv.gz',index=False,compression='gzip')
    # Market-month equal weights: return per-month mean errors; independent months=48 for primary.
    months=[]
    for (m,sd),g in pred.groupby(['market','signal_date']):
        out={'market':m,'signal_date':sd,'year':sd.year,'n':len(g)}
        for y in ['r_abs_bp','r_rel_bp']:
            for loss in ['sqerr','abserr']:
                for mod in ['B1','B2']:
                    out[f'{y}_{mod}_{loss}']=float(g[f'{y}_{mod}_{loss}'].mean())
                out[f'{y}_{loss}_improvement_B1_minus_B2']=out[f'{y}_B1_{loss}']-out[f'{y}_B2_{loss}']
        gg=g[g.auth_rank<=5]
        out['top5_n']=len(gg)
        for y in ['r_abs_bp','r_rel_bp']:
            for mod in ['B1','B2']:
                out[f'top5_{y}_{mod}_sqerr']=float(np.mean((gg[y]-gg[y+'_'+mod])**2)) if len(gg) else np.nan
        months.append(out)
    monthly=pd.DataFrame(months)
    monthly.to_csv(OUT/'11_G2_MONTHLY_LOSS.csv',index=False)
    rows=[]
    for market in ['EU','USA']:
        for label,mask in [('MAIN2021_2024',(monthly.year>=2021)&(monthly.year<=2024)),('2025',monthly.year==2025),('2026_PARTIAL',monthly.year==2026)]:
            c=monthly[(monthly.market==market)&mask]
            if not len(c):continue
            q={'market':market,'period':label,'months':len(c)}
            for y in ['r_abs_bp','r_rel_bp']:
                for loss in ['sqerr','abserr']:
                    for mod in ['B1','B2']:
                        q[f'{y}_{mod}_{loss}']=float(c[f'{y}_{mod}_{loss}'].mean())
                    q[f'{y}_improvement_{loss}']=q[f'{y}_B1_{loss}']-q[f'{y}_B2_{loss}']
            rows.append(q)
    summary=pd.DataFrame(rows);summary.to_csv(OUT/'12_G2_MATCHED_LOSS_SUMMARY.csv',index=False)
    # Joint month-block bootstrap (paired markets by calendar), descriptive only.
    use=monthly[(monthly.year>=2021)&(monthly.year<=2024)].copy()
    use['calendar_month']=pd.to_datetime(use.signal_date).dt.to_period('M')
    for y in ['r_abs_bp','r_rel_bp']:
        for loss in ['sqerr','abserr']:
            for m in ['EU','USA']:
                assert len(use[use.market==m])==48, (m,y,loss)
    res=[];rng=np.random.default_rng(20261102)
    months_list=sorted(use.calendar_month.unique());n=len(months_list)
    assert n==48
    assert all(list(use[use.market==m].sort_values('calendar_month').calendar_month)==months_list for m in ['EU','USA'])
    draws=[]
    for _ in range(4000):
        starts=rng.integers(0,n,size=int(np.ceil(n/6)));draws.append(np.concatenate([np.arange(j,j+6)%n for j in starts])[:n])
    draws=np.asarray(draws)
    for y in ['r_abs_bp','r_rel_bp']:
        for loss in ['sqerr','abserr']:
            b={}
            for m in ['EU','USA']:
                x=use[use.market==m].sort_values('calendar_month')[f'{y}_{loss}_improvement_B1_minus_B2'].to_numpy(float)
                boot=x[draws].mean(axis=1);lo,hi=np.quantile(boot,[.025,.975]);b[m]=boot
                res.append({'market':m,'target':y,'loss':loss,'diff_B1_minus_B2':float(x.mean()),'ci95_low':float(lo),'ci95_high':float(hi),'months':n,'block':6,'resamples':4000,'descriptive':True})
            joint=np.minimum(b['EU'],b['USA']);res.append({'market':'JOINT_MIN','target':y,'loss':loss,'diff_B1_minus_B2':float(min(b['EU'].mean(),b['USA'].mean())),'ci95_low':float(np.quantile(joint,.025)),'ci95_high':float(np.quantile(joint,.975)),'months':n,'block':6,'resamples':4000,'descriptive':True})
    pd.DataFrame(res).to_csv(OUT/'13_G2_BOOTSTRAP_MONTH6.csv',index=False)
    (OUT/'14_G2_FIT_AUDIT.json').write_text(json.dumps({'frozen_protocol':'670546a828d85f9b4ce044239b38bb2573252c99','models':'ridge alpha10 common pooled markets / weighted month','years':audits,'input_features':FEATURES,'train_quality_threshold':MIN_MONTH_QUALITY,'no_economic_replay':True,'no_market_specific_recipe':True,'n_pred':int(len(pred))},indent=2))
    print(summary[['market','period','months','r_rel_bp_improvement_sqerr','r_rel_bp_improvement_abserr','r_abs_bp_improvement_sqerr']].round(4).to_string(index=False))
    print('\nBootstrap description');print(pd.DataFrame(res).query("target=='r_rel_bp'").round(4).to_string(index=False))

if __name__=='__main__': main()
