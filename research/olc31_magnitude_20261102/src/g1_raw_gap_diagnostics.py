"""OLC31 G1: NON-fitted exploratory information diagnostics on fixed OLC20 forecasts.
Frozen preregistration CHECKPOINT_G1_PRE_OUTCOME.md. No new predictive model or portfolio run.
"""
from __future__ import annotations
from pathlib import Path
import json,zipfile,io
import numpy as np,pandas as pd
from scipy.stats import pearsonr,spearmanr
from g0_source_parity import ARCH,P19,readcsv,readnpz,OUT

FEATURES=['FUSION','RETURN_RAW','ET_RAW','XGB_RAW','C21_ET','C21_XGB','C42_ET','C42_XGB','C63_ET','C63_XGB']

def corr(a,b):
    m=np.isfinite(a)&np.isfinite(b)
    if m.sum()<4 or np.std(a[m])<1e-14 or np.std(b[m])<1e-14:return np.nan
    return float(np.corrcoef(a[m],b[m])[0,1])

def build_market(market,z08,z19,z20):
    au=readcsv(z20,f'results/trials/AUTH/{market}_SCORES.csv.gz')
    raw=readcsv(z08,f'results/{market}_R_RSI_DOMAIN_FORECASTS.csv.gz')
    old=readcsv(z19,P19+f'{market}_FITTING_FRAME.csv.gz')
    cal=readcsv(z19,P19+f'{market}_CALENDAR.csv')
    state=readnpz(z19,P19+f'{market}_STATE_HALF.npz')
    data=au[['signal_date','ticker','FUSION']].merge(raw[['signal_date','ticker','RETURN_RAW','ET_RAW','XGB_RAW']],on=['signal_date','ticker'],how='left',validate='one_to_one')
    cols=['signal_date','ticker','C21_ET','C21_XGB','C42_ET','C42_XGB','C63_ET','C63_XGB']
    data=data.merge(old[cols],on=['signal_date','ticker'],how='left',validate='one_to_one')
    data=data.merge(cal[['signal_date','entry_date','exit_date']],on='signal_date',how='left',validate='many_to_one')
    idx={pd.Timestamp(d):i for i,d in enumerate(state['dates'])};tc={t:i for i,t in enumerate(state['tickers'])}
    ti=data.ticker.map(tc).to_numpy(int)
    e0=pd.to_datetime(data.entry_date);e1=pd.to_datetime(data.exit_date)
    ii0=e0.map(idx).to_numpy(int)
    validfuture=(e1>e0)&e1.isin(idx)
    ii1=np.zeros(len(data),dtype=int)
    ii1[validfuture.to_numpy()]=e1[validfuture].map(idx).to_numpy(int)
    o0=state['O'][ii0,ti];o1=state['O'][ii1,ti]
    ok=(o0>0)&np.isfinite(o0)&(o1>0)&np.isfinite(o1)&validfuture.to_numpy()
    if 'observed' in state:ok&=state['observed'][ii0,ti]&state['observed'][ii1,ti]
    out=np.full(len(data),np.nan);out[ok]=np.log(o1[ok]/o0[ok])
    data['r_o2o']=out;data['label_valid']=ok
    return data

