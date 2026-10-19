#!/usr/bin/env python3
"""Audited European ETF 48 source-only adapter for V2 UNRESTRICTED universe.

ISIN uniqueness and identity are guaranteed by the upstream freeze.
Never use a derived historical prediction from any earlier model.
Open, Close, Volume untouched; OHLC inconsistent High/Low are preserved in
original upstream files and corrected ONLY inside this explicitly quarantined
experimental derived-data directory. Not a clean brokerage executable OHLC feed.
"""
from __future__ import annotations
import argparse,json,hashlib,collections
from pathlib import Path
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/"isin_first2026/full_eu_2017/results"
FRESH=ROOT/"isin_first2026"
SOURCES={
"fresh60":FRESH/"fresh60_results/adj_price",
"sector30":ROOT/"europe_sector2026/results/adj_price",
"alts21":ROOT/"europe_sector2026/alternatives/results/adj_price",
"alias8":ROOT/"europe_sector2026/aliases/results/adj_price",
"bond16":FRESH/"full_eu_2017/bonds_results/vendor_adjusted",
"isin5_16":FRESH/"five_isin_yfinance/results/yahoo_adjusted",
"isin5_4":FRESH/"five_isin_yfinance/second_pass/results/adj_price"
}
CAT={
"EU_EQUITY_BROAD":"C01_EU_BROAD",
"EU_EQUITY_SECTOR":"C02_EU_SECTOR",
"EU_EQUITY_COUNTRY":"C03_EU_COUNTRY",
"EU_EQUITY_FACTOR":"C04_EU_FACTOR",
"SOVEREIGN_EUR":"C05_BONDS_CASH_CREDIT",
"EU_PROPERTY":"C06_EU_PROPERTY"
}
start=pd.Timestamp("2015-01-01")
end=pd.Timestamp("2026-07-01")
OHLC=["Open","High","Low","Close","Volume"]

def sha(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as fd:
        for b in iter(lambda:fd.read(1<<20),b""):h.update(b)
    return h.hexdigest()

def bars(path,ticker):
    z=pd.read_csv(path)
    assert "date" in z.columns and set(OHLC).issubset(z.columns),ticker
    z["date"]=pd.to_datetime(z.date,errors="raise")
    z=z.loc[(z.date>=start)&(z.date<=end),["date"]+OHLC].copy()
    if z.date.duplicated().any():raise AssertionError("Duplicate date "+ticker)
    for c in OHLC:z[c]=pd.to_numeric(z[c],errors="coerce")
    if (~np.isfinite(z[OHLC].to_numpy(dtype=float))).any():
        raise AssertionError("Missing or infinite within listed bars "+ticker)
    if (z[["Open","High","Low","Close"]]<=0).any(axis=None):
        raise AssertionError("Nonpositive price "+ticker)
    if (z.Volume<0).any():raise AssertionError("Negative volume "+ticker)
    bad=(z.High<z[["Open","Low","Close"]].max(axis=1)-1e-8)|(
           z.Low>z[["Open","High","Close"]].min(axis=1)+1e-8)
    raw_count=int(bad.sum())
    # Only HIGH and LOW "envelope repair" in copied *derived* data.
    # Neither Open nor Close nor labels are altered by this correction.
    z.loc[bad,"High"]=z.loc[bad,["High","Open","Close","Low"]].max(axis=1)
    z.loc[bad,"Low"]=z.loc[bad,["Low","Open","Close","High"]].min(axis=1)
    if (z.High<z[["Open","Low","Close"]].max(axis=1)-1e-8).any() or (
          z.Low>z[["Open","High","Close"]].min(axis=1)+1e-8).any():
        raise AssertionError("Residual bad envelope "+ticker)
    return z,raw_count

def run(out):
    out=Path(out);out.mkdir(exist_ok=False,parents=True)
    inp=out/"raw_ticker_csv";inp.mkdir()
    roster=pd.read_csv(DATA/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv")
    assert len(roster)==48 and roster["isin"].is_unique and roster.ticker.nunique()==48
    assert roster.benchmark_bucket.isin(CAT).all()
    categories=roster.benchmark_bucket.map(CAT)
    assert categories.nunique()==6 and categories.value_counts().min()>=4
    universe=pd.DataFrame(dict(ticker=roster.ticker,
        macro_category=categories,isin=roster["isin"]))
    universe.to_csv(inp/"universe.csv",index=False)
    details=[];corrected=0
    for item in roster.itertuples(index=False):
        source=SOURCES[item.source]
        file=source/(item.ticker+".csv")
        assert file.is_file(),str(file)
        z,n=bars(file,item.ticker)
        assert len(z)>=2200 and (z.date<=pd.Timestamp("2016-12-30")).sum()>=200
        p=inp/(item.ticker+".csv")
        z.to_csv(p,index=False,float_format="%.16g")
        corrected+=n
        details.append(dict(ticker=item.ticker,isin=item.isin,
              economic_bucket=item.benchmark_bucket,original_source=item.source,
              original_price_SHA256=sha(file),original_rows=len(pd.read_csv(file)),
              derived_2015_2026_rows=len(z),first_date=str(z.date.min().date()),
              last_date=str(z.date.max().date()),adjusted_envelope_rows=n,
              source_quote_grade=item.decision,derived_sha256=sha(p)))
    # No fills or invented sessions: model labels and risk simulator only see
    # sessions in which ALL 48 separate exchange venues actually published a
    # valid Open and Close. This is the same strict common-Open policy as the
    # previously completed F3/H1 evaluation, applied before model fitting.
    common=None
    for row in details:
        ds=set(pd.read_csv(inp/(row["ticker"]+".csv"),usecols=["date"]).date)
        common=ds if common is None else common.intersection(ds)
    assert common and len(common)>2400
    assert sum("2015" in x or "2016" in x for x in common)>=252
    assert sum("2021"<=x[:4]<="2026" for x in common)>1200
    for row in details:
        p=inp/(row["ticker"]+".csv")
        z=pd.read_csv(p)
        z=z[z.date.isin(common)].copy().sort_values("date")
        assert len(z)==len(common)
        z.to_csv(p,index=False,float_format="%.16g")
        row["common_venue_original_daily_rows"]=len(z)
        row["derived_sha256"]=sha(p)
    pd.DataFrame(details).to_csv(out/"SOURCE_AND_OHLC_REPAIR_AUDIT.csv",index=False)
    # Risk-only reference: exact European EUR high yield listed price
    # not part of 48 investable ETF universe. Never expose as basket member.
    risk_src=FRESH/"full_eu_2017/bonds_results/vendor_adjusted/IHYG.MI.csv"
    assert risk_src.is_file()
    risk,n=bars(risk_src,"IHYG.MI")
    risk.to_csv(out/"EURO_CORP_HY_RISK_ONLY.csv",index=False)
    result=dict(status="EU48_PORT_FULL_SOURCE_INPUTS_PREPARED",n_tickers=48,
         n_unique_isin=48,category_counts={str(k):int(v) for k,v in categories.value_counts().items()},
         raw_source_unmodified=True,derived_high_low_envelope_rows=corrected,
         shared_EU48_original_quote_sessions=len(common),
         shared_EU48_pre2017_sessions=sum(x<"2017-01-31" for x in common),
         non_observed_calendar_dates_NEVER_filled=True,
         derived_corp_HY_non_europe_issuer_risk_only=True,
         risk_ref_euro_HY="IHYG.MI",risk_ref_equity="IMEU.AS",
         risk_ref_euro_gov="EUNH.DE",defensive1="IBCA.DE",
         defensive2="IBCN.DE",first_model_data=str(start.date()),
         final_model_data=str(end.date()),vendor_path="vendor/etf_trader_v2",
         original_48_manifest_sha=sha(DATA/"RESULT.json"),
         roster_sha256=sha(DATA/"STRICT_EUROPE_2017_WARM_2016_UNIQUE_ISIN.csv"),
         contract_modification_to_US_cluster_and_risk=True)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
    print("ETF_TRADER_48_PREPARED "+json.dumps(result),flush=True)

if __name__=="__main__":
    q=argparse.ArgumentParser();q.add_argument("--out",required=True)
    run(q.parse_args().out)
