from __future__ import annotations
from pathlib import Path
import sys, json, hashlib, importlib.util, shutil
import numpy as np
import pandas as pd
from numba import njit

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'HYBRID25_STAGE19_ARCHITECTURE_20260925'; OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'vendor'/'etf_trader_v2'/'src'))
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer, ddfirst, v6, highcagr24

RAW=ROOT/'etf_cleanroom'/'raw_ticker_csv'
PRED=ROOT/'stage15_unpack'/'sourceonly'/'clean_run'/'ENSEMBLE_TAIL_OOS.csv'
TIT=ROOT/'stage15_unpack'/'sourceonly'/'clean_run'/'titanium'/'TIT_R_SOURCE_ONLY.csv'
PATH=ROOT/'stage15_unpack'/'sourceonly'/'clean_run'/'PATH.npz'


def metrics(E, mask):
    mask=np.asarray(mask,bool)
    lr=np.diff(np.log(np.column_stack([np.ones(E.shape[0]),E])),axis=1)[:,mask]
    r=np.expm1(lr); n=lr.shape[1]
    c=np.expm1(lr.sum(axis=1)*252/n)
    eq=np.exp(np.cumsum(lr,axis=1)); pk=np.maximum.accumulate(np.column_stack([np.ones(E.shape[0]),eq]),axis=1)[:,1:]
    dd=(eq/pk-1).min(axis=1); sd=r.std(axis=1,ddof=1)
    sh=np.divide(r.mean(axis=1)*np.sqrt(252),sd,out=np.zeros_like(sd),where=sd>0)
    return dict(cagr=float(c.mean()),median_cagr=float(np.median(c)),p10_cagr=float(np.quantile(c,.1)),p05_cagr=float(np.quantile(c,.05)),maxdd=float(dd.mean()),p10dd=float(np.quantile(dd,.1)),p05dd=float(np.quantile(dd,.05)),worst=float(dd.min()),sharpe=float(sh.mean()))


def score_matrix(pred,cal,tickers):
    dates=pd.DatetimeIndex(cal.signal_date)
    def mat(col):
        return pred.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    B=mat('BASE'); ET=mat('ET_RANK'); X=mat('XGB_RANK')
    T=.6*ET+.4*X
    l1=np.vstack([T[:1],T[:-1]]); l2=np.vstack([T[:1],T[:1],T[:-2]])
    sm=.4*T+.3*l1+.3*l2
    return .475*B+.525*np.power(np.clip(sm,0,1),1.10)


def monthly_top(score,basket_matrix,basket_valid,k):
    S=np.where(basket_valid,score[basket_matrix],-np.inf)
    order=np.argsort(-S,axis=1)[:,:k]
    vals=np.take_along_axis(S,order,axis=1)
    ids=np.take_along_axis(basket_matrix,order,axis=1)
    return ids.astype(np.int16), vals


def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def pred_matrices(pred, cal, tickers):
    dates=pd.DatetimeIndex(cal.signal_date)
    def mat(col):
        return pred.pivot(index='signal_date',columns='ticker',values=col).reindex(index=dates,columns=tickers).to_numpy(float)
    return {c:mat(c) for c in ['BASE','ET_RANK','XGB_RANK']}


def daily_monthly_state(score, pm, cal, ds, BM, BOK):
    B=BM.shape[0]; D=len(ds)
    s1=np.ones((B,D),float); agree_models=np.zeros((B,D),bool); agree_all=np.zeros((B,D),bool)
    for m,row in enumerate(cal.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date))); e=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=D or e<=a: continue
        ids,vals=monthly_top(score[m],BM,BOK,2)
        top1=ids[:,0]; top2=ids[:,1]
        et1=pm['ET_RANK'][m,top1]; et2=pm['ET_RANK'][m,top2]
        x1=pm['XGB_RANK'][m,top1]; x2=pm['XGB_RANK'][m,top2]
        b1=pm['BASE'][m,top1]; b2=pm['BASE'][m,top2]
        am=(et1>et2)&(x1>x2)
        aa=am&(b1>b2)
        s1[:,a:e]=vals[:,0,None]
        agree_models[:,a:e]=am[:,None]
        agree_all[:,a:e]=aa[:,None]
    return s1,agree_models,agree_all


def risk_gross_transform(ddgross):
    g=np.asarray(ddgross,float).copy()
    g[np.isclose(g,.95)]=1.0
    g[np.isclose(g,.75)]=highcagr24.C4_GROSS
    g[g<=.251]=highcagr24.SEVERE_GROSS
    return g


