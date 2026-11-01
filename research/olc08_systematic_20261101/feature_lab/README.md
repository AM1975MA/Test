# OLC08-F feature laboratory

Read RESULTS_IT.md and the immutable protocols before using outputs. The work changes first-layer feature representations only, preserving parent labels, annual training keys, parameters and portfolio mechanics. Research only, no main edits and no production promotion.

## Complete checkpoint

The final checkpoint contains all new source/tests/model files, generated features,180paths and the actual authenticated parent dependencies. Extract into a directory, run `python RESTORE_LAYOUT.py`, then set `OLC08F_ROOT` to that directory. The script repairs only the internal legacy symlink; it neither downloads data nor trains. Do not load pickles/joblib from an unverified or unknown archive.

Intermediate checkpoints01/02/03 have narrower scope and dependencies as stated in their manifests. A manifest registered onGitHub is not an upload of its referenced Library archive. Large binary archives remain in the authorized Library unless a remote release hash explicitly verifies them.

## Commands

    python -m pytest -q tests
    python src/build_features.py
    python src/train_pack.py --workers 4
    python src/replay_pack.py --variants LEGACY,REF_RSI,R_NO_LIQ,R_RANK46,R_PRUNE,R_PATH,R_SESSION,R_LEADERSHIP,R_ALL,R_PRUNE_ALL,H_UNIQUE,H_PATH,H_SESSION
    python src/analyze_pack.py
    python src/verify_outputs.py

Declared post-result diagnostic experiments:

    python src/null_path_diagnostic.py
    python src/replay_nulls.py
    python src/path_interaction.py
    python src/replay_interaction.py
    python src/final_evidence.py

Training runners reuse only a complete checkpoint whose input/code/model hashes match; otherwise they train. Never change features and silently reuse old predictions. Path analyses preserve legacy fees, frozen V6/risk and known same-Open assumptions; do not relabel them as certified live fills or true one-way commissions.

`results/ALL_SCORECARD.csv` distinguishes preregistered versus post-result experiments. `FEATURE_DICTIONARY.csv` documents18newmeasurements; `TRAIN_ONLY_PRUNING.csv` lists removed inputs by annual training; `FEATURE_PACK_REGISTRY.json` states actual research status. `FINAL_VERIFICATION.json`, yearly model audit and logs are inspectable evidence, not a claim that every historical repository test passes.

Observed Python3.13.5,numpy2.3.5,pandas2.2.3,scikit-learn1.8.0,xgboost3.1.3,numba0.65.1. Exact package list is in the delivered ENVIRONMENT.txt. Review was by the author, not independent. Current versus old39% windows are different. Large models/data/ledger ZIPs are not asserted uploaded as GitHub assets.
