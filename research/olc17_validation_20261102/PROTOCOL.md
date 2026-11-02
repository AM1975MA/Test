# OLC17 — frozen-candidate validation, first block

2026-11-02. User approved stronger evaluation of TOP2_CONTEXT_REVALUE. Parent frozen at 99d6219006df62882cf04ada65db72951fadc419. This is validation, not a new search for a winning ranking. CUM_FIT and main remain unchanged. No live orders.

## Scope and immutable controls
Restore exact source tree 0a58a1bb375db1615f390d04f9e4a65e5c7047e4 and the two actually persistent OLC16 archives. Verify hashes and parent tests. Rebuild forecasts from the saved annual models without fitting. Four comparators: ORIGINAL, CUM_FIT, TOP2_STATIC_REVALUE, TOP2_CONTEXT_REVALUE. Identical data, dates, nominal50/50 allocation, IMMEDIATE primary policy, original costs. Do not change labels, model parameters, memory, candidate or contexts after outcomes.

## First validation block
1. Reproduce FULL and LAG1 parent portfolios in USA/EU, fee .001/.003. Audit cash/units and report yearly and common2021-24/full windows with prior definitions.
2. Audit signal availability in source. Distinguish monthly forecasts known before next Open; prior-close weakness/gross inputs; current opening gap/breadth used to reduce exposure or arm stops; daily Low used as barrier evidence; current/frozen V6 dependency. Daily OHLC does not provide the first executable price after observing all opening gaps. Therefore no claim that arbitrary day shifts prove exact live execution.
3. Isolate same-Open dependencies with a fixed factorial: exposure systemic trigger uses NOW or PREVIOUS_SESSION gap/breadth; conditional-stop arming independently uses NOW or PREVIOUS_SESSION gap/breadth. Previous-session stop arming uses its own target-weighted systemic predicate, not the exposure predicate. Prior-close UH/SA and prior-close stop threshold remain unchanged. NOW/NOW must match legacy, PREVIOUS/PREVIOUS must match parent LAG1 exactly. Mixed variants are attribution probes, not proposed strategies.
4. NO_GAP_LAYER ablation disables systemic gap exposure and conditional stops, retaining prior-close gross and V6. It is diagnostic of dependency, not a safer or promoted strategy. Fees .001/.003, both markets, all four comparators;5 scenarios x4x2x2=80 paths planned. Only completed verified counts will be reported.
5. Reconcile daily log-return differences into primary price PnL, defensive PnL, stop effect and frictions. Trace all final-pair disagreements and monthly relative PnL, including shared decisions with different inherited holdings. Arithmetic attribution is conditional on paths and is not a unique causal claim. Measure win concentration without removing observations from the strategy.
6. Test candidate sensitivity to execution-cost assumptions through paired stress levels already declared, with no per-market choice. Attempt candidate-consistent V6 reconstruction only if frozen source/price support and exact original-input parity can be proved; otherwise explicitly leave it unverified rather than silently substitute.

## Inference and limits
Layer quality and portfolio benefit remain separate. Same comparisons on USA and EU; do not hide harm in pooled averages. Report numerical effects, adverse years, multiplicity and reused history. Zero-containing intervals are not automatic veto. No new data considered pristine. Actual intraday fills, raw total-return/FX, delisted-fund completeness and live market capacity remain uncertified.

A larger blocked-context null experiment with nested reselection and a genuinely prospective frozen campaign are separate remaining blocks; this first block does not claim them completed. No HMM, new ranking, new risk thresholds or parameter rescue.

## Execution and preservation
Isolated local validation workspace; original source read-only copy, new instrumented engine in a separate module. Synthetic failing tests first for independent trigger timing and prefix invariance, then parity tests. Preserve code, protocol, findings and checkpoints incrementally on this research branch; verify actual binary persistence separately. No background-work promise. Final report names finished checks and remaining gates; self-review is not external review.
