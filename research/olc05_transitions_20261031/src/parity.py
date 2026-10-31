from io_common import *
from vector_engine import simulate
import sys
sys.path.insert(0,str(SOURCE/'src'))
from action_engine import simulate_action

def main():
 out=ROOT/'results';rows=[]
 for market in ['EU','USA']:
  for wt in ['HALF','ORIGINAL']:
   q,ev,cal=load(market,wt);ts=list(q['tickers']);bil=ts.index('BIL') if market=='USA' else ts.index('EUR_CASH_A');shv=ts.index('SHV') if market=='USA' else ts.index('EUR_CASH_B')
   for fee in [.001,.003]:
    args=[q['d1'],q['d2'],q['weights']]+[q[x] for x in ['O','L','C','PC','gap','ud1','uneg','UH','SA']]+[bil,shv,q['g'][None,:],q['g'],q['alt'],True]
    old=simulate_action(*args,cost=fee,slip=.001,observed=q.get('observed'),low_observed=q.get('low_observed'))
    ref=np.load(SOURCE/f'results/paths/{market}_CL01_{wt}_C{int(fee*10000)}.npz')
    olderr=np.max(abs(old[0][0]-ref['nav']))
    r=simulate(q,ev,fee=fee,legacy_slots=True)
    error=np.max(abs(r['nav']-ref['nav']));k=int(np.argmax(abs(r['nav']-ref['nav'])))
    diag={'market':market,'weight':wt,'fee':fee,'original_replay_error':float(olderr),'vector_legacy_error':float(error),'max_error_date':str(pd.Timestamp(q['dates'][k]).date()),'daily_accounting_error':float(np.max(abs(r['ledger'][:,25])))}
    rows.append(diag);print(diag,flush=True)
    if error>1e-10:
     ix=np.flatnonzero(abs(r['nav']-ref['nav'])>1e-10)[0]
     print('FIRST',ix,q['dates'][ix],r['nav'][ix],ref['nav'][ix]);print('NEW',r['ledger'][ix]);print('OLD',old[4][0,ix]);np.savez_compressed(out/'PARITY_DEBUG.npz',new=r['ledger'],old=old[4][0],dates=q['dates']);raise AssertionError(diag)
    assert olderr<1e-12
 pd.DataFrame(rows).to_csv(out/'BASELINE_PARITY.csv',index=False)
 print('PASS_ALL_8')
if __name__=='__main__':main()
