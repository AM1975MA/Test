"""Paired uncertainty, stage effects and realized failure cases. No parameter selection."""
from pathlib import Path
import json
import numpy as np,pandas as pd
from prepare import read
from portfolio_adapter import adapt_state
R=Path(__file__).resolve().parents[1];O=R/'results';I=R/'inputs'
PAIRS=[('NAIVE_CLASS','MATCHED_REG'),('MIX_CLASS_CURRENT','NAIVE_CLASS'),('SOLO_CLASS_CURRENT','SOLO_REG_CURRENT'),('SOLO_CLASS_MEMORY','SOLO_CLASS_CURRENT'),('PROB_MEMORY','SOLO_CLASS_MEMORY'),('SPECIALIST20_CURRENT','MATCHED_REG'),('SPECIALIST20_MEMORY','MATCHED_REG'),('RERANK5','MATCHED_REG'),('META2','MATCHED_REG'),('META3','META2'),('META3','MATCHED_REG'),('MATCHED_REG','ARCHIVE_S101')]
GRID=pd.period_range('2021-01','2024-12',freq='M')

def paired_uncertainty(frame,metric,source):
    out=[];arrays=[];names=[]
    for cand,base in PAIRS:
        by_market={}
        for market in ['EU','USA']:
            d=frame[frame.market==market]
            a=d[d.variant==cand].set_index('month')[metric].reindex(GRID);b=d[d.variant==base].set_index('month')[metric].reindex(GRID)
            by_market[market]=a-b
        joint=np.isfinite(by_market['EU'])&np.isfinite(by_market['USA'])
        for market in ['EU','USA']:
            names.append((market,cand,base));arrays.append(np.where(joint,by_market[market].to_numpy(),np.nan))
    x=np.array(arrays);mean=np.nanmean(x,axis=1)
    rng=np.random.default_rng(20261101)
    for block in [3,6]:
        starts=rng.integers(0,len(GRID),size=(6000,int(np.ceil(len(GRID)/block))))
        idx=((starts[:,:,None]+np.arange(block))%len(GRID)).reshape(6000,-1)[:,:len(GRID)]
        draws=np.nanmean(x[:,idx],axis=2)
        family=float(np.quantile(np.max(np.abs(draws-mean[:,None]),axis=0),.95))
        for i,(market,cand,base) in enumerate(names):
            lo,hi=np.quantile(draws[i],[.025,.975]);out.append(dict(source=source,metric=metric,market=market,candidate=cand,baseline=base,block_months=block,paired_months=int(np.isfinite(x[i]).sum()),effect=mean[i],ci95_low=lo,ci95_high=hi,family95_low=mean[i]-family,family95_high=mean[i]+family,resampling_positive_fraction=float(np.mean(draws[i]>0))))
    return out

def main():
    all_unc=[]
    f=read(O/'ALL_LAYER_MONTHS.csv');f=f[(f.seed=='MEAN3')&(f.period=='PRE2025')].copy();f['month']=f.date.dt.to_period('M')
    for metric in ['ndcg2','target_top_quintile_precision','target_bottom_quintile_fraction','target_regret']:all_unc+=paired_uncertainty(f,metric,'native_target')
    f=read(O/'ALL_OPPORTUNITY_MONTHS.csv');f=f[(f.seed=='MEAN3')&(f.period=='PRE2025')&(f.horizon==21)].copy();f['month']=f.date.dt.to_period('M')
    all_unc+=paired_uncertainty(f,'top2_excess','static21_payoff')
    monthly=[];by_config={}
    score=read(O/'ALL_SCORECARD.csv')
    for key,g in score.groupby('config'):
        row=g.iloc[0];z=np.load(O/f'paths/{key}.npz');dates=pd.DatetimeIndex(z['dates'])[1:];r=np.diff(np.log(np.r_[1.,z['nav']]))[:-1]
        s=pd.Series(r,index=dates).groupby(dates.to_period('M')).sum();by_config[key]=s
        for month,v in s.items():monthly.append({'market':row.market,'variant':row.variant,'policy':row.policy,'mode':row['mode'],'fee':row.fee,'config':key,'month':month,'log_return':v,'annual_log_proxy':v*12})
    mo=pd.DataFrame(monthly);mo.to_csv(O/'MONTHLY_PORTFOLIO_RETURNS.csv',index=False)
    for policy in ['IMMEDIATE','DELAY3','PHASE5']:
        d=mo[(mo.policy==policy)&(mo['mode']=='FULL')&(mo.fee==.001)]
        all_unc+=paired_uncertainty(d,'annual_log_proxy','portfolio_'+policy)
    pd.DataFrame(all_unc).to_csv(O/'PAIRED_UNCERTAINTY.csv',index=False)
    # Per-period native performance and training example counts, without selecting a winning window.
    t=read(O/'ALL_LAYER_MONTHS.csv');t=t[t.seed=='MEAN3']
    metrics=['ndcg2','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']
    t.groupby(['market','variant','period']).agg(months=('date','nunique'),**{m:(m,'mean') for m in metrics}).reset_index().to_csv(O/'KEY_LAYER_RESULTS.csv',index=False)
    pd.DataFrame(read(O/'META_PROBABILITY_MONTHS.csv').groupby(['market','variant','period'])[['brier','logloss']].mean()).reset_index().to_csv(O/'META_PROBABILITY_SUMMARY.csv',index=False)
    primary=score[(score.period=='ACTIVE2021_2024')&(score['mode']=='FULL')]
    primary.to_csv(O/'KEY_PORTFOLIO_RESULTS.csv',index=False)
    # Report every adverse case, not just a hand-picked successful integration episode.
    cases=[]
    for market in ['EU','USA']:
        q=dict(np.load(I/f'{market}_STATE_HALF.npz'));cal=read(I/f'{market}_CALENDAR.csv');ms=read(O/f'{market}_META_SCORES.csv.gz');labels=read(I/f'{market}_LAYER_LABELS.csv.gz')
        proposals={}
        for v in ['META2','META3']:
            _,_,d=adapt_state(q,cal,ms,v);d['month']=d.entry_date.dt.to_period('M');proposals[v]=d.set_index('month')
        a=by_config[f'{market}_META3_IMMEDIATE_FULL_C10'];b=by_config[f'{market}_META2_IMMEDIATE_FULL_C10'];diff=(a-b).reindex(GRID)
        for month in diff.sort_values().index[:5]:
            pa=proposals['META3'].loc[month];pb=proposals['META2'].loc[month]
            cases.append({'market':market,'month':str(month),'base_return_pct':float(np.expm1(b[month])*100),'candidate_return_pct':float(np.expm1(a[month])*100),'log_difference_pp':float(diff[month]*100),'base_tickers':pb.ticker1+'/'+pb.ticker2,'candidate_tickers':pa.ticker1+'/'+pa.ticker2,'signal_date':str(pa.signal_date.date())})
    pd.DataFrame(cases).to_csv(O/'ADVERSE_MONTH_CASES.csv',index=False)
    print('UNCERTAINTY_ROWS',len(all_unc),'CASE_ROWS',len(cases))
if __name__=='__main__':main()
