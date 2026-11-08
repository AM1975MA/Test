#!/usr/bin/env python3
"""Predeclared paired six-month block diagnostics and policy gates; descriptive not OOS."""
from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
MAIN=(2021,2024);FULL=(2019,2026)

def circular_delta_ci(dates, a, b, B=4000,seed=74008):
    # DataFrames filtered to exact same fee, market, timing, with date/logr; matched months.
    d=a.merge(b,on='date',suffixes=('_a','_b'),validate='one_to_one').sort_values('date')
    assert len(d)==len(a)==len(b) and d.date.nunique()==len(d)
    d['month']=d.date.dt.to_period('M')
    month=d.groupby('month',sort=True).agg(s=('logr_a','sum'),v=('logr_b','sum'),n=('date','size'))
    dr=month.s.to_numpy()-month.v.to_numpy(); n=month.n.to_numpy(); M=len(dr)
    point=float(100*252*dr.sum()/n.sum())
    rng=np.random.default_rng(seed)
    loops=int(np.ceil(M/6))
    start=rng.integers(0,M,size=(B,loops))
    inds=(start[:,:,None]+np.arange(6))%M
    inds=inds.reshape(B,-1)[:,:M]
    samples=100*252*dr[inds].sum(axis=1)/n[inds].sum(axis=1)
    lo,hi=np.quantile(samples,[.025,.975])
    pos=dr[dr>0].sum();largest=np.sort(dr[dr>0])[::-1][:3].sum() if pos>0 else 0
    return {'delta_log_ann_pp':point,'ci95_lo':float(lo),'ci95_hi':float(hi),'months':M,'positive_months':int((dr>0).sum()),'negative_months':int((dr<0).sum()),'top3_positive_fraction':float(largest/pos) if pos else np.nan,'max_month_pp':float(np.max(dr)*100),'min_month_pp':float(np.min(dr)*100),'monthly_delta_by_month':list(zip([str(k) for k in month.index],dr))}

def run():
    score=pd.concat([pd.read_csv(R/'OLC74_SCORECARD.csv'),pd.read_csv(R/'OLC74B_SCORECARD.csv')],ignore_index=True)
    annual=pd.concat([pd.read_csv(R/'OLC74_ANNUAL.csv'),pd.read_csv(R/'OLC74B_ANNUAL.csv')],ignore_index=True)
    daily=pd.concat([pd.read_csv(R/'OLC74_DAILY_LOGRET.csv.gz'),pd.read_csv(R/'OLC74B_DAILY_LOGRET.csv.gz')],ignore_index=True)
    daily.date=pd.to_datetime(daily.date)
    keys=['FUSION_CONF','RETURN_CONF','PAIR_RIDGE','PAIR_LOGIT','RISK_PLUS_RIDGE','TOP10_RIDGE','TOP10_LOGIT']
    ci=[];month=[]
    for market in ['EU','USA']:
        for timing in ['IMMEDIATE','DELAY3']:
            for period,mask in [('MAIN',daily.date.dt.year.between(2021,2024)),('FULL',daily.date.dt.year.between(2019,2026))]:
                base=daily[(daily.market==market)&(daily.timing==timing)&(daily.fee==.001)&(daily.policy=='HALF')&mask][['date','logr']]
                for policy in keys:
                    comp=daily[(daily.market==market)&(daily.timing==timing)&(daily.fee==.001)&(daily.policy==policy)&mask][['date','logr']]
                    x=circular_delta_ci(comp.date,comp,base)
                    for mon,v in x.pop('monthly_delta_by_month'):
                        if period=='FULL':month.append({'market':market,'timing':timing,'policy':policy,'month':mon,'delta_log_pp':100*v})
                    ci.append({'market':market,'timing':timing,'period':period,'policy':policy,**x})
    pd.DataFrame(ci).to_csv(R/'OLC74_PAIRED_BLOCK6.csv',index=False)
    pd.DataFrame(month).to_csv(R/'OLC74_MONTHLY_DELTAS.csv',index=False)
    # Fixed mandatory gates against HALF with same timing and fee .001.
    gates=[]
    for policy in keys:
        row={'policy':policy,'all_pass':True}
        for market in ['EU','USA']:
            for t in ['IMMEDIATE','DELAY3']:
                def rr(p,period):
                    x=score[(score.market==market)&(score.policy==p)&(score.timing==t)&(score.fee==.001)&(score.period==period)]
                    assert len(x)==1
                    return x.iloc[0]
                bmain,bfull=rr('HALF','ACTIVE2021_2024'),rr('HALF','FULL')
                a1,af=rr(policy,'ACTIVE2021_2024'),rr(policy,'FULL')
                md=a1.cagr-bmain.cagr;fd=af.cagr-bfull.cagr; dd=af.maxdd-bfull.maxdd
                passrisk=dd>=-.03
                ok=(md>=0 and fd>=0 and passrisk)
                row[f'{market}_{t}_main_delta']=md;row[f'{market}_{t}_full_delta']=fd;row[f'{market}_{t}_dd_delta']=dd
                row[f'{market}_{t}_pass']=bool(ok)
        row['same_timing_global_pass']=bool(all(row[f'{m}_{t}_pass'] for m in ['EU','USA'] for t in ['IMMEDIATE','DELAY3']))
        row['any_timing_pair_pass']=bool(any(all(row[f'{m}_{t}_pass'] for m in ['EU','USA']) for t in ['IMMEDIATE','DELAY3']))
        gates.append(row)
    pd.DataFrame(gates).to_csv(R/'OLC74_POLICY_GATES.csv',index=False)
    # Effect distributions for 2024-2026, separately from scored annual.
    ann=annual[(annual.fee==.001)&(annual.year.isin([2024,2025,2026]))]
    wide=ann.pivot_table(index=['market','timing','year'],columns='policy',values='return')
    wide.to_csv(R/'OLC74_ANNUAL_2024_26_WIDE.csv')
    print('CIs',pd.DataFrame(ci).query("timing=='IMMEDIATE' and period=='FULL' and policy in ['FUSION_CONF','PAIR_RIDGE','TOP10_LOGIT']")[['market','policy','delta_log_ann_pp','ci95_lo','ci95_hi','positive_months','months','top3_positive_fraction']].to_string(index=False))
    print('Gates',pd.DataFrame(gates)[['policy','any_timing_pair_pass']].to_string(index=False))
    print('Selected annual',wide.loc[('USA','IMMEDIATE')][['HALF','MINVAR63','FUSION_CONF','PAIR_RIDGE','TOP10_LOGIT']].to_string())
if __name__=='__main__':run()