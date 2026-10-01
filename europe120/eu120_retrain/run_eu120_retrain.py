#!/usr/bin/env python3
from __future__ import annotations

import json, os, re, shutil, subprocess, sys, hashlib, time
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent.parent
OUT = ROOT / "results"
MODELS = OUT / "model_bundle"
RAW_TRAIN = OUT / "raw120"
RAW_TARGET = RAW_TRAIN
RAW_REF = OUT / "raw_refs"
MA3_TRAIN = OUT / "ma3_train149"
MA3_TARGET = OUT / "ma3_target56"
for p in (OUT, MODELS, RAW_TRAIN, RAW_TARGET, RAW_REF, MA3_TRAIN, MA3_TARGET):
    p.mkdir(parents=True, exist_ok=True)

ETF = Path(os.environ.get("ETF_TRADER_ROOT", REPO / "_etf_trader"))
sys.path.insert(0, str(ETF / "src"))

import yfinance as yf
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import Ridge
from sklearn.ensemble import ExtraTreesRegressor
from xgboost import XGBRanker, XGBRegressor

from etf_trader.source_only import kernel as k
from etf_trader.source_only.raw_io import load_ticker_csv_folder
from etf_trader.ma3 import producer, ddfirst, v6, highcagr24
from etf_trader.ma3.hybrid_producer import (
    FEATURES_42, ET_MODEL_KW, XGB_MODEL_KW,
    ET_WEIGHT, XGB_WEIGHT, TAIL_LAG_WEIGHTS, TAIL_POWER,
    BASE_WEIGHT, TAIL_WEIGHT,
)
from bocpd_router import route_trace

START = "2005-01-01"
END = "2026-08-03"
FIRST_SIGNAL = pd.Timestamp("2017-01-31")
LAST_SIGNAL = pd.Timestamp("2026-06-30")
EVAL_END = pd.Timestamp("2026-07-01")
REF_TICKERS = ["SPY","HYG","IEF","BIL","SHV"]

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1<<20), b""):
            h.update(b)
    return h.hexdigest()

def download_folder(meta: pd.DataFrame, out: Path) -> None:
    # Source-only run: read the quality-gated frozen CSVs and original reference
    # series. No network price request and no regenerated history.
    out.mkdir(parents=True, exist_ok=True)
    meta = meta[["ticker","macro_category"]].drop_duplicates().copy()
    meta["ticker"] = meta["ticker"].astype(str).str.upper()
    meta.to_csv(out/"universe.csv", index=False)
    root=Path(os.environ["FROZEN_EU120_ROOT"]) if len(meta)==120 else Path(os.environ["FROZEN_149_ROOT"])
    source=root/("raw_ticker_csv" if len(meta)==120 else "etf_trader_raw")
    missing=[]
    for t in meta.ticker:
        p=source/f"{t}.csv"
        if not p.exists():missing.append(t)
        else:shutil.copyfile(p,out/p.name)
    if missing:raise RuntimeError(f"missing frozen inputs: {missing}")

def set_kernel_categories(cats: dict[str,str], tickers: list[str]) -> None:
    k.ALL_TICKERS=list(tickers);k.TICKER_CATEGORY=dict(cats);k.CATEGORY_TICKERS={c:sorted([t for t in tickers if cats.get(t)==c]) for c in sorted(set(cats.values()))}

def build_titanium_parts(raw: Path, *, market_spy_raw: Path|None=None, candidates: list[str]|None=None):
    mats,cats,_=load_ticker_csv_folder(raw);tickers=list(map(str,mats["Close"].columns))
    if market_spy_raw is not None and "SPY" not in mats["Close"].columns:
        rm,_,_=load_ticker_csv_folder(market_spy_raw)
        for f in mats:mats[f]=pd.concat([mats[f],rm[f]["SPY"].rename("SPY")],axis=1).sort_index()
        cats=dict(cats);cats["SPY"]="REF_MARKET";tickers=tickers+["SPY"]
    set_kernel_categories(cats,tickers);dates=k.month_end_dates(mats["Close"].index)
    if len(dates) and dates[-1]==mats["Close"].index[-1]:dates=dates[:-1]
    _,compact,tail,_=k.build_features(mats);compact=compact[compact.signal_date.isin(dates)].copy();tail=tail[tail.signal_date.isin(dates)].copy()
    if candidates is not None:
        compact=compact[compact.ticker.isin(candidates)].copy();tail=tail[tail.ticker.isin(candidates)].copy();cats2={t:cats[t] for t in candidates};set_kernel_categories(cats2,candidates)
    return mats,cats,dates,compact,tail

