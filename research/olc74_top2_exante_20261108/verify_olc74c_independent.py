#!/usr/bin/env python3
"""OLC74C separate path QA: market-month branch labels, maturity, annuals, daily CAGR/DD.
This verifier does not share OLC74C's runtime simulation helpers."""
from pathlib import Path
import json
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parent;R=ROOT/'results'

def main():
    labels=pd.read_csv(R/'OLC74C_ON_POLICY_COUNTERFACTUAL_LABELS.csv',parse_dates=['date']);route=pd.read_csv(R/'OLC74C_ON_POLICY_ROUTE.csv',parse_dates=['date']);pred=pd.read_csv(R/'OLC74C_FORECAST_SKILL.csv',parse_dates=['date']);orig=pd.read_csv(R/'OLC74_PAIR_PANEL.csv')
    score=pd.read_csv(R/'OLC74C_SCORECARD.csv');annual=pd.read_csv(R/'OLC74C_ANNUAL.csv');daily=pd.read_csv(R/'OLC74C_DAILY_LOGRET.csv.gz');daily.date=pd.to_datetime(daily.date)
    assert len(labels)==178 and len(route)==178 and len(score)==36 and len(annual)==32 and len(pred)==128
    assert len(labels.drop_duplicates(['market','pos']))==178
    assert ((route.w1>=.25)&(route.w1<=.75)).all() and (route.w1+route.w2-1).abs().max()<1e-12
    assert np.allclose(labels.marginal_y_logbp,labels.w75_bp-labels.w25_bp,rtol=0,atol=1e-10)
    joined=route.merge(labels[['market','pos','marginal_y_logbp']],on=['market','pos'],validate='one_to_one')
    assert (joined.same_state_effect_bp_EXPOST-joined.marginal_y_logbp).abs().max()<1e-10
    assert (pred.max_train_pos<=pred.pos-2).all()
    for m,z in pred.groupby('market'):
        assert len(z)==64 and z.n_train.min()>=24
    maxdiff=0.;n=0
    for v in score.itertuples(index=False):
        d=daily[(daily.key==v.key)&(daily.date>=v.first_valuation)&(daily.date<=v.last_valuation)].sort_values('date');x=d.logr.to_numpy()
        assert len(d)==v.n
        c=float(np.expm1(252*x.mean()))
        eq=np.exp(np.cumsum(x));peak=np.maximum.accumulate(np.r_[1.,eq]);dd=float(np.min(eq/peak[1:]-1))
        diff=max(abs(c-v.cagr),abs(dd-v.maxdd));assert diff<1e-10
        maxdiff=max(maxdiff,diff);n+=1
    for r in annual.itertuples(index=False):
        z=daily[(daily.market==r.market)&(daily.policy==r.policy)&(daily.timing==r.timing)&(daily.fee==r.fee)&(daily.date.dt.year==r.year)]
        # OLC74C annual CSV order: market, policy, timing, fee, year, n, return.
        assert len(z)==r.n and abs(float(np.expm1(z.logr.to_numpy().sum()))-r[-1])<1e-10
    out={'status':'PASS','same_state_event_triplets':178,'on_policy_refits':128,'model_feature_asof_checked_in_OLC74A':True,'train_lag_two_events':True,'native_replay_7arrays_bitwise_confirmed_in_OLC74C_QA':True,'independently_recomputed_periods':n,'recomputed_annual_rows':len(annual),'max_abs_cagr_or_dd_error':maxdiff,'price_fixed_counterfactual_only':True}
    (R/'OLC74C_INDEPENDENT_QA.json').write_text(json.dumps(out,indent=2))
    print(json.dumps(out,indent=2))
if __name__=='__main__':main()