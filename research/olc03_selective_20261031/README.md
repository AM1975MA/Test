# OLC03 selective veto

Read PROTOCOL.md and RESULTS_IT.md. The complete executable source bundle and all92paths are in the conversation results ZIP; the full checkpoint also restores the authenticated OLC02 parent, including32prepared inputs and72models. The small GitHub directory stores core calibration/controller code and verified summaries, not the large datasets or all diagnostics. Main is unchanged.

Parent checkpoint SHA256:8bccd2b80956f92de4094d204625d6d1a0f6e2687ef7a7770c9bf10687e83cdb. Verify internal parent manifest before loading joblib/pickle. New source bundle SHA256:4fa6300e7a5be8e8cbfb52cc28b338bfa27cba505c8fd634f73b1d5307893456. Restore parent at source/olc02_pairwise_20261031 relative to the experiment directory; do not fetch current prices.

From the complete delivery: python -m pytest -q; PYTHONPATH=src python src/run_experiment.py EU USA; PYTHONPATH=src python src/diagnose.py; PYTHONPATH=src python src/evaluate_calibration.py; PYTHONPATH=src python src/verify_outputs.py. Run in a separate copy because these regenerate outputs.

Versions:Python3.13.5,numpy2.3.5,pandas2.2.3,scipy1.17.0,sklearn1.8.0,numba0.65.1. The posterior is generalized and model-conditional, not a certified chance of investment success. Source/calibration/risk/cost limitations are in the report. Review by author only; no claim the entire historical repository suite passes.
