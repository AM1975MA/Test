import unittest

import numpy as np
import pandas as pd

from compact21_feature_ablation_v1.run import masked
from compact21_feature_ablation_v1.variants import FEATURES, MASKS, mask_manifest


class FeatureAblationProtocolTest(unittest.TestCase):
    def test_masks_are_fixed_and_within_original_schema(self):
        manifest = mask_manifest()
        self.assertEqual([len(MASKS[k]) for k in MASKS], [9, 33, 46, 22])
        self.assertEqual(len(FEATURES), 125)
        self.assertEqual(len({manifest[k]["masked_columns_sha256"] for k in MASKS}), 4)

    def test_mask_preserves_keys_labels_and_other_features(self):
        frame = pd.DataFrame({"signal_date": pd.to_datetime(["2021-01-01", "2021-02-01"]),
                              "ticker": ["AAA", "BBB"], "target_rank_21": [0.4, 0.8],
                              "exit_date_21": pd.to_datetime(["2021-02-01", "2021-03-01"]),
                              "mom5": [0.01, 0.02], "downvol21": [0.03, np.nan]})
        result = masked(frame, ("downvol21",))
        pd.testing.assert_frame_equal(result.drop(columns="downvol21"), frame.drop(columns="downvol21"))
        self.assertTrue(result.downvol21.isna().all())
        self.assertTrue(frame.downvol21.notna().any())


if __name__ == "__main__":
    unittest.main()
