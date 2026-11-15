from settings import *
import pandas as pd,numpy as np,json,hashlib
from functools import lru_cache
from corporate_actions import forward_units
import portability_controls as pc
FIELDS=['Open','High','Low','Close','Volume']
@lru_cache(maxsize=1)
def candidate_data():
    frames,qa,checks=pc.load_frozen();out={}
    for name,f in frames.items():
        ratio=f['Adj Close']/f.Close
        g=f[FIELDS].copy()
        for col in FIELDS[:4]:g[col]=g[col]*ratio
        if name=='IE00B3YCGJ38':
            # Official Invesco notice 30 Oct 2025: 100-to-1, ex 15 Dec 2025.
            # Frozen Yahoo data has neither adjustment nor split action.
            before=g.loc[:'2025-12-12','Close'].iloc[-1];after=g.loc['2025-12-15','Close']
            assert .008<after/before<.012, 'Do not double-adjust an already repaired source'
            g=forward_units(g,'2025-12-15',100.)
        # Positive/finite OHLC is required by the source formulas; geometry flags do NOT veto fills.
        mask=np.isfinite(g[FIELDS[:4]]).all(axis=1)&(g[FIELDS[:4]]>0).all(axis=1)
        out[name]=g[mask].copy()
    qa.to_csv(ROOT/'results/CANDIDATE_SOURCE_QA.csv',index=False)
    (ROOT/'results/CANDIDATE_HASH_QA.json').write_text(json.dumps({'status':'PASS','verified':len(checks),'candidates':len(out),'source':'frozen OLC105 captures; no redownload'},indent=2))
    # Recompute the simple benchmark signals on the SAME corrected economic series.
    for i,g in out.items():
        frames[i].loc[g.index,'adjusted_open']=g.Open
        frames[i].loc[g.index,'adjusted_close']=g.Close
    _,events,eligible=pc.signals(frames,pd.read_csv(CONTROL/'CANDIDATES_FROZEN.csv'))
    events.to_csv(ROOT/'results/MOMENTUM_SIGNALS_CORRECTED.csv',index=False)
    eligible.to_csv(ROOT/'results/ASOF_ELIGIBILITY_CORRECTED.csv',index=False)
    return out,qa
@lru_cache(maxsize=1)
def anchored_data():
    folder=BASE/'source/raw/inputs/eu/source_v4/input/EU165_SPECIALISTS_20261029'
    u=pd.read_csv(folder/'input/universe.csv');frames={}
    for t in u.ticker:
        f=pd.read_csv(folder/'prices'/f'{t}.csv',index_col=0,parse_dates=True,float_precision='round_trip').sort_index().loc[:'2026-07-01',FIELDS]
        f=f[np.isfinite(f[FIELDS[:4]]).all(axis=1)&(f[FIELDS[:4]]>0).all(axis=1)]
        p=APPEND/'quotes'/f'EU_{t}.csv'
        a=pd.read_csv(p,index_col='date',parse_dates=True,float_precision='round_trip')
        a=a[['adj_open','adj_high','adj_low','adj_close','Volume']].rename(columns=dict(zip(['adj_open','adj_high','adj_low','adj_close'],FIELDS[:4])))
        assert a.index.min()>f.index.max()
        frames[t]=pd.concat([f,a]).sort_index();assert frames[t].index.is_unique
    candidates,qa=candidate_data();frames.update(candidates)
    roster=pd.read_csv(CONTROL/'CANDIDATES_FROZEN.csv')
    c=roster[roster['isin'].isin(candidates)].rename(columns={'isin':'ticker'})[['ticker','macro_category']]
    return frames,pd.concat([u,c],ignore_index=True)
def benchmark():
    f,_=anchored_data();return f['EXSA.DE'].Close

