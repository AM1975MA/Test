#!/usr/bin/env python3
"""OLC58 venue-quote coverage / indicative-price audit. NO fill certification.

Supply a historical vendor quote CSV whose quote times, instrument/venue
mapping and provenance you have independently verified. Without those inputs,
this tool reports MISSING and never fabricates prices or performance.

Required columns: market,day,ticker,venue,isin,session,quote_timestamp_utc,
source_file,bid,ask,bid_size,ask_size,auction_price,auction_volume.

session: OPEN_AUCTION or CONTINUOUS_FIRST_MINUTE. A single opening auction
trade is not a guaranteed executable fill; continuous top-of-book is likewise
only a snapshot. Positions are normalized to NAV=1; portfolio size is unknown.

Usage: python match_venue_quotes.py ORDER_MANIFEST.csv VENUE_QUOTES.csv OUT.csv
"""
import argparse
import sys
from pathlib import Path
import pandas as pd
import numpy as np

COLUMNS=['market','day','ticker','venue','isin','session','quote_timestamp_utc','source_file',
         'bid','ask','bid_size','ask_size','auction_price','auction_volume']

def main(order_path,quote_path,out_path):
    orders=pd.read_csv(order_path,dtype={'market':str,'day':str,'ticker':str})
    quotes=pd.read_csv(quote_path,dtype={'market':str,'day':str,'ticker':str,'isin':str,'venue':str})
    missing=[x for x in COLUMNS if x not in quotes]
    if missing:raise ValueError('Missing vendor fields: '+str(missing))
    if len(quotes)==0:
        orders['source_verified']=False
        orders['gate']='NO_VENUE_QUOTES'
        orders.to_csv(out_path,index=False)
        print('NO_VENUE_QUOTES: 0 matched / '+str(len(orders))+' orders; no fills verified.')
        return
    # One quote row per (market, day, ticker) for this deterministic audit.
    # Multiple venues must be mapped with verified ISIN and chosen broker venue
    # upstream; do not guess a venue from .DE or .MI ticker suffix.
    keys=['market','day','ticker']
    if quotes.duplicated(keys).any():
        raise ValueError('Ambiguous duplicate ticker/date quotes; map exact venue and ISIN first.')
    if quotes['source_file'].isna().any() or quotes['source_file'].eq('').any():
        raise ValueError('Missing original source_file provenance')
    if quotes['isin'].isna().any() or not quotes['isin'].str.fullmatch('[A-Z0-9]{12}').all():
        raise ValueError('Missing or malformed 12-char ISIN')
    if not quotes.session.isin(['OPEN_AUCTION','CONTINUOUS_FIRST_MINUTE']).all():
        raise ValueError('Unknown market session')
    if pd.to_datetime(quotes.quote_timestamp_utc,utc=True,errors='coerce').isna().any():
        raise ValueError('Missing or invalid timestamp UTC')
    for col in ['bid','ask','bid_size','ask_size','auction_price','auction_volume']:
        quotes[col]=pd.to_numeric(quotes[col],errors='coerce')
    x=quotes[quotes.session=='CONTINUOUS_FIRST_MINUTE']
    if not ((x.bid>0)&(x.ask>=x.bid)&(x.bid_size>=0)&(x.ask_size>=0)).all():
        raise ValueError('Invalid quoted bid/ask or size')
    x=quotes[quotes.session=='OPEN_AUCTION']
    if not ((x.auction_price>0)&(x.auction_volume>0)).all():
        raise ValueError('Invalid opening-auction price/volume')
    merged=orders.merge(quotes,on=keys,how='left',validate='many_to_one',suffixes=('','_vendor'))
    available=merged.source_file.notna()
    merged['source_verified']=available
    merged['gate']=np.where(available,'QUOTE_ONLY_NOT_FILL','MISSING_OR_UNMAPPED')
    proxy=np.where(merged.session.eq('OPEN_AUCTION'),merged.auction_price,
                   np.where(merged.side.eq('BUY'),merged.ask,merged.bid))
    merged['quote_proxy_price']=np.where(available,proxy,np.nan)
    # For BUY, worse if paid > model open; for SELL, worse if sold < model open.
    signed=np.where(merged.side.eq('BUY'),1,-1)
    merged['quote_proxy_adverse_bp']=signed*(merged.quote_proxy_price/merged.theoretical_open-1)*1e4
    # Not brokerage fills. No calibrated bar-by-bar reinvestment/P&L is possible
    # from a single quote snapshot, even if 100% of the rows are matched.
    merged.to_csv(out_path,index=False,float_format='%.12g')
    print('VENDOR_QUOTES: matched=',int(available.sum()),' of ',len(merged),
          '; audit status is QUOTE_ONLY_NOT_FILL. This is NOT live execution validation.')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('order_manifest');p.add_argument('vendor_quotes');p.add_argument('output_csv');a=p.parse_args()
    main(a.order_manifest,a.vendor_quotes,a.output_csv)