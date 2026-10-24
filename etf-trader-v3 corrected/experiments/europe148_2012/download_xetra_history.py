#!/usr/bin/env python3
"""Download and audit full pre-2012 through Oct-2026 XETRA EUR OHLCV by ISIN.

Six independent cluster jobs. Source ISIN/ticker/EUR venue must have matched
official 2026 Xetra instrument reference. Uses 2010-01-01 vendor request, but
does not invent prices or fill quotes from before *specific* Xetra listing.
Evidence is retrospective with 2026-survivor selection, not historical PIT.
"""
import argparse,json,time,re,hashlib,traceback
from pathlib import Path
import numpy as np,pandas as pd,yfinance as yf
from universe_discovery import CLUSTERS,ADD_QUOTAS,PROPERTY
END="2026-10-25";BEGIN="2010-01-01"
def quote(row):
    t=row["yahoo_symbol"]
    if not isinstance(t,str) or not t.endswith(".DE"):
        raise ValueError("Not an official XETR Yahoo mnemonic")
    date=pd.Timestamp(row["first_xetra_trading_date"])
    launch=pd.Timestamp(row["inception_date"])
    first_allowed=max(date,launch)
    if first_allowed>pd.Timestamp("2024-12-31"):
        raise ValueError("Class first EUR venue trading too recent to estimate robust OOS")
    df=yf.download(t,start=BEGIN,end=END,threads=False,
                   auto_adjust=False,progress=False,actions=False,repair=False)
    if isinstance(df.columns,pd.MultiIndex):
        df.columns=df.columns.get_level_values(0)
    if "Adj Close" not in df or len(df)<450:
        raise ValueError(f"No reliable historical adjusted quotes, {len(df)}")
    df=df.loc[df.index>=first_allowed].copy()
    if len(df)<400:raise ValueError("After legal-share-class listing only "+str(len(df))+" bars")
    if df.index.max()<pd.Timestamp("2026-09-30"):
        raise ValueError("Quote stale before September 2026")
    q=df["Adj Close"]/df["Close"]
    price=pd.DataFrame({"date":df.index,
      "Open":df["Open"]*q,"High":df["High"]*q,"Low":df["Low"]*q,
      "Close":df["Adj Close"],"Volume":df["Volume"]})
    price=price.dropna()
    assert price.date.is_unique and price.date.is_monotonic_increasing
    px=price[["Open","High","Low","Close"]].to_numpy(float)
    if not (np.isfinite(px).all() and (px>0).all()):raise ValueError("Bad pricing")
    if not np.isfinite(price.Volume.fillna(0)).all():raise ValueError("Bad volume")
    gap=(price.date.diff().dt.days.fillna(1))
    if (gap>60).any():raise ValueError("Historic quote gap >60 calendar days")
    wrong=((price.Low>price[["Open","Close"]].min(axis=1)*1.001) |
           (price.High<price[["Open","Close"]].max(axis=1)*.999))
    outlier=int(wrong.sum())
    if outlier/max(1,len(price))>.01:raise ValueError("OHLC envelope invalid >1%")
    if outlier:
        # Do not rewrite Open/Close; repair only High/Low to contain them.
        price["Low"]=np.minimum(price.Low,price[["Open","Close"]].min(axis=1))
        price["High"]=np.maximum(price.High,price[["Open","Close"]].max(axis=1))
    volzero=float((price.Volume<=0).mean())
    if volzero>.15:raise ValueError("Thin or inactive Xetra history (zero volume)")
    pre2012=int((price.date<pd.Timestamp("2012-01-01")).sum())
    bars2012=int(price.date.dt.year.eq(2012).sum())
    bars2017=int(price.date.dt.year.eq(2017).sum())
    bars2018=int(price.date.dt.year.eq(2018).sum())
    if max(bars2012,bars2017,bars2018)<100:
        raise ValueError("No trustworthy training/cross-validation-year bars")
    report=dict(isin=row["isin"],ticker=t,first_vendor_bar=str(price.date.iloc[0].date()),
        first_xetra_bar=str(date.date()),catalog_fund_inception=str(launch.date()),
        earliest_legal_price=str(first_allowed.date()),
        last_vendor_bar=str(price.date.iloc[-1].date()),n_bars=len(price),
        pre2012_bars=pre2012,year2012_bars=bars2012,year2017_bars=bars2017,
        year2018_bars=bars2018,ohlc_envelope_repairs=outlier,
        nontrading_gap_max_days=int(gap.max()),zero_volume_fraction=volzero,
        valid_2012_start=(pre2012>=126 and bars2012>=180),
        can_train_from_2012=(bars2012>=180),
        can_evaluate_from_2018=(price.date.iloc[0]<=pd.Timestamp("2017-01-01") and bars2017>200),
        xetra_isin_matching_source="official_cashmarket_t7_2026",
        no_backfill_before_inception=True,
        quality_passed=True)
    price["date"]=price.date.dt.strftime("%Y-%m-%d")
    return price,report
def eligible(row):
    desc=str(row["name"])+" "+str(row["index"])
    if row["cluster"]=="EU_PROPERTY" and not PROPERTY.search(desc):
        return False,"FALSE_PROPERTY_INDEX"
    if row["cluster"]=="SOVEREIGN_EUR" and re.search(r"\bUK\b|united kingdom|gilt|swiss|us treasury",desc,re.I):
        return False,"NON_EURO_SOVEREIGN"
    if row["cluster"] in ("EU_EQUITY_BROAD","EU_EQUITY_SECTOR","EU_EQUITY_COUNTRY","EU_EQUITY_FACTOR","EU_PROPERTY"):
        if row["europe_weight_percent"]>0 and row["europe_weight_percent"]<75:
            return False,"EU_EXPOSURE_LT_75PCT"
    return True,"PASS"
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--cluster",choices=CLUSTERS,required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    prices=out/"raw_by_isin";prices.mkdir(exist_ok=True)
    df=pd.read_csv(Path(a.input)/"OFFICIAL_XETRA_ISIN_MATCHES.csv")
    cat=df[df.cluster.eq(a.cluster)&df.official_eur_xetra_verified].copy()
    assert cat["isin"].nunique()==len(cat)
    cat=cat.sort_values(["priority","fund_size_millions_eur","isin"],ascending=[False,False,True])
    goal=ADD_QUOTAS[a.cluster]
    results=[];rejected=[];selected=[]
    scan_limit=min(len(cat),max(18,goal*3+12))
    for k,row in enumerate(cat.head(scan_limit).to_dict("records")):
        ok,why=eligible(row)
        if not ok:
            rejected.append(dict(isin=row["isin"],ticker=row["yahoo_symbol"],
                                 cluster=a.cluster,reason=why));continue
        for attempt in range(2):
            try:
                price,audit=quote(row)
                fn=prices/(row["isin"]+".csv")
                price.to_csv(fn,index=False,float_format="%.12g")
                audit["price_sha256"]=hashlib.sha256(fn.read_bytes()).hexdigest()
                audit["cluster"]=a.cluster
                audit["fund_name"]=row["name"]
                audit["original_vendor_symbol"]=row["ticker"]
                audit["europe_exposure_percent_2026"]=row["europe_weight_percent"]
                audit["source_etfdb_commit"]="a75a11330ac1825946ae1c37c60ec2135d03cf77"
                results.append(audit);selected.append(row)
                print("EU148_PRICE_PASS",a.cluster,row["isin"],row["yahoo_symbol"],
                      audit["first_vendor_bar"],audit["n_bars"],len(results),flush=True)
                break
            except Exception as exc:
                if attempt==1:
                    rejected.append(dict(isin=row["isin"],ticker=row["yahoo_symbol"],
                            cluster=a.cluster,reason=repr(exc)[:260]))
                    print("EU148_PRICE_REJECT",a.cluster,row["isin"],repr(exc)[:140],flush=True)
                else:time.sleep(1.7)
        if len(results)>=goal:break
    pd.DataFrame(results).to_csv(out/"PRICE_QUALITY_PASS.csv",index=False)
    pd.DataFrame(rejected).to_csv(out/"PRICE_QUALITY_REJECT.csv",index=False)
    pd.DataFrame(selected).to_csv(out/"SELECTED_LEGAL_ISIN.csv",index=False)
    (out/"MANIFEST.json").write_text(json.dumps(dict(cluster=a.cluster,
       requested_additional=goal,actually_verified=len(results),
       quotes_start_requested=BEGIN,provider_end=END,
       n_candinates_scanned=min(scan_limit,len(cat)),
       n_candidate_isin_official=len(cat),
       n_pre2012_eligible=sum(x["valid_2012_start"] for x in results),
       n_pre2018_eligible=sum(x["can_evaluate_from_2018"] for x in results),
       prices_have_no_prefix_before_specific_legal_listing=True,
       source_ISIN_EUR_quote_verified_official=True,
       strategy_retrained=False,portfolio_backtest_performed=False,
       warnings=["Current-survivor universe, not point-in-time membership",
                 "No synthetic history before ETF share-class XETRA listing",
                 "2026 geography from current portfolio holdings",
                 "Historical vendor adjusted execution not certified broker fills"]),indent=2))
    print("EU148_CLUSTER_PRICE_RESULT",a.cluster,len(results),"goal",goal,
       "pre2012",sum(x["valid_2012_start"] for x in results),flush=True)
if __name__=="__main__":main()
