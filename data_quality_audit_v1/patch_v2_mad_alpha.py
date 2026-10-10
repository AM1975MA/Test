"""Research-only shared source kernel transform, never modify production."""
import argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("path",type=Path);p.add_argument("--alpha",type=float,required=True);a=p.parse_args()
assert a.alpha in (0.05,1.0)
text=a.path.read_text()
old1="""def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return ret.where(ret<0).rolling(h,min_periods=max(10,h//2)).std(ddof=0)*np.sqrt(252)"""
new1="""def rolling_downvol(ret:pd.DataFrame,h:int)->pd.DataFrame:
    return np.sqrt(ret.clip(upper=0).pow(2).rolling(h,min_periods=h).mean()*252.0)"""
old2="""def cs_robust_dev(df:pd.DataFrame)->pd.DataFrame:
    med=df.median(axis=1)
    mad=df.sub(med,axis=0).abs().median(axis=1).replace(0,np.nan)
    return df.sub(med,axis=0).div(1.4826*mad,axis=0).clip(-8,8)"""
new2=f"""def cs_robust_dev(df:pd.DataFrame)->pd.DataFrame:
    med=df.median(axis=1)
    numerator=df.sub(med,axis=0)
    mad=numerator.abs().median(axis=1)
    std=df.std(axis=1,ddof=0)
    scale=np.maximum(1.4826*mad,{a.alpha}*std)
    result=numerator.div(scale.replace(0,np.nan),axis=0).clip(-8,8)
    # Only proven all-tied columns have meaningful centered deviation zero.
    fully_tied=scale.eq(0)&std.eq(0)
    if fully_tied.any():
        result.loc[fully_tied]=numerator.loc[fully_tied].where(numerator.loc[fully_tied].isna(),0.0)
    return result"""
assert text.count(old1)==1 and text.count(old2)==1,"Canonical source signature drift"
a.path.write_text(text.replace(old1,new1).replace(old2,new2))
print("APPLIED_RESEARCH_GLOBAL_DOWNVOL_AND_MAD_ALPHA",a.alpha,hashlib.sha256(a.path.read_bytes()).hexdigest())
