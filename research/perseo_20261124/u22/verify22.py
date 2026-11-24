from run22 import *

def replay(m,rule,bps,q):
    tag=f'{m}_{rule}_{bps}';z=load(OUT/f'{tag}.npz');names=list(q['tickers']);cashids=np.array(['CASH_' in t for t in names])
    od=pd.read_csv(OUT/f'{tag}_ORDERS.csv');st=pd.read_csv(OUT/f'{tag}_STOPS.csv')
    prices={(int(r.signal_index),r.ticker):float(r.fill_price) for r in st.itertuples()}
    groups={int(k):v for k,v in od.groupby('index')};held=np.zeros(len(names));cash=1.;err=0.;cerr=0.
    for k in range(len(q['dates'])-1):
        if k in groups:
            for row in groups[k].itertuples():
                j=names.index(row.ticker);price=q['O'][k,j] if row.kind=='REBALANCE' else prices[k,row.ticker]
                held[j]+=row.signed_notional_eur/10000/price
                cash-=(row.signed_notional_eur+row.cost_eur)/10000
        actual=z['primary_units'][k]+z['defensive_units'][k]
        err=max(err,float(np.max(abs(held[~cashids]-actual[~cashids]))))
        actualcash=z['free_cash'][k]+float(actual[cashids]@q['O'][k,cashids])
        cerr=max(cerr,abs(cash-actualcash))
    assert err<1e-9 and cerr<1e-9,(tag,err,cerr)
    return dict(account=tag,unit_error=err,cash_error=cerr)

def main():
    models=json.loads((OUT/'MODELS.json').read_text());rows=pd.read_csv(OUT/'TRAINING_PAIRS.csv',float_precision='round_trip')
    fits=[]
    for year in [2023,2024,2026]:
        mutant=rows.copy();mutant.loc[mutant.exit_date>=f'{year}-01-01','y']+=.37
        alt=fit_models(mutant,save=False)
        for yy in range(2020,year+1):assert models[str(yy)]==alt[str(yy)]
        fits.append(dict(cutoff=f'{year}-01-01',future_label_invariance=True))
    audited=[];prefix=[];first=[]
    for m in MARKETS:
        q=state(m);f=features(q)
        for rule in RULES:
            for bps in [15,30]:audited.append(replay(m,rule,bps,q))
        for k in [700,1100,1450]:
            alt={key:value.copy() for key,value in q.items()};alt['C'][k:]*=1.31
            f2=features(alt);assert np.array_equal(f[:k+1],f2[:k+1],equal_nan=True)
            prefix.append(dict(market=m,index=k,prior_close_features=True))
        # Run the actual new policy after mutating future bars and features.
        k=pd.DatetimeIndex(q['dates']).searchsorted('2024-06-03')
        alt={key:value.copy() for key,value in q.items()}
        for key in ['O','C','PC','L']:alt[key][k+1:]*=1.17
        _,r,d=run(m,'LCB21',15,models,q=alt,save=False)
        old=load(OUT/f'{m}_LCB21_15.npz')
        assert np.array_equal(r['ledger'][:k+1,0],old['nav'][:k+1])
        olddec=pd.read_csv(OUT/f'{m}_LCB21_15_DECISIONS.csv');a=d[d['index']<=k].reset_index(drop=True);b=olddec[olddec['index']<=k].reset_index(drop=True)
        pd.testing.assert_frame_equal(a,b,check_dtype=False,rtol=1e-13,atol=1e-13)
        assert (olddec.last_exit<olddec.date.str[:4]+'-01-01').all()
        assert (olddec.last_input<olddec.date).all()
        first.append(dict(market=m,first_economic_review=olddec.date.min(),all_cutoffs_valid=True))
        prefix.append(dict(market=m,index=int(k),actual_account_future_invariance=True))
    result=dict(status='PASS',baseline_bitwise_parity=3,independent_accounts=audited,training_cutoffs=fits,price_invariance=prefix,first_reviews=first,scope='New economic admission and accounting; no certification of upstream data/forecasts')
    (OUT/'QA.json').write_text(json.dumps(result,indent=2));print('QA_PASS',len(audited),len(prefix),flush=True)

if __name__=='__main__':main()
