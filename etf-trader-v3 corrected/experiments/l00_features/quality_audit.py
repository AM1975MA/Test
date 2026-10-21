#!/usr/bin/env python3
"""V3 L00: quality/semantics audit of every feature; NEVER optimize against labels.

Outputs 203-column coverage, full same-month zero-MAD audit, raw/derived
redundancy, ETF-age missingness and data semantics risks. Uses the EXACT 149
frozen source, not 390-day truncated snapshots. No future targets, labels,
model fits, CAGR or allocation.
"""
import argparse,sys,hashlib,json
from pathlib import Path
from collections import defaultdict
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent
V3=HERE.parents[1]
sys.path.insert(0,str(V3/"src"))
from etf_trader_v3.source_only import kernel as k, features as extra
from etf_trader_v3.source_only.raw_io import load_ticker_csv_folder

def signature(s):
    x=np.asarray(s,dtype=np.float64)
    nan=np.isnan(x);inf=np.isinf(x)
    finite=np.where(nan,0.,x)
    finite=np.where(inf,np.sign(x)*1.e300,finite)
    data=np.ascontiguousarray(finite,dtype="<f8").tobytes()
    mask=np.packbits(nan).tobytes()+np.packbits(inf).tobytes()
    return hashlib.sha256(mask+data).hexdigest()

