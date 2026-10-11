import tempfile
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from paper_ltr_v1.replay import replace_exact,assert_replay_parity,verify_cache,sha,ROOT

class ReplayTest(unittest.TestCase):
    def test_only_requested_score_replaced_with_exact_keys(self):
        original=pd.DataFrame({'signal_date':pd.to_datetime(['2020-01-31']*2),'ticker':['A','B'],'compact21':[1.,2.],'tail':[8.,9.]})
        replacement=original[['signal_date','ticker']].iloc[::-1].copy();replacement['pred']=[20.,10.]
        changed=replace_exact(original,replacement,'compact21','pred')
        np.testing.assert_array_equal(changed.compact21,[10.,20.]);pd.testing.assert_frame_equal(original.drop(columns='compact21'),changed.drop(columns='compact21'))
        with self.assertRaises(ValueError):replace_exact(original,replacement.iloc[:1],'compact21','pred')
        with self.assertRaises(ValueError):replace_exact(original,pd.concat([replacement,replacement.iloc[:1]]),'compact21','pred')

    def test_array_path_parity_catches_hidden_difference(self):
        result=dict(candidate_count=149,sessions=2,start='2020-01-01',end='2020-01-02',completed_signals=1,
                    v2_full_universe={'cagr':.2},equal_weight_buy_hold={'cagr':.1})
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);a=root/'a.npz';b=root/'b.npz';csv=root/'leaders.csv'
            pd.DataFrame({'date':['2020-01-01'],'top1':['A'],'top2':['B']}).to_csv(csv,index=False)
            np.savez(a,equity=np.array([1.,1.1]),d1=np.array([0,0]));np.savez(b,equity=np.array([1.,1.1]),d1=np.array([0,0]))
            self.assertTrue(assert_replay_parity(result,result,a,b,csv,csv)['PASS'])
            np.savez(b,equity=np.array([1.,1.1]),d1=np.array([0,1]))
            with self.assertRaises(ValueError):assert_replay_parity(result,result,a,b,csv,csv)

    def test_raw_and_cache_hashes_detect_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); raw=root/'raw';cache=root/'cache';evidence=cache/'evidence'
            raw.mkdir();evidence.mkdir(parents=True)
            (raw/'universe.csv').write_text('ticker,macro_category\nA,EQUITY\n')
            annual=evidence/'ANNUAL_PREDICTIONS.csv';annual.write_text('compact21\n0.5\n')
            contract=dict(raw_files_sha256={'universe.csv':sha(raw/'universe.csv')},
                canonical_models_sha256=sha(ROOT/'vendor/etf_trader_v2/src/etf_trader/source_only/models.py'),
                canonical_compare_sha256=sha(ROOT/'holdout70/v2_canonical_same_source_compare.py'))
            (cache/'INPUT_CONTRACT.json').write_text(json.dumps(contract))
            (cache/'RESULT_BASE.json').write_text(json.dumps({'evidence_files_sha256':{'ANNUAL_PREDICTIONS.csv':sha(annual)}}))
            self.assertTrue(verify_cache(cache,raw)[3]['cache_identity_PASS'])
            annual.write_text('compact21\n0.6\n')
            with self.assertRaises(ValueError):verify_cache(cache,raw)
            annual.write_text('compact21\n0.5\n');(raw/'universe.csv').write_text('ticker,macro_category\nB,EQUITY\n')
            with self.assertRaises(ValueError):verify_cache(cache,raw)

if __name__=='__main__':unittest.main()
