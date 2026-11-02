"""OLC29. Frozen AUTH rankings + KAMA-only conditional persistence/opportunity actions.
No ETF learner fitted. Targets do not use benchmark or future returns.
"""
import sys, json, warnings, io, zipfile
from pathlib import Path
import numpy as np
import pandas as pd
from collections import defaultdict
ROOT=Path('/mnt/data/kama29')
P20=ROOT/'olc20'
sys.path.insert(0,str(P20/'src'))
from portfolio_validation import P16,readcsv,adapt_state,v6_inputs,rebuild,simulate,validate_book,metrics,extra_metrics
SOURCE=Path('/mnt/data/OLC27_TopTail_Results_20261102.zip')
OUT=ROOT/'out';OUT.mkdir(exist_ok=True)
MARKETS=('EU','USA')
TRIALS=('AUTH','KAMA_PERSIST','KAMA_OPPORTUNITY')
BENCH={('EU','MAIN'):'QDVE.DE',('EU','FULL'):'QDVE.DE',('USA','MAIN'):'ARGT',('USA','FULL'):'SMH'}

def kama_arrays(state):
    c=np.asarray(state['C'],float).copy(); valid=np.isfinite(c)&(c>0)
    if 'observed' in state:valid &=state['observed']
    c[~valid]=np.nan
    t,n=c.shape
    er=np.full((t,n),np.nan);kama=np.full((t,n),np.nan)
    for i in range(10,t):
        chunk=c[i-10:i+1,:]
        # 11 consecutive valid closes, no repair across gaps.
        ok=np.isfinite(chunk).all(axis=0)
        if not ok.any():continue
        net=np.abs(c[i]-c[i-10]);den=np.nansum(np.abs(np.diff(chunk,axis=0)),axis=0)
        er[i,ok]=np.where(den[ok]>0,net[ok]/np.maximum(den[ok],1e-300),0)
        alpha=(er[i,ok]*(2/3-2/31)+2/31)**2
        prev=kama[i-1,ok]
        kama[i,ok]=np.where(np.isfinite(prev),prev+alpha*(c[i,ok]-prev),c[i,ok])
    slope=np.full_like(c,np.nan)
    slope[5:]=(kama[5:]-kama[:-5])/c[5:]
    direction=(slope>0)&(c>kama)
    direction&=np.isfinite(er)&np.isfinite(slope)
    return {'kama':kama,'er':er,'slope':slope,'direction':direction, 'C':c}

def score_map():
    out={}
    with zipfile.ZipFile(SOURCE) as z:
        for market in MARKETS:
            raw=z.read(f'results/AUTH/{market}_SCORES.csv.gz')
            s=pd.read_csv(io.BytesIO(raw),compression='gzip')
            s.signal_date=pd.to_datetime(s.signal_date)
            out[market]=s
    return out

def rank(tab):
    return tab[np.isfinite(tab.FUSION)].sort_values(['FUSION','ticker'],ascending=[False,True],kind='stable')