def confidence_weights(base, g_risk, agree_models, agree_all, mode):
    w=np.asarray(base.weight1,float).copy()
    if mode=='current':
        w[(g_risk[None,:]>=.999)&(base.margin>=highcagr24.TOP1_MARGIN)]=1.0
    elif mode=='smooth':
        pass
    elif mode=='hard_independent':
        w[base.margin>=highcagr24.TOP1_MARGIN]=1.0
    elif mode=='models_agree':
        w[(base.margin>=highcagr24.TOP1_MARGIN)&agree_models]=1.0
    elif mode=='all_agree':
        w[(base.margin>=highcagr24.TOP1_MARGIN)&agree_all]=1.0
    elif mode=='current_plus_models_riskoff':
        w[(g_risk[None,:]>=.999)&(base.margin>=highcagr24.TOP1_MARGIN)]=1.0
        w[(g_risk[None,:]<.999)&(base.margin>=highcagr24.TOP1_MARGIN)&agree_models]=1.0
    elif mode=='current_plus_allagree_riskoff':
        w[(g_risk[None,:]>=.999)&(base.margin>=highcagr24.TOP1_MARGIN)]=1.0
        w[(g_risk[None,:]<.999)&(base.margin>=highcagr24.TOP1_MARGIN)&agree_all]=1.0
    else:
        raise ValueError(mode)
    return w


def opportunity_cap(top1_score):
    # No return-fitted threshold: final producer score is percentile-like [0,1].
    # Do not de-risk if the selected ETF score is >= .80; below .80, linearly
    # cap gross from 1.00 down to .75 at score=.60 or lower.
    weakness=np.clip((.80-np.asarray(top1_score,float))/.20,0,1)
    return 1.0-.25*weakness


def shock_caps(close_full, ds, d1, d2, weight1, base_cap=.80, severe_cap=.66):
    """Basket-specific Stage7-style shock translated to risk only.

    Event: current top1 close-to-close return <= -3 * prior 21-session sigma.
    Wait two confirmation closes, act at the next open (t+3). Cap applies from
    action open through the current allocation spell. <= -4 sigma uses severe cap.
    No ETF switch is performed and V6 selector is unchanged.
    """
    close=close_full.astype(float)
    r=close.pct_change(fill_method=None)
    sig=r.rolling(21,min_periods=21).std().shift(1)
    rr=r.reindex(ds).to_numpy(float); ss=sig.reindex(ds).to_numpy(float)
    B,D=d1.shape; caps=np.ones((B,D),float); events=[]
    for b in range(B):
        k=1
        while k<D-3:
            leader=int(d1[b,k])
            if leader<0 or not np.isfinite(rr[k,leader]) or not np.isfinite(ss[k,leader]) or ss[k,leader]<=0:
                k+=1; continue
            z=rr[k,leader]/ss[k,leader]
            if z<=-3.0:
                action=k+3
                if action<D and np.all(d1[b,k:action+1]==leader):
                    end=action+1
                    while end<D and d1[b,end]==leader and d1[b,end]>=0:
                        if d2[b,end]!=d2[b,action] or abs(weight1[b,end]-weight1[b,action])>1e-12:
                            break
                        end+=1
                    cap=severe_cap if z<=-4.0 else base_cap
                    caps[b,action:end]=np.minimum(caps[b,action:end],cap)
                    events.append((b,k,action,end,leader,float(z),float(cap)))
                k=action+1
            else:
                k+=1
    return caps,pd.DataFrame(events,columns=['basket','shock_idx','action_idx','end_idx','leader','z','cap'])


