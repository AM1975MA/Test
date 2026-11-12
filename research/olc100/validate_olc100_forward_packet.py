#!/usr/bin/env python3
"""Static gate for OLC100 pre-outcome signal packets.

Passing this gate is NOT a proof of independent pre-outcome storage: only an
externally verified server-side GitHub commit receipt created before the first
executable open can supply the provenance certificate. No future return fields
are allowed at prediction registration.
"""
from __future__ import annotations
import argparse,datetime as dt,json,re
from pathlib import Path

ARMS={
 'B_BASE':('S1','A0','T0','P0'),
 'C_CANDIDATE':('S1','A1','T1','P0'),
 'D_SELECTION':('S0','A0','T0','P0'),
 'D_ALLOCATION':('S1','A1','T0','P0'),
 'D_TIMING':('S1','A0','T1','P0'),
 'D_PROTECTION':('S1','A0','T0','P1'),
}
SOURCE={
 'olc19_zip_sha256':'3b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540',
 'olc56_zip_sha256':'f22b92a5c4b5024d6f8afef6504b794e1f46ff53ffa87adfaa8f3a2e0e3e2573',
 'olc67_zip_sha256':'dbfb2cec587fa7b1a118209856d474236707692b6f7ed68fa99c1c27df9661c4',
}
EXCLUDED_TOKENS=['future','realized','outcome','target_return','forward_return','backtest_cagr','oracle','actual_logr','pnl']

def stamp(value):
 d=dt.datetime.fromisoformat(value.replace('Z','+00:00'))
 assert d.tzinfo is not None and d.utcoffset() is not None,'UTC/offset required'
 return d.astimezone(dt.timezone.utc)

def sha(value):
 return isinstance(value,str) and bool(re.fullmatch('[a-f0-9]{64}',value))

def validate(data):
 assert data.get('protocol_id')=='OLC100'
 assert data.get('market') in ('EU','USA')
 asof=stamp(data['source_data_asof_utc']);pred=stamp(data['signal_generated_at_utc']);opening=stamp(data['first_eligible_open_utc'])
 assert asof<=pred<opening,('invalid information chronology',asof,pred,opening)
 assert pred.date()>dt.date(2026,11,12),'2026H2 retrospective bridge is not prospective'
 assert dt.date.fromisoformat(data['signal_date'])<=pred.date()
 assert (opening-pred).total_seconds()>=0
 assert isinstance(data.get('account_state_sha256'),str) and sha(data['account_state_sha256'])
 assert sha(data['universe_snapshot_sha256']) and sha(data['input_snapshot_sha256'])
 assert 0<=float(data['v6_exposure_budget'])<=1
 assert all(data.get(k)==v for k,v in SOURCE.items()),'frozen parent archive mismatch'
 assert set(data['arms'])==set(ARMS),'exact six arms required'
 # Never permit results in the pre-signal packet, including deeply nested keys.
 def banned_keys(a):
  if isinstance(a,dict):
   for k,v in a.items():
    assert not any(tok in str(k).lower() for tok in EXCLUDED_TOKENS),('result leakage field',k)
    banned_keys(v)
  elif isinstance(a,list):
   for v in a:banned_keys(v)
 banned_keys(data)
 for arm,contract in ARMS.items():
  val=data['arms'][arm]
  assert tuple(val[k] for k in ['selection','allocation','timing','protection'])==contract,(arm,'contract changed')
  a,b=val['tickers']; assert a and b and a!=b
  w1,w2=map(float,val['weights']);assert -1e-10<=w1<=1+1e-10 and -1e-10<=w2<=1+1e-10
  assert abs(w1+w2-1)<1e-9
  if contract[1]=='A0': assert abs(w1-.5)<1e-9
  if contract[1]=='A1': assert .25-1e-9<=w1<=.75+1e-9
  assert val['delay_sessions']==(1 if contract[2]=='T0' else 3)
  assert val['protection_name']==('V6_FAST_LOCK3' if contract[3]=='P0' else 'V6_BASE')
  assert val['selection_name']==('TOP2_CONTEXT_REVALUE' if contract[0]=='S1' else 'ORIGINAL_FUSION')
 s1=data['arms']['B_BASE']['tickers'];s0=data['arms']['D_SELECTION']['tickers']
 assert all(data['arms'][k]['tickers']==s1 for k in ['C_CANDIDATE','D_ALLOCATION','D_TIMING','D_PROTECTION'])
 assert all(data['arms'][k]['weights']==data['arms']['C_CANDIDATE']['weights'] for k in ['D_ALLOCATION'])
 return {'status':'STRUCTURALLY_VALID_PREOUTCOME_PACKET__PROVENANCE_NOT_ATTESTED',
         'protocol_id':'OLC100','market':data['market'],'signal_date':data['signal_date'],
         'first_executable_open_utc':opening.isoformat(),
         'n_frozen_arms':len(data['arms']),
         'genuinely_prospective_certified':False,
         'reason':'Needs externally fetched GitHub server commit timestamp AND immutable packet hash strictly before first executable open; local/self-asserted timestamps are not sufficient.'}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument('--packet',type=Path)
 ap.add_argument('--out',type=Path)
 args=ap.parse_args()
 if not args.packet or not args.packet.is_file():
  result={'status':'BLOCKED_NO_PREOUTCOME_OLC100_PACKET','genuinely_prospective_certified':False,
  'reason':'No new OLC19 EU/USA signal with trustworthy pre-first-open server receipt exists in supplied artifacts.'}
  print(json.dumps(result,indent=2));raise SystemExit(2)
 try:r=validate(json.loads(args.packet.read_text()))
 except (KeyError,AssertionError,TypeError,ValueError) as ex:
  result={'status':'INVALID_FORWARD_PACKET','genuinely_prospective_certified':False,'reason':str(ex)}
  print(json.dumps(result,indent=2));raise SystemExit(3)
 print(json.dumps(r,indent=2))
 if args.out:args.out.write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
