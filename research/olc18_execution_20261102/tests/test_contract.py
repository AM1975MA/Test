import numpy as np
import pytest
from stop_contract import eligible,fill

def test_weak_prearm_does_not_require_market_confirmation():
 assert eligible('PREARM_WEAK',True,False)
 assert not eligible('PREARM_WEAK',False,True)
def test_all_prearmed_without_weakness():
 assert eligible('PREARM_ALL',False,False)
def test_legacy_requires_both():
 assert eligible('LEGACY',True,True)
 assert not eligible('LEGACY',True,False)
 assert not eligible('LEGACY',False,True)
def test_no_stop_disabled():
 assert not eligible('NO_STOP',True,True)
def test_bad_policy_rejected():
 with pytest.raises(ValueError):eligible('LOOKAHEAD',True,True)
def test_gap_price_not_barrier():
 raw,net,offset=fill('PREARM_WEAK',90,88,91,100,92,friction=.001)
 assert raw==90 and net==90*.999 and offset==0
 assert raw<94.5
def test_intraday_barrier():
 assert fill('PREARM_WEAK',100,94,99,100,101,friction=.001)==(94.5,94.5*.999,0)
def test_no_touch_no_fill():
 assert fill('PREARM_ALL',100,95,99,100,101,friction=.001) is None
def test_eod_low_uses_next_open_not_barrier():
 assert fill('EOD_LOW',100,90,99,100,102,friction=.001)==(102,102*.999,1)
def test_eod_close_ignores_recovered_intraday_touch():
 assert fill('EOD_CLOSE',100,90,99,100,102,friction=.001) is None
def test_eod_close_exit_next_open_gap():
 assert fill('EOD_CLOSE',100,90,93,100,85,friction=.001)==(85,85*.999,1)
def test_next_price_does_not_change_alarm():
 for p in [50,100,150]:
  assert fill('EOD_LOW',100,90,99,100,p,friction=.001) is not None
  assert fill('EOD_CLOSE',100,90,99,100,p,friction=.001) is None
def test_next_missing_never_stale_fill():
 with pytest.raises(ValueError,match='observed'):
  fill('EOD_LOW',100,90,99,100,101,next_observed=False,friction=.001)
def test_unobserved_low_does_not_trigger():
 assert fill('PREARM_WEAK',100,90,99,100,101,low_observed=False,friction=.001) is None
def test_legacy_gap_slippage_unchanged():
 assert fill('LEGACY',90,88,91,100,92)==(90,90,0)
 assert fill('LEGACY',100,94,99,100,92)==(94.5,94.5*.999,0)
def test_invalid_friction_rejected():
 with pytest.raises(ValueError):fill('PREARM_ALL',100,94,99,100,101,friction=-.1)
def test_friction_monotonic():
 assert fill('PREARM_ALL',100,94,99,100,101,friction=.005)[1]<fill('PREARM_ALL',100,94,99,100,101,friction=.001)[1]
