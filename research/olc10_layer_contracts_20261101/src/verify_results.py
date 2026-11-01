"""Independent checks of targets, loss, rankings, maturity and causal-prefix fits."""
from pathlib import Path
import sys,json,hashlib
import numpy as np,pandas as pd
from sklearn.metrics import ndcg_score
from calibration import mature_history,month_weights,fit_affine,fit_stack
from recovery_core import atomic_json
from run_experiment import ROOT,I,O,readcsv,source,prepare_labels,merged
rng=np.random.default_rng(20261101);errors=[];prefix=[];checked=0
# Independently compare NDCG against the separately maintained sklearn implementation.
from layer_metrics import ndcg,topk_weights
for _ in range(200):
    n=int(rng.integers(5,100));y=rng.integers(0,16,n).astype(float);s=rng.integers(0,20,n).astype(float)
    for k in (2,5):
        a=ndcg(y,s,k);b=ndcg_score(y[None,:],s[None,:],k=k)
        errors.append(abs(a-b));assert abs(a-b)<1e-12;checked+=1
# Recompute every principal calibration monthly MSE directly from saved predictions.
t=pd.read_csv(O/'TARGET_MONTHS.csv');loss_checks=0;target_checks=0
for market in ['EU','USA']:
    p=readcsv(O/f'{market}_CALIBRATED_PREDICTIONS.csv.gz')
    # Source target equation checked without calling the shared target helper.
    manual=np.sum(np.column_stack([p.target_rank_21.to_numpy()**1.5*.45,p.target_rank_42.to_numpy()**1.5*.35,p.target_rank_63.to_numpy()**1.5*.20]),axis=1)
    np.testing.assert_allclose(manual,p.TARGET,rtol=0,atol=2e-16,equal_nan=True);target_checks+=len(p)
    mapping={'CAL_AFFINE':'AFFINE_TARGET','CAL_STACK2':'STACK2_TARGET','SHRINK50':'SHRINK50_TARGET','RAW_TARGET_RANK':'RAW_TARGET','MEAN_ONLY':'MEAN_TARGET','REF_RSI':'RAW_TARGET'}
    for name,col in mapping.items():
        for row in t[(t.market==market)&t.variant.eq(name)].itertuples():
            g=p[p.signal_date.eq(pd.Timestamp(row.date))]
            g=g[np.isfinite(g[['ET_RAW','XGB_RAW']]).all(axis=1)]
            assert len(g)==row.n and np.isfinite(g.TARGET).all()
            loss=float(sum((g[col].to_numpy()-g.TARGET.to_numpy())**2)/len(g));errors.append(abs(loss-row.mse));assert abs(loss-row.mse)<1e-13;loss_checks+=1
    # Calibration must be invariant to any future outcome or future forecast edits.
    for year in (2021,2023,2025):
        cut=pd.Timestamp(year,1,1);f=p.copy();mask=(f.signal_date>=cut)|(f.exit_date_63>=cut)|f.exit_date_63.isna()
        f.loc[mask,'TARGET']=rng.random(mask.sum());f.loc[mask,['ET_RAW','XGB_RAW']]=rng.random((mask.sum(),2))
        a=mature_history(p,cut);b=mature_history(f,cut);pd.testing.assert_frame_equal(a,b)
        w=month_weights(a.signal_date);m1=fit_stack(a[['ET_RAW','XGB_RAW']],a.TARGET,w);m2=fit_stack(b[['ET_RAW','XGB_RAW']],b.TARGET,w)
        assert m1==m2
        # Verify archived coefficients rather than just relying on log assertions.
        saved=json.loads((O/'calibrators'/f'{market}_{year}.json').read_text())
        for c in ['coef','intercept']:np.testing.assert_allclose(saved['stack2'][c],m1[c],rtol=0,atol=1e-13)
        prefix.append({'market':market,'year':year,'mutated_future_rows':int(mask.sum()),'exact_past_training_identity':True})
# Unchanged rank-channel identities are checked for every monthly primary metric.
ref=t[t.variant=='REF_RSI'].set_index(['market','period','date'])
for v in ['CAL_AFFINE','SHRINK50']:
    a=t[t.variant==v].set_index(['market','period','date'])
    assert a.index.equals(ref.index)
    for c in ['ndcg2','ndcg5','ic','selected_target','target_regret','target_top_quintile_precision','target_bottom_quintile_fraction']:
        np.testing.assert_allclose(a[c],ref[c],rtol=0,atol=0,equal_nan=True)
# All summaries are monthly means, not pooled ticker observations.
s=pd.read_csv(O/'TARGET_SUMMARY.csv')
for row in s.itertuples():
    q=t[(t.market==row.market)&(t.variant==row.variant)&(t.period==row.period)]
    assert len(q)==row.months
    for c in ['mse','ndcg2','ndcg5','ic','target_regret']:
        val=q[c].mean();rep=getattr(row,c)
        if np.isnan(val):assert np.isnan(rep)
        else:assert abs(val-rep)<1e-13
atomic_json(O/'VERIFICATION.json',{'sklearn_tie_aware_ndcg_checks':checked,'source_target_row_checks':target_checks,'independent_monthly_loss_checks':loss_checks,'summary_rows_checked':len(s),'max_numeric_error':max(errors),'causal_label_and_forecast_perturbations':prefix,'rank_channel_unchanged':['CAL_AFFINE','SHRINK50'],'no_portfolio_replay_claimed':True,'review':'Author verification, not independent reviewer'})
print(json.dumps(json.loads((O/'VERIFICATION.json').read_text()),indent=2))
