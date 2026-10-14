"""Audit riproducibile dei checkpoint: sola inferenza, nessun addestramento."""
from __future__ import annotations
import argparse, hashlib, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from paper_ltr_v1 import learner as original
from compact21_predictive_v2.metrics import evaluate
KEYS=['signal_date','ticker']

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def query_diagnostics(frame,scores,cutoff=None):
    f=frame.copy().reset_index(drop=True);p=np.asarray(scores,float)
    if p.shape!=(len(f),) or not np.isfinite(p).all() or f.empty or f.duplicated(KEYS).any():
        raise ValueError('Predizioni/supporto non validi')
    f['pred']=p
    if 'fwd_ret_21' in f and 'target_ret_21' not in f:f['target_ret_21']=f.fwd_ret_21
    quality=evaluate(f,quality_exit_cutoff=cutoff)
    f['signal_date']=pd.to_datetime(f.signal_date)
    if cutoff is not None:
        mask=pd.to_datetime(f.exit_date_21).notna() & (pd.to_datetime(f.exit_date_21)<=pd.Timestamp(cutoff))
        f=f.loc[mask].reset_index(drop=True)
    labels=original.decile_labels(f); rows=[];leaders=[];selected_returns=[]
    for date,g in f.groupby('signal_date',sort=True):
        ix=g.index.to_numpy();s=g.pred.to_numpy();q=original.softmax(labels[ix].astype(float))
        shifted=s-s.max();logp=shifted-np.log(np.exp(shifted).sum())
        h=float(-np.dot(q,np.log(q)));ce=float(-np.dot(q,logp));kl=ce-h
        if kl < -1e-10:raise ValueError('KL negativa oltre tolleranza numerica')
        order=g.sort_values(['pred','ticker'],ascending=[False,True],kind='stable')
        leader=str(order.ticker.iloc[0]);leaders.append(leader)
        true_order=g.sort_values(['target_rank_21','ticker'],ascending=[False,True],kind='stable')
        low_order=g.sort_values(['target_rank_21','ticker'],ascending=[True,True],kind='stable')
        count=int(np.ceil(len(g)/10));selected=order.iloc[0]
        if 'target_ret_21' in g:selected_returns.append(float(selected.target_ret_21))
        rows.append(dict(signal_date=pd.Timestamp(date).isoformat(),n_tickers=len(g),
            cross_entropy=ce,target_entropy=h,kl=max(0.,kl),uniform_loss=float(np.log(len(g))),
            uniform_kl=float(np.log(len(g))-h),top_decile_mass=float(q[labels[ix]==10].sum()),
            target_effective_assets=float(np.exp(h)),score_std=float(s.std()),score_range=float(np.ptp(s)),
            predicted_max_probability=float(np.exp(logp).max()),top1_tie_rows=int((s==s.max()).sum()),top1=leader,
            top1_in_best_decile=float(leader in true_order.head(count).ticker.tolist()),
            top1_in_worst_decile=float(leader in low_order.head(count).ticker.tolist())))
        rows[-1]['exante_features']={name:float(selected[name]) if np.isfinite(selected[name]) else None
            for name in ('vol21','vol63','downvol21','downvol63') if name in g}
    fields=[k for k,v in rows[0].items() if isinstance(v,(float,int))]
    counts=pd.Series(leaders).value_counts()
    support=original.keys_hash(f)
    target=original.array_hash(f.target_rank_21.to_numpy(float))
    return dict(aggregate={k:float(np.mean([r[k] for r in rows])) for k in fields},per_query=rows,
        support_sha256=support,target_sha256=target,
        quality=quality,leader_counts={str(k):int(v) for k,v in counts.items()},
        leader_concentration=dict(unique_tickers=len(counts),max_fraction=float(counts.max()/len(leaders)),
                                  hhi=float(np.sum((counts/len(leaders))**2))),
        selected_return_distribution=dict(mean=float(np.mean(selected_returns)),median=float(np.median(selected_returns)),
            p10=float(np.quantile(selected_returns,.1)),p90=float(np.quantile(selected_returns,.9))) if selected_returns else None,
        estimand='Date equiponderate; CE e KL non sono rendimenti o probabilità di successo')

