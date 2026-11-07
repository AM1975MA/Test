#!/usr/bin/env python3
"""OLC63: exact frozen-score factorial and descriptive 4-factor Shapley.

No new fits, no market data, no changed OLC19 ledger, no hyperparameter search.
Uses OLC14/O16/O19 immutable source ZIPs. 2019-2026 researched data is not fresh OOS.
"""
from __future__ import annotations
import argparse, hashlib, io, gzip, json, itertools, math, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata

H14 = '4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1'
H16 = 'ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7'
H19 = '3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
P14 = 'olc14_fitted_ranking_20261101/results/'
P16 = 'olc16_contextual_rank_20261102/inputs/'
P19 = 'olc19_combined_risk_20261102/restore/olc18_execution_20261102/inputs/'
COMPONENTS=('R','E','X','M')
ALL_MASK=15


def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as fh:
        for buf in iter(lambda:fh.read(1<<20), b''):h.update(buf)
    return h.hexdigest()


def readgz(z,filename):return pd.read_csv(io.BytesIO(gzip.decompress(z.read(filename))))


def top2_weight(scores):
    a=np.asarray(scores,dtype=float)
    assert np.isfinite(a).all() and len(a)>1
    thresh=np.sort(a)[-2]
    up=a>thresh; eq=a==thresh
    w=up.astype(float);w[eq]=(2-up.sum())/eq.sum()
    assert np.isclose(w.sum(),2,atol=1e-12)
    return w/2


def smooth_matrix(c, use_memory):
    # Exactly OLC14's compose_current, including renormalization of missing history
    if not use_memory: return np.where(np.isfinite(c), np.clip(c,0,1)**1.1, np.nan)
    l1=c[np.maximum(np.arange(len(c))-1,0)];l2=c[np.maximum(np.arange(len(c))-2,0)]
    vals=np.stack([c,l1,l2]);weights=np.array([.4,.3,.3])[:,None,None]
    ok=np.isfinite(vals);den=(weights*ok).sum(0)
    avg=np.divide((np.where(ok,vals,0)*weights).sum(0),den,out=np.full_like(c,np.nan),where=den>0)
    avg=np.where(ok.all(0),.4*c+.3*l1+.3*l2,avg)
    return np.where(np.isfinite(c),np.clip(avg,0,1)**1.1,np.nan)


