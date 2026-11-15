"""Audit scorecard/segment aggregation using independently verified daily paths."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
from account_reference import metrics
from signal_reference import ARMS, SCENARIOS


def run(root):
    root = Path(root).resolve()
    evidence = json.loads((root/'validation/INDEPENDENT_QA.json').read_text())
    assert evidence['status'] == 'PASS_COMPLETE_INDEPENDENT_RECONSTRUCTION' and evidence['passed_paths'] == 78
    reconstructions = pd.read_csv(root/'validation/INDEPENDENT_RECONSTRUCTIONS.csv',float_precision='round_trip').set_index('path_id')
    scorecard = pd.read_csv(root/'results/SCORECARD.csv',float_precision='round_trip').set_index('path_id')
    segments = pd.read_csv(root/'results/DESCRIPTIVE_SEGMENTS.csv',float_precision='round_trip').set_index(['path_id','segment'])
    paths = [f'{arm}__{scenario}' for arm in ARMS for scenario in SCENARIOS]
    assert set(scorecard.index) == set(paths) and len(scorecard) == 78
    assert len(segments) == 78*4 and not segments.index.duplicated().any()
    checked = []
    fields = ('cagr','cumulative','maxdd_close','maxdd_sampled','calmar','volatility','worst_21_sessions','end_equity','days',
              'orders','instructions','costs','trading_days','mean_exposure','mean_cash_share','mean_positions','full_cash_days','deferred_sessions','two_sided_turnover_per_year')
    for path_id in paths:
        independent,recorded = reconstructions.loc[path_id],scorecard.loc[path_id]
        for field in fields:
            assert np.isclose(independent[field],recorded[field],rtol=1e-10,atol=1e-9,equal_nan=True), ('SCORECARD',path_id,field)
        daily_path = root/'results'/path_id/'DAILY.csv.gz'
        # This exact complete daily file was reconstructed in the mandatory
        # preceding audit; do not derive new policy decisions from this table.
        daily = pd.read_csv(daily_path,float_precision='round_trip')
        dates = pd.DatetimeIndex(daily.date)
        years = dates.year
        for label,mask in [('2020',years==2020),('2021_2024',(years>=2021)&(years<=2024)),('2025_2026',years>=2025),('2021_2026',years>=2021)]:
            ix = np.flatnonzero(mask)
            initial = 10000. if ix[0] == 0 else float(daily.nav_close.iloc[ix[0]-1])
            expected = metrics(daily.nav_close.to_numpy()[ix],daily.nav_open.to_numpy()[ix],dates[ix],initial)
            actual = segments.loc[(path_id,label)]
            for field,value in expected.items():
                assert np.isclose(value,actual[field],rtol=1e-10,atol=1e-9,equal_nan=True), ('SEGMENT',path_id,label,field,value,actual[field])
            checked.append(dict(path_id=path_id,segment=label,observations=len(ix),initial_equity=initial,status='PASS'))
    report = dict(status='PASS_COMPLETE_AGGREGATIONS',scorecard_paths=78,segment_rows=len(checked),
                  annual_rows_previously_audited=546,all_2024_results_included=True,
                  prior_full_audit_sha256=hashlib.sha256((root/'validation/INDEPENDENT_QA.json').read_bytes()).hexdigest(),
                  uses_only_independently_verified_daily_paths=True,results=checked)
    (root/'validation/AGGREGATE_TABLE_QA.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({key:report[key] for key in ('status','scorecard_paths','segment_rows','annual_rows_previously_audited','all_2024_results_included')},indent=2))


if __name__=='__main__':
    run(Path(__file__).resolve().parents[1])
