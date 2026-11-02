"""Independent product-based tail and drawdown-duration metric checks."""
import json,itertools
import numpy as np,pandas as pd
from combined_engine import ROOT

def main():
    score=pd.read_csv(ROOT/'results/SCORECARD.csv');n=0;err=0.
    for key,rows in score.groupby('key'):
        p=np.load(ROOT/f'results/paths/{key}.npz');dates=pd.to_datetime(p['dates'][1:])
        rr=pd.Series(p['nav'][:-1]/p['ledger'][:-1,0]-1,index=dates)
        for z in rows.to_dict('records'):
            r=rr.loc[z['first_valuation']:z['last_valuation']]
            wealth=np.r_[1.,(1+r).cumprod().to_numpy()];peak=pd.Series(wealth).cummax().to_numpy()
            under=wealth/peak<1-1e-12
            duration=max((sum(1 for _ in group) for k,group in itertools.groupby(under) if k),default=0)
            values=dict(worst_day=r.min(),cvar05=r.nsmallest(max(1,int(np.ceil(.05*len(r))))).mean(),
                worst5=(1+r).rolling(5).apply(np.prod,raw=True).min()-1,
                worst21=(1+r).rolling(21).apply(np.prod,raw=True).min()-1,
                max_underwater_sessions=duration,end_underwater=wealth[-1]/peak[-1]-1)
            for k,value in values.items():
                if pd.isna(value) and pd.isna(z[k]):continue
                e=abs(value-z[k]);assert e<5e-11,(key,z['period'],k,e)
                n+=1;err=max(err,e)
    result=dict(additional_risk_values_checked=n,maximum_error=err)
    (ROOT/'results/EXTRA_RISK_VERIFICATION.json').write_text(json.dumps(result,indent=2));print(result)
if __name__=='__main__':main()