@njit(cache=False)
def simulate_arch(
    d1,d2,wg,O,L,C,PC,gap,ud1,uneg,UH,SA,bil,shv,G2,GALT,ALT,use_alt,
    cost=.001,stop=.055,slip=.001,
):
    B,D=d1.shape
    E=np.ones((B,D)); T=np.zeros((B,D)); X=np.ones((B,D)); AW=np.zeros((B,D))
    for bb in range(B):
        t1=-1;t2=-1;at=-1;u1=0.;u2=0.;au=0.;bu=0.;su=0.;free=0.;pw1=-1.;pf=-1.;paw=-1.;cd=0
        for k in range(D):
            val=free
            if t1>=0 and u1: val+=u1*O[k,t1]
            if t2>=0 and u2: val+=u2*O[k,t2]
            if at>=0 and au: val+=au*O[k,at]
            if bu: val+=bu*O[k,bil]
            if su: val+=su*O[k,shv]
            if k==0 and val==0: val=1.
            if k==D-1:
                E[bb,k]=val; X[bb,k]=min(1.,G2[bb,k]); break
            nt1=d1[bb,k];nt2=d2[bb,k];w1=wg[bb,k]
            if nt2==nt1:w1=1.
            p1=False;p2=False;sysm=False;basef=1.
            if nt1<0:
                basef=0.
            else:
                p1=UH[k,nt1] or SA[k,nt1]
                if nt2>=0:p2=UH[k,nt2] or SA[k,nt2]
                g1=gap[k,nt1];g2=gap[k,nt2] if nt2>=0 else g1
                pg=w1*g1+(1-w1)*g2
                sysm=((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))
                if sysm: basef=.25;cd=3
                elif cd>0: basef=.25;cd-=1
            f=min(basef,G2[bb,k]); rw1=f*w1;rw2=f*(1-w1);cw=1-f
            nat=-1;aw=0.
            if use_alt and ALT[bb,k]>=0:
                nat=int(ALT[bb,k]); gcash=max(0.,1.-GALT[k]); aw=min(cw,gcash)
            cashw=cw-aw
            reb=((t1!=nt1) or (t2!=nt2) or (at!=nat) or abs(pw1-w1)>1e-12 or abs(pf-f)>1e-12 or abs(paw-aw)>1e-12 or free>1e-14 or k==0)
            if reb:
                c1=u1*O[k,t1]/val if t1>=0 and u1 else 0.;c2=u2*O[k,t2]/val if t2>=0 and u2 else 0.;ca=au*O[k,at]/val if at>=0 and au else 0.;cb=bu*O[k,bil]/val if bu else 0.;cs=su*O[k,shv]/val if su else 0.;cf=free/val if val>0 else 0.
                tv=.5*(abs(cf)+abs(cb-cashw*.5)+abs(cs-cashw*.5));tv+=.5*((abs(c1)+rw1) if t1!=nt1 else abs(c1-rw1));tv+=.5*((abs(c2)+rw2) if t2!=nt2 else abs(c2-rw2));tv+=.5*((abs(ca)+aw) if at!=nat else abs(ca-aw))
                val*=1-cost*tv;T[bb,k]=tv;t1=nt1;t2=nt2;at=nat
                u1=rw1*val/O[k,t1] if t1>=0 and rw1>0 else 0.;u2=rw2*val/O[k,t2] if t2>=0 and rw2>0 else 0.;au=aw*val/O[k,at] if at>=0 and aw>0 else 0.;bu=cashw*.5*val/O[k,bil];su=cashw*.5*val/O[k,shv];free=0.;pw1=w1;pf=f;paw=aw
            if t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55):
                sp=PC[k,t1]*(1-stop);fill=O[k,t1] if O[k,t1]<=sp else (sp*(1-slip) if L[k,t1]<=sp else 0.)
                if fill>0:free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)
            if t2>=0 and u2>0 and p2 and (sysm or ud1[k]>=.55):
                sp=PC[k,t2]*(1-stop);fill=O[k,t2] if O[k,t2]<=sp else (sp*(1-slip) if L[k,t2]<=sp else 0.)
                if fill>0:free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)
            nv=free
            if t1>=0 and u1:nv+=u1*O[k+1,t1]
            if t2>=0 and u2:nv+=u2*O[k+1,t2]
            if at>=0 and au:nv+=au*O[k+1,at]
            if bu:nv+=bu*O[k+1,bil]
            if su:nv+=su*O[k+1,shv]
            E[bb,k]=nv;X[bb,k]=f;AW[bb,k]=aw
    return E,T,X,AW


def basket_boot_delta(Ea,Eb,mask,nboot=3000,seed=101):
    mask=np.asarray(mask,bool)
    def cagr(E):
        lr=np.diff(np.log(np.column_stack([np.ones(E.shape[0]),E])),axis=1)[:,mask]; n=lr.shape[1]
        return np.expm1(lr.sum(axis=1)*252/n)
    a,b=cagr(Ea),cagr(Eb);d=a-b;rng=np.random.default_rng(seed);means=np.empty(nboot);n=len(d)
    for i in range(nboot):means[i]=d[rng.integers(0,n,n)].mean()
    return {'mean':float(d.mean()),'positive_rate':float((d>0).mean()),'lo':float(np.quantile(means,.025)),'hi':float(np.quantile(means,.975))}