def add_train_labels(compact,tail,mats,dates):
    c=k.add_labels(compact,mats["Open"],dates);t=k.add_labels(tail,mats["Open"],dates)
    no=t.drop(columns=[x for x in t.columns if x.startswith(("fwd_","target_","exit_")) or x in ["entry_date","y_tailmix"]],errors="ignore")
    macro,mfeatures=k.build_macro_panel(no,t);return c,t,macro,mfeatures

def dummy_macro(tail,cats):
    set_kernel_categories(cats,list(cats));labels=tail[["signal_date","ticker"]].drop_duplicates().copy()
    for c in ("fwd_ret_21","fwd_ret_42","fwd_ret_63"):labels[c]=np.nan
    labels["exit_date_63"]=pd.NaT;return k.build_macro_panel(tail,labels)

def compact_fit_predict(tr,te,cutoff,tag,modeldir):
    valid=tr[k.F2D_FEATURES].notna().sum(axis=1)>=30;train=tr[(tr.signal_date<cutoff)&(tr.exit_date_21<cutoff)&tr.target_rank_pct.notna()&valid].sort_values(["signal_date","ticker"])
    vte=te[k.F2D_FEATURES].notna().sum(axis=1)>=30;test=te[vte].sort_values(["signal_date","ticker"]).copy()
    if train.signal_date.nunique()<60 or test.empty:return test[["signal_date","ticker"]].assign(compact_raw=np.nan)
    groups=train.groupby("signal_date",sort=True).size().tolist();y=(train.target_rank_pct*100).round().astype(int);X=train[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan);Xt=test[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan);ps=[]
    for seed in k.COMPACT_SEEDS:
        md=modeldir/f"{tag}_compact21_seed{seed}.json";md.parent.mkdir(parents=True,exist_ok=True);m=XGBRanker(**k.COMPACT_PARAMS,random_state=seed)
        if md.exists():m.load_model(md)
        else:m.fit(X,y,group=groups,verbose=False);m.save_model(md)
        ps.append(m.predict(Xt))
    o=test[["signal_date","ticker"]].copy();o["compact_raw"]=np.mean(ps,axis=0);return o

def tail_fit_predict(tr,te,cutoff,tag,modeldir):
    valid=tr[k.TAIL_FEATURES].notna().sum(axis=1)>=12;train=tr[(tr.signal_date<cutoff)&(tr.exit_date_63<cutoff)&tr.y_tailmix.notna()&valid];vte=te[k.TAIL_FEATURES].notna().sum(axis=1)>=12;test=te[vte].copy()
    if train.empty or test.empty:return test[["signal_date","ticker"]].assign(tail_raw=np.nan)
    path=modeldir/f"{tag}_titanium_tail.joblib";m=joblib.load(path) if path.exists() else make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=30.0))
    if not path.exists():m.fit(train[k.TAIL_FEATURES],train.y_tailmix);joblib.dump(m,path)
    o=test[["signal_date","ticker"]].copy();o["tail_raw"]=m.predict(test[k.TAIL_FEATURES]);return o

def macro_fit_predict(train_macro,target_macro,mfeatures,cutoff,tag,modeldir):
    tr=train_macro[(train_macro.signal_date<cutoff)&(train_macro.label_exit_date_63<cutoff)&train_macro.target_rank.notna()];te=target_macro.copy()
    if len(tr)<=50 or te.empty:return pd.DataFrame(columns=["signal_date","macro_category","macro_raw"])
    path=modeldir/f"{tag}_titanium_macro.joblib";m=joblib.load(path) if path.exists() else make_pipeline(SimpleImputer(strategy="median"),StandardScaler(),Ridge(alpha=50.0))
    if not path.exists():m.fit(tr[mfeatures],tr.target_rank);joblib.dump(m,path)
    z=te[["signal_date","macro_category"]].copy();z["macro_raw"]=m.predict(te[mfeatures]);return z

