#!/usr/bin/env python3
"""OLC74 preregistered causal-time exposure study, original OLC19 full engine.
No optimizing any parameter based on test results; 7 fixed policy arms.
"""
from __future__ import annotations
import hashlib, io, json, gzip, zipfile, sys, math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge, LogisticRegression

ROOT=Path(__file__).resolve().parent
TOP=Path('/mnt/data/OLC73_Allocation_20261108')
N=TOP/'OLC67/native/olc19_combined_risk_20261102'
P=N/'restore/olc18_execution_20261102'
R=ROOT/'results'; R.mkdir(exist_ok=True)
sys.path[:0]=[str(N/'src'),str(P/'parent_archive/parent/olc16_contextual_rank_20261102/src')]
from combined_engine import _impl
from portfolio_metrics_parent import metrics

ARCH16=Path('/mnt/data/etf_source/OLC16_Input_Code_Checkpoint_20261102.zip')
ARCH19=Path('/mnt/data/etf_source/OLC19_Rischio_Rientro_Checkpoint_20261102.zip')
ARCH73=Path('/mnt/data/OLC73_Allocazioni_Top2_20261108_VERIFICATO.zip')
MARKETS=('EU','USA')
POLICIES=('HALF','MINVAR63','FUSION_CONF','RETURN_CONF','PAIR_RIDGE','PAIR_LOGIT','RISK_PLUS_RIDGE')
TIMINGS=('IMMEDIATE','DELAY3')
FEES=(.001,.003)
XCOLS=['d_return','d_hybrid_smooth','d_mom21','d_mom63','d_log_vol63','corr63','missing63']

