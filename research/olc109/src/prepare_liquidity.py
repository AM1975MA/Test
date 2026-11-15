"""Build historical traded EUR turnover from the frozen OLC108 source copies."""
from pathlib import Path
import argparse,hashlib,json,datetime
import numpy as np
import pandas as pd

def build(root,source):
    root,source=Path(root).resolve(),Path(source).resolve()
    panel_path=root/'source/data/XETRA_EUR_ETF.npz'
    with np.load(panel_path,allow_pickle=False) as z:p={k:z[k] for k in z.files}
    assert hashlib.sha256(panel_path.read_bytes()).hexdigest()=='14b4ee4a5834e93407f5b7aac2c4857cf6f0b0403f38296daea2725fe4848b96'
    names=list(map(str,p['names']));dates=pd.DatetimeIndex(p['dates'])
    coverage=pd.read_csv(source/'data/UNIVERSE_COVERAGE.csv').set_index('isin')
    turnover=np.zeros(p['C'].shape);sources=[]
    for j,isin in enumerate(names):
        symbol=coverage.loc[isin,'symbol'];path=source/'data/prices'/f'{symbol}.csv.gz'
        q=pd.read_csv(path,usecols=['date','close','volume'])
        q['date']=pd.to_datetime(q['date']);q=q.set_index('date').reindex(dates)
        values=(q.close*q.volume).to_numpy()
        good=p['observed'][:,j]&np.isfinite(values)&(values>=0)
        turnover[good,j]=values[good]
        sources.append(dict(isin=isin,symbol=symbol,price_file=str(path.relative_to(source)),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    out=root/'data/LIQUIDITY.npz'
    np.savez_compressed(out,dates=p['dates'],names=p['names'],turnover=turnover)
    manifest=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  input_panel_sha256=hashlib.sha256(panel_path.read_bytes()).hexdigest(),
                  output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
                  formula='raw EUR close * raw volume where V3 observed; zero otherwise',
                  rows=len(dates),instruments=len(names),sources=sources)
    (root/'data/LIQUIDITY_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='sources'},indent=2))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('root');ap.add_argument('source');a=ap.parse_args();build(a.root,a.source)
