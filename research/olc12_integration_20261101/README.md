# OLC12 — research integration, not a promoted trading strategy

Read REPORT_IT.md and protocol references before interpreting any numbers.
No new base predictor is trained. Frozen OLC11 annual OOF regressors/classifiers and Return125 RSI form the inputs. META2/META3 are 24 small yearly combinations trained only on completed past OOF groups. PRIMARY comparisons are task-native; complete strategy replays are a separate integration check.

## Reproduce from the delivered prepared inputs

Python3.13, numpy2.3.5, pandas2.2.3, scipy1.17.0, scikit-learn1.8.0; full environment recorded.

    python -m pytest -q
    python src/evaluate_layers.py
    python src/run_portfolios.py
    python src/run_meta.py
    python src/analyze.py
    python src/verify.py

The checkpoint contains inputs, original numerical oracles, all new code, meta-model parameters, all212 curves and ledgers. No network/price download is needed for these commands. Source `prepare.py` regenerates portable inputs from the authenticated full OLC11/OLC06 archives and is NOT a required command for replaying this checkpoint. Those original model/raw archives are identified by hashes in SOURCE_ARCHIVES.json, not silently included or recertified.

Native target, event probability, ranking score and capital allocation remain separate. The classifier cannot increase leverage or choose cash. No strategy is promoted by selecting the largest CAGR. `INTEGRATION_REGISTRY.json` states the roles.

Saved source package on GitHub is distinct from the complete binary checkpoint in the user's Library. Main unchanged. Historical data survivorship, total-return/dividends and same-Open execution assumptions remain unresolved.
