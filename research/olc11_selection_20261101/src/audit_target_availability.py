"""Demonstrate availability of a cross-sectional target, not only its own outcome."""
from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
from prepare import readcsv
from recovery_core import atomic_json
ROOT=Path(__file__).resolve().parents[1]

def changed_count(rows):
    return int(sum(r['max_change']>1e-14 for r in rows))

def main():
    rows=[];cohorts=[]
    for market in ['EU','USA']:
        f=readcsv(ROOT/'inputs'/f'{market}_LAYER_LABELS.csv.gz')
        for year in range(2019,2027):
            cut=pd.Timestamp(year,1,1)
            old=(f.signal_date<cut)&(f.exit_date_63<cut)&np.isfinite(f.TARGET)
            for date,g in f[f.signal_date<cut].groupby('signal_date'):
                unknown=(g.exit_date_63>=cut)&np.isfinite(g.fwd_ret_63)
                chosen=old.loc[g.index]
                if not unknown.any() or not chosen.any():continue
                # Reconstruct the source target before perturbation.
                ranks={h:g[f'fwd_ret_{h}'].rank(pct=True) for h in [21,42,63]}
                y0=.45*ranks[21]**1.5+.35*ranks[42]**1.5+.2*ranks[63]**1.5
                np.testing.assert_allclose(y0,g.TARGET,rtol=0,atol=1e-14,equal_nan=True)
                future=g.fwd_ret_63.copy();future.loc[unknown]=-0.95
                low=.45*ranks[21]**1.5+.35*ranks[42]**1.5+.2*future.rank(pct=True)**1.5
                future.loc[unknown]=max(1.,float(g.fwd_ret_63.max())+1.)
                high=.45*ranks[21]**1.5+.35*ranks[42]**1.5+.2*future.rank(pct=True)**1.5
                diff=np.maximum(abs(low-y0),abs(high-y0))
                for idx,row in g[chosen].iterrows():
                    rows.append({'market':market,'fit_year':year,'signal_date':str(date.date()),'ticker':row.ticker,'own_exit_63':str(row.exit_date_63.date()),'cohort_last_exit_63':str(g.exit_date_63.max().date()),'target_original':row.TARGET,'target_future_low':low.loc[idx],'target_future_high':high.loc[idx],'max_change':diff.loc[idx]})
                cohorts.append({'market':market,'fit_year':year,'signal_date':str(date.date()),'prematurely_accepted_rows':int(chosen.sum()),'unmatured_peers':int(unknown.sum()),'max_change':float(diff.loc[chosen].max())})
    pd.DataFrame(rows).to_csv(ROOT/'results/TARGET_AVAILABILITY_ROWS.csv',index=False)
    atomic_json(ROOT/'results/TARGET_AVAILABILITY_AUDIT.json',{'scope':'Original per-row maturity of Hybrid relative target; no claim about other pipelines','cohorts':cohorts,'affected_rows':len(rows),'rows_changed_by_future_only_perturbation':changed_count(rows),'candidate_contract':'All OLC11 new arms use complete cohorts whose latest exit is before cutoff, so none of these rows are accepted until complete. Missing historical cohorts are a separate exclusion, not all called leakage.','no_new_fits':True})
    print(json.dumps(cohorts,indent=2));print('AFFECTED',len(rows))
if __name__=='__main__':main()
