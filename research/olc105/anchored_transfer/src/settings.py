from pathlib import Path
import os,sys
for n in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[n]='1'
ROOT=Path(__file__).resolve().parents[1]
BASE=Path(os.environ.get('OLC104_ROOT','/mnt/data/olc105_work/OLC104_20261114'))
CONTROL=Path(os.environ.get('OLC105_CONTROLS','/mnt/data/olc105_work/controls'))
APPEND=Path(os.environ.get('OLC100_APPEND','/mnt/data/olc105_work/anchor_append'))
SRC=BASE/'source/legacy/source/research/tail-only-and-allocation-ablation-20261017'
VENDOR=SRC/'vendor/etf_trader_v2'
N19=BASE/'source/native19/olc19_combined_risk_20261102'
P18=N19/'restore/olc18_execution_20261102'
P16=P18/'parent_archive/parent/olc16_contextual_rank_20261102'
S=BASE/'source/forward100/srcfreeze'
sys.path[:0]=[str(ROOT/'src'),str(S),str(P16/'src'),str(N19/'src'),str(SRC),str(VENDOR/'src'),str(CONTROL)]
