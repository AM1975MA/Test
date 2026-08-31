# Meteor DD Research — Full Reframing Audit after STEP08M

Date: 2026-09-01

## Executive conclusion

STEP08M (true HY/IG OAS + breadth) is a clear reject on 2021–2022:
- ΔCAGR vs FUSION1: -2.9635 pp
- Δmean MaxDD: -0.9522 pp
- Δp10 MaxDD: -1.0562 pp
- 2021 Δmean MaxDD: -1.5369 pp
- 2022 Δmean MaxDD: -0.2758 pp
- BIL chosen 50.80% vs oracle BIL 38.26%
- only 23.29% of selected BIL actions were economically better than STAY.

No 2023+ data were opened for STEP08M.

The audit conclusion is that the current research has not primarily failed because of model capacity or because one more standard stress feature is missing. It has increasingly been solving the wrong conditional decision problem.

## What is already proven

### 1. The basic DD controller works
STEP06B was already an unusually efficient frontier move on untouched 2023–Jul2026:
- ΔCAGR -0.0641 pp
- Δmean MaxDD +1.6656 pp
- Δp10 +1.6686 pp
- Sharpe +0.0449.

STEP06E FUSION1 is stronger still and remains the frozen DD-first challenger:
- holdout ΔCAGR +0.2425 pp
- Δmean MaxDD +2.7805 pp
- Δp10 +3.4170 pp
- Δp5 +4.4211 pp
- Δworst-decile +3.3466 pp.

Therefore the DD problem is not “unsolved”. The unresolved problem is incremental improvement beyond FUSION1 without paying away CAGR.

### 2. More aggressive de-risking is mechanically capable, but timing it is hard
At the first -5% crossing, 92.8% of development events reached -7.5% within 21 sessions. The aggressive STEP06K tail ladder improves local DD by about 1.96 pp on average, but has higher return in only ~31% of crossing events. It is highly effective in true crash regimes and expensive in recoverable dips.

### 3. Local exposure/cash action space has a limited incremental ceiling
STEP07B/C and the persistent-action oracle showed that even perfect local exposure choices do not create the desired large incremental global MaxDD improvement. This means the problem cannot be solved simply by a more accurate “reduce exposure now?” classifier.

### 4. Protective rotation has a large ceiling
The basket-local oracle among the original 24 ETFs showed that alternative destinations frequently exist:
- oracle stay-allowed ΔCAGR about +9.16 pp
- Δmean MaxDD about +3.05 pp
- Δp10 about +4.94 pp.

After a causal live-shock-resilience filter reduced the action set to roughly five candidates, the filtered oracle still retained:
- ΔCAGR about +3.64 pp
- Δmean MaxDD about +2.01 pp
- Δp10 about +3.12 pp.

Therefore the economic opportunity to rotate exists. The failure is destination identification, not lack of available alternatives.

### 5. Fresh Titanium ranking carries alpha, not enough protection
STEP08F event-time Titanium:
- ΔCAGR +0.6325 pp
- positive CAGR contribution in both 2021 and 2022
- Δmean MaxDD only +0.0505 pp
- p10 worsened by -0.8650 pp.

This should remain a separate Titanium alpha challenger. It demonstrates that stale monthly ranks are a real problem, but alpha ranking is not a protective selector.

### 6. Simple inverse correlation is the wrong destination criterion
Inverse correlation and downside-beta-first variants in STEP08E2 materially worsened the frontier. Correlation should therefore be used to characterize whether rotation is feasible/systemic risk is compressing, not as the primary ETF selector.

### 7. BIL/STAY has useful oracle value but unstable learned mapping
The BIL/STAY oracle was meaningful (roughly +1.32 pp CAGR and +1.17 pp mean MaxDD), but STEP08J/K could not learn the timing stably. New standard stress information in STEP08L and true OAS in STEP08M made the policy too defensive rather than fixing it.

## What we have been getting wrong

