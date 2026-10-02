# Evidence V4 — CLOSED

## Purpose

Evidence V4 tested the hypothesis derived from the V3 tail-symmetry diagnostic:

`Stage 1 frozen LTR magnitude/tail retrieval -> Stage 2 separately trained causal 21-day direction/sign classifier`.

The architecture, Stage-1 K=10, Stage-2 target, features, hyperparameters, decision rule and primary gate were preregistered before the new V4 universe performance was observed.

## Phase A — new V4 development universe

The initial V4 universe was frozen as Dev60: 60 ETFs, 10 per six structural categories, selected only by frozen candidate order, burned-set exclusion, data coverage and OHLC quality. It was disjoint from the 400-name union of Original149, Holdout70, tested EU110/EU120 reference names and V3 Dev72.

Dev60 freeze run: `37075202192`.

Frozen identities:
- Dev60 manifest SHA256 `c83494032c4a0675a1cf5769dd01cefa5025f406606e3bb0c4a2779f1a9e642a`;
- Dev60 universe SHA256 `b2a14c91f5dad67132032f79249bd00a8fd742bf13eaddf6dea712ca93dcde40`.

## Pre-performance engineering correction — Dev60 -> Dev72V4

The first model orchestration run `37075621569` failed inside canonical MA3 cluster reconstruction **before any Stage-1/Stage-2 model result or performance was computed**.

Root cause: frozen MA3 clustering requires at least 8 defensive ETFs and 7 dynamic clusters × 8 names = 56 dynamic names. Dev60 had 10 defensive + only 50 dynamic names, so canonical clustering was structurally impossible.

The correction was documented before any V4 performance in `evidence_v4/protocols/DEV60_TO_DEV72_ENGINEERING_FIX.md`:
- preserve all 60 Dev60 constituents byte-for-byte;
- add exactly the next two coverage-valid names per category from the already-frozen pre-V3 candidate order;
- no performance criterion;
- architecture and gate unchanged.

Corrected Dev72V4 expansion run: `37075943794`.

Dataset commit: `ad8c68e` (`Freeze corrected Evidence V4 Dev72 universe`).

Artifact:
- id `11256896519`;
- SHA256 `2574118b2084c94b1012ad7aeb10e2acc71a78b59ce7f59ed088675f0cc647f9`.

Frozen corrected identities:
- manifest SHA256 `8a50de08efd056e2637b6e043ff540d19d882ab34e53c16c930eea43a642a4dd`;
- universe SHA256 `ae19ffdd0f4e89c677734a640ca1814c3651489caddc61aef089158d3ccb6a62`.

Dev72V4 has exactly 72 ETFs, 12 per category, zero overlap with the 400-name burned/tested union and `performance_used_for_selection = false`.

## Architecture preregistration

Protocol: `evidence_v4/protocols/MAGNITUDE_DIRECTION_V1_PREREG.md`.

Protocol Git blob: `8cdcc887f6707352645f90bff1a95519146bd1d7`.

Source: `evidence_v4/src/magnitude_direction_v1.py`.

Source Git blob: `b7a517b247e62de8866dfe35592a7ba73643b504`.

### Stage 1
Exact frozen Evidence V1 LTR architecture, annual expanding, 63-day label maturity, fixed Top10 shortlist.

### Stage 2
Causal XGBClassifier trained only on historical Stage-1 OOS Top10 candidates whose 21-day label is mature. Target is exactly `SIGN21 = 1 iff fwd_ret_21 > 0`; features are `FEATURES_42 + LTR_POSITION`. Current Top10 selection is max predicted `P(SIGN21=1)` with no threshold/cash/blend/fallback.

## Valid V4 result — REJECT

Valid run: `37076213843`.

Result commit: `5beece2` (`Record Evidence V4 magnitude-direction v1 result`).

Artifact:
- id `11256447625`;
- SHA256 `fb8f9a3317a9d36e3c09a7f9c1ef4b36c626d7de186007705e5a2808be211fcf`.

Evaluation: 114 monthly periods, 2017-01-31 through 2026-06-30, 72 candidates each month.

### Stage-1 retrieval still transfers

- Top10 global-winner hits: **62/114**;
- random expected: 15.83;
- winner enrichment: **3.916x**;
- Top10 global-loser hits: **47/114**;
- loser enrichment: **2.968x**.

Thus the broad tail/opportunity retrieval phenomenon transfers again.

### Economics

| Portfolio proxy | CAGR | Ann. vol | Sharpe rf0 | Max DD |
|---|---:|---:|---:|---:|
| Stage1 global Top1 | **11.27%** | 32.91% | 0.486 | -47.23% |
| Stage1 Top10-EW | **11.04%** | 22.68% | 0.579 | -39.10% |
| Two-stage direction Top1 | **-0.33%** | 25.67% | 0.118 | -60.71% |
| Dev72V4 Universe-EW | **8.45%** | 13.69% | 0.663 | -22.01% |

The direction head selected a positive future return only 54.39% of months and exact global winner only 3/114 times, despite mean predicted positive probability 0.674.

Subperiod direction result:
- 2017-2022: **3.80%** vs Universe-EW **7.81%**;
- 2023-2026: **-7.03%** vs Universe-EW **9.56%**.

### Primary gate

- Stage1 Top10 winner enrichment >=2x: PASS;
- direction full-window CAGR > Universe-EW: FAIL;
- direction 2017-2022 CAGR > Universe-EW: FAIL;
- direction 2023-2026 CAGR > Universe-EW: FAIL.

**Binding verdict: DEVELOPMENT_REJECTED.**

No K, sign threshold, sign target, class weighting, classifier hyperparameters, feature subset, blending, cash rule or horizon variant may be tried on Dev72V4.

## Scientific interpretation

The V3 hypothesis that a separate generic sign classifier could resolve the tail symmetry is not supported. The classifier destroys rather than improves the economic value of the Stage-1 opportunity set.

At the same time, one diagnostic comparator deserves future independent verification but cannot be promoted ex-post from V4: the **unchanged Stage-1 LTR alone**, especially Top10 equal-weight, produced 11.04% CAGR versus 8.45% Universe-EW on Dev72V4. This contrasts with V3 Dev72, where LTR concentration/allocation was weaker, so robustness is not established.

The next scientifically admissible question is therefore narrower:

**Does the exact frozen Stage-1 LTR Top10 equal-weight portfolio, with no direction head and no further model tuning, outperform its own Universe-EW robustly on another fully disjoint development universe?**

That question must be preregistered and tested on new data. It may not be answered by tuning or selecting a variant on Dev72V4.

## Data status

- Original149: burned.
- Holdout70: burned diagnostic.
- EU110/EU120: previously tested.
- V3 Dev72: burned.
- V4 Dev60 / Dev72V4: burned V4 development after valid performance run.
- No Holdout-B has been opened.
- Evidence V4: **CLOSED**.