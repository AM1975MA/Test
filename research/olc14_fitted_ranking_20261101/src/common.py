from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
P11=ROOT/'parents/olc11'
P12=ROOT/'parents/olc12_integration_20261101'
P13=ROOT/'parents/olc13_target_factorial_20261101'
SEEDS=(101,211,307)
MARKETS=('EU','USA')
HEADS=('C21','C42','C63','I42','I63')
TARGETS=('ORIGINAL_P15','EXP42_P15','ORIGINAL_P10','EXP42_P10')
VARIANTS=('ORIGINAL','TARGET_SELECT','CUM_FIXED','CUM_FIT','INC_FIXED','INC_FIT')
PROTOCOL='facad01242bca20502dcf5563b84c9f60d0bd015'
def readcsv(path):
 f=pd.read_csv(path,float_precision='round_trip')
 for c in ('signal_date','source_date','entry_date','exit_date_21','exit_date_42','exit_date_63','date','last_exit','available'):
  if c in f:f[c]=pd.to_datetime(f[c])
 return f
