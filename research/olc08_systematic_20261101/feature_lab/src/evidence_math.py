"""Small independent evidence computations; sampled frequency is not posterior probability."""
import numpy as np

def circular_weights(n:int,block:int,reps:int,seed:int):
    if min(n,block,reps)<1:raise ValueError('Positive dimensions required')
    rng=np.random.default_rng(seed)
    starts=rng.integers(0,n,size=(reps,(n+block-1)//block))
    indices=((starts[:,:,None]+np.arange(block))%n).reshape(reps,-1)[:,:n]
    weights=np.zeros((reps,n))
    np.add.at(weights,(np.repeat(np.arange(reps),n),indices.ravel()),1/n)
    return weights

def score_month(frame,score:str,outcome:str,k:int=2):
    good=frame[[score,outcome]].dropna()
    if len(good)<k:return {'n':len(good),'rank_ic':np.nan,'top2_return':np.nan,'top2_excess':np.nan,'top5_overlap':np.nan}
    # Stable tied-score evaluation; model scores are not probabilities.
    pred=good.sort_values(score,ascending=False,kind='stable')
    top=pred[outcome].iloc[:k].mean();r=good[score].rank();y=good[outcome].rank()
    ic=float(r.corr(y)) if r.nunique()>1 and y.nunique()>1 else np.nan
    kk=min(5,len(good));actual=good.nlargest(kk,outcome).index
    overlap=len(set(pred.index[:kk])&set(actual))/kk
    return dict(n=len(good),rank_ic=ic,top2_return=float(top),top2_excess=float(top-good[outcome].mean()),top5_overlap=overlap)

def daily_log(nav):
    a=np.asarray(nav,float)
    if a.ndim!=1 or np.any(~np.isfinite(a)) or np.any(a<=0):raise ValueError('Positive finite NAV required')
    return np.diff(np.log(np.r_[1.,a]))
