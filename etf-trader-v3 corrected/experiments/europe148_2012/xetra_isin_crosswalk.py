#!/usr/bin/env python3
"""Verify extra Europe UCITS ISINs against official Deutsche Boerse XETR CSV.

No market ticker is accepted solely from a third-party catalog. Match ISIN on
official *current listing* and EUR quote venue, then audit share class and
available historical prices in a separate stage. Inception is not first trading.
"""
import argparse,io,json,re,hashlib,requests
from pathlib import Path
import pandas as pd
from universe_discovery import CLUSTERS,ADD_QUOTAS
URL="https://www.cashmarket.deutsche-boerse.com/resource/blob/1528/a31c10e3183f4c5dd721f9c7f9eaaaea/data/t7-xetr-allTradableInstruments.csv"
def official_cols(df):
    cols=list(df.columns)
    def col(candidates):
        for c in cols:
            s=re.sub(r"[^a-z0-9]+","",str(c).lower())
            for q in candidates:
                if s==q:return c
        for c in cols:
            s=re.sub(r"[^a-z0-9]+","",str(c).lower())
            for q in candidates:
                if q in s:return c
        return None
    return {k:col(v) for k,v in {
        "isin":["isin","instrumentisin","productisin"],
        "symbol":["mnemonic","tradingmnemonic","instrumentmnemonic","ticker"],
        "currency":["tradingcurrency","currency","currencycode"],
        "instrument":["instrumenttype","securitytype","producttype"],
        "market":["mic","market","marketsegment"]
    }.items()}
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--discovery",required=True)
    p.add_argument("--out",required=True)
    a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    resp=requests.get(URL,timeout=120,headers={"User-Agent":"Mozilla/5.0 ETF Research Integrity Audit"})
    resp.raise_for_status()
    data=resp.content;assert len(data)>100000,(resp.status_code,len(data))
    (out/"XETRA_OFFICIAL_ALL_TRADABLE.csv").write_bytes(data)
    df=None; attempts=[]
    for enc in ["utf-8-sig","iso-8859-1"]:
        for sep in [";",",","\t","|"]:
            try:
                table=pd.read_csv(io.BytesIO(data),dtype=str,low_memory=False,
                            encoding=enc,sep=sep,on_bad_lines="warn")
                if len(table.columns)>6:
                    m=official_cols(table)
                    attempts.append((enc,sep,len(table.columns),len(table),m))
                    if m["isin"] is not None and m["symbol"] is not None:
                        df=table;break
            except Exception as e: attempts.append((enc,sep,str(e)[:200]))
        if df is not None:break
    (out/"XETRA_SCHEMA_AUDIT.json").write_text(json.dumps(dict(source=URL,bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),first_500_chars=data[:500].decode("utf-8",errors="replace"),
        attempts=attempts),indent=2,default=str))
    assert df is not None,"Official Xetra CSV schema did not include extractable ISIN/mnemonic"
    mapping=official_cols(df)
    print("XETRA_OFFICIAL_COLS",list(df.columns),flush=True)
    print("XETRA_MAP",mapping,"rows",len(df),flush=True)
    catalog=pd.read_csv(Path(a.discovery)/"EU_CANDIDATE_CATALOG_AUDITED.csv")
    assert catalog.isin.nunique()==len(catalog) if "isix" in catalog else catalog["isin"].nunique()==len(catalog)
    assert len(catalog)>200
    df[mapping["isin"]]=df[mapping["isin"]].astype(str).str.strip().str.upper()
    df[mapping["symbol"]]=df[mapping["symbol"]].astype(str).str.strip().str.upper()
    eu=df[df[mapping["isin"]].isin(catalog["isin"])].copy()
    if mapping["currency"] is not None:
        eur=eu[eu[mapping["currency"]].astype(str).str.upper().str.strip().eq("EUR")].copy()
    else:
        raise RuntimeError("Official Xetra CSV has no verifiable quote currency field")
    # When same ISIN lists several mnemonics, assign lexicographically earliest
    # EUR XETRA ticker: no duplicate share class counted as an additional ISIN.
    eur=eur.sort_values([mapping["isin"],mapping["symbol"]]).drop_duplicates(mapping["isin"])
    matched=eur[[mapping["isin"],mapping["symbol"]]].copy()
    matched.columns=["isin","official_xetra_mnemonic"]
    for k in ("currency","instrument","market"):
        matched["official_"+k]=eur[mapping[k]].astype(str).to_numpy() if mapping[k] else "UNKNOWN"
    merged=catalog.merge(matched,on="isin",how="left",validate="one_to_one")
    merged["official_eur_xetra_verified"]=merged.official_xetra_mnemonic.notna()
    merged["yahoo_symbol"]=merged.official_xetra_mnemonic.fillna("").apply(lambda x:x+".DE" if x else "")
    merged.to_csv(out/"OFFICIAL_XETRA_ISIN_MATCHES.csv",index=False)
    selected=[];stats=[]
    for cluster,quota in ADD_QUOTAS.items():
        candidates=merged[merged.cluster.eq(cluster)&merged.official_eur_xetra_verified]
        # Do not optimize historical returns. Longest fund history prioritized.
        pick=candidates.sort_values(["priority","fund_size_millions_eur","isin"],
                                    ascending=[False,False,True]).head(quota)
        selected.extend(pick.to_dict("records"))
        stats.append(dict(cluster=cluster,required_extra=quota,
             official_EUR_ISIN_count=len(candidates),
             official_pre2012_inception=int(candidates.since_2012.sum()),
             selected=len(pick),deficit=max(0,quota-len(pick))))
    chosen=pd.DataFrame(selected)
    chosen.to_csv(out/"XETRA_EUR100_PRE_PRICE_SELECTED.csv",index=False)
    pd.DataFrame(stats).to_csv(out/"XETRA_SIX_CLUSTER_COUNTS.csv",index=False)
    print("XETRA_IDENTITY_AUDIT",pd.DataFrame(stats).to_string(index=False),flush=True)
    print("XETRA_PREPRICE_SELECTED",len(chosen),"verified",int(merged.official_eur_xetra_verified.sum()),flush=True)
    assert len(chosen)>=75,"Cannot truthfully build 100 ETF universe with this venue from existing candidates"
if __name__=="__main__":main()
