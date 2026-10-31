"""Common-support USA/EU factorial: frozen 21 selectors and 40 policies.
All state is simulated independently and self-financing, not spliced NAVs.
"""
from pathlib import Path
import json,io,zipfile,pickle,itertools,time,os
import numpy as np,pandas as pd
from common import atomic_json,atomic_bytes,digest
from modeling import MODELS
from engine import run_portfolio
ROOT=Path(__file__).resolve().parents[1]
ALIASES={'BASE_D4':'BASE','RETURN_D4':'RETURN','PAIR127':'PAIR127','RIDGE125':'RIDGE','BASE_MATURE63':'MATURE63','MULTI_453520':'MULTI','CONSENSUS_MULTI':'CONSENSUS'}
BASELINE='BASE_H_K2_EQ_B0_R1_S1'

def native_hybrid(market,signals,tickers):
    if market=='USA':
        z=zipfile.ZipFile('/mnt/data/compact21-tail-factorial-full.zip')
        d=pd.read_csv(io.BytesIO(z.read('B_T1_H1/r1/ENSEMBLE_TAIL_OOS.csv')),parse_dates=['signal_date'])
        d=d[['signal_date','ticker','ET_TAIL','XGB_TAIL']]
    else:
        z=zipfile.ZipFile(ROOT.parent/'inputs/ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip')
        n='source_v4/input/EU165_SPECIALISTS_20261029/input/EU165_NATIVE_MODEL_SCORES_AND_LABELS.csv.gz'
        d=pd.read_csv(io.BytesIO(z.read(n)),compression='gzip',parse_dates=['signal_date'])
        d=d[d.model.isin(['V2_ET_TAIL','V2_XGB_TAIL'])].pivot(index=['signal_date','ticker'],columns='model',values='score').rename(columns={'V2_ET_TAIL':'ET_TAIL','V2_XGB_TAIL':'XGB_TAIL'}).reset_index()
    # Align only observations dated no later than local month-end signal.
    d['month']=d.signal_date.dt.to_period('M');dates=pd.Series(signals,index=signals.to_period('M'))
    d=d[d.month.isin(dates.index)].copy();d=d[d.signal_date<=d.month.map(dates)]
    d=d.sort_values('signal_date').drop_duplicates(['month','ticker'],keep='last')
    allmonths=pd.period_range(signals.min().to_period('M'),signals.max().to_period('M'),freq='M')
    mix=None
    for col,w in [('ET_TAIL',.6),('XGB_TAIL',.4)]:
        v=d.pivot(index='month',columns='ticker',values=col).reindex(index=allmonths,columns=tickers)
        mix=w*v if mix is None else mix+w*v
    sm=.4*mix+.3*mix.shift(1)+.3*mix.shift(2)
    sm=sm.clip(0,1)**1.1;sm=sm.reindex(signals.to_period('M'));sm.index=signals
    return sm

def signals_for(market):
    p=pd.read_pickle(ROOT/'prepared'/f'{market}_panel.pkl');m=pd.read_pickle(ROOT/'prepared'/f'{market}_market.pkl')
    tickers=list(m['mats']['Close'].columns);signals=pd.DatetimeIndex(sorted(p.signal_date.unique()))
    keys=p[['signal_date','ticker','eligible','entry_date','fwd_ret_21']].copy()
    for model in MODELS:
        frames=[]
        for year in range(2019,2027):
            folder=ROOT/'checkpoints'/market/str(year);f=folder/f'{model}.csv.gz';meta=json.loads((folder/f'{model}.json').read_text())
            assert digest(f.read_bytes())==meta['output_sha256']
            assert pd.Timestamp(meta['max_label_exit'])<pd.Timestamp(year,1,1)
            frames.append(pd.read_csv(f,parse_dates=['signal_date']))
        d=pd.concat(frames)[['signal_date','ticker','score']].rename(columns={'score':ALIASES[model]})
        keys=keys.merge(d,on=['signal_date','ticker'],how='left',validate='one_to_one')
    h=native_hybrid(market,signals,tickers).rename_axis(index='signal_date',columns='ticker').stack(dropna=False).rename('HYBRID').reset_index()
    keys=keys.merge(h,on=['signal_date','ticker'],how='left',validate='one_to_one')
    for horizon in [21,63,252]:
        v=p[f'mom{horizon}'].where(p.eligible).groupby(p.signal_date).rank(pct=True)
        keys[f'MOM{horizon}']=v.to_numpy()
    res=m['residual'].reindex(index=signals).rename_axis(index='signal_date',columns='ticker').stack(dropna=False).rename('RESID63_RAW').reset_index()
    keys=keys.merge(res,on=['signal_date','ticker'],how='left',validate='one_to_one')
    keys['RESID63']=keys.RESID63_RAW.where(keys.eligible).groupby(keys.signal_date).rank(pct=True)
    names=list(ALIASES.values())+['HYBRID','MOM21','MOM63','MOM252','RESID63']
    for n in ALIASES.values():keys[n+'_H']=.475*keys[n]+.525*keys.HYBRID;names.append(n+'_H')
    hrank=keys.HYBRID.where(keys.eligible).groupby(keys.signal_date).rank(pct=True)
    keys['COMMITTEE']=(keys.RETURN+keys.PAIR127+keys.RIDGE+hrank)/4
    keys['MOM_COMMITTEE']=.8*keys.COMMITTEE+.1*keys.MOM63+.1*keys.MOM252
    names+=['COMMITTEE','MOM_COMMITTEE'];assert len(names)==21
    keys['supported']=keys.eligible&np.isfinite(keys[names]).all(axis=1)
    counts=keys.groupby('signal_date').supported.sum()
    valid=counts[counts>=20].index;valid=valid[valid>=pd.Timestamp('2019-01-01')]
    atomic_bytes(ROOT/'results'/f'{market}_SIGNAL_COVERAGE.csv',pd.DataFrame({'eligible':keys.groupby('signal_date').eligible.sum(),'common_supported':counts}).to_csv().encode())
    return keys,valid,m,names,tickers