def assemble_base(preds,macro_preds,target_cats):
    p=pd.concat(preds,ignore_index=True);p["compact_rank"]=p.groupby("signal_date").compact_raw.rank(pct=True);p["tail_rank"]=p.groupby("signal_date").tail_raw.rank(pct=True);p["titanium_score"]=.70*p.compact_rank+.30*p.tail_rank
    mp=pd.concat(macro_preds,ignore_index=True) if macro_preds else pd.DataFrame(columns=["signal_date","macro_category","macro_raw"])
    if len(mp):
        mp["macro_z"]=mp.groupby("signal_date").macro_raw.transform(lambda x:(x-x.mean())/(x.std(ddof=0)+1e-12));tops=[]
        for dt,g in mp.groupby("signal_date"):
            g=g.sort_values("macro_z",ascending=False);tops.append({"signal_date":dt,"top_macro":g.iloc[0].macro_category,"macro_gap_z":float(g.iloc[0].macro_z-g.iloc[1].macro_z) if len(g)>1 else 0.})
        p["macro_category"]=p.ticker.map(target_cats);p=p.merge(pd.DataFrame(tops),on="signal_date",how="left");p["macro_bonus"]=np.where((p.macro_category==p.top_macro)&(p.macro_gap_z>=.75)&(p.tail_rank>=.80),.15,0.);p["titanium_score"]+=p.macro_bonus
    p["BASE"]=p.groupby("signal_date").titanium_score.rank(pct=True);return p[["signal_date","ticker","BASE"]].sort_values(["signal_date","ticker"])

def fit_titanium_cross(train_parts,target_parts,target_cats,mode,signals,modeldir):
    trc,trt,trm,mfeatures=train_parts;tec,tet,tem,_=target_parts;preds=[];macros=[]
    groups=[(pd.Timestamp(f"{y}-01-01"),signals[signals.year==y],f"A{y}") for y in sorted(set(signals.year))] if mode=="annual" else [(pd.Timestamp(sd),pd.DatetimeIndex([sd]),"M"+pd.Timestamp(sd).strftime("%Y%m%d")) for sd in signals]
    for gi,(cutoff,sds,tag) in enumerate(groups,1):
        if not len(sds):continue
        cp=compact_fit_predict(trc,tec[tec.signal_date.isin(sds)],cutoff,tag,modeldir);tp=tail_fit_predict(trt,tet[tet.signal_date.isin(sds)],cutoff,tag,modeldir);preds.append(cp.merge(tp,on=["signal_date","ticker"],how="outer"));mp=macro_fit_predict(trm,tem[tem.signal_date.isin(sds)],mfeatures,cutoff,tag,modeldir)
        if len(mp):macros.append(mp)
        if gi%12==0 or gi==len(groups):print("TIT",mode,gi,"/",len(groups),flush=True)
    return assemble_base(preds,macros,target_cats)

def corrected_target(panel):return .45*panel.target_rank_21.astype(float).pow(1.5)+.35*panel.target_rank_42.astype(float).pow(1.5)+.20*panel.target_rank_63.astype(float).pow(1.5)

