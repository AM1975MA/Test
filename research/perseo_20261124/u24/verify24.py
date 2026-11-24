from walkforward24 import *

def replay(row,q):
    name=tag(row.market,row.rule,row.bps,row.lag);z=load(OUT/f'{name}.npz');names=list(q['tickers']);lookup={t:i for i,t in enumerate(names)};cashids=np.array(['CASH_' in t for t in names])
    od=pd.read_csv(OUT/f'{name}_ORDERS.csv');sp=OUT/f'{name}_STOPS.csv';st=pd.read_csv(sp) if sp.stat().st_size>2 else pd.DataFrame()
    prices={(int(r.signal_index),r.ticker):r.fill_price for r in st.itertuples()}
    groups={int(k):v for k,v in od.groupby('index')};units=np.zeros(len(names));cash=1.;ue=ce=0.
    for k in range(len(q['dates'])-1):
        if k in groups:
            for r in groups[k].itertuples():
                j=lookup[r.ticker];price=q['O'][k,j] if r.kind=='REBALANCE' else prices[k,r.ticker]
                units[j]+=r.signed_notional_eur/10000/price;cash-=(r.signed_notional_eur+r.cost_eur)/10000
        actual=z['primary_units'][k]+z['defensive_units'][k]
        ue=max(ue,float(np.max(abs(actual[~cashids]-units[~cashids]))))
        ce=max(ce,abs(cash-float(z['free_cash'][k]+actual[cashids]@q['O'][k,cashids])))
    assert ue<1e-9 and ce<1e-9,(name,ue,ce)
    return dict(account=name,units_error=ue,cash_error=ce)

def main():
    summary=pd.read_csv(OUT/'SUMMARY.csv');audits=[];prefix=[];real=[]
    for m in MARKETS:
        q=state(m);built=signals(q,m)
        for rule in ['BASE','TRAIL_CASH','RAMP']:
            old=load(ROOT.parent/'u23'/'results'/f'{tag(m,rule,15)}.npz');new=load(OUT/f'{tag(m,rule,15)}.npz')
            assert np.array_equal(old['ledger'],new['ledger']),(m,rule,'CONTROL_MISMATCH')
        for row in summary[summary.market==m].itertuples():audits.append(replay(row,q))
        print('REPLAY',m,flush=True)
        for k in [300,900,1400]:
            alt={key:v.copy() for key,v in q.items()};alt['C'][k:]*=1.29
            changed=signals(alt,m)
            for name in RULES:assert np.array_equal(built[0][name][:k+1],changed[0][name][:k+1]),(m,name,k)
            assert np.array_equal(built[1][:k+1],changed[1][:k+1])
            prefix.append(dict(market=m,index=k,rules_checked=len(RULES),future_prices_no_effect=True))
        k=pd.DatetimeIndex(q['dates']).searchsorted('2024-06-03')
        alt={key:v.copy() for key,v in q.items()}
        for key in ['O','C','L','PC']:alt[key][k+1:]*=1.13
        for rule in ['CONFIRM_RAMP','TRAIL_FAST','PROFIT_RAMP']:
            _,r,_=run(m,rule,q=alt,save=False)
            with np.load(OUT/f'{tag(m,rule,15)}.npz') as z:assert np.array_equal(r['ledger'][:k+1,0],z['nav'][:k+1])
            real.append(dict(market=m,rule=rule,prefix_end=str(pd.Timestamp(q['dates'][k]).date()),account_invariant=True))
        base=load(INPUT/f'{m}_REFERENCE.npz');before=pd.DatetimeIndex(q['dates'])<'2022-01-01'
        for rule in ['WF_ECONOMIC','WF_PRUDENT']:
            with np.load(OUT/f'{tag(m,rule,15)}.npz') as z:assert np.array_equal(z['nav'][before],base['nav'][before])
    saved=frozen_paths();original=pd.read_csv(OUT/'WF_PLAN.csv');wf=[]
    for year in [2022,2024,2026]:
        mutant={b:{key:{kk:vv.copy() for kk,vv in vals.items()} for key,vals in lib.items()} for b,lib in saved.items()}
        for b,lib in mutant.items():
            for key,z in lib.items():z['close_nav'][pd.DatetimeIndex(z['dates'])>=f'{year}-01-01']*=1.53
        plans=choose(mutant,save=False)
        pd.testing.assert_frame_equal(plans[plans.year<=year].reset_index(drop=True),original[original.year<=year].reset_index(drop=True))
        wf.append(dict(cutoff=f'{year}-01-01',plans_unchanged=True))
    cut=pd.read_csv(OUT/'WF_INPUT_CUTOFFS.csv');assert (cut.last_input<cut.cutoff).all()
    qa=dict(status='PASS',baseline_bitwise_accounts=3, u23_control_bitwise_accounts=9,independent_replays=audits,new_signal_prefix_checks=prefix,actual_account_checks=real,annual_selection_checks=wf,annual_cutoffs=len(cut),wf_initial_path_parity=6,scope='New transformations and accounting; does not certify upstream data, catalogues or frozen rankings')
    (OUT/'QA.json').write_text(json.dumps(qa,indent=2));print('QA_PASS',len(audits),flush=True)

if __name__=='__main__':main()