def checkpoint_predict(path,frame):
    with np.load(path,allow_pickle=False) as archive:
        state={k:archive[k] for k in archive.files}
    if state.get('feature_names',np.array([])).tolist()!=original.FEATURES:
        raise ValueError('Ordine delle feature del checkpoint diverso')
    x=original.transform(original.raw_matrix(frame),state)
    if 'w' in state:
        if state['w'].shape!=(len(original.FEATURES),):raise ValueError('Forma coefficienti lineari diversa')
        p=x@state['w']
    else:
        p=original.forward(x,state)[0]
    if not np.isfinite(p).all():raise ValueError('Inferenza checkpoint non finita')
    return p,state

def mature_train(panel,year):
    f=panel.copy();f.signal_date=pd.to_datetime(f.signal_date);f.exit_date_21=pd.to_datetime(f.exit_date_21)
    cutoff=pd.Timestamp(year,1,1)
    valid=f[original.FEATURES].notna().sum(axis=1)>=30
    return f[(f.signal_date<cutoff)&(f.exit_date_21<cutoff)&f.target_rank_21.notna()&valid].sort_values(KEYS).reset_index(drop=True)

def audit_saved_fit(train,year,model_paths,expected_audit):
    sub,val,_=original.split_training(train,year)
    for field,value in (('train_keys_sha256',original.keys_hash(train)),
                        ('subtrain_keys_sha256',original.keys_hash(sub)),('validation_keys_sha256',original.keys_hash(val)),
                        ('train_matrix_sha256',original.array_hash(original.raw_matrix(train))),
                        ('train_labels_sha256',original.array_hash(original.decile_labels(train)))):
        if expected_audit.get(field)!=value:raise ValueError('Fingerprint del supporto/target diverso: '+field)
    records=[]
    seeds=expected_audit['seeds']
    if len(model_paths)!=len(seeds):raise ValueError('Numero checkpoint diverso dai semi dichiarati')
    for path,seed in zip(model_paths,seeds):
        sp,state=checkpoint_predict(path,sub);vp,_=checkpoint_predict(path,val)
        for k in ('median','mean','scale'):
            if original.array_hash(state[k])!=expected_audit['learned_state_hashes'][k]:
                raise ValueError('Preprocessing checkpoint modificato: '+k)
        if 'parameter_sha256' in seed:
            for k,digest in seed['parameter_sha256'].items():
                if k not in state or original.array_hash(state[k])!=digest:raise ValueError('Parametri checkpoint modificati')
        sd=query_diagnostics(sub,sp,cutoff=pd.Timestamp(year,1,1));vd=query_diagnostics(val,vp,cutoff=pd.Timestamp(year,1,1))
        if 'best_validation_loss' in seed and abs(vd['aggregate']['cross_entropy']-seed['best_validation_loss'])>1e-10:
            raise ValueError('Loss checkpoint diversa dalla migliore loss dichiarata')
        records.append(dict(seed=seed['seed'],model_sha256=sha(path),training=sd,validation=vd,
                            original_stop_reason=seed.get('stop_reason'),best_epoch=seed.get('best_epoch')))
    return dict(year=year,subtrain_rows=len(sub),validation_rows=len(val),seeds=records,
                support_and_preprocessing_PASS=True,new_fits_executed=0)

def budget_gate(old_records,new_records):
    if len(old_records)!=63 or len(new_records)!=63:raise ValueError('Richiesti esattamente i 63 checkpoint limitati')
    old={r['key']:r for r in old_records};new={r['key']:r for r in new_records}
    if len(old)!=63 or set(old)!=set(new):raise ValueError('Checkpoint appaiati non corrispondenti')
    ratios=[];improved=0
    for key,a in old.items():
        b=new[key]
        if any(a[k]!=b[k] for k in ('support_sha256','target_sha256','target_entropy')):
            raise ValueError('Supporto/entropia target non identico')
        if any(not np.isfinite(r[k]) or r[k]<0 for r in (a,b) for k in ('kl','top1_quality','ndcg5')):
            raise ValueError('Metriche diagnostiche non valide')
        ratios.append((a['kl']-b['kl'])/a['kl'] if a['kl']>0 else 0.)
        improved+=b['kl']<a['kl']-1e-12
    oldq={k:float(np.mean([r[k] for r in old.values()])) for k in ('top1_quality','ndcg5')}
    newq={k:float(np.mean([r[k] for r in new.values()])) for k in oldq}
    checks=dict(median_relative_kl_reduction_ge1pct=float(np.median(ratios))>=.01,
                at_least42_improved=improved>=42,
                top1_validation_ge95pct=newq['top1_quality']>=.95*oldq['top1_quality'],
                ndcg5_validation_ge95pct=newq['ndcg5']>=.95*oldq['ndcg5'])
    return dict(checks=checks,PASS=all(checks.values()),median_relative_kl_reduction=float(np.median(ratios)),
                improved_checkpoint_count=improved,old_quality=oldq,new_quality=newq,
                weighting='63 checkpoint equiponderati; ciascun checkpoint media le proprie date di validazione',
                interpretation='Schermo convenzionale di budget, non prova di convergenza né di non inferiorità')

