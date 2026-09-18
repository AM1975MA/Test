"""Causal features. No scaler fitted here; all rolling windows end at t."""
import numpy as np
import pandas as pd
GROUPS={'session':['overnight21','intraday21','overnight63','intraday63','gap_share63','gap_reversal63'],
        'residual':['resid21','resid63','peer21','peer63','down_beta126','corr_stress63'],
        'flow':['signed_flow21','signed_flow63','range_position21','impact_change','volume_price_corr63','volume_trend63']}

def build(mats, categories, dates):
    O,H,L,C,V=[mats[k] for k in ['Open','High','Low','Close','Volume']]
    lr=np.log(C).diff(); m=lr['SPY']; var=m.rolling(126,min_periods=100).var()
    beta=lr.rolling(126,min_periods=100).cov(m).div(var,axis=0).shift(1)
    resid=lr-beta.mul(m,axis=0)
    peer=pd.DataFrame(index=C.index,columns=C.columns,dtype=float)
    for cat in sorted(set(categories.values())):
        ts=[t for t in C if categories[t]==cat]
        sums=lr[ts].sum(axis=1,min_count=1); count=lr[ts].count(axis=1)
        for t in ts: peer[t]=(sums-lr[t])/(count-lr[t].notna()).replace(0,np.nan)
    overnight=np.log(O/C.shift(1)); intraday=np.log(C/O)
    d={}
    for h in [21,63]:
        d[f'overnight{h}']=overnight.rolling(h,min_periods=h).sum()
        d[f'intraday{h}']=intraday.rolling(h,min_periods=h).sum()
        d[f'resid{h}']=resid.rolling(h,min_periods=h).sum()
        d[f'peer{h}']=(lr-peer).rolling(h,min_periods=h).sum()
        d[f'signed_flow{h}']=(np.sign(lr)*V).rolling(h,min_periods=h).sum()/V.rolling(h,min_periods=h).sum().replace(0,np.nan)
    d['gap_share63']=overnight.rolling(63).var()/(overnight.rolling(63).var()+intraday.rolling(63).var()).replace(0,np.nan)
    d['gap_reversal63']=overnight.rolling(63).corr(intraday)
    down=m.clip(upper=0); d['down_beta126']=lr.rolling(126,min_periods=100).cov(down).div(down.rolling(126,min_periods=100).var(),axis=0)
    d['corr_stress63']=lr.clip(upper=0).rolling(63).corr(down)
    d['range_position21']=((2*C-H-L)/(H-L).replace(0,np.nan)).rolling(21).mean()
    impact=lr.abs()/(C*V).replace(0,np.nan)
    d['impact_change']=np.log(impact.rolling(21).mean()/impact.rolling(126).mean())
    d['volume_price_corr63']=lr.rolling(63).corr(np.log(V.where(V>0)).diff())
    d['volume_trend63']=np.log(V.rolling(21).mean()/V.rolling(63).mean())
    blocks=[]
    for n,v in d.items():
        v=v.replace([np.inf,-np.inf],np.nan).reindex(dates)
        # Cross-sectional ranks at the same observation time are causal.
        blocks.append(v.rank(axis=1,pct=True).stack(dropna=False).rename(n))
    out=pd.concat(blocks,axis=1).reset_index(); out.columns=['signal_date','ticker',*d]
    return out
