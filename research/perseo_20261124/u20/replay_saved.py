"""Standalone replay from the two U20 archives; no U19 imports or refitting."""
from pathlib import Path
import json,sys,numpy as np
from frozen_engine20 import simulate
ROOT=Path(__file__).resolve().parent

def load(p):
 with np.load(p) as z:return {k:z[k].copy() for k in z.files}

def main():
 manifest=json.loads((ROOT/'REPLAY_MANIFEST.json').read_text());chosen=sys.argv[1:];checks=[]
 for item in manifest:
  if chosen and not any(s in item['account'] for s in chosen):continue
  q=load(ROOT/item['state']);saved=load(ROOT/item['account']);q['risk_mode']=saved['risk_mode']
  if item['lag1']:
   for k in ['d1','d2','alt']:q[k][:,1:]=q[k][:,:-1]
   q['events'][1:]=q['events'][:-1];q['events'][0]=True
  risk=item['risk']
  r=simulate(q,q['events'],policy='IMMEDIATE',fraction=1,fee=0,stop_friction=0,exposure_timing='PREVIOUS' if risk else 'OFF',stop_timing='NOW' if risk else 'OFF',ordinary_alarm=False,fast_stop=risk,lock_days=3,risk_on=risk,broker={'initial':10000.,'ticket':1.,'impact':item['bps']/10000})
  assert np.array_equal(r['ledger'],saved['ledger']),item['account']
  checks.append(item['account']);print('PASS',item['account'],flush=True)
 (ROOT/'REPLAY_CHECK.json').write_text(json.dumps({'status':'PASS','accounts':checks},indent=2))
if __name__=='__main__':main()
