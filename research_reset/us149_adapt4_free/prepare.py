"""Validate original_US149 source archive and derive EXACT usable 149 ticker panel.

Allowed: source-derived OHLC High/Low repair only if vendor envelope violation,
copy original Open Close untouched, original missingness is retained.
Do not fill sparse rows, fail if complete 149 synchronous panel unavailable.
"""
from __future__ import annotations
import argparse,json,hashlib
from pathlib import Path
import pandas as pd,numpy as np
from etf_trader.source_only.raw_io import load_ticker_csv_folder

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for x in iter(lambda:f.read(1048576),b''):h.update(x)
    return h.hexdigest()

def prepare(us,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    root=Path(us)
    files=list(root.rglob('universe.csv'))
    assert len(files)==1,files
    raw=files[0].parent
    roster=pd.read_csv(files[0])
    assert len(roster)==149 and roster.ticker.nunique()==149,(len(roster),roster.columns.tolist())
    assert roster.macro_category.nunique()==6 and roster.groupby('macro_category').size().between(24,25).all()
    diagnostics=[];raw={};series={}
    names=sorted(roster.ticker.to_list())
    dtidx=None
    for t in names:
        file=files[0].parent/(t+'.csv')
        z=pd.read_csv(file,parse_dates=['date'],float_precision='round_trip')
        assert z.date.is_monotonic_increasing and z.date.is_unique
        assert set(['Open','High','Low','Close','Volume'])<=set(z)
        assert len(z)>=500,(t,len(z))
        # Original US149 archive stores each ETF on its OWN source vendor date
        # calendar, not a synthetic master common calendar. Intersect only
        # observations actually present; never manufacture missing sessions.
        present=pd.DatetimeIndex(z.loc[z[['Open','High','Low','Close','Volume']].notna().all(axis=1),'date'])
        dtidx=present if dtidx is None else dtidx.intersection(present)
        num=z[['Open','High','Low','Close','Volume']]
        finite=np.isfinite(num.to_numpy(float))
        missing=int((~finite).sum())
        bad=(z.Low>z[['Open','Close']].min(axis=1)+1e-9)|(z.High<z[['Open','Close']].max(axis=1)-1e-9)
        diagnostics.append(dict(ticker=t,rows=len(z),missing_cells=missing,
            envelope_corrections=int(bad.sum()),raw_sha256=sha(file),
            first=str(z.date.min().date()),last=str(z.date.max().date())))
        raw[t]=z
    m=pd.DataFrame(diagnostics)
    dtidx=dtidx.sort_values()
    print('US149_SOURCE_RAW_DIAGNOSTIC',json.dumps(dict(n=149,source_real_common_rows=len(dtidx),
       earliest=str(dtidx.min().date()),latest=str(dtidx.max().date()),
       missing_cells=int(m.missing_cells.sum()),bad_hilo=int(m.envelope_corrections.sum()),
       earliest_ticker=str(m.loc[m['rows'].idxmin(),'ticker']),
       min_ticker_rows=int(m.rows.min()),
       pre2017_common=int((dtidx<pd.Timestamp('2017-01-01')).sum()),
       after2021_common=int((dtidx>=pd.Timestamp('2021-01-01')).sum()),
       categories=roster.macro_category.value_counts().to_dict())),flush=True)
    # Repair only the immutable vendor envelope for executable safety:
    # Source raw remains unchanged. Existing all-finite archive can remain.
    pre=out/'raw_ticker_csv';pre.mkdir()
    for t in names:
        # Keep ONLY actual source days common across ALL 149 ETF tickers.
        # Different calendar coverage is not silently forward-filled.
        z=raw[t].set_index('date').loc[dtidx].reset_index()
        assert len(z)==len(dtidx)
        z['Low']=z[['Low','Open','Close']].min(axis=1)
        z['High']=z[['High','Open','Close']].max(axis=1)
        z.to_csv(pre/(t+'.csv'),index=False,float_format='%.16g')
    roster.to_csv(pre/'universe.csv',index=False)
    mats,cats,manifest=load_ticker_csv_folder(pre)
    assert mats['Close'].shape[1]==149
    assert len(mats['Close'].index)>1000
    assert (mats['Close'].index<pd.Timestamp('2017-01-01')).sum()>=252
    assert pd.Timestamp('2026-07-01') in mats['Close'].index
    (out/'ORIGINAL_SOURCE_AUDIT.json').write_text(json.dumps(dict(
      archive_path=str(files[0].parent),n=149,common_date_count=len(dtidx),
      common_calendar_intersection_not_forward_filled=True,
      source_from='archived run36551650325 artifact etf-trader-raw-149',
      original_149_universe_sha=sha(files[0]),all_source_raw_checksums=m.to_dict('records'),
      raw_data_manually_changed=False,only_high_low_envelopes_derived=True,
      passed_full_source_load_and_2017_warmup=True),indent=2)+'\n')
    m.to_csv(out/'SOURCE_ETF149_QUOTE_QUALITY.csv',index=False)
    return out

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--us',required=True)
    a.add_argument('--out',required=True);x=a.parse_args()
    prepare(x.us,x.out)
