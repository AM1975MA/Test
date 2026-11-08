#!/usr/bin/env python3
"""OLC74B preregistered Top10 pairwise anti-symmetric ridge/logit before native replay."""
from __future__ import annotations
from pathlib import Path
import io,json,gzip,zipfile,sys
import numpy as np,pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge,LogisticRegression
import run_olc74 as A
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'
FEATS=['d_return','d_hybrid_smooth','d_mom21','d_mom63','d_log_vol63']

def per_etf(q,k,idx):
    out={}
    for n in [21,63]:
        if k<n+1:
            out[f'mom{n}']=np.nan
            if n==63:out['logvol63']=np.nan
            continue
        h=q['C'][k-n-1:k,idx];obs=q.get('observed')
        ok=np.isfinite(h).all() and np.all(h>0) and (obs is None or np.all(obs[k-n-1:k,idx]))
        if not ok:
            out[f'mom{n}']=np.nan
            if n==63:out['logvol63']=np.nan
            continue
        logh=np.log(h)
        out[f'mom{n}']=float(logh[-1]-logh[0])
        if n==63:out['logvol63']=float(np.log(max(np.diff(logh).std(),1e-8)))
    return out

def make_pool():
    rows=[]; QA={}
    with zipfile.ZipFile(A.ARCH16) as z:
        for m in A.MARKETS:
            q=dict(np.load(A.P/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
            ids=np.flatnonzero(q['events']);sc=A.load_scores(z,m)
            source=A.pd.read_csv(A.TOP/f'OLC67/native/OLC56_{m}_DECISIONS.csv')
            srcframe=pd.read_csv(R/'OLC74_PAIR_PANEL.csv')
            srcframe=srcframe[srcframe.market==m].sort_values('pos').reset_index(drop=True)
            hit=0
            for pos,k in enumerate(ids):
                et=pd.Timestamp(q['dates'][k]);signal=srcframe.signal_date.iloc[pos]
                sl=sc[sc.signal_date==signal].sort_values(['ORIGINAL_FUSION','ticker'],ascending=[False,True])
                sl=sl[sl.ticker.isin(q['tickers'])].iloc[:10]
                assert len(sl)==10,(m,pos)
                top10=list(sl.ticker)
                selected=(source.ticker1.iloc[pos],source.ticker2.iloc[pos]);assert all(t in top10 for t in selected),(m,pos,selected)
                lookup={str(t):i for i,t in enumerate(q['tickers'])}
                entry=int(k);next_idx=int(ids[pos+1]) if pos+1<len(ids) else None
                ticker_info={}
                for _,row in sl.iterrows():
                    t=str(row.ticker);j=lookup[t]
                    h=per_etf(q,entry,j)
                    label=np.nan
                    if next_idx is not None:
                        oo=q['O']
                        pair=[oo[entry,j],oo[next_idx,j]]
                        ok=np.isfinite(pair).all() and np.all(np.asarray(pair)>0)
                        if 'observed' in q:ok=ok and bool(q['observed'][entry,j] and q['observed'][next_idx,j])
                        if ok:label=float(np.log(pair[1]/pair[0]))
                    ticker_info[t]={'return':float(row.RETURN),'smooth':float(row.ORIGINAL_SMOOTH),'label':label,**h}
                for ii in range(10):
                    for jj in range(ii+1,10):
                        t1,t2=top10[ii],top10[jj];a,b=ticker_info[t1],ticker_info[t2]
                        f={'d_return':a['return']-b['return'],'d_hybrid_smooth':a['smooth']-b['smooth'],'d_mom21':a['mom21']-b['mom21'],'d_mom63':a['mom63']-b['mom63'],'d_log_vol63':a['logvol63']-b['logvol63']}
                        y=a['label']-b['label']
                        if t1==selected[0] and t2==selected[1]:hit+=1;expect=srcframe.diff_month_log.iloc[pos];assert not (np.isfinite(expect) and abs(expect-y)>1e-9),(m,pos,expect,y)
                        if t1==selected[1] and t2==selected[0]:hit+=1;expect=srcframe.diff_month_log.iloc[pos];assert not (np.isfinite(expect) and abs(expect+y)>1e-9),(m,pos,expect,y)
                        rows.append({'market':m,'pos':int(pos),'event_date':et,'ticker1':t1,'ticker2':t2,'delta':y,**f})
            QA[m]={'events':len(ids),'pairs':len(ids)*45,'actual_pair_in_pool':int(hit)}
    pool=pd.DataFrame(rows)
    assert all(QA[m]['actual_pair_in_pool']==90 for m in A.MARKETS)
    return pool,QA

def fit_predict(pool):
    actual=pd.read_csv(R/'OLC74_PAIR_PANEL.csv');out=[]; QA={}
    for m in A.MARKETS:
        ds=actual[actual.market==m].sort_values('pos')
        mpool=pool[pool.market==m]
        for rec in ds.itertuples(index=False):
            tr=mpool[(mpool.pos<=rec.pos-2)&mpool.delta.notna()]
            n_dates=tr.pos.nunique()
            z={'market':m,'pos':int(rec.pos),'event_date':rec.event_date,'n_train_months':int(n_dates),'max_train_pos':int(tr.pos.max()) if len(tr) else -1,'fit_available':False,'mu':0.,'p1':.5,'train_pair_sd':np.nan,'y':float(rec.diff_month_log) if np.isfinite(rec.diff_month_log) else np.nan}
            if n_dates>=24:
                assert tr.pos.max()<=rec.pos-2
                x=tr[FEATS].to_numpy(float);y=tr.delta.to_numpy(float)
                finite_label=np.isfinite(y);assert finite_label.all()
                x=np.nan_to_num(x,nan=0.,posinf=0.,neginf=0.)
                # Symmetric pair augmentation: conditional win probability flips if ticker order flips.
                X=np.concatenate([x,-x],axis=0);Y=np.concatenate([y,-y])
                count=tr.groupby('pos').size().to_dict()
                weights=np.array([1./(2*count[int(k)]) for k in tr.pos],float)
                W=np.tile(weights,2)
                scaler=StandardScaler().fit(X)
                Xtr=scaler.transform(X)
                test=np.asarray([getattr(rec,k) for k in FEATS],float).reshape(1,-1)
                Xt=scaler.transform(np.nan_to_num(test,nan=0.,posinf=0.,neginf=0.))
                model=Ridge(alpha=20.,fit_intercept=False).fit(Xtr,Y,sample_weight=W)
                lr=LogisticRegression(C=.1,fit_intercept=False,solver='lbfgs',max_iter=1000,random_state=74009)
                lr.fit(Xtr,(Y>0).astype(int),sample_weight=W)
                z.update(fit_available=True,mu=float(model.predict(Xt)[0]),p1=float(lr.predict_proba(Xt)[0,1]),train_pair_sd=float(max(np.sqrt(np.average(Y*Y,weights=W)),1e-5)))
            out.append(z)
    pred=pd.DataFrame(out)
    assert len(pred)==180
    assert (pred.loc[pred.fit_available,'max_train_pos']<=pred.loc[pred.fit_available,'pos']-2).all()
    return pred

def wpolicy(r,policy):
    if not r.fit_available:return .5
    if policy=='TOP10_RIDGE':return float(np.clip(.5+.25*np.tanh(r.mu/r.train_pair_sd),.25,.75))
    if policy=='TOP10_LOGIT':return float(.25+.5*r.p1)
    raise ValueError(policy)

def main():
    pool,qa=make_pool();pool.to_csv(R/'OLC74B_TOP10_PAIR_POOL.csv.gz',index=False)
    pred=fit_predict(pool);pred.to_csv(R/'OLC74B_PAIR_FORECASTS.csv',index=False)
    stats=[]
    for m in A.MARKETS:
        dd=pred[pred.market==m].copy();dd.event_date=pd.to_datetime(dd.event_date)
        for period,mask in [('MAIN',dd.event_date.dt.year.between(2021,2024)),('2024',dd.event_date.dt.year==2024),('2025',dd.event_date.dt.year==2025),('2026',dd.event_date.dt.year==2026),('FULL',dd.event_date.dt.year>=2019)]:
            z=dd[mask & dd.fit_available & dd.y.notna()]
            if len(z):
                val=z.y.to_numpy();pr=z.mu.to_numpy();pp=z.p1.to_numpy();win=(val>0).astype(int)
                stats.append({'market':m,'period':period,'n':len(z),'mse':float(np.mean((val-pr)**2)),'null_mse':float(np.mean(val**2)),'brier':float(np.mean((win-pp)**2)),'null_brier':float(np.mean((win-.5)**2)),'spearman':float(pd.Series(pr).corr(pd.Series(val),method='spearman')),'accuracy':float(np.mean((pp>.5)==(win==1)))})
    skill=pd.DataFrame(stats);skill.to_csv(R/'OLC74B_FORECAST_SKILL.csv',index=False);print('OLC74B SKILL',skill[skill.period=='MAIN'].to_string(index=False),flush=True)
    cards=[];annual=[];daily=[];weights=[];replayQA={}
    prior=pd.read_csv(R/'OLC74_DAILY_LOGRET.csv.gz')
    for m in A.MARKETS:
        q=dict(np.load(A.P/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False));ids=np.flatnonzero(q['events']);ds=pd.to_datetime(q['dates'][1:])
        pm=pred[pred.market==m].sort_values('pos');assert len(pm)==90
        for policy in ['TOP10_RIDGE','TOP10_LOGIT']:
            w=np.array([wpolicy(row,policy) for row in pm.itertuples()],float)
            assert len(w)==90 and (w>=.25).all() and (w<=.75).all()
            for j,v in enumerate(w):weights.append({'market':m,'pos':j,'event_date':str(q['dates'][ids[j]]),'policy':policy,'w1':v,'w2':1-v})
            qq=A.policy_apply(q,ids,w)
            for timing in A.TIMINGS:
                for fee in A.FEES:
                    key=f'{m}_{policy}_{timing}_{int(fee*10000)}'
                    r=A._impl(qq,q['events'],policy='IMMEDIATE' if timing=='IMMEDIATE' else 'DELAY',fraction=1 if timing=='IMMEDIATE' else 3,fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,ordinary_alarm=False,fast_stop=True,lock_days=3)
                    x=A.logr(r);assert len(x)==len(ds)
                    mfull=A.metrics(qq,r)
                    for met in mfull:
                        if met['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026','CRASH2020','2021','2022','2023'):
                            mask=(ds>=met['first_valuation'])&(ds<=met['last_valuation']);c,dd=A.independent_metrics(x[mask]);assert len(x[mask])==met['n'] and abs(c-met['cagr'])<1e-10 and abs(dd-met['maxdd'])<1e-10
                            cards.append({'market':m,'policy':policy,'timing':timing,'fee':fee,'key':key,**met})
                    for year in sorted(np.unique(ds.year)):
                        y=x[ds.year==year]
                        annual.append({'market':m,'policy':policy,'timing':timing,'fee':fee,'year':int(year),'n':len(y),'return':float(np.expm1(y.sum()))})
                    daily.append(pd.DataFrame({'date':ds,'market':m,'policy':policy,'timing':timing,'fee':fee,'key':key,'logr':x}))
                    print('REPLAY',key,'MAIN',round(100*[e['cagr'] for e in mfull if e['period']=='ACTIVE2021_2024'][0],3),'FULL',round(100*[e['cagr'] for e in mfull if e['period']=='FULL'][0],3),flush=True)
    pd.DataFrame(cards).to_csv(R/'OLC74B_SCORECARD.csv',index=False)
    pd.DataFrame(annual).to_csv(R/'OLC74B_ANNUAL.csv',index=False)
    pd.DataFrame(weights).to_csv(R/'OLC74B_EVENT_WEIGHTS.csv',index=False)
    pd.concat(daily,ignore_index=True).to_csv(R/'OLC74B_DAILY_LOGRET.csv.gz',index=False)
    qa.update({'train_gap_min_events':2,'n_fits':int(pred.fit_available.sum()),'pool_rows':len(pool),'replays':len(daily),'source_observed_issue_USA':True,'QA_status':'PASS'})
    assert qa['replays']==16
    (R/'OLC74B_QA.json').write_text(json.dumps(qa,indent=2,default=str))
if __name__=='__main__':main()