def reconstruct(m,z14,z16,z19):
    f=readgz(z16,P16+m+'_FITTING_FRAME.csv.gz')
    s=readgz(z14,P14+m+'_MEAN3_SCORES.csv.gz')
    decisions=pd.read_csv(io.BytesIO(z19.read(P19+m+'_ORIGINAL_DECISIONS.csv')))
    assert not f.duplicated(['signal_date','ticker']).any()
    assert not s.duplicated(['signal_date','ticker']).any()
    assert set(zip(f.signal_date,f.ticker))==set(zip(s.signal_date,s.ticker))
    keep=['signal_date','ticker','RETURN','ORIGINAL_P15','ORIGINAL_P15_ET','ORIGINAL_P15_XGB',
          'C21_ET','C21_XGB','C42_ET','C42_XGB','C63_ET','C63_XGB',
          'fwd_ret_21','fwd_ret_42','fwd_ret_63']
    f=f[keep].merge(s[['signal_date','ticker','ORIGINAL_CURRENT','ORIGINAL_SMOOTH','ORIGINAL_FUSION']],
                       on=['signal_date','ticker'],validate='one_to_one',suffixes=('','_OLC14'))
    assert np.array_equal(f.ORIGINAL_P15.notna(),f.ORIGINAL_CURRENT.notna())
    f=f.sort_values(['signal_date','ticker']).reset_index(drop=True)
    f['ER']=f.groupby('signal_date').ORIGINAL_P15_ET.rank(pct=True,method='average')
    f['XR']=f.groupby('signal_date').ORIGINAL_P15_XGB.rank(pct=True,method='average')
    valid=f.ORIGINAL_CURRENT.notna()
    assert np.isfinite(f.loc[valid,'RETURN']).all()
    assert np.allclose(f.loc[valid,'ORIGINAL_CURRENT'],.6*f.loc[valid,'ER']+.4*f.loc[valid,'XR'],rtol=0,atol=2e-14)
    assert np.allclose(f.loc[valid,'ORIGINAL_P15'],f.loc[valid,'ORIGINAL_CURRENT'],rtol=0,atol=0)
    dates=pd.Index(sorted(f.signal_date.unique()),name='signal_date')
    tickers=pd.Index(sorted(f.ticker.unique()),name='ticker')
    di=dates.get_indexer(f.signal_date);ti=tickers.get_indexer(f.ticker)
    def mat(col):return f.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    eligibility=mat('ORIGINAL_CURRENT');mask=np.isfinite(eligibility)
    r=mat('RETURN');e=mat('ER');x=mat('XR')
    n=len(dates); t=len(tickers)
    scores={}; components={}
    for bits in range(16):
        rr=np.where(mask,r if bits&1 else .5,np.nan)
        ee=np.where(mask,e if bits&2 else .5,np.nan)
        xx=np.where(mask,x if bits&4 else .5,np.nan)
        c=.6*ee+.4*xx
        sm=smooth_matrix(c,bool(bits&8))
        score=.475*rr+.525*sm
        score[~mask]=np.nan
        scores[bits]=score
        if bits==15:components={'CURRENT':c,'SMOOTH':sm,'FUSION':score}
    qa={}
    for col in components:
        original=mat('ORIGINAL_'+col)
        assert np.array_equal(np.isfinite(original),mask)
        err=float(np.nanmax(abs(components[col]-original)))
        assert err<=1e-12,('Original formula mismatch',m,col,err)
        qa['score_max_abs_error_'+col]=err
    assert np.allclose(scores[0][mask],np.full(int(mask.sum()),.475*.5+.525*(.5**1.1)),rtol=0,atol=1e-14)
    # Native OLC19 proposed Top2 must match all signals including warmup / partial 2026
    assert len(decisions)==90
    n_good=0;tie_dates=0
    for row in decisions.itertuples(index=False):
        q=dates.get_loc(row.signal_date);ids=np.flatnonzero(mask[q]);srow=scores[15][q,ids]
        cut=np.sort(srow)[-2];is_tie=(srow==cut).sum()>1
        if is_tie:tie_dates+=1
        winners=set(tickers[ids[np.argsort(-srow,kind='stable')[:2]]])
        if winners!={row.ticker1,row.ticker2}:
            raise AssertionError(('OLC19 pair mismatch',m,row.signal_date,winners,row.ticker1,row.ticker2))
        n_good+=1
    qa.update(market=m,source_rows=len(f),unique_signals=len(dates),unique_tickers=len(tickers),
              eligible_rows=int(mask.sum()),matched_olc19_decisions=n_good,full_baseline_ties=tie_dates)
    return f,dates,tickers,di,ti,mask,scores,qa


