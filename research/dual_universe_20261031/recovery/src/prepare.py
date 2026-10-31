"""Restore frozen inputs and common corrected features; no online market fetch."""
from pathlib import Path
import os,sys,io,json,zipfile,pickle,inspect,hashlib,time,warnings
import numpy as np,pandas as pd
from common import atomic_bytes,atomic_json,digest,eligibility,forward_labels
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'code'))
import frozen_kernel as k
EXPECTED_KERNEL='3e024b3cf169f19ed30747cb8c41d4078d8eee6107455c860668d4bd7180a65a'
assert digest(Path(k.__file__).read_bytes())==EXPECTED_KERNEL
# Reuse exactly the compact125 section; omit unused, expensive legacy Tail calculations.
source=inspect.getsource(k.build_features).split('\n    D={}')[0]
assert source.count("mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)")==1
source=source.replace("mkt=ret['SPY'] if 'SPY' in ret else ret.median(axis=1)",'mkt=ret.median(axis=1)')
source+='\n    return dates,compact_long\n'
ns=dict(k.__dict__);exec(compile(source,'<corrected125-common-market>','exec'),ns)
features=ns['build_features']

FIELDS=['Open','High','Low','Close','Volume']

def load_market(market:str):
    if market=='USA':
        archive=Path('/mnt/data/yfinance-repeatability-v1-raw.zip');z=zipfile.ZipFile(archive)
        u=pd.read_csv(io.BytesIO(z.read('_repeat1/universe.csv')));tickers=u.ticker.astype(str).tolist()
        names={t:f'_repeat1/{t}.csv' for t in tickers}
    else:
        archive=ROOT.parent/'inputs/ETF_TRADER_V5_GERARCHICA_EU165_20261031.zip';z=zipfile.ZipFile(archive)
        prefix='source_v4/input/EU165_SPECIALISTS_20261029/'
        u=pd.read_csv(io.BytesIO(z.read(prefix+'input/universe.csv')));tickers=u.ticker.astype(str).tolist()
        names={t:prefix+'prices/'+t+'.csv' for t in tickers}
    assert len(tickers)==(149 if market=='USA' else 165) and len(set(tickers))==len(tickers)
    frames={};hashes={}
    for t,n in names.items():
        raw=z.read(n);hashes[t]=digest(raw)
        f=pd.read_csv(io.BytesIO(raw),index_col=0,parse_dates=True,float_precision='round_trip').sort_index()
        f.index=f.index.tz_localize(None);f=f.loc[:'2026-07-01']
        assert f.index.is_unique and f.index.is_monotonic_increasing,t
        frames[t]=f
    mats={fld:pd.concat({t:f[fld] for t,f in frames.items()},axis=1).sort_index().reindex(columns=tickers) for fld in FIELDS}
    return mats,{'archive':str(archive),'sha256':digest(archive.read_bytes()),'ticker_sha256':hashes,'tickers':tickers}

def build(market:str):
    t0=time.time();m,manifest=load_market(market)
    elig=eligibility(m['Close'],m['Volume'])
    fm={fld:(f.ffill(limit=3) if fld!='Volume' else f) for fld,f in m.items()}
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');dates,p=features(fm)
    # Do not turn a partial final month into an investible event. Entry must exist.
    labels=forward_labels(m['Open'],dates)
    p=p.merge(labels,on=['signal_date','ticker'],how='inner',validate='one_to_one')
    p=p.merge(elig.stack(dropna=False).rename('eligible').rename_axis(['signal_date','ticker']).reset_index(),on=['signal_date','ticker'],validate='one_to_one')
    p=p.sort_values(['signal_date','ticker']).reset_index(drop=True)
    p[k.F2D_FEATURES]=p[k.F2D_FEATURES].replace([np.inf,-np.inf],np.nan)
    # Target ranks among historically eligible names, not all future survivors.
    for h in [21,42,63]:
        p[f'target_rank_{h}']=p[f'fwd_ret_{h}'].where(p.eligible).groupby(p.signal_date).rank(pct=True)
    c=fm['Close'];ret=c.pct_change(fill_method=None);market_ret=ret.median(axis=1).fillna(0)
    index=(1+market_ret).cumprod();regime=index>=index.rolling(200,min_periods=200).mean()
    vol=np.log(c).diff().rolling(63,min_periods=63).std(ddof=0)*np.sqrt(252)
    beta=ret.rolling(126,min_periods=126).cov(market_ret).div(market_ret.rolling(126,min_periods=126).var(),axis=0).shift(1)
    residual=(ret-beta.mul(market_ret,axis=0)).rolling(63,min_periods=63).sum().div(vol)
    sample_date=pd.Timestamp('2018-12-31')
    cutoff=m['Close'].index[m['Close'].index<=sample_date][-1]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore');d2,p2=features({fld:f.loc[:cutoff] for fld,f in fm.items()})
    full=p[p.signal_date<=cutoff].set_index(['signal_date','ticker'])[k.F2D_FEATURES]
    past=p2.set_index(['signal_date','ticker'])[k.F2D_FEATURES]
    keys=full.index.intersection(past.index)
    # At least one complete previous year, all feature values and missingness.
    keys=keys[keys.get_level_values(0)>=pd.Timestamp('2017-01-01')]
    np.testing.assert_allclose(full.loc[keys].to_numpy(),past.loc[keys].to_numpy(),atol=1e-12,rtol=0,equal_nan=True)
    out=ROOT/'prepared';out.mkdir(exist_ok=True)
    atomic_bytes(out/f'{market}_panel.pkl',pickle.dumps(p,protocol=5))
    atomic_bytes(out/f'{market}_market.pkl',pickle.dumps({'mats':m,'regime':regime,'vol':vol,'residual':residual,'market_index':index},protocol=5))
    atomic_json(out/f'{market}_INPUTS.json',manifest)
    check={'market':market,'tickers':len(manifest['tickers']),'rows':len(p),'eligible_rows':int(p.eligible.sum()),'dates':int(p.signal_date.nunique()),'first':str(m['Close'].index.min().date()),'last':str(m['Close'].index.max().date()),'prefix_rows_checked':len(keys),'prefix_pass':True,'kernel_sha256':EXPECTED_KERNEL,'panel_sha256':digest((out/f'{market}_panel.pkl').read_bytes()),'seconds':time.time()-t0,'recovery_note':'Reconstructed from frozen written protocol; original working scripts and predictions were not recovered.'}
    atomic_json(out/f'{market}_PREP_CHECK.json',check);print(json.dumps(check),flush=True)
if __name__=='__main__':
    for market in sys.argv[1:] or ['USA','EU']:build(market)
