"""The additional twelve paths are kept separate from the original 156-path lot."""
from bootstrap import *
import replay_pack as rp
import numpy as np,pandas as pd

def main():
    original_out=ROOT/'results';out=original_out/'interaction';out.mkdir(exist_ok=True)
    rp.OUT=out;rp.PATHS=out/'paths';rp.PATHS.mkdir(exist_ok=True)
    rp.forecast_path=lambda market,variant:original_out/f'{market}_{variant}_FORECASTS.csv.gz'
    rp.run(['H_PATH_KEEP'])
    for market in ['EU','USA']:
        x=pd.read_csv(out/f'{market}_H_PATH_KEEP_COMBINED.csv',index_col=0,parse_dates=True)
        y=pd.read_csv(original_out/f'{market}_REF_RSI_COMBINED.csv',index_col=0,parse_dates=True)
        assert x.index.equals(y.index) and x.columns.equals(y.columns)
        assert np.array_equal(np.isfinite(x),np.isfinite(y))
    sc=pd.read_csv(out/'SCORECARD.csv')
    print(sc.query("period=='ACTIVE2021_2024' and fee==.001").pivot(index='policy',columns='market',values=['cagr','maxdd']).to_string())
if __name__=='__main__':main()
