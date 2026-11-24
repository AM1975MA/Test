"""Generate minimally edited, reviewable source from the frozen U19 cash engine."""
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OLD=ROOT.parent/'perseo_u19_work'
import sys
sys.path.insert(0,str(OLD))
from cash_execution19 import cash_engine

def engine():
 cash_engine()
 code=(OLD/'common_cash_engine.py').read_text()
 def change(a,b):
  nonlocal code
  assert code.count(a)==1,(a,code.count(a));code=code.replace(a,b)
 change('next_observed: bool=True, friction: float|None=None)', 'next_observed: bool=True, friction: float|None=None, stop_fraction: float=.055)')
 change('barrier=previous_close*(1-.055)', 'barrier=previous_close*(1-stop_fraction)')
 change('reentry_count=0;alarm_count=0', 'reentry_count=0;alarm_count=0\n        mode=int(q.get("risk_mode",np.zeros(D,int))[k])')
 change('locked=lock_until>=k', 'locked=lock_until>=k\n        if mode in (3,4):locked |= pending_reentry & ~q["rebound"][k]')
 change('if not(fast_stop and risk_on):continue', 'if not(fast_stop and risk_on) or mode==5:continue\n            threshold=float(q["stop_threshold"][k,t]) if mode in (2,4) else .055')
 change('observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),friction=stop_friction)', 'observed=bool(obs[k,t]),low_observed=bool(lobs[k,t]),friction=stop_friction,stop_fraction=threshold)')
 change('free+=qty*fill-stop_cost;units[t]=0.;cd=max(cd,3)', 'free+=qty*fill-stop_cost;units[t]=0.\n            if mode==0:cd=max(cd,3)')
 change('lock_until[t]=max(lock_until[t],k+lock_days);pending_reentry[t]=True', 'lock_until[t]=max(lock_until[t],k+(1 if mode in (3,4) else lock_days));pending_reentry[t]=True')
 change('quantity=qty,carried_quantity=', 'threshold=threshold,quantity=qty,carried_quantity=')
 change('fill_price=fill,barrier=float(PC[k,t]*.945)', 'fill_price=fill,barrier=float(PC[k,t]*(1-threshold))')
 (ROOT/'frozen_engine20.py').write_text(code)
 ns={};exec(compile(code,str(ROOT/'frozen_engine20.py'),'exec'),ns);return ns['simulate']
