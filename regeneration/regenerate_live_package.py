#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import ExtraTreesRegressor, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRanker

PACKAGE_NAME = 'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE_PACKAGE'
FROZEN_REFERENCE = {
    'Titanium_V2_CAGR': 0.21654064,
    'Titanium_V2_MaxDD': -0.339351,
    'Titanium_V2_Sharpe': 0.868077,
    'Opportunity_Router_CAGR': 0.22742810,
    'Opportunity_Router_MaxDD': -0.349569,
    'Opportunity_Router_Sharpe': 0.877664,
}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def corrected_downvol(mode: str):
    if mode == 'original':
        return None
    if mode == 'zero_std':
        def f(ret, h):
            neg = ret.clip(upper=0.0)
            return neg.rolling(h, min_periods=h).std(ddof=0) * np.sqrt(252)
        return f
    if mode == 'downside_rms':
        def f(ret, h):
            neg = ret.clip(upper=0.0)
            return np.sqrt(neg.pow(2).rolling(h, min_periods=h).mean()) * np.sqrt(252)
        return f
    if mode == 'negative_std_full':
        def f(ret, h):
            neg = ret.where(ret < 0)
            return neg.rolling(h, min_periods=1).std(ddof=0) * np.sqrt(252)
        return f
    raise ValueError(mode)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def safe_parquet(df: pd.DataFrame, path: Path, *, index: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=index, compression='zstd')


def final_fit_and_export(v5, base, compact, tail, macro, macro_feats, opp, cutoff: pd.Timestamp, model_dir: Path, n_estimators: int):
    model_dir.mkdir(parents=True, exist_ok=True)
    params = dict(base.COMPACT_PARAMS)
    params['n_estimators'] = n_estimators
    params['n_jobs'] = 2
    manifest: Dict[str, Any] = {'cutoff': str(cutoff.date()), 'models': {}, 'feature_lists': {}}

    cvalid = compact[base.F2D_FEATURES].notna().sum(axis=1) >= 30
    tr = compact[(compact.signal_date < cutoff) & (compact.exit_date_21 < cutoff) & compact.target_rank_pct.notna() & cvalid].sort_values(['signal_date', 'ticker'])
    groups = tr.groupby('signal_date', sort=True).size().tolist()
    y = (tr.target_rank_pct * 100).round().astype(int)
    manifest['feature_lists']['compact'] = list(base.F2D_FEATURES)
    manifest['compact_train_rows'] = int(len(tr))
    manifest['compact_train_dates'] = int(tr.signal_date.nunique())
    for seed in v5.MODEL_SEEDS:
        m = XGBRanker(**params, random_state=seed)
        m.fit(tr[base.F2D_FEATURES].replace([np.inf, -np.inf], np.nan), y, group=groups, verbose=False)
        p = model_dir / f'compact_seed_{seed}.json'
        m.save_model(p)
        manifest['models'][f'compact_seed_{seed}'] = p.name

    tvalid = tail[base.TAIL_FEATURES].notna().sum(axis=1) >= 12
    ttr = tail[(tail.signal_date < cutoff) & (tail.exit_date_63 < cutoff) & tail.y_tailmix.notna() & tvalid]
    tm = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), Ridge(alpha=30.0)).fit(ttr[base.TAIL_FEATURES], ttr.y_tailmix)
    joblib.dump(tm, model_dir / 'tailmix.joblib', compress=3)
    manifest['models']['tailmix'] = 'tailmix.joblib'
    manifest['feature_lists']['tailmix'] = list(base.TAIL_FEATURES)
    manifest['tail_train_rows'] = int(len(ttr))

    mtr = macro[(macro.signal_date < cutoff) & (macro.label_exit_date_63 < cutoff) & macro.target_rank.notna()]
    mm = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), Ridge(alpha=50.0)).fit(mtr[macro_feats], mtr.target_rank)
    joblib.dump(mm, model_dir / 'macro_destination.joblib', compress=3)
    manifest['models']['macro_destination'] = 'macro_destination.joblib'
    manifest['feature_lists']['macro'] = list(macro_feats)
    manifest['macro_train_rows'] = int(len(mtr))

    for spec in v5.OPPORTUNITY_SPECS:
        feats = spec['features']; target = spec['target']
        otr = opp[(opp.signal_date < cutoff) & (opp.label_exit_date_21 < cutoff) & opp[target].notna()]
        if spec['model'].startswith('ET'):
            model = make_pipeline(SimpleImputer(strategy='median'), ExtraTreesRegressor(n_estimators=300, max_depth=4, min_samples_leaf=30, n_jobs=2, random_state=26072037))
        elif spec['model'].startswith('RF'):
            model = make_pipeline(SimpleImputer(strategy='median'), RandomForestClassifier(n_estimators=300, max_depth=3, min_samples_leaf=30, n_jobs=2, class_weight='balanced', random_state=26072043))
        else:
            model = make_pipeline(SimpleImputer(strategy='median'), StandardScaler(), Ridge(alpha=100.0))
        model.fit(otr[feats], otr[target].astype(int) if target == 'target_explosive' else otr[target])
        fn = f'opportunity_{target}.joblib'
        joblib.dump(model, model_dir / fn, compress=3)
        manifest['models'][target] = fn
        manifest['feature_lists'][target] = list(feats)
        manifest[f'{target}_train_rows'] = int(len(otr))

    return manifest