def audit_artifact(panel_dirs,artifact):
    root=Path(artifact);result=json.loads((root/'RESULT.json').read_text(encoding='utf-8'))
    if set(result.get('per_year',{}))!=set(map(str,range(2017,2027))):raise ValueError('Anni incompleti')
    hashes={str(i):sha(Path(panel_dirs[i])/'TI_COMPACT.parquet') for i in (1,2,3)}
    if result.get('input_sha256')!=hashes:raise ValueError('Input diversi dagli input del fit conservato')
    panels={i:pd.read_parquet(Path(panel_dirs[i])/'TI_COMPACT.parquet') for i in (1,2,3)}
    output={};budget_records=[]
    for year in range(2017,2027):
        output[str(year)]={}
        for i in (1,2,3):
            meta=result['per_year'][str(year)]['transforms'][str(i)]
            paths=[root/'models'/Path(p).name for p in meta['saved_models']]
            for path in paths:
                relative=path.relative_to(root).as_posix()
                if sha(path)!=result.get('model_files_sha256',{}).get(relative):raise ValueError('Hash checkpoint diverso dal manifest')
            audited=audit_saved_fit(mature_train(panels[i],year),year,paths,meta)
            output[str(year)][str(i)]=audited
            for s in audited['seeds']:
                vd=s['validation'];ag=vd['aggregate'];q=vd['quality']['aggregate_by_date']
                budget_records.append(dict(key=f'{year}/{i}/{s["seed"]}',stop_reason=s['original_stop_reason'],
                    support_sha256=vd['support_sha256'],target_sha256=vd['target_sha256'],
                    target_entropy=ag['target_entropy'],kl=ag['kl'],top1_quality=q['top1_realized_percentile'],ndcg5=q['ndcg5']))
    return dict(status='PAPER_LTR_V2_NOFIT_AUDIT_COMPLETE',variant=result.get('variant'),
                input_sha256=hashes,result_sha256=sha(root/'RESULT.json'),per_year=output,
                validation_records=budget_records,new_fits_executed=0,production_adoption=False)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for i in (1,2,3):ap.add_argument(f'--r{i}',required=True)
    ap.add_argument('--original',required=True);ap.add_argument('--baseline',required=True);ap.add_argument('--out',required=True)
    args=ap.parse_args()
    # Audit ufficiale nel medesimo profilo numerico; unit test puri non richiedono quel runtime.
    sys.path.insert(0,str(ROOT/'vendor/etf_trader_v2/src'))
    from compact21_predictive_v2.run import numerical_gate
    numerical=numerical_gate()
    result=audit_artifact({i:getattr(args,f'r{i}') for i in (1,2,3)},args.original)
    baseline_root=Path(args.baseline);baseline=json.loads((baseline_root/'RESULT.json').read_text(encoding='utf-8'))
    if baseline.get('variant')!='BASE' or baseline.get('status')!='COMPACT21_PREDICTIVE_V2_COMPLETE' or baseline.get('input_sha256')!=result['input_sha256']:
        raise ValueError('BASE predictive non corrispondente')
    if baseline.get('ALL_DETERMINISM_PASS') is not True or baseline.get('LEGACY_PARITY_PASS') is not True:raise ValueError('BASE non verificato')
    for name in ('NATIVE_PREDICTIONS.parquet','COMMON_PREDICTIONS.parquet'):
        if sha(baseline_root/name)!=baseline['files_sha256'][name]:raise ValueError('Predizioni BASE modificate')
    result['baseline_result_sha256']=sha(baseline_root/'RESULT.json')
    result['numeric_contract']=numerical
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],new_fits_executed=0),ensure_ascii=False))

if __name__=='__main__':main()