def fit_ma3_one(train_panel,target_panel,cutoff,sds,tag,modeldir):
    tr=train_panel[(train_panel.signal_date<cutoff)&(train_panel.exit_date_63<cutoff)].copy();tr["Y"]=corrected_target(tr);tr=tr[tr.Y.notna()];te=target_panel[target_panel.signal_date.isin(sds)].copy()
    if tr.empty or te.empty:return pd.DataFrame(columns=["signal_date","ticker","ET_RANK","XGB_RANK","TAIL_EXTRA"])
    ip=modeldir/f"{tag}_ma3_imputer.joblib";ep=modeldir/f"{tag}_ma3_et.joblib";xp=modeldir/f"{tag}_ma3_xgb.json";xcfg=dict(XGB_MODEL_KW);xcfg["n_jobs"]=2
    if ip.exists() and ep.exists() and xp.exists():
        imp=joblib.load(ip);et=joblib.load(ep);xb=XGBRegressor(**xcfg);xb.load_model(xp)
    else:
        imp=SimpleImputer(strategy="median");xtr=imp.fit_transform(tr[list(FEATURES_42)]);y=tr.Y.to_numpy(float);et=ExtraTreesRegressor(n_jobs=2,**ET_MODEL_KW);et.fit(xtr,y);xb=XGBRegressor(**xcfg);xb.fit(xtr,y);joblib.dump(imp,ip);joblib.dump(et,ep);xb.save_model(xp)
    xt=imp.transform(te[list(FEATURES_42)]);te["ET_RAW"]=et.predict(xt);te["XGB_RAW"]=xb.predict(xt);te["ET_RANK"]=te.groupby("signal_date").ET_RAW.rank(pct=True,method="average");te["XGB_RANK"]=te.groupby("signal_date").XGB_RAW.rank(pct=True,method="average");te["TAIL_EXTRA"]=ET_WEIGHT*te.ET_RANK+XGB_WEIGHT*te.XGB_RANK;return te[["signal_date","ticker","ET_RANK","XGB_RANK","TAIL_EXTRA"]]

def fit_ma3_cross(train_panel,target_panel,mode,signals,modeldir):
    groups=[(pd.Timestamp(f"{y}-01-01"),signals[signals.year==y],f"A{y}") for y in sorted(set(signals.year))] if mode=="annual" else [(pd.Timestamp(sd),pd.DatetimeIndex([sd]),"M"+pd.Timestamp(sd).strftime("%Y%m%d")) for sd in signals];outs=[]
    for i,(cutoff,sds,tag) in enumerate(groups,1):
        outs.append(fit_ma3_one(train_panel,target_panel,cutoff,sds,tag,modeldir));
        if i%12==0 or i==len(groups):print("MA3",mode,i,"/",len(groups),flush=True)
    return pd.concat(outs,ignore_index=True)

def calendar_from_open(open_df,signals):
    idx=open_df.index;rows=[]
    for i,sd in enumerate(signals):
        p=idx.get_indexer([sd])[0]
        if p<0 or p+1>=len(idx):continue
        entry=idx[p+1];exit_=pd.NaT
        if i+1<len(signals):
            pn=idx.get_indexer([signals[i+1]])[0];exit_=idx[pn+1] if pn>=0 and pn+1<len(idx) else pd.NaT
        rows.append({"signal_date":sd,"entry_date":entry,"exit_date":exit_})
    return pd.DataFrame(rows)

def score_from_panel(p,cal,tickers,monthly=False,pre=None):
    dates=pd.DatetimeIndex(cal.signal_date)
    def mat(df,col,ds=dates):return df.pivot(index="signal_date",columns="ticker",values=col).reindex(index=ds,columns=tickers).to_numpy(float)
    B=mat(p,"BASE");ET=mat(p,"ET_RANK");X=mat(p,"XGB_RANK");T=.6*ET+.4*X
    if monthly and pre is not None:
        hd=pd.DatetimeIndex([pd.Timestamp("2016-11-30"),pd.Timestamp("2016-12-30"),*list(dates)]);alltail=pd.concat([pre,p[["signal_date","ticker","TAIL_EXTRA"]]],ignore_index=True);TT=mat(alltail,"TAIL_EXTRA",hd);sm=.4*TT[2:]+.3*TT[1:-1]+.3*TT[:-2]
    else:
        l1=np.vstack([T[:1],T[:-1]]);l2=np.vstack([T[:1],T[:1],T[:-2]]);sm=.4*T+.3*l1+.3*l2
    return .475*B+.525*np.power(np.clip(sm,0,1),1.10),{"BASE":B,"ET_RANK":ET,"XGB_RANK":X}

