#!/usr/bin/env python3
"""OLC33 prequential tail-event gate. Frozen pre-outcome protocol at GitHub commit 05b1d17.
No new tuning, labels only used in mature training and post-hoc evaluation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import brier_score_loss, average_precision_score, roc_auc_score

FEATURE = ['d_FUSION','d_ret_21','d_ret_63','d_ret_126','d_ret_252',
           'd_dd_63','d_vol_63','d_eff_63','d_sma_ratio_200','d_acc_21_63',
           'top5_dispersion_ret63','leader_ret63']
CONTRAST = ['FUSION','ret_21','ret_63','ret_126','ret_252','dd_63',
            'vol_63','eff_63','sma_ratio_200','acc_21_63']
TARGET_THRESHOLD_BP = 300.0
COST_BP = 20.0
TRIGGER_PROB = 0.40
TRIGGER_EXCESS = 0.10
SEED = 33001
YEARS = range(2021, 2027)
MAIN_YEAR_START, MAIN_YEAR_END = 2021, 2024


def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_pairs(src: Path):
    raw=pd.read_csv(src,parse_dates=['signal_date','source_date','entry_date','exit_date'])
    assert len(raw)==len(raw.drop_duplicates(['market','signal_date','ticker']))
    # Historical OLC32 data quality: no future feature snapshots.
    assert not (raw['source_date'].notna() & (raw.source_date > raw.signal_date)).any(), 'forward source_date'
    assert not raw.loc[(raw.market=='EU') & (raw.entry_date.dt.year==2020), 'entry_date'].astype(str).eq('2020-06-01').any()
    assert not raw.loc[(raw.market=='EU') & (raw.exit_date.dt.year==2020), 'exit_date'].astype(str).eq('2020-06-01').any()
    assert not raw.loc[(raw.market=='EU') & (raw.ticker=='LEEU.DE') & (raw.entry_date.dt.strftime('%Y-%m-%d')=='2024-05-02'), 'entry_price_observed'].any(), 'LEEU quote should not be marked observed'
    assert not raw.loc[raw.signal_date==pd.Timestamp('2026-06-30'), 'eligible_label'].any(), 'terminal pseudo-label'
    rows=[]
    for (market, date),g in raw.loc[raw.auth_rank<=5].groupby(['market','signal_date'], sort=True):
        g=g.sort_values(['auth_rank','ticker'])
        if g.auth_rank.tolist() != [1,2,3,4,5]:
            raise AssertionError(f'bad top5: {market} {date}: {g.auth_rank.tolist()}')
        lead=g.iloc[0]
        disp=np.std(g.ret_63.dropna().to_numpy(dtype=float),ddof=0) if g.ret_63.notna().sum()>=2 else np.nan
        for _,chall in g.iloc[1:].iterrows():
            row={'market':market,'signal_date':date,'year':date.year,
                 'challenger_rank':int(chall.auth_rank),'challenger':chall.ticker,
                 'incumbent':lead.ticker,
                 'exit_date':chall.exit_date,
                 'inc_exit_date':lead.exit_date,
                 'leader_ret63':lead.ret_63,
                 'top5_dispersion_ret63':disp,
                 'pair_features_asof':bool(lead.feature_available_asof and chall.feature_available_asof),
                 'inc_label_eligible':bool(lead.eligible_label),
                 'chal_label_eligible':bool(chall.eligible_label)}
            for key in CONTRAST:
                row['d_'+key] = chall[key]-lead[key]
            row['full_features']=bool(row['pair_features_asof'] and np.isfinite([row[k] for k in FEATURE]).all())
            # Outcomes are attached for training/evaluation only, never queried for scoring decisions.
            row['eval_valid']=bool(lead.eligible_label and chall.eligible_label and
                                   pd.notna(lead.r_o2o_bp) and pd.notna(chall.r_o2o_bp))
            row['spread_bp']=float(chall.r_o2o_bp-lead.r_o2o_bp) if row['eval_valid'] else np.nan
            row['net_spread_bp']=row['spread_bp']-COST_BP if row['eval_valid'] else np.nan
            row['y_plus']=int(row['net_spread_bp']>=TARGET_THRESHOLD_BP) if row['eval_valid'] else np.nan
            row['y_minus']=int(row['net_spread_bp']<=-TARGET_THRESHOLD_BP) if row['eval_valid'] else np.nan
            rows.append(row)
    pairs=pd.DataFrame(rows)
    assert len(pairs)==2*90*4, len(pairs)
    assert pairs.loc[pairs.signal_date==pd.Timestamp('2026-06-30'),'eval_valid'].eq(False).all()
    return pairs


def weighted_month_market(train:pd.DataFrame):
    group_sizes=train.groupby(['market','signal_date'])['challenger'].transform('size')
    per_month=train.groupby('market').signal_date.transform('nunique')
    weights=(1.0/group_sizes / per_month) # each market/period equal, 50/50 pooled
    return weights.to_numpy() * (len(weights)/weights.sum())


def score_oof(pairs:pd.DataFrame):
    scored=pairs.copy()
    scored['p1']=np.nan
    scored['p0']=np.nan
    scored['model_available']=False
    audit=[]
    coefficients=[]
    for year in YEARS:
        cutoff=pd.Timestamp(year=year,month=1,day=1)
        mature=scored.loc[(scored.exit_date<cutoff)&(scored.inc_exit_date<cutoff)&
                          scored.eval_valid&scored.full_features].copy()
        months=mature.groupby('market').signal_date.nunique().to_dict()
        weights=weighted_month_market(mature) if not mature.empty else np.array([])
        pos=int(mature.y_plus.sum())
        prior=float(np.average(mature.y_plus,weights=weights)) if len(mature) else np.nan
        can_train=(all(months.get(m,0)>=12 for m in ['EU','USA']) and pos>=20 and mature.y_plus.nunique()==2)
        this=scored.year==year
        enough=scored.loc[this & scored.full_features].index
        scored.loc[this,'p0']=prior
        model=None
        if can_train:
            model=make_pipeline(StandardScaler(), LogisticRegression(C=0.1,max_iter=1000,solver='lbfgs',random_state=SEED))
            model.fit(mature[FEATURE].to_numpy(dtype=float),mature.y_plus.astype(int).to_numpy(),logisticregression__sample_weight=weights)
            scored.loc[enough,'p1']=model.predict_proba(scored.loc[enough,FEATURE].to_numpy(dtype=float))[:,1]
            scored.loc[enough,'model_available']=True
            coef=model.named_steps['logisticregression']
            coefficients.append({'year':year,'intercept':float(coef.intercept_[0]),'features':dict(zip(FEATURE,coef.coef_[0].astype(float).tolist())),
                                 'fit_sample_count':len(mature),'train_last_exit':mature.exit_date.max().strftime('%Y-%m-%d')})
        audit.append({'year':year,'cutoff':str(cutoff.date()),'n_training':len(mature),'n_positive':pos,
                      'train_eligible_months_EU':months.get('EU',0),'train_eligible_months_USA':months.get('USA',0),
                      'P0_event_prior':prior,'trained':can_train,'forecast_pairs':len(enough)})
    return scored,pd.DataFrame(audit),coefficients


def make_decisions(scored:pd.DataFrame):
    decisions=[]
    for (market,date),g in scored.groupby(['market','signal_date'],sort=True):
        g=g.sort_values(['p1','challenger_rank','challenger'],ascending=[False,True,True],na_position='last')
        choice=g.iloc[0]
        has_model=bool(choice.model_available and np.isfinite(choice.p1) and np.isfinite(choice.p0))
        trigger=bool(has_model and choice.p1>=TRIGGER_PROB and choice.p1-choice.p0>=TRIGGER_EXCESS)
        lead_eligible=bool(choice.inc_label_eligible)
        # No outcome-based decision: actual chosen challenger even if label later missing.
        row={'market':market,'signal_date':date,'year':date.year,'incumbent':choice.incumbent,
             'challenger':choice.challenger if has_model else None,
             'challenger_rank':int(choice.challenger_rank) if has_model else None,
             'p1':float(choice.p1) if has_model else None,
             'p0':float(choice.p0) if pd.notna(choice.p0) else None,
             'switch':trigger,'model_available':has_model,
             'inc_label_eligible':lead_eligible,
             'chosen_eval_valid':bool(choice.eval_valid) if trigger else True,
             'eval_valid':bool(lead_eligible and (not trigger or choice.eval_valid)),
             'net_gain_bp':float(choice.net_spread_bp) if trigger and choice.eval_valid else (0. if not trigger and lead_eligible else np.nan),
             'y_plus':float(choice.y_plus) if trigger and choice.eval_valid else np.nan,
             'y_minus':float(choice.y_minus) if trigger and choice.eval_valid else np.nan}
        decisions.append(row)
    return pd.DataFrame(decisions)


def macro_brier(grp:pd.DataFrame, col:str):
    return grp.groupby('signal_date').apply(lambda x:np.mean((x[col]-x.y_plus)**2),include_groups=False).mean()


def metrics_market(scored:pd.DataFrame,decisions:pd.DataFrame, market:str,start:int=MAIN_YEAR_START,end:int=MAIN_YEAR_END):
    x=scored.loc[(scored.market==market)&scored.year.between(start,end)&scored.eval_valid&scored.model_available].copy()
    d=decisions.loc[(decisions.market==market)&decisions.year.between(start,end)].copy()
    active=d.loc[d.switch & d.eval_valid]
    unacted=scored.loc[(scored.market==market)&scored.year.between(start,end)&scored.eval_valid].copy()
    if len(active):
        acted_key=set(zip(active.signal_date.astype(str),active.challenger))
        unacted=unacted.loc[~unacted.apply(lambda r:(str(r.signal_date),r.challenger) in acted_key,axis=1)]
    null_rate=float(unacted.y_plus.mean()) if len(unacted) else np.nan
    null_bad=float(unacted.y_minus.mean()) if len(unacted) else np.nan
    valid_d=d.loc[d.eval_valid]
    rows={'market':market,'period':f'{start}-{end}',
          'n_months':len(d),'n_incumbent_evaluable':int(d.inc_label_eligible.sum()),
          'n_evaluable_strategy_months':len(valid_d),'n_unverifiable_actions':int((d.switch&~d.eval_valid).sum()),
          'n_candidate_pairs_evaluable':int(len(x)),
          'n_model_forecast_pairs':int(scored.loc[(scored.market==market)&scored.year.between(start,end)&scored.model_available].shape[0]),
          'n_actions':int(d.switch.sum()),'n_actions_evaluable':len(active),
          'n_positive_events_scored':int(x.y_plus.sum()),
          'event_rate_all_scored':float(x.y_plus.mean()) if len(x) else np.nan,
          'brier_p0':float(macro_brier(x,'p0')) if len(x) else np.nan,
          'brier_p1':float(macro_brier(x,'p1')) if len(x) else np.nan,
          'auprc_p1':float(average_precision_score(x.y_plus,x.p1)) if len(x) and x.y_plus.nunique()==2 else np.nan,
          'precision_actions':float(active.y_plus.mean()) if len(active) else np.nan,
          'reference_yplus_unselected':null_rate,
          'precision_uplift':float(active.y_plus.mean()/null_rate) if len(active) and null_rate>0 else np.nan,
          'risk_yminus_actions':float(active.y_minus.mean()) if len(active) else np.nan,
          'reference_yminus_unselected':null_bad,
          'mean_net_gain_bp_all_evaluable':float(valid_d.net_gain_bp.mean()) if len(valid_d) else np.nan,
          'median_net_gain_bp_all_evaluable':float(valid_d.net_gain_bp.median()) if len(valid_d) else np.nan,
          'min_net_gain_bp_all_evaluable':float(valid_d.net_gain_bp.min()) if len(valid_d) else np.nan,
          'sum_net_gain_bp_all_evaluable':float(valid_d.net_gain_bp.sum()) if len(valid_d) else np.nan,
          'mean_net_gain_bp_actions':float(active.net_gain_bp.mean()) if len(active) else np.nan}
    rows['gate_brier']=bool(rows['brier_p1']<rows['brier_p0'])
    rows['gate_precision']=bool(rows['n_actions_evaluable']>=12 and rows['precision_uplift']>=1.5)
    rows['gate_positive_mean']=bool(rows['mean_net_gain_bp_all_evaluable']>0)
    rows['gate_downside']=bool(rows['n_actions_evaluable']>=12 and rows['risk_yminus_actions']<=rows['reference_yminus_unselected'])
    return rows


def paired_bootstrap(decisions:pd.DataFrame,start=2021,end=2024,nboot=2000,block=6):
    d=decisions.loc[decisions.year.between(start,end)&decisions.eval_valid,['market','signal_date','net_gain_bp']].copy()
    # Match EU and USA by economic calendar month, not identical signal-day.
    d['calendar_month']=d.signal_date.dt.to_period('M')
    tab=d.pivot(index='calendar_month',columns='market',values='net_gain_bp').sort_index().reindex(columns=['EU','USA'])
    assert len(tab)==48, len(tab)
    data=tab.to_numpy(dtype=float)
    months=len(tab)
    rng=np.random.default_rng(SEED)
    means=[]
    for _ in range(nboot):
        ix=[]
        for j in range(int(np.ceil(months/block))):
            a=rng.integers(0,months-block+1)
            ix.extend(range(a,a+block))
        sample=data[np.array(ix[:months]),:]
        means.append(float(np.nanmean(sample)))
    means=np.asarray(means)
    return {'estimator':'EU-USA paired 6-month moving block bootstrap of monthly net spread, mean over available month-market',
            'nboot':nboot,'seed':SEED,'block_months':block,'monthly_net_mean_bp':float(np.nanmean(data)),
            'ci_low':float(np.quantile(means,.025)),'ci_high':float(np.quantile(means,.975)),
            'n_missing_cells':int(np.isnan(data).sum()),
            'gate_bootstrap':bool(np.quantile(means,.025)>0)}


def negative_control_leakage(scored:pd.DataFrame):
    # Deterministic causality assertions about model training: fit cutoffs in audit; no label feature in FEATURE.
    forbidden={'y_plus','y_minus','r_o2o_bp','r_rel_bp','net_spread_bp','eligible_label','exit_date','ticker','market'}
    assert not forbidden.intersection(FEATURE)
    assert (scored.loc[scored.model_available,'pair_features_asof']).all()
    assert (scored.loc[scored.model_available].full_features).all()
    assert scored.loc[scored.model_available].p1.between(0,1).all()
    return True


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--input',required=True)
    ap.add_argument('--out',required=True)
    opt=ap.parse_args()
    out=Path(opt.out);out.mkdir(parents=True,exist_ok=True)
    src=Path(opt.input)
    assert sha256(src)=='83b5190501ba79029e1677d719a22893eaa98bddeb6042de2a46a885bca32d16', 'SOURCE SHA MISMATCH'
    pairs=load_pairs(src)
    scored,audit,coefs=score_oof(pairs)
    negative_control_leakage(scored)
    decisions=make_decisions(scored)
    records=[metrics_market(scored,decisions,m) for m in ['EU','USA']]
    bootstrap=paired_bootstrap(decisions)
    gates={key:all(r[key] for r in records) for key in ['gate_brier','gate_precision','gate_positive_mean','gate_downside']}
    gates['gate_bootstrap']=bootstrap['gate_bootstrap']
    gates['all_success']=all(gates.values())
    result={'protocol_commit':'05b1d1735e2528e0f0512dbf029d1831057cce52',
            'source_sha256':sha256(src),'metrics':records,'bootstrap':bootstrap,'gates':gates,
            'audit':{'pairs':len(pairs),'months':int(scored.signal_date.nunique()),
                     'models_by_year':audit.to_dict(orient='records'),'coefficients':coefs,
                     'asof_invalid':int((~pairs.pair_features_asof).sum()),
                     'full_feature_rows':int(pairs.full_features.sum()),
                     'evaluated_pairs':int(pairs.eval_valid.sum())}}
    scored.to_csv(out/'OLC33_OOF_PAIRS.csv.gz',index=False,compression='gzip')
    decisions.to_csv(out/'OLC33_DECISIONS.csv',index=False)
    audit.to_csv(out/'OLC33_TRAIN_AUDIT.csv',index=False)
    pd.DataFrame(records).to_csv(out/'OLC33_MARKET_METRICS.csv',index=False)
    (out/'OLC33_RESULTS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    (out/'OLC33_MANIFEST.json').write_text(json.dumps({'script':'olc33_tail_condition.py',
        'python':sys.version,'pandas':pd.__version__,'numpy':np.__version__,
        'source_sha256':sha256(src),'generated_sha256':{p.name:sha256(p) for p in sorted(out.iterdir()) if p.is_file() and p.name!='OLC33_MANIFEST.json'}},indent=2),encoding='utf-8')
    print('OLC33',json.dumps({'metrics':records,'bootstrap':bootstrap,'gates':gates},indent=2))

if __name__=='__main__':main()