### A. Wrong target: local fixed-horizon utility is not global MaxDD contribution
MaxDD is path-dependent. A 10- or 21-day action-value label treats many events as economically comparable even though only a small subset lies on the path that produces the eventual major drawdown.

The next target should be defined over the entire drawdown episode, not a fixed horizon: start at the first relevant stress state, terminate at recovery to the prior high-water mark/new peak (or a safety cap), and measure terminal wealth, trough reduction, recovery time and area-under-water under counterfactual actions.

### B. Wrong statistical unit: basket-event rows exaggerate independent evidence
Hundreds or thousands of basket events often occur on only a few dozen independent market dates. STEP06L had 458 events but only 56 calendar dates; later holdout tail work had 1,051 crossing events on 48 dates.

Future model selection must be episode/date-blocked, with one market episode/date block as the independent macro unit and leave-one-crisis/leave-one-year-out validation.

### C. We collapsed three distinct states into a binary decision
The evidence supports at least three states:
1. RECOVERABLE_BREATH — STAY.
2. ROTATABLE_STRESS — rotate to a genuine alternative.
3. SYSTEMIC_NO_ESCAPE — BIL/aggressive FUSION1.

A direct STAY/BIL classifier cannot represent state 2. A pure ETF ranker cannot represent states 1 and 3.

### D. We used stress variables to predict action, instead of measuring escape topology
VIX, OAS, NFCI, breadth and rates mostly answer “is the market stressed?”, which FUSION1 already answers reasonably well.

The missing information is whether stress is systemic or origin-specific, whether correlations are compressing, whether a genuinely independent destination exists, whether capital is migrating into alternatives, and whether recovery breadth is broadening or collapsing.

## Proposed new formulation

### Stage 1 — Trigger
Keep FUSION1/q95 frozen. Do not build another crash predictor.

### Stage 2 — Market geometry / escape-regime classifier
Estimate RECOVERABLE_BREATH vs ROTATABLE_STRESS vs SYSTEMIC_NO_ESCAPE using:
- first eigenvalue / total variance of correlation matrix;
- average pairwise and downside correlation;
- cross-sectional dispersion and acceleration;
- fraction of candidates with positive relative return vs origin at 1/3/5/10/21d;
- fraction above 63/126/252d moving averages;
- new-high/new-low participation;
- breadth recovery speed;
- gap/volume/liquidity participation;
- OAS/funding only as systemic confirmation.

### Stage 3 — Conditional action
- RECOVERABLE_BREATH -> STAY/FUSION1.
- ROTATABLE_STRESS -> small resilient set + event-time Titanium/opportunity score.
- SYSTEMIC_NO_ESCAPE -> BIL/aggressive FUSION1.

## New orthogonal information worth adding

Priority:
1. Cross-sectional market geometry from the existing 150 ETF panel: eigenvalue concentration, correlation-network compression, tail-dependence, dispersion, breadth and recovery participation.
2. Funding/liquidity plumbing: SOFR-IORB/repo stress, RRP, TGA, Fed balance sheet/reserves, MOVE if an immutable history can be frozen.
3. Positioning/flow: CFTC positioning with publication lag, option/dealer-gamma proxies if point-in-time history is reliable, ETF flows if a stable archive exists.

True credit OAS should remain a confirmation feature, not the main decision variable.

## Validation redesign

Use as much pre-2021 calendar history as causally possible, ideally including 2008, 2011, 2015–16, 2018 and 2020; episode-level labels; leave-one-crisis/year-out; date/episode weighting; and only one frozen 2023+ opening after a candidate passes.

## Immediate next experiment

**STEP09A — Escape Topology Audit**

Question: can causal market-geometry variables distinguish, at FUSION1/q95 stress episodes, whether the oracle action is STAY, ROTATE or BIL?

No portfolio replay selection yet. Test information content only, date/episode weighted. If stable, proceed to STEP09B hierarchical controller. If not, standard public price/macro information is likely near its practical limit and the next step should require genuinely new flow/positioning data.
