import unittest,copy,datetime as dt
from validate_olc100_forward_packet import ARMS,SOURCE,validate

def packet():
 v={
 'protocol_id':'OLC100','market':'USA','signal_date':'2026-11-30',
 'source_data_asof_utc':'2026-11-30T21:00:00Z',
 'signal_generated_at_utc':'2026-11-30T22:00:00Z',
 'first_eligible_open_utc':'2026-12-01T14:30:00Z',
 'account_state_sha256':'a'*64,'universe_snapshot_sha256':'b'*64,
 'input_snapshot_sha256':'c'*64,'v6_exposure_budget':0.8,'arms':{},**SOURCE}
 for key,(s,a,t,p) in ARMS.items():
  v['arms'][key]={'selection':s,'allocation':a,'timing':t,'protection':p,
   'selection_name':'TOP2_CONTEXT_REVALUE' if s=='S1' else 'ORIGINAL_FUSION',
   'protection_name':'V6_FAST_LOCK3' if p=='P0' else 'V6_BASE',
   'tickers':['PPLT','PALL'] if s=='S1' else ['SMH','SOXX'],
   'weights':[.65,.35] if a=='A1' else [.5,.5],
   'delay_sessions':3 if t=='T1' else 1}
 return v
class TestForwardPacket(unittest.TestCase):
 def test_synthetic_staging_not_claimed_oos(self):
  self.assertFalse(validate(packet())['genuinely_prospective_certified'])
 def test_reject_lookahead(self):
  p=packet();p['source_data_asof_utc']='2026-12-05T00:00:00Z'
  with self.assertRaises(AssertionError):validate(p)
 def test_reject_future_label(self):
  p=packet();p['arms']['B_BASE']['future_return']=.9
  with self.assertRaises(AssertionError):validate(p)
 def test_reject_changed_causal_arm(self):
  p=packet();p['arms']['C_CANDIDATE']['weights']=[.9,.1]
  with self.assertRaises(AssertionError):validate(p)
 def test_reject_late_signal(self):
  p=packet();p['first_eligible_open_utc']='2026-11-30T20:30:00Z'
  with self.assertRaises(AssertionError):validate(p)
 def test_reject_modified_archives(self):
  p=packet();p['olc19_zip_sha256']='0'*64
  with self.assertRaises(AssertionError):validate(p)
 def test_reject_retrospective_as_prospective(self):
  p=packet();p['signal_generated_at_utc']='2026-10-31T22:00:00Z';p['source_data_asof_utc']='2026-10-31T21:00:00Z';p['signal_date']='2026-10-31'
  with self.assertRaises(AssertionError):validate(p)
if __name__=='__main__':unittest.main()
