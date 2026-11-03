#!/usr/bin/env python3
"""OLC34: incremental predictive value of strictly lagged CBOE VIX context.
Prerecorded model and decision rules: GitHub OLC34 commit 320d11c (2026-11-03).
No adaptive threshold selection. Annual strictly mature walk-forward.
Usage: python olc34_vix_context.py --input .../OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz --vix .../OLC34_VIX_ASOF_SIGNAL.csv --baseline-src .../olc33_tail_condition.py --out ...
"""
from __future__ import annotations
import argparse, importlib.util, hashlib, json, platform
from pathlib import Path
import numpy as np
import pandas as pd
import sklearn
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import average_precision_score

SOURCE_SHA='83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16'
VIX_BLOB_SHA='762fe8cd591b45cae78a869e8b1541e14fc87188'
MAIN_YEARS=range(2021,2025)
SEED=34001
COST_BP=20
THRESHOLD=300


def sha256(p:Path):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()


def git_blob_sha(p:Path):
    b=p.read_bytes()
    return hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()


def load_baseline(path:Path):
    spec=importlib.util.spec_from_file_location('olc33_original_frozen',path)
    m=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def load_augmented_pairs(input_file:Path,vix_file:Path,olc33):
    assert sha256(input_file)==SOURCE_SHA,'OLC32 input mismatch'
    assert git_blob_sha(vix_file)==VIX_BLOB_SHA,'VIX snapshot Git blob mismatch'
    vix=pd.read_csv(vix_file,parse_dates=['signal_date','vix_asof_date'])
    assert not vix.signal_date.duplicated().any()
    assert len(vix)==91
    assert vix.signal_date.min()==pd.Timestamp('2019-01-31')
    assert vix.signal_date.max()==pd.Timestamp('2026-06-30')
    assert ((vix.signal_date-vix.vix_asof_date).dt.days==vix.lag_days).all()
    assert vix.lag_days.between(1,7).all()
    assert np.isfinite(vix[['vix_close','vix_21ago_close','log_vix_change_21']]).all().all()
    assert (vix[['vix_close','vix_21ago_close']]>0).all().all()
    assert np.max(np.abs(np.log(vix.vix_close/vix.vix_21ago_close)-vix.log_vix_change_21))<5e-13
    p=olc33.load_pairs(input_file)
    out=p.merge(vix[['signal_date','vix_asof_date','vix_close','log_vix_change_21','lag_days']],on='signal_date',how='left',validate='many_to_one')
    assert len(out)==len(p)
    assert out.vix_close.notna().all()
    assert (out.vix_asof_date<out.signal_date).all()
    out['vix_features_finite']=np.isfinite(out[['vix_close','log_vix_change_21']]).all(axis=1)
    out['full_vix_features']=out.full_features & out.vix_features_finite
    # Important: no outcome-dependent filtering in live prediction support.
    assert int((~out.vix_features_finite).sum())==0
    return out


