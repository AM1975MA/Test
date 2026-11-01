from pathlib import Path
import os,subprocess,sys

def test_null_diagnostic_imports_local_helpers_in_fresh_interpreter():
    root=Path(__file__).resolve().parents[1]
    env=dict(os.environ,PYTHONPATH=str(root/'src'),OLC08F_ROOT=str(root))
    result=subprocess.run([sys.executable,'-c','import replay_nulls; assert callable(replay_nulls.score_month)'],env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
