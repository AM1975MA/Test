"""OLC30: signed price-KAMA area and slopes as causal second-stage ranker features.
Locked research protocol on GitHub; does not modify baseline / main / original learners.
"""
import sys, json, warnings
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge

BASE=Path('/mnt/data/kama29')
sys.path.insert(0,str(BASE))
from run_olc29 import kama_arrays
ROOT=Path('/mnt/data/olc30_kama')
ROOT.mkdir(exist_ok=True)
TRIALS={'FUSION_ONLY':['FUSION'], 'FUSION_AREA':['FUSION','area21'],
        'FUSION_SLOPE':['FUSION','slope21'],
        'FUSION_GEOMETRY':['FUSION','area21','slope21','gapspeed5']}
MK=('EU','USA')
FULL=['FUSION','area21','slope21','gapspeed5']

def build_feats(q):
    f=kama_arrays(q)
    c=f['C'];ka=f['kama'];t,n=c.shape
    with np.errstate(invalid='ignore',divide='ignore'):
        g=np.log(c/ka)
        lk=np.log(ka)
    area=pd.DataFrame(g).rolling(21,min_periods=21).mean().to_numpy()
    slope=np.full_like(c,np.nan)
    slope[21:]=(lk[21:]-lk[:-21])/21.
    speed=np.full_like(c,np.nan)
    speed[5:]=(g[5:]-g[:-5])/5.
    return {'area21':area,'slope21':slope,'gapspeed5':speed,'gap':g}

def data_market(m):
    q=dict(np.load(BASE/f'olc19/inputs/{m}_STATE_HALF.npz',allow_pickle=False))
    sc=pd.read_csv(BASE/f'out/trials/AUTH/{m}_SCORES.csv.gz')
    sc.signal_date=pd.to_datetime(sc.signal_date)
    dates=pd.DatetimeIndex(q['dates'])
    cal=pd.read_csv(BASE/f'olc19/inputs/{m}_CALENDAR.csv')
    cal.signal_date=pd.to_datetime(cal.signal_date);cal.entry_date=pd.to_datetime(cal.entry_date)
    feat=build_feats(q)
    tix={str(t):i for i,t in enumerate(q['tickers'])}
    # Date filtering and event data are tied to the frozen monthly calendar.
    rows=[]
    sdates=sorted(sc.signal_date.unique())
    bydate={t:d for t,d in sc.groupby('signal_date')}
    for j,t in enumerate(sdates):
        signal=pd.Timestamp(t)
        si=dates.searchsorted(signal,side='right')-1
        entry=cal.loc[cal.signal_date==signal,'entry_date']
        ei=dates.searchsorted(entry.iloc[0]) if len(entry) else -1
        valid_entry=len(entry)>0 and ei<len(dates) and dates[ei]==entry.iloc[0]
        nex=cal.loc[cal.signal_date>signal,'entry_date']
        exi=dates.searchsorted(nex.iloc[0]) if len(nex) else -1
        valid_exit=len(nex)>0 and exi<len(dates) and dates[exi]==nex.iloc[0]
        tab=bydate[t]
        tick=tab.ticker.astype(str).tolist()
        ix=np.array([tix.get(v,-1) for v in tick])
        rf=tab[['signal_date','ticker','FUSION']].copy()
        for col in ('area21','slope21','gapspeed5'):
            val=np.full(len(rf),np.nan)
            mask=(ix>=0)&(si>=0)
            if mask.any():val[mask]=feat[col][si,ix[mask]]
            rf[col]=val
        rt=np.full(len(rf),np.nan)
        if valid_entry and valid_exit:
            mask=ix>=0
            if mask.any():
                a=q['O'][ei,ix[mask]]; b=q['O'][exi,ix[mask]]
                good=np.isfinite(a)&np.isfinite(b)&(a>0)&(b>0)
                if 'observed' in q:good&=q['observed'][ei,ix[mask]]&q['observed'][exi,ix[mask]]
                val=np.where(good,np.log(b/a),np.nan)
                rt[mask]=val
        rf['monthly_o2o']=rt
        rf['maturity']=pd.Timestamp(nex.iloc[0]) if len(nex)>0 else pd.NaT
        valid_ret=np.isfinite(rt)
        rf['future_percentile']=np.nan
        if valid_ret.sum()>1:
            rf.loc[valid_ret,'future_percentile']=(pd.Series(rt[valid_ret]).rank(method='average').to_numpy()-1)/(valid_ret.sum()-1)
        rf['market']=m
        rows.append(rf)
    df=pd.concat(rows,ignore_index=True)
    return df,q,feat

