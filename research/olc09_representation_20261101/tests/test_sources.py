import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from replay_models import source,ARCHIVE
from bridge import parent_bootstrap

def test_rsi_reference_uses_authenticated_recovery_forecasts():
    for m in ['EU','USA']:
        p=source(m,'REF_RSI')
        assert p.is_file()
        assert p==parent_bootstrap.PARENT/'results'/f'{m}_R_RSI_DOMAIN_FORECASTS.csv.gz'

def test_all_archived_forecasts_exist():
    for m in ['EU','USA']:
        for name in ARCHIVE:assert source(m,name).is_file()
