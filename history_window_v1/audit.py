"""Exact frozen V2 feasibility gate. No training-policy or model changes.

If the unchanged 60-mature-month gate fails in 2017, a 2017-2026 full
performance comparison does not exist; do not relabel a 2018 start as 2017.
"""
import argparse, hashlib, json, os, shutil, subprocess, sys
from pathlib import Path
import numpy as np
import pandas as pd
from history_window_v1.contract import mature_rows

REPO=Path(__file__).resolve().parents[1]
SRC=REPO/'vendor/etf_trader_v2/src'
sys.path.insert(0,str(SRC))
from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.source_only.features import build as extra_build
from etf_trader.source_only.models import fit_predict
from etf_trader.ma3.hybrid_producer import corrected_target
from etf_trader.ma3.producer import FEATURES_42

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def derive(raw,out,end=None):
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(raw/'universe.csv',out/'universe.csv')
    universe=pd.read_csv(raw/'universe.csv')
    assert len(universe)==universe.ticker.nunique()==149
    rows=[]
    for ticker in universe.ticker:
        p=raw/f'{ticker}.csv'; lines=p.read_bytes().splitlines(keepends=True)
        assert lines[0].split(b',')[0]==b'date'
        kept=[line for line in lines[1:] if line[:10]>=b'2011-01-01' and (end is None or line[:10]<=end.encode())]
        assert kept
        q=out/p.name; q.write_bytes(lines[0]+b''.join(kept))
        # Preserve original textual prices and volumes exactly, no round-trip edits.
        rows.append({'ticker':ticker,'original_sha256':digest(p),'derived_sha256':digest(q),'original_rows':len(lines)-1,'derived_rows':len(kept),'first_date':kept[0][:10].decode(),'last_date':kept[-1][:10].decode()})
    return rows

def build(raw):
    mats,cats,manifest=load_ticker_csv_folder(raw)
    assert min(x.index.min() for x in mats.values())>=pd.Timestamp('2011-01-01')
    k.ALL_TICKERS=sorted(cats);k.TICKER_CATEGORY=cats
    k.CATEGORY_TICKERS={c:sorted(t for t in cats if cats[t]==c) for c in sorted(set(cats.values()))}
    dates,compact,tail,D=k.build_features(mats)
    if dates[-1]==mats['Close'].index[-1]: dates=dates[:-1]
    compact=compact[compact.signal_date.isin(dates)]
    tail=tail[tail.signal_date.isin(dates)]
    cl=k.add_labels(compact,mats['Open'],dates)
    tl=k.add_labels(tail,mats['Open'],dates)
    macro,mf=k.build_macro_panel(tail,tl)
    clusters=k.build_clusters(D,dates,mats['Close'].columns)
    opp,of=k.build_opp_panel(D,clusters,cl)
    extra=extra_build(mats,cats,dates)
    panels={name:p[p.signal_date.ge('2012-01-01')].copy() for name,p in {'compact':cl,'tail':tl,'macro':macro,'opportunity':opp,'extra':extra}.items()}
    return panels,mf,of

def same(a,b,keys,cols):
    common=sorted(set(a.signal_date)&set(b.signal_date))
    x=a[a.signal_date.isin(common)].sort_values(keys).reset_index(drop=True)[keys+cols]
    y=b[b.signal_date.isin(common)].sort_values(keys).reset_index(drop=True)[keys+cols]
    pd.testing.assert_frame_equal(x,y,check_exact=True)
    return {'rows':len(x),'columns':len(cols),'first_signal':str(min(common).date()),'last_signal':str(max(common).date()),'exact_equal':True}

