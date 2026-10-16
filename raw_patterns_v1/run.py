"""Fixed-budget pre-2017 raw OHLCV Flatten pilot, no portfolio performance claims."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from raw_patterns_v1.patterns import flatten_views,leave_one_out,split_dates
from raw_patterns_v1.model import learner as v1
from compact21_predictive_v2.metrics import evaluate
from paper_ltr_v2.diagnostics_solver import relative_curvature as solver
from etf_trader.source_only.raw_io import load_ticker_csv_folder,FIELDS

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,obj):Path(path).write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')

def build_panel(mats):
    # Slice all matrices BEFORE windows, signals or labels are constructed.
    mats={k:v.loc[(v.index>='2011-01-01')&(v.index<'2017-04-01')].copy() for k,v in mats.items()}
    dates=mats['Close'].index;tickers=list(mats['Close'].columns)
    monthends=pd.Series(np.arange(len(dates)),index=dates).groupby(dates.to_period('M')).last()
    arrays={t:np.column_stack([mats[k][t].to_numpy(float) for k in FIELDS]) for t in tickers}
    rows=[];local=[];context=[];coverage=[]
    for pos in monthends:
        sd=dates[pos]
        if sd.year<2012 or sd.year>2016:continue
        ix=[];x=[];rejected=[]
        for t in tickers:
            try:z=flatten_views(arrays[t],int(pos))
            except ValueError:rejected.append(t);continue
            ix.append(t);x.append(z)
        coverage.append(dict(signal_date=str(sd.date()),eligible=len(ix),excluded=rejected))
        if len(ix)<100:continue
        x=np.stack(x);c=leave_one_out(x)
        entry=int(pos)+1;exitpos=entry+21
        if exitpos>=len(dates):raise ValueError('Missing label calendar')
        ret=[]
        for t in ix:
            prices=arrays[t][[entry,exitpos],0]
            if not np.isfinite(prices).all() or (prices<=0).any():
                raise ValueError('Invalid future label: never silently filter eligible assets')
            ret.append(prices[1]/prices[0]-1)
        ranks=pd.Series(ret).rank(pct=True,method='average').to_numpy()
        for j,t in enumerate(ix):
            rows.append(dict(signal_date=sd,ticker=t,exit_date_21=dates[exitpos],target_rank_21=ranks[j],target_ret_21=ret[j]))
        local.extend(x);context.extend(np.column_stack([x,c]))
    frame=pd.DataFrame(rows)
    if frame.empty:raise ValueError('Empty raw cohort')
    order=frame.sort_values(v1.KEYS).index.to_numpy()
    return frame.loc[order].reset_index(drop=True),np.asarray(local)[order],np.asarray(context)[order],coverage

def prediction(test,score):
    f=test.copy();f['pred']=score;f['vintage']=2
    if not np.isfinite(score).all():raise ValueError('Nonfinite prediction')
    return f

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out)
    if out.exists() and any(out.iterdir()):raise ValueError('Output must be new')
    out.mkdir(parents=True,exist_ok=True);(out/'models').mkdir()
    expected=json.loads((Path(__file__).with_name('FROZEN_R2.json')).read_text())
    actual={p.name:sha(p) for p in sorted(Path(a.raw).glob('*.csv'))}
    if actual!=expected:raise ValueError('Raw original frozen r2 byte hashes differ')
    mats,cats,manifest=load_ticker_csv_folder(a.raw,allow_missing=True)
    if len(cats)!=149:raise ValueError('Wrong Original149 universe')
    f,local,ctx,coverage=build_panel(mats)
    if not np.isfinite(local).all() or not np.isfinite(ctx).all():raise ValueError('Nonfinite tensors')
    f.to_parquet(out/'COHORT.parquet',index=False)
    write(out/'INPUT_AUDIT.json',dict(original_files_sha256=actual,universe_count=149,
        ignored_before='2011-01-01',first_supervised_signal=str(f.signal_date.min()),coverage=coverage,
        local_shape=list(local.shape),context_shape=list(ctx.shape),local_tensor_sha256=v1.array_hash(local),context_tensor_sha256=v1.array_hash(ctx),cohort_sha256=sha(out/'COHORT.parquet')))
    result=dict(status='RUNNING',protocol_sha256=sha(Path(__file__).with_name('PROTOCOL.md')),
        source_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in Path(__file__).parent.glob('*.py')},
        neural_recipe=v1.RECIPE,linear_recipe=solver.RECIPE,folds=[],new_neural_fits=0,new_linear_fits=0,no_portfolio_replay=True,production_adoption=False)
    predictions={k:[] for k in ('RAW_LINEAR','FLATTEN_LOCAL','FLATTEN_CONTEXT')}
    seeds={k:{s:[] for s in (101,202,303)} for k in ('FLATTEN_LOCAL','FLATTEN_CONTEXT')}
    started=time.perf_counter()
    for year in (2014,2015,2016):
        sub,val,test=split_dates(f,year)
        if sub.empty or val.empty or test.empty:raise ValueError('Empty temporal fold')
        if not (sub.exit_date_21<val.signal_date.min()).all():raise ValueError('Purge failed')
        if not (val.exit_date_21<pd.Timestamp(year,1,1)).all():raise ValueError('Maturity failed')
        fold=dict(year=year,subtrain_queries=sub.signal_date.nunique(),validation_queries=val.signal_date.nunique(),test_queries=test.signal_date.nunique(),
                  max_subtrain_exit=str(sub.exit_date_21.max()),validation_start=str(val.signal_date.min()),max_validation_exit=str(val.exit_date_21.max()),models=[])
        for variant,matrix in [('RAW_LINEAR',local),('FLATTEN_LOCAL',local),('FLATTEN_CONTEXT',ctx)]:
            state=v1.fit_transform_state(matrix[sub.index])
            x=v1.transform(matrix[sub.index],state);vx=v1.transform(matrix[val.index],state);tx=v1.transform(matrix[test.index],state)
            y=v1.decile_labels(sub);vy=v1.decile_labels(val);groups=v1.query_indices(sub);vg=v1.query_indices(val)
            base=dict(variant=variant,fit_input_sha256=v1.array_hash(x),validation_input_sha256=v1.array_hash(vx),test_input_sha256=v1.array_hash(tx))
            if variant=='RAW_LINEAR':
                w,audit=solver.solve_linear(x,y,groups);score=tx@w
                path=out/'models'/f'{year}_{variant}.npz';np.savez(path,w=w,**state)
                fold['models'].append(dict(**base,audit=audit,model_sha256=sha(path)))
                result['new_linear_fits']+=1
            else:
                by_seed=[]
                for seed in (101,202,303):
                    p,audit=v1.train_network(x,y,groups,vx,vy,vg,seed)
                    score=v1.forward(tx,p)[0];by_seed.append(score)
                    path=out/'models'/f'{year}_{variant}_{seed}.npz';np.savez(path,**p,**state)
                    # Saved-parameter inference is independently reconstructed here.
                    with np.load(path,allow_pickle=False) as z:
                        xx=(matrix[test.index]-z['mean'])/z['scale']
                        h=np.maximum(xx@z['W1']+z['b1'],0)
                        h=np.maximum(h@z['W2']+z['b2'],0)
                        np.testing.assert_allclose((h@z['W3']+z['b3']).ravel(),score,rtol=0,atol=1e-12)
                    seeds[variant][seed].append(prediction(test,score))
                    fold['models'].append(dict(**base,audit=audit,model_sha256=sha(path),parameters=sum(v.size for v in p.values())))
                    result['new_neural_fits']+=1
                score=np.mean(by_seed,axis=0)
            predictions[variant].append(prediction(test,score))
            print(json.dumps(dict(year=year,variant=variant,neural_fits=result['new_neural_fits'],seconds=time.perf_counter()-started)),flush=True)
        result['folds'].append(fold);write(out/'RESULT.json',result)
    quality={};seed_quality={};disagree={}
    for variant,parts in predictions.items():
        z=pd.concat(parts,ignore_index=True);z.to_parquet(out/(variant+'.parquet'),index=False)
        quality[variant]=evaluate(z,quality_exit_cutoff='2016-12-31')['aggregate_by_date']
    for variant,ss in seeds.items():
        seed_quality[variant]={};tops=[]
        for seed,parts in ss.items():
            z=pd.concat(parts,ignore_index=True);z.to_parquet(out/f'{variant}_{seed}.parquet',index=False)
            seed_quality[variant][str(seed)]=evaluate(z,quality_exit_cutoff='2016-12-31')['aggregate_by_date']
            mature=z[z.exit_date_21<'2017-01-01']
            top=mature.sort_values(['signal_date','pred','ticker'],ascending=[True,False,True]).groupby('signal_date').first().ticker
            tops.append(top.rename(str(seed)))
        leaders=pd.concat(tops,axis=1)
        disagree[variant]=float((leaders.nunique(axis=1)>1).mean())
    checks={v:{m:quality[v][m]>=.95*quality['RAW_LINEAR'][m] for m in ('top1_realized_percentile','ndcg5')} for v in seeds}
    result.update(status='RAW_FLATTEN_PILOT_COMPLETE',quality=quality,seed_quality=seed_quality,seed_top1_any_disagreement=disagree,
        exploratory_preservation_screen=checks,elapsed_seconds=time.perf_counter()-started,ALL_MATURITY_PASS=True,
        files_sha256={p.name:sha(p) for p in out.glob('*.parquet')},model_files_sha256={p.name:sha(p) for p in (out/'models').glob('*.npz')})
    if result['new_neural_fits']!=18 or result['new_linear_fits']!=3:raise ValueError('Unexpected fit budget')
    write(out/'RESULT.json',result)
    print(json.dumps(dict(status=result['status'],quality=quality,seed_top1_any_disagreement=disagree),indent=2))

if __name__=='__main__':main()
