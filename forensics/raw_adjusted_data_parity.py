#!/usr/bin/env python3
from pathlib import Path
import argparse, json, time
import numpy as np
import pandas as pd
import yfinance as yf

ETF_UNIVERSE={
'C01_US_BROAD_STYLE':['DIA','IJR','SCHD','QQQ','QUAL','RSP','DGRO','IJH','IWF','HDV','MDY','SCHB','IWM','MTUM','SCHX','SPY','IVV','VTI','VO','VB','VUG','VTV','IWD','IWN','SPLV'],
'C02_US_SECTOR_THEME':['PPA','SMH','SOXX','IGV','IHI','KBE','HACK','IYT','KRE','IBB','ICLN','ITA','FDN','TAN','XBI','XLK','XLF','XLE','XLV','XLI','XLY','XLP','XLU','XLB','XRT'],
'C03_DEVELOPED_GLOBAL':['ACWI','EWL','EWP','EWA','EWN','IEFA','EFA','EWH','EWQ','EWC','EWD','EWJ','EWG','EWI','EWU','VEA','VEU','VGK','EWK','EWO','EIRL','EIS','EPOL','ENZL','EPP'],
'C04_EMERGING':['EWS','EWY','FXI','ASHR','INDA','VWO','EWT','IEMG','KWEB','EEM','MCHI','TUR','AAXJ','EWZ','EZA','EIDO','EWM','THD','EPHE','SCHE','DEM','DGS','EPI','PIN','ARGT'],
'C05_BONDS_CASH_CREDIT':['AGG','BIL','EMB','IEF','IEI','LQD','BNDX','HYG','MUB','BND','JNK','SCHP','EDV','SHY','TLT','TIP','SHV','VGSH','VGIT','VGLT','VCIT','VCSH','MBB','BKLN','ANGL'],
'C06_REAL_ASSETS':['COMT','GLD','SLV','GSG','IYR','PPLT','CPER','DBB','VNQ','DBC','GDX','PALL','BNO','DBA','GDXJ','IAU','USO','UNG','DBO','USL','RWO','RWX','WOOD','CORN','URA']}
TICKERS=[t for xs in ETF_UNIVERSE.values() for t in xs]

def download_one(t,start,end):
    x=yf.download(t,start=start,end=end,auto_adjust=False,actions=True,repair=False,progress=False,threads=False,timeout=60,multi_level_index=False)
    if x is None or x.empty: return None
    x.index=pd.to_datetime(x.index).tz_localize(None)
    return x

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--canonical',required=True);ap.add_argument('--output',default='DATA_PARITY');ap.add_argument('--start',default='2005-01-01');ap.add_argument('--end',default='2026-08-04');a=ap.parse_args()
    root=Path(a.canonical);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    old={f:pd.read_parquet(root/f'{f}.parquet') for f in ['OPEN','HIGH','LOW','CLOSE','VOLUME']}
    for x in old.values(): x.index=pd.to_datetime(x.index).tz_localize(None);x.columns=[str(c).upper() for c in x.columns]
    mats={k:[] for k in ['OPEN','HIGH','LOW','CLOSE','VOLUME']}; logs=[]
    for i,t in enumerate(TICKERS,1):
        try:
            x=download_one(t,a.start,a.end)
            if x is None: raise RuntimeError('empty')
            need=['Open','High','Low','Close','Adj Close','Volume']
            miss=[c for c in need if c not in x.columns]
            if miss: raise RuntimeError('missing '+str(miss))
            rawc=pd.to_numeric(x['Close'],errors='coerce')
            adjc=pd.to_numeric(x['Adj Close'],errors='coerce')
            factor=(adjc/rawc.replace(0,np.nan)).replace([np.inf,-np.inf],np.nan)
            for F,c in [('OPEN','Open'),('HIGH','High'),('LOW','Low'),('CLOSE','Close')]:
                s=(pd.to_numeric(x[c],errors='coerce')*factor).rename(t);mats[F].append(s)
            mats['VOLUME'].append(pd.to_numeric(x['Volume'],errors='coerce').rename(t))
            logs.append({'ticker':t,'status':'ok','rows':len(x),'first':x.index.min(),'last':x.index.max(),'factor_min':factor.min(),'factor_max':factor.max()})
        except Exception as e:
            logs.append({'ticker':t,'status':'fail','error':repr(e)})
        if i%25==0: print('downloaded',i,flush=True)
        time.sleep(.05)
    new={k:pd.concat(v,axis=1).sort_index() if v else pd.DataFrame() for k,v in mats.items()}
    for k,x in new.items(): x.to_parquet(out/f'RAW_ACTIONS_ADJ_{k}.parquet',compression='zstd')
    pd.DataFrame(logs).to_csv(out/'DOWNLOAD_LOG.csv',index=False)
    rows=[]
    for k in ['OPEN','HIGH','LOW','CLOSE','VOLUME']:
        A=old[k];B=new[k]
        idx=A.index.intersection(B.index); cols=A.columns.intersection(B.columns)
        aa=A.reindex(index=idx,columns=cols).to_numpy(float);bb=B.reindex(index=idx,columns=cols).to_numpy(float)
        good=np.isfinite(aa)&np.isfinite(bb)&(np.abs(aa)>1e-12)
        rel=np.full_like(aa,np.nan);rel[good]=np.abs(bb[good]/aa[good]-1)
        finite=np.isfinite(rel)
        rows.append({'field':k,'dates':len(idx),'tickers':len(cols),'cells':int(finite.sum()),'mean_abs_rel':float(np.nanmean(rel)),'median_abs_rel':float(np.nanmedian(rel)),'p99_abs_rel':float(np.nanquantile(rel,.99)),'max_abs_rel':float(np.nanmax(rel)),'share_gt_1bp':float(np.nanmean(rel>1e-4)),'share_gt_10bp':float(np.nanmean(rel>1e-3)),'share_gt_1pct':float(np.nanmean(rel>1e-2))})
    cmp=pd.DataFrame(rows);cmp.to_csv(out/'PARITY_SUMMARY.csv',index=False)
    payload={'requested':len(TICKERS),'success':sum(r['status']=='ok' for r in logs),'failed':[r['ticker'] for r in logs if r['status']!='ok'],'comparisons':rows}
    (out/'PARITY_SUMMARY.json').write_text(json.dumps(payload,indent=2,default=str));print(json.dumps(payload,indent=2,default=str))
if __name__=='__main__':main()
