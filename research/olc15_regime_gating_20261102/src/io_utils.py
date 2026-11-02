from pathlib import Path
import json,hashlib
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
MARKETS=('EU','USA')
BASE_VARIANTS=('ORIGINAL','CUM_FIXED','CUM_FIT','HALF','CONSTANT','RECENT','CONTEXT','CONTEXT_RECENT','CONTEXT_RECENT_LAG')
FUSION_VARIANTS=('F_CONSTANT','F_RECENT','F_CONTEXT','F_CONTEXT_RECENT','F_CONTEXT_RECENT_LAG')
VARIANTS=BASE_VARIANTS+FUSION_VARIANTS
def readcsv(p):
 f=pd.read_csv(p,float_precision='round_trip')
 for c in f.columns:
  if c in ['date','available'] or c.endswith('_date') or c.startswith('exit_date_'):f[c]=pd.to_datetime(f[c])
 return f
def dump(p,obj):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,default=str));tmp.replace(p)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
