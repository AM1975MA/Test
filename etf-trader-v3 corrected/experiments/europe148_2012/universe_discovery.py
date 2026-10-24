#!/usr/bin/env python3
"""Europe UCITS ISIN discovery with strict exposure and 2012 inception audit.

Catalog source is pinned to a public 2026-09-13 commit and the original
certified 48 legal ISINs. This stage creates *candidate lists*, not certified
quotes, and never invents histories before a fund's inception.
"""
from __future__ import annotations
import argparse,hashlib,json,re
from pathlib import Path
import pandas as pd,numpy as np,requests
from collections import Counter
PUBLIC_SHA="a75a11330ac1825946ae1c37c60ec2135d03cf77"
PUBLIC_ROOT=f"https://raw.githubusercontent.com/albertored/etfdb/{PUBLIC_SHA}/csv"
CLUSTERS=("EU_EQUITY_BROAD","EU_EQUITY_SECTOR","EU_EQUITY_COUNTRY",
          "EU_EQUITY_FACTOR","SOVEREIGN_EUR","EU_PROPERTY")
ADD_QUOTAS=dict(zip(CLUSTERS,(16,22,21,18,18,5)))
REGION=set("Andorra Austria Belgium Bulgaria Croatia Cyprus Czech Republic Denmark Estonia Finland France Germany Greece Hungary Iceland Ireland Italy Latvia Liechtenstein Lithuania Luxembourg Malta Monaco Netherlands Norway Poland Portugal Romania Slovakia Slovenia Spain Sweden Switzerland United Kingdom United_Kingdom".split(" "))
REGION.update({"United Kingdom","Bosnia and Herzegovina","North Macedonia","Serbia","Montenegro","Jersey","Guernsey"})
NONSTRICT=re.compile(r"global|world|north america|latin america|emerging markets|asia|pacific|africa|japan|united states|u\.s\.|china|india|bitcoin|crypto|leveraged|short\b|inverse|3x\b|2x\b",re.I)
GEO=re.compile(r"europe|european|euro stoxx|eurozone|euro zone|euro area|euro government|euro sovereign|emu|stoxx 600|stoxx 50|ftse 100|ftse 250|ftse mib|germany|german|france|french|italy|italian|spain|spanish|switzerland|swiss|sweden|swedish|denmark|danish|austria|austrian|belgium|belgian|netherlands|dutch|poland|polish|uk equity|united kingdom|ftse all-share|dax|cac 40|ibex|bel 20|aex\b|atx\b|smi\b|omx\b",re.I)
COUNTRY=re.compile(r"germany|german|france|french|italy|italian|spain|spanish|switzerland|swiss|sweden|swedish|denmark|danish|austria|austrian|belgium|belgian|netherlands|dutch|poland|polish|finland|norway|norwegian|portugal|ireland|united kingdom|uk\b|ftse 100|ftse 250|ftse mib|dax\b|cac 40|ibex|bel 20|aex\b|atx\b|smi\b|omx\b",re.I)
SECTOR=re.compile(r"sector|banks|banking|financials|insurance|industrials|technology|information tech|health care|healthcare|health|consumer staples|consumer discretionary|utilities|telecommunications|real assets|chemicals|food.beverage|automobiles|retail|oil.gas|energy|resources|semiconductor|media|construction|travel.leisure|materials",re.I)
FACTOR=re.compile(r"factor|value|minimum vol|low volatility|momentum|quality|dividend|small cap|mid cap|multi.factor|equal weight|growth|size\b|fundamental|smart beta|minimum variance",re.I)
PROPERTY=re.compile(r"property|real estate|reit|epra|european property",re.I)
SOV=re.compile(r"euro government|euro sovereign|eur govt|euro gov|eurozone government|euro area government|euroland government|government bond|govt bond|bund\b|bunds\b|german government|france government|italian government|euro inflation.linked",re.I)
EXCLUDE_BONDS=re.compile(r"corporate|credit|high yield|emerging|asia|treasury.*us|us.*treasury|global|world",re.I)
def isin_valid(s):
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]",str(s)):return False
    digits="".join(str(ord(x)-55) if x.isalpha() else x for x in s)
    q=0
    for i,v in enumerate(map(int,digits[::-1])):
        t=v*(2 if i%2 else 1);q+=t//10+t%10
    return q%10==0
