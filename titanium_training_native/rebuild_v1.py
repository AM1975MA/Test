#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path


def replace_one(text: str, old: str, new: str, label: str) -> str:
    n = text.count(old)
    if n != 1:
        raise RuntimeError(f"{label}: expected exactly one patch site, found {n}")
    return text.replace(old, new)


def patch_runner(src: Path, dst: Path) -> str:
    text = src.read_text()

    text = replace_one(
        text,
        "models_dir.mkdir(parents=True,exist_ok=True); params=dict(objective='rank:pairwise',eval_metric='ndcg',n_estimators=60,max_depth=4,learning_rate=0.05,min_child_weight=20,subsample=0.80,colsample_bytree=0.75,reg_lambda=12.0,reg_alpha=0.2,tree_method='hist',n_jobs=2,verbosity=0)",
        "models_dir.mkdir(parents=True,exist_ok=True); params=dict(base.COMPACT_PARAMS);params['n_estimators']=n_estimators;params['n_jobs']=2",
        "compact params",
    )
    text = replace_one(
        text,
        "tr=compact[(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_21.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])",
        "tr=compact[(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()].sort_values(['signal_date','ticker']);te=compact[compact.signal_date.dt.year==year].sort_values(['signal_date','ticker'])",
        "compact monthly label maturity",
    )
    text = replace_one(
        text,
        "groups=tr.groupby('signal_date',sort=True).size().tolist();y=np.minimum(4,np.floor(tr.target_rank_21.to_numpy(float)*5.0)).astype(int);seed_parts=[]",
        "groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int);seed_parts=[]",
        "compact relevance",
    )
    text = replace_one(
        text,
        "mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.cat_top2_mean_rank.notna()];mte=macro[macro.signal_date.dt.year==year]",
        "mtr=macro[(macro.signal_date<cutoff)&(pd.to_datetime(macro.macro_label_exit_date_63)<cutoff)&macro.cat_top2_mean_rank.notna()];mte=macro[macro.signal_date.dt.year==year]",
        "macro explicit maturity",
    )
    text = replace_one(
        text,
        "pred['macro_category']=pred.ticker.map(base.TICKER_CATEGORY);pred=pred.merge(pd.DataFrame(tops),on='signal_date',how='left');pred['macro_bonus']=np.where((pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.titanium_score_pre_macro>=.80),.15,0.0);pred['titanium_score']=pred.titanium_score_pre_macro+pred.macro_bonus",
        "pred['macro_category']=pred.ticker.map(base.TICKER_CATEGORY);pred=pred.merge(pd.DataFrame(tops),on='signal_date',how='left');pred['macro_bonus']=np.where((pred.macro_category==pred.top_macro)&(pred.macro_gap_z>=.75)&(pred.titanium_score_pre_macro>=.80),.15,0.0);pred['titanium_score']=pred.titanium_score_pre_macro+pred.macro_bonus;pred['TIT_R']=pred.groupby('signal_date').titanium_score.rank(pct=True,method='average')",
        "TIT_R after macro",
    )
    text = replace_one(
        text,
        "opp_rows.append(oq);audit.append({'year':year,'compact_train_rows':len(tr),'compact_train_dates':tr.signal_date.nunique(),'tail_train_rows':len(ttr),'macro_train_rows':len(mtr),'opp_rows_before_cutoff':len(opp[opp.signal_date<cutoff])})",
        "opp_rows.append(oq);audit.append({'year':year,'cutoff':str(cutoff.date()),'compact_train_rows':len(tr),'compact_train_dates':tr.signal_date.nunique(),'compact_max_exit':str(pd.to_datetime(tr.exit_date).max().date()) if len(tr) else None,'tail_train_rows':len(ttr),'tail_max_exit63':str(pd.to_datetime(ttr.exit_date_63).max().date()) if len(ttr) else None,'macro_train_rows':len(mtr),'macro_max_exit63':str(pd.to_datetime(mtr.macro_label_exit_date_63).max().date()) if len(mtr) else None,'opp_rows_before_cutoff':len(opp[opp.signal_date<cutoff]),'opp_max_exit21':str(pd.to_datetime(opp[(opp.signal_date<cutoff)&(opp.label_exit_date_21<cutoff)].label_exit_date_21).max().date()) if len(opp[(opp.signal_date<cutoff)&(opp.label_exit_date_21<cutoff)]) else None})",
        "fit maturity audit",
    )

    anchor = "def package(out:Path,base_src:Path,v5_src:Path):"
    if text.count(anchor) != 1:
        raise RuntimeError("package anchor not unique")
    helper = '''def load_fixture_baskets(path:Path,n:int):
    m=pd.read_csv(path)
    need={'basket','ticker'}
    if not need.issubset(m.columns): raise RuntimeError(f'Basket fixture missing {need-set(m.columns)}')
    groups=[tuple(g.sort_values('ticker').ticker.astype(str).tolist()) for _,g in m.groupby('basket',sort=True)]
    if len(groups)<n: raise RuntimeError(f'Basket fixture has {len(groups)} baskets, requested {n}')
    groups=groups[:n]
    if any(len(x)!=24 for x in groups): raise RuntimeError('Frozen validation fixture must have 24 tickers per basket')
    return groups


def period_metrics_500(idx,EB,ED,ER,v5):
    periods={'D1':(2017,2019),'D2':(2020,2022),'DEV':(2017,2022),'HOLD':(2023,9999),'FULL':(2017,9999)}
    rows=[]
    years=pd.DatetimeIndex(idx).year
    for period,(lo,hi) in periods.items():
        pos=np.flatnonzero((years>=lo)&(years<=hi))
        if len(pos)<2: continue
        sl=slice(pos[0],pos[-1]+1); ix=pd.DatetimeIndex(idx)[sl]
        for b in range(EB.shape[0]):
            for name,arr in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
                q=np.asarray(arr[sl],float);q=q/q[0]
                c,dd,sh,fe=v5.metrics(q,ix)
                rows.append({'period':period,'basket':b,'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe})
    detail=pd.DataFrame(rows)
    detail['calmar']=detail.cagr/(-detail.maxdd.replace(0,np.nan))
    score=detail.groupby(['period','strategy'],as_index=False).agg(cagr=('cagr','mean'),maxdd=('maxdd','mean'),sharpe=('sharpe','mean'),calmar=('calmar','mean'))
    return detail,score


'''
    text = text.replace(anchor, helper + anchor)

    text = replace_one(
        text,
        "baskets,cats=v5.make_baskets(base,pred,args.n_baskets);idx,EB,ED,ER,active,margin,cond,bs,bw,ds,dw=v5.simulate_all(baskets,pred,opred,clusters,mats,cal);rows=[]",
        "baskets=load_fixture_baskets(Path(args.data_dir)/'BASKET_MEMBERSHIP_500.csv',args.n_baskets);cats={};idx,EB,ED,ER,active,margin,cond,bs,bw,ds,dw=v5.simulate_all(baskets,pred,opred,clusters,mats,cal);rows=[]",
        "fixed basket validation fixture",
    )
    text = replace_one(
        text,
        "res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS_500.csv',index=False);pd.DataFrame([{'basket':b,'ticker':t,'category':base.TICKER_CATEGORY.get(t)} for b,u in enumerate(baskets) for t in u]).to_csv(out/'BASKET_MEMBERSHIP_500.csv',index=False)",
        "res=pd.DataFrame(rows);res.to_csv(out/'BASKET_RESULTS_500.csv',index=False);pd.DataFrame([{'basket':b,'ticker':t,'category':base.TICKER_CATEGORY.get(t)} for b,u in enumerate(baskets) for t in u]).to_csv(out/'BASKET_MEMBERSHIP_500.csv',index=False);period_detail,period_score=period_metrics_500(idx,EB,ED,ER,v5);period_detail.to_csv(out/'PER_BASKET_PERIOD_METRICS.csv',index=False);period_score.to_csv(out/'PERIOD_SCORECARD_500.csv',index=False)",
        "period scorecards",
    )
    text = replace_one(
        text,
        "chk=pred[pred.signal_date==pd.Timestamp('2026-06-30')].sort_values('titanium_score',ascending=False).head(5)",
        "chk=pred[pred.signal_date==pd.Timestamp('2026-06-30')].sort_values(['TIT_R','titanium_score'],ascending=False).head(5)",
        "checkpoint TIT_R",
    )
    text = replace_one(
        text,
        "'compact_trees':60,'compact_historical_params':True,'compact_target':'fwd_ret_21','compact_relevance_bins':5",
        "'compact_trees':args.n_estimators,'compact_historical_params':False,'compact_target':'fwd_ret_monthly','compact_relevance':'rank_pct_x100_round','concentration_margin_score':'TIT_R','basket_validation_fixture':'BASKET_MEMBERSHIP_500.csv'",
        "manifest",
    )

    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def patch_execution(src: Path, dst: Path) -> str:
    text = src.read_text()
    text = replace_one(
        text,
        "pred_by={pd.Timestamp(d):g.sort_values('titanium_score',ascending=False) for d,g in pred.groupby('signal_date')}",
        "pred_by={pd.Timestamp(d):g.sort_values(['TIT_R','titanium_score'],ascending=False) for d,g in pred.groupby('signal_date')}",
        "selection by TIT_R",
    )
    text = replace_one(
        text,
        "m=float(r1.titanium_score-r2.titanium_score);margin[b,k]=m",
        "m=float(r1.TIT_R-r2.TIT_R);margin[b,k]=m",
        "concentration margin by TIT_R",
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--runner-input', required=True)
    ap.add_argument('--execution-input', required=True)
    ap.add_argument('--runner-output', required=True)
    ap.add_argument('--execution-output', required=True)
    args = ap.parse_args()
    rs = patch_runner(Path(args.runner_input), Path(args.runner_output))
    es = patch_execution(Path(args.execution_input), Path(args.execution_output))
    print('runner_sha256', rs)
    print('execution_sha256', es)


if __name__ == '__main__':
    main()
