"""Annual raw neural fits and reconstructable, raw-only training provenance."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from raw_patterns_v1.run import build_panel,sha,write
from raw_patterns_v1.model import learner as v1
from raw_patterns_v1.patterns import split_dates
from etf_trader.source_only.raw_io import load_ticker_csv_folder

VARIANT='RAW_FLATTEN_CONTEXT'

def panel(raw,expected):
    actual={p.name:sha(p) for p in sorted(Path(raw).glob('*.csv'))}
    if actual!=expected:raise ValueError('Original raw byte identity failed')
    mats,cats,_=load_ticker_csv_folder(raw,allow_missing=True)
    if len(cats)!=149:raise ValueError('Wrong Original149 universe')
    f,_,x,coverage=build_panel(mats,last_signal='2026-06-30',data_end='2026-09-01')
    return f,x,coverage

def expected_keys(ti,year):
    from paper_ltr_v1.learner import FEATURES
    valid=ti[FEATURES].notna().sum(axis=1)>=30
    return ti[(ti.signal_date.dt.year==year)&(ti.signal_date<='2026-06-30')&valid][v1.KEYS].sort_values(v1.KEYS).reset_index(drop=True)

def forward_saved(x,p):
    h=np.maximum(x@p['W1']+p['b1'],0)
    h=np.maximum(h@p['W2']+p['b2'],0)
    return (h@p['W3']+p['b3']).ravel()

def cohort_meta(sub,val,test,x,state):
    return dict(subtrain_keys_sha256=v1.keys_hash(sub),validation_keys_sha256=v1.keys_hash(val),test_keys_sha256=v1.keys_hash(test),
        subtrain_raw_tensor_sha256=v1.array_hash(x[sub.index]),validation_raw_tensor_sha256=v1.array_hash(x[val.index]),
        fit_matrix_sha256=v1.array_hash(v1.transform(x[sub.index],state)),
        validation_matrix_sha256=v1.array_hash(v1.transform(x[val.index],state)),
        test_matrix_sha256=v1.array_hash(v1.transform(x[test.index],state)),
        labels_sha256=v1.array_hash(v1.decile_labels(sub)),validation_labels_sha256=v1.array_hash(v1.decile_labels(val)),
        state_hashes={k:v1.array_hash(v) for k,v in state.items()},subtrain_queries=sub.signal_date.nunique(),validation_queries=val.signal_date.nunique(),
        max_subtrain_exit=str(sub.exit_date_21.max()),validation_start=str(val.signal_date.min()),max_validation_exit=str(val.exit_date_21.max()))

def verify_full_fingerprints(result,ti,repeat,raw):
    """Rebuild tensors and saved-model predictions; never fit or trust125feature fingerprints."""
    root=Path(result['out_dir'])
    for relative,digest in result['source_sha256'].items():
        if sha(Path(__file__).resolve().parents[1]/relative)!=digest:raise ValueError('Neural source changed')
    f,x,_=panel(raw,result['raw_files_sha256'][str(repeat)])
    ref=pd.read_parquet(root/'NATIVE_PREDICTIONS.parquet')
    if sha(root/'NATIVE_PREDICTIONS.parquet')!=result['files_sha256']['NATIVE_PREDICTIONS.parquet']:raise ValueError('Neural prediction artifact changed')
    records={}
    for year in range(2017,2027):
        sub,val,test=split_dates(f,year);state=v1.fit_transform_state(x[sub.index])
        if not (sub.exit_date_21<val.signal_date.min()).all() or not (val.exit_date_21<pd.Timestamp(year,1,1)).all():raise ValueError('Raw maturity/purge failed')
        meta=result['per_year'][str(year)]['transforms'][str(repeat)]
        actual=cohort_meta(sub,val,test,x,state)
        if any(meta.get(k)!=v for k,v in actual.items()):raise ValueError('Raw training fingerprint failed')
        pd.testing.assert_frame_equal(test[v1.KEYS].reset_index(drop=True),expected_keys(ti,year),check_exact=True)
        scores=[];tx=v1.transform(x[test.index],state)
        for path in meta['saved_models']:
            path=Path(path)
            if sha(path)!=result['model_files_sha256'][path.relative_to(root).as_posix()]:raise ValueError('Saved neural model changed')
            with np.load(path,allow_pickle=False) as z:
                for k,v in state.items():np.testing.assert_array_equal(z[k],v)
                p={k:z[k].copy() for k in ('W1','b1','W2','b2','W3','b3')}
            scores.append(forward_saved(tx,p))
        expected=ref[(ref.vintage==repeat)&(ref.signal_date.dt.year==year)].sort_values(v1.KEYS).reset_index(drop=True)
        pd.testing.assert_frame_equal(expected[v1.KEYS],test[v1.KEYS].reset_index(drop=True),check_exact=True)
        np.testing.assert_allclose(np.mean(scores,axis=0),expected.pred,rtol=0,atol=1e-12)
        records[str(year)]=dict(raw_training_PASS=True,maturity_PASS=True,prediction_reconstruction_PASS=True)
    return dict(PASS=True,years=records,raw_only_training=True,ti_panel_role='replay_reference_only',new_fits_executed=0)
