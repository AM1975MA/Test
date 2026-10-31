"""Restore only the exact inputs this experiment uses, after archive SHA verification."""
from pathlib import Path
import argparse,hashlib,zipfile
ROOT=Path(__file__).resolve().parent
SPECS=[('OLC01_Opportunita_Permanenza_Checkpoint_20261031.zip','6151028ccff8419a057485817d003993969e352c00eb707fdb63c4a9d696203f'),('ETF_Frontiera_USA_Europa_Risultati_20261031.zip','feb8d79f5dc8ac95b545d8bc00cb42e0d43b0329c6f17b23bfddfaf0e2361789')]
def required(name):
 p=Path(name)
 if p.name in ['EU_CALENDAR.csv','USA_CALENDAR.csv','EU_SCORE.csv','USA_SCORE.csv','EU_Open.pkl','USA_Open.pkl']:return True
 if 'inputs' in p.parts and p.name.endswith(('_STATE_HALF.npz','_STATE_ORIGINAL.npz')):return True
 if p.name in ['EU_FORECASTS.csv.gz','USA_FORECASTS.csv.gz']:return True
 if p.name=='action_engine.py' and 'lifecycle_execution_20261031' in p.parts:return True
 if 'paths' in p.parts and '_CL01_' in p.name and p.suffix=='.npz':return True
 return False
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--archives',type=Path,required=True);args=parser.parse_args()
 for fn,expected in SPECS:
  f=args.archives/fn
  if hashlib.sha256(f.read_bytes()).hexdigest()!=expected:raise ValueError(f'Archive checksum mismatch: {fn}')
  with zipfile.ZipFile(f) as z:
   for n in z.namelist():
    p=Path(n)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe archive path')
    if not required(n):continue
    out=ROOT/'source'/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(n))
 print('Restored hash-verified inputs. No network access or model fitting.')
