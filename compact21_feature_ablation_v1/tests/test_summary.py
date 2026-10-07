"""Scientific controls for the ablation summary's most dangerous shortcuts."""
from __future__ import annotations

import unittest

from compact21_feature_ablation_v1.summarize import YEARS, check_complete_matrix
from compact21_feature_ablation_v1.variants import MASKS, mask_manifest, FEATURES


class SummaryContractTests(unittest.TestCase):
    def test_complete_year_variant_grid_rejects_missing_and_extra_identity(self):
        full = {(variant, year): object() for variant in MASKS for year in YEARS}
        self.assertIsNone(check_complete_matrix(full))
        incomplete = full.copy()
        del incomplete['DOWNVOL9', 2017]
        with self.assertRaisesRegex(ValueError, 'Incomplete ablation matrix'):
            check_complete_matrix(incomplete)
        extra = full.copy()
        extra['UNREGISTERED', 2020] = object()
        with self.assertRaisesRegex(ValueError, 'Incomplete ablation matrix'):
            check_complete_matrix(extra)


    def test_mask_registry_is_exhaustive_and_ordered(self):
        manifest = mask_manifest()
        self.assertEqual(tuple(manifest), tuple(MASKS))
        self.assertEqual(len(FEATURES), 125)
        self.assertEqual([manifest[name]['retained_count'] for name in MASKS], [116, 92, 79, 103])
        for name, columns in MASKS.items():
            self.assertEqual(manifest[name]['masked_columns'], list(columns))
            self.assertEqual(len(columns), len(set(columns)))
            self.assertTrue(set(columns).issubset(FEATURES))


if __name__ == '__main__':
    unittest.main()