def configurations(names):
    cs=[]
    for name in names:
        for k in (2,5):
            for weight in (('EQ','INV','MARG') if k==2 else ('EQ','INV')):
                for buf,risk,stop in itertools.product([False,True],repeat=3):
                    key=f'{name}_K{k}_{weight}_B{int(buf)}_R{int(risk)}_S{int(stop)}'
                    cs.append(dict(id=key,selector=name,k=k,weight=weight,buffer=buf,half=risk,stops=stop))
    assert len(cs)==840 and len({c['id'] for c in cs})==840
    return cs

def metrics(nav,dates,start,end):
    dates=pd.DatetimeIndex(dates);idx=(dates>=start)&(dates<=end)
    if idx.sum()<2:return None
    lr=np.diff(np.log(np.r_[1.,nav]))[idx];eq=np.exp(np.cumsum(lr));dd=eq/np.maximum.accumulate(np.r_[1.,eq])[1:]-1
    return {'days':int(idx.sum()),'ann_log':float(lr.mean()*252),'cagr':float(np.expm1(lr.mean()*252)),'maxdd':float(dd.min()),'ann_vol':float(np.std(np.expm1(lr),ddof=1)*np.sqrt(252)),'end_equity':float(eq[-1])}

PERIODS={'DEV_2019_2024':('2019-01-01','2024-12-31'),'DEV_2021_2024':('2021-01-01','2024-12-31'),'2019_2020':('2019-01-01','2020-12-31'),'2021_2022':('2021-01-01','2022-12-31'),'2023_2024':('2023-01-01','2024-12-31'),'2025':('2025-01-01','2025-12-31'),'2026_PARTIAL':('2026-01-01','2026-07-01'),'FULL':('2019-01-01','2026-07-01')}

def main():
    t=time.time();O=ROOT/'results';O.mkdir(exist_ok=True)
    inputs={m:signals_for(m) for m in ['USA','EU']}
    common=set(inputs['USA'][1].to_period('M'))&set(inputs['EU'][1].to_period('M'))
    assert len(common)>60
    first=min(common);last=max(common)
    assert len(common)==len(set(common))
    cfg=configurations(inputs['USA'][3]);atomic_json(O/'CONFIGURATIONS.json',cfg)
    rows=[];event_audit=[];modelskill=[]
    from scipy.stats import spearmanr
    for market,(keys,valid,m,names,tickers) in inputs.items():
        signals=pd.DatetimeIndex([d for d in valid if d.to_period('M') in common])
        event_table=keys[keys.signal_date.isin(signals)][['signal_date','entry_date']].drop_duplicates().sort_values('signal_date')
        assert (event_table.entry_date>event_table.signal_date).all()
        start=event_table.entry_date.min();mats=m['mats'];days=mats['Open'].index[mats['Open'].index>=start]
        entry_idx=days.get_indexer(event_table.entry_date);assert (entry_idx>=0).all()
        ed=np.full(len(days),-1,dtype=np.int64);ed[entry_idx]=np.arange(len(event_table))
        scores=np.empty((len(names),len(signals),len(tickers)),dtype=float)
        sup=keys.pivot(index='signal_date',columns='ticker',values='supported').reindex(index=signals,columns=tickers).fillna(False)
        for j,name in enumerate(names):
            f=keys.pivot(index='signal_date',columns='ticker',values=name).reindex(index=signals,columns=tickers).where(sup)
            scores[j]=f.to_numpy()
        vols=m['vol'].reindex(index=signals,columns=tickers).to_numpy();regime=m['regime'].reindex(signals).fillna(False).to_numpy(dtype=bool)
        rawO=mats['Open'].reindex(index=days,columns=tickers).to_numpy();rawL=mats['Low'].reindex(index=days,columns=tickers).to_numpy()
        # Carry prior observed closing mark only for valuation, NEVER for Open fills.
        markC=mats['Close'].ffill().reindex(index=days,columns=tickers).to_numpy()
        np.savez_compressed(O/f'{market}_REPLAY_INPUTS.npz',dates=days.values,O=rawO,L=rawL,C=markC,event_day=ed,scores=scores,vols=vols,regime=regime,tickers=np.array(tickers),selectors=np.array(names))
        for r in event_table.itertuples():event_audit.append({'market':market,'signal_date':str(r.signal_date.date()),'entry_date':str(r.entry_date.date()),'support':int(sup.loc[r.signal_date].sum())})
        for sd,g in keys[keys.supported&keys.signal_date.isin(signals)&keys.fwd_ret_21.notna()].groupby('signal_date'):
            if len(g)<20:continue
            winner=g.fwd_ret_21.idxmax()
            for name in names:
                top=g.nlargest(5,name);sel=g.nlargest(2,name)
                modelskill.append({'market':market,'signal_date':str(sd.date()),'selector':name,'n_etfs':len(g),'ic':float(spearmanr(g[name],g.fwd_ret_21).statistic),'top1_hit':int(winner==g[name].idxmax()),'top5_hit':int(winner in top.index),'top2_excess':float(sel.fwd_ret_21.mean()-g.fwd_ret_21.mean()),'top2_regret':float(g.fwd_ret_21.max()-sel.fwd_ret_21.mean())})
        for fee in [.001,.003]:
            navs=np.empty((len(days),len(cfg)));ledgers=np.empty((len(days),len(cfg),11))
            for ci,c in enumerate(cfg):
                nav,l=run_portfolio(rawO,rawL,markC,ed,scores[names.index(c['selector'])],vols,regime,k=c['k'],weight_mode={'EQ':0,'INV':1,'MARG':2}[c['weight']],buffer=c['buffer'],half=c['half'],stops=c['stops'],fee=fee,slip=.001)
                navs[:,ci]=nav;ledgers[:,ci]=l
                for period,(a,b) in PERIODS.items():
                    stats=metrics(nav,days,a,b)
                    if stats is None:continue
                    mask=(days>=a)&(days<=b);stats.update(turnover=float(l[mask,0].sum()*252/mask.sum()),stops=int(l[mask,2].sum()),deferred=int(l[mask,4].sum()),rebalances=int(l[mask,5].sum()))
                    rows.append({'market':market,'fee_bps':int(fee*10000),'config':c['id'],'period':period,**stats})
            np.savez_compressed(O/f'{market}_NAV_{int(fee*10000)}BP.npz',dates=days.values,configs=np.array([c['id'] for c in cfg]),nav=navs,ledger=ledgers)
            print('REPLAY',market,int(fee*10000),len(cfg),'paths',round(time.time()-t,1),'seconds',flush=True)
            atomic_bytes(O/'SCORECARD.csv',pd.DataFrame(rows).to_csv(index=False).encode())
    atomic_bytes(O/'EVENT_AUDIT.csv',pd.DataFrame(event_audit).to_csv(index=False).encode())
    atomic_bytes(O/'PREDICTIVE_MONTHLY.csv',pd.DataFrame(modelskill).to_csv(index=False).encode())
    atomic_json(O/'REPLAY_STATUS.json',{'status':'REPLAY_COMPLETE_ANALYSIS_PENDING','paths':3360,'selectors':21,'configs':840,'markets':['USA','EU'],'common_signal_months':len(common),'first_signal_month':str(first),'last_signal_month':str(last),'baseline':BASELINE,'seconds':time.time()-t,'note':'Reconstructed execution version; not legacy Stage19 parity or pristine prospective validation.'})
if __name__=='__main__':main()