def sha256(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def load_scores(archive,market):
    name=f'olc16_contextual_rank_20261102/inputs/{market}_MEAN3_SCORES.csv.gz'
    frame=pd.read_csv(io.BytesIO(gzip.decompress(archive.read(name))))
    frame.signal_date=pd.to_datetime(frame.signal_date)
    assert not frame.duplicated(['signal_date','ticker']).any()
    return frame

def calc_hist(q,k,i,j,length):
    if k<length+1:return None
    raw=q['C'][k-length-1:k-1][:,[i,j]]  # explicitly through previous close k-2? careful index
    assert raw.shape==(length,2)
    obs=q.get('observed')
    if obs is not None and not np.all(obs[k-length-1:k-1][:,[i,j]]):return None
    if not (np.isfinite(raw).all() and np.all(raw>0)):return None
    logreturns=np.diff(np.log(raw),axis=0)
    return raw,logreturns

def calc_features(q,k,i,j):
    # At event open k, all historical bars must end by k-1.
    # k-64:k gives 64 fully completed close points up to k-1.
    def history(length):
        if k<length+1:return None
        raw=q['C'][k-length-1:k][:,[i,j]]
        assert raw.shape==(length+1,2)
        obs=q.get('observed')
        if obs is not None and not np.all(obs[k-length-1:k][:,[i,j]]):return None
        if not(np.isfinite(raw).all() and np.all(raw>0)):return None
        return np.log(raw)
    h21,h63=history(21),history(63)
    out={}
    if h21 is None:out['d_mom21']=np.nan
    else:out['d_mom21']=float((h21[-1,0]-h21[0,0])-(h21[-1,1]-h21[0,1]))
    if h63 is None:
        out.update(d_mom63=np.nan,d_log_vol63=np.nan,corr63=np.nan,missing63=1.)
    else:
        lr=np.diff(h63,axis=0)
        vol=lr.std(axis=0)
        out['d_mom63']=float((h63[-1,0]-h63[0,0])-(h63[-1,1]-h63[0,1]))
        out['d_log_vol63']=float(np.log(max(vol[0],1e-8)/max(vol[1],1e-8)))
        out['corr63']=float(np.corrcoef(lr[:,0],lr[:,1])[0,1]) if all(vol>1e-9) else np.nan
        out['missing63']=0.
    return out

def build_monthly():
    frames=[]; sources={}
    with zipfile.ZipFile(ARCH16) as z:
        for market in MARKETS:
            q=dict(np.load(P/f'inputs/{market}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
            ids=np.flatnonzero(q['events'])
            decisions=pd.read_csv(TOP/f'OLC67/native/OLC56_{market}_DECISIONS.csv')
            assert len(ids)==len(decisions)==90
            assert np.array_equal(ids,decisions.event_index.to_numpy())
            scores=load_scores(z,market)
            signals=np.sort(scores.signal_date.unique())
            sources[market]={'n_events':int(len(ids)),'n_score_rows':int(len(scores)),'observed_mask':('original' if 'observed' in q else 'missing_source_proxy')}
            for pos,k in enumerate(ids):
                et=pd.Timestamp(q['dates'][k])
                assert et==pd.Timestamp(decisions.entry_date.iloc[pos]),(market,pos,et)
                prior_dates=signals[signals<np.datetime64(et)]
                assert len(prior_dates)>0
                prev_sig=pd.Timestamp(prior_dates[-1])
                # All available monthly score dates are lagged, never observed after the event.
                a,b=int(q['d1'][0,k]),int(q['d2'][0,k])
                t1,t2=str(q['tickers'][a]),str(q['tickers'][b])
                assert t1==decisions.ticker1.iloc[pos] and t2==decisions.ticker2.iloc[pos]
                pair=scores[(scores.signal_date==prev_sig)&scores.ticker.isin([t1,t2])]
                assert len(pair)==2,(market,pos,et,t1,t2,prev_sig,pair)
                one,two=(pair.set_index('ticker').loc[t] for t in (t1,t2))
                s={name:float(one[name]-two[name]) for name in ['RETURN','ORIGINAL_SMOOTH','ORIGINAL_FUSION']}
                assert abs(s['ORIGINAL_FUSION']-(.475*s['RETURN']+.525*s['ORIGINAL_SMOOTH']))<1e-11
                f=calc_features(q,int(k),a,b)
                if pos+1<len(ids):
                    k2=int(ids[pos+1]); o=q['O']
                    ok=all(np.isfinite([o[k,a],o[k,b],o[k2,a],o[k2,b]])) and all(np.asarray([o[k,a],o[k,b],o[k2,a],o[k2,b]])>0)
                    if 'observed' in q:ok=ok and bool(q['observed'][k,a] and q['observed'][k,b] and q['observed'][k2,a] and q['observed'][k2,b])
                    label=float(np.log(o[k2,a]/o[k,a])-np.log(o[k2,b]/o[k,b])) if ok else np.nan
                    exit_date=pd.Timestamp(q['dates'][k2])
                else:label=np.nan;exit_date=pd.NaT
                rec={'market':market,'pos':int(pos),'event_index':int(k),'event_date':et,'signal_date':prev_sig,'exit_date':exit_date,'ticker1':t1,'ticker2':t2,'d_return':s['RETURN'],'d_hybrid_smooth':s['ORIGINAL_SMOOTH'],'d_fusion':s['ORIGINAL_FUSION'],'minvar':float(decisions['weight__B1_MINVAR63_CAP25'].iloc[pos]),'diff_month_log':label,**f}
                frames.append(rec)
    frame=pd.DataFrame(frames).sort_values(['market','pos']).reset_index(drop=True)
    assert len(frame)==180 and (frame.signal_date<frame.event_date).all()
    assert frame.groupby('market').size().to_dict()=={'EU':90,'USA':90}
    return frame,sources

def predictive_forecast(frame):
    lines=[]
    for market,g in frame.groupby('market',sort=True):
        g=g.sort_values('pos').reset_index(drop=True)
        for ix,rec in g.iterrows():
            train=g[(g.pos<=rec.pos-2)&g.diff_month_log.notna()]
            ok=len(train)>=24
            row={'market':market,'pos':int(rec.pos),'event_date':rec.event_date,'n_train':int(len(train)), 'max_train_pos':int(train.pos.max()) if len(train) else -1, 'ridge_mu':0.0,'logit_p':.5,'train_sd_y':np.nan,'mean_only':np.nan,'prob_only':np.nan,'actual':rec.diff_month_log,'fit_available':False}
            if ok:
                assert train.pos.max()<=rec.pos-2
                # Missing indicators are explicit; unknown historical features are imputed exclusively within training cohort.
                trX=train[XCOLS].to_numpy(dtype=float);xt=rec[XCOLS].to_numpy(dtype=float).reshape(1,-1)
                im=SimpleImputer(strategy='median',keep_empty_features=True)
                scl=StandardScaler()
                Xtr=scl.fit_transform(im.fit_transform(trX));Xt=scl.transform(im.transform(xt))
                y=train.diff_month_log.to_numpy(float)
                reg=Ridge(alpha=20.).fit(Xtr,y)
                row['ridge_mu']=float(reg.predict(Xt)[0]);row['mean_only']=float(y.mean());row['train_sd_y']=float(max(y.std(ddof=0),1e-5));row['prob_only']=float(np.mean(y>0));row['fit_available']=True
                if len(np.unique(y>0))>1:
                    logit=LogisticRegression(C=.1,solver='lbfgs',max_iter=1000,random_state=74008)
                    logit.fit(Xtr,(y>0).astype(int));row['logit_p']=float(logit.predict_proba(Xt)[0,1])
                else:row['logit_p']=float(np.mean(y>0))
            lines.append(row)
    forecasts=pd.DataFrame(lines)
    assert len(forecasts)==180
    return forecasts

def policy_weight(row,name):
    if name=='HALF':return .5
    if name=='MINVAR63':return float(row.minvar)
    if name=='FUSION_CONF':return float(np.clip(.5+.25*np.tanh(row.d_fusion/.10),.25,.75))
    if name=='RETURN_CONF':return float(np.clip(.5+.25*np.tanh(row.d_return/.10),.25,.75))
    if name in ('PAIR_RIDGE','PAIR_LOGIT','RISK_PLUS_RIDGE') and not bool(row.fit_available):return float(row.minvar) if name=='RISK_PLUS_RIDGE' else .5
    if name=='PAIR_RIDGE':return float(np.clip(.5+.25*np.tanh(row.ridge_mu/row.train_sd_y),.25,.75))
    if name=='PAIR_LOGIT':return float(.25+.5*row.logit_p)
    if name=='RISK_PLUS_RIDGE':return float(np.clip(row.minvar+.20*np.tanh(row.ridge_mu/row.train_sd_y),.25,.75))
    raise ValueError(name)

def policy_apply(q,ids,w):
    qq={k:v for k,v in q.items()};qq['weights']=q['weights'].copy()
    for pos,k in enumerate(ids):
        kk=int(ids[pos+1]) if pos+1<len(ids) else qq['weights'].shape[1]
        qq['weights'][0,k:kk]=w[pos]
    return qq

def logr(r):
    a=r['nav'][:-1]/r['ledger'][:-1,0]
    assert np.isfinite(a).all() and (a>0).all()
    return np.log(a)

def independent_metrics(x):
    c=float(np.expm1(np.mean(x)*252))
    cum=np.exp(np.cumsum(x)); peak=np.maximum.accumulate(np.r_[1.,cum])
    dd=float(np.min(cum/peak[1:]-1))
    return c,dd

def summary_stats(g):
    ranges={'MAIN':(2021,2024),'2024':(2024,2024),'2025':(2025,2025),'2026_PART':(2026,2026),'FULL':(2019,2026)}
    stats=[]
    for m,dates in ranges.items():
        data=g[ (g.date.dt.year>=dates[0]) & (g.date.dt.year<=dates[1]) ]
        if len(data):
            ret,dd=independent_metrics(data.logr.to_numpy())
            stats.append((m,ret,dd,int(len(data))))
    return stats

def study(frame,predict):
    x=frame.merge(predict.drop(columns=['event_date','actual']),on=['market','pos'],validate='one_to_one')
    assert len(x)==180
    weights=[]
    for _,row in x.iterrows():
        for p in POLICIES:
            w=policy_weight(row,p)
            assert np.isfinite(w) and .25-1e-12<=w<=.75+1e-12
            weights.append({'market':row.market,'event_date':row.event_date,'pos':row.pos,'ticker1':row.ticker1,'ticker2':row.ticker2,'policy':p,'w1':w,'w2':1-w})
    weights=pd.DataFrame(weights)
    evmet=[];corrs=[];predquality=[]
    for market,g in x.groupby('market'):
        mg=g[g.diff_month_log.notna()]
        for period,years in [('MAIN',[2021,2022,2023,2024]),('2024',[2024]),('2025',[2025]),('2026',[2026]),('ALL',list(range(2019,2027)))]:
            seg=mg[mg.event_date.dt.year.isin(years)]
            for feature in ['d_return','d_hybrid_smooth','d_fusion','d_mom21','d_mom63','d_log_vol63','corr63']:
                s=seg[[feature,'diff_month_log']].dropna()
                if len(s)>=5:
                    corrs.append({'market':market,'period':period,'feature':feature,'n':len(s),'spearman':float(s[feature].corr(s.diff_month_log,method='spearman')),'pearson':float(s[feature].corr(s.diff_month_log))})
            pred=seg[seg.fit_available]
            if len(pred):
                y=pred.diff_month_log.to_numpy(float);pr=pred.ridge_mu.to_numpy(float);mean=pred.mean_only.to_numpy(float)
                p=pred.logit_p.to_numpy(float);p0=pred.prob_only.to_numpy(float);hit=(y>0).astype(int)
                predquality.append({'market':market,'period':period,'n':len(pred),'ridge_mse':float(np.mean((y-pr)**2)),'mean_only_mse':float(np.mean((y-mean)**2)),'logit_brier':float(np.mean((hit-p)**2)),'train_frequency_brier':float(np.mean((hit-p0)**2)),'sign_acc':float(np.mean((p>.5)==(hit==1))),'prior_sign_acc':float(np.mean((p0>.5)==(hit==1))),'ridge_spearman':float(pd.Series(pr).corr(pd.Series(y),method='spearman')),'mean_label':float(np.mean(y)),'win_rate_top1':float(np.mean(hit))})
    return x,weights,pd.DataFrame(corrs),pd.DataFrame(predquality)

def run():
    hashes={'OLC16':sha256(ARCH16),'OLC19':sha256(ARCH19),'OLC73':sha256(ARCH73)}
    assert hashes['OLC16']=='ddc79c174afdbacc4060c1dd94b874f745eda3406fbabe6d0b475784322d3df7'
    assert hashes['OLC19']=='3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540'
    assert hashes['OLC73']=='af6fe36e5a2d6f2ea202d48800316ecbae5872c7ca89caf10bd343b1bf9899c6'
    frame,source=build_monthly();pred=predictive_forecast(frame)
    x,weights,assoc,skill=study(frame,pred)
    x.to_csv(R/'OLC74_PAIR_PANEL.csv',index=False)
    weights.to_csv(R/'OLC74_EVENT_WEIGHTS.csv',index=False)
    assoc.to_csv(R/'OLC74_ASSOCIATIONS.csv',index=False)
    skill.to_csv(R/'OLC74_FORECAST_SKILL.csv',index=False)
    for m in MARKETS:
        print('PRE-OUTCOME diagnostic',m, skill[(skill.market==m)&(skill.period=='MAIN')].to_dict('records'),flush=True)
    qa={'hashes':hashes,'source':source,'model_train_lag_events':2,'n_train_fits':int(pred.fit_available.sum()),'fit_maturity_ok':bool((pred.max_train_pos<=pred.pos-2).all()),'score_parity_max':float(np.max(np.abs(frame.d_fusion-(.475*frame.d_return+.525*frame.d_hybrid_smooth)))),'engine_parity':{},'reference_OLC73_logparity':{},'runs':[]}
    prior=pd.read_csv(TOP/'results/OLC73_DAILY_LOGRET.csv.gz')
    prior=prior.set_index(['key','date']).logr
    scorecards=[];annual=[];daily=[]
    for market in MARKETS:
        q=dict(np.load(P/f'inputs/{market}_TOP2_CONTEXT_REVALUE.npz',allow_pickle=False))
        ids=np.flatnonzero(q['events']);events=q['events']
        ds=pd.to_datetime(q['dates'][1:]);a=x[x.market==market].sort_values('pos');assert len(a)==len(ids)
        for policy in POLICIES:
            ww=np.array([policy_weight(row,policy) for row in a.itertuples()],float)
            qq=policy_apply(q,ids,ww)
            for timing in TIMINGS:
                for fee in FEES:
                    key=f'{market}_{policy}_{timing}_{int(fee*10000)}'
                    r=_impl(qq,events,policy='IMMEDIATE' if timing=='IMMEDIATE' else 'DELAY',fraction=1 if timing=='IMMEDIATE' else 3,fee=fee,exposure_timing='PREVIOUS',stop_timing='NOW',stop_friction=.001,ordinary_alarm=False,fast_stop=True,lock_days=3)
                    series=logr(r)
                    assert len(series)==len(ds)
                    f=pd.DataFrame({'date':ds,'market':market,'policy':policy,'timing':timing,'fee':fee,'key':key,'logr':series});daily.append(f)
                    native_metrics=metrics(qq,r)
                    for m in native_metrics:
                        if m['period'] in ('FULL','ACTIVE2021_2024','2024','2025','2026','CRASH2020','2021','2022','2023'):
                            sel=(ds>=m['first_valuation'])&(ds<=m['last_valuation'])
                            c,dd=independent_metrics(series[sel]);assert len(series[sel])==m['n'] and abs(c-m['cagr'])<1e-10 and abs(dd-m['maxdd'])<1e-10,(key,m['period'])
                            scorecards.append({'market':market,'policy':policy,'timing':timing,'fee':fee,'key':key,**m})
                    for yr in sorted(np.unique(ds.year)):
                        vals=series[ds.year==yr]
                        annual.append({'market':market,'policy':policy,'timing':timing,'fee':fee,'year':int(yr),'return':float(np.expm1(vals.sum())),'n':len(vals)})
                    if policy=='HALF' and timing=='IMMEDIATE' and fee==.001:
                        with np.load(N/f'results/paths/{market}_TOP2_CONTEXT_REVALUE_FAST_LOCK3_F10_S10.npz') as old:
                            for col in ['nav','ledger','primary_units','defensive_units','free_cash','targets','risk_trace']:
                                assert np.array_equal(r[col],old[col]),(market,col)
                        qa['engine_parity'][market]='EXACT_7_ARRAYS'
                    if policy in ('HALF','MINVAR63'):
                        oldpolicy='HALF' if policy=='HALF' else 'MINVAR63_CAP25';oldkey=f'{market}_{oldpolicy}_{timing}_{int(fee*10000)}'
                        val=prior.loc[[(oldkey,v.strftime('%Y-%m-%d')) for v in ds]]
                        err=float(np.max(np.abs(series-val.to_numpy())))
                        assert err<1e-13,(key,oldkey,err)
                        qa['reference_OLC73_logparity'][oldkey]=err
                    qa['runs'].append(key)
                    print('REPLAY',key,'MAIN',round(100*[v['cagr'] for v in native_metrics if v['period']=='ACTIVE2021_2024'][0],3),'FULL',round(100*[v['cagr'] for v in native_metrics if v['period']=='FULL'][0],3),flush=True)
    pd.DataFrame(scorecards).to_csv(R/'OLC74_SCORECARD.csv',index=False)
    pd.DataFrame(annual).to_csv(R/'OLC74_ANNUAL.csv',index=False)
    pd.concat(daily,ignore_index=True).to_csv(R/'OLC74_DAILY_LOGRET.csv.gz',index=False)
    qa['replays']=len(qa['runs']);qa['parity_paths']=len(qa['reference_OLC73_logparity']);qa['qa_pass']=qa['replays']==56 and qa['parity_paths']==16 and len(qa['engine_parity'])==2
    assert qa['qa_pass']
    (R/'OLC74_QA.json').write_text(json.dumps(qa,indent=2,default=str))
    print('COMPLETE',qa,flush=True)
if __name__=='__main__':run()