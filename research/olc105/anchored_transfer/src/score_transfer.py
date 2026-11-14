"""Predict only: frozen annual EU Return125, ET/XGB and OLC14 heads.
No candidate outcome enters any fit. Original-source parity is tested separately.
"""
from settings import *
import numpy as np,pandas as pd,joblib,xgboost as xgb,json,hashlib,time
from etf_trader.source_only.kernel import F2D_FEATURES
from etf_trader.ma3.producer import FEATURES_42
import data_transfer as dat
HEAD=BASE/'source/heads14/olc14_fitted_ranking_20261101'
REG=BASE/'source/reg11';RET=BASE/'source/rsi08'
SEEDS=(101,211,307);RSEEDS=(101,202,303);KEY=['signal_date','ticker'];HORIZ=['C21','C42','C63']

def xpredict(path,arr):
    model=xgb.Booster();model.load_model(str(path));model.set_param({'nthread':1})
    return model.predict(xgb.DMatrix(arr,nthread=1))

def prepare(which):
    if which=='PARITY':
        folder=BASE/'source/panels08/parents/olc07_calendar_20261101/phases/P0/results/calendar'
        cp=pd.read_pickle(folder/'EU_COMPACT.pkl');hp=pd.read_pickle(folder/'EU_HYBRID.pkl')
        patch=pd.read_pickle(BASE/'source/panels08/inputs/EU_PATCH.pkl')
        assert cp[KEY].equals(patch[KEY]);cp['rsi14']=patch.rsi14;cp['rsi14_pct']=patch.rsi14_pct
    else:
        cp=pd.read_pickle(ROOT/'data/panels/EU_COMPACT.pkl');hp=pd.read_pickle(ROOT/'data/panels/EU_HYBRID.pkl')
        fs,_=dat.anchored_data();v=np.full(len(cp),np.nan)
        for t,ids in cp.groupby('ticker',sort=False).groups.items():
            f=fs[t];diff=f.Close.diff();up=diff.clip(lower=0).ewm(alpha=1/14,adjust=False,min_periods=14).mean();dn=(-diff.clip(upper=0)).ewm(alpha=1/14,adjust=False,min_periods=14).mean()
            r=100-100/(1+up/dn.replace(0,np.nan));r=r.mask((dn==0)&(up>0),100.).mask((dn==0)&(up==0),50.)
            v[np.asarray(ids,int)]=r.reindex(pd.DatetimeIndex(cp.loc[ids,'source_date'])).to_numpy()
        cp['rsi14']=v;cp['rsi14_pct']=cp.groupby('signal_date').rsi14.rank(pct=True)
    cp=cp[cp.eligible & cp.signal_date.dt.year.between(2019,2026)].sort_values(KEY).reset_index(drop=True)
    hp=hp[hp.signal_date.dt.year.between(2019,2026)].sort_values(KEY).reset_index(drop=True)
    return cp,hp

