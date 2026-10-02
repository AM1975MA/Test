# Evidence V3

## Status

**OPEN — Phase A universe freeze only. No V3 performance result exists yet.**

## Why V3 exists

Evidence V1 and V2 established that the frozen LTR architecture can retrieve plausible candidates but that repeated attempts to improve the extreme Top1 choice on Original149 did not survive preregistered gates. Original149 is closed/burned development data and Holdout70 is burned diagnostic data. EU120/EU110 was subsequently used in P45 transfer/retrain work and is therefore not treated as a clean new development universe.

Evidence V3 starts from a new development universe before any architecture selection.

## Phase A — Dev72 freeze

Dev72 is defined by `evidence_v3/protocols/DEV72_FREEZE_PREREG.md` and produced only by `evidence_v3/src/freeze_dev72.py`.

Rules:
- exactly 72 ETFs, 12 per six macro categories;
- ordered candidate pools frozen before download;
- exclude Original149, Holdout70 and the tested EU110 reference;
- selection uses only identity/category/data availability/coverage/OHLC quality;
- no performance, target, score or model may be computed in Phase A;
- data end is frozen at 2026-07-31;
- at least 252 valid observations must exist by 2017-01-31;
- if a category cannot fill its quota, the freeze fails closed.

## Planned Phase B

Only after Phase A succeeds and the data/manifest are committed and hashed:
1. rebuild the canonical MA3 source-only panel on Dev72 using the same frozen source used by Evidence V1/V2;
2. preregister a **baseline transfer test** of the exact frozen LTR architecture on Dev72, with no V3 feature additions;
3. use that test to establish whether the original LTR retrieval phenomenon transfers to a genuinely new universe;
4. only if transfer is credible will V3 preregister one new decision-layer hypothesis.

No Holdout-B or promotion claim is opened at this stage. Dev72 is development data and becomes burned once Phase B performance is observed.

## Repository rule

Every V3 test must commit source, preregistration, workflow, provenance and durable results. Scientific source/preregistration must be frozen before the corresponding run.