def live_script_text() -> str:
    return r'''#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json
from pathlib import Path
import joblib, numpy as np, pandas as pd
from xgboost import XGBRanker
ROOT=Path(__file__).resolve().parent
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def patch_downvol(base,mode):
    if mode=='zero_std': base.rolling_downvol=lambda ret,h: ret.clip(upper=0.0).rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)
    elif mode=='downside_rms': base.rolling_downvol=lambda ret,h: np.sqrt(ret.clip(upper=0.0).pow(2).rolling(h,min_periods=h).mean())*np.sqrt(252)
    elif mode=='negative_std_full': base.rolling_downvol=lambda ret,h: ret.where(ret<0).rolling(h,min_periods=1).std(ddof=0)*np.sqrt(252)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--basket',default='');ap.add_argument('--output',default='LIVE_SIGNAL.json');args=ap.parse_args()
    base=load_module(ROOT/'source/titanium_retrained_current_data_audit.py','base');v5=load_module(ROOT/'source/titanium_reconstruction_v6.py','v6')
    manifest=json.loads((ROOT/'models/MODEL_MANIFEST.json').read_text());patch_downvol(base,manifest['downvol_mode']);mats=v5.load_mats(ROOT/'data')
    dates,compact,tail0,D=base.build_features(mats);D=v5.enhance_feature_dictionary(base,mats,dates,D);tail=v5.rebuild_tail_long(base,D,dates,mats['Close'].columns)
    compact=base.add_labels(compact,mats['Open'],dates);tail=base.add_labels(tail,mats['Open'],dates);clusters,_,_=v5.build_s3b_clusters(mats,dates,base.TICKER_CATEGORY);macro,macro_feats=v5.build_macro_panel(base,D,compact,base.TICKER_CATEGORY);opp=v5.build_opportunity_panel(base,D,clusters,compact)
    dt=pd.Timestamp(dates.max());cvalid=compact[base.F2D_FEATURES].notna().sum(axis=1)>=30;te=compact[(compact.signal_date==dt)&cvalid].sort_values(['signal_date','ticker']);cp=[]
    for seed in v5.MODEL_SEEDS:
        m=XGBRanker();m.load_model(ROOT/f'models/compact_seed_{seed}.json');cp.append(m.predict(te[base.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)))
    p=te[['signal_date','ticker']].copy();p['compact_raw']=np.mean(cp,axis=0);tvalid=tail[base.TAIL_FEATURES].notna().sum(axis=1)>=12;tte=tail[(tail.signal_date==dt)&tvalid]
    tm=joblib.load(ROOT/'models/tailmix.joblib');tp=tte[['signal_date','ticker']].copy();tp['tail_raw']=tm.predict(tte[base.TAIL_FEATURES]);p=p.merge(tp,on=['signal_date','ticker'],how='left');p['compact_rank']=p.compact_raw.rank(pct=True);p['tail_rank']=p.tail_raw.rank(pct=True);p['titanium_score_pre_macro']=.70*p.compact_rank+.30*p.tail_rank
    mte=macro[macro.signal_date==dt];mm=joblib.load(ROOT/'models/macro_destination.joblib');mq=mte[['macro_category']].copy();mq['macro_raw']=mm.predict(mte[macro_feats]);mq['macro_z']=(mq.macro_raw-mq.macro_raw.mean())/(mq.macro_raw.std(ddof=0)+1e-12);mq=mq.sort_values('macro_z',ascending=False);top_macro=str(mq.iloc[0].macro_category);macro_gap=float(mq.iloc[0].macro_z-mq.iloc[1].macro_z) if len(mq)>1 else 0.0
    p['macro_category']=p.ticker.map(base.TICKER_CATEGORY);p['macro_bonus']=np.where((p.macro_category==top_macro)&(macro_gap>=.75)&(p.tail_rank>=.80),.15,0.0);p['titanium_score']=p.titanium_score_pre_macro+p.macro_bonus
    ote=opp[opp.signal_date==dt].copy();weights={'target_top2_pred':.35,'target_spread_pred':.15,'target_excess_max_pred':.35,'target_explosive_pred':.15}
    for spec in v5.OPPORTUNITY_SPECS:
        target=spec['target'];model=joblib.load(ROOT/f'models/opportunity_{target}.joblib')
        if target=='target_explosive':
            clf=model[-1];pp=model.predict_proba(ote[spec['features']]);val=pp[:,list(clf.classes_).index(1)] if 1 in clf.classes_ else np.zeros(len(ote))
        else: val=model.predict(ote[spec['features']])
        ote[target+'_pred']=val;ote[target+'_pred_rank']=pd.Series(val,index=ote.index).rank(pct=True)
    ote['opp_raw']=sum(w*ote[c+'_rank'] for c,w in weights.items());ote['opp_z']=(ote.opp_raw-ote.opp_raw.mean())/(ote.opp_raw.std(ddof=0)+1e-12);og=ote.sort_values('opp_z',ascending=False)
    universe=[x.strip().upper() for x in args.basket.split(',') if x.strip()] or sorted(p.ticker.unique());g=p[p.ticker.isin(universe)].sort_values('titanium_score',ascending=False);r1,r2=g.iloc[0],g.iloc[1];margin=float(r1.titanium_score-r2.titanium_score);w1=1.0 if margin>=.12 else .75
    latest_clusters=clusters[clusters.signal_date==dt].set_index('ticker').cluster_id.to_dict();top_cluster=int(og.iloc[0].cluster_id);opp_gap=float(og.iloc[0].opp_z-og.iloc[1].opp_z) if len(og)>1 else 0.0;direct=bool(w1<1 and latest_clusters.get(str(r1.ticker),-1)==top_cluster and opp_gap>=.50);router_on=bool(manifest.get('last_router_on',False));final_direct=direct and router_on
    result={'signal_date':str(dt.date()),'top1':str(r1.ticker),'top2':str(r2.ticker),'margin':margin,'base_weights':{str(r1.ticker):w1,str(r2.ticker):1-w1},'top_macro':top_macro,'macro_gap_z':macro_gap,'opportunity_top_cluster':top_cluster,'opportunity_gap_z':opp_gap,'direct_condition':direct,'router_on':router_on,'final_weights':{str(r1.ticker):1.0} if final_direct else {str(r1.ticker):w1,str(r2.ticker):1-w1},'downvol_mode':manifest['downvol_mode'],'model_cutoff':manifest['cutoff']}
    (ROOT/args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
if __name__=='__main__':main()
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base-module', required=True);ap.add_argument('--v5-module', required=True);ap.add_argument('--data-dir', required=True);ap.add_argument('--output-parent', default='.')
    ap.add_argument('--downvol-mode', choices=['original','zero_std','downside_rms','negative_std_full'], default='zero_std');ap.add_argument('--n-estimators', type=int, default=360);ap.add_argument('--n-baskets', type=int, default=500)
    args = ap.parse_args();started = time.time();parent = Path(args.output_parent).resolve();root = parent / PACKAGE_NAME;shutil.rmtree(root, ignore_errors=True)
    for d in ['source','data','panels','models','backtest','manifest']:(root/d).mkdir(parents=True, exist_ok=True)
    base_path = Path(args.base_module).resolve();v5_path = Path(args.v5_module).resolve();data_dir = Path(args.data_dir).resolve();base = load_module(base_path, 'meteor_base');v5 = load_module(v5_path, 'meteor_v5')
    f = corrected_downvol(args.downvol_mode)
    if f is not None:base.rolling_downvol = f
    v5.N_BASKETS = args.n_baskets;mats = v5.load_mats(data_dir);dates, compact, tail0, D = base.build_features(mats);D = v5.enhance_feature_dictionary(base, mats, dates, D);tail = v5.rebuild_tail_long(base, D, dates, mats['Close'].columns)
    compact = base.add_labels(compact, mats['Open'], dates);tail = base.add_labels(tail, mats['Open'], dates);clusters, balance, ari = v5.build_s3b_clusters(mats, dates, base.TICKER_CATEGORY);macro, macro_feats = v5.build_macro_panel(base, D, compact, base.TICKER_CATEGORY);opp = v5.build_opportunity_panel(base, D, clusters, compact)
    pred, opp_pred, fit_audit, macro_pred = v5.fit_predict(base, compact, tail, macro, macro_feats, opp, range(2017, 2027), args.n_estimators);pred = pred[pred.signal_date >= v5.BACKTEST_START].copy();opp_pred = opp_pred[opp_pred.signal_date >= v5.BACKTEST_START].copy()
    cal = compact[['signal_date','entry_date','exit_date']].drop_duplicates().sort_values('signal_date');cal = cal[(cal.signal_date >= v5.BACKTEST_START) & cal.signal_date.isin(pred.signal_date.unique()) & cal.exit_date.notna()].reset_index(drop=True)
    baskets, cats = v5.make_baskets(base, pred, args.n_baskets);idx, EB, ED, ER, active, margin, cond, bs, bw, ds, dw = v5.simulate_all(baskets, pred, opp_pred, clusters, mats, cal)
    rows=[]
    for b in range(len(baskets)):
        for name, arr in [('BASE',EB[b]),('DIRECT',ED[b]),('ROUTER',ER[b])]:
            c,dd,sh,fe=v5.metrics(arr,idx);rows.append({'basket':b,'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(active.sum()),'direct_condition_months':int(cond[b].sum())})
    results=pd.DataFrame(rows);global_universe=[sorted(pred.ticker.unique())];idxg,Ebg,Edg,Erg,activeg,marging,condg,gbs,gbw,gds,gdw=v5.simulate_all(global_universe,pred,opp_pred,clusters,mats,cal,forced_active=active);grows=[]
    for name,arr in [('BASE',Ebg[0]),('DIRECT',Edg[0]),('ROUTER',Erg[0])]:
        c,dd,sh,fe=v5.metrics(arr,idxg);grows.append({'strategy':name,'cagr':c,'maxdd':dd,'sharpe':sh,'final_equity':fe,'router_active_months':int(activeg.sum()),'direct_condition_months':int(condg[0].sum())});pd.Series(arr,index=idxg,name='equity').to_csv(root/'backtest'/f'GLOBAL_{name}_EQUITY.csv')
    global_score=pd.DataFrame(grows);results.to_csv(root/'backtest'/'BASKET_RESULTS_500.csv',index=False);global_score.to_csv(root/'backtest'/'GLOBAL_SCORECARD.csv',index=False)
    pd.DataFrame([{'basket':b,'ticker':t,'category':base.TICKER_CATEGORY.get(t)} for b,u in enumerate(baskets) for t in u]).to_csv(root/'panels'/'BASKET_MEMBERSHIP_500.csv',index=False);pd.DataFrame({'signal_date':cal.signal_date,'entry_date':cal.entry_date,'exit_date':cal.exit_date,'router_on':active}).to_csv(root/'panels'/'ROUTER_SCHEDULE.csv',index=False);cal.to_csv(root/'panels'/'MONTHLY_CALENDAR.csv',index=False)
    np.savez_compressed(root/'panels'/'TITANIUM_CONCENTRATION_FRONTIER_PATHS.npz',dates=np.array(idx,dtype='datetime64[ns]'),BASE=EB,DIRECT=ED,ROUTER=ER);np.savez_compressed(root/'panels'/'TARGET_ARRAYS_500.npz',base_sel=bs,base_weights=bw,direct_sel=ds,direct_weights=dw,margin=margin,direct_condition=cond,tickers=np.array(list(mats['Close'].columns)),signal_dates=np.array(cal.signal_date,dtype='datetime64[ns]'))
    safe_parquet(pred, root/'panels'/'SUPER_GOLD_OOS_SCORE_PANEL.parquet');safe_parquet(compact, root/'panels'/'NPORT_TITANIUM_PANEL.parquet');safe_parquet(tail, root/'panels'/'TAILMIX_PANEL.parquet');safe_parquet(macro, root/'panels'/'MACRO_DESTINATION_PANEL.parquet');safe_parquet(opp, root/'panels'/'OPPORTUNITY_TRAINING_PANEL.parquet')
    opp_pred.to_csv(root/'panels'/'TITANIUM_V3_OPPORTUNITY_OOS_CLUSTER_PANEL.csv',index=False);clusters.to_csv(root/'panels'/'DYNAMIC_CLUSTERS_MONTHLY.csv',index=False);balance.to_csv(root/'panels'/'S3B_BALANCE.csv',index=False);ari.to_csv(root/'panels'/'S3B_ARI.csv',index=False);fit_audit.to_csv(root/'panels'/'FIT_AUDIT.csv',index=False)
    for key in ['Open','High','Low','Close','Volume']:shutil.copy2(data_dir/f'{key.upper()}.parquet', root/'data'/f'{key.upper()}.parquet')
    if (data_dir/'DOWNLOAD_LOG.csv').exists():shutil.copy2(data_dir/'DOWNLOAD_LOG.csv',root/'data'/'DOWNLOAD_LOG.csv')
    shutil.copy2(base_path,root/'source'/'titanium_retrained_current_data_audit.py');shutil.copy2(v5_path,root/'source'/'titanium_reconstruction_v6.py');shutil.copy2(Path(__file__),root/'source'/'regenerate_live_package.py')
    cutoff = pd.Timestamp(dates.max()) + pd.Timedelta(days=1);model_manifest=final_fit_and_export(v5,base,compact,tail,macro,macro_feats,opp,cutoff,root/'models',args.n_estimators);model_manifest.update({'downvol_mode':args.downvol_mode,'last_router_on':bool(active[-1]) if len(active) else False,'last_signal_date':str(pd.Timestamp(dates.max()).date()),'n_baskets':args.n_baskets,'n_tickers':len(mats['Close'].columns),'frozen_reference':FROZEN_REFERENCE});(root/'models'/'MODEL_MANIFEST.json').write_text(json.dumps(model_manifest,indent=2))
    live_path=root/'METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py';live_path.write_text(live_script_text());live_path.chmod(0o755);(root/'requirements.txt').write_text('numpy==2.3.5\npandas==2.2.3\nscipy==1.17.0\nscikit-learn==1.8.0\nxgboost==3.1.3\njoblib==1.5.3\npyarrow>=18\nmatplotlib>=3.8\nnumba>=0.60\n')
    router=results[results.strategy=='ROUTER'];base_res=results[results.strategy=='BASE'];direct=results[results.strategy=='DIRECT'];q=router.cagr.quantile([.01,.05,.10,.25,.50,.75,.90,.95,.99]);score_summary={'downvol_mode':args.downvol_mode,'oos_start':str(pd.Timestamp(idx[0]).date()),'oos_end':str(pd.Timestamp(idx[-1]).date()),'n_tickers':len(mats['Close'].columns),'n_baskets':len(baskets),'n_months':len(cal),'basket_base_mean_cagr':float(base_res.cagr.mean()),'basket_direct_mean_cagr':float(direct.cagr.mean()),'basket_router_mean_cagr':float(router.cagr.mean()),'basket_router_median_cagr':float(router.cagr.median()),'basket_router_mean_maxdd':float(router.maxdd.mean()),'basket_router_median_maxdd':float(router.maxdd.median()),'basket_router_percentiles':{str(k):float(v) for k,v in q.items()},'global':global_score.set_index('strategy').to_dict('index'),'frozen_reference':FROZEN_REFERENCE,'delta_vs_frozen_router_mean_cagr':float(router.cagr.mean()-FROZEN_REFERENCE['Opportunity_Router_CAGR']),'elapsed_seconds':time.time()-started};(root/'backtest'/'SCORECARD_SUMMARY.json').write_text(json.dumps(score_summary,indent=2))
    audit=[]
    for family,cols,frame in [('COMPACT',base.F2D_FEATURES,compact),('TAIL',base.TAIL_FEATURES,tail),('MACRO',macro_feats,macro)]:
        for c in cols:audit.append({'family':family,'feature':c,'exists':c in frame,'missing_rate':float(frame[c].isna().mean()) if c in frame else 1.0,'std':float(pd.to_numeric(frame[c],errors='coerce').std()) if c in frame else np.nan})
    pd.DataFrame(audit).to_csv(root/'backtest'/'FEATURE_PARITY_AUDIT.csv',index=False)
    readme=f'''# METEOR Titanium V2 + Opportunity V3 — regenerated live package\n\nGenerated directly from the ticker OHLCV matrices with a complete annual expanding walk-forward retraining.\n\n## Configuration\n\n- Downside volatility definition: `{args.downvol_mode}`\n- Compact: three XGBRanker models, seeds 101/202/303, {args.n_estimators} trees\n- TailMix: Ridge alpha 30\n- Blend: 70% Compact / 30% TailMix\n- Conditional macro bonus: +0.15\n- Confidence-adaptive concentration: 100/0 or 75/25 at margin 0.12\n- S3B clusters and four-model Opportunity layer\n- Common causal 12-month Router schedule\n- D+1 open execution, one-way costs, systemic governor and conditional stop\n\n## Regenerated results\n\n- Mean Router CAGR over 500 baskets: **{router.cagr.mean():.4%}**\n- Median Router CAGR: **{router.cagr.median():.4%}**\n- Mean Base CAGR: **{base_res.cagr.mean():.4%}**\n- Global Router CAGR: **{global_score.set_index('strategy').loc['ROUTER','cagr']:.4%}**\n- Global Direct CAGR: **{global_score.set_index('strategy').loc['DIRECT','cagr']:.4%}**\n\nFrozen historical reference: Titanium V2 21.6541%, Opportunity Router 22.7428%. The regenerated result is explicitly reported separately and is not silently substituted for the frozen result.\n\n## Usage\n\n```bash\npip install -r requirements.txt\npython METEOR_TITANIUM_V2_OPPORTUNITY_V3_LIVE.py\n```\n\nUse `--basket SPY,QQQ,...` to restrict the live selection universe.\n''';(root/'README.md').write_text(readme);subprocess.run([sys.executable,str(live_path),'--output','LIVE_SIGNAL.json'],cwd=root,check=True)
    files=[]
    for p in sorted(root.rglob('*')):
        if p.is_file() and p.relative_to(root).as_posix()!='manifest/SHA256SUMS.txt':files.append({'path':p.relative_to(root).as_posix(),'size':p.stat().st_size,'sha256':sha256(p)})
    manifest={'package':PACKAGE_NAME,'created_utc':pd.Timestamp.utcnow().isoformat(),'downvol_mode':args.downvol_mode,'source_hashes':{'base':sha256(base_path),'v5':sha256(v5_path),'generator':sha256(Path(__file__))},'files':files,'score_summary':score_summary};(root/'manifest'/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    with (root/'manifest'/'SHA256SUMS.txt').open('w') as fsum:
        for r in files:fsum.write(f"{r['sha256']}  {r['path']}\n")
        fsum.write(f"{sha256(root/'manifest'/'PACKAGE_MANIFEST.json')}  manifest/PACKAGE_MANIFEST.json\n")
    zip_path=parent/f'{PACKAGE_NAME}.zip'
    if zip_path.exists():zip_path.unlink()
    shutil.make_archive(str(parent/PACKAGE_NAME),'zip',parent,PACKAGE_NAME);print(json.dumps({'package':str(zip_path),'sha256':sha256(zip_path),'score_summary':score_summary},indent=2))

if __name__=='__main__':main()
