"""Evidence handling failures must never turn into successful replay gates."""
import json
from pathlib import Path
import tempfile
import unittest

from compact21_stability_v1.summarize_full import disagreement, summarize


class FullSummaryEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for variant in ("BASE", "Q4", "Q4_LEGACY"):
            for repeat in (1, 2, 3):
                folder = self.root / f"compact21-full-{variant}-r{repeat}"
                folder.mkdir()
                result = {
                    "sessions": 2, "start": "2020-01-02", "end": "2020-01-03",
                    "candidate_count": 149, "completed_signals": 1,
                    "v2_full_universe": {"cagr": .3 + repeat * (.01 if variant == "BASE" else .005),
                                         "maxdd": -.2, "sharpe": 1.1, "annualized_turnover": 13},
                    "source_only": {**{key: "a" * 64 for key in ("titanium_full_sha256", "titanium_candidates_sha256", "predictions_sha256", "ma3_panel_sha256")},
                                    "historical_scores_consumed": False, "historical_paths_consumed": False},
                    "stability": {"variant": variant, "maturity_all": True,
                                  "negative_feedback_changed": False,
                                  "compact63_mean_prediction_sha256": {"2020": "a" * 64},
                                  "transforms": [{"year": 2020, "horizons": {h: {
                                      "fit_cutoff": "2020-01-01", "max_signal": "2019-11-30",
                                      "max_exit": "2019-12-31", "maturity_ok": True} for h in ("21", "63")}}]},
                }
                contract = {"variant": variant, "canonical_models_sha256": "a" * 64,
                            "canonical_compare_sha256": "b" * 64, "raw_files_sha256": {"A.csv": "c" * 64},
                            "negative_feedback_changed": False, "CAGR_used_for_selection": False}
                (folder / f"RESULT_{variant}.json").write_text(json.dumps(result))
                (folder / "INPUT_CONTRACT.json").write_text(json.dumps(contract))
                (folder / f"DAILY_LEADERS_{variant}.csv").write_text("date,top1,top2\n2020-01-02,A,B\n2020-01-03,A,B\n")

    def tearDown(self):
        self.temporary.cleanup()

    def mutate(self, edit):
        path = self.root / "compact21-full-Q4-r1" / "RESULT_Q4.json"
        data = json.loads(path.read_text())
        edit(data)
        path.write_text(json.dumps(data))

    def test_complete_comparison_preserves_all_outcomes(self):
        result = summarize(self.root)
        self.assertTrue(result["models"]["Q4"]["comparison_to_new_BASE"]["ECONOMIC_ROBUSTNESS_GATE_PASS"])
        self.assertTrue(result["models"]["BASE"]["ALL_EVIDENCE_PASS"])
        self.assertEqual(set(result["models"]), {"BASE", "Q4", "Q4_LEGACY"})
        self.assertFalse(result["production_adoption"])

    def test_source_consumption_rejects_gate_but_retains_result(self):
        self.mutate(lambda q: q["source_only"].update(historical_scores_consumed=True))
        result = summarize(self.root)
        self.assertFalse(result["models"]["Q4"]["comparison_to_new_BASE"]["ECONOMIC_ROBUSTNESS_GATE_PASS"])
        self.assertIn("Q4", result["models"])

    def test_immature_exit_rejects_gate(self):
        self.mutate(lambda q: q["stability"]["transforms"][0]["horizons"]["21"].update(max_exit="2020-01-01"))
        self.assertFalse(summarize(self.root)["models"]["Q4"]["ALL_EVIDENCE_PASS"])

    def test_coverage_loss_fails_closed(self):
        path = self.root / "compact21-full-Q4-r1" / "DAILY_LEADERS_Q4.csv"
        path.write_text("date,top1,top2\n2020-01-02,A,B\n")
        with self.assertRaisesRegex(ValueError, "coverage"):
            summarize(self.root)

    def test_missing_result_fails_closed(self):
        (self.root / "compact21-full-Q4-r3" / "RESULT_Q4.json").unlink()
        with self.assertRaisesRegex(ValueError, "Incomplete"):
            summarize(self.root)

    def test_nonfinite_metric_fails_closed(self):
        self.mutate(lambda q: q["v2_full_universe"].update(cagr=float("nan")))
        with self.assertRaisesRegex(ValueError, "Nonfinite JSON"):
            summarize(self.root)

    def test_benchmark_matrix_prevents_missing_challenger(self):
        path = self.root / "benchmark.json"
        path.write_text(json.dumps({"full_matrix": {"include": [
            {"variant": v, "repeat": i} for v in ("BASE", "Q4", "Q4_LEGACY", "SCALE") for i in (1, 2, 3)]}}))
        with self.assertRaisesRegex(ValueError, "advancement matrix"):
            summarize(self.root, benchmark_summary=path)

    def test_disagreement_rejects_silent_inner_join(self):
        with self.assertRaises(ValueError):
            disagreement({"2020-01-01": ("A", "B")}, {"2020-01-02": ("A", "B")})


if __name__ == "__main__":
    unittest.main()
