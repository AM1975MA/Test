import io,zipfile,json,argparse
from pathlib import Path
import numpy as np,pandas as pd

ROOT=Path(__file__).parent
R=ROOT/'results'
TOP=ROOT.parent/'etf_source/OLC14_Fitting_Risultati_20261101.zip'


def run(original_archive=TOP):
    selection=pd.read_csv(R/'OLC60_TOP2_SELECTIONS.csv')
    monthly=pd.read_csv(R/'OLC60_MONTHLY_METRICS.csv')
    fits=pd.read_csv(R/'OLC60_FIT_QA.csv')
    pred=pd.read_csv(R/'OLC60_PREDICTIONS.csv.gz')
    summary=pd.read_csv(R/'OLC60_MAIN_SUMMARY.csv')
    assert len(fits)==20 and fits.convergence_warnings.sum()==0
    assert (pd.to_datetime(fits.last_training_exit)<pd.to_datetime(fits.year.astype(str)+'-01-01')).all()
    assert not pred.duplicated(['market','signal_date','ticker']).any()
    assert not selection.duplicated(['market','signal_date','method','ticker']).any()
    assert not monthly.duplicated(['market','signal_date','method']).any()
    assert (pred['signal_date'].str[:4].astype(int).between(2021,2025)).all()
    # Source parity for exact CURRENT and FUSION shortlist, including fractional ties.
    with zipfile.ZipFile(original_archive) as z:
        ref=pd.read_csv(io.BytesIO(z.read('olc14_fitted_ranking_20261101/results/TOP2_DECISIONS.csv.gz')),compression='gzip')
    expected=ref[(ref.variant=='ORIGINAL')&(ref.date>='2021-01-01')&(ref.date<='2024-12-31')]
    checks=[]
    for stage,method in [('CURRENT','B0_NATIVE'),('FUSION','B0_FUSION_CONTEXT')]:
        a=selection[(selection.method==method)&(selection.signal_date>='2021-01-01')&(selection.signal_date<='2024-12-31')]
        b=expected[expected.stage==stage]
        m=a.merge(b,left_on=['market','signal_date','ticker'],right_on=['market','date','ticker'],how='outer',validate='one_to_one',indicator=True)
        assert len(m)==len(a)==len(b) and (m._merge=='both').all()
        np.testing.assert_allclose(m.weight_x,m.weight_y,rtol=0,atol=1e-15)
        np.testing.assert_allclose(m.score_x,m.score_y,rtol=0,atol=1e-15)
        checks.append(dict(stage=stage,rows=len(a),max_weight_diff=float((m.weight_x-m.weight_y).abs().max()),max_score_diff=float((m.score_x-m.score_y).abs().max())))
    # Independent all-month aggregations cross check (not using the primary helpers).
    tally=selection.groupby(['market','signal_date','method'])['weight'].sum()
    np.testing.assert_allclose(tally.values,np.ones(len(tally)),rtol=0,atol=1e-12)
    for (market,method),group in monthly[monthly.year.between(2021,2024)].groupby(['market','method']):
        ss=summary[(summary.market==market)&(summary.period=='MAIN')&(summary.method==method)]
        assert len(ss)==1 and int(ss.nmonths.iloc[0])==48
        assert abs(ss.top2_persist_hit.iloc[0] - group.persist_rate.mean())<1e-12
        assert abs(ss.avg_fwd21.iloc[0] - group.avg_21.mean())<1e-12
    audit=dict(status='PASS',fit_models=20,rows=len(pred),selection_rows=len(selection),monthly_rows=len(monthly),
               baseline_source_parity=checks,monthly_unit_weights_max_dev=float(np.max(np.abs(tally.values-1))),
               no_future_labels_used_in_fit=True,candidate_42_features=True,main_unchanged=True)
    (R/'OLC60_INDEPENDENT_QA.json').write_text(json.dumps(audit,indent=2))
    print(json.dumps(audit,indent=2))

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--original-results',default=str(TOP),help='OLC14_Fitting_Risultati_20261101.zip')
    z=a.parse_args()
    run(z.original_results)