def evaluate_market(m,f,dates,tickers,di,ti,mask,scores):
    out_month=[]; out_weights=[]; heads=[]; corr=[]
    # put true labels in full date x ticker matrices. All eligibility is before reading these labels.
    def mat(col):return f.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    r21=mat('fwd_ret_21');r42=mat('fwd_ret_42');r63=mat('fwd_ret_63')
    sources={z:mat(z) for z in ['RETURN','ER','XR','ORIGINAL_CURRENT','ORIGINAL_FUSION']}
    head_sources={}
    for h in (21,42,63):
        for family in ('ET','XGB'):
            # Ranking each separate horizon's frozen predicted head. NOT a true FUSION ablation.
            c=f.groupby('signal_date')[f'C{h}_{family}'].rank(pct=True,method='average')
            tmp=f[['signal_date','ticker']].copy();tmp['value']=c
            head_sources[f'C{h}_{family}']=tmp.pivot(index='signal_date',columns='ticker',values='value').reindex(index=dates,columns=tickers).to_numpy(float)
        head_sources[f'C{h}_BLEND']=.6*head_sources[f'C{h}_ET']+.4*head_sources[f'C{h}_XGB']
    for q,date in enumerate(dates):
        yr=int(date[:4])
        if yr<2021 or yr>2025:continue
        ii=np.flatnonzero(mask[q]); tick=tickers[ii]
        if len(ii)<20:raise AssertionError('Insufficient eligible ticker count')
        # Zero/unknown label not allowed: discard the month only for evaluation, not earlier selection.
        if not (np.isfinite(r21[q,ii]).all() and np.isfinite(r42[q,ii]).all()):
            out_month.append(dict(market=m,date=date,year=yr,method='SKIPPED_MISSING_LABEL',eligible_tickers=len(ii),
                                  nmissing=int((~np.isfinite(r21[q,ii])|~np.isfinite(r42[q,ii])).sum())))
            continue
        w={k:top2_weight(v[q,ii]) for k,v in scores.items()}
        v21=r21[q,ii];v42=r42[q,ii];
        relative21=rankdata(v21,method='average')/len(ii);relative42=rankdata(v42,method='average')/len(ii)
        hit=(relative21>.8)&(relative42>.8)
        full=w[15]
        for bits,ww in w.items():
            out_month.append(dict(market=m,date=date,year=yr,method='SUBSET',mask=bits,
                  subset=''.join(c for i,c in enumerate(COMPONENTS) if bits&(1<<i)) or 'NEUTRAL',
                  eligible_tickers=len(ii),mean21=float(ww@v21),mean42=float(ww@v42),
                  upper21=float(ww@(relative21>.8)),persistent=float(ww@hit),
                  negative21=float(ww@(v21<0)),overlap_full=float(np.minimum(ww,full).sum())))
        # record union of selected tickers for reference, including fractional ties
        for bits in [15,15^1,15^2,15^4,15^8,0,1,2,4,6,7]:
            for j in np.flatnonzero(w[bits]>0):
                out_weights.append(dict(market=m,date=date,year=yr,mask=bits,
                                        subset=''.join(c for i,c in enumerate(COMPONENTS) if bits&(1<<i)) or 'NEUTRAL',
                                        ticker=str(tick[j]),weight=float(w[bits][j])))
        for nm,v in head_sources.items():
            sv=v[q,ii]
            if not np.isfinite(sv).all(): continue
            wh=top2_weight(sv)
            heads.append(dict(market=m,date=date,year=yr,head=nm,mean21=float(wh@v21),mean42=float(wh@v42),
                              upper21=float(wh@(relative21>.8)),persistent=float(wh@hit),
                              overlap_fusion=float(np.minimum(wh,full).sum())))
        # Pairwise cross sectional rank correlations of underlying sources, for redundancy diagnosis.
        for a,b in [('ER','XR'),('RETURN','ER'),('RETURN','XR'),('RETURN','ORIGINAL_CURRENT'),('RETURN','ORIGINAL_FUSION'),('ORIGINAL_CURRENT','ORIGINAL_FUSION')]:
            aa=sources[a][q,ii];bb=sources[b][q,ii]
            assert np.isfinite(aa).all() and np.isfinite(bb).all()
            correlation=float(np.corrcoef(rankdata(aa),rankdata(bb))[0,1])
            corr.append(dict(market=m,date=date,year=yr,pair=a+'__'+b,spearman=correlation))
    return pd.DataFrame(out_month),pd.DataFrame(out_weights),pd.DataFrame(heads),pd.DataFrame(corr)


def exact_shapley(table):
    rows=[]
    for (m,date),g in table.groupby(['market','date'],sort=True):
        g=g.set_index('mask')
        assert set(g.index)==set(range(16)),(m,date,len(g))
        for h in ('mean21','mean42'):
            pay=g[h].to_dict()
            vals={}
            for j,label in enumerate(COMPONENTS):
                coef=0.
                for subset in range(16):
                    if subset&(1<<j):continue
                    size=subset.bit_count();weight=math.factorial(size)*math.factorial(3-size)/math.factorial(4)
                    coef+=weight*(pay[subset|(1<<j)]-pay[subset])
                vals[label]=coef
                rows.append(dict(market=m,date=date,year=int(date[:4]),horizon=h,component=label,
                                 shapley_return=coef,baseline_uniform=pay[0],full_fusion=pay[15]))
            assert abs(sum(vals.values())-(pay[15]-pay[0]))<1e-13
    return pd.DataFrame(rows)


