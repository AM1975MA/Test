"""As-of feature blocks and inspectable per-input census; no model fitting."""
from bootstrap import *
from feature_blocks import *
from calendar_rebuild import raw_frames
from pathlib import Path
import json,time,warnings
import pandas as pd,numpy as np
OUT=ROOT/'results';CACHE=ROOT/'inputs';OUT.mkdir(exist_ok=True);CACHE.mkdir(exist_ok=True)

def run():
    start=time.time();counts=[];checks=[];sourcechecks=[]
    for market in ['EU','USA']:
        cp=pd.read_pickle(CAL/f'{market}_COMPACT.pkl');hp=pd.read_pickle(CAL/f'{market}_HYBRID.pkl')
        patch=pd.read_pickle(PARENT/'inputs'/f'{market}_PATCH.pkl')
        assert cp[['signal_date','ticker']].equals(patch[['signal_date','ticker']])
        cp[['rsi14','rsi14_pct']]=patch[['rsi14','rsi14_pct']]
        frames,_=raw_frames(market)
        cr=cp[['signal_date','ticker','source_date']].copy();hr=hp[['signal_date','ticker','source_date']].copy()
        for col in PATH+SESSION:cr[col]=np.nan;hr[col]=np.nan
        for number,(ticker,frame) in enumerate(frames.items()):
            features=native_blocks(frame)
            ci=cr.index[cr.ticker.eq(ticker)];hi=hr.index[hr.ticker.eq(ticker)]
            cr.loc[ci,PATH+SESSION]=sample_native(features,cr.loc[ci,'source_date']).to_numpy()
            hr.loc[hi,PATH+SESSION]=sample_native(features,hr.loc[hi,'source_date']).to_numpy()
            if number in [0,12,50,100]:
                p=len(frame)*2//3
                before=native_blocks(frame.iloc[:p]);pd.testing.assert_frame_equal(before,features.iloc[:p])
                disturbed=frame.copy();disturbed.iloc[p:,disturbed.columns.get_indexer(['Open','Close'])]*=3
                pd.testing.assert_frame_equal(before,native_blocks(disturbed).iloc[:p])
                sourcechecks.append({'market':market,'ticker':ticker,'prefix_rows':p,'prefix_equality':True,'future_perturbation_equality':True})
        cr[LEADERSHIP]=leadership_block(cp)
        for block,frame,cols in [('RETURN',cp,list(kernel.F2D_FEATURES)),('HYBRID',hp,list(FEATURES_42)),('NEW_RETURN',cr,PATH+SESSION+LEADERSHIP)]:
            df=frame.loc[cp.eligible] if block in ['RETURN','NEW_RETURN'] else frame
            for name in cols:
                s=df[name];counts.append({'market':market,'block':block,'feature':name,'rows':len(s),'missing':int(s.isna().sum()),'missing_fraction':float(s.isna().mean()),'unique':int(s.nunique()),'min':float(s.min()) if s.notna().any() else None,'max':float(s.max()) if s.notna().any() else None})
        # The Hybrid learner retains its own peer universe; rank new measurements on exactly that panel.
        for c in PATH+SESSION:hr[c+'_pct']=hr.groupby('signal_date')[c].rank(pct=True)
        assert not cr.duplicated(['signal_date','ticker']).any()
        assert not hr.duplicated(['signal_date','ticker']).any()
        for f in [cr,hr]:assert (f.loc[f.source_date.notna(),'source_date']<=f.loc[f.source_date.notna(),'signal_date']).all()
        cr.to_pickle(CACHE/f'{market}_NEW_RETURN.pkl');hr.to_pickle(CACHE/f'{market}_NEW_HYBRID.pkl')
        cp.to_pickle(CACHE/f'{market}_RSI_COMPACT.pkl')
        for n,frame in [('RETURN',cr),('HYBRID',hr)]:checks.append({'market':market,'block':n,'rows':len(frame),'source_date_after_signal':0,'keys_sha256':__import__('hashlib').sha256(frame[['signal_date','ticker']].to_csv(index=False).encode()).hexdigest()})
        print('FEATURES_COMPLETE',market,len(cr),len(hr),'seconds',round(time.time()-start,1),flush=True)
    pd.DataFrame(counts).to_csv(OUT/'FEATURE_CATALOGUE.csv',index=False)
    pd.DataFrame(checks).to_csv(OUT/'FEATURE_PANEL_CHECKS.csv',index=False)
    atomic_json(OUT/'CAUSAL_FEATURE_CHECKS.json',{'real_prefix_checks':sourcechecks,'synthetic_suite':'logs/TEST_GREEN_NEW.txt','novel_measurements':18,'interpretation':'New transformations of existing prices and ranks, not external fundamental information.'})
    atomic_json(OUT/'FEATURE_BLOCKS.json',{'PATH':PATH,'SESSION':SESSION,'LEADERSHIP':LEADERSHIP})
    files=[str(p.relative_to(ROOT)) for p in CACHE.glob('*NEW*.pkl')]+[str(p.relative_to(ROOT)) for p in CACHE.glob('*RSI_COMPACT.pkl')]
    complete_checkpoint(ROOT/'checkpoints'/'01_features','features_v1',[],{}) if False else None
    atomic_json(ROOT/'checkpoints'/'01_features.json',{'stage':'features_generated','files':[{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':sha256(ROOT/n)} for n in files],'prefix_checks':len(sourcechecks),'old_inputs_per_market':167,'new_measurements':18})
if __name__=='__main__':run()