def main():
    mats,cats,manifest=load_ticker_csv_folder(RAW); tickers=list(map(str,mats['Open'].columns));ti={t:i for i,t in enumerate(tickers)}
    bp=ROOT/'stage15_unpack'/'sourceonly'/'source'/'etf_trader'/'source_only'/'baskets.py';sp=importlib.util.spec_from_file_location('cert_baskets',bp);bm=importlib.util.module_from_spec(sp);sp.loader.exec_module(bm)
    membership=bm.build_canonical_baskets(pd.read_csv(RAW/'universe.csv'),tickers);BM,BOK=producer.basket_arrays(membership,tickers,n_baskets=500)
    tit=pd.read_csv(TIT,parse_dates=['signal_date','entry_date','exit_date']);cal=tit[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date').reset_index(drop=True)
    pred=pd.read_csv(PRED,parse_dates=['signal_date']);score=score_matrix(pred,cal,tickers);pm=pred_matrices(pred,cal,tickers)
    Odf=mats['Open'].reindex(columns=tickers).ffill().bfill();Ldf=mats['Low'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index);Cdf=mats['Close'].reindex(columns=tickers).ffill().bfill().reindex(Odf.index)
    end=pd.Timestamp(cal.exit_date.max());start=pd.Timestamp(cal.entry_date.min());Odf=Odf.loc[:end];Ldf=Ldf.reindex(Odf.index);Cdf=Cdf.reindex(Odf.index);st=int(Odf.index.get_loc(start));en=int(Odf.index.get_loc(end));ds=Odf.index[st:en+1]
    ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float);g_risk=risk_gross_transform(ddgross)
    ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf);O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[k][st:en+1] for k in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]
    base=producer.allocations_from_score(score,cal,ds,BM,BOK,continuous=True)
    s6=v6.build_v6_state(Cdf.loc[ds,tickers],base.d1,base.d2,base.weight1,ddgross)
    s1,agree_models,agree_all=daily_monthly_state(score,pm,cal,ds,BM,BOK)
    opp=opportunity_cap(s1)
    shock,event_df=shock_caps(Cdf.reindex(columns=tickers),ds,base.d1,base.d2,base.weight1)
    event_df['shock_date']=event_df.shock_idx.map(lambda x:str(ds[int(x)].date()));event_df['action_date']=event_df.action_idx.map(lambda x:str(ds[int(x)].date()));event_df['leader_ticker']=event_df.leader.map(lambda x:tickers[int(x)])
    event_df.to_csv(OUT/'SHOCK_EVENTS.csv',index=False)
    periods={'y2017':(ds>=pd.Timestamp('2017-01-01'))&(ds<pd.Timestamp('2018-01-01')),'dev_2018_2020':(ds>=pd.Timestamp('2018-01-01'))&(ds<pd.Timestamp('2021-01-01')),'rep_2021_2022':(ds>=pd.Timestamp('2021-01-01'))&(ds<pd.Timestamp('2023-01-01')),'diag_2023_2026':ds>=pd.Timestamp('2023-01-01'),'hist_2017_2022':ds<pd.Timestamp('2023-01-01'),'full':np.ones(len(ds),bool)}
    ghb,wb=highcagr24.apply_highcagr24(ddgross,base.weight1,base.margin)
    Eb,Tb,_,_=v6.simulate_with_alt(base.d1,base.d2,wb,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],ghb,s6.alt_idx,True,.001)
    Gbase=np.tile(ghb,(BM.shape[0],1));Ep,Tp,_,_=simulate_arch(base.d1,base.d2,wb,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],Gbase,ghb,s6.alt_idx,True,.001)
    parity={'equity_max_abs_diff':float(np.max(np.abs(Ep-Eb))),'turnover_max_abs_diff':float(np.max(np.abs(Tp-Tb)))}
    if parity['equity_max_abs_diff']>1e-10 or parity['turnover_max_abs_diff']>1e-10:raise RuntimeError(parity)
    cached=np.load(PATH,allow_pickle=True); parity['certified_equity_max_abs_diff']=float(np.max(np.abs(Eb-cached['equity'])))

    policies=[];equities={};turns={}
    def run(name,conf_mode,use_opp=False,use_shock=False):
        w=confidence_weights(base,g_risk,agree_models,agree_all,conf_mode)
        G=np.tile(g_risk,(BM.shape[0],1))
        if use_opp:G=np.minimum(G,opp)
        if use_shock:G=np.minimum(G,shock)
        E,T,X,AW=simulate_arch(base.d1,base.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti['BIL'],ti['SHV'],G,g_risk,s6.alt_idx,True,.001)
        equities[name]=E;turns[name]=T
        row={'policy':name,'confidence':conf_mode,'opportunity':use_opp,'shock_risk':use_shock,'turnover_ann':float(T.mean()*252),'mean_gross':float(X.mean()),'hard_top1_rate':float((w>=.999999).mean()),'opp_binding_rate':float((opp<g_risk[None,:]-1e-12).mean()) if use_opp else 0.0,'shock_binding_rate':float((shock<g_risk[None,:]-1e-12).mean()) if use_shock else 0.0}
        for p,m in periods.items():
            mm=metrics(E,m)
            for k,v in mm.items():row[f'{p}_{k}']=v
        policies.append(row)

    run('BASELINE_CURRENT','current',False,False)
    run('ORTHO_SMOOTH','smooth',False,False)
    run('ORTHO_HARD_INDEPENDENT','hard_independent',False,False)
    run('CONF_MODELS_AGREE','models_agree',False,False)
    run('CONF_ALL_AGREE','all_agree',False,False)
    run('BASELINE_PLUS_OPPORTUNITY','current',True,False)
    run('BASELINE_PLUS_SHOCK_RISK','current',False,True)
    run('ORTHO_SMOOTH_PLUS_OPP','smooth',True,False)
    run('ORTHO_SMOOTH_PLUS_SHOCK','smooth',False,True)
    run('ARCH19_FULL','models_agree',True,True)
    run('RISKOFF_HARD_MODELS','current_plus_models_riskoff',False,False)
    run('RISKOFF_HARD_ALLAGREE','current_plus_allagree_riskoff',False,False)
    run('RISKOFF_HARD_ALL_PLUS_OPP','hard_independent',True,False)
    run('RISKOFF_HARD_MODELS_PLUS_OPP','current_plus_models_riskoff',True,False)

    res=pd.DataFrame(policies); b=res[res.policy=='BASELINE_CURRENT'].iloc[0]
    for p in periods:
        for k in ['cagr','maxdd','sharpe','p05_cagr','worst']:
            res[f'{p}_delta_{k}']=res[f'{p}_{k}']-float(b[f'{p}_{k}'])
    elig=res[(res.dev_2018_2020_cagr>=b.dev_2018_2020_cagr-.005)&(res.dev_2018_2020_maxdd>=b.dev_2018_2020_maxdd-.005)].copy()
    selected=elig.sort_values(['dev_2018_2020_sharpe','dev_2018_2020_p05_cagr','dev_2018_2020_cagr'],ascending=False).iloc[0]
    res['selected_dev']=res.policy.eq(selected.policy);res.to_csv(OUT/'POLICY_SCORECARD.csv',index=False)

    ann=[]
    names=list(dict.fromkeys(['BASELINE_CURRENT',str(selected.policy),'ARCH19_FULL','BASELINE_PLUS_SHOCK_RISK','CONF_MODELS_AGREE','ORTHO_HARD_INDEPENDENT','RISKOFF_HARD_MODELS','RISKOFF_HARD_ALLAGREE','RISKOFF_HARD_ALL_PLUS_OPP','RISKOFF_HARD_MODELS_PLUS_OPP','BASELINE_PLUS_OPPORTUNITY']))
    for name in names:
        E=equities[name]
        for y in range(2017,2027):
            m=(ds>=pd.Timestamp(f'{y}-01-01'))&(ds<pd.Timestamp(f'{y+1}-01-01'))
            if m.sum()<10:continue
            mm=metrics(E,m);ann.append({'policy':name,'year':y,**mm})
    pd.DataFrame(ann).to_csv(OUT/'ANNUAL.csv',index=False)

    boots=[]
    for name in list(dict.fromkeys([str(selected.policy),'ARCH19_FULL','BASELINE_PLUS_SHOCK_RISK','CONF_MODELS_AGREE','ORTHO_HARD_INDEPENDENT','RISKOFF_HARD_MODELS','RISKOFF_HARD_ALLAGREE','RISKOFF_HARD_ALL_PLUS_OPP','RISKOFF_HARD_MODELS_PLUS_OPP','BASELINE_PLUS_OPPORTUNITY'])):
        for p,m in periods.items():
            if p=='full':continue
            x=basket_boot_delta(equities[name],Eb,m)
            boots.append({'policy':name,'period':p,**x})
    pd.DataFrame(boots).to_csv(OUT/'PAIRED_BASKET_BOOTSTRAP.csv',index=False)


if __name__=='__main__':
    main()
