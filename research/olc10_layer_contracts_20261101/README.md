# OLC10 — layer-native integration and evaluation
Read REPORT_IT.md and LAYER_CONTRACTS.json. Research only, no main edit or trading.
The checkpoint reproduces the new layer diagnostics and24small annual calibrator fits from saved genuine OOF forecasts. It is NOT a raw-data reproduction of the parent strategy's base-model training.

Python3.13.5,numpy2.3.5,pandas2.2.3,scipy1.17.0,scikit-learn1.8.0,pytest. Complete environment in ENVIRONMENT.txt.

From the extracted root:
python -m pytest -q
python src/run_experiment.py
python src/diagnose_composition.py
python src/verify_results.py
python src/verify_labels.py
python src/uncertainty.py

No network is used. Files in inputs/ are authenticated source extracts. CSVs are read with float_precision='round_trip'. True targets, endpoint dates, calibration parameters and monthly contributions are inspectable. Inherited large panel/model archives are identified in checkpoints/01_INTEGRATION.json; optional original matrix reconstruction requires those dependencies.

Default native ranking is unchanged. Expected Hybrid target is not a success probability and calibration is NOT silently substituted into the strategy. Source/analysis failure logs are retained. GitHub and persistent Library are distinct destinations.
