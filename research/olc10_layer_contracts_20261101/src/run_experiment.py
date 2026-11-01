"""Layer-first evaluation and genuinely prior-OOF calibration; no portfolio refit."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
from layer_metrics import hybrid_target,economic_relevance,ranking_metrics,opportunity_metrics,ndcg,rank_ic
from calibration import month_weights,mature_history,fit_affine,fit_stack,predict
from recovery_core import atomic_json,sha256,complete_checkpoint
ROOT=Path(__file__).resolve().parents[1];I=ROOT/'inputs';O=ROOT/'results';O.mkdir(exist_ok=True)
PRIMARY_VARIANTS=['REF_RSI','ENSEMBLE_REF42','FRACTION_CORE','FRACTION_PATH','FIXED_CORE_S101','FIXED_PATH_S101','ALL_CORE_S101','ALL_PATH_S101','ENSEMBLE_FIXED_CORE','ENSEMBLE_FIXED_PATH','FIXED_NULL7101_S101','FIXED_NULL7102_S101','FIXED_NULL7103_S101','ALL_NULL7101_S101','ALL_NULL7102_S101','ALL_NULL7103_S101']
DATECOLS=['signal_date','source_date','entry_date','exit_date_21','exit_date_42','exit_date_63']

def keyhash(df):return hashlib.sha256(df[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()
def readcsv(p):
    f=pd.read_csv(p,float_precision='round_trip')
    for c in DATECOLS:
        if c in f:f[c]=pd.to_datetime(f[c])
    return f

def prepare_labels(market):
    dest=I/f'{market}_LAYER_LABELS.csv.gz'
    if dest.exists():return readcsv(dest)
    p=pd.read_pickle(I/f'{market}_HYBRID.pkl');c=pd.read_pickle(I/f'{market}_COMPACT.pkl')
    p['TARGET']=hybrid_target(p.target_rank_21,p.target_rank_42,p.target_rank_63)
    cols=['signal_date','ticker','source_date','entry_date','exit_date_21','exit_date_42','exit_date_63','fwd_ret_21','fwd_ret_42','fwd_ret_63','target_rank_21','target_rank_42','target_rank_63','TARGET']
    out=p[cols].copy().sort_values(['signal_date','ticker'])
    out.to_csv(dest,index=False,compression='gzip')
    # Native Return labels have a potentially different universe; retain explicitly.
    c[c.eligible][[k for k in cols if k in c]+['eligible']].to_csv(I/f'{market}_RETURN_LABELS.csv.gz',index=False,compression='gzip')
    return readcsv(dest)

def source(m,v):
    names={'REF_RSI':'R_RSI_DOMAIN','FRACTION_CORE':'H_UNIQUE','FRACTION_PATH':'H_PATH'}
    return I/f'{m}_{names.get(v,v)}_FORECASTS.csv.gz'

def merged(m,v,l):
    p=readcsv(source(m,v))
    if p.duplicated(['signal_date','ticker']).any():raise ValueError('Duplicate forecast keys')
    if l.duplicated(['signal_date','ticker']).any():raise ValueError('Duplicate label keys')
    assert (p.source_date.dropna()<=p.loc[p.source_date.notna(),'signal_date']).all()
    p=p.rename(columns={'source_date':'prediction_source_date'})
    out=p.merge(l,on=['signal_date','ticker'],how='left',validate='one_to_one').sort_values(['signal_date','ticker']).reset_index(drop=True)
    return out

def calibrate_market(m,l,means):
    f=merged(m,'REF_RSI',l);f['RAW_TARGET']=.6*f.ET_RAW+.4*f.XGB_RAW
    records=[];aud=[]
    for year in range(2019,2027):
        cutoff=pd.Timestamp(year,1,1);h=mature_history(f,cutoff)
        current=f[f.signal_date.dt.year.eq(year)].copy();enough=h.signal_date.nunique()>=18
        base_mean=float(means.loc[(means.market==m)&(means.year==year),'mean_target'].iloc[0])
        current['MEAN_TARGET']=base_mean;current['SHRINK50_TARGET']=.5*current.RAW_TARGET+.5*base_mean
        if enough:
            w=month_weights(h.signal_date);affine=fit_affine(h.RAW_TARGET.to_numpy(),h.TARGET.to_numpy(),w)
            stack=fit_stack(h[['ET_RAW','XGB_RAW']].to_numpy(),h.TARGET.to_numpy(),w)
            current['AFFINE_TARGET']=predict(affine,current.RAW_TARGET)
            current['STACK2_TARGET']=predict(stack,current[['ET_RAW','XGB_RAW']])
        else:
            affine=stack=None
            current['AFFINE_TARGET']=current.RAW_TARGET;current['STACK2_TARGET']=current.RAW_TARGET
        current['CALIBRATION_ACTIVE']=enough
        # This is the immutable output consumed by the old ranking pipeline.
        current['NATIVE_RANK_SCORE']=.6*current.ET+.4*current.XGB
        for col in ['RAW_TARGET','AFFINE_TARGET','STACK2_TARGET','SHRINK50_TARGET']:
            # Values in [0,1] are expectations of a bounded target, not probabilities.
            current[col]=current[col].clip(0,1)
        record={'market':m,'year':year,'active':bool(enough),'training_months':int(h.signal_date.nunique()),'training_rows':len(h),'last_mature_exit':str(h.exit_date_63.max()) if len(h) else None,'max_training_signal':str(h.signal_date.max()) if len(h) else None,'cutoff':str(cutoff),'key_hash':keyhash(h),'affine':affine,'stack2':stack,'original_training_mean':base_mean}
        if len(h):assert h.exit_date_63.max()<cutoff
        aud.append(record);records.append(current)
        atomic_json(O/'calibrators'/f'{m}_{year}.json',record)
    f=pd.concat(records,ignore_index=True)
    f.to_csv(O/f'{m}_CALIBRATED_PREDICTIONS.csv.gz',index=False,compression='gzip')
    atomic_json(O/f'{m}_CALIBRATION_AUDIT.json',aud)
    return f,aud

def in_period(date,exitdate,period):
    if pd.isna(exitdate):return False
    if period=='PRE2025':return pd.Timestamp('2021-01-01')<=date<pd.Timestamp('2025-01-01') and exitdate<pd.Timestamp('2025-01-01')
    if period=='Y2025':return date.year==2025 and exitdate<pd.Timestamp('2026-01-01')
    if period=='Y2026_PARTIAL':return date.year==2026 and exitdate<=pd.Timestamp('2026-07-01')
    if period=='ALL_ACTIVE':return date>=pd.Timestamp('2021-01-01') and exitdate<=pd.Timestamp('2026-07-01')
    raise ValueError(period)

def target_rows(m,v,f,meanmap,targetcol,rankcol):
    rows=[]
    for date,g0 in f.groupby('signal_date'):
        # Prediction support is fixed without inspecting the future target.
        g=g0[np.isfinite(g0[['ET_RAW','XGB_RAW']]).all(axis=1)].copy()
        if len(g)<20:continue
        n_pred=len(g);ok=np.isfinite(g[['TARGET',targetcol,rankcol]]).all(axis=1)&g.exit_date_63.notna()
        # Require complete labelled monthly support for ranking: no future-based candidate removal.
        if not ok.all():continue
        y=g.TARGET.to_numpy();p=g[targetcol].to_numpy();r=g[rankcol].to_numpy();mean=meanmap[date.year]
        rm=ranking_metrics(y,r)
        for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
            if not in_period(date,g.exit_date_63.max(),period):continue
            rows.append(dict(market=m,variant=v,period=period,date=str(date.date()),last_exit=str(g.exit_date_63.max().date()),n=n_pred,
                mse=float(np.mean((p-y)**2)),mae=float(np.mean(abs(p-y))),bias=float(np.mean(p-y)),
                mean_baseline_mse=float(np.mean((mean-y)**2)),pred_sd=float(p.std()),target_sd=float(y.std()),**rm))
    return rows

def opportunity_rows(m,v,f,scorecol):
    rows=[]
    for date,g0 in f.groupby('signal_date'):
        g=g0[np.isfinite(g0[scorecol])].copy()
        if len(g)<20:continue
        scores=g[scorecol].to_numpy()
        for horizon in [21,42,63]:
            exitcol=f'exit_date_{horizon}';retcol=f'fwd_ret_{horizon}'
            if not (np.isfinite(g[retcol]).all() and g[exitcol].notna().all()):continue
            r=g[retcol].to_numpy();stats=opportunity_metrics(r,scores)
            graded=economic_relevance(r)
            for period in ['PRE2025','Y2025','Y2026_PARTIAL','ALL_ACTIVE']:
                if not in_period(date,g[exitcol].max(),period):continue
                rows.append(dict(market=m,variant=v,period=period,date=str(date.date()),last_exit=str(g[exitcol].max().date()),horizon=horizon,n=len(g),economic_ndcg2=ndcg(graded,scores,2),economic_ndcg5=ndcg(graded,scores,5),ic=rank_ic(r,scores),**stats))
    return rows

def main():
    means=pd.read_csv(I/'TRAIN_MEANS.csv');tm=[];op=[];audits=[];support=[]
    for market in ['EU','USA']:
        labels=prepare_labels(market);meanmap=means[means.market==market].set_index('year').mean_target.to_dict()
        cal,aud=calibrate_market(market,labels,means);audits+=aud
        reference_keys=None
        for v in PRIMARY_VARIANTS:
            f=merged(market,v,labels)
            valid=np.isfinite(f[['ET_RAW','XGB_RAW']]).all(axis=1)
            keys=keyhash(f[valid])
            if reference_keys is None:reference_keys=keys
            assert keys==reference_keys,(market,v,'support')
            f['PRED_TARGET']=.6*f.ET_RAW+.4*f.XGB_RAW;f['RANK_SCORE']=.6*f.ET+.4*f.XGB
            tm+=target_rows(market,v,f,meanmap,'PRED_TARGET','RANK_SCORE');op+=opportunity_rows(market,v,f[valid],'RANK_SCORE')
            support.append({'market':market,'variant':v,'predict_rows':int(valid.sum()),'key_hash':keys})
        # Separate target expectation calibration from the native rank channel.
        for v,t,r in [('CAL_AFFINE','AFFINE_TARGET','NATIVE_RANK_SCORE'),('SHRINK50','SHRINK50_TARGET','NATIVE_RANK_SCORE'),('CAL_STACK2','STACK2_TARGET','STACK2_TARGET'),('RAW_TARGET_RANK','RAW_TARGET','RAW_TARGET'),('MEAN_ONLY','MEAN_TARGET','MEAN_TARGET')]:
            tm+=target_rows(market,v,cal,meanmap,t,r);op+=opportunity_rows(market,v,cal,'NATIVE_RANK_SCORE' if v in ['CAL_AFFINE','SHRINK50'] else r)
        for learner in ['ET','XGB']:
            tm+=target_rows(market,learner+'_ALONE',cal,meanmap,learner+'_RAW',learner)
            op+=opportunity_rows(market,learner+'_ALONE',cal,learner)
        # Return is evaluated on its own eligible population (not Hybrid-selected population).
        rlabels=readcsv(I/f'{market}_RETURN_LABELS.csv.gz');p=readcsv(source(market,'REF_RSI'))
        rf=p[['signal_date','ticker','RETURN']].merge(rlabels,on=['signal_date','ticker'],validate='one_to_one')
        op+=opportunity_rows(market,'RETURN_NATIVE',rf,'RETURN')
        print('EVALUATED',market,'monthly_target_rows',len(tm),'opportunity_rows',len(op),flush=True)
        pd.DataFrame(tm).to_csv(O/'TARGET_MONTHS.csv',index=False);pd.DataFrame(op).to_csv(O/'OPPORTUNITY_MONTHS.csv',index=False)
        atomic_json(O/'CALIBRATION_AUDIT.json',audits)
    t=pd.DataFrame(tm);p=pd.DataFrame(op)
    ts=t.groupby(['market','variant','period']).agg(months=('date','nunique'),mse=('mse','mean'),mean_baseline_mse=('mean_baseline_mse','mean'),mae=('mae','mean'),bias=('bias','mean'),pred_sd=('pred_sd','mean'),target_sd=('target_sd','mean'),ndcg2=('ndcg2','mean'),ndcg5=('ndcg5','mean'),ic=('ic','mean'),target_regret=('target_regret','mean'),top_quintile_precision=('target_top_quintile_precision','mean'),bottom_quintile_fraction=('target_bottom_quintile_fraction','mean')).reset_index()
    ts['mse_skill_vs_train_mean']=1-ts.mse/ts.mean_baseline_mse
    ts.to_csv(O/'TARGET_SUMMARY.csv',index=False)
    ps=p.groupby(['market','variant','period','horizon']).agg(months=('date','nunique'),economic_ndcg2=('economic_ndcg2','mean'),economic_ndcg5=('economic_ndcg5','mean'),ic=('ic','mean'),top2_return=('top2_return','mean'),top2_excess=('top2_excess','mean'),top2_regret=('top2_regret','mean'),selected_negative_return=('selected_negative_return','mean'),bottom_quintile_fraction=('bottom_quintile_fraction','mean'),top5_capture=('top5_capture','mean')).reset_index()
    ps.to_csv(O/'OPPORTUNITY_SUMMARY.csv',index=False);pd.DataFrame(support).to_csv(O/'MATCHED_SUPPORT.csv',index=False)
    atomic_json(O/'RUN_SUMMARY.json',{'base_learners_refitted':0,'new_calibration_fits':2*sum(a['active'] for a in audits),'calibration_active_year_batches':sum(a['active'] for a in audits),'target_month_rows':len(t),'opportunity_month_rows':len(p),'saved_variants_reassessed':len(PRIMARY_VARIANTS),'portfolios_simulated':0,'selection_output_unchanged_for':['CAL_AFFINE','SHRINK50'],'warning':'These are native-target and static opportunity metrics, not CAGR, probabilities or portfolio performance.'})
    print(ts[(ts.period=='PRE2025')&ts.variant.isin(['REF_RSI','ENSEMBLE_REF42','CAL_AFFINE','CAL_STACK2','SHRINK50','MEAN_ONLY'])].to_string(index=False))
if __name__=='__main__':main()