def main():
    group_res=[];top12=[];null=[];pairs=[];quality={};datafiles={}
    with zipfile.ZipFile(ARCH['OLC08']) as z08,zipfile.ZipFile(ARCH['OLC19']) as z19,zipfile.ZipFile(ARCH['OLC20']) as z20:
        for m in ['EU','USA']:
            data=build_market(m,z08,z19,z20)
            data=data[(data.signal_date>='2021-01-01')&(data.signal_date<'2025-01-01')].copy()
            quality[m]={'rows':int(len(data)),'outcomes_valid':int(data.label_valid.sum()),'months':int(data.signal_date.nunique())}
            for date,g in data.groupby('signal_date',sort=True):
                rank=g.sort_values(['FUSION','ticker'],ascending=[False,True],kind='stable')
                top5=rank.iloc[:5];top2=rank.iloc[:2];s=top5['r_o2o'].to_numpy(float)
                for f in FEATURES:
                    a=top5[f].to_numpy(float)
                    group_res.append({'market':m,'signal_date':date,'feature':f,'n':int((np.isfinite(a)&np.isfinite(s)).sum()),'pearson_top5':corr(a,s)})
                if len(top2)==2 and top2['r_o2o'].notna().all():
                    r=float(top2.r_o2o.iloc[0]-top2.r_o2o.iloc[1])
                    row={'market':m,'signal_date':date,'actual_top1_minus_top2_log':r}
                    for f in FEATURES:row[f+'_gap']=float(top2[f].iloc[0]-top2[f].iloc[1])
                    top12.append(row)
                # All 10 unordered pairs among frozen Top5; never interpreted as 10 independent months.
                for i in range(5):
                    for j in range(i+1,5):
                        x=top5.iloc[i];y=top5.iloc[j]
                        if not (np.isfinite(x.r_o2o) and np.isfinite(y.r_o2o)):continue
                        row={'market':m,'signal_date':date,'ticker_high_auth':x.ticker,'ticker_lower_auth':y.ticker,'actual_spread_log':x.r_o2o-y.r_o2o}
                        for f in FEATURES:row[f+'_gap']=x[f]-y[f]
                        pairs.append(row)
                for f in FEATURES[1:]:
                    raw_values=top5[f].to_numpy(float)
                    for seed in range(31001,31006):
                        rng=np.random.default_rng(np.random.SeedSequence([int(seed),int(pd.Timestamp(date).strftime('%Y%m%d')),0 if m=='EU' else 1,FEATURES.index(f)]))
                        p=raw_values.copy();good=np.isfinite(p);p[good]=p[good][rng.permutation(good.sum())]
                        null.append({'market':m,'signal_date':date,'feature':f,'seed':seed,'pearson_top5_null':corr(p,s)})
    gr=pd.DataFrame(group_res);tt=pd.DataFrame(top12);pn=pd.DataFrame(pairs);nn=pd.DataFrame(null)
    summary=[]
    for m in ['EU','USA']:
        for f in FEATURES:
            actual=gr[(gr.market==m)&(gr.feature==f)].pearson_top5
            t=tt[tt.market==m]
            obs=corr(t[f+'_gap'].to_numpy(float),t.actual_top1_minus_top2_log.to_numpy(float))
            u=nn[(nn.market==m)&(nn.feature==f)] if f!='FUSION' else None
            nullmean=float(u.groupby('seed').pearson_top5_null.mean().mean()) if u is not None else np.nan
            summary.append({'market':m,'feature':f,'months_total':int(len(actual)),'months_valid_top5_corr':int(actual.notna().sum()),'mean_top5_pearson':float(actual.mean()),'median_top5_pearson':float(actual.median()),'top1_top2_months':int(len(t)),'top1_top2_spread_pearson':obs,'null_mean_pearson':nullmean,'candidate_minus_null':float(actual.mean()-nullmean) if f!='FUSION' else np.nan})
    summary=pd.DataFrame(summary)
    for name,df in [('04_G1_MONTHLY_TOP5.csv',gr),('05_G1_TOP1_TOP2_SPREADS.csv',tt),('06_G1_PAIR_DIAGNOSTICS.csv',pn),('07_G1_SAME_MONTH_NULLS.csv',nn),('08_G1_SUMMARY.csv',summary)]:df.to_csv(OUT/name,index=False)
    (OUT/'G1_DIAGNOSTIC_MANIFEST.json').write_text(json.dumps({'status':'DIAGNOSTIC_ONLY_NOT_CALIBRATION','period':'2021-2024','markets':quality,'source_features':FEATURES,'n_pairs':int(len(pn)),'n_top2_months':int(len(tt)),'fixed_null_seeds':list(range(31001,31006)),'no_model_fit':True,'no_portfolio_replay':True,'note':'Within-month Top5 Pearson diagnostics are not proof of calibrated economic magnitude; Top1/2 month correlations have only 48 points and are not independent by ETF.'},indent=2))
    print(summary[['market','feature','mean_top5_pearson','median_top5_pearson','top1_top2_spread_pearson','null_mean_pearson']].round(4).to_string(index=False))

if __name__=='__main__':main()
