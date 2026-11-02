from pathlib import Path
import numpy as np,pandas as pd
from g2_prequential_calibration import dataset,training,weights_market_month,fit,FEATURES,OUT


def test_calendar_cutoff_and_market_balancing():
    d=dataset()
    for year in range(2021,2027):
        tr=training(d,year)
        assert tr is not None
        assert (tr.exit_date<pd.Timestamp(year,1,1)).all()
        assert (tr.signal_date<pd.Timestamp(year,1,1)).all()
        w=weights_market_month(tr)
        assert np.isclose(w.mean(),1.,atol=1e-12)
        assert np.isclose(w[tr.market=='EU'].sum()/w.sum(),.5,atol=1e-12)
        assert np.isclose(w[tr.market=='USA'].sum()/w.sum(),.5,atol=1e-12)


def test_future_price_mutation_never_affects_prior_fit():
    d=dataset();train=training(d,2023)
    data=d.copy()
    m=data.signal_date>=pd.Timestamp('2023-01-01')
    data.loc[m,'r_abs_bp']=1e8
    data.loc[m,'r_rel_bp']=-1e8
    clean=training(data,2023)
    pd.testing.assert_frame_equal(train,clean)
    s1,f1=fit(train,FEATURES,'r_rel_bp')
    s2,f2=fit(clean,FEATURES,'r_rel_bp')
    assert np.array_equal(f1.coef_,f2.coef_)
    assert f1.intercept_==f2.intercept_
    assert np.array_equal(s1.mean_,s2.mean_)


def test_monthly_output_is_invariant_to_row_order():
    d=dataset()
    t=training(d,2024)
    shuffled=t.sample(frac=1,random_state=204)
    w1=weights_market_month(t)
    w2=weights_market_month(shuffled)
    k1=t.assign(weight=w1).set_index(['market','signal_date','ticker']).weight.sort_index()
    k2=shuffled.assign(weight=w2).set_index(['market','signal_date','ticker']).weight.sort_index()
    assert np.array_equal(k1.to_numpy(),k2.to_numpy())


def test_paired_variants_keep_identical_forecast_support():
    d=pd.read_csv(OUT/'10_G2_ALL_OOF_PREDICTIONS.csv.gz')
    import json
    m=json.loads((OUT/"14_G2_FIT_AUDIT.json").read_text())
    assert len(d)==sum(x["test_rows"] for x in m["years"])
    for t in ['r_abs_bp','r_rel_bp']:
        assert d[f'{t}_B1'].notna().equals(d[f'{t}_B2'].notna())
    assert not d.duplicated(['market','signal_date','ticker']).any()


def test_main_summary_matches_independent_groupby_calculation():
    d=pd.read_csv(OUT/'10_G2_ALL_OOF_PREDICTIONS.csv.gz',parse_dates=['signal_date'])
    s=pd.read_csv(OUT/'12_G2_MATCHED_LOSS_SUMMARY.csv')
    d=d[(d.signal_date.dt.year>=2021)&(d.signal_date.dt.year<=2024)]
    for market in ['EU','USA']:
        m=d[d.market==market]
        for t in ['r_rel_bp','r_abs_bp']:
            for method in ['B1','B2']:
                er=(m[t]-m[f'{t}_{method}'])**2
                monthly=er.groupby(m.signal_date).mean()
                actual=monthly.mean()
                recorded=s[(s.period=='MAIN2021_2024')&(s.market==market)].iloc[0][f'{t}_{method}_sqerr']
                assert abs(actual-recorded)<1e-8
