"""Generate a minimally instrumented research copy; canonical source stays unchanged."""
from pathlib import Path
import inspect,hashlib
from engine_prepare import stage,B
s=inspect.getsource(stage.simulate_arch.py_func)
def change(old,new):
    global s
    if s.count(old)!=1:raise ValueError('Expected one source anchor: '+old)
    s=s.replace(old,new)
change('def simulate_arch(', 'def simulate_instrumented(')
change('cost=.001,stop=.055,slip=.001,','cost=.001,stop=.055,slip=.001, systemic_enabled=True, stops_enabled=True,')
change('E=np.ones((B,D)); T=np.zeros((B,D)); X=np.ones((B,D)); AW=np.zeros((B,D))',
       'E=np.ones((B,D)); T=np.zeros((B,D)); X=np.ones((B,D)); AW=np.zeros((B,D))\n    ledger=np.zeros((B,D,24))')
change('if k==D-1:\n                E[bb,k]=val;', 'ledger[bb,k,0]=val\n            if k==D-1:\n                E[bb,k]=val;')
change('sysm=((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))',
       'sysm=systemic_enabled and ((pg<=-.032 and ud1[k]>=.70) or (pg<=-.044 and uneg[k]>=.75))')
change('if reb:\n                c1=', 'ledger[bb,k,1]=f;ledger[bb,k,2]=w1;ledger[bb,k,3]=aw;ledger[bb,k,4]=reb;ledger[bb,k,17]=sysm\n            ledger[bb,k,19]=nt1;ledger[bb,k,20]=nt2;ledger[bb,k,21]=nat\n            if reb:\n                c1=')
change('val*=1-cost*tv;T[bb,k]=tv;', 'ledger[bb,k,5]=tv;ledger[bb,k,6]=val*cost*tv\n                val*=1-cost*tv;T[bb,k]=tv;')
change('if t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55):','if stops_enabled and t1>=0 and u1>0 and p1 and (sysm or ud1[k]>=.55):')
change('if t2>=0 and u2>0 and p2 and (sysm or ud1[k]>=.55):','if stops_enabled and t2>=0 and u2>0 and p2 and (sysm or ud1[k]>=.55):')
change('if fill>0:free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)',
'''if fill>0:
                    ledger[bb,k,7]=1;ledger[bb,k,9]+=u1*fill*cost
                    if O[k,t1]>sp:ledger[bb,k,10]+=u1*(sp-fill)
                    ledger[bb,k,22]+=u1*fill
                    free+=u1*fill*(1-cost);u1=0.;cd=max(cd,3)''')
change('if fill>0:free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)',
'''if fill>0:
                    ledger[bb,k,8]=1;ledger[bb,k,9]+=u2*fill*cost
                    if O[k,t2]>sp:ledger[bb,k,10]+=u2*(sp-fill)
                    ledger[bb,k,22]+=u2*fill
                    free+=u2*fill*(1-cost);u2=0.;cd=max(cd,3)''')
change('nv=free\n            if t1>=0',
'''ledger[bb,k,18]=cd
            ledger[bb,k,11]=u1*O[k,t1] if t1>=0 else 0.
            ledger[bb,k,12]=u2*O[k,t2] if t2>=0 else 0.
            ledger[bb,k,13]=au*O[k,at] if at>=0 else 0.
            ledger[bb,k,14]=bu*O[k,bil];ledger[bb,k,15]=su*O[k,shv];ledger[bb,k,16]=free
            ledger[bb,k,23]=val
            nv=free
            if t1>=0''')
change('return E,T,X,AW','return E,T,X,AW,ledger')
p=B/'work/instrumented_engine.py';p.write_text('"""Research-only Stage19 switches and execution audit. Generated from frozen source."""\nimport numpy as np\nfrom numba import njit\n'+s)
print('instrumented_sha256',hashlib.sha256(p.read_bytes()).hexdigest())
