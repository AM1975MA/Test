import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from bridge import complete_checkpoint,valid_checkpoint
import pytest

def test_hash_tamper_fails_closed(tmp_path):
    (tmp_path/'model.txt').write_text('original')
    complete_checkpoint(tmp_path,'config-A',['model.txt'])
    assert valid_checkpoint(tmp_path,'config-A')
    (tmp_path/'model.txt').write_text('changed!')
    assert not valid_checkpoint(tmp_path,'config-A')

def test_different_configuration_not_reused(tmp_path):
    (tmp_path/'data').write_text('data')
    complete_checkpoint(tmp_path,'A',['data'])
    assert not valid_checkpoint(tmp_path,'B')

def test_missing_file_is_not_complete(tmp_path):
    with pytest.raises(FileNotFoundError):complete_checkpoint(tmp_path,'A',['absent'])
    assert not valid_checkpoint(tmp_path,'A')