def score_olc34(pairs,olc33):
    base,baudit,bcoefs=olc33.score_oof(pairs)
    base['p2']=np.nan
    base['p2_available']=False
    A=olc33.FEATURE+['vix_close','log_vix_change_21']
    forbidden={'r_o2o_bp','r_rel_bp','label_valid','eligible_label','spread_bp','net_spread_bp','y_plus','y_minus','market','year','ticker','auth_rank','exit_date'}
    assert not forbidden.intersection(A)
    fits=[]
    coefs=[]
    for year in olc33.YEARS:
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        matured=base.loc[base.exit_date.lt(cutoff)&base.inc_exit_date.lt(cutoff)&base.eval_valid&base.full_features&base.full_vix_features].copy()
        months=matured.groupby('market').signal_date.nunique().to_dict()
        pos=int(matured.y_plus.sum())
        can=all(months.get(x,0)>=12 for x in ['EU','USA']) and pos>=20 and matured.y_plus.nunique()==2
        old=baudit.loc[baudit.year==year].iloc[0]
        assert can==bool(old.trained),'OLC33 and OLC34 must have identical model availability'
        assert int(old.n_training)==len(matured),'OLC33 and OLC34 must have identical training support'
        scored=base.loc[base.year.eq(year)&base.full_vix_features].copy()
        weights=olc33.weighted_month_market(matured) if len(matured) else np.array([])
        if can:
            model=make_pipeline(StandardScaler(), LogisticRegression(C=.1,max_iter=1000,solver='lbfgs',random_state=33001))
            model.fit(matured[A].to_numpy(dtype=float),matured.y_plus.astype(int).to_numpy(),logisticregression__sample_weight=weights)
            base.loc[scored.index,'p2']=model.predict_proba(scored[A].to_numpy(dtype=float))[:,1]
            base.loc[scored.index,'p2_available']=True
            c=model.named_steps['logisticregression'];coefs.append({'year':year,'intercept':float(c.intercept_[0]),'coefficients':dict(zip(A,c.coef_[0].tolist()))})
        fits.append({'year':year,'n_training':len(matured),'positive':pos,'EU_mature_months':int(months.get('EU',0)),'USA_mature_months':int(months.get('USA',0)),'last_mature_exit':str(matured.exit_date.max().date()) if len(matured) else None,'n_forecast_pairs':len(scored),'trained':bool(can)})
    assert (base.p2_available==base.model_available).all(),'P1/P2 availability mismatch'
    assert np.all(base.loc[base.p2_available,'p2'].between(0,1))
    return base,baudit,fits,coefs


def decisions_from(scored,olc33):
    x=scored.copy()
    x['p1']=x['p2']
    x['model_available']=x['p2_available']
    ret=olc33.make_decisions(x)
    return ret.rename(columns={'p1':'p2'})


def _macro_brier(month_pairs,name):
    return month_pairs.groupby('signal_date').apply(lambda x:float(np.mean((x[name]-x.y_plus)**2)),include_groups=False).mean()


def market_results(scored,p1dec,p2dec,market:str,start=2021,end=2024):
    x=scored.loc[scored.market.eq(market)&scored.year.between(start,end)&scored.eval_valid&scored.model_available&scored.p2_available].copy()
    d=p2dec.loc[p2dec.market.eq(market)&p2dec.year.between(start,end)].copy()
    d1=p1dec.loc[p1dec.market.eq(market)&p1dec.year.between(start,end)].copy()
    assert len(d)==len(d1)==48 if (start,end)==(2021,2024) else True
    pair=d.merge(d1[['signal_date','eval_valid','net_gain_bp']],on='signal_date',suffixes=('_p2','_p1'),validate='one_to_one')
    p=pair.loc[pair.eval_valid_p1&pair.eval_valid_p2]
    active=d.loc[d.switch & d.eval_valid]
    acted=set(zip(active.signal_date.astype(str),active.challenger))
    unselected=x.loc[~x.apply(lambda r:(str(r.signal_date),r.challenger) in acted,axis=1)]
    n_month=int(d.signal_date.nunique())
    b0=float(_macro_brier(x,'p0'))
    b1=float(_macro_brier(x,'p1'))
    b2=float(_macro_brier(x,'p2'))
    res={'market':market,'period':f'{start}-{end}', 'months':n_month, 'pairs_scored':int(len(x)),
         'p0_brier':b0,'p1_brier':b1,'p2_brier':b2,'p1_minus_p2_brier':b1-b2,'p0_minus_p2_brier':b0-b2,
         'p2_average_precision':float(average_precision_score(x.y_plus,x.p2)),
         'p1_average_precision':float(average_precision_score(x.y_plus,x.p1)),
         'p0_event_rate':float(x.y_plus.mean()),
         'p2_actions':int(d.switch.sum()),'p2_actions_evaluable':int(len(active)),
         'p1_actions':int(d1.switch.sum()),'p2_extreme_positive':int(active.y_plus.sum()),
         'p2_extreme_negative':int(active.y_minus.sum()),
         'p2_precision':float(active.y_plus.mean()) if len(active) else None,
         'null_event_rate_unselected':float(unselected.y_plus.mean()) if len(unselected) else None,
         'p2_negative_rate':float(active.y_minus.mean()) if len(active) else None,
         'null_negative_rate_unselected':float(unselected.y_minus.mean()) if len(unselected) else None,
         'p2_net_mean_bp_per_month':float(d.loc[d.eval_valid,'net_gain_bp'].mean()),
         'p1_net_mean_bp_per_month':float(d1.loc[d1.eval_valid,'net_gain_bp'].mean()),
         'p2_net_total_bp':float(d.loc[d.eval_valid,'net_gain_bp'].sum()),
         'p2_minus_p1_mean_bp':float((p.net_gain_bp_p2-p.net_gain_bp_p1).mean()),
         'common_evaluable_months':len(p),
         'p2_worst_net_month_bp':float(d.loc[d.eval_valid,'net_gain_bp'].min()),
         'p2_missing_action_labels':int((d.switch&(~d.eval_valid)).sum())}
    r=res
    r['gate_brier']=bool(b2<b1 and b2<b0)
    r['gate_precision']=bool(r['p2_actions_evaluable']>=12 and r['p2_precision'] is not None and r['p2_precision']>=1.5*r['null_event_rate_unselected'])
    r['gate_econ']=bool(r['p2_net_mean_bp_per_month']>0 and r['p2_minus_p1_mean_bp']>0)
    r['gate_downside']=bool(r['p2_actions_evaluable']>=12 and r['p2_negative_rate'] is not None and r['p2_negative_rate']<=r['null_negative_rate_unselected'])
    return res


