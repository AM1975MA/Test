"""Complete 2017-2026 history experiment with explicit 58-month fit gate."""
import argparse,importlib.util,json,os,sys
from pathlib import Path
import pandas as pd
from history_window_v1.audit import derive,digest
from history_window_v1.replay_patch import apply

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.raw).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    originals={p.name:digest(p) for p in raw.iterdir() if p.is_file()}
    rows=derive(raw,out/'derived_raw')
    pd.DataFrame(rows).to_csv(out/'RAW_WINDOW_MANIFEST.csv',index=False)
    patch=apply(ROOT/'vendor/etf_trader_v2',out)
    os.environ['FROZEN_149_ROOT']=str(out);os.environ['FROZEN_HOLDOUT70_ROOT']=str(out)
    spec=importlib.util.spec_from_file_location('history_canonical_compare',ROOT/'holdout70/v2_canonical_same_source_compare.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    mod.FROZEN149=out/'derived_raw';mod.FROZEN70=mod.FROZEN149;mod.OUT=out/'replay'
    original_ensemble=mod.fit_ensemble_producer
    def baseline_ensemble(*args,**kwargs):
        kwargs['n_jobs']=1
        return original_ensemble(*args,**kwargs)
    mod.fit_ensemble_producer=baseline_ensemble
    original_run=mod.run
    def baseline_run(cmd):
        cmd=list(cmd)
        if '--xgb-workers' in cmd:
            cmd[cmd.index('--xgb-workers')+1]='1'
        return original_run(cmd)
    mod.run=baseline_run
    state=mod.build_source_only_state('original149',mod.FROZEN149)
    panel=pd.read_pickle(state['ma3_panel_path'])
    assert panel.signal_date.ge('2012-01-01').all()
    audits=pd.read_csv(state['base']/'ENSEMBLE_FIT_AUDIT.csv')
    assert audits.maturity_ok.all()
    assert set(audits.year)==set(range(2017,2027))
    annual=state['base']/'titanium/annual_models'
    eligibility=json.loads((annual/'eligibility_audit.json').read_text())
    assert [e['year'] for e in eligibility if e['status']=='FIT']==list(range(2017,2027))
    assert eligibility[0]['train_signal_dates']==58
    fit_rows=[]
    for year in range(2017,2027):
        aa=json.loads((annual/f'fit_audit_{year}.json').read_text())
        for entry in aa:
            assert pd.Timestamp(entry['max_exit'])<pd.Timestamp(entry['fit_date'])
        fit_rows.extend(aa)
    pd.DataFrame(fit_rows).to_csv(out/'TITANIUM_FIT_AUDIT.csv',index=False)
    result=mod.replay_full_universe(state)
    baseline=json.loads((ROOT/'history_window_v1/results/SUMMARY.json').read_text())['baseline'][0]
    for key in ('start','end','sessions'):assert result[key]==baseline[key],(key,result[key],baseline[key])
    assert result['candidate_count']==149
    assert originals=={p.name:digest(p) for p in raw.iterdir() if p.is_file()}
    result['history_experiment']={'raw_start':'2011-01-01','train_signal_start':'2012-01-01','minimum_mature_compact21_months':58,'all_annual_folds':list(range(2017,2027)),'original_inputs_unchanged':True,'baseline_training_not_repeated':True,'opportunity':'Inactive in canonical reference; existing separate forward-target defect not modified or activated.'}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
