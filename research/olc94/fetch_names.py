#!/usr/bin/env python3
"""Snapshot ETF/EU instrument descriptions from Yahoo. Research mapping only; not PIT."""
import csv, json, time, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import yfinance as yf

root = Path(__file__).parent
tickers=[r['ticker'] for r in csv.DictReader((root/'eu_universe_tickers.csv').open())]
out=root/'metadata_output'; out.mkdir(exist_ok=True)
def one(ticker):
    rec={'ticker':ticker, 'status':'ERROR'}
    for i in range(2):
        try:
            t=yf.Ticker(ticker)
            info=t.get_info() or {}
            for k in ('shortName','longName','quoteType','category','fundFamily',
                      'currency','exchange','legalType','fundSummary','description','underlyingSymbol'):
                v=info.get(k)
                rec[k]=v if isinstance(v,(str,float,int,bool)) else ''
            rec['status']='OK' if any(rec.get(k) for k in ('shortName','longName')) else 'MISSING_NAME'
            break
        except Exception as ex:
            rec['error']=str(ex)[:400]
            time.sleep(1+i)
    return rec
rows=[]
with ThreadPoolExecutor(max_workers=3) as pool:
    fs={pool.submit(one,t):t for t in tickers}
    for i,f in enumerate(as_completed(fs),1):
        rows.append(f.result())
        if i%20==0:print(f'METADATA {i}/{len(tickers)}',flush=True)
rows.sort(key=lambda x:x['ticker'])
keys=['ticker','status','shortName','longName','quoteType','category','fundFamily','currency','exchange','legalType','underlyingSymbol','fundSummary','description','error']
with (out/'eu_ticker_metadata.csv').open('w',encoding='utf8',newline='') as h:
    writer=csv.DictWriter(h,fieldnames=keys);writer.writeheader();writer.writerows(rows)
qa={'downloaded_utc':datetime.now(timezone.utc).isoformat(),'n_tickers':len(rows),
    'n_ok':sum(x['status']=='OK' for x in rows),'n_failed':sum(x['status']=='ERROR' for x in rows),
    'warning':'Yahoo metadata retrieved in 2026. Identity needs historical verification. Labels are NOT PIT.'}
(out/'metadata_qa.json').write_text(json.dumps(qa,indent=2,ensure_ascii=False))
print(json.dumps(qa,indent=2),flush=True)
sys.exit(0 if qa['n_ok'] else 2)
