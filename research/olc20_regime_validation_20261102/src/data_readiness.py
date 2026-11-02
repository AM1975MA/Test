"""Audit the actual prepared-data limits, without relabeling them as raw certification."""
import json,hashlib
import numpy as np,pandas as pd
from paths import ROOT,P16,P17,P18
from experiment import load_groups,dump

def main():
    gs,_,_=load_groups();rows=[]
    for market in ('EU','USA'):
        q=dict(np.load(P16/f'inputs/{market}_STATE_HALF.npz',allow_pickle=False))
        groups=[x for x in gs if x['market']==market]
        observed=q.get('observed');low_observed=q.get('low_observed')
        source=P16/f'inputs/{market}_STATE_HALF.npz'
        rows.append(dict(market=market,first_date=str(q['dates'][0]),last_date=str(q['dates'][-1]),
          intervals=len(q['dates'])-1,prepared_columns=len(q['tickers']),
          has_observed_mask=observed is not None,has_observed_low_mask=low_observed is not None,
          nonobserved_cells=int((~observed).sum()) if observed is not None else None,
          invalid_prepared_open=int((~np.isfinite(q['O'])|(q['O']<=0)).sum()),
          current_forecast_dates=len(groups),complete_63day_groups=sum(x['full'] for x in groups),
          first_forecast=str(min(x['date'] for x in groups)),last_forecast=str(max(x['date'] for x in groups)),
          sha256=hashlib.sha256(source.read_bytes()).hexdigest()))
        assert len(np.unique(q['dates']))==len(q['dates'])
        assert (q['dates'][1:]>q['dates'][:-1]).all()
        for x in groups:
            assert np.isfinite(x['z']).all()
            if x['full']:assert x['available']>x['date']
    eu=dict(np.load(P17/'inputs/EU_V6_CONTEXT.npz',allow_pickle=False))
    assert (eu['SPY_source_date']<eu['dates']).all()
    result=dict(prepared_inputs=rows,EU_V6_global_proxy_strictly_previous_date=True,
        raw_adjustment_metadata_certified=False,delisted_universe_certified=False,
        original_quote_masks_certified=False,intraday_bidask_available=False,
        prospective_observations_collected=0,
        provider_checks=[
          dict(provider='Financial_Datasets',ticker='XLE',dates='2020-03-12',interval='minute',
            result="Rejected: Must be one of {'year', 'week', 'month', 'day'}"),
          dict(provider='Financial_Datasets',ticker='XLE',dates='2020-03-11 to 2020-03-12',interval='day',
            result='Rejected: insufficient API credit balance; no data returned; no credits purchased')],
        interpretation='Finite prepared prices do not prove original observations, total-return conventions or executable fills. No new vendor prices entered any model or account.')
    dump(ROOT/'results/DATA_READINESS.json',result);print(json.dumps(result,indent=2))
if __name__=='__main__':main()
