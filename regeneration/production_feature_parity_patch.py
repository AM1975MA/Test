from __future__ import annotations
import argparse
from pathlib import Path


def replace_once(s: str, old: str, new: str, label: str) -> str:
    n=s.count(old)
    if n != 1:
        raise RuntimeError(f'{label}: expected 1 exact match, got {n}')
    return s.replace(old,new,1)


def patch_base(path: Path):
    s=path.read_text()
    s=replace_once(s,
"""def cs_robust_dev(df:pd.DataFrame)->pd.DataFrame:\n    med=df.median(axis=1)\n    mad=df.sub(med,axis=0).abs().median(axis=1).replace(0,np.nan)\n    return df.sub(med,axis=0).div(1.4826*mad,axis=0).clip(-8,8)\n""",
"""def cs_robust_dev(df:pd.DataFrame)->pd.DataFrame:\n    med=df.median(axis=1,skipna=True)\n    q75=df.quantile(.75,axis=1)\n    q25=df.quantile(.25,axis=1)\n    scale=(q75-q25).replace(0,np.nan)\n    return df.sub(med,axis=0).div(scale,axis=0).clip(-8,8)\n""",'cs_robust_dev')
    s=replace_once(s,
"""def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    return ret.where(ret<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*np.sqrt(252)\n""",
"""def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    neg=ret.where(ret<0,0.0)\n    return np.sqrt(neg.pow(2).rolling(h,min_periods=h).mean()*252)\n""",'rolling_downvol')
    s=replace_once(s,
"""def rolling_rsi(c:pd.DataFrame,h:int=14)->pd.DataFrame:\n    d=c.diff(); up=d.clip(lower=0).ewm(alpha=1/h,adjust=False,min_periods=h).mean(); dn=(-d.clip(upper=0)).ewm(alpha=1/h,adjust=False,min_periods=h).mean()\n    rs=up/dn.replace(0,np.nan); return 100-100/(1+rs)\n""",
"""def rolling_rsi(c:pd.DataFrame,h:int=14)->pd.DataFrame:\n    d=c.diff(); up=d.clip(lower=0); dn=(-d.clip(upper=0))\n    au=up.rolling(h,min_periods=h).mean(); ad=dn.rolling(h,min_periods=h).mean()\n    rs=au/ad.replace(0,np.nan); return 100-100/(1+rs)\n""",'rolling_rsi')
    s=replace_once(s,
"""def rolling_cvar10(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    return ret.rolling(h,min_periods=h).apply(lambda x: np.nanmean(np.sort(x)[:max(1,int(math.ceil(.1*len(x))))]),raw=True)\n""",
"""def rolling_cvar10(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    def _cvar(x):\n        x=np.asarray(x,float); q=np.nanquantile(x,.10); y=x[x<=q]\n        return float(np.nanmean(y)) if len(y) else np.nan\n    return ret.rolling(h,min_periods=h).apply(_cvar,raw=True)\n""",'rolling_cvar10')
    s=replace_once(s,
"""def rolling_sign_entropy(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    p=(ret>0).rolling(h,min_periods=h).mean().clip(1e-9,1-1e-9)\n    return -(p*np.log(p)+(1-p)*np.log(1-p))\n""",
"""def rolling_sign_entropy(ret:pd.DataFrame,h:int)->pd.DataFrame:\n    p=(ret>0).rolling(h,min_periods=h).mean().clip(1e-9,1-1e-9)\n    return -(p*np.log(p)+(1-p)*np.log(1-p))/np.log(2)\n""",'rolling_sign_entropy')
    s=replace_once(s,"mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)","mkt=ret.mean(axis=1,skipna=True)",'market')
    s=s.replace("lr.rolling(h,min_periods=h).std(ddof=0)*np.sqrt(252)","lr.rolling(h,min_periods=h).std()*np.sqrt(252)")
    s=replace_once(s,
"gk=.5*np.log(H/L.replace(0,np.nan))**2-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan))**2\n    compact['gkvol21']=snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252),dates)",
"gk=(.5*np.log(H/L.replace(0,np.nan))**2-(2*np.log(2)-1)*np.log(C/O.replace(0,np.nan))**2).clip(lower=0)\n    compact['gkvol21']=snapshot(np.sqrt(gk.rolling(21,min_periods=21).mean()*252),dates)",'gk')
    s=replace_once(s,
"adv=(C*V).rolling(63,min_periods=42).mean()\n    compact['log_adv63']=snapshot(np.log(adv.where(adv>0)),dates)\n    lv=np.log(V.where(V>0)); compact['volume_surprise21']=snapshot((lv-lv.rolling(21,min_periods=15).mean())/lv.rolling(21,min_periods=15).std(ddof=0).replace(0,np.nan),dates)",
"dollar=V*C\n    compact['log_adv63']=snapshot(np.log1p(dollar.rolling(63,min_periods=63).mean()),dates)\n    lv=np.log1p(V); compact['volume_surprise21']=snapshot((lv-lv.rolling(21,min_periods=21).mean())/lv.rolling(21,min_periods=21).std().replace(0,np.nan),dates)",'adv-volume')
    old="""    for h in [21,42,63]:\n        vals=[]\n        for r in info.itertuples():\n            if pd.isna(getattr(r,f'exit_date_{h}')):continue\n            a=O.loc[r.entry_date];b=O.loc[getattr(r,f'exit_date_{h}')]\n            q=(b/a-1).rename('fwd').reset_index().rename(columns={'index':'ticker'});q['signal_date']=r.signal_date;vals.append(q)\n        tmp=pd.concat(vals,ignore_index=True) if vals else pd.DataFrame(columns=['ticker','fwd','signal_date'])\n        out=out.merge(tmp.rename(columns={'fwd':f'fwd_ret_{h}'}),on=['signal_date','ticker'],how='left')\n        out[f'target_rank_{h}']=out.groupby('signal_date')[f'fwd_ret_{h}'].rank(pct=True)\n    out['target_rank_pct']=out['target_rank_21']\n"""
    new="""    for h in [21,42,63]:\n        vals=[]\n        for r in info.itertuples():\n            if pd.isna(getattr(r,f'exit_date_{h}')):continue\n            a=O.loc[r.entry_date];b=O.loc[getattr(r,f'exit_date_{h}')]\n            q=(b/a-1).rename('fwd').reset_index().rename(columns={'index':'ticker'});q['signal_date']=r.signal_date;vals.append(q)\n        tmp=pd.concat(vals,ignore_index=True) if vals else pd.DataFrame(columns=['ticker','fwd','signal_date'])\n        out=out.merge(tmp.rename(columns={'fwd':f'fwd_ret_{h}'}),on=['signal_date','ticker'],how='left')\n        out[f'target_rank_{h}']=out.groupby('signal_date')[f'fwd_ret_{h}'].rank(pct=True)\n    vals=[]\n    for r in info.itertuples():\n        if pd.isna(r.exit_date): continue\n        a=O.loc[r.entry_date]; b=O.loc[r.exit_date]\n        q=(b/a-1).rename('fwd_ret_monthly').reset_index().rename(columns={'index':'ticker'}); q['signal_date']=r.signal_date; vals.append(q)\n    tmp=pd.concat(vals,ignore_index=True) if vals else pd.DataFrame(columns=['ticker','fwd_ret_monthly','signal_date'])\n    out=out.merge(tmp,on=['signal_date','ticker'],how='left')\n    out['target_rank_pct']=out.groupby('signal_date')['fwd_ret_monthly'].rank(pct=True)\n"""
    s=replace_once(s,old,new,'monthly-target')
    s=s.replace("(compact_labeled.exit_date_21<cutoff)","(compact_labeled.exit_date<cutoff)")
    path.write_text(s)


def patch_v6(path: Path):
    s=path.read_text()
    s=replace_once(s,"(compact.signal_date<cutoff)&(compact.exit_date_21<cutoff)&compact.target_rank_pct.notna()&cvalid", "(compact.signal_date<cutoff)&(compact.exit_date<cutoff)&compact.target_rank_pct.notna()&cvalid", 'v6 compact cutoff')
    s=s.replace("mtr=macro[(macro.signal_date<cutoff)&(macro.label_exit_date_63<cutoff)&macro.target_rank.notna()]", "mtr=macro[(macro.signal_date<cutoff-pd.Timedelta(days=70))&macro.target_rank.notna()]")
    path.write_text(s)


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--base',type=Path,required=True); ap.add_argument('--v6',type=Path,required=True); a=ap.parse_args(); patch_base(a.base); patch_v6(a.v6)

if __name__=='__main__': main()
