import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pandas as pd
import pytest
import transfer_contract as t

def test_select_excludes_anchor_even_if_highest():
 f=pd.DataFrame({'ticker':['ANCHOR','NEW1','NEW2'],'score':[.99,.5,.4]})
 assert t.select_pair(f,{'NEW1','NEW2'})==('NEW1','NEW2')
def test_select_rejects_less_than_two_valid_new():
 f=pd.DataFrame({'ticker':['ANCHOR','NEW1'],'score':[.99,.5]})
 with pytest.raises(ValueError):t.select_pair(f,{'NEW1','NEW2'})
def test_signal_strictly_before_open():
 with pytest.raises(ValueError):t.require_asof('2026-10-30','2026-10-30')
 t.require_asof('2026-10-30','2026-11-02')
def test_no_anchor_book():
 with pytest.raises(ValueError):t.require_allowed(['ANCHOR'],{'NEW1'})
 t.require_allowed(['NEW1','EUR_CASH_A'],{'NEW1'})
def test_last_month_cutoff_includes_friday_month_end():
 assert t.completed_month_cutoff('2026-11-13')==pd.Timestamp('2026-10-31')
