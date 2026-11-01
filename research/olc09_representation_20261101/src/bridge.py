"""Load authenticated immutable parent without changing its source or outputs."""
from pathlib import Path
import os,sys
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(os.environ.get('OLC09_ROOT',Path(__file__).resolve().parents[1])).resolve()
PARENT=ROOT/'parent'
os.environ['OLC08F_ROOT']=str(PARENT)
sys.path.insert(0,str(PARENT/'src'))
import train_pack as parent_train
import bootstrap as parent_bootstrap
from diagnostic_primitives import permute_block
from feature_blocks import PATH
from train_variants import annual_inputs,arr_hash,key_hash
from recovery_core import atomic_json,sha256,complete_checkpoint,valid_checkpoint,canonical_forecasts
from context import FEATURES_42,ET_MODEL_KW,XGB_MODEL_KW
ALIASES={x+'_mean_rank':x+'_univ_rank' for x in ['cluster_acc_5_21','cluster_eff_63','cluster_ret_21']}
CORE=[c for c in FEATURES_42 if c not in ALIASES]
PATH_COLS=[c+'_pct' for c in PATH]
