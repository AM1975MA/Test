from pathlib import Path
import sys, os
ROOT=Path(__file__).resolve().parents[1]
PARENT=ROOT/'source/olc02_pairwise_20261031'
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[k]='1'
sys.path.insert(0,str(PARENT/'src'))