def audit(raw,out):
    dest=Path(out);dest.mkdir(parents=True,exist_ok=True)
    mats,cats,_=load_ticker_csv_folder(raw)
    assert len(cats)==149 and all(len(v.columns)==149 for v in mats.values())
    assert sorted(mats)==["Close","High","Low","Open","Volume"]
    mats={n:x.loc[x.index>=pd.Timestamp("2011-01-01")] for n,x in mats.items()}
    dates,compact,tail,D=k.build_features(mats)
    add=extra.build(mats,cats,dates)
    specs=[("compact",compact,k.F2D_FEATURES),("tail",tail,k.TAIL_FEATURES),
           ("extra",add,sum(extra.GROUPS.values(),[]))]
    assert [len(x[2]) for x in specs]==[125,60,18]
    total=[]
    for block,panel,cols in specs:
        assert len(panel)==len(dates)*149,(block,len(panel),len(dates)*149)
        assert not panel[["signal_date","ticker"]].duplicated().any()
        for name in cols:
            v=pd.to_numeric(panel[name],errors="coerce")
            numeric=v[np.isfinite(v.to_numpy(float))]
            total.append({"block":block,"feature":name,
                "observations":len(panel),"valid_observations":int(len(numeric)),
                "missing_fraction":float(v.isna().mean()),
                "n_distinct_values":int(numeric.nunique()),
                "min":float(numeric.min()) if len(numeric) else None,
                "max":float(numeric.max()) if len(numeric) else None,
                "std":float(numeric.std()) if len(numeric)>1 else None})
    coverage=pd.DataFrame(total)
    coverage.to_csv(dest/"FEATURE_COVERAGE_203.csv",index=False)
    assert len(coverage)==203
    # Exact duplicates within the same feature block: identical value and NaN mask.
    duplicate_pairs=[]
    for block,panel,cols in specs:
        groups=defaultdict(list)
        for col in cols:
            groups[signature(panel[col])].append(col)
        for equal in groups.values():
            if len(equal)>1:
                duplicate_pairs.append({"block":block,"features":equal,"members":len(equal)})
    (dest/"EXACT_DUPLICATE_GROUPS.json").write_text(json.dumps(duplicate_pairs,indent=2))
    # Robust cross-sectional deviation undefined when entire universe has zero
    # MAD; detect it explicitly and report, without silently changing feature math.
    cs=[]
    for name in k.F2D_FEATURES:
        if not name.endswith("_dev"):continue
        base=name[:-4]
        pivot=compact.pivot(index="signal_date",columns="ticker",values=base).reindex(index=dates)
        med=pivot.median(axis=1)
        mad=pivot.sub(med,axis=0).abs().median(axis=1)
        eligible=pivot.notna().sum(axis=1)>=20
        bad=eligible & mad.eq(0)
        cs.append({"feature":name,"base":base,"months_with_n_ge_20":int(eligible.sum()),
            "months_with_zero_mad_and_20_etfs":int(bad.sum()),
            "months_with_at_least_20_etfs":int(eligible.sum()),
            "cs_zero_mad_fraction":float(bad.sum()/max(1,eligible.sum()))})
    pd.DataFrame(cs).to_csv(dest/"CROSS_SECTION_ZERO_MAD.csv",index=False)
    # Genuine prehistory warm-up vs mature-month missingness.
    close=mats["Close"]
    history=close.notna().cumsum().reindex(dates)
    missing=[]
    for block,panel,cols in specs:
        pivot_age=history.stack(dropna=False).rename("observed_close_days").reset_index()
        pivot_age.columns=["signal_date","ticker","observed_close_days"]
        x=panel.merge(pivot_age,on=["signal_date","ticker"],validate="one_to_one")
        for name in cols:
            for label,mask in [("young_lt252",x.observed_close_days.lt(252)),
                               ("mature_ge252",x.observed_close_days.ge(252))]:
                subset=x.loc[mask,name]
                missing.append({"block":block,"feature":name,"age_group":label,
                     "count":int(len(subset)),"missing_fraction":float(subset.isna().mean()) if len(subset) else None})
    pd.DataFrame(missing).to_csv(dest/"MISSINGNESS_BY_ETF_AGE.csv",index=False)
    C=mats["Close"];O=mats["Open"];H=mats["High"];L=mats["Low"];V=mats["Volume"]
    consistency=((H>=np.maximum(O,C))&(L<=np.minimum(O,C))&(H>=L))
    valid_c=O.notna()&H.notna()&L.notna()&C.notna()
    failures=(~consistency)&valid_c
    anomaly_count=int(failures.to_numpy().sum())
    raw_info={"n_tickers":149,"n_signal_months":len(dates),"first_date":str(C.index.min().date()),
        "last_date":str(C.index.max().date()),"ohlc_violations":anomaly_count,
        "ohlc_total_valid":int(valid_c.to_numpy().sum()),
        "volume_zero_or_negative":int((V.notna()&(V<=0)).to_numpy().sum()),
        "zero_return_or_flat_period":"Must distinguish zero from missing",
        "critical_adjustment_semantics":"Close/Open/High/Low may be adjusted: Close*Volume is a proxy, not unadjusted dollar turnover",
        "raw_source_run":39482809691,"uses_future_targets":False}
    (dest/"OHLCV_AUDIT.json").write_text(json.dumps(raw_info,indent=2))
    risks=[]
    if anomaly_count:risks.append(f"{anomaly_count} OHLC contradictions need investigation")
    for x in duplicate_pairs:
        risks.append(f"{x['block']} exact duplicates: {', '.join(x['features'])}")
    for row in cs:
        if row["months_with_zero_mad_and_20_etfs"]:
            risks.append(f"{row['feature']} lost information in {row['months_with_zero_mad_and_20_etfs']} months with zero cross-sectional MAD")
    (dest/"FINDINGS.md").write_text(
        "# V3 L00: source/feature quality audit (no prediction targets)\n\n"+
        f"Audited {len(coverage)} feature columns across {len(dates)} month ends and 149 ETF price histories.\n\n"+
        f"OHLC contradictions: {anomaly_count}. Exact duplicate feature groups: {len(duplicate_pairs)}. "+
        f"Robust-dev families with at least one zero-MAD month: {sum(z['months_with_zero_mad_and_20_etfs']>0 for z in cs)}.\n\n"+
        "The feature audit is descriptive; no formula changed and **no predictive superiority is claimed**. "+
        "Missingness is split by ETF history length, not imputed. Structural duplicate names and "+
        "adjusted-price times volume proxies should be corrected only in independent preregistered comparisons.\n\n"+
        "\n".join("- "+r for r in risks[:45])+"\n")
    (dest/"MANIFEST.json").write_text(json.dumps({
        **raw_info,"n_feature_columns":len(coverage),"n_exact_duplicate_groups":len(duplicate_pairs),
        "requires_review_before_feature_freeze":bool(anomaly_count),
        "production_modified":False},indent=2))
    print("V3_L00_QUALITY_AUDIT_COMPLETED",raw_info,
          "dup_groups",duplicate_pairs[:12],"zero_mad",sum(z["months_with_zero_mad_and_20_etfs"]>0 for z in cs),flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--raw",default="etf_trader_raw")
    p.add_argument("--out",default="runs/v3_l00_quality")
    a=p.parse_args()
    audit(a.raw,a.out)
