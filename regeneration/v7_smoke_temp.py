#!/usr/bin/env python3
import argparse, importlib.util, json
from pathlib import Path
import numpy as np, pandas as pd

def load(path,name):
    s=importlib.util.spec_from_file_location(name,str(path)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def full12(logex,window=12):
    a=np.zeros(len(logex),dtype=bool)
    for k in range(len(logex)):
        hist=logex[max(0,k-window):k]
        if len(hist)>=window: a[k]=float(np.mean(hist))>0
    return a

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',required=True);ap.add_argument('--v6',required=True);ap.add_argument('--prod',required=True);ap.add_argument('--data',required=True);ap.add_argument('--trees',type=int,default=60);ap.add_argument('--baskets',type=int,default=20);ap.add_argument('--output',default='V7_SMOKE')
    a=ap.parse_args(); out=Path(a.output); out.mkdir(parents=True,exist_ok=True)
    base=load(Path(a.base),'v7_base'); v6=load(Path(a.v6),'v7_exec'); prod=load(Path(a.prod),'v7_prod')
    base.rolling_downvol=lambda ret,h: np.sqrt(ret.clip(upper=0.0).pow(2).rolling(h,min_periods=h).mean())*np.sqrt(252)
    v6.router_active=full12
    mats=v6.load_mats(Path(a.data))
    dates, compact_raw, compact_frames = prod.build_compact(mats,base)
    compact=base.add_labels(compact_raw,mats['Open'],dates)
    d2, _c_unused, _tail0, D=base.build_features(mats)
    if not pd.DatetimeIndex(d2).equals(pd.DatetimeIndex(dates)): raise RuntimeError('date grid mismatch')
    D=v6.enhance_feature_dictionary(base,mats,dates,D)
    tail=v6.rebuild_tail_long(base,D,dates,mats['Close'].columns)
    tail=base.add_labels(tail,mats['Open'],dates)
    clusters,balance,ari=v6.build_s3b_clusters(mats,dates,base.TICKER_CATEGORY)
    macro,macro_feats=v6.build_macro_panel(base,D,compact,base.TICKER_CATEGORY)
    opp=v6.build_opportunity_panel(base,D,clusters,compact)
    pred,opred,fit_audit,macro_pred=v6.fit_predict(base,compact,tail,macro,macro_feats,opp,range(2017,2027),a.trees)
    pred=pred[pred.signal_date>=v6.BACKTEST_START].copy();opred=opred[opred.signal_date>=v6.BACKTEST_START].copy()
    cal=compact[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date')
    cal=cal[(cal.signal_date>=v6.BACKTEST_START)&cal.signal_date.isin(pred.signal_date.unique())&cal.exit_date.notna()].reset_index(drop=True)
    baskets,_=v6.make_baskets(base,pred,a.baskets)
    idx,EB,ED,ER,active,margin,cond,*_=v6.simulate_all(baskets,pred,opred,clusters,mats,cal)
    rows=[]
    for b in range(len(baskets)):
        for n,x in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
            c,dd,sh,fe=v6.metrics(x,idx); rows.append({'basket':b,'strategy':n,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe})
    res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS.csv',index=False)
    glob=[sorted(pred.ticker.unique())];idxg,Ebg,Edg,Erg,ag,mg,cg,*_=v6.simulate_all(glob,pred,opred,clusters,mats,cal,forced_active=active)
    grows=[]
    for n,x in [('BASE',Ebg[0]),('DIRECT',Edg[0]),('ROUTER',Erg[0])]:
        c,dd,sh,fe=v6.metrics(x,idxg);grows.append({'strategy':n,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe})
    pd.DataFrame(grows).to_csv(out/'GLOBAL.csv',index=False)
    chk=pred[pred.signal_date==pd.Timestamp('2026-06-30')].sort_values('titanium_score',ascending=False).head(5)
    checkpoint={'top':chk[['ticker','titanium_score','compact_rank','tail_rank']].to_dict('records'),'matches_USO_PALL':bool(len(chk)>=2 and chk.iloc[0].ticker=='USO' and chk.iloc[1].ticker=='PALL')}
    base_mean=float(res[res.strategy=='BASE'].cagr.mean());direct_mean=float(res[res.strategy=='DIRECT'].cagr.mean());router_mean=float(res[res.strategy=='ROUTER'].cagr.mean())
    summary={'trees':a.trees,'baskets':a.baskets,'n_months':len(cal),'n_tickers':int(pred.ticker.nunique()),'base_mean_cagr':base_mean,'direct_mean_cagr':direct_mean,'router_mean_cagr':router_mean,'router_active_months':int(active.sum()),'median_s3b_ari':float(ari.ari.median()) if 'ari' in ari else None,'checkpoint':checkpoint}
    (out/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
