#!/usr/bin/env python3
"""ETF Trader V2: independent large-leaf extension on frozen source-only inputs."""
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from xgboost import XGBRanker

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'regeneration'/'campaign'))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder, load_baskets
from etf_trader.source_only.execution import replay
from etf_trader.source_only.statistics import metrics, subpath

CAPS=(31,63,127,255,511)
BSHA='36a45916b5d8191f3ccd206f39bf3fd3f1ed4bcaffd474e352b69c598f2b6a5e'
PERIODS={'development':(2017,2021),'validation':(2022,2023),'confirmation':(2024,2026),'full':(2017,2026)}

def configurations():
    p=dict(k.COMPACT_PARAMS)
    assert p['objective']=='rank:pairwise' and p['max_depth']==4 and p['n_estimators']==360
    cfg={'reference_depth4':p}
    for n in CAPS:
        cfg['leaves_'+str(n)]=dict(p,max_depth=0,grow_policy='lossguide',max_leaves=n)
    return cfg

def fixed_annual_frames(compact,tail,years):
    tail0=tail.drop(columns=[c for c in tail if c.startswith(('fwd_','target_','exit_')) or c in ('entry_date','y_tailmix')])
    macro,mfeatures=k.build_macro_panel(tail0,tail)
    allyears=[];audit=[]
    for yr in years:
        cutoff=pd.Timestamp(yr,1,1)
        valid=compact[k.F2D_FEATURES].notna().sum(axis=1)>=30
        tr=compact[(compact.signal_date>=pd.Timestamp(2012,1,1))&(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()&valid].sort_values(['signal_date','ticker'])
        te=compact[(compact.signal_date.dt.year==yr)&valid].sort_values(['signal_date','ticker'])
        if len(te)==0 or tr.signal_date.nunique()<60:
            audit.append({'year':yr,'status':'SKIP_INSUFFICIENT_DATA','months':int(tr.signal_date.nunique())});continue
        if not tr.exit_date_21.max()<cutoff:raise RuntimeError('immature compact label')
        X=tr[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
        XP=te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
        y=np.rint(100*tr.target_rank_21.to_numpy(float)).astype(int)
        groups=tr.groupby('signal_date',sort=True).size().to_numpy()
        assert groups.sum()==len(tr) and list(X.columns)==list(XP.columns)
        tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12
        tt=tail[(tail.signal_date>=pd.Timestamp(2012,1,1))&(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tv]
        tp=tail[(tail.signal_date.dt.year==yr)&tv][['signal_date','ticker']+k.TAIL_FEATURES]
        mt=macro[(macro.signal_date>=pd.Timestamp(2012,1,1))&(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]
        mp=macro[macro.signal_date.dt.year==yr]
        if tt.empty or mt.empty:raise RuntimeError('missing matured fixed tail or macro training')
        if not tt.exit_date_63.max()<cutoff or not mt.label_exit_date_63.max()<cutoff:raise RuntimeError('immature auxiliary target')
        tailmodel=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.))
        tailmodel.fit(tt[k.TAIL_FEATURES],tt.y_tailmix)
        ts=tp[['signal_date','ticker']].copy()
        ts['tail']=tailmodel.predict(tp[k.TAIL_FEATURES])
        macmodel=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.))
        macmodel.fit(mt[mfeatures],mt.target_rank)
        q=mp[['signal_date','macro_category']].copy()
        q['raw']=macmodel.predict(mp[mfeatures])
        q['z']=q.groupby('signal_date').raw.transform(lambda a:(a-a.mean())/(a.std(ddof=0)+1e-12))
        top=[]
        for dt,g in q.groupby('signal_date'):
            g=g.sort_values(['z','macro_category'],ascending=[False,True])
            if len(g)>1:top.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap':float(g.iloc[0].z-g.iloc[1].z)})
        labels=['signal_date','ticker','entry_date','exit_date','exit_date_21','fwd_ret_21','target_rank_21']
        fixed=te[labels].merge(ts,on=['signal_date','ticker'],validate='one_to_one').merge(pd.DataFrame(top),on='signal_date',validate='many_to_one')
        fixed['macro_category']=fixed.ticker.map(k.TICKER_CATEGORY)
        allyears.append((yr,X,XP,y,groups,te,fixed))
        audit.append({'year':yr,'status':'FIT','train_rows':len(tr),'test_rows':len(te),'train_dates':int(tr.signal_date.nunique()),'max_mature_exit_21':str(tr.exit_date_21.max()),'max_mature_exit_tail_63':str(tt.exit_date_63.max()),'max_mature_exit_macro_63':str(mt.label_exit_date_63.max()),'fit_cutoff':str(cutoff)})
    return allyears,audit

