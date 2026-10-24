#!/usr/bin/env python3
"""Refetch existing 48 Europe verified legal ISIN prices back to 2010.

Keep the previous certified EU48 source snapshot immutable. Only accept
official same ISIN active ETF/EUR XETR tickers with genuinely existing dates.
No substituting post-2018 newly issued share classes for predecessor history.
"""
import argparse,json,io,re
from pathlib import Path
import pandas as pd
from download_xetra_history import quote
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--reference",required=True)
    p.add_argument("--xetra",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    target=out/"original48_raw_by_isin";target.mkdir(exist_ok=True)
    r=pd.read_csv(a.reference)
    assert len(r)==r["isin"].nunique()==48
    df=pd.read_csv(a.xetra,sep=";",skiprows=2,encoding="latin-1",dtype=str,low_memory=False)
    active=df[df["ISIN"].isin(r["isin"])&
              df["Instrument Type"].eq("ETF")&
              df["Instrument Status"].eq("Active")&
              df["MIC Code"].eq("XETR")&
              df["Currency"].eq("EUR")].copy()
    active=active.sort_values(["ISIN","Mnemonic"]).drop_duplicates("ISIN")
    look=active.set_index("ISIN")
    results=[];rejected=[]
    for row in r.itertuples(index=False):
        isin=row.isin
        if isin not in look.index:
            rejected.append(dict(isin=isin,reason="No live official XETRA EUR venue for original ISIN"));continue
        arow=look.loc[isin]
        expiry=str(getattr(row,"current_class_first_seen","")).strip()
        venue=pd.Timestamp(arow["First Trading Date"])
        # Do not trust a fund strategy's predecessor 2008 series for
        # 2018 issue classes: exchange actually listed ISIN from venue date.
        first=venue
        if expiry and expiry!="nan" and expiry>str(venue.date()):
            first=pd.Timestamp(expiry)
        fields=dict(isin=isin,yahoo_symbol=str(arow["Mnemonic"])+".DE",
            first_xetra_trading_date=str(first.date()),
            inception_date=str(first.date()),
            name=str(arow["Instrument"]),
            index=str(row.index_subsector),cluster=row.benchmark_bucket,
            europe_weight_percent=100)
        try:
            history,info=quote(fields)
            history.to_csv(target/(isin+".csv"),index=False,float_format="%.12g")
            info["cluster"]=row.benchmark_bucket
            info["source_original48"]="original48 strict Europe ISIN, official XETRA"
            results.append(info)
            print("EU48_HISTORICAL_PASS",isin,len(history),info["first_vendor_bar"],flush=True)
        except Exception as exc:
            rejected.append(dict(isin=isin,reason=repr(exc)))
            print("EU48_HISTORICAL_REJECT",isin,repr(exc),flush=True)
    pd.DataFrame(results).to_csv(out/"ORIGINAL48_PRICE_PASS.csv",index=False)
    pd.DataFrame(rejected).to_csv(out/"ORIGINAL48_PRICE_REJECT.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(
        original_48=48,old_reference_unchanged=True,
        n_official_venue=len(active),n_data_pass=len(results),
        n_rejected=len(rejected),
        original_legally_distinct_isins=48,
        original_missing_2012_prices_not_synthetically_filled=True,
        training_dates_after_each_class_listing_only=True),indent=2))
    print("EU48_HISTORICAL_AUDIT",len(results),"of 48",flush=True)
if __name__=="__main__":main()
