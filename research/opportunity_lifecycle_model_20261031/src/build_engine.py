"""Minimal, anchor-checked extension of the immutable legacy accounting kernel."""
from common import F,ROOT
import inspect,sys,hashlib,json
sys.path.insert(0,str(F/'previous/work'))
from remedy_engine import simulate_remedy
s=inspect.getsource(simulate_remedy.py_func)
s=s.replace('@njit(cache=True)\n','')
def change(a,b):
    global s
    assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
change('def simulate_remedy(', 'def simulate_action(')
change('total_risk_cap=None, recovery_ok=None,','total_risk_cap=None, recovery_ok=None, controller=None, alt_selector=None,')
change('nt1=d1[bb,k];nt2=d2[bb,k];w1=wg[bb,k]', '''nt1=d1[bb,k];nt2=d2[bb,k];w1=wg[bb,k];rho=1.
            if controller is not None:
                nt1,nt2,w1,rho=controller.step(k,t1,t2,at,u1,u2,au,bu,su,free,pw1,pf)
                assert 0<=rho<=1 and 0<=w1<=1''')
change('f=min(basef,G2[bb,k])','f=min(basef,G2[bb,k])*rho')
change('if use_alt and ALT[bb,k]>=0:\n                nat=int(ALT[bb,k]);', '''alternative=int(ALT[bb,k]) if alt_selector is None else alt_selector(k,nt1,nt2,w1)
            if use_alt and alternative>=0:
                nat=alternative;''')
change('cashw=cw-aw','aw=min(aw,max(0.,rho-f))\n            cashw=cw-aw')
change('if reb and strict_quotes and observed is not None:', '''if controller is not None and getattr(controller,'force_rebalance',False):reb=True
            if reb and strict_quotes and observed is not None:''')
(ROOT/'src/action_engine.py').write_text('"""OLC01: unchanged default accounting; optional actual-incumbent decision callback."""\nimport numpy as np\n'+s)
(ROOT/'results/ENGINE_SOURCE.json').write_text(json.dumps({'source_sha256':hashlib.sha256(inspect.getsource(simulate_remedy.py_func).encode()).hexdigest(),'source_file':str(inspect.getfile(simulate_remedy.py_func)),'adapter_sha256':hashlib.sha256((ROOT/'src/action_engine.py').read_bytes()).hexdigest(),'changes':['monthly decision callback before current gap','decision primary investment fraction','dynamic V6 eligibility/relative ranking callback','V6 cannot refill voluntary cash']},indent=2))
