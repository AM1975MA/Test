import numpy as np,pandas as pd
from experiment import eligible,folds,counts,shuffled_context_groups

def data():
    out=[]
    for market in ['EU','USA']:
        for date in pd.date_range('2019-01-31','2023-12-31',freq='ME'):
            out.append(dict(market=market,date=date,available=date+pd.Timedelta(days=95),full=True,
                            x=np.array([date.month,date.year,0.]),u=np.array([0.,1.])))
    return out

def test_cutoff_checks_whole_outcome_group():
    g=data();p=eligible(g,'2021-01-01')
    assert all(x['date']<pd.Timestamp('2021-01-01') and x['available']<pd.Timestamp('2021-01-01') for x in p)
    assert counts(p)=={'EU':20,'USA':20}

def test_future_outcomes_do_not_change_training_membership():
    g=data();base=eligible(g,'2021-01-01')
    alt=[dict(x,u=np.array([-100.,100.])) if x['available']>=pd.Timestamp('2021-01-01') else x for x in g]
    assert [(x['market'],x['date']) for x in eligible(alt,'2021-01-01')]==[(x['market'],x['date']) for x in base]

def test_each_nested_split_is_earlier_and_mature():
    for year,tr,va in folds(data(),'2023-01-01'):
        assert all(g['available']<pd.Timestamp(year,1,1) for g in tr)
        assert all(g['date'].year==year and g['available']<pd.Timestamp('2023-01-01') for g in va)
        assert min(counts(tr).values())>=8

def test_null_only_shuffles_given_training_contexts():
    g=eligible(data(),'2021-01-01');p=shuffled_context_groups(g,1601)
    for a,b in zip(g,p):
        assert a['date']==b['date'] and a['market']==b['market']
        np.testing.assert_array_equal(a['u'],b['u'])
    for m in ['EU','USA']:
        assert sorted(tuple(x['x']) for x in g if x['market']==m)==sorted(tuple(x['x']) for x in p if x['market']==m)
