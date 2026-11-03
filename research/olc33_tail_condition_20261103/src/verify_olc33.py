#!/usr/bin/env python3
"""Independent OLC33 data/forecast verification, no model tuning."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import pandas as pd

S=Path(__file__).resolve().parent/'olc33_tail_condition.py'
spec=importlib.util.spec_from_file_location('olc33',S)
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SRC=Path('/mnt/data/olc32/unpacked/results/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz')
OUT=Path('/mnt/data/olc33/results')
raw=pd.read_csv(SRC,parse_dates=['signal_date','source_date','entry_date','exit_date'])
raw5=raw[raw.auth_rank<=5].copy()
inc=raw5[raw5.auth_rank==1][['market','signal_date','ticker','eligible_label','r_o2o_bp','exit_date']]
inc=inc.rename(columns={'ticker':'leader_ticker','eligible_label':'leader_valid','r_o2o_bp':'leader_ret','exit_date':'leader_exit'})
alt=raw5[raw5.auth_rank>1][['market','signal_date','ticker','eligible_label','r_o2o_bp','auth_rank']]
join=alt.merge(inc,on=['market','signal_date'],how='left',validate='many_to_one')
join['pair_valid']=(join.eligible_label&join.leader_valid&join.r_o2o_bp.notna()&join.leader_ret.notna())
join['independent_spread']=np.where(join.pair_valid,join.r_o2o_bp-join.leader_ret,np.nan)
calc=m.load_pairs(SRC)
merged=calc.merge(join,left_on=['market','signal_date','challenger'],right_on=['market','signal_date','ticker'],validate='one_to_one')
assert len(merged)==len(calc)==720
valid=merged.eval_valid
max_pair_error=float(np.nanmax(abs(merged.loc[valid,'spread_bp']-merged.loc[valid,'independent_spread'])))
assert max_pair_error < 1e-9,max_pair_error
assert (merged['eval_valid'].to_numpy()==merged['pair_valid'].to_numpy()).all()
# One-month horizon. Case: two national markets can have different signal dates in the same calendar month.
assert merged.loc[merged.eval_valid].groupby(['market','signal_date']).exit_date.nunique().max()==1
# Source-label gate exactly as inherited; never alter terminal.
assert not merged.loc[merged.signal_date==pd.Timestamp('2026-06-30'),'eval_valid'].any()
# More stringent anti-leakage: changes to 2024 outcomes cannot alter forecast 2021-2024,
# because the earliest model with 2024 mature labels is 2025-01-01.
scored_a, audit_a, coef_a=m.score_oof(calc)
pert=calc.copy()
ix=(pert.signal_date.dt.year==2024)&(pert.eval_valid)
pert.loc[ix,'y_plus']=1-pert.loc[ix,'y_plus']
scored_b, audit_b, coef_b=m.score_oof(pert)
pre=scored_a.year.between(2021,2024)
max_pre_diff=float(np.nanmax(np.abs(scored_a.loc[pre,'p1'].to_numpy()-scored_b.loc[pre,'p1'].to_numpy())))
assert max_pre_diff==0.0
post=scored_a.year==2025
post_model_changes=int(np.sum(~np.isclose(scored_a.loc[post,'p1'].to_numpy(),scored_b.loc[post,'p1'].to_numpy(),equal_nan=True)))
assert post_model_changes>0
# Strict rerun deterministic against saved artifacts, after perturbation re-score original.
saved=pd.read_csv(OUT/'OLC33_OOF_PAIRS.csv.gz',parse_dates=['signal_date','exit_date','inc_exit_date'])
assert len(saved)==len(scored_a)
max_score_diff=float(np.nanmax(np.abs(saved.p1.to_numpy()-scored_a.p1.to_numpy())))
assert max_score_diff<1e-12, max_score_diff
saved_dec=pd.read_csv(OUT/'OLC33_DECISIONS.csv',parse_dates=['signal_date'])
regenerated=m.make_decisions(scored_a)
assert saved_dec['switch'].to_numpy().tolist()==regenerated['switch'].to_numpy().tolist()
assert np.allclose(saved_dec['net_gain_bp'].to_numpy(),regenerated['net_gain_bp'].to_numpy(),equal_nan=True)
assert not (calc.loc[calc.eval_valid].inc_exit_date!=calc.loc[calc.eval_valid].exit_date).any()
# Cross check total actions, mean gains and expected exact net accounting.
main=regenerated[regenerated.year.between(2021,2024)]
assert main.groupby('market')['switch'].sum().to_dict()=={'EU':1,'USA':7}
# Calendar 2020 fix: corrected label exit+entry for both signal rows.
assert (raw.query("market=='EU' and signal_date=='2020-04-30'").exit_date==pd.Timestamp('2020-06-02')).all()
assert (raw.query("market=='EU' and signal_date=='2020-05-29'").entry_date==pd.Timestamp('2020-06-02')).all()
res={'status':'PASS','independent_pairs':len(merged),'eligible_pairs':int(valid.sum()),
     'max_absolute_pair_label_error_bp':max_pair_error,
     'max_pre2025_forecast_change_when_2024_outcomes_are_corrupted':max_pre_diff,
     'post2024_forecasts_changed_under_corruption':post_model_changes,
     'max_rerun_prediction_difference':max_score_diff,
     'calendar_2020_06_02_repaired':True,'terminal_missing_labels':True,
     'matched_decisions':True,'no_future_label_leakage_test':True}
(OUT/'OLC33_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(res,indent=2),encoding='utf-8')
print(json.dumps(res,indent=2))
