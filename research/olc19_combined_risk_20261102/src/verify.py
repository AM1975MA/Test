"""Final array replay, parent controls, and real-data future-prefix verification."""
import json
import numpy as np
from run_experiment import ROOT,PARENT,VARIANTS
from combined_engine import simulate

def main():
    audit=[a for p in (ROOT/'results').glob('CHECKS_*.json') for a in json.loads(p.read_text())]
    keys=[];prefix=[];redundant=[]
    for m in ('EU','USA'):
        for v in VARIANTS:
            q=dict(np.load(PARENT/f'inputs/{m}_{v}.npz',allow_pickle=False));ev=q.pop('events')
            for a in [x for x in audit if x['market']==m and x['variant']==v]:
                r=simulate(q,ev,contract=a['contract'],fee=a['fee'],friction=a['stop_friction'])
                saved=np.load(ROOT/f"results/paths/{a['key']}.npz",allow_pickle=False)
                for k in r:np.testing.assert_array_equal(r[k],saved[k])
                keys.append(a['key'])
                if a['contract'].startswith('COMBINED'):
                    other=a['key'].replace('COMBINED','FAST');s=np.load(ROOT/f'results/paths/{other}.npz')
                    for k in ['nav','ledger','primary_units','defensive_units','free_cash','targets']:
                        np.testing.assert_array_equal(r[k],s[k])
                    redundant.append(a['key'])
        q=dict(np.load(PARENT/f'inputs/{m}_TOP2_CONTEXT_REVALUE.npz'));ev=q.pop('events')
        for mode in ('ALARM','FAST_NOLOCK','FAST_LOCK3','COMBINED_LOCK3'):
            for cutoff in (400,1100):
                a=[];s=[];o=[]
                base=simulate(q,ev,contract=mode,event_log=s,alarm_log=a,order_log=o)
                z={k:x.copy() for k,x in q.items()}
                for name in ('O','L','C','PC'):z[name][cutoff:]*=.63
                z['gap'][cutoff:]=-.4;z['ud1'][cutoff:]=1.;z['uneg'][cutoff:]=1.
                a2=[];s2=[];o2=[];new=simulate(z,ev,contract=mode,event_log=s2,alarm_log=a2,order_log=o2)
                for name in ('primary_units','defensive_units','targets','risk_trace'):
                    np.testing.assert_array_equal(base[name][:cutoff],new[name][:cutoff])
                np.testing.assert_array_equal(base['nav'][:cutoff-1],new['nav'][:cutoff-1])
                for old,newlog,key in [(a,a2,'signal_index'),(s,s2,'signal_index'),(o,o2,'index')]:
                    assert [x for x in old if x[key]<cutoff]==[x for x in newlog if x[key]<cutoff]
                prefix.append(dict(market=m,contract=mode,cutoff=cutoff))
        print('VERIFIED',m,flush=True)
    result=dict(exact_saved_paths=len(keys),keys=keys,exact_redundant_pairs=len(redundant),future_prefix_tests=prefix,
      parent_controls=sum(a.get('parent_exact',False) for a in audit),accounting_intervals=sum(a['intervals'] for a in audit),
      metric_values=sum(len(a['metrics'])*3 for a in audit),maximum_nav_error=max(a['nav_error'] for a in audit),
      maximum_metric_error=max(z['maximum_metric_error'] for a in audit for z in a['metrics']),external_review=False)
    (ROOT/'results/FINAL_VERIFICATION.json').write_text(json.dumps(result,indent=2))
    print({k:v for k,v in result.items() if k not in ('keys','future_prefix_tests')})
if __name__=='__main__':main()