def ma3(raw,out):
    env=os.environ.copy();env['PYTHONPATH']=str(SRC)+os.pathsep+env.get('PYTHONPATH','')
    subprocess.run([sys.executable,str(REPO/'vendor/etf_trader_v2/scripts/build_ma3_panel_source_only.py'),'--data',str(raw),'--cluster-data',str(raw),'--output',str(out)],env=env,check=True)
    p=pd.read_pickle(out/'RAW_FEATURE_PANEL.pkl')
    assert p.signal_date.ge('2012-01-01').all()
    return p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--raw',required=True);ap.add_argument('--out',required=True);a=ap.parse_args()
    raw=Path(a.raw).resolve();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=False)
    originals={p.name:digest(p) for p in raw.glob('*') if p.is_file()}
    rows=derive(raw,out/'derived_raw');pd.DataFrame(rows).to_csv(out/'RAW_WINDOW_MANIFEST.csv',index=False)
    derive(raw,out/'prefix_raw','2016-12-30')
    panels,mf,of=build(out/'derived_raw');prefix,pmf,pof=build(out/'prefix_raw')
    assert mf==pmf and of==pof
    # Original inactive Opportunity discovers predictors by suffix, accidentally
    # including target_excess_max and target_excess_max_rank. Record the source
    # defect; never certify these forward-label fields as causal predictors.
    opportunity_forward_predictors=[c for c in of if c.startswith('target_')]
    causal={}
    for name,features,keys in [('compact',k.F2D_FEATURES,['signal_date','ticker']),('tail',k.TAIL_FEATURES,['signal_date','ticker']),('extra',list(panels['extra'].columns[2:]),['signal_date','ticker']),('macro',mf,['signal_date','macro_category']),('opportunity',[c for c in of if not c.startswith('target_')],['signal_date','cluster_id'])]:
        causal[name]=same(panels[name],prefix[name],keys,features)
    mp=ma3(out/'derived_raw',out/'ma3');mpp=ma3(out/'prefix_raw',out/'ma3_prefix')
    causal['ma3']=same(mp,mpp,['signal_date','ticker'],list(FEATURES_42))
    membership=pd.read_csv(out/'ma3/DYNAMIC_CLUSTER_MEMBERSHIP.csv',parse_dates=['signal_date'])
    membership_prefix=pd.read_csv(out/'ma3_prefix/DYNAMIC_CLUSTER_MEMBERSHIP.csv',parse_dates=['signal_date'])
    causal['ma3_membership']=same(membership,membership_prefix,['signal_date','ticker'],['cluster_id'])
    eligibility=[]
    compact=panels['compact'];tail=panels['tail'];macro=panels['macro'];opp=panels['opportunity']
    compact=compact[compact[k.F2D_FEATURES].notna().sum(axis=1)>=30]
    tail=tail[tail[k.TAIL_FEATURES].notna().sum(axis=1)>=12]
    for year in range(2017,2027):
        for name,p,exit_col,target in [('compact21',compact,'exit_date_21','target_rank_pct'),('compact63',compact,'exit_date_63','target_rank_63'),('tail',tail,'exit_date_63','y_tailmix'),('macro',macro,'label_exit_date_63','target_rank'),('opportunity_inactive_in_canonical',opp,'label_exit_date_21','target_excess_max'),('ma3',mp.assign(target=corrected_target(mp)),'exit_date_63','target')]:
            tr=mature_rows(p,exit_col,year);tr=tr[tr[target].notna()]
            assert tr.signal_date.ge('2012-01-01').all() and tr[exit_col].lt(pd.Timestamp(year,1,1)).all()
            eligibility.append({'year':year,'component':name,'train_rows':len(tr),'train_signal_dates':tr.signal_date.nunique(),'min_signal':str(tr.signal_date.min()),'max_exit':str(tr[exit_col].max())})
    pd.DataFrame(eligibility).to_csv(out/'TRAINING_ELIGIBILITY.csv',index=False)
    # Exercise the ORIGINAL producer, not a surrogate eligibility rule.
    try:
        fit_predict(k,panels['compact'],panels['tail'],panels['macro'],mf,panels['extra'],out/'original_producer_2017',years=[2017])
    except RuntimeError as e:
        assert str(e)=='no annual model has at least 60 mature monthly training signals',str(e)
        producer_error=str(e)
    else:
        raise AssertionError('Expected original 2017 producer to reject insufficient mature history')
    gate=json.loads((out/'original_producer_2017/eligibility_audit.json').read_text())
    assert gate[0]['status']=='SKIP_INSUFFICIENT_MATURE_HISTORY' and gate[0]['train_signal_dates']<60
    assert originals=={p.name:digest(p) for p in raw.glob('*') if p.is_file()}
    result={'status':'INFEASIBLE_2017_WITH_UNCHANGED_V2','raw_start':'2011-01-01','training_start':'2012-01-01','candidate_count':149,'original_producer_gate':gate,'original_producer_error':producer_error,'causal_prefix_checks':causal,'opportunity_original_forward_label_predictors':opportunity_forward_predictors,'opportunity_full_feature_contract_causal':not opportunity_forward_predictors,'original_inputs_unchanged':True,'model_source_unchanged':True,'candidate_2017_2026_metrics':None,'decision':'KEEP_ORIGINAL_HISTORY','reason':'2017 has fewer than the unchanged required 60 mature monthly signals; no complete comparable performance or selection series exists. No 2018-only replay is represented as 2017-2026.','opportunity_contract':'kernel Opportunity panel checked separately; canonical source-only TIT_R/MA3/Stage19 does not call fit_predict_all/router Opportunity. Adding it would change the baseline. Original Opportunity suffix discovery includes forward target_excess_max and its rank: explicitly NOT causality certified and not silently fixed.'}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2),flush=True)

if __name__=='__main__':main()