def score_frame(te,fixed,p,name):
    z=te[['signal_date','ticker']].copy()
    z['raw']=p
    z=z.merge(fixed,on=['signal_date','ticker'],validate='one_to_one')
    z['compact_rank']=z.groupby('signal_date').raw.rank(pct=True)
    z['tail_rank']=z.groupby('signal_date')['tail'].rank(pct=True)
    z['mix']=.70*z.compact_rank+.30*z.tail_rank
    z['mix']+=.15*((z.macro_category==z.top_macro)&(z.macro_gap>=.75)&(z.tail_rank>=.8))
    z['score']=z.groupby('signal_date')['mix'].rank(pct=True)
    z['variant']=name
    return z[['variant','signal_date','ticker','entry_date','exit_date','exit_date_21','fwd_ret_21','target_rank_21','raw','score']]

def assess(scores,baskets):
    universe=[];brows=[]
    for (name,date),g in scores.groupby(['variant','signal_date'],sort=True):
        g=g.dropna(subset=['score','fwd_ret_21'])
        if len(g)<10:continue
        g=g.sort_values(['score','ticker'],ascending=[False,True])
        win=g.sort_values(['fwd_ret_21','ticker'],ascending=[False,True]).iloc[0]
        first=g.iloc[0]
        pos=g.ticker.to_list().index(win.ticker)+1
        rho=spearmanr(g.score,g.fwd_ret_21).statistic
        rawrho=spearmanr(g.raw,g.fwd_ret_21).statistic
        raw_sorted=g.sort_values(['raw','ticker'],ascending=[False,True])
        raw_winpos=raw_sorted.ticker.to_list().index(win.ticker)+1
        universe.append({'variant':name,'signal_date':date,'year':pd.Timestamp(date).year,'ic':float(rho),'raw_ic':float(rawrho),'raw_top1_hit':float(raw_sorted.iloc[0].ticker==win.ticker),'raw_top3_capture':float(raw_winpos<=3),'top1_hit':float(first.ticker==win.ticker),'top3_capture':float(pos<=3),'winner_rank':pos,'regret':float(win.fwd_ret_21-first.fwd_ret_21),'selected_return_21':float(first.fwd_ret_21),'selected_excess_21':float(first.fwd_ret_21-g.fwd_ret_21.mean())})
        gg=g.set_index('ticker')
        for bid,basket in enumerate(baskets):
            b=gg.reindex(basket).dropna(subset=['score','fwd_ret_21'])
            if len(b)<2:continue
            b=b.sort_values('score',ascending=False)
            best=b.sort_values('fwd_ret_21',ascending=False).iloc[0]
            pos=b.index.to_list().index(best.name)+1
            raw_order=b.sort_values(['raw','ticker'],ascending=[False,True])
            raw_pick=raw_order.iloc[0]
            brows.append({'variant':name,'signal_date':date,'year':pd.Timestamp(date).year,'basket':bid,'top1':b.iloc[0].name,'raw_top1_hit':float(raw_pick.name==best.name),'raw_selected_excess_21':float(raw_pick.fwd_ret_21-b.fwd_ret_21.mean()),'top1_hit':float(b.iloc[0].name==best.name),'top3_capture':float(pos<=3),'regret':float(best.fwd_ret_21-b.iloc[0].fwd_ret_21),'selected_excess_21':float(b.iloc[0].fwd_ret_21-b.fwd_ret_21.mean())})
    return pd.DataFrame(universe),pd.DataFrame(brows)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--raw',default='etf_trader_raw')
    ap.add_argument('--baskets',default='regeneration/SUPER_GOLD_BASKET_MEMBERSHIP.csv')
    ap.add_argument('--out',default='runs/v2_large_leaf_sweep')
    ap.add_argument('--years',default='2017,2018,2019,2020,2021,2022,2023,2024,2025,2026')
    args=ap.parse_args()
    years=[int(y) for y in args.years.split(',')]
    assert years and set(years)<=set(range(2017,2027))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    h=hashlib.sha256(Path(args.baskets).read_bytes()).hexdigest()
    assert h==BSHA,'canonical basket fingerprint mismatched'
    mats,cats,rawmeta=load_ticker_csv_folder(args.raw)
    assert len(cats)==149
    mats={key:v.loc[v.index>=pd.Timestamp(2011,1,1)] for key,v in mats.items()}
    baskets=load_baskets(args.baskets,cats)
    assert len(baskets)==500 and all(len(b)==24 for b in baskets)
    k.ALL_TICKERS=sorted(cats)
    k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c) for c in sorted(set(cats.values()))}
    dates=k.month_end_dates(mats['Close'].index)
    if len(dates) and dates[-1]==mats['Close'].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats)
    compact=k.add_labels(compact[compact.signal_date.isin(dates)],mats['Open'],dates)
    tail=k.add_labels(tail[tail.signal_date.isin(dates)],mats['Open'],dates)
    contexts,audit=fixed_annual_frames(compact,tail,years)
    config=configurations()
    predictions=[]; tree_audit=[]
    for yr,X,XP,y,groups,te,fixed in contexts:
        for name,param in config.items():
            pred=[]
            for seed in k.COMPACT_SEEDS:
                model=XGBRanker(**param,random_state=seed)
                model.fit(X,y,group=groups,verbose=False)
                if seed==k.COMPACT_SEEDS[0]:
                    # Leaf counts are determined from every fitted tree of the first seed;
                    # other seeds remain part of the unchanged predictive ensemble.
                    counts=[dump.count('"leaf":') for dump in model.get_booster().get_dump(dump_format='json')]
                    if not counts or min(counts)<1:
                        raise RuntimeError('Cannot inspect effective leaf counts')
                    tree_audit.append({'year':yr,'variant':name,'seed':seed,'trees':len(counts),
                        'min_realized_leaves':int(min(counts)),
                        'mean_realized_leaves':float(np.mean(counts)),
                        'p90_realized_leaves':float(np.quantile(counts,.90)),
                        'max_realized_leaves':int(max(counts)),
                        'fraction_at_cap':float(np.mean(np.asarray(counts)==int(param.get('max_leaves',2**int(param['max_depth'])))))})
                pred.append(model.predict(XP))
            f=score_frame(te,fixed,np.mean(pred,axis=0),name)
            predictions.append(f)
            print('FIT_DONE',yr,name,len(f),flush=True)
    if not predictions:raise RuntimeError('NO_FITTED_YEARS')
    scores=pd.concat(predictions,ignore_index=True)
    scores.to_csv(out/'OOS_SCORES.csv',index=False)
    universe,basket=assess(scores,baskets)
    universe.to_csv(out/'UNIVERSE_MONTHLY.csv',index=False)
    basket.to_csv(out/'BASKET_MONTHLY.csv',index=False)
    U=['ic','raw_ic','raw_top1_hit','raw_top3_capture','top1_hit','top3_capture','winner_rank','regret','selected_return_21','selected_excess_21']
    B=['raw_top1_hit','raw_selected_excess_21','top1_hit','top3_capture','regret','selected_excess_21']
    reference=basket[basket.variant=='reference_depth4'][['signal_date','basket','top1']].rename(columns={'top1':'reference_top1'})
    diff=[]
    for name,g in basket.groupby('variant'):
        if name=='reference_depth4':continue
        joined=g.merge(reference,on=['signal_date','basket'],validate='one_to_one')
        diff.append({'variant':name,'n_basket_months':len(joined),'top1_disagreement':float((joined.top1!=joined.reference_top1).mean())})
    # Correct dependence: resample shared monthly observations, NEVER individual
    # basket observations (the 500 baskets heavily overlap).
    paired=[]
    bm=basket.groupby(['variant','signal_date'],as_index=False)[B].mean()
    reference_monthly=bm[bm.variant=='leaves_31'].sort_values('signal_date').set_index('signal_date')
    for name in ['leaves_63','leaves_127','leaves_255','leaves_511','reference_depth4']:
        comp=bm[bm.variant==name].sort_values('signal_date').set_index('signal_date')
        if not comp.index.equals(reference_monthly.index):
            raise RuntimeError('Calendar mismatch in paired bootstrap '+name)
        for metric in ('top1_hit','top3_capture','regret','selected_excess_21','raw_top1_hit'):
            d=(comp[metric]-reference_monthly[metric]).to_numpy(float)
            if not np.isfinite(d).all(): raise RuntimeError('Nonfinite paired metric')
            rng=np.random.default_rng(20261020)
            n=len(d); block=min(6,n); reps=3000
            starts=rng.integers(0,n,size=(reps,int(np.ceil(n/block))))
            indices=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
            means=d[indices].mean(axis=1)
            paired.append({'comparison':name+' minus leaves_31','metric':metric,'months':n,
                'mean_delta':float(d.mean()),'ci95_lower':float(np.quantile(means,.025)),
                'ci95_upper':float(np.quantile(means,.975)),'bootstrap_unit':'shared months, 6-month circular blocks'})
    pd.DataFrame(tree_audit).to_csv(out/'REALIZED_LEAF_COUNTS.csv',index=False)
    pd.DataFrame(paired).to_csv(out/'PAIRED_MONTHLY_BOOTSTRAP.csv',index=False)
    replay_rows=[]
    for name,frame in scores.groupby('variant'):
        try:
            days,e,t=replay(frame[['signal_date','ticker','score']],mats,baskets,cost=.001)
            for period,(a,b) in PERIODS.items():
                mask=(days.year>=a)&(days.year<=b)
                if mask.sum()>1:replay_rows.append({'variant':name,'period':period,**metrics(subpath(e,mask),t[:,mask])})
            print('REPLAY_DONE',name,flush=True)
        except Exception as exc:
            replay_rows.append({'variant':name,'status':'REPLAY_FAILED','error':repr(exc)})
            print('REPLAY_FAILED',name,repr(exc),flush=True)
    pd.DataFrame(replay_rows).to_csv(out/'REPLAY.csv',index=False)
    result={'status':'DONE','model':'ETF Trader V2 Compact21 70% + fixed Tail 30% + fixed macro rule',
        'configs':config,'years_requested':years,'years_fitted':[z[0] for z in contexts],
        'seeds':k.COMPACT_SEEDS,'n_features':len(k.F2D_FEATURES),
        'warmup':'2011-01-01','earliest_training_signal':'2012-01-01','oos_start':2017,
        'raw_etfs':len(cats),'canonical_baskets':500,'basket_sha256':h,
        'raw_source_files':rawmeta,'historical_scores_used_as_train_inputs':False,
        'fit_audit':audit,'realized_leaf_counts':tree_audit,'paired_monthly_bootstrap':paired,'universe_overall':universe.groupby('variant')[U].mean().reset_index().to_dict('records'),
        'universe_yearly':universe.groupby(['variant','year'])[U].mean().reset_index().to_dict('records'),
        'basket_overall':basket.groupby('variant')[B].mean().reset_index().to_dict('records'),
        'basket_yearly':basket.groupby(['variant','year'])[B].mean().reset_index().to_dict('records'),
        'top1_vs_reference':diff,'replay':replay_rows}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2,default=str))
    print('SUMMARY',json.dumps({z:result[z] for z in ('status','years_fitted','universe_overall','basket_overall','top1_vs_reference','realized_leaf_counts')},default=str),flush=True)

if __name__=='__main__':main()
