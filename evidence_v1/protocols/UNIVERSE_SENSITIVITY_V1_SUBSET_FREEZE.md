# Evidence V1 — Universe Sensitivity v1 subset freeze

Status: **FROZEN BEFORE ANY PERFORMANCE TEST**

Purpose: freeze three nested candidate universes derived only from the already-frozen `Original149` metadata. No OHLCV, return, target, model score, or historical performance may enter subset selection.

## Frozen inputs

- branch: `research/evidence-v1`
- Original149 metadata: `evidence_v1/data/original149/universe.csv`
- Original149 metadata Git blob: `7d176c3963e3bc69c53745a68e1a1e8db6ca570d`
- freezer source: `evidence_v1/src/freeze_universe_sensitivity_v1_subsets.py`
- freezer source Git blob: `6fecaae82c7ef28d8559e01aac55212b9135d194`
- frozen data manifest SHA256: `1efba2bc213ba26b042a9e77630fe26664343654629e658f43d314d068ba9e71`
- frozen source manifest SHA256: `cc4d315da68ec42275a7a74f05446ac6cbb484c3bd92a7861cd76805c5a94782`

The Action must fail closed if these identities do not match.

## Deterministic subset rule

Candidate sizes: `120`, `100`, `70`.

The subsets are nested prefixes of one deterministic priority order:

1. `SPY` is mandatory and first, only to keep the source-only calendar anchor constant across all candidate universes.
2. Remaining slots are allocated category-by-category using proportional deficit versus the six Original149 macro categories.
3. Within each category, ticker order is fixed by `SHA256("evidence-v1-universe-sensitivity-v1|<ticker>")`.
4. Ties in category deficit are resolved lexicographically by category name.
5. The freezer reads only `ticker` and `macro_category` from `universe.csv`.

This rule is frozen before any sensitivity result is generated.

## Durable outputs

Directory:

`evidence_v1/protocols/universe_sensitivity_v1/`

Expected files:

- `PRIORITY_ORDER.csv`
- `U120.csv`
- `U100.csv`
- `U70.csv`
- `SUBSET_MANIFEST.json`

The manifest records category counts and SHA256 for every frozen subset file. Once generated, these files become immutable inputs to the sensitivity experiment.

## Scientific restriction

The subset-freeze run is not evidence about model quality. It only establishes candidate universes before the downstream test. `Holdout70` is not read or used here.