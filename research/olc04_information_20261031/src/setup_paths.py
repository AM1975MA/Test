from pathlib import Path
import os,sys
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[k]='1'
ROOT=Path(__file__).resolve().parents[1]
OLC3=ROOT/'source/olc03_selective_20261031'
OLC2=OLC3/'source/olc02_pairwise_20261031'
sys.path.insert(0,str(OLC2/'src'))
sys.path.insert(0,str(OLC3/'src'))
