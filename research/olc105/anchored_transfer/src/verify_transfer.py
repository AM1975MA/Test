"""Independent reconciliation from persisted NAV, positions, prices and order logs.
Does not import fitting, score construction, simulator or its metric functions.
"""
from pathlib import Path
import math,json,hashlib
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];P=R/'results';D=R/'data'
KEY=['arm','mode','initial_eur','ticket_fee_eur','shortfall_bps_per_side']
def keys(row):return tuple('NONE' if pd.isna(row[k]) else row[k] for k in KEY)
def run():
    scores=pd.read_csv(P/'TRANSFER_SCORECARD.csv');daily=pd.read_csv(P/'TRANSFER_DAILY.csv.gz',parse_dates=['date']);orders=pd.read_csv(P/'TRANSFER_ORDERS.csv.gz',parse_dates=['date'])
    groups={keys(g.iloc[0]):g.sort_values('date') for _,g in daily.groupby(KEY,dropna=False)}
    ogroups={keys(g.iloc[0]):g for _,g in orders.groupby(KEY,dropna=False)}
    expected_cost=orders.ticket_fee_eur+orders.notional_eur*orders.shortfall_bps_per_side/10000
    costerr=float(abs(orders.cost_eur-expected_cost).max());assert costerr<1e-8
    errors=[];common={};base=[]
    for row in scores.to_dict('records'):
        g=groups[keys(row)];g=g[g.date<=pd.Timestamp(row['end_open'])]
        assert g.date.is_unique and g.date.is_monotonic_increasing
        v=list(g.nav_open);peak=1.;dd=0.
        for x in v:peak=max(peak,x);dd=min(dd,x/peak-1)
        span=(g.date.iloc[-1]-g.date.iloc[0]).days;ann=math.exp(math.log(v[-1])*365.2425/span)-1
        err=max(abs(ann-row['cagr_calendar']),abs(dd-row['maxdd_openings']),abs(v[-1]-1-row['net_cumulative']),abs(v[-1]*row['initial_eur']-row['end_equity_eur'])/row['initial_eur'])
        assert err<1e-11,(row['arm'],err);errors.append(err)
        common.setdefault(row['window'],set()).add(tuple(g.date))
        if row['mode']=='BROKER':
            o=ogroups[keys(row)];o=o[o.date<pd.Timestamp(row['end_open'])]
            assert len(o)==row['ticket_orders'];assert abs(o.cost_eur.sum()-row['modelled_cost_eur'])<1e-7
            before=g[g.date<pd.Timestamp(row['end_open'])];assert abs(o.cost_eur.sum()-before[['rebalance_cost','stop_cost','stop_slippage']].to_numpy().sum())<1e-7
        if row['arm']=='WORLD_PASSIVE':
            z=np.load(D/'WORLD_PASSIVE_STATE.npz');i=list(z['tickers']).index('IE00BFY0GT14');px=z['O'][:len(g),i]
            initial=row['initial_eur'];net=1. if row['mode']=='GROSS' else (initial-row['ticket_fee_eur'])/(1+row['shortfall_bps_per_side']/10000)/initial
            pred=net*px/px[0];pred[0]=1.
            assert np.max(abs(pred-np.array(v)))<1e-12
    assert all(len(x)==1 for x in common.values())
    allowed=set(pd.read_csv(P/'CANDIDATE_SOURCE_QA.csv')['isin'])|{'EUR_CASH_A','EUR_CASH_B'}
    position_error=0.;paths=0
    for path in P.glob('*_PATH.npz'):
        tag=path.stem.removesuffix('_PATH');arm=tag.rsplit('_',1)[0];z=np.load(D/(arm+'_STATE.npz'));a=np.load(path)
        book=a['primary_units']+a['defensive_units'];held=np.any(book>1e-14,axis=0)
        assert set(z['tickers'][held]).issubset(allowed)
        own=np.sum(book[:-1]*z['O'][1:],axis=1)+a['free_cash'][:-1]
        err=float(np.max(abs(own-a['ledger'][1:,0])));assert err<1e-12,(path.name,err);position_error=max(position_error,err)
        assert np.max(abs(a['nav'][:-1]-own))<1e-12
        assert np.min(book)>-1e-14 and np.min(a['free_cash'])>-1e-12
        paths+=1
    dec=pd.read_csv(P/'ANCHORED_TRANSFER_DECISIONS.csv',parse_dates=['signal_date','effective_date']);assert (dec.signal_date<dec.effective_date).all()
    elig=pd.read_csv(P/'ASOF_ELIGIBILITY_CORRECTED.csv',parse_dates=['signal_date'])
    for r in dec.itertuples():
        allow=set(elig.loc[elig.signal_date.eq(r.signal_date),'isin']);assert r.ticker1 in allow and r.ticker2 in allow and r.ticker1!=r.ticker2
    out={'status':'PASS_NUMERICAL_TRANSFER_NOT_BROKER_CERTIFIED','paths':len(groups),'score_rows':len(scores),'independent_metric_max_abs_error':max(errors),'cost_formula_max_abs_error_eur':costerr,'full_position_paths_checked':paths,'position_value_max_abs_error':position_error,'matched_calendar_windows':{k:len(v) for k,v in common.items()},'signals_strictly_before_execution':len(dec),'anchor_holdings':0,'corporate_action_repair':'Issuer-confirmed P500 100-for-1 2025-12-15, forward economic units, raw unchanged','whole_share_execution':False,'actual_broker_quotes':False,'taxes':False,'prospective':False}
    (P/'INDEPENDENT_VALIDATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':run()
