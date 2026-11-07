#!/usr/bin/env python3
"""OLC65 - diagnostic upstream error taxonomy from frozen original ETFs.

Input blobs SHA-checked. Never changes OLC19, fits models or generates a trading rule.
Includes oracle targets only as hindsight evaluation, NOT available at signal.

python run_olc65.py --olc14 /path/OLC14_Fitting_Risultati_20261101.zip \
  --olc16 /path/OLC16_Input_Code_Checkpoint_20261102.zip \
  --olc19 /path/OLC19_Rischio_Rientro_Checkpoint_20261102.zip \
  --olc61 /path/OLC61_PREDICTIONS.csv.gz --out results
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

HASHES={
'olc14':'4259b9e756ce02b48b473988a3467cd8c2f2c93394df6f3040698aa06e17c6e1',
'olc16':'ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7',
'olc19':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
'olc61':'a3cf0d3d6755cefaa1962c0dd96d8ad2bd6b92e973ec9d852d536f78fa171659',
'original_reconstruction':'df0a6569e937d9389a03e60e70e8c29725f0f88d509fce24312d9034e7a82bd2',
'olc63_monthly':'f6cf047b543904e425f46b0b8c3c4aac13f81b0aea9040f4fb57f4df93759916',
}
BASE=Path(__file__).resolve().parent

def digest(p):
    h=hashlib.sha256()
    with open(p,'rb') as fh:
        for x in iter(lambda:fh.read(1<<20),b''):h.update(x)
    return h.hexdigest()

def rank_leaders(x):
    # integer min rank 1 best; deterministic tie rank through scipy
    return rankdata(-np.asarray(x,float),method='min').astype(int)

def chosen(indices,s,top_k,include_ties=True):
    n=len(s)
    assert n>=top_k and np.isfinite(s).all()
    cut=np.sort(s)[-top_k]
    if include_ties:return set(np.asarray(indices)[s>=cut])
    sort=np.lexsort((np.asarray(indices,dtype=str), -s))[:top_k]
    return set(np.asarray(indices)[sort])

def average_best_k_return(v,subset,k=2):
    y=np.asarray(v)[list(subset)]
    assert len(y)>=k and np.isfinite(y).all()
    return float(np.sort(y)[-k:].mean())

def boot_spearman(x,y,block=6,B=1000,seed=65001):
    x=np.asarray(x,float);y=np.asarray(y,float);n=len(x)
    rho=float(spearmanr(x,y).statistic) if np.std(x)>1e-15 and np.std(y)>1e-15 else float('nan')
    rng=np.random.default_rng(seed);draw=[]
    for _ in range(B):
        inds=[]
        while len(inds)<n:
            st=int(rng.integers(n));inds.extend((st+k)%n for k in range(block))
        ix=inds[:n]
        a=x[ix];b=y[ix]
        if np.std(a)<=1e-15 or np.std(b)<=1e-15:continue
        q=float(spearmanr(a,b).statistic)
        if np.isfinite(q):draw.append(q)
    return rho,float(np.quantile(draw,.025)) if draw else float('nan'),float(np.quantile(draw,.975)) if draw else float('nan'),len(draw)

def market(m,z14,z16,z19,original,base63,olc61):
    f,dates,tickers,di,ti,mask,scores,qa=base63.reconstruct(m,z14,z16,z19)
    subset=f[f.signal_date.str[:4].astype(int).between(2021,2025) & f.ORIGINAL_CURRENT.notna()].copy()
    p=olc61[olc61.market==m].copy()
    t=subset.merge(p[['signal_date','ticker','ORIGINAL_FUSION','fwd_ret_21','fwd_ret_42']],on=['signal_date','ticker'],how='left',validate='one_to_one',indicator=True,suffixes=('_original','_olc61'))
    assert (t._merge=='both').all() and len(t)==len(p)
    for n in ['ORIGINAL_FUSION','fwd_ret_21','fwd_ret_42']:
        x=t[n+'_original'].to_numpy(float);y=t[n+'_olc61'].to_numpy(float)
        assert np.array_equal(np.isnan(x),np.isnan(y))
        assert float(np.nanmax(abs(x-y)))<1e-12,(m,n)
    months=[];oracle=[];phenotypes=[];base_rank=[];comparisons=[]
    # Input to this loop is generated entirely before any labels are read for ranking.
    for date, g in subset.groupby('signal_date',sort=True):
        idx=dates.get_loc(date)
        inds=np.flatnonzero(mask[idx]);ticker_group=np.array(tickers[inds],dtype=str)
        assert set(g.ticker)==set(ticker_group)
        g=g.set_index('ticker').reindex(ticker_group)
        yr=int(date[:4]);period='MAIN' if yr<=2024 else 'LATE'
        src={
          'FUSION':scores[15][idx,inds],
          'RETURN':g.RETURN.to_numpy(float),
          'ET':g.ER.to_numpy(float),
          'XGB':g.XR.to_numpy(float),
          'CURRENT':g.ORIGINAL_CURRENT.to_numpy(float),
          'SMOOTH':g.ORIGINAL_SMOOTH.to_numpy(float),
        }
        assert all(np.isfinite(v).all() for v in src.values())
        rnk={name:rank_leaders(v) for name,v in src.items()}
        top10={name:chosen(np.arange(len(inds)),v,10) for name,v in src.items()}
        abl10={name:chosen(np.arange(len(inds)),scores[15^(1<<j)][idx,inds],10) for j,name in enumerate(['RETURN','ET','XGB','MEMORY'])}
        top2weight=base63.top2_weight(src['FUSION'])
        assert abs(top2weight.sum()-1)<1e-12
        selected=np.flatnonzero(top2weight>1e-15)
        v21=g.fwd_ret_21.to_numpy(float);v42=g.fwd_ret_42.to_numpy(float)
        # Evaluation is complete-case by MARKET×MONTH for original eligible names; never used to select Top10.
        if not (np.isfinite(v21).all() and np.isfinite(v42).all()):
            months.append(dict(market=m,date=date,year=yr,period=period,status='EXCLUDE_INCOMPLETE_FUTURE_LABEL',n_eligible=len(inds),nmissing=int((~np.isfinite(v21)|~np.isfinite(v42)).sum())))
            continue
        assert (v21>-1).all() and (v42>-1).all()
        fwd_log21=np.log1p(v21);fwd_log42=np.log1p(v42)
        interval=fwd_log42-fwd_log21
        r21=rankdata(v21,method='average')/len(inds);r42=rankdata(v42,method='average')/len(inds)
        full10=top10['FUSION'];universe=set(range(len(inds)))
        for horizon,v in [(21,v21),(42,v42)]:
            true_oracle=chosen(np.arange(len(inds)),v,2,include_ties=False)
            assert len(true_oracle)==2
            for j in sorted(true_oracle):
                found=j in full10;picked=top2weight[j]>1e-12
                assert not picked or found
                typ='ALREADY_SELECTED' if picked else ('ORDERING' if found else 'DISCOVERY')
                vis=[a for a in ('RETURN','ET','XGB','CURRENT','SMOOTH') if j in top10[a]]
                rescue=[a for a in ('RETURN','ET','XGB','MEMORY') if j in abl10[a]]
                oracle.append(dict(market=m,date=date,year=yr,period=period,horizon=horizon,oracle_ticker=ticker_group[j],
                    oracle_future_return=float(v[j]),oracle_edge_logbp=float(1e4*(np.log1p(v[j])-np.median(np.log1p(v)))),
                    classification=typ,rank_fusion=int(rnk['FUSION'][j]),score_fusion=float(src['FUSION'][j]),
                    ranked_original=int(picked),rank_RETURN=int(rnk['RETURN'][j]),rank_ET=int(rnk['ET'][j]),
                    rank_XGB=int(rnk['XGB'][j]),rank_CURRENT=int(rnk['CURRENT'][j]),rank_SMOOTH=int(rnk['SMOOTH'][j]),
                    expert_top10_visible=int(len(vis)>0),expert_visible_in=';'.join(vis),
                    rescued_by_ablation=';'.join(rescue),n_ablations_rescuing=len(rescue)))
        actual21=float(top2weight@v21);actual42=float(top2weight@v42)
        u21=average_best_k_return(v21,universe);k21=average_best_k_return(v21,full10)
        u42=average_best_k_return(v42,universe);k42=average_best_k_return(v42,full10)
        assert u21>=k21-1e-12 and k21>=actual21-1e-12
        assert u42>=k42-1e-12 and k42>=actual42-1e-12
        # Main persistence phenotype is forward percentile >.8 at 21 and 42; disjoint return is separate.
        leader21=r21>.8;leader42=r42>.8
        durable=leader21&leader42;flash=leader21&~leader42;miss=~leader21
        weighted=lambda x:float(top2weight@np.asarray(x,float))
        months.append(dict(market=m,date=date,year=yr,period=period,status='VALID',n_eligible=len(inds),n_top10=len(full10),
          actual21=actual21,oracle_top10_21=k21,oracle_universe21=u21,ordering_gap21=k21-actual21,discovery_gap21=u21-k21,total_gap21=u21-actual21,
          actual42=actual42,oracle_top10_42=k42,oracle_universe42=u42,ordering_gap42=k42-actual42,discovery_gap42=u42-k42,total_gap42=u42-actual42,
          actual_selection_near21=weighted(leader21),actual_durable=weighted(durable),actual_flash=weighted(flash),actual_miss=weighted(miss),
          actual_disjoint_below_peer_median=weighted(interval<np.median(interval)),
          score_margin_top2_3=float(np.sort(src['FUSION'])[-2]-np.sort(src['FUSION'])[-3]),
          score_margin_top10_11=float(np.sort(src['FUSION'])[-10]-np.sort(src['FUSION'])[-11]),
          disagree_return_current=float(1-spearmanr(src['RETURN'],src['CURRENT']).statistic),
          disagree_et_xgb=float(1-spearmanr(src['ET'],src['XGB']).statistic)))
        for j in selected:
            ptyp='DURABLE' if durable[j] else ('SHORT_LIVED' if flash[j] else 'NO_INITIAL_LEADERSHIP')
            phenotypes.append(dict(market=m,date=date,year=yr,period=period,ticker=ticker_group[j],weight=float(top2weight[j]),
                 future21=float(v21[j]),future42=float(v42[j]),relative21=float(r21[j]),relative42=float(r42[j]),
                 second_interval_logbp_vs_median=float(1e4*(interval[j]-np.median(interval))),
                 phenotype=ptyp,score=float(src['FUSION'][j]),top2_3_gap=float(np.sort(src['FUSION'])[-2]-np.sort(src['FUSION'])[-3])))
        for j in range(len(inds)):
            # Grouped rank data make model-input evidence reproducible for a later, separately pre-registered task.
            base_rank.append(dict(market=m,date=date,year=yr,period=period,ticker=ticker_group[j],
                future_ret21=float(v21[j]),future_ret42=float(v42[j]),future_log_g21=float((fwd_log21[j]-np.median(fwd_log21))*1e4),
                future_relative21=float(r21[j]),future_relative42=float(r42[j]),
                original_score_fusion=float(src['FUSION'][j]),
                fusion_rank=int(rnk['FUSION'][j]),return_rank=int(rnk['RETURN'][j]),
                et_rank=int(rnk['ET'][j]),xgb_rank=int(rnk['XGB'][j]),
                current_rank=int(rnk['CURRENT'][j]),smooth_rank=int(rnk['SMOOTH'][j]),
                in_top10=int(j in full10),actual_top2_weight=float(top2weight[j]),
                high_future_gain=int(r21[j]>.9),durable_future_leader=int(durable[j])))
    return pd.DataFrame(months),pd.DataFrame(oracle),pd.DataFrame(phenotypes),pd.DataFrame(base_rank),qa

def summaries(months,oracle,phenotypes):
    rows=[];types=[];vis=[];annual=[];assocs=[];concentr=[]
    for m in ('EU','USA'):
        for period in ('MAIN','LATE'):
            d=months[(months.market==m)&(months.period==period)&(months.status=='VALID')].sort_values('date').copy()
            if len(d)==0:continue
            o=oracle[(oracle.market==m)&(oracle.period==period)]
            pp=phenotypes[(phenotypes.market==m)&(phenotypes.period==period)]
            d21=o[o.horizon==21];d42=o[o.horizon==42]
            q=dict(market=m,period=period,months=len(d),n_avg_eligible=float(d.n_eligible.mean()),
                   avg_actual21=float(d.actual21.mean()),avg_oracle_top10_21=float(d.oracle_top10_21.mean()),
                   avg_oracle_universe21=float(d.oracle_universe21.mean()),
                   avg_ordering_gap21=float(d.ordering_gap21.mean()),avg_discovery_gap21=float(d.discovery_gap21.mean()),
                   avg_total_gap21=float(d.total_gap21.mean()),
                   avg_actual42=float(d.actual42.mean()),avg_ordering_gap42=float(d.ordering_gap42.mean()),
                   avg_discovery_gap42=float(d.discovery_gap42.mean()),avg_total_gap42=float(d.total_gap42.mean()),
                   pct_gap21_ordering=float(d.ordering_gap21.sum()/d.total_gap21.sum()),
                   pct_gap21_discovery=float(d.discovery_gap21.sum()/d.total_gap21.sum()),
                   selected_durable=float(d.actual_durable.mean()),selected_short_lived=float(d.actual_flash.mean()),
                   selected_no_leader21=float(d.actual_miss.mean()),selected_second_interval_below_median=float(d.actual_disjoint_below_peer_median.mean()),
                   n_oracle21=len(d21),n_oracle42=len(d42))
            for label,od in [('21',d21),('42',d42)]:
                ct=od.classification.value_counts()
                for k in ('DISCOVERY','ORDERING','ALREADY_SELECTED'):
                    q[f'oracle{label}_{k.lower()}']=int(ct.get(k,0))
                    q[f'oracle{label}_{k.lower()}_share']=float(ct.get(k,0)/len(od))
            rows.append(q)
            for h,dd in [(21,d21),(42,d42)]:
                for k,g in dd.groupby('classification'):
                    types.append(dict(market=m,period=period,horizon=h,category=k,n=len(g),pct=len(g)/len(dd),
                                     avg_rank_fusion=float(g.rank_fusion.mean()),median_rank_fusion=float(g.rank_fusion.median()),
                                     mean_future_ret=float(g.oracle_future_return.mean())))
                miss=dd[dd.classification=='DISCOVERY']
                for label,source in [('RETURN','RETURN'),('ET','ET'),('XGB','XGB'),('CURRENT','CURRENT'),('SMOOTH','SMOOTH')]:
                    vis.append(dict(market=m,period=period,horizon=h,source=label,n_missed=len(miss),
                                    visible_10=int((miss['rank_'+source]<=10).sum()),
                                    visible_pct=float((miss['rank_'+source]<=10).mean()) if len(miss) else float('nan')))
                vis.append(dict(market=m,period=period,horizon=h,source='ANY_EXPERT',n_missed=len(miss),
                                    visible_10=int(miss.expert_top10_visible.sum()),
                                    visible_pct=float(miss.expert_top10_visible.mean()) if len(miss) else float('nan')))
                for name in ('RETURN','ET','XGB','MEMORY'):
                    vis.append(dict(market=m,period=period,horizon=h,source='ABLATION_'+name,n_missed=len(miss),
                                    visible_10=int(miss.rescued_by_ablation.str.split(';').map(lambda a:name in a).sum()),
                                    visible_pct=float(miss.rescued_by_ablation.str.split(';').map(lambda a:name in a).mean()) if len(miss) else float('nan')))
            for y,dd in d.groupby('year'):
                yy=o[o.year==y];oo=yy[yy.horizon==21]
                annual.append(dict(market=m,year=int(y),period=period,months=len(dd),avg_actual21=float(dd.actual21.mean()),
                   avg_ordering_gap21=float(dd.ordering_gap21.mean()),avg_discovery_gap21=float(dd.discovery_gap21.mean()),
                   avg_total_gap21=float(dd.total_gap21.mean()),
                   oracle21_discovery=int((oo.classification=='DISCOVERY').sum()),
                   oracle21_ordering=int((oo.classification=='ORDERING').sum()),
                   oracle21_total=len(oo),selected_durable=float(dd.actual_durable.mean())))
            for name, col in [('DISCOVERY','discovery_gap21'),('ORDERING','ordering_gap21'),('TOTAL','total_gap21')]:
                v=d[col].to_numpy(float);total=v.sum()
                worst3=d.nlargest(3,col)
                concentr.append(dict(market=m,period=period,part=name,nmonths=len(d),
                                  total_gap_sum_pp=float(100*total),top3_gap_sum_pp=float(100*worst3[col].sum()),
                                  top3_fraction=float(worst3[col].sum()/total) if total>1e-12 else float('nan'),
                                  top3_months=';'.join(worst3.date)))
            # Ex ante diagnostic only; NO fitted trading rules. Four pre-set predictors, two pre-set error metrics.
            for metric in ('discovery_gap21','ordering_gap21','discovery_gap42','ordering_gap42'):
                for num,pred in enumerate(('score_margin_top2_3','score_margin_top10_11',
                                            'disagree_return_current','disagree_et_xgb')):
                    nrep=1000 if period=='MAIN' and metric.endswith('21') else (250 if period=='MAIN' else 0)
                    corr,lo,hi,nboot=boot_spearman(d[pred].values,d[metric].values,B=nrep,seed=65001+num)
                    assocs.append(dict(market=m,period=period,metric=metric,predictor=pred,nmonths=len(d),
                                       spearman=corr,bootstrap_low=lo,bootstrap_high=hi,bootstrap_valid=nboot))
    return tuple(pd.DataFrame(x) for x in [rows,types,vis,annual,assocs,concentr])

def run(a):
    d=Path(a.out);d.mkdir(parents=True,exist_ok=True)
    inputs={z:getattr(a,z) for z in ('olc14','olc16','olc19','olc61')}
    inputs['original_reconstruction']=str(BASE/'reference_run_olc63.py')
    inputs['olc63_monthly']=str(BASE/'reference_OLC63_MONTHLY_FACTORIAL.csv')
    actual={k:digest(v) for k,v in inputs.items()}
    assert actual==HASHES,('SOURCE HASH MISMATCH',actual)
    sp=importlib.util.spec_from_file_location('olc63_reference',inputs['original_reconstruction'])
    assert sp and sp.loader
    ref=importlib.util.module_from_spec(sp);sp.loader.exec_module(ref)
    p61=pd.read_csv(a.olc61)
    out=[];q=[]
    with zipfile.ZipFile(a.olc14) as z14,zipfile.ZipFile(a.olc16) as z16,zipfile.ZipFile(a.olc19) as z19:
        for m in ('EU','USA'):
            result=market(m,z14,z16,z19,False,ref,p61)
            out.append(result[:-1]);q.append(result[-1])
    months,oracle,phenotypes,fullrank=[pd.concat([x[i] for x in out],ignore_index=True) for i in range(4)]
    valid=months[months.status=='VALID']
    assert (valid.groupby(['market','period']).size().loc[('EU','MAIN')]==48 and
            valid.groupby(['market','period']).size().loc[('USA','MAIN')]==48)
    # reconcile with OLC63 month-by-month returns and OLC61 fusion original.
    m63=pd.read_csv(inputs['olc63_monthly'])
    m63=m63[(m63.method=='SUBSET')&(m63['mask']==15)]
    merged=valid.merge(m63[['market','date','mean21','mean42']],on=['market','date'],validate='one_to_one')
    assert len(merged)==len(valid)
    parity21=float((merged.actual21-merged.mean21).abs().max())
    parity42=float((merged.actual42-merged.mean42).abs().max())
    assert parity21<1e-12 and parity42<1e-12
    for name,data in [('MONTHLY_GAPS',months),('ORACLE_TOP2_CLASSIFICATION',oracle),
                       ('SELECTED_PERSISTENCE',phenotypes),('FROZEN_SCORE_AND_OUTCOMES',fullrank)]:
        data.to_csv(d/('OLC65_'+name+'.csv'+('.gz' if name=='FROZEN_SCORE_AND_OUTCOMES' else '')),index=False,
                    compression='gzip' if name=='FROZEN_SCORE_AND_OUTCOMES' else None)
    s,typ,visibility,annual,assoc,concentration=summaries(months,oracle,phenotypes)
    for name,data in [('SUMMARY',s),('ERROR_CATEGORIES',typ),('EXPERT_VISIBILITY',visibility),
                      ('ANNUAL',annual),('EXANTE_ASSOCIATIONS',assoc),('GAP_CONCENTRATION',concentration)]:
        data.to_csv(d/'OLC65_{}.csv'.format(name),index=False)
    qa={'status':'PASS','validated_original_inputs_sha256':actual,'reference_parity':q,
        'olc63_max_abs_return_difference_21':parity21,'olc63_max_abs_return_difference_42':parity42,
        'valid_months':valid.groupby(['market','period']).size().rename('n').reset_index().to_dict('records'),
        'excluded_incomplete':months[months.status!='VALID'][['market','date','nmissing']].to_dict('records'),
        'oracle_top2_events':len(oracle),'selected_weighted_ticker_rows':len(phenotypes),
        'full_rank_rows':len(fullrank),'date_range':{'first':valid.date.min(),'last':valid.date.max()},
        'opportunity_decomposition_max_error':float(max(abs(valid.total_gap21-valid.ordering_gap21-valid.discovery_gap21).max(),
                                                          abs(valid.total_gap42-valid.ordering_gap42-valid.discovery_gap42).max())),
        'model_fit_count':0,'portfolio_backtests':0,'independent_new_holdout':False}
    (d/'OLC65_QA.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
    print('RUN OK',json.dumps({'summary':s.to_dict('records'),'qa':qa},ensure_ascii=False))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--olc14',required=True);ap.add_argument('--olc16',required=True)
    ap.add_argument('--olc19',required=True);ap.add_argument('--olc61',required=True);ap.add_argument('--out',required=True)
    run(ap.parse_args())