def decision(market,trial,sc,state):
    ix={x:i for i,x in enumerate(state['tickers'].astype(str))}
    dt=pd.DatetimeIndex(state['dates'])
    feat=kama_arrays(state)
    dates=sorted(sc.signal_date.unique())
    monthly={};prev_auth=None;ttl=set();records=[];summary=[]
    for sdt in dates:
        sd=pd.Timestamp(sdt)
        it=dt.searchsorted(sd,side='right')-1
        v=rank(sc[sc.signal_date==sd]);original=list(v.head(2).ticker)
        assert len(original)==2
        valid_idx={ticker:ix[ticker] for ticker in v.ticker if ticker in ix}
        def raw(ticker):
            return {name:feat[name][it,valid_idx[ticker]] for name in ('slope','er','direction','kama','C')} if (it>=0 and ticker in valid_idx) else {}
        def persist(ticker):
            if it<0 or ticker not in valid_idx:return False
            k=valid_idx[ticker]
            if not (feat['direction'][it,k] and feat['er'][it,k]>=.25):return False
            # The two PRIOR signal dates, not calendar rows.
            pos=dates.index(sdt)
            if pos<2:return False
            for prior in [dates[pos-1],dates[pos-2]]:
                j=dt.searchsorted(pd.Timestamp(prior),side='right')-1
                if j<0 or not feat['direction'][j,k]:return False
            return True
        chosen=original[:];action=None
        if trial=='KAMA_PERSIST' and prev_auth is not None:
            possible=[]
            for t in prev_auth:
                if t in original or t in ttl or t not in valid_idx:continue
                row=v[v.ticker==t]
                if row.empty or not persist(t):continue
                if float(v.iloc[1].FUSION-row.iloc[0].FUSION)>.05:continue
                possible.append((float(row.iloc[0].FUSION),t))
            if possible:
                candidate=sorted(possible,key=lambda x:(-x[0],x[1]))[0][1]
                drop=original[1]
                if candidate!=drop:
                    chosen=[original[0],candidate];action={'add':candidate,'drop':drop,'kind':'persistence'}
            ttl={action['add']} if action else set()
        elif trial=='KAMA_OPPORTUNITY':
            weak=original[1];k=valid_idx[weak]
            if it>=0 and not feat['direction'][it,k]:
                second=float(v.iloc[1].FUSION)
                shortlist=v.head(75)
                eligible=[]
                for rr in shortlist.itertuples():
                    t=rr.ticker
                    if t in original:continue
                    sc2=float(rr.FUSION)
                    if sc2<.65 or second-sc2>.25 or not persist(t):continue
                    s=raw(t)['slope']
                    if np.isfinite(s):eligible.append((float(s),sc2,t))
                if eligible:
                    aa=sorted(eligible,key=lambda x:(-x[0],-x[1],x[2]))[0]
                    chosen=[original[0],aa[2]];action={'add':aa[2],'drop':weak,'kind':'opportunity'}
        if trial!='AUTH' and chosen!=original:
            idx=sc.index[(sc.signal_date==sd)&(sc.ticker==action['add'])]
            assert len(idx)==1
            s_old=float(sc.loc[idx[0],'FUSION'])
            sc.loc[idx[0],'FUSION']=float(v.iloc[1].FUSION)+1e-8
            confirmed=list(rank(sc[sc.signal_date==sd]).head(2).ticker)
            if set(confirmed)!=set(chosen):
                raise AssertionError(f'Adapter mismatch {market} {trial} {sd} {confirmed} vs {chosen} old={s_old}')
        monthly[sd]=chosen
        records.append({'market':market,'signal_date':sd,'trial':trial,'auth_1':original[0],'auth_2':original[1],
                        'selected_1':chosen[0],'selected_2':chosen[1],'changed':chosen!=original,
                        'change_kind':action['kind'] if action else None,'add':action['add'] if action else None,
                        'drop':action['drop'] if action else None})
        prev_auth=original
    return sc, pd.DataFrame(records),feat

def add_target_info(records, state, feat):
    tix={str(t):i for i,t in enumerate(state['tickers'])}
    dt=pd.DatetimeIndex(state['dates']);O=state['O']; obs=state.get('observed')
    cal=readcsv(P16/f"inputs/{records.market.iloc[0]}_CALENDAR.csv");cal.signal_date=pd.to_datetime(cal.signal_date)
    cal.entry_date=pd.to_datetime(cal.entry_date)
    entries={r.signal_date:r.entry_date for r in cal.itertuples()}
    rows=[]
    for rr in records.itertuples():
        sd=rr.signal_date
        ent=entries.get(sd)
        i=dt.searchsorted(ent) if ent is not None else -1
        valid_ent=i>=0 and i<len(dt) and dt[i]==ent
        # month ends at the next signal entry, aligned to the execution contract.
        nxt=cal.loc[cal.signal_date>sd,'entry_date']
        j=dt.searchsorted(nxt.iloc[0]) if len(nxt)>0 else -1
        valid_out=j>=0 and j<len(dt) and len(nxt)>0 and dt[j]==nxt.iloc[0]
        for t in set([rr.auth_1,rr.auth_2,rr.selected_1,rr.selected_2]):
            k=tix[t];ret=np.nan
            if valid_ent and valid_out and O[i,k]>0 and O[j,k]>0 and np.isfinite(O[i,k]) and np.isfinite(O[j,k]):
                if obs is None or (obs[i,k] and obs[j,k]):ret=float(np.log(O[j,k]/O[i,k]))
            rows.append({'date':sd,'market':rr.market,'trial':rr.trial,'ticker':t,'next_month_log':ret})
    return pd.DataFrame(rows)

