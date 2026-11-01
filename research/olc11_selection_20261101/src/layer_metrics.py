"""Task-native diagnostics. No compounded returns, cost model or portfolio controls."""
from __future__ import annotations
import numpy as np
from scipy.stats import rankdata

def hybrid_target(r21,r42,r63):
    return .45*np.asarray(r21,float)**1.5+.35*np.asarray(r42,float)**1.5+.20*np.asarray(r63,float)**1.5

def economic_relevance(returns):
    r=np.asarray(returns,float)
    if not np.isfinite(r).all():raise ValueError('Economic relevance requires mature finite outcomes')
    spread=max(float(np.quantile(r,.90)-np.quantile(r,.10)),1e-6)
    return np.rint(7.5+7.5*np.clip((r-np.median(r))/spread,-1.,1.))

def topk_weights(scores,k=2):
    """Expected membership under uniform resolution of ties; no outcome tie-break."""
    p=np.asarray(scores,float)
    if p.ndim!=1 or not np.isfinite(p).all() or not 1<=k<=len(p):raise ValueError('Invalid scores or k')
    threshold=np.sort(p)[-k];above=p>threshold;equal=p==threshold
    w=above.astype(float);w[equal]=(k-above.sum())/equal.sum()
    return w/k

def ndcg(relevance,scores,k=2):
    y=np.asarray(relevance,float);p=np.asarray(scores,float)
    if y.shape!=p.shape or y.ndim!=1 or not np.isfinite(y).all() or not np.isfinite(p).all() or (y<0).any():raise ValueError('Invalid NDCG inputs')
    k=min(k,len(y));discount=1/np.log2(np.arange(k)+2.)
    ideal=float(np.dot(np.sort(y)[::-1][:k],discount))
    if ideal<=0:return float('nan')
    order=np.argsort(-p,kind='stable');s=p[order];r=y[order];result=0.;start=0
    while start<k:
        end=start+1
        while end<len(s) and s[end]==s[start]:end+=1
        result+=float(r[start:end].mean()*discount[start:min(end,k)].sum());start=end
    return result/ideal

def rank_ic(y,p):
    a=rankdata(y);b=rankdata(p)
    if np.std(a)==0 or np.std(b)==0:return float('nan')
    return float(np.corrcoef(a,b)[0,1])

def ranking_metrics(y,p):
    y=np.asarray(y,float);p=np.asarray(p,float);w=topk_weights(p,2);n=len(y)
    expected_rank=rankdata(y,method='average')/n
    best=np.sort(y)[-2:].mean();selected=float(np.dot(w,y))
    return {'ndcg2':ndcg(y,p,2),'ndcg5':ndcg(y,p,5),'ic':rank_ic(y,p),
       'selected_target':selected,'target_regret':float(best-selected),
       'target_top_quintile_precision':float(np.dot(w,expected_rank>.8)),
       'target_bottom_quintile_fraction':float(np.dot(w,expected_rank<=.2))}

def opportunity_metrics(returns,scores):
    r=np.asarray(returns,float);w=topk_weights(scores,2);n=len(r)
    return {'top2_return':float(np.dot(w,r)),
      'top2_excess':float(np.dot(w,r)-r.mean()),
      'top2_regret':float(np.sort(r)[-2:].mean()-np.dot(w,r)),
      'selected_negative_return':float(np.dot(w,r<0)),
      'bottom_quintile_fraction':float(np.dot(w,rankdata(r)/n<=.2)),
      'top5_capture':float(np.dot(w,rankdata(r)>n-5))}

def compose(return_rank,et_rank,xgb_rank):
    r=np.asarray(return_rank,float);e=np.asarray(et_rank,float);x=np.asarray(xgb_rank,float)
    if r.ndim!=2 or r.shape!=e.shape or r.shape!=x.shape or len(r)==0:raise ValueError('Aligned monthly matrices required')
    current=.6*e+.4*x
    lag1=current[np.maximum(np.arange(len(current))-1,0)]
    lag2=current[np.maximum(np.arange(len(current))-2,0)]
    vals=np.stack([current,lag1,lag2]);weights=np.array([.4,.3,.3])[:,None,None]
    ok=np.isfinite(vals);den=(weights*ok).sum(0)
    average=np.divide((np.where(ok,vals,0.)*weights).sum(0),den,out=np.full_like(current,np.nan),where=den>0)
    average=np.where(ok.all(0),.4*current+.3*lag1+.3*lag2,average)
    smooth=np.where(np.isfinite(current),np.clip(average,0,1)**1.1,np.nan)
    return current,smooth,.475*r+.525*smooth

def paired_month_matrix(series):
    import pandas as pd
    normalized={}
    for name,s in series.items():
        x=s.copy();x.index=pd.to_datetime(x.index).to_period('M')
        if x.index.duplicated().any():raise ValueError('More than one observation in a calendar month')
        normalized[name]=x
    return pd.concat(normalized,axis=1).dropna()