def run(which):
    cp,hp=prepare(which);retparts=[];hparts=[];parity=[];modelhash={};st=time.time()
    for yr in range(2019,2027):
        c=cp[cp.signal_date.dt.year.eq(yr)].copy();h=hp[hp.signal_date.dt.year.eq(yr)].copy()
        if c.empty or h.empty:continue
        rx=c[F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy(float);hx=h[list(FEATURES_42)].to_numpy(float)
        rr=[];preds={f'{name}_{fam}':[] for name in ['ORIGINAL_P15']+HORIZ for fam in ['ET','XGB']}
        for seed,rs in zip(SEEDS,RSEEDS):
            p=RET/f'fits/EU/R_RSI_DOMAIN/{yr}/RETURN_{rs}.ubj';rr.append(xpredict(p,rx));modelhash[str(p.relative_to(BASE))]=hashlib.sha256(p.read_bytes()).hexdigest()
            for isreg,names,folder in [(True,['ORIGINAL_P15'],REG/f'models/EU/{yr}/{seed}'),(False,HORIZ,HEAD/f'models/EU/{yr}/{seed}')]:
                impfile=folder/'IMPUTER.joblib';imp=joblib.load(impfile);arr=imp.transform(hx)
                modelhash[str(impfile.relative_to(BASE))]=hashlib.sha256(impfile.read_bytes()).hexdigest()
                ref=pd.read_csv(folder/'predictions.csv.gz',parse_dates=['signal_date'],float_precision='round_trip') if which=='PARITY' else None
                for name in names:
                    for fam in ['ET','XGB']:
                        fn=(fam+'_REG' if isreg else name+'_'+fam);path=folder/(fn+('.joblib' if fam=='ET' else '.ubj'))
                        if fam=='ET':
                            model=joblib.load(path);model.n_jobs=1;pr=model.predict(arr)
                        else:pr=xpredict(path,arr)
                        preds[name+'_'+fam].append(pr);modelhash[str(path.relative_to(BASE))]=hashlib.sha256(path.read_bytes()).hexdigest()
                        if which=='PARITY':
                            chk=h[KEY].assign(pred=pr).merge(ref[KEY+[fn]],on=KEY,validate='one_to_one');assert len(chk)==len(h)==len(ref)
                            err=float(abs(chk.pred-chk[fn]).max());assert err<2e-7,(yr,seed,fn,err)
                            parity.append({'year':yr,'seed':seed,'head':fn,'rows':len(chk),'max_abs_error':err})
        a=c[KEY].copy();a['RETURN_RAW']=np.mean(rr,axis=0);retparts.append(a)
        b=h[KEY].copy()
        for key,pp in preds.items():b[key]=np.mean(pp,axis=0)
        hparts.append(b)
        print(which,yr,'rows',len(c),len(h),'seconds',round(time.time()-st,1),flush=True)
    ret=pd.concat(retparts,ignore_index=True);hy=pd.concat(hparts,ignore_index=True)
    ret['RETURN']=ret.groupby('signal_date').RETURN_RAW.rank(pct=True)
    for name in ['ORIGINAL_P15']+HORIZ:
        for fam in ['ET','XGB']:
            col=name+'_'+fam;hy[col+'_RANK']=hy.groupby('signal_date')[col].rank(pct=True)
        hy[name]=.6*hy[name+'_ET_RANK']+.4*hy[name+'_XGB_RANK']
    hy['CUM_FIXED_MAPPED']=.45*hy.C21+.35*hy.C42+.20*hy.C63
    f=ret.merge(hy,on=KEY,how='inner',validate='one_to_one').sort_values(KEY).reset_index(drop=True)
    if which=='PARITY':
        ref=pd.read_csv(RET/'results/EU_R_RSI_DOMAIN_FORECASTS.csv.gz',parse_dates=['signal_date'],float_precision='round_trip')
        j=ret.merge(ref[KEY+['RETURN_RAW','RETURN']],on=KEY,suffixes=('','_ref'),validate='one_to_one')
        err=float(abs(j.RETURN_RAW-j.RETURN_RAW_ref).max());assert err<2e-7,err
        # CSV float32 serialization can affect raw last digits; rank agreement remains a strict test.
        months=sum(g.sort_values(['RETURN','ticker']).ticker.tolist()==g.sort_values(['RETURN_ref','ticker']).ticker.tolist() for _,g in j.groupby('signal_date'))
        assert months==90,(months,err)
        (ROOT/'results/ORIGINAL_HEAD_PARITY.json').write_text(json.dumps({'status':'PASS','hybrid_seed_head_checks':len(parity),'return_monthly_rank_parity':months,'return_raw_max_error':err,'checks':parity},indent=2))
    f.to_pickle(ROOT/f'data/{which}_FORECASTS.pkl');f.to_csv(ROOT/f'results/{which}_FORECASTS.csv.gz',index=False,compression={'method':'gzip','mtime':0})
    (ROOT/f'results/{which}_MODEL_HASHES.json').write_text(json.dumps(modelhash,indent=2))
    print('SCORED',which,len(f),flush=True)
if __name__=='__main__':run(sys.argv[1])