def generate():
    canonical=score_map();allrecords=[];signals={}
    for m in MARKETS:
        q=dict(np.load(P16/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False));st=kama_arrays(q)
        for trial in TRIALS:
            sc,records,feat=decision(m,trial,canonical[m].copy(),q)
            d=OUT/'trials'/trial;d.mkdir(parents=True,exist_ok=True)
            sc.to_csv(d/f'{m}_SCORES.csv.gz',index=False)
            records.to_csv(d/f'{m}_DECISION_CHANGES.csv',index=False)
            allrecords.append(records)
            signals[m,trial]=(sc,records)
    decisions=pd.concat(allrecords,ignore_index=True)
    decisions.to_csv(OUT/'ALL_DECISIONS.csv',index=False)
    return decisions,signals

def run_trial(m,trial):
    sc=readcsv(OUT/f'trials/{trial}/{m}_SCORES.csv.gz')
    state=dict(np.load(P16/f'inputs/{m}_STATE_HALF.npz',allow_pickle=False))
    cal=readcsv(P16/f'inputs/{m}_CALENDAR.csv')
    st,events,dec=adapt_state(state,cal,sc,'FUSION')
    ctx,allowed=v6_inputs(state,m)
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',category=RuntimeWarning)
        np.testing.assert_array_equal(rebuild(ctx,allowed=allowed),state['alt'])
        st['alt']=rebuild(ctx,st['d1'],st['d2'],st['weights'],allowed)
    assert not np.any((st['alt']>=0)&((st['alt']==st['d1'])|(st['alt']==st['d2'])))
    output=[];outdir=OUT/'trials'/trial;dec.to_csv(outdir/f'{m}_DECISIONS.csv',index=False)
    for contract in ('FAST_LOCK3','ALARM'):
        for fee in (.001,.003):
            key=f'{m}_{contract}_{round(fee*10000)}'
            rv=simulate(st,events,contract=contract,fee=fee,friction=.001)
            audit=validate_book(st,rv)
            if trial=='AUTH':
                reference=np.load(P20/'results/portfolios/AUTH'/f'{key}.npz',allow_pickle=False)
                for k in rv:np.testing.assert_array_equal(rv[k],reference[k])
            if contract=='FAST_LOCK3' and fee==.001:
                np.savez_compressed(outdir/f'{key}.npz',dates=st['dates'],nav=rv['nav'],ledger=rv['ledger'],primary_units=rv['primary_units'])
            pd.DataFrame({'date':st['dates'][1:],'log_return':np.log(rv['nav'][:-1]/rv['ledger'][:-1,0])}).to_csv(outdir/f'{key}_RETURNS.csv.gz',index=False)
            a=extra_metrics(st,rv,metrics(st,rv))
            output.extend(dict(market=m,trial=trial,contract=contract,fee=fee,key=key,**row) for row in a)
    pd.DataFrame(output).to_csv(outdir/f'{m}_SCORECARD.csv',index=False)
    return dict(market=m,trial=trial,scorecard_count=len(output),reference_identical=trial=='AUTH')

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--stage',choices=['scores','replay'],required=True);a=p.parse_args()
    if a.stage=='scores':
        dec,_=generate();print(dec.groupby(['market','trial']).changed.agg(['sum','count']).to_string())
    else:
        for trial in TRIALS:
            for m in MARKETS:
                print(run_trial(m,trial),flush=True)
