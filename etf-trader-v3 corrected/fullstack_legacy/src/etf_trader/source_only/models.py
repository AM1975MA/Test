"""Annual prequential models; explicit label maturity and training-only transforms."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import Ridge
from .features import GROUPS


def _run_xgb_worker(cmd):
    cp=subprocess.run(cmd,capture_output=True,text=True)
    if cp.returncode!=0:
        raise RuntimeError(
            f"isolated XGBoost worker failed ({cp.returncode})\n"
            f"stdout: {cp.stdout[-2000:]}\n"
            f"stderr: {cp.stderr[-4000:]}"
        )
    return cp.stdout


def _fit_compact_rankers_isolated(k,frame,te,valid,cutoff,out,year):
    """Fit the 21/63-day Compact ensembles in isolated one-fit processes.

    Each seed/horizon fit is statistically identical to XGBRanker but runs in a
    fresh process.  This avoids OpenMP/XGBoost state reuse problems and lets the
    three independent seeds of each horizon execute concurrently.
    """
    params=dict(k.COMPACT_PARAMS)
    rounds=int(params.pop("n_estimators"))
    params.pop("n_jobs",None)  # execution-only; worker threading is explicit
    worker_threads=max(
        1,int(os.environ.get("ETF_TRADER_XGB_THREADS_PER_WORKER","1"))
    )
    worker_count=max(
        1,int(os.environ.get("ETF_TRADER_XGB_WORKERS","3"))
    )
    worker=Path(__file__).with_name("_xgb_worker.py")
    params_json=json.dumps(params,separators=(",",":"),sort_keys=True)

    scratch_root=Path(out)/".xgb_scratch"
    scratch_root.mkdir(parents=True,exist_ok=True)
    td=Path(tempfile.mkdtemp(prefix=f"{year}_",dir=scratch_root))
    tasks=[]
    meta={}
    Xte=te[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan).to_numpy()
    try:
        for horizon in (21,63):
            train=(
                frame[
                    (frame.signal_date<cutoff)
                    &(frame[f"exit_date_{horizon}"]<cutoff)
                    &frame[f"target_rank_{horizon}"].notna()
                    &valid
                ]
                .sort_values(["signal_date","ticker"])
            )
            if not (train.signal_date<cutoff).all() or not (
                train[f"exit_date_{horizon}"]<cutoff
            ).all():
                raise RuntimeError(
                    f"look-ahead: immature compact{horizon} label "
                    f"in fit year {year}"
                )

            Xtr=(
                train[k.F2D_FEATURES]
                .replace([np.inf,-np.inf],np.nan)
                .to_numpy()
            )
            y=(
                (train[f"target_rank_{horizon}"]*100)
                .round().astype(int).to_numpy()
            )
            groups=(
                train.groupby("signal_date",sort=True)
                .size().to_numpy()
            )
            data=td/f"data_{horizon}.npz"
            np.savez(data,Xtr=Xtr,Xte=Xte,y=y,groups=groups)
            meta[horizon]=train

            for seed in k.COMPACT_SEEDS:
                pred=td/f"pred_{horizon}_{int(seed)}.npy"
                cmd=[
                    sys.executable,str(worker),
                    "--data",str(data),
                    "--seed",str(int(seed)),
                    "--threads",str(worker_threads),
                    "--rounds",str(rounds),
                    "--params-json",params_json,
                    "--output",str(pred),
                ]
                tasks.append((horizon,int(seed),pred,cmd))

        # Run one horizon at a time.  Three single-thread workers avoid CPU
        # oversubscription while still parallelizing the independent seeds.
        max_workers=min(
            worker_count,
            len(k.COMPACT_SEEDS),
            max(1,os.cpu_count() or 1),
        )
        for horizon in (21,63):
            batch=[x for x in tasks if x[0]==horizon]
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                fut={
                    ex.submit(_run_xgb_worker,cmd):(h,s,pred)
                    for h,s,pred,cmd in batch
                }
                for future in as_completed(fut):
                    future.result()

        out_pred={}
        for horizon in (21,63):
            pp=[
                np.load(td/f"pred_{horizon}_{int(seed)}.npy")
                for seed in k.COMPACT_SEEDS
            ]
            out_pred[horizon]=np.mean(pp,axis=0)

        exec_info={
            "mode":"isolated_parallel_workers",
            "workers":max_workers,
            "threads_per_worker":worker_threads,
        }
        return out_pred,meta,exec_info
    finally:
        shutil.rmtree(td,ignore_errors=True)

def fit_predict(k,compact,tail,macro,mfeatures,extra,out,years=range(2017,2027)):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    frame=compact.merge(extra,on=['signal_date','ticker'],validate='one_to_one')
    predictions=[]; audit=[]; eligibility=[]
    for year in years:
        cached=out/f'scores_{year}.csv'
        if cached.exists():
            # Cached predictions are derived acceleration only.  They are accepted
            # only when the corresponding causal fit audit exists; otherwise fail closed.
            audit_file=out/f'fit_audit_{year}.json'
            if not audit_file.exists():
                raise RuntimeError(f'cached scores without causal fit audit: {cached}')
            predictions.append(pd.read_csv(cached,parse_dates=['signal_date','entry_date','exit_date']))
            continue
        cutoff=pd.Timestamp(year,1,1)
        valid=frame[k.F2D_FEATURES].notna().sum(axis=1)>=30
        tr=frame[(frame.signal_date<cutoff)&(frame.exit_date_21<cutoff)&frame.target_rank_pct.notna()&valid].sort_values(['signal_date','ticker'])
        te=frame[(frame.signal_date.dt.year==year)&valid].sort_values(['signal_date','ticker'])
        if te.empty:
            eligibility.append({'year':year,'status':'SKIP_NO_TEST_ROWS','train_signal_dates':int(tr.signal_date.nunique())})
            continue
        n_train_dates=int(tr.signal_date.nunique())
        if n_train_dates<60:
            # A short raw vintage cannot support the recovered ranker minimum.
            # Skip the year rather than weakening the model or backfilling scores.
            eligibility.append({'year':year,'status':'SKIP_INSUFFICIENT_MATURE_HISTORY','train_signal_dates':n_train_dates,'required':60})
            continue
        eligibility.append({'year':year,'status':'FIT','train_signal_dates':n_train_dates})
        assert (tr.exit_date_21<cutoff).all()
        if not (tr.signal_date < cutoff).all():
            raise RuntimeError(f'look-ahead: compact signal_date reaches fit cutoff {year}')
        o=te[['signal_date','ticker','entry_date','exit_date']].copy()
        compact_pred,compact_train,exec_info=_fit_compact_rankers_isolated(
            k,frame,te,valid,cutoff,out,year
        )
        for horizon in [21,63]:
            train=compact_train[horizon]
            o[f'compact{horizon}']=compact_pred[horizon]
            audit.append({
                'year':year,
                'model':f'compact{horizon}',
                'train_rows':len(train),
                'max_exit':str(train[f'exit_date_{horizon}'].max()),
                'fit_date':str(cutoff),
                **exec_info,
            })
        # Independently regularized predictors test incremental information.
        for group,features in {**GROUPS,'all':sum(GROUPS.values(),[])}.items():
            model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=100.))
            model.fit(tr[features],tr.target_rank_pct)
            o[group]=model.predict(te[features])
        tv=tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12
        ttr=tail[(tail.signal_date<cutoff)&(tail.exit_date_63<cutoff)&tail.y_tailmix.notna()&tv]
        tte=tail[(tail.signal_date.dt.year==year)&tv]
        if not (ttr.signal_date < cutoff).all() or not (ttr.exit_date_63 < cutoff).all():
            raise RuntimeError(f'look-ahead: immature tail label in fit year {year}')
        model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=30.))
        model.fit(ttr[k.TAIL_FEATURES],ttr.y_tailmix)
        t=tte[['signal_date','ticker']].copy(); t['tail']=model.predict(tte[k.TAIL_FEATURES])
        o=o.merge(t,on=['signal_date','ticker'],validate='one_to_one')
        mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]
        mte=macro[macro.signal_date.dt.year==year]
        if not (mtr.signal_date < cutoff).all() or not (mtr.label_exit_date_63 < cutoff).all():
            raise RuntimeError(f'look-ahead: immature macro label in fit year {year}')
        model=make_pipeline(SimpleImputer(strategy='median'),StandardScaler(),Ridge(alpha=50.))
        model.fit(mtr[mfeatures],mtr.target_rank)
        q=mte[['signal_date','macro_category']].copy();q['raw']=model.predict(mte[mfeatures])
        q['z']=q.groupby('signal_date').raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12))
        records=[]
        for dt,g in q.groupby('signal_date'):
            g=g.sort_values(['z','macro_category'],ascending=[False,True]);records.append({'signal_date':dt,'top_macro':g.iloc[0].macro_category,'macro_gap':g.iloc[0].z-g.iloc[1].z})
        o=o.merge(pd.DataFrame(records),on='signal_date');o['macro_category']=o.ticker.map(k.TICKER_CATEGORY)
        audit.extend([{'year':year,'model':'tail','max_exit':str(ttr.exit_date_63.max()),'fit_date':str(cutoff)},
                      {'year':year,'model':'macro','max_exit':str(mtr.label_exit_date_63.max()),'fit_date':str(cutoff)}])
        # Atomic annual cache: an interrupted process must never leave a
        # final scores_YEAR.csv without its causal fit audit.
        audit_file=out/f'fit_audit_{year}.json'
        audit_tmp=out/f'.fit_audit_{year}.json.tmp'
        score_tmp=out/f'.scores_{year}.csv.tmp'
        audit_tmp.write_text(json.dumps([a for a in audit if a['year']==year],indent=2))
        o.to_csv(score_tmp,index=False)
        audit_tmp.replace(audit_file)
        score_tmp.replace(cached)
        predictions.append(o)
        print('FIT_YEAR_COMPLETE',year,len(o),flush=True)
    (out/'eligibility_audit.json').write_text(json.dumps(eligibility,indent=2))
    if not predictions:
        raise RuntimeError('no annual model has at least 60 mature monthly training signals')
    return pd.concat(predictions,ignore_index=True)

def variants(pred):
    p=pred.copy()
    for col in ['compact21','compact63','tail',*GROUPS,'all']:
        p[col]=p.groupby('signal_date')[col].rank(method='average',pct=True)
    mix=.7*p.compact21+.3*p['tail']
    condition=(p.macro_category==p.top_macro)&(p.macro_gap>=.75)
    historical=mix+.15*(condition&(p['tail']>=.8))
    out={'baseline':historical,'macro_rule':mix+.15*(condition&(mix>=.8)),
         'compact_only':p.compact21,'blend85':.85*p.compact21+.15*p['tail'],
         'horizon63':.7*p.compact63+.3*p['tail']+.15*(condition&(p['tail']>=.8))}
    for group in [*GROUPS,'all']:
        out[group]=.8*historical+.2*p[group]
    panels={}
    for name,values in out.items():
        q=p[['signal_date','ticker']].copy();q['score']=values.groupby(p.signal_date).rank(method='average',pct=True);panels[name]=q
    return panels