def daily_state(score,pm,cal,ds,BM,BOK):
    B=BM.shape[0];D=len(ds);agree=np.zeros((B,D),bool)
    for m,row in enumerate(cal.itertuples(index=False)):
        a=int(ds.searchsorted(pd.Timestamp(row.entry_date)));e=int(ds.searchsorted(pd.Timestamp(row.exit_date)))
        if a>=D or e<=a:continue
        S=np.where(BOK,score[m][BM],-np.inf);order=np.argsort(-S,axis=1)[:,:2];ids=np.take_along_axis(BM,order,axis=1);t1,t2=ids[:,0],ids[:,1];am=(pm["ET_RANK"][m,t1]>pm["ET_RANK"][m,t2])&(pm["XGB_RANK"][m,t1]>pm["XGB_RANK"][m,t2]);agree[:,a:e]=am[:,None]
    return agree

def risk_transform(dd):
    g=np.asarray(dd,float).copy();g[np.isclose(g,.95)]=1.0;g[np.isclose(g,.75)]=highcagr24.C4_GROSS;g[g<=.251]=highcagr24.SEVERE_GROSS;return g

def conf_weights(base,g,agree):
    w=np.asarray(base.weight1,float).copy();w[(g[None,:]>=.999)&(base.margin>=highcagr24.TOP1_MARGIN)]=1.0;w[(g[None,:]<.999)&(base.margin>=highcagr24.TOP1_MARGIN)&agree]=1.0;return w

def metrics(E):
    lr=np.diff(np.log(np.r_[1.0,E]));r=np.expm1(lr);n=len(lr);cagr=float(np.expm1(lr.sum()*252/n));eq=np.exp(np.cumsum(lr));pk=np.maximum.accumulate(np.r_[1.,eq])[1:];dd=float((eq/pk-1).min());sh=float(r.mean()*np.sqrt(252)/r.std(ddof=1)) if r.std(ddof=1)>0 else 0.;return {"cagr":cagr,"maxdd":dd,"sharpe":sh,"terminal_equity":float(E[-1])}

def replay(score,pm,cal,candidate_mats,ref_mats,tickers):
    refs=[x for x in REF_TICKERS if x not in tickers];cols=tickers+refs;mats={}
    for f in ("Open","Low","Close"):mats[f]=pd.concat([candidate_mats[f][tickers],ref_mats[f][refs]],axis=1).sort_index().reindex(columns=cols).ffill().bfill()
    ti={t:i for i,t in enumerate(cols)};start=pd.Timestamp(cal.entry_date.min());end=pd.Timestamp(cal.exit_date.max());Odf=mats["Open"].loc[:end];Ldf=mats["Low"].reindex(Odf.index);Cdf=mats["Close"].reindex(Odf.index);st=Odf.index.get_loc(start);en=Odf.index.get_loc(end);ds=Odf.index[st:en+1];Cseg=Cdf.loc[ds];ddgross=np.asarray(ddfirst.sync_c95_m75_gross(Cdf)[st:en+1],float);g=risk_transform(ddgross);ex=ddfirst.daily_execution_inputs(Odf,Ldf,Cdf);O,L,C,PC,gap,ud1,uneg,UH,SA=[ex[x][st:en+1] for x in ["O","L","C","PC","gap","ud1","uneg","UH","SA"]];BM=np.arange(len(tickers),dtype=np.int32)[None,:];BOK=np.ones_like(BM,dtype=bool);base=producer.allocations_from_score(score,cal,ds,BM,BOK,continuous=True);agree=daily_state(score,pm,cal,ds,BM,BOK);w=conf_weights(base,g,agree);s6=v6.build_v6_state(Cseg,base.d1,base.d2,base.weight1,ddgross);alt=s6.alt_idx.copy();alt[alt>=len(tickers)]=-1;E,T,_,_=v6.simulate_with_alt.py_func(base.d1,base.d2,w,O,L,C,PC,gap,ud1,uneg,UH,SA,ti["BIL"],ti["SHV"],g,alt,True,.001);m=metrics(E[0]);m["annualized_turnover"]=float(T.mean()*252);return m,E[0],T[0],ds

def main():
    target=pd.read_csv(ROOT/"UNIVERSE_120.csv");srcu=target.copy();refs=pd.DataFrame({"ticker":REF_TICKERS,"macro_category":["REF_US","REF_CREDIT","REF_BOND","REF_CASH","REF_CASH"]})
    assert len(target)==120 and target.ticker.nunique()==120
    download_folder(srcu,RAW_TRAIN);download_folder(refs,RAW_REF)
    env=os.environ.copy();env["PYTHONPATH"]=str(ETF/"src");subprocess.run([sys.executable,str(ROOT/"build_ma3_panel_causal.py"),"--data",str(RAW_TRAIN),"--output",str(MA3_TRAIN)],check=True,env=env,cwd=ETF)
    train_panel=pd.read_pickle(MA3_TRAIN/"RAW_FEATURE_PANEL.pkl");target_panel=train_panel.copy()
    for df in (train_panel,target_panel):df["signal_date"]=pd.to_datetime(df.signal_date);df["exit_date_63"]=pd.to_datetime(df.exit_date_63)
    target_tickers=target.ticker.astype(str).tolist();target_cats=dict(zip(target.ticker,target.macro_category));tmats,tcats,tdates,tcomp,ttail=build_titanium_parts(RAW_TRAIN,market_spy_raw=RAW_REF,candidates=target_tickers);train_parts=add_train_labels(tcomp,ttail,tmats,tdates);xcomp=tcomp.copy();xtail=ttail.copy();target_macro,target_mfeatures=dummy_macro(xtail,target_cats);target_parts=(xcomp,xtail,target_macro,target_mfeatures)
    signals=pd.DatetimeIndex(sorted(set(xcomp.signal_date)));signals=signals[(signals>=pd.Timestamp("2016-11-30"))&(signals<=LAST_SIGNAL)];p45_signals=signals[signals>=FIRST_SIGNAL]
    baseA=fit_titanium_cross(train_parts,target_parts,target_cats,"annual",p45_signals,MODELS/"annual");baseM=fit_titanium_cross(train_parts,target_parts,target_cats,"monthly",p45_signals,MODELS/"monthly");maA=fit_ma3_cross(train_panel,target_panel,"annual",p45_signals,MODELS/"annual");maM=fit_ma3_cross(train_panel,target_panel,"monthly",signals,MODELS/"monthly");pA=baseA.merge(maA,on=["signal_date","ticker"],how="inner");pM=baseM.merge(maM,on=["signal_date","ticker"],how="inner");preM=maM[maM.signal_date.isin([pd.Timestamp("2016-11-30"),pd.Timestamp("2016-12-30")])][["signal_date","ticker","TAIL_EXTRA"]]
    cand_mats,_,_=load_ticker_csv_folder(RAW_TARGET);ref_mats,_,_=load_ticker_csv_folder(RAW_REF);cal=calendar_from_open(cand_mats["Open"],p45_signals).dropna(subset=["exit_date"]).reset_index(drop=True);pA=pA[pA.signal_date.isin(cal.signal_date)].copy();pM=pM[pM.signal_date.isin(cal.signal_date)].copy();pA.to_csv(OUT/"ANNUAL_PREDICTIONS_120.csv",index=False);pM.to_csv(OUT/"MONTHLY_PREDICTIONS_120.csv",index=False);print("PREDICTIONS_SAVED",len(pA),len(pM),flush=True)
    # The cross-market replay is isolated in replay_audited.py. The older
    # single-exchange replay below is retained only for historical diagnosis.
    if os.environ.get("EU120_LEGACY_REPLAY")!="1":return
    sA,pmA=score_from_panel(pA,cal,target_tickers,False);sM,pmM=score_from_panel(pM,cal,target_tickers,True,preM)
    results={};paths={}
    for name,s,pm in [("annual",sA,pmA),("monthly",sM,pmM)]:
        m,E,T,ds=replay(s,pm,cal,cand_mats,ref_mats,target_tickers);results[name]=m;paths[name]=E;print(name,json.dumps(m),flush=True)
    shadow=[]
    for row in cal.itertuples(index=False):
        entry=pd.Timestamp(row.entry_date);end=pd.Timestamp(row.exit_date)
        a=int(ds.get_indexer([entry])[0]);b=int(ds.get_indexer([end])[0])
        if a<0 or b<=a:raise RuntimeError(f"shadow calendar mismatch {entry} {end}")
        ea=paths["annual"];em=paths["monthly"]
        # E[k] is already valued at the next session's open. At outcome_end
        # only E[b-1] has matured; E[b] would consume the following open.
        ra=float(ea[b-1]/(ea[a-1] if a else 1.)-1)
        rm=float(em[b-1]/(em[a-1] if a else 1.)-1)
        ga=np.log1p(ra);gm=np.log1p(rm)
        skill=float(np.clip((gm-ga)/(abs(gm)+abs(ga)+1e-12),-1,1))
        shadow.append({"interval_signal_date":row.signal_date,"outcome_end":end,"annual_return":ra,"monthly_return":rm,"skill":skill})
    shadow=pd.DataFrame(shadow)
    route=route_trace(cal.signal_date,shadow)
    route["w_monthly"]=route.p_monthly.astype(float)
    route["w_annual"]=1-route.w_monthly
    assert all(pd.isna(v) or pd.Timestamp(v)<pd.Timestamp(d) for v,d in zip(route.last_matured_outcome_end,route.signal_date))
    route.to_csv(OUT/"ROUTER_TRACE.csv",index=False)
    shadow.to_csv(OUT/"SHADOW_SKILL.csv",index=False)
    wm=route.w_monthly.to_numpy(float)[:,None];wa=1-wm;s50=.5*sA+.5*sM;sR=wa*sA+wm*sM;pm50={x:.5*pmA[x]+.5*pmM[x] for x in pmA};pmR={x:wa*pmA[x]+wm*pmM[x] for x in pmA}
    for name,s,pm in [("p42_50_50",s50,pm50),("p45",sR,pmR)]:
        m,E,T,ds=replay(s,pm,cal,cand_mats,ref_mats,target_tickers);results[name]=m;paths[name]=E;print(name,json.dumps(m),flush=True)
    C=cand_mats["Close"].reindex(ds).ffill().bfill();eq=(C/C.iloc[0]).mean(axis=1).to_numpy(float);results["equal_weight_buy_hold"]=metrics(eq);annual=[]
    for y in range(2017,2027):
        mask=(ds>=pd.Timestamp(f"{y}-01-01"))&(ds<pd.Timestamp(f"{y+1}-01-01"))
        if not mask.any():continue
        rec={"year":y,"sessions":int(mask.sum())}
        for name,E in paths.items():
            rr=pd.Series(E,index=ds).pct_change().fillna(pd.Series(E,index=ds).iloc[0]-1);r=rr[mask];rec[name+"_return"]=float(np.prod(1+r)-1)
        annual.append(rec)
    pd.DataFrame(annual).to_csv(OUT/"ANNUAL_COMPARISON.csv",index=False);pA.to_csv(OUT/"ANNUAL_PREDICTIONS_120.csv",index=False);pM.to_csv(OUT/"MONTHLY_PREDICTIONS_120.csv",index=False);np.savez_compressed(OUT/"PATHS_120.npz",dates=ds.values,**paths)
    manifest={"status":"P45_EU120_RETRAIN_COMPLETE","training_universe_count":int(len(srcu)),"target_count":int(len(target)),"training_target_overlap":120,"target_labels_used_for_fit":True,"fit_scope":"120 ETF expanding walk-forward; only labels matured strictly before each fit cutoff","router":"P44 BOCPD constants, P45 continuous posterior, rebuilt from EU120 matured shadow intervals","source_repo":"AM1975MA/Etf_trader; AM1975MA/Trader_selector","target_universe_file":"UNIVERSE_120.csv","period":[str(ds.min().date()),str(ds.max().date())],"results":results};(OUT/"RESULT.json").write_text(json.dumps(manifest,indent=2)+"\n");files=[p for p in MODELS.rglob("*") if p.is_file()];(OUT/"MODEL_BUNDLE_MANIFEST.json").write_text(json.dumps({"model_files":len(files),"sha256":{str(p.relative_to(MODELS)):sha256(p) for p in files}},indent=2)+"\n");print("FINAL_RESULT",json.dumps(manifest,indent=2),flush=True)

if __name__=="__main__":main()
