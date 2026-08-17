#!/usr/bin/env python3
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
