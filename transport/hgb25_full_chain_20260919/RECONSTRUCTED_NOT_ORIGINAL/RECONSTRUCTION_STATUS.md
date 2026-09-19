# HGB25 missing helpers — reconstruction status

**STATUS: RECONSTRUCTED — NOT ORIGINAL HISTORICAL SOURCE**

The three files in this directory are clean-room reconstructions created only after the original-source search failed to recover the corresponding historical blobs:

- `titanium_alternative_ranker.py`
- `titanium_breath_collapse_detector.py`
- `titanium_sequential_leader_state.py`

They MUST NOT be copied into `original_sources/`, renamed as recovered originals, or cited as byte-identical historical source.

## What is anchored to recovered historical evidence

- leader-only BREATH/COLLAPSE semantics;
- -3% close-confirmed fire followed by sequential confirmation;
- decision after the second close and execution at the next open;
- whole-universe alternative search excluding leader/BIL/SHV;
- causal TIT_R is the dominant destination score;
- 10 bp alternative return cost convention;
- downstream consumer contracts (`BASE_FEATURES`, `SCORE_FEATURES`, `DYNAMIC`, `SCORE_COLS`, `DAILY_COLS`);
- no feature uses data after `score_date`; future path values are labels only.

## What is NOT claimed recovered exactly

The lost files' exact internal feature lists, exact model hyperparameters, and exact implementation details are not proven identical. These reconstructions preserve the documented strategy idea and downstream interface, and require parity testing against historical intermediate panels / decisions before they can be promoted as operational equivalents.

## Search status

Original-source search performed across reachable GitHub repository code/branches/commit-path history, the saved Library file inventory, and recovered historical packages. No original blob for the three filenames above was recovered as of 2026-09-19.