def weight_balance(df):
    w=pd.Series(0.,index=df.index,dtype=float)
    for market,g in df.groupby('market'):
        for dt,z in g.groupby('signal_date'):
            w.loc[z.index]=.5/g.signal_date.nunique()/len(z)
    return (w/w.sum()*len(w)).to_numpy()

def apply_ranks(yn, train, test, spec):
    w=weight_balance(train)
    scaler=StandardScaler().fit(train[spec],sample_weight=w)
    mod=Ridge(alpha=10.).fit(scaler.transform(train[spec]),train.future_percentile.to_numpy(),sample_weight=w)
    good=test[FULL].notna().all(axis=1)&np.isfinite(test.FUSION)
    pred=np.full(len(test),np.nan)
    if good.sum():pred[good]=mod.predict(scaler.transform(test.loc[good,spec]))
    return pred,{'year':yn,'spec':'+'.join(spec),'rows':len(train),'last_maturity':str(train.maturity.max().date()),
                 'market_weight_eu':float(w[train.market.to_numpy()=='EU'].sum()/w.sum()),
                 'coef':mod.coef_.tolist(), 'intercept':float(mod.intercept_)}

def main():
    frames={}; states={};feats={}
    for market in MK:
        df,states[market],feats[market]=data_market(market)
        frames[market]=df
        print(market,'shape',df.shape,'complete',int(df[FULL].notna().all(axis=1).sum()),flush=True)
    both=pd.concat(frames.values(),ignore_index=True)
    allscores={(m,tr):frames[m][['signal_date','ticker','FUSION']].copy() for m in MK for tr in TRIALS}
    fitrows=[]
    allres=[]
    for year in range(2021,2027):
        cutoff=pd.Timestamp(f'{year}-01-01')
        train=both[(both.maturity<cutoff)&(both.signal_date<cutoff)&both[FULL].notna().all(axis=1)&np.isfinite(both.future_percentile)].copy()
        test=both[both.signal_date.dt.year==year].copy()
        assert len(train)==0 or bool((train.maturity<cutoff).all())
        if len(train)<100 or min(train.groupby('market').signal_date.nunique().reindex(MK,fill_value=0))<8:
            print('fallback',year,len(train)); continue
        for trial,spec in TRIALS.items():
            pred,detail=apply_ranks(year,train,test,spec)
            detail['trial']=trial;fitrows.append(detail)
            zz=test[['market','signal_date','ticker','FUSION','monthly_o2o','future_percentile']].copy()
            zz['pred']=pred
            zz['pred_pct']=np.nan
            for (m,dt),g in zz.groupby(['market','signal_date']):
                val=np.isfinite(g.pred)
                if val.sum()>1:
                    idx=g.index[val]
                    zz.loc[idx,'pred_pct']=(g.loc[idx,'pred'].rank(method='average')-1)/(val.sum()-1)
            zz['adjusted']=np.where(np.isfinite(zz.pred_pct),.8*zz.FUSION+.2*zz.pred_pct,zz.FUSION)
            for m in MK:
                sel=zz.market==m
                rows=zz.loc[sel,['signal_date','ticker','adjusted']].rename(columns={'adjusted':'FUSION'})
                dest=allscores[m,trial]
                mapping={(a,b):v for a,b,v in rows.itertuples(index=False,name=None)}
                # exact old ordering maintained; scores replaced by (date,ticker) keyed join
                keys=list(zip(dest.signal_date,dest.ticker))
                dest['FUSION']=[mapping.get(k,val) for k,val in zip(keys,dest.FUSION)]
            allres.append(zz.assign(trial=trial,year=year))
        print('fitted',year,'rows',len(train),'last',train.maturity.max(),flush=True)
    output=BASE/'out/trials'
    for m in MK:
        for tr in TRIALS:
            dst=output/('OLC30_'+tr);dst.mkdir(parents=True,exist_ok=True)
            allscores[m,tr].to_csv(dst/f'{m}_SCORES.csv.gz',index=False)
    pd.DataFrame(fitrows).to_csv(ROOT/'FIT_AUDIT.csv',index=False)
    if allres:pd.concat(allres,ignore_index=True).to_csv(ROOT/'PREDICTIONS.csv.gz',index=False)
    for market in MK:
        base=frames[market].sort_values(['signal_date','FUSION','ticker'],ascending=[True,False,True]).groupby('signal_date').head(2)
        print('AUTH_TOP2',market,base.groupby(base.signal_date.dt.year).ticker.nunique().to_dict())
    print('saved scores and audit')

if __name__=='__main__': main()
