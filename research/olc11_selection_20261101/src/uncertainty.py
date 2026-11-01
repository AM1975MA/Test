"""Paired calendar-block uncertainty. Bootstrap signs are not posterior probabilities."""
from pathlib import Path
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[1];O=ROOT/'results'
METRICS=['ndcg2','target_top_quintile_precision','target_bottom_quintile_fraction']
NATIVE=[('ET_CLASS','ET_REG'),('XGB_CLASS','XGB_REG'),('XGB_RANK','XGB_REG'),('CLASS_PROB_BLEND','REG_RAW_BLEND')]
PIPE=[(c,'MATCHED_REG') for c in ['ET_CLASS','XGB_CLASS','BOTH_CLASS','XGB_RANK','RANK_ONLY']]

def draw_means(x,block,reps=6000,seed=20261101):
    x=np.asarray(x,float);n,p=x.shape;rng=np.random.default_rng(seed);out=np.empty((reps,p))
    for a in range(0,reps,200):
        k=min(200,reps-a);starts=rng.integers(0,n,size=(k,int(np.ceil(n/block))))
        idx=((starts[:,:,None]+np.arange(block))%n).reshape(k,-1)[:,:n]
        vals=x[idx];counts=np.isfinite(vals).sum(1)
        if (counts==0).any():raise ValueError('No observed months in bootstrap replicate')
        out[a:a+k]=np.nansum(vals,axis=1)/counts
    return out

def make_family(frame,pairs,key,family):
    monthgrid=pd.period_range('2021-01','2024-12',freq='M');columns=[];values=[]
    for cand,base in pairs:
        for metric in METRICS:
            series={}
            for market in ['EU','USA']:
                a=frame[(frame.market==market)&(frame[key]==cand)].copy();b=frame[(frame.market==market)&(frame[key]==base)].copy()
                a.index=pd.to_datetime(a.date).dt.to_period('M');b.index=pd.to_datetime(b.date).dt.to_period('M')
                if a.index.duplicated().any() or b.index.duplicated().any():raise ValueError('Repeated monthly output')
                series[market]=(a[metric]-b[metric]).reindex(monthgrid)
            # Identical calendar support and bootstrap indices for both universes.
            valid=series['EU'].notna()&series['USA'].notna()
            for market in ['EU','USA']:
                values.append(series[market].where(valid).to_numpy());columns.append((cand,base,metric,market,int(valid.sum())))
    x=np.column_stack(values);point=np.nanmean(x,axis=0);rows=[]
    for block in [3,6]:
        draws=draw_means(x,block);sd=draws.std(0,ddof=1);active=sd>1e-15
        critical=float(np.quantile(np.max(np.abs((draws[:,active]-point[active])/sd[active]),axis=1),.95))
        for j,(cand,base,metric,market,n) in enumerate(columns):
            lo,hi=np.quantile(draws[:,j],[.025,.975]);rows.append(dict(family=family,candidate=cand,reference=base,metric=metric,market=market,months=n,calendar_months=48,block_months=block,delta=point[j],low95=lo,high95=hi,simultaneous_low95=point[j]-critical*sd[j],simultaneous_high95=point[j]+critical*sd[j],family_dimensions=len(columns),replicates=6000))
    return rows

def main():
    t=pd.read_csv(O/'TARGET_MONTHS.csv');n=pd.read_csv(O/'NATIVE_LEARNER_MONTHS.csv');rows=[]
    n=n[(n.period=='PRE2025')&(n.seed=='MEAN3')]
    rows+=make_family(n,NATIVE,'learner','native_objectives')
    rows+=make_family(n,[('ET_REG','ARCH_ET'),('XGB_REG','ARCH_XGB')],'learner','matched_cohort_gate')
    for stage in ['CURRENT','FUSION']:
        f=t[(t.period=='PRE2025')&(t.seed=='MEAN3')&(t.stage==stage)]
        rows+=make_family(f,PIPE,'variant','pipeline_'+stage)
    pd.DataFrame(rows).to_csv(O/'PAIRED_UNCERTAINTY.csv',index=False)
    print('uncertainty_rows',len(rows))
if __name__=='__main__':main()