def cir_bootstrap(v, B=5000, seed=63001,block=6):
    a=np.asarray(v,float);n=len(a);rng=np.random.default_rng(seed);res=np.empty(B)
    for k in range(B):
        inds=[]
        while len(inds)<n:
            start=int(rng.integers(n));inds.extend((start+j)%n for j in range(block))
        res[k]=a[np.asarray(inds[:n])].mean()
    return float(np.quantile(res,.025)),float(np.quantile(res,.975))


def summarize(month, shap, heads, corr):
    summ=[]; loo=[]; shape=[]; head_s=[]
    subset=month[month.method=='SUBSET'].copy()
    for m in ('EU','USA'):
        for period,years in [('MAIN',(2021,2022,2023,2024)),('LATE',(2025,))]:
            x=subset[(subset.market==m)&subset.year.isin(years)].copy()
            pv21=x.pivot(index='date',columns='mask',values='mean21')
            pv42=x.pivot(index='date',columns='mask',values='mean42')
            overlap=x.pivot(index='date',columns='mask',values='overlap_full')
            assert pv21.notna().all().all() and pv21.columns.size==16
            for bits,gg in x.groupby('mask'):
                summ.append(dict(market=m,period=period,subset=gg.iloc[0].subset,mask=bits,months=len(gg),
                                 avg21=float(gg.mean21.mean()),avg42=float(gg.mean42.mean()),
                                 uplift_vs_uniform21=float(gg.mean21.mean()-pv21[0].mean()),
                                 upper21=float(gg.upper21.mean()),persistent=float(gg.persistent.mean()),
                                 overlap_fusion=float(gg.overlap_full.mean())))
            for j,name in enumerate(COMPONENTS):
                bits=15^(1<<j)
                d21=pv21[15]-pv21[bits];d42=pv42[15]-pv42[bits]
                switched=(overlap[bits]<1-1e-12)
                ci_lo,ci_hi=cir_bootstrap(d21,seed=63001+j)
                loo.append(dict(market=m,period=period,component=name,nmonths=len(d21),changed_months=int(switched.sum()),
                                mean_overlap=float(overlap[bits].mean()),mean21_inclusion=float(d21.mean()),
                                mean42_inclusion=float(d42.mean()),
                                mean21_when_changed=float(d21[switched].mean()) if switched.any() else 0.,
                                favor_inclusion_months=int((d21[switched]>1e-12).sum()),
                                harm_inclusion_months=int((d21[switched]<-1e-12).sum()),
                                bootstrap_mean21_low=ci_lo,bootstrap_mean21_high=ci_hi))
            f=shap[(shap.market==m)&shap.year.isin(years)]
            for (h,c),g in f.groupby(['horizon','component']):
                ss=g.sort_values('date').shapley_return.to_numpy();lo,hi=cir_bootstrap(ss,seed=63001+COMPONENTS.index(c))
                shape.append(dict(market=m,period=period,horizon=h,component=c,nmonths=len(ss),
                                  mean_shapley=float(ss.mean()),bootstrap_ci_lo=lo,bootstrap_ci_hi=hi,
                                  positive_months=int((ss>0).sum()),negative_months=int((ss<0).sum())))
            hs=heads[(heads.market==m)&heads.year.isin(years)]
            for head,g in hs.groupby('head'):
                head_s.append(dict(market=m,period=period,head=head,months=len(g),mean21=float(g.mean21.mean()),
                                   mean42=float(g.mean42.mean()),persistent=float(g.persistent.mean()),
                                   overlap_fusion=float(g.overlap_fusion.mean())))
    correlations=corr.groupby(['market','pair'],as_index=False).agg(mean_spearman=('spearman','mean'),median_spearman=('spearman','median'))
    return pd.DataFrame(summ),pd.DataFrame(loo),pd.DataFrame(shape),pd.DataFrame(head_s),correlations


