import json
import tempfile
import unittest
from pathlib import Path

from checkpoint import create_checkpoint, verify_checkpoint, CheckpointError


class CheckpointContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "prices.csv"
        self.raw.write_bytes(b"Date,Close\n2020-01-02,100\n")
        self.grouping = self.root / "grouping.json"
        self.grouping.write_bytes(b"[3,2]")
        self.model = self.root / "model.ubj"
        self.model.write_bytes(b"a fake test-only model")
        self.metadata = {
            "cutoff": "2020-01-01", "training_exit_before_cutoff": True,
            "feature_names": ["mom21", "vol63"], "seed": 101,
            "model_parameters": {"objective": "rank:pairwise", "n_estimators": 360},
            "runtime_versions": {"python": "3.13.5", "xgboost": "3.1.3"},
            "source_commit": "test-hash", "cohort_key_hash": "dummy-test-key"
        }
        self.sources = {"adjusted_prices.csv": self.raw, "groups.json": self.grouping}
        self.dest = self.root / "ckpt"

    def create(self):
        return create_checkpoint(self.dest, self.model, self.sources, self.metadata)

    def test_create_and_verify_full_model_and_sources(self):
        manifest = self.create()
        observed = verify_checkpoint(self.dest, expected_sources=self.sources,
                                     expected_metadata=self.metadata)
        self.assertEqual(manifest, observed)
        self.assertEqual((self.dest / "models" / "model.ubj").read_bytes(), self.model.read_bytes())
        self.assertEqual((self.dest / "sources" / "adjusted_prices.csv").read_bytes(), self.raw.read_bytes())
        self.assertEqual(observed["metadata"]["cutoff"], "2020-01-01")

    def test_reject_changed_historical_data_even_when_checkpoint_is_valid(self):
        self.create()
        self.raw.write_bytes(b"Date,Close\n2020-01-02,100.00001\n")
        with self.assertRaisesRegex(CheckpointError, "source mismatch"):
            verify_checkpoint(self.dest, expected_sources=self.sources)
        self.assertIsNotNone(verify_checkpoint(self.dest))

    def test_reject_corrupted_saved_model(self):
        self.create()
        (self.dest / "models" / "model.ubj").write_bytes(b"tampered")
        with self.assertRaisesRegex(CheckpointError, "digest mismatch"):
            verify_checkpoint(self.dest)

    def test_reject_corrupted_manifest(self):
        self.create()
        manifest = self.dest / "manifest.json"
        info = json.loads(manifest.read_text())
        info["metadata"]["seed"] = 999
        manifest.write_text(json.dumps(info))
        with self.assertRaisesRegex(CheckpointError, "manifest checksum mismatch"):
            verify_checkpoint(self.dest)

    def test_reject_existing_checkpoint_without_modification(self):
        self.create()
        before = (self.dest / "manifest.json").read_bytes()
        with self.assertRaisesRegex(CheckpointError, "exists"):
            self.create()
        self.assertEqual((self.dest / "manifest.json").read_bytes(), before)

    def test_reject_unsafe_asset_names(self):
        with self.assertRaises(CheckpointError):
            create_checkpoint(self.dest, self.model, {"../escape.csv": self.raw}, self.metadata)
        self.assertFalse(self.dest.exists())

    def test_reject_incomplete_contract(self):
        meta = dict(self.metadata)
        meta.pop("training_exit_before_cutoff")
        with self.assertRaisesRegex(CheckpointError, "missing metadata"):
            create_checkpoint(self.dest, self.model, self.sources, meta)
        self.assertFalse(self.dest.exists())

    def test_reject_changed_parameters_even_if_source_bytes_identical(self):
        self.create()
        different = dict(self.metadata)
        different["model_parameters"] = {"objective":"rank:pairwise", "n_estimators": 361}
        with self.assertRaisesRegex(CheckpointError, "metadata mismatch"):
            verify_checkpoint(self.dest, expected_metadata=different)


if __name__ == "__main__":
    unittest.main()
