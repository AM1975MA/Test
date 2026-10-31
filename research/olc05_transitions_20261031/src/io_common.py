from pathlib import Path
import numpy as np,pandas as pd,hashlib,json
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/lifecycle_execution_20261031'
def load(market,weight='HALF'):
 q=dict(np.load(SOURCE/f'inputs/{market}_STATE_{weight}.npz',allow_pickle=False))
 dates=pd.DatetimeIndex(q['dates']);cal=pd.read_csv(SOURCE/f'inputs/{market}_CALENDAR.csv',parse_dates=['signal_date','entry_date','exit_date'])
 events=dates.isin(cal.entry_date)
 return q,np.array(events),cal

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