def month_panel(scored,p1dec,p2dec):
    f=scored.loc[scored.year.between(2021,2024)&scored.eval_valid&scored.model_available&scored.p2_available].copy()
    for name in ['p0','p1','p2']:
        f['se_'+name]=(f[name]-f.y_plus)**2
    met=f.groupby(['market','signal_date'],as_index=False)[['se_p0','se_p1','se_p2']].mean()
    p2=p2dec.loc[p2dec.year.between(2021,2024),['market','signal_date','net_gain_bp','eval_valid']].rename(columns={'net_gain_bp':'net_p2','eval_valid':'valid_p2'})
    p1=p1dec.loc[p1dec.year.between(2021,2024),['market','signal_date','net_gain_bp','eval_valid']].rename(columns={'net_gain_bp':'net_p1','eval_valid':'valid_p1'})
    met=met.merge(p2,on=['market','signal_date'],validate='one_to_one').merge(p1,on=['market','signal_date'],validate='one_to_one')
    met['month']=met.signal_date.dt.to_period('M').astype(str)
    met['se_gain_p2_vs_p1']=met.se_p1-met.se_p2
    met['econ_gain_p2_vs_p1']=met.net_p2-met.net_p1
    return met.sort_values(['month','market'])


def block_bootstrap(mp,field,seed=SEED,nboot=2000,block=6):
    tab=mp.pivot(index='month',columns='market',values=field).sort_index().reindex(columns=['EU','USA'])
    assert tab.shape==(48,2)
    x=tab.to_numpy(dtype=float)
    rng=np.random.default_rng(seed)
    boots=np.empty(nboot)
    for b in range(nboot):
        idx=[]
        for j in range(int(np.ceil(48/block))):
            start=int(rng.integers(0,48-block+1));idx.extend(range(start,start+block))
        boots[b]=float(np.nanmean(x[np.array(idx[:48])]))
    return {'point_mean':float(np.nanmean(x)),'ci_low':float(np.quantile(boots,.025)),'ci_high':float(np.quantile(boots,.975)),'nboot':nboot,'block_months':block,'seed':seed,'missing_market_months':int(np.isnan(x).sum())},boots


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--vix',type=Path,required=True)
    ap.add_argument('--baseline-src',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    opts=ap.parse_args();opts.out.mkdir(parents=True,exist_ok=True)
    olc33=load_baseline(opts.baseline_src)
    pairs=load_augmented_pairs(opts.input,opts.vix,olc33)
    scored,baudit,fits,coefs=score_olc34(pairs,olc33)
    p1dec=olc33.make_decisions(scored)
    p2dec=decisions_from(scored,olc33)
    prim=[market_results(scored,p1dec,p2dec,m) for m in ['EU','USA']]
    secondary=[market_results(scored,p1dec,p2dec,m,2025,2025) for m in ['EU','USA']]
    mp=month_panel(scored,p1dec,p2dec)
    bb_brier,ds=block_bootstrap(mp,'se_gain_p2_vs_p1')
    bb_econ,ds_e=block_bootstrap(mp,'net_p2')
    bb_increment,ds_i=block_bootstrap(mp,'econ_gain_p2_vs_p1')
    gates={
      'brier_both':all(r['gate_brier'] for r in prim),
      'brier_bootstrap_lower_gt_0':bb_brier['ci_low']>0,
      'precision_both':all(r['gate_precision'] for r in prim),
      'economic_both':all(r['gate_econ'] for r in prim),
      'econ_bootstrap_lower_gt_0':bb_econ['ci_low']>0,
      'downside_both':all(r['gate_downside'] for r in prim),
    }
    gates['all_pass']=all(gates.values())
    output={'pre_outcome_protocol_commit':'320d11c9c29180f669f54dd45f92bb01b4d4e043',
            'source':{'olc32_sha256':sha256(opts.input),'vix_snapshot_git_blob':git_blob_sha(opts.vix),'vix_daily_remote_github_blob':'c05e0d9c28ddf3b98d0531017ef5b5180df05ae1'},
            'metrics_main_2021_2024':prim,'metrics_secondary_2025':secondary,
            'bootstrap_brier_p1_minus_p2':bb_brier,'bootstrap_economic_p2_vs_top1':bb_econ,'bootstrap_economic_p2_minus_p1':bb_increment,
            'gates':gates,'train_audit':fits,
            'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__}}
    (opts.out/'OLC34_RESULTS.json').write_text(json.dumps(output,indent=2,ensure_ascii=False))
    pd.DataFrame(fits).to_csv(opts.out/'OLC34_TRAIN_AUDIT.csv',index=False)
    pd.DataFrame(coefs).to_json(opts.out/'OLC34_COEFFICIENTS.json',orient='records',indent=2)
    pd.DataFrame(prim+secondary).to_csv(opts.out/'OLC34_MARKET_METRICS.csv',index=False)
    scored.to_csv(opts.out/'OLC34_PREQUENTIAL_PAIRS.csv.gz',index=False,compression={'method':'gzip','compresslevel':6,'mtime':0})
    p2dec.to_csv(opts.out/'OLC34_DECISIONS.csv',index=False)
    mp.to_csv(opts.out/'OLC34_MONTHLY_METRICS.csv',index=False)
    pd.DataFrame({'brier_diff':ds,'economic_net_p2':ds_e,'econ_increment_p2_vs_p1':ds_i}).to_csv(opts.out/'OLC34_BLOCK_BOOTSTRAP_DRAWS.csv',index=False)
    manifest={p.name:{'sha256':sha256(p),'bytes':p.stat().st_size} for p in sorted(opts.out.iterdir()) if p.is_file()}
    (opts.out/'OLC34_OUTPUT_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
    print(json.dumps({'metrics':prim,'boot_brier':bb_brier,'boot_econ':bb_econ,'boot_increment':bb_increment,'gates':gates,'output_files':list(manifest)},indent=2))
    return output


if __name__=='__main__':main()