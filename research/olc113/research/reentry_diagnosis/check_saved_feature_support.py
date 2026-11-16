"""Supplement saved-head diagnostics; no fits and no policy-return replays."""
import gzip
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True
from diagnose_saved_reentry import ROOT, OUT, load_model, native, read_npz, describe


def run():
    details = pd.read_csv(OUT/'CASH_DECISION_DETAILS.csv',float_precision='round_trip')
    bank = read_npz(ROOT/'olc111/data/BANK_ENTRY.npz')
    cboe = read_npz(ROOT/'olc111/data/CBOE_ALIGNED.npz')
    selections = read_npz(ROOT/'olc111/data/CAUSAL_SELECTIONS.npz')
    panel = read_npz(ROOT/'olc110/source/data/XETRA_EUR_ETF.npz')
    names = ['fresh_nm21','fresh_nm63','fresh_log_vol21_over_vol63','breadth63',
             'sessions_to_next_month_div21']
    cache = {}
    def model(cutoff, arm):
        key = (cutoff, arm)
        if key not in cache:
            raw = json.loads(gzip.decompress((ROOT/f'olc111/results/FITS/FIT_{cutoff:06d}.json.gz').read_bytes()))
            m = load_model(raw['heads']['ENTRY']['models'][arm])
            rows = np.flatnonzero(bank['terminal_idx'] < cutoff)
            train = np.array([m._prediction_vector(bank['Xprice'][i],bank['Xlegacy'][i],bank['Xterm'][i])
                              for i in rows])
            cache[key] = (m, train)
        return cache[key]
    support = []
    for path_id, start in [('PRICE_ROTATION__NEXT_CLOSE',1606),('TERM_ROTATION__NEXT_CLOSE',1627)]:
        frame = details.loc[(details.path_id==path_id)&(details.k>=start)&(details.k<=1820)]
        rows=[]
        for r in frame.itertuples():
            arm='PRICE' if path_id.startswith('PRICE') or r.fallback_price else 'TERM'
            m, train=model(int(r.cutoff),arm)
            vector=m._prediction_vector(np.array([getattr(r,f) for f in names]),cboe['legacy'][r.k],cboe['term'][r.k])
            z=vector[1:]
            outside=(vector<train.min(axis=0))|(vector>train.max(axis=0))
            rows.append(dict(date=r.date,k=r.k,model_arm=arm,max_abs_all_z=float(np.max(np.abs(z))),
                             outside_any_representation_range=bool(outside.any()),
                             price_max_abs_z=float(np.max(np.abs(z[:5]))),
                             option_max_abs_z=float(np.max(np.abs(z[5:]))) if len(z)>5 else 0.))
        rframe=pd.DataFrame(rows)
        support.append(dict(path_id=path_id,rows=len(rframe),all_representation_max_abs_z=describe(rframe.max_abs_all_z),
                            dates_above_3=int((rframe.max_abs_all_z>3).sum()),
                            dates_above_5=int((rframe.max_abs_all_z>5).sum()),
                            outside_any_representation_range=int(rframe.outside_any_representation_range.sum()),
                            options_max_abs_z=describe(rframe.option_max_abs_z)))
        rframe.to_csv(OUT/f'{path_id}_FULL_FEATURE_SUPPORT.csv',index=False)
    crossings=[]
    for arm in ['PRICE','VIX','TERM']:
        for cutoff in [1798,1820]:
            m,_=model(cutoff,arm)
            for k in [1819,1820]:
                row=details.loc[(details.path_id=='PRICE_ROTATION__NEXT_CLOSE')&(details.k==k)].iloc[0]
                prediction=m.predict(row[names].to_numpy(float),cboe['legacy'][k],cboe['term'][k])
                crossings.append(dict(arm=arm,fit_cutoff=cutoff,feature_idx=k,date=row.date,
                    future_model_on_prior_state=cutoff>k,**prediction))
    # The new model on the previous day's features is an explanatory decomposition,
    # explicitly hindsight, never a historical recommendation or policy replay.
    candidates=[]
    for k in [1819,1820]:
        target=selections['targets'][k]
        candidates.append(dict(k=k,date=str(pd.Timestamp(panel['dates'][k]).date()),
            weights={str(panel['names'][j]):float(target[j]) for j in np.flatnonzero(target)}))
    output=dict(full_feature_support=support,final_crossing=crossings,candidate_change=candidates,
        candidate_change_l1=float(np.abs(selections['targets'][1820]-selections['targets'][1819]).sum()),
        unsupported_vix_dates=['2023-12-04','2023-12-05','2023-12-06'],
        unsupported_vix_mechanism='breadth63 is missing on all three dates; fresh candidate gross remains 1 with two holdings',
        no_refit=True,no_policy_replay=True)
    (OUT/'SUPPLEMENTARY_DIAGNOSTICS.json').write_text(json.dumps(native(output),indent=2,allow_nan=False)+'\n')
    print(json.dumps(native(output),indent=2))


if __name__=='__main__':
    run()
