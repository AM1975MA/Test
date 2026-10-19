#!/usr/bin/env python3
"""4 venue mnemonic alternatives, only direct Yahoo feeds and public justETF
pre-discovered listings. No justETF requests.
"""
from __future__ import annotations
import json,collections
from pathlib import Path
import pandas as pd
import numpy as np
from europe_sector2026.download import one,diagnose_and_normalize,sha

HERE=Path(__file__).resolve().parent
OLD=HERE.parent/"results/TICKER_BY_ISIN_CURRENCY_HISTORY_QUALITY.csv"
START=pd.Timestamp("2017-02-01")
END=pd.Timestamp("2026-07-01")

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    (out/"raw_vendor").mkdir();(out/"adj_price").mkdir()
    catalog=pd.read_csv(HERE/"CATALOG.csv")
    assert len(catalog)==4 and catalog["isin"].nunique()==3
    original=pd.read_csv(OLD)
    assert len(original)==16
    stat=[]
    for i,row in enumerate(catalog.itertuples(index=False),1):
        item=dict(isin=row.isin,ticker=row.yahoo_ticker,
                  category=row.underlying_geo,evidence=row.discovery_evidence)
        try:
            raw,metadata,errors=one(row.yahoo_ticker)
            df,adjusted,metrics=diagnose_and_normalize(raw)
            p=out/"raw_vendor"/(row.yahoo_ticker+".csv")
            q=out/"adj_price"/(row.yahoo_ticker+".csv")
            df.to_csv(p,float_format="%.16g")
            adjusted.to_csv(q,float_format="%.16g")
            currency=str(metadata.get("currency") or "").upper()
            typ=str(metadata.get("instrumentType") or "").upper()
            name=str(metadata.get("shortName") or metadata.get("longName") or "")
            oldrows=original[original["isin"]==row.isin]
            prevbest=oldrows[oldrows.download_status==
                "YAHOO_CURRENCY_EUR_AND_XETRA_IDENTITY_OK"]
            n=max(1,int(metrics["study_observed_bars"]))
            zerofrac=metrics["study_zero_volume"]/n
            flatfrac=metrics["study_flat_OHLC"]/n
            sameisin_overlap=[]
            for old in prevbest.itertuples(index=False):
                q_old=HERE.parent/"results/yahoo_adjusted"/(old.ticker+".csv")
                if not q_old.exists():continue
                pold=pd.read_csv(q_old,parse_dates=["date"]).set_index("date")
                pnew=adjusted.copy()
                common=pd.DataFrame(dict(a=pnew.Close,b=pold.Close)
                    ).loc[START:END].dropna()
                if len(common)<30:continue
                d=np.log(common).diff().dropna()
                sameisin_overlap.append(dict(other_ticker=old.ticker,
                    common_days=len(common),
                    daily_log_return_corr=float(d.a.corr(d.b)),
                    median_gap_bps=float((d.a-d.b).abs().median()*10000),
                    gap_gt1pct_days=int(((d.a-d.b).abs()>.01).sum())))
            # Do not silently accept a non-ETF security using the same
            # 3 or 4 letter exchange mnemonic, e.g. INS may be a company.
            yahooETF=typ=="ETF"
            item.update(
                result="EUR_YAHOO_ETF_CANDIDATE" if currency=="EUR" and yahooETF
                    else "REJECT_NON_ETF_OR_NON_EUR_YAHOO",
                currency=currency,instrument_type=typ,yahoo_fund_name=name,
                vendor_warnings=";".join(errors),
                history_first=metrics["source_first"],
                history_last=metrics["source_last"],
                history_n=metrics["source_rows"],
                study_n=metrics["study_observed_bars"],
                study_prior_2017_252=metrics["study_pre2017_252_bars"],
                full_2017_to_july2026=metrics["study_reaches_july2026"],
                study_zero_vendor_volume_fraction=zerofrac,
                study_flat_ohlc_fraction=flatfrac,
                studied_ohlc_anomalies=metrics["study_bad_ohlc_envelope"],
                prior_same_isin_yahoo_vendor_return_agreement=sameisin_overlap,
                raw_sha256=sha(p),adjusted_sha256=sha(q))
            print("ISIN_ALIAS2_YFINANCE",i,row.isin,row.yahoo_ticker,
                item["result"],metrics["source_first"],metrics["source_last"],
                "zero",round(zerofrac,4),flush=True)
        except Exception as e:
            item.update(result="DOWNLOAD_FAILED",error=type(e).__name__+": "+str(e)[:300])
            print("ISIN_ALIAS2_FAIL",row.isin,row.yahoo_ticker,item["error"],flush=True)
        stat.append(item)
    pd.DataFrame(stat).to_csv(out/"ALIAS2_REAL_QUOTES_AND_ORIGINAL_ISIN_VALIDATION.csv",index=False)
    result=dict(status="SECOND_PASS_ISIN_EXCHANGE_MNEMONIC_YAHOO_COMPLETE",
        attempts=len(stat),yahoo_results=dict(collections.Counter(s["result"] for s in stat)),
        catalog_sha256=sha(HERE/"CATALOG.csv"),
        original_proof_snapshot_sha256=sha(OLD),
        no_automated_justETF_scraping=True,not_proven_trading_price=True,
        future_asset_ranking_not_run=True)
    (out/"RESULT.json").write_text(json.dumps(result,indent=2)+"\n")
    (out/"SHA256_MANIFEST.txt").write_text("".join(
         sha(p)+"  "+str(p.relative_to(out))+"\n"
         for p in sorted(out.rglob("*.csv")))+sha(out/"RESULT.json")+"  RESULT.json\n")
    print("ISIN_ALIAS2_RESULT",json.dumps(result),flush=True)

if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument("--out",required=True)
    run(parser.parse_args().out)