def run(a):
    paths={name:getattr(a,name) for name in ['olc14','olc16','olc19']}
    computed={name:digest(p) for name,p in paths.items()}
    assert computed=={'olc14':H14,'olc16':H16,'olc19':H19},('Source digests wrong',computed)
    dest=Path(a.out);dest.mkdir(parents=True,exist_ok=True)
    months=[];weights=[];heads=[];corr=[];qa=[]
    with zipfile.ZipFile(a.olc14) as z14,zipfile.ZipFile(a.olc16) as z16,zipfile.ZipFile(a.olc19) as z19:
        for m in ('EU','USA'):
            f,dates,tickers,di,ti,mask,scores,check=reconstruct(m,z14,z16,z19)
            mo,we,he,co=evaluate_market(m,f,dates,tickers,di,ti,mask,scores)
            months.append(mo);weights.append(we);heads.append(he);corr.append(co);qa.append(check)
    mo=pd.concat(months,ignore_index=True)
    skip=mo[mo.method=='SKIPPED_MISSING_LABEL'].copy()
    full=mo[mo.method=='SUBSET'].copy();we=pd.concat(weights,ignore_index=True)
    hs=pd.concat(heads,ignore_index=True);co=pd.concat(corr,ignore_index=True)
    shape=exact_shapley(full)
    s,loo,shs,headsum,cors=summarize(mo,shape,hs,co)
    full.to_csv(dest/'OLC63_MONTHLY_FACTORIAL.csv',index=False)
    we.to_csv(dest/'OLC63_SELECTED_WEIGHTED_TICKERS.csv',index=False)
    shape.to_csv(dest/'OLC63_MONTHLY_SHAPLEY.csv',index=False)
    hs.to_csv(dest/'OLC63_MONTHLY_HEADS.csv',index=False)
    co.to_csv(dest/'OLC63_MONTHLY_CORRELATIONS.csv',index=False)
    for name,df in [('SUMMARY',s),('LEAVE_ONE_OUT',loo),('SHAPLEY_SUMMARY',shs),('HEADS_SUMMARY',headsum),('CORRELATIONS',cors),('SKIPPED_MONTHS',skip)]:
        df.to_csv(dest/('OLC63_'+name+'.csv'),index=False)
    # Matrix Shapley reconciliation with reference selection and uniform baseline.
    for (m,date,h),g in shape.groupby(['market','date','horizon']):
        assert len(g)==4
        assert np.isclose(g.shapley_return.sum(),g.iloc[0].full_fusion-g.iloc[0].baseline_uniform,atol=1e-13)
    # Explicit gate 48 paired main months EU/USA (the researched 2021–24 period).
    counts=full[(full.year>=2021)&(full.year<=2024)&(full['mask']==15)].groupby('market').size().to_dict()
    assert counts=={'EU':48,'USA':48},counts
    assert set(full['mask'])==set(range(16))
    audit=dict(source_sha256=computed,protocol_sha256=digest(dest.parent/'PROTOCOL_PRE_RESULTS.md'),
        reconstruction=qa,matched_months_main=counts,missing_future_months=skip[['market','date','nmissing']].to_dict('records'),
        factor_variants=16,original_weights_unchanged=True,new_learner_fits=0,
        result_shapley_reconciliation=True,production_unchanged=True,comparison_is_retroactively_mined=True)
    (dest/'OLC63_QA.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print('MAIN FUSION + SUBSET CHECK')
    print(s[(s.period=='MAIN')&(s.subset.isin(['REXM','REM','RXM','REX','EXM','E','X','R','NEUTRAL']))].to_string(index=False,float_format=lambda v:f'{v:.4f}'))
    print('LEAVE ONE OUT\n'+loo.to_string(index=False,float_format=lambda v:f'{v:.4f}'))
    print('SHAPLEY\n'+shs.to_string(index=False,float_format=lambda v:f'{v:.4f}'))
    print('HEADS\n'+headsum[headsum.period=='MAIN'].to_string(index=False,float_format=lambda v:f'{v:.4f}'))
    print('QA',json.dumps(audit,indent=1))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--olc14',required=True);ap.add_argument('--olc16',required=True);ap.add_argument('--olc19',required=True);ap.add_argument('--out',required=True)
    run(ap.parse_args())