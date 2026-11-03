#!/usr/bin/env python3
"""Independent OLC34 audit: pinned inputs, baseline parity, valid sessions, causal perturbations."""
from pathlib import Path
import importlib.util, json
import pandas as pd,numpy as np,exchange_calendars as xc

BASE=Path(__file__).resolve().parents[1]
OLC32=BASE/'input/OLC32_CORRECTED_LABELS_AND_INPUTS.csv.gz'
OLC33_SCRIPT=BASE/'src/olc33_tail_condition.py'
VIX_CLEAN=BASE/'results/OLC34_VIX_ASOF_SIGNAL_EXCHANGE_FILTERED.csv'
VIX_DIRTY=BASE/'results/OLC34_VIX_ASOF_SIGNAL.csv'
OUT=BASE/'filtered'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m
olc33=load(OLC33_SCRIPT,'ref_olc33');olc34=load(BASE/'src/olc34_vix_context_exchange_filtered.py','olc34')

sp=pd.read_csv(OUT/'OLC34_PREQUENTIAL_PAIRS.csv.gz',parse_dates=['signal_date','exit_date','inc_exit_date','vix_asof_date'])
old=pd.read_csv(BASE/'olc33_reference/OLC33_OOF_PAIRS.csv.gz',parse_dates=['signal_date'])
olddec=pd.read_csv(BASE/'olc33_reference/OLC33_DECISIONS.csv',parse_dates=['signal_date'])
clean=pd.read_csv(VIX_CLEAN,parse_dates=['signal_date','vix_asof_date'])
dirty=pd.read_csv(VIX_DIRTY,parse_dates=['signal_date','vix_asof_date'])
res=json.loads((OUT/'OLC34_RESULTS.json').read_text())
checks={}
checks['olc32_sha']=olc34.sha256(OLC32)
checks['vix_clean_blob_sha']=olc34.git_blob_sha(VIX_CLEAN)
assert checks['olc32_sha']==olc34.SOURCE_SHA
assert checks['vix_clean_blob_sha']==olc34.VIX_BLOB_SHA
assert len(clean)==len(dirty)==91
assert len(sp)==len(old)==720
assert not sp.duplicated(['market','signal_date','challenger']).any()

oldmatch=sp.merge(old[['market','signal_date','challenger','p1','p0','eval_valid','net_spread_bp']],on=['market','signal_date','challenger'],suffixes=('','_olc33'),validate='one_to_one')
assert len(oldmatch)==len(sp)
checks['max_abs_p1_olc33_difference']=float(np.nanmax(abs(oldmatch.p1-oldmatch.p1_olc33)))
checks['max_abs_p0_olc33_difference']=float(np.nanmax(abs(oldmatch.p0-oldmatch.p0_olc33)))
checks['max_abs_spread_difference']=float(np.nanmax(abs(oldmatch.net_spread_bp-oldmatch.net_spread_bp_olc33)))
assert checks['max_abs_p1_olc33_difference']<=1e-14
assert checks['max_abs_p0_olc33_difference']<=1e-14
assert checks['max_abs_spread_difference']<=1e-14
assert (oldmatch.eval_valid==oldmatch.eval_valid_olc33).all()

# Rebuild p1 decisions directly with frozen code, not a new tuner.
old_from_sp=olc33.make_decisions(sp)
dc=old_from_sp.merge(olddec,on=['market','signal_date'],suffixes=('','_saved'),validate='one_to_one')
checks['olc33_decision_action_mismatches']=int((dc.switch!=dc.switch_saved).sum())
checks['olc33_decision_gain_max_diff']=float(np.nanmax(abs(dc.net_gain_bp-dc.net_gain_bp_saved)))
assert checks['olc33_decision_action_mismatches']==0
assert checks['olc33_decision_gain_max_diff']<1e-12

assert ((clean.vix_asof_date<clean.signal_date)&clean.lag_days.between(1,7)).all()
calendar=xc.get_calendar('XNYS',start='2019-01-02',end='2026-06-30')
sessions=calendar.sessions_in_range('2019-01-02','2026-06-30')
assert clean.vix_asof_date.isin(sessions).all()
dirtybad=dirty[~dirty.vix_asof_date.isin(sessions)]
checks['original_non_session_asof_signal_dates']=sorted(dirtybad.signal_date.dt.strftime('%Y-%m-%d').tolist())
checks['original_non_session_asof_count']=len(dirtybad)
checks['filtered_non_session_asof_count']=int((~clean.vix_asof_date.isin(sessions)).sum())
chk=dirty.merge(clean,on='signal_date',suffixes=('_raw','_clean'),validate='one_to_one')
changed=(chk.vix_asof_date_raw!=chk.vix_asof_date_clean)|(abs(chk.vix_21ago_close_raw-chk.vix_21ago_close_clean)>1e-9)
checks['monthly_dates_repaired']=int(changed.sum())
assert checks['original_non_session_asof_count']==3
assert checks['monthly_dates_repaired']==30
assert checks['filtered_non_session_asof_count']==0

for rec in res['train_audit']:
    if rec['last_mature_exit'] is not None:
        assert pd.Timestamp(rec['last_mature_exit'])<pd.Timestamp(f"{rec['year']}-01-01")
assert not {'label_valid','spread_bp','net_spread_bp','exit_date','y_plus','y_minus'}.intersection(olc33.FEATURE+['vix_close','log_vix_change_21'])

# Perturb outcomes in 2024. Models through end-2024 must remain untouched.
raw=olc34.load_augmented_pairs(OLC32,VIX_CLEAN,olc33)
raw.loc[(raw.year==2024)&raw.eval_valid,'y_plus']=1-raw.loc[(raw.year==2024)&raw.eval_valid,'y_plus']
perturbed,_,_,_=olc34.score_olc34(raw,olc33)
pre=sp.loc[sp.year<=2024,['market','signal_date','challenger','p1','p2']].merge(perturbed[['market','signal_date','challenger','p1','p2']],on=['market','signal_date','challenger'],suffixes=('_ref','_pert'),validate='one_to_one')
checks['max_abs_prediction_change_before_2025_when_2024_labels_altered']={k:float(np.nanmax(abs(pre[f'{k}_ref']-pre[f'{k}_pert']))) for k in ['p1','p2']}
assert all(x<1e-14 for x in checks['max_abs_prediction_change_before_2025_when_2024_labels_altered'].values())
post=sp.loc[sp.year==2025,['market','signal_date','challenger','p2']].merge(perturbed[['market','signal_date','challenger','p2']],on=['market','signal_date','challenger'],suffixes=('_ref','_pert'),validate='one_to_one')
checks['changed_2025_forecasts_after_2024_labels_altered']=int((abs(post.p2_ref-post.p2_pert)>1e-12).sum())
assert checks['changed_2025_forecasts_after_2024_labels_altered']>0
checks['main_switches_by_market']={r['market']:int(r['p2_actions']) for r in res['metrics_main_2021_2024']}
checks['primary_all_gates_pass']=bool(res['gates']['all_pass'])
checks['primary_decision']='STOP' if not checks['primary_all_gates_pass'] else 'CONDITIONAL_REPLAY_RESEARCH_ONLY'
(OUT/'OLC34_INDEPENDENT_VERIFICATION.json').write_text(json.dumps(checks,indent=2))
print(json.dumps(checks,indent=2))