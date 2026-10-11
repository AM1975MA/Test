"""Read-only formula-derived warmup gates for residual Compact21 base NaNs.
Source-of-truth mappings manually transcribed from frozen kernel.build_features;
fail closed if any participating base feature is unmapped.
"""
import argparse,ast,json,re
from pathlib import Path
import numpy as np,pandas as pd
# Minimum number of PRIOR daily observations before signal date, from kernel.
# For e.g. 63 log returns, require 64 closes, hence prior >=63.
RULES={}
for h in (5,10,21,42,63,126,252):RULES[f"mom{h}"]=(h,"Close")
for h in (21,63,126):
 RULES.update({f"vol{h}":(h,"Close"),f"downvol{h}":(h,"Close"),
               f"drawdown{h}":(h-1,"Close"),f"efficiency{h}":(h,"Close")})
RULES.update({
 "mom126_ex21":(126,"Close"),"mom252_ex21":(252,"Close"),
 "acc_mom_5_21":(21,"Close"),"acc_mom_21_63":(63,"Close"),
 "vol_ratio_21_126":(126,"Close"),"skew63":(63,"Close"),
 "kurt63":(63,"Close"),"gkvol21":(20,"OHLC"),
 "log_adv63":(41,"CloseVolume"),"volume_surprise21":(14,"Volume"),
 "beta_mkt63":(63,"CloseMarket"),"corr_mkt63":(63,"CloseMarket"),
 "beta_mkt126":(126,"CloseMarket"),"corr_mkt126":(126,"CloseMarket"),
 "ma_gap50":(49,"Close"),"ma_gap200":(199,"Close"),
 "ema_gap20":(19,"Close"),"ema_gap50":(49,"Close"),
 "breakout_pos126":(125,"Close"),"breakout_pos252":(251,"Close"),
 "rsi14":(14,"Close"),"positive_frac63":(62,"Close"),
 "max_loss63":(63,"Close"),"max_gain63":(63,"Close"),
 "cvar10_63":(63,"Close"),"sign_entropy63":(62,"Close"),
 "autocorr1_63":(64,"Close"),
})
def feature_names():
 tree=ast.parse(Path("vendor/etf_trader_v2/src/etf_trader/source_only/kernel.py").read_text())
 return next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=="F2D_FEATURES" for t in n.targets))
def classify():
 p=argparse.ArgumentParser()
 for k in ("r1","r2","r3","raw1","raw2","raw3","out"):p.add_argument("--"+k,required=True)
 a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
 ff=feature_names();bases=[x for x in ff if not x.endswith(("_dev","_pct"))]
 assert set(bases)==set(RULES),{"missing_rules":sorted(set(bases)-set(RULES)),"extra_rules":sorted(set(RULES)-set(bases))}
 results=[];details=[];keys=[]
 for repeat in (1,2,3):
  f=Path(getattr(a,f"r{repeat}"))/"TI_COMPACT.parquet"
  d=pd.read_parquet(f).sort_values(["signal_date","ticker"]).reset_index(drop=True)
  d.signal_date=pd.to_datetime(d.signal_date)
  fin=np.isfinite(d[ff].to_numpy(float))
  inc=(fin.sum(axis=1)>=30)&~fin.all(axis=1)
  keys.append(d.loc[inc,["signal_date","ticker"]].reset_index(drop=True))
  rawroot=Path(getattr(a,f"raw{repeat}"));ticker_data={}
  for ticker in d.loc[inc,"ticker"].unique():
   raw=pd.read_csv(rawroot/f"{ticker}.csv",parse_dates=["date"]).sort_values("date")
   ticker_data[ticker]=(pd.DatetimeIndex(raw.date),raw)
  for base in bases:
   miss=np.flatnonzero(inc&d[base].isna().to_numpy())
   if not len(miss):continue
   required,kind=RULES[base]
   for z in miss:
    t=d.at[z,"ticker"];date=d.at[z,"signal_date"]
    idx,raw=ticker_data[t];pos=idx.get_indexer([date])[0]
    if pos<0:cause="RAW_SIGNAL_DATE_ABSENT"
    elif pos<required:cause="FORMULA_WARMUP_INSUFFICIENT_BARS"
    else:
     window=raw.iloc[pos-required:pos+1]
     reqfields=("Open","High","Low","Close") if kind=="OHLC" else (("Volume",) if kind=="Volume" else (("Close","Volume") if kind=="CloseVolume" else ("Close",)))
     if not all(field in window for field in reqfields):cause="REQUIRED_RAW_COLUMN_ABSENT"
     elif any(~np.isfinite(window[field].to_numpy(float)).all() for field in reqfields):cause="NONFINITE_REQUIRED_INPUT"
     elif any((window[field].to_numpy(float)<=0).any() for field in reqfields if field!="Volume"):cause="NONPOSITIVE_REQUIRED_PRICE"
     elif kind=="Volume" and (window.Volume.to_numpy(float)<=0).sum()>0:
      cause="VOLUME_ZERO_POSSIBLE_LOG_UNDEFINED"
     elif kind=="CloseVolume" and not np.any((window.Close*window.Volume).to_numpy(float)>0):
      cause="NO_POSITIVE_DOLLAR_VOLUME"
     elif base.startswith("breakout_pos") and window.Close.max()==window.Close.min():
      cause="KNOWN_ZERO_RANGE_DENOMINATOR"
     elif base.startswith("efficiency") and np.diff(np.log(window.Close.to_numpy(float))).__abs__().sum()==0:
      cause="KNOWN_ZERO_EFFICIENCY_DENOMINATOR"
     elif base=="vol_ratio_21_126" and np.std(np.diff(np.log(window.Close.to_numpy(float)))[-126:])==0:
      cause="KNOWN_ZERO_VOLATILITY_DENOMINATOR"
     else:cause="ENOUGH_RAW_HISTORY_FORMULA_DOMAIN_UNVERIFIED"
    details.append(dict(repeat=repeat,ticker=t,signal_date=str(date.date()),feature=base,
      min_prior_bars=required,raw_bars_through_signal=int(pos+1) if pos>=0 else 0,
      raw_fields=kind,cause=cause))
  arows=[x for x in details if x["repeat"]==repeat]
  results.append({"repeat":repeat,"missing_base_cells":len(arows),"causes":pd.Series([x["cause"] for x in arows]).value_counts().to_dict()})
 for k in (1,2):pd.testing.assert_frame_equal(keys[0],keys[k],check_exact=True)
 df=pd.DataFrame(details);df.to_csv(out/"EXACT_FORMULA_WARMUP_CELLS.csv",index=False)
 df.groupby(["repeat","feature","cause"]).size().reset_index(name="cells").to_csv(out/"PER_FEATURE_CAUSES.csv",index=False)
 summary={"status":"FORMULA_WARMUP_GATE_CLASSIFICATION_COMPLETE","source":"frozen kernel build_features static minimum lookbacks",
   "by_repeat":results,"limitation":"Windows meeting minimum requirements may still have rolling missingness, undefined domains or earlier input gaps; these are not certified without full kernel replay",
   "no_training":True,"no_imputation":True}
 (out/"RESULT.json").write_text(json.dumps(summary,indent=2)+"\n")
 print(json.dumps(summary,indent=2))
if __name__=="__main__":classify()
