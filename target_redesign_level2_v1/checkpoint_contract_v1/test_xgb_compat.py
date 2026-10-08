import unittest

from xgb_refresh_probe import run_synthetic_ranker_refresh_probe

class XgbRefreshSyntheticOnlyTests(unittest.TestCase):
    def test_rank_pairwise_refresh_preserves_split_structure_and_model_io(self):
        result=run_synthetic_ranker_refresh_probe()
        self.assertEqual(result['objective'], 'rank:pairwise')
        self.assertEqual(result['original_tree_count'], result['updated_tree_count'])
        self.assertTrue(result['identical_split_topology'])
        self.assertGreater(result['changed_leaf_count'],0)
        self.assertLess(result['reload_max_prediction_error'],1e-10)
        self.assertGreater(result['prediction_change_max'],0.0)
        self.assertEqual(result['n_training_rows'],result['n_refresh_rows'])

if __name__ == '__main__':unittest.main()


class XgbRealCheckpointRoundTrip(unittest.TestCase):
    def test_actual_ubj_is_saved_and_exactly_reloaded_through_contract(self):
        import tempfile
        from pathlib import Path
        import numpy as np
        import xgboost as xgb
        from checkpoint import create_checkpoint, verify_checkpoint
        rng = np.random.default_rng(123)
        X = rng.normal(size=(24,3)).astype('float32')
        y = np.tile(np.arange(6),4).astype('float32')
        dm = xgb.QuantileDMatrix(X,label=y)
        dm.set_group([6]*4)
        model = xgb.train({'objective':'rank:pairwise','tree_method':'hist',
                           'max_depth':2,'nthread':1,'seed':101},dm,num_boost_round=3)
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            model_file=root/'trained.ubj'
            model.save_model(model_file)
            feature_file=root/'features.bin'
            feature_file.write_bytes(X.tobytes())
            meta = {'cutoff':'2024-01-01','training_exit_before_cutoff':True,
                    'feature_names':['a','b','c'],'seed':101,
                    'model_parameters':{'objective':'rank:pairwise'},
                    'runtime_versions':{'xgboost':xgb.__version__},
                    'source_commit':'synthetic-only','cohort_key_hash':'synthetic-only'}
            dest=root/'ckpt'
            create_checkpoint(dest,model_file,{'features.bin':feature_file},meta)
            verify_checkpoint(dest,expected_sources={'features.bin':feature_file},expected_metadata=meta)
            reloaded=xgb.Booster(model_file=str(dest/'models'/'model.ubj'))
            np.testing.assert_allclose(model.predict(xgb.DMatrix(X)),
                                       reloaded.predict(xgb.DMatrix(X)),rtol=0,atol=0)
