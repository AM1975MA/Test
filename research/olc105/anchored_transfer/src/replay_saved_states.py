"""Repeat all 118 declared accounts from frozen states, without model archives.
Invoke from any directory: python src/replay_saved_states.py --out /new/empty/path
Expected inputs are data/*_STATE.npz, results/TRANSFER_DAILY.csv.gz and ten
reference *_PATH.npz. This is numerical reproducibility, not broker validation.
"""
from pathlib import Path
import argparse,json,itertools
import numpy as np,pandas as pd
import native_broker_engine as eng
ROOT=Path(__file__).resolve().parents[1]

def run(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    daily=pd.read_csv(ROOT/'results/TRANSFER_DAILY.csv.gz',parse_dates=['date'])
    count=0;full=0;diff=0.;rows=[]
    cases=[(10000.,None,None,'GROSS'),(10000.,None,None,'LEGACY')]+[(c,t,b,'BROKER') for c in [5000.,10000.,50000.] for t in [1.,2.] for b in [5.,15.,30.]]
    for state in sorted((ROOT/'data').glob('*_STATE.npz')):
        arm=state.stem.removesuffix('_STATE')
        if arm=='TRANSFER':continue
        with np.load(state,allow_pickle=False) as z:q={k:z[k].copy() for k in z.files}
        ev=q.pop('events');ml=arm.startswith('TRANSFER_');policy='DELAY' if arm.endswith('DELAY3') else 'IMMEDIATE'
        for initial,ticket,bps,mode in cases:
            if mode=='LEGACY' and not ml:continue
            broker=None if mode!='BROKER' else {'initial':initial,'ticket':ticket,'impact':bps/10000}
            kwargs=dict(policy=policy,fraction=3 if policy=='DELAY' else 1,fee=.001 if mode=='LEGACY' else 0.,exposure_timing='PREVIOUS' if ml else 'OFF',stop_timing='NOW' if ml else 'OFF',stop_friction=.001 if mode=='LEGACY' else 0.,ordinary_alarm=False,fast_stop=ml,lock_days=3,risk_on=ml,broker=broker)
            r=eng.simulate(q,ev,**kwargs)
            sel=(daily.arm==arm)&(daily['mode']==mode)&(daily.initial_eur==initial)
            if mode=='BROKER':sel&=daily.ticket_fee_eur.eq(ticket)&daily.shortfall_bps_per_side.eq(bps)
            ref=daily[sel].sort_values('date');assert len(ref)==len(r['nav'])
            error=float(np.max(abs(ref.nav_open.to_numpy()-r['ledger'][:,0])));assert error<2e-12,(arm,error);diff=max(diff,error);count+=1
            tag='LEGACY' if mode=='LEGACY' else ('BROKER' if mode=='BROKER' and initial==10000 and ticket==1 and bps==15 else None)
            if tag:
                a=np.load(ROOT/f'results/{arm}_{tag}_PATH.npz');assert set(a.files)==set(r)
                for k in a.files:assert np.array_equal(a[k],r[k]),(arm,k,'NOT_BITWISE')
                full+=len(a.files)
            rows.append(dict(arm=arm,mode=mode,initial=initial,ticket=ticket,bps=bps,max_abs_nav_error=error))
    result={'status':'PASS_ISOLATED_ACCOUNT_REPLAY','replays':count,'reference_full_arrays_bitwise':full,'max_csv_roundtrip_nav_difference':diff,'trained_models_needed':False,'broker_fill_certified':False,'prospective':False}
    pd.DataFrame(rows).to_csv(out/'REPLAY_RECONCILIATION.csv',index=False);(out/'ISOLATED_QA.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--out',required=True);run(a.parse_args().out)
