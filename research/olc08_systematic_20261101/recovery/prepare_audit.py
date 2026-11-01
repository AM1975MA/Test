"""Reconstruct variant inputs, inventory every input and save a completed panel stage."""
from context import ROOT,CAL,P0,kernel,FEATURES_42
from recovery_core import *
from calendar_rebuild import raw_frames
import itertools,warnings
warnings.filterwarnings('ignore',category=FutureWarning)
OUT=ROOT/'results';IN=ROOT/'inputs';stats=[];annual=[];changes=[];duplicates={}
for market in ['EU','USA']:
    cp=pd.read_pickle(CAL/f'{market}_COMPACT.pkl');hp=pd.read_pickle(CAL/f'{market}_HYBRID.pkl')
    frames,_=raw_frames(market);patch=cp[['signal_date','ticker','source_date']].copy()
    patch['rsi14_new']=np.nan
    for h in [21,63,126]:patch[f'downvol{h}_new']=np.nan
    for ticker,ids in patch.groupby('ticker').groups.items():
        close=frames[ticker][['Close']];dates=pd.DatetimeIndex(patch.loc[ids,'source_date'])
        patch.loc[ids,'rsi14_new']=rsi_domain(close).Close.reindex(dates).to_numpy()
        lr=np.log(close).diff()
        for h in [21,63,126]:patch.loc[ids,f'downvol{h}_new']=lower_partial_rms(lr,h).Close.reindex(dates).to_numpy()
    old=cp.rsi14.to_numpy();new=patch.rsi14_new.to_numpy();same=(old==new)|(np.isnan(old)&np.isnan(new))
    assert np.array_equal(old[np.isfinite(old)],new[np.isfinite(old)])
    for i in np.flatnonzero(~same):
        changes.append({'market':market,'signal_date':str(cp.signal_date.iloc[i].date()),'ticker':cp.ticker.iloc[i],'old':None if np.isnan(old[i]) else old[i],'new':None if np.isnan(new[i]) else new[i],'eligible':bool(cp.eligible.iloc[i])})
    for name in ['rsi14']+[f'downvol{h}' for h in [21,63,126]]:
        patch[name]=patch[name+'_new'];patch[name+'_pct']=patch.groupby('signal_date')[name].rank(pct=True)
        if name+'_dev' in kernel.F2D_FEATURES:
            w=patch.pivot(index='signal_date',columns='ticker',values=name)
            z=kernel.cs_robust_dev(w).stack(dropna=False).rename(name+'_dev').reset_index()
            patch=patch.merge(z,on=['signal_date','ticker'],validate='one_to_one',sort=False)
    patch.to_pickle(IN/f'{market}_PATCH.pkl')
    ds=[]
    for cols,frame,block in [(kernel.F2D_FEATURES,cp.loc[cp.eligible],'RETURN'),(list(FEATURES_42),hp,'HYBRID')]:
        for a,b in itertools.combinations(cols,2):
            if frame[a].equals(frame[b]):ds.append({'block':block,'first':a,'duplicate':b})
        for col in cols:
            a=frame[col];valid=a.dropna()
            stats.append({'market':market,'block':block,'feature':col,'rows':len(a),'missing':int(a.isna().sum()),'missing_fraction':float(a.isna().mean()),'unique_finite':int(valid.nunique()),'minimum':float(valid.min()) if len(valid) else None,'maximum':float(valid.max()) if len(valid) else None,'median':float(valid.median()) if len(valid) else None})
            for year,g in frame.groupby(frame.signal_date.dt.year):
                annual.append({'market':market,'block':block,'feature':col,'year':int(year),'rows':len(g),'missing':int(g[col].isna().sum())})
    duplicates[market]=ds
    print('AUDITED',market,'changed RSI rows',int((~same).sum()),'eligible',int(((~same)&cp.eligible.to_numpy()).sum()),'exact duplicate pairs',len(ds),flush=True)
shared=[x for x in duplicates['EU'] if x in duplicates['USA']]
keep=[]
for col in FEATURES_42:
    if not any(x['block']=='HYBRID' and x['first'] in keep and x['duplicate']==col for x in shared):keep.append(col)
atomic_json(OUT/'DUPLICATES.json',{'per_market':duplicates,'both_markets':shared,'hybrid_original_count':len(FEATURES_42),'hybrid_unique_count':len(keep),'hybrid_unique_columns':keep})
pd.DataFrame(stats).to_csv(OUT/'FEATURE_AUDIT.csv',index=False)
pd.DataFrame(annual).to_csv(OUT/'FEATURE_AUDIT_BY_YEAR.csv',index=False)
pd.DataFrame(changes,columns=['market','signal_date','ticker','old','new','eligible']).to_csv(OUT/'RSI_CHANGED_OBSERVATIONS.csv',index=False)
atomic_json(OUT/'PREPARATION_SUMMARY.json',{'feature_rows':len(stats),'inputs_per_market':len(kernel.F2D_FEATURES)+len(FEATURES_42),'RSI_changes':changes,'hybrid_unique_count':len(keep),'warning':'Coverage and exact duplicates, not full predictive validation of167 independent variables.'})
files=[str(p.relative_to(ROOT)) for p in CAL.iterdir() if p.is_file() and (p.suffix=='.pkl' or p.name.endswith('AUDIT.json') or p.name.endswith('FORECASTS.csv.gz') or p.name.endswith('CALENDAR.csv'))]+[str(p.relative_to(ROOT)) for p in IN.glob('*PATCH.pkl')]
key=sha256(ROOT/'inputs/SOURCE_ARCHIVES.json')
complete_checkpoint(ROOT,key,files,{'stage':'reconstructed_and_audited_panels','source_manifest_sha256':key})
print('PANEL_CHECKPOINT_VERIFIED',valid_checkpoint(ROOT,key),flush=True)
