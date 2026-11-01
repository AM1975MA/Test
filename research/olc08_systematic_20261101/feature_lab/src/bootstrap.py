"""Path-only bootstrap for immutable authenticated parents."""
from pathlib import Path
import os,sys
ROOT=Path(os.environ.get('OLC08F_ROOT',Path(__file__).resolve().parents[1])).resolve()
PARENT=ROOT/'parents'
os.environ['OLC08_ROOT']=str(PARENT)
for key in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:
    os.environ[key]='1'
sys.path.insert(0,str(PARENT/'src'))
from context import CAL,SOURCE,kernel,FEATURES_42,ET_MODEL_KW,XGB_MODEL_KW,corrected_target,recipe,prepare_targets
from recovery_core import atomic_json,sha256,complete_checkpoint,valid_checkpoint,canonical_forecasts
