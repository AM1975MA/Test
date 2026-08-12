#!/usr/bin/env python3
from __future__ import annotations
import argparse, importlib.util, json, time
from pathlib import Path
import numpy as np, pandas as pd
from xgboost import XGBRanker
import optuna

SEED_MODEL=101

def load_module(path:Path):
    spec=importlib.util.spec_from_file_location('base_spec',str(path));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def predict_dev(panel,features,params):
    out=[]
    for year in range(2017,2023):
        cutoff=pd.Timestamp(year,1,1)
        tr=panel[(panel.signal_date<cutoff)&(panel.exit_date_21<cutoff)&panel.target_rank_pct.notna()].sort_values(['signal_date','ticker'])
        te=panel[panel.signal_date.dt.year.eq(year)].sort_values(['signal_date','ticker'])
        if tr.signal_date.nunique()<60 or te.empty: continue
        groups=tr.groupby('signal_date',sort=True).size().tolist();y=(tr.target_rank_pct*100).round().astype(int)
        m=XGBRanker(objective='rank:pairwise',eval_metric='ndcg@3',tree_method='hist',n_jobs=2,verbosity=0,random_state=SEED_MODEL,**params)
        m.fit(tr[features].replace([np.inf,-np.inf],np.nan),y,group=groups,verbose=False)
        q=te[['signal_date','ticker','fwd_ret_21']].copy();q['pred']=m.predict(te[features].replace([np.inf,-np.inf],np.nan));out.append(q)
    return pd.concat(out,ignore_index=True)

def basket_metrics(pred,mem):
    x=pred.merge(mem[['basket','ticker']],on='ticker',how='inner').dropna(subset=['pred','fwd_ret_21']).copy()
    x['rel']=x.groupby(['signal_date','basket'])['fwd_ret_21'].rank(pct=True,method='average')
    x['pred_rank']=x.groupby(['signal_date','basket'])['pred'].rank(ascending=False,method='first')
    top=x[x.pred_rank<=3].copy();top['disc']=1.0/np.log2(top.pred_rank.to_numpy(float)+1.0)
    dcg=top.groupby(['signal_date','basket']).apply(lambda g: float((g.rel*g.disc).sum()),include_groups=False).rename('dcg3')
    true_top=x.sort_values(['signal_date','basket','rel'],ascending=[True,True,False]).groupby(['signal_date','basket'],sort=False).head(3).copy()
    true_top['ideal_rank']=true_top.groupby(['signal_date','basket']).cumcount()+1;true_top['disc']=1.0/np.log2(true_top.ideal_rank.to_numpy(float)+1.0)
    idcg=true_top.groupby(['signal_date','basket']).apply(lambda g: float((g.rel*g.disc).sum()),include_groups=False).rename('idcg3')
    nd=pd.concat([dcg,idcg],axis=1).dropna();nd['ndcg3']=nd.dcg3/nd.idcg3.replace(0,np.nan)
    top1=x[x.pred_rank.eq(1)].set_index(['signal_date','basket'])['rel'].rename('ndcg1')
    m=nd.join(top1,how='inner').reset_index()
    top2=x[x.pred_rank<=2].groupby(['signal_date','basket']).rel.mean().rename('top2_mean_rel');m=m.join(top2,on=['signal_date','basket'])
    x['true_rank_desc']=x.groupby(['signal_date','basket'])['fwd_ret_21'].rank(ascending=False,method='min')
    hit=x[x.pred_rank.eq(1)].set_index(['signal_date','basket']).true_rank_desc.le(3).astype(float).rename('top1_hit_true_top3');m=m.join(hit,on=['signal_date','basket'])
    return m

def objective_factory(panel,features,mem,output,shard):
    def objective(trial):
        params={
          'n_estimators':trial.suggest_int('n_estimators',120,600,step=40),
          'max_depth':trial.suggest_int('max_depth',2,6),
          'learning_rate':trial.suggest_float('learning_rate',0.015,0.080,log=True),
          'min_child_weight':trial.suggest_float('min_child_weight',5.0,80.0,log=True),
          'subsample':trial.suggest_float('subsample',0.70,1.00),
          'colsample_bytree':trial.suggest_float('colsample_bytree',0.55,1.00),
          'reg_lambda':trial.suggest_float('reg_lambda',1.0,30.0,log=True),
          'reg_alpha':trial.suggest_float('reg_alpha',0.01,2.0,log=True),
          'gamma':trial.suggest_float('gamma',0.0,1.0),
        }
        t0=time.time();p=predict_dev(panel,features,params);bm=basket_metrics(p,mem)
        nd1=float(bm.ndcg1.mean());nd3=float(bm.ndcg3.mean());top2=float(bm.top2_mean_rel.mean());hit=float(bm.top1_hit_true_top3.mean())
        score=.60*nd1+.40*nd3
        trial.set_user_attr('ndcg1',nd1);trial.set_user_attr('ndcg3',nd3);trial.set_user_attr('top2_mean_rel',top2);trial.set_user_attr('top1_hit_true_top3',hit);trial.set_user_attr('elapsed_s',time.time()-t0)
        rec={'trial':trial.number,'score':score,'ndcg1':nd1,'ndcg3':nd3,'top2_mean_rel':top2,'top1_hit_true_top3':hit,'params':params}
        with open(output/f'TRIALS_{shard}.jsonl','a') as f:f.write(json.dumps(rec)+'\n')
        print(json.dumps(rec),flush=True);return score
    return objective

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--panel',required=True);ap.add_argument('--membership',required=True);ap.add_argument('--base-module',required=True);ap.add_argument('--output',required=True);ap.add_argument('--trials',type=int,default=12);ap.add_argument('--shard',type=int,default=0);a=ap.parse_args()
    out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
    panel=pd.read_parquet(a.panel);panel.signal_date=pd.to_datetime(panel.signal_date);panel.exit_date_21=pd.to_datetime(panel.exit_date_21)
    mem=pd.read_csv(a.membership);mem.ticker=mem.ticker.astype(str).str.upper();base=load_module(Path(a.base_module));features=list(base.F2D_FEATURES)
    sampler=optuna.samplers.TPESampler(seed=260721+a.shard,n_startup_trials=min(6,a.trials))
    study=optuna.create_study(direction='maximize',sampler=sampler,study_name=f'titanium_compact_dev_shard{a.shard}')
    study.optimize(objective_factory(panel,features,mem,out,a.shard),n_trials=a.trials,gc_after_trial=True)
    rows=[]
    for t in study.trials:
        if t.value is None: continue
        rows.append({'trial':t.number,'score':t.value,**t.params,**t.user_attrs})
    pd.DataFrame(rows).sort_values('score',ascending=False).to_csv(out/f'OPTUNA_DEV_SHARD_{a.shard}.csv',index=False)
    best={'value':study.best_value,'params':study.best_params,'attrs':study.best_trial.user_attrs,'shard':a.shard};(out/f'BEST_{a.shard}.json').write_text(json.dumps(best,indent=2));print(json.dumps(best,indent=2))
if __name__=='__main__':main()