def retrieve(out,name):
    url=PUBLIC_ROOT+"/"+name
    r=requests.get(url,timeout=80)
    r.raise_for_status()
    p=out/name
    p.write_bytes(r.content)
    return p
def cluster(row):
    desc=(str(row["name"])+" "+str(row["index"]))
    a=str(row["asset_class"])
    if NONSTRICT.search(desc):return None,"EXCLUDED_NON_EU_UNDERLYING_TEXT"
    eu_share=row["europe_weight"]
    geo=GEO.search(desc) is not None
    if a=="bonds":
        if SOV.search(desc) and not EXCLUDE_BONDS.search(desc):
            return "SOVEREIGN_EUR","EUR_GOVERNMENT_INDEX"
        return None,"OTHER_CREDIT_OR_BONDS"
    if a=="realEstate" or PROPERTY.search(desc):
        if eu_share>=75 or geo:return "EU_PROPERTY","EU_PROPERTY_GEO"
        return None,"PROPERTY_NOT_EU"
    if a!="equity":return None,"NOT_EQUITY"
    if not geo and eu_share<75:return None,"NOT_STRICT_EU_EQUITY"
    if SECTOR.search(desc):return "EU_EQUITY_SECTOR","EU_SECTOR"
    if COUNTRY.search(desc) and not re.search(r"stoxx europe|msci europe|ftse developed europe",desc,re.I):
        return "EU_EQUITY_COUNTRY","EU_COUNTRY"
    if FACTOR.search(desc):return "EU_EQUITY_FACTOR","EU_FACTOR"
    return "EU_EQUITY_BROAD","EU_BROAD"
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--reference",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    raw=out/"source";raw.mkdir(exist_ok=True)
    files={k:retrieve(raw,k) for k in ("basic_info.csv","countries.csv")}
    catalog=pd.read_csv(files["basic_info.csv"],low_memory=False,dtype={"isin":str,"ticker":str})
    countries=pd.read_csv(files["countries.csv"],low_memory=False,dtype={"isin":str})
    print("OPEN_ETFDB_COLS",catalog.columns.tolist(),flush=True)
    assert "isin" in catalog and "inception_date" in catalog
    assert countries["isin"].is_unique and catalog["isin"].is_unique
    eu_cols=[c for c in countries.columns if c in REGION]
    assert len(eu_cols)>=24,eu_cols
    score=countries[["isin"]+eu_cols].copy()
    for col in eu_cols:score[col]=pd.to_numeric(score[col],errors="coerce").fillna(0).clip(lower=0)
    score["europe_weight"]=score[eu_cols].sum(axis=1).clip(upper=100)
    src=catalog.merge(score[["isin","europe_weight"]],on="isin",how="left",validate="one_to_one")
    src["europe_weight"]=src.europe_weight.fillna(0)
    src["inception_date"]=pd.to_datetime(src.inception_date,errors="coerce")
    src["name"]=src.name.fillna("")
    src["index"]=src["index"].fillna("")
    src["asset_class"]=src.asset_class.fillna("")
    src["isin_valid"]=src['isin'].apply(isin_valid)
    # The original 48 are legally VERIFIED via provider and exchange but
    # are not automatically interchangeable with today's catalog listing.
    ref=pd.read_csv(a.reference)
    ref=ref[ref.decision.isin(["A","B"])].copy()
    assert ref["isin"].nunique()==len(ref)==48, (len(ref),ref["isin"].nunique())
    assert ref["isin"].map(isin_valid).all()
    originals=set(ref["isin"])
    candidates=[]
    for _,d in src.iterrows():
        v=d.to_dict()
        if not v["isin_valid"]:continue
        c,why=cluster(v)
        if not c:continue
        if v["isin"] in originals:continue
        if pd.isna(v["inception_date"]):continue
        if v["inception_date"]>pd.Timestamp("2025-01-01"):continue
        if not str(v["ticker"]).strip() or str(v["ticker"])=="nan":continue
        if str(v["currency"]) not in ("EUR","GBP","CHF","USD"):continue
        rec=dict(isin=v["isin"],ticker=v["ticker"],name=v["name"],isin_valid=True,
             index=v["index"],asset_class=v["asset_class"],
             inception_date=v["inception_date"].date().isoformat(),
             fund_provider=v["fund_provider"],currency=v["currency"],
             fund_size_millions_eur=pd.to_numeric(v["size"],errors="coerce"),
             europe_weight_percent=float(v["europe_weight"]),
             cluster=c,selection_reason=why,
             reference="etfdb_"+PUBLIC_SHA,
             actual_yahoo_venue_unverified=True,
             exposure_2026_not_historical=True,
             quote_2012_not_yet_verified=True)
        candidates.append(rec)
    pool=pd.DataFrame(candidates)
    assert pool["isin"].is_unique
    pool["fund_size_millions_eur"]=pool.fund_size_millions_eur.fillna(0)
    pool["inception_date"]=pd.to_datetime(pool.inception_date)
    pool["since_2012"]=pool.inception_date.le(pd.Timestamp("2012-01-01"))
    pool["since_2017"]=pool.inception_date.le(pd.Timestamp("2017-01-01"))
    pool["since_2018"]=pool.inception_date.le(pd.Timestamp("2018-01-01"))
    pool["size_ok"]=pool.fund_size_millions_eur.ge(30)
    pool["priority"]=pool.since_2012.astype(int)*12+pool.since_2017.astype(int)*5+pool.since_2018.astype(int)*2+pool.size_ok.astype(int)*3+(pool.europe_weight_percent>=90).astype(int)
    pool=pool.sort_values(["cluster","priority","fund_size_millions_eur","isin"],ascending=[True,False,False,True])
    pool["inception_date"]=pool.inception_date.dt.strftime("%Y-%m-%d")
    pool.to_csv(out/"EU_CANDIDATE_CATALOG_AUDITED.csv",index=False)
    orig_counts=ref.benchmark_bucket.value_counts().to_dict()
    rows=[];selected=[]
    for cluster_name,quota in ADD_QUOTAS.items():
        eligible=pool[pool.cluster.eq(cluster_name)]
        take=eligible.head(quota)
        selected.extend(take.to_dict("records"))
        rows.append(dict(cluster=cluster_name,original_48=orig_counts.get(cluster_name,0),
             required_additional=quota,available_distinct_isin=len(eligible),
             available_pre2012=int(eligible.since_2012.sum()),available_pre2017=int(eligible.since_2017.sum()),
             preliminary_selected=len(take),shortfall=max(0,quota-len(take))))
    selected=pd.DataFrame(selected)
    selected.to_csv(out/"PRELIMINARY_EXTRA100_FOR_PRICE_VALIDATION.csv",index=False)
    audit=pd.DataFrame(rows)
    audit.to_csv(out/"SIX_CLUSTER_QUOTA_AUDIT.csv",index=False)
    (out/"CATALOG_MANIFEST.json").write_text(json.dumps(dict(
        etfdb_source_commit=PUBLIC_SHA,
        catalog_rows=len(catalog),eligible_unique_isin=len(pool),
        original_reference_48=len(ref),
        quotas=ADD_QUOTAS,
        screening_purpose="candidate_not_quote_certification",
        initial_precertification_selected=len(selected),
        shortfall=sum(int(x["shortfall"]) for x in rows),
        selection_asof_2026_not_historical=True,
        n_pre2012=int(pool.since_2012.sum()),n_pre2017=int(pool.since_2017.sum()),
        category_exposure_from_current_holdings_not_historical=True,
        no_proxy_backfill_before_fund_inception=True,
        candidate_list_is_not_verified_trade_universe=True),indent=2))
    print("UNIVERSE_DISCOVERY_PASS",len(pool),"preselected",len(selected),flush=True)
    print(audit.to_string(index=False),flush=True)
if __name__=="__main__":main()
