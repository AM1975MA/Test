"""Independent arithmetic and state checks on saved diagnostic rows."""
from pathlib import Path
import json
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];O=R/'results'
sw=pd.read_csv(O/'ACTUAL_SWITCHES.csv',parse_dates=['signal_date','entry_date','label_exit'])
sz=pd.read_csv(O/'SIZING_MONTHS.csv')
ev=pd.read_csv(O/'ACTUAL_DECISION_EVENTS.csv',parse_dates=['signal_date','entry_date'])
po=pd.read_csv(O/'OPPORTUNITY_MONTHS.csv',parse_dates=['signal_date','entry_date','label_exit'])
valid=sw[sw.valid];c=valid.cost_bps_side.to_numpy()/10000.
# Arithmetic reconstructed independently using an explicit sell cash / buy shares equation.
sold_cash=1.-c;new_market_value=sold_cash/(1.+c)
net_delta=new_market_value*(1.+valid.new_return.to_numpy())-(1.+valid.old_return.to_numpy())
maxswitch=float(np.max(np.abs(net_delta-valid.net_advantage)))
assert maxswitch<1e-12
s=sz[sz.valid];orig=s.weight1*s.return1+(1.-s.weight1)*s.return2;eq=(s.return1+s.return2)/2
maxsize=float(np.max(abs((orig-eq)-s.original_minus_half)));assert maxsize<1e-12
assert (sw.signal_date<sw.entry_date).all();assert (valid.entry_date<valid.label_exit).all()
assert not (ev.entry_date==pd.Timestamp('2026-07-01')).any()
assert (po.available_outcomes<=po.eligible).all()
for col in ['recall_actual2','recall_pool','recall_sameK','recall_highvolK']:
    x=po[col].dropna();assert x.between(0,1).all()
assert po.recall_actual2.max()<=1 # denominator can have fewer than5 positive winners.
# For each diagnostic switch, verify the outgoing name really was held before execution,
# and the incoming name was present after that opening's rebalance, before intraday stops.
checks=0;duration=[]
matched=pd.read_csv(O/'MATCHED_ACTUAL_SWITCH_OUTCOMES.csv',parse_dates=['signal_date','entry_date'])
for (market,weight),g in sw.groupby(['market','weight']):
    z=np.load(O/'references'/f'{market}_CL01_{weight}.npz',allow_pickle=False)
    ds=pd.DatetimeIndex(z['dates']);T=list(z['tickers']);ld=z['ledger']
    distinct=g[['signal_date','entry_date','old_ticker','new_ticker']].drop_duplicates()
    for row in distinct.itertuples(index=False):
        k=ds.get_indexer([row.entry_date])[0];old=T.index(row.old_ticker);new=T.index(row.new_ticker)
        assert k>0
        oldvalid=((ld[k-1,25]==old)&(ld[k-1,11]>0))|((ld[k-1,26]==old)&(ld[k-1,12]>0))
        newvalid=((ld[k,25]==new)&(ld[k,28]>0))|((ld[k,26]==new)&(ld[k,29]>0))
        assert oldvalid and newvalid and ld[k,4]==1
        checks+=1
        if weight=='ORIGINAL':
            end=k
            for t in range(k,len(ds)-1):
                held=((ld[t,25]==new)&(ld[t,11]>0))|((ld[t,26]==new)&(ld[t,12]>0))|((ld[t,27]==new)&(ld[t,13]>0))
                if not held:break
                end=t+1
            censored=end==len(ds)-1
            duration.append(dict(market=market,signal_date=row.signal_date,entry_date=row.entry_date,old_ticker=row.old_ticker,new_ticker=row.new_ticker,first_unheld_decision=ds[end],continuous_held_intervals=end-k,censored=censored))
dur=pd.DataFrame(duration);dur.to_csv(O/'ACTUAL_HOLDING_DURATION.csv',index=False)
key=['market','signal_date','entry_date','old_ticker','new_ticker'];m=matched.merge(dur,on=key,validate='one_to_one')
late=m[(m['21']<=0)&(m['63']>0)];late.to_csv(O/'LATE_PAYOFF_DIAGNOSTIC.csv',index=False)
late_summary=late.groupby('market').agg(n=('new_ticker','size'),median_continuous_intervals=('continuous_held_intervals','median'),left_before21=('continuous_held_intervals',lambda a:int((a<21).sum())),left_before63=('continuous_held_intervals',lambda a:int((a<63).sum())))
late_summary.to_csv(O/'LATE_PAYOFF_SUMMARY.csv')
ver={'static_switch_rows_checked':len(valid),'distinct_actual_replacements_verified':checks,'max_cash_accounting_delta_error':maxswitch,'sizing_rows_checked':len(s),'max_sizing_arithmetic_error':maxsize,'actual_holding_history_verified':True,'final_flat_day_excluded':True,'late_payoff':late_summary.reset_index().to_dict('records'),'caveat':'Selling before later hypothetical payoff is not necessarily a mistake; a replacement may do better, and risk/execution changes matter. No oracle timing strategy is claimed.'}
(O/'INDEPENDENT_VERIFICATION.json').write_text(json.dumps(ver,indent=2));print(json.dumps(ver,indent=2))
