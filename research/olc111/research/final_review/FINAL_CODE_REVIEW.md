# OLC111 independent final code review

## Decision and scope

**No Critical or Important finding remains in the reviewed implementation.** The code is consistent with the frozen experiment's causal timing, native account economics, matched information ablations, and fixed 18-path execution matrix. This is a code and synthetic-boundary conclusion. It does not certify the financial results, forecast gates, reliability of the repeated policy, or any promotion claim; those require the requested later read-only results review.

Authority was `docs/DESIGN_AND_PROTOCOL.md`, read with `docs/IMPLEMENTATION_PLAN.md` and `docs/PROGRESS.md`. The review covered all five files in `src/`, the five test modules, the frozen selector/core functions used by the new runner, both freeze manifests, and the previous pipeline review. No financial source, historical input, model setting, bank label, or existing report was modified. No full research fit or historical account path was started by this reviewer. Synthetic fits used small artificial arrays in temporary directories. This file is the reviewer's only persistent deliverable.

The previously corrected pipeline issues were not reopened without evidence. In particular, the primary Close adapter, separate terminal feature calendar, unsupported seed-mark censor, and bank cache provenance checks remain present. The parent's 1,566-pair historical HOLD reconciliation was not independently rerun here and is not counted as this reviewer's evidence.

## Causal fitting and information comparisons

`MonthlyFitCache` derives cutoffs from the first panel session of each calendar month, clipped to the initial decision index. Its calendar does not depend on the first surviving bank row. `fit_head` applies the complete finite-feature/label mask together with `terminal_idx < cutoff` before scaling, projection, weighting, or estimation. The cutoff used by a decision is never later than that decision. The prequential ledger checks both inequalities again and records the maximum training endpoint and immutable model hash. Preparing every historical monthly fit in advance does not introduce future labels into an earlier fit.

All four arms within a head use the same surviving training rows. Date weights give a date a total weight of one before normalization, including where duplicate state rows exist. Readiness requires both 504 distinct mature dates and 24 greedily nonoverlapping 21-session intervals. The runner requires all three heads to be fitted before any learned override, so an available exit model cannot move the account to cash while entry is still unavailable. Initial entry remains the baseline even if a synthetic fixture supplies already-ready models.

The representation uses training-only price scaling, weighted least-squares removal of price/intercept information from the legacy VIX block, and removal of price/legacy/intercept information from the term block. Negligible numerical projection residues are disabled instead of being amplified to unit variance. The Ridge objective normalizes weights before adding a slope penalty of 1.0; the intercept remains unpenalized. This implements the specified mean-loss penalty rather than an unnormalized row-sum penalty.

The coefficient bootstrap resamples fixed 63-session signal-date blocks and retains all rows attached to selected dates. Draws are paired across the four information arms within each head. The representation remains fixed at its full mature-training estimate during resampling. The 10th percentile is correctly described in the code and saved metadata as a conditional-mean action buffer, not a calibrated 90% confidence bound. Neither overlapping label values nor their buffer quantiles are transformed into a portfolio CAGR.

The Cboe adapter independently finds each index's last source date strictly before the European decision date. It requires the three source dates to match, age to be at most seven calendar days, and current/lagged values to be positive and finite. Invalid latest observations are not silently replaced with an older source observation, and invalid sessions are not deleted to redefine the 21-source-session VIX lag. Missing inference support makes VIX/TERM use the matching PRICE model; the callback logs that substitution. PRICE can predict without the missing option arrays, as required.

## Economic labels and daily account policy

Each native comparison starts from copied actual units and cash. The initial action is executable no earlier than the following session. A HOLD emits no initial instruction, including at a monthly intervention date. Future scheduled targets use the frozen selector at their own future decision dates, and the common continuation starts strictly after the intervention date. The selector's current-weight argument is unused for the frozen arm, so storing its causal daily targets in advance does not change those targets or introduce learned continuation.

The all-cash training state has the same starting NAV as the baseline account and is explicitly conditional. Its label does not book a free sale of the baseline portfolio. Similarly, the ENTRY comparison's no-entry branch follows the future monthly baseline; it is not a promise that cash remains idle for the entire 21-session label window. The repeated policy can choose a different future action sequence and encounter different holdings. Actual account replays are therefore essential to the conclusion even if the conditional forecast diagnostics are favorable.

Both baseline training states and all native training comparisons receive the explicit next-Close execution panel and normal costs. Labels are log terminal NAV ratios with actual order costs already deducted; the prediction rule adds no second cost hurdle. Terminal holdings are marked without a fictional final sale. The native comparison validator checks causal supported marks at the signal and every subsequent realized Close, censors a matched comparison on unsupported valuation, and leaves right-edge outcomes pending. Future targets at the terminal Close itself are excluded because they cannot execute inside the label window.

In the learned runner, CASH/FRESH act from the current account received from the engine. FRESH/ENTRY must have a positive target and pass the explicit total-weight-difference no-op test. Eligible actions require a positive mean and positive lower buffer; the largest lower buffer wins, with CASH before FRESH on equal values. All discretionary instructions are forced only after the no-op test. HOLD returns `None`; with `allow_scheduled_hold=True`, a monthly HOLD preserves actual units and cash instead of rebalancing to a stale weight vector. The synthetic opening-gap tests exercise that distinction directly.

An outstanding pending/queued instruction blocks new learned discretionary instructions. During warmup the scheduled baseline keeps its inherited instruction semantics. Stress paths use the same primary-bank monthly fits and make predictions on their own actual account states; they do not refit for costs or execution convention. The Open sensitivity retains its documented execution-quality limitation and is not silently presented as the primary Close convention.

## Accounting summaries and persistence

The first common post-warmup performance session is the session after the first all-head-ready decision Close. `performance_window` uses each path's actual immediately preceding Close NAV as its denominator. Annual windows also use the preceding actual account NAV. Sampled drawdowns include both the native pre-fee execution mark and the closing mark. Under Close execution those are pre/post-fee Close samples; under Open execution they are Open/Close samples. They are not intraday extrema.

The forecast ledger is written before the account-path loop. Its MSE and bias diagnostics use date balancing and matched information-arm support. TERM's incremental MSE is compared with VIX, as well as the retained MEAN/PRICE references. Realized intervention counts require an actual order and deduplicate an instruction that generated multiple orders. The 21-session episode counts remain diagnostic counts, not formal independent experimental replications.

The experiment freeze covers the runner, transitive frozen sources, raw inputs, causal selections, baseline states, bank event ledger, and bank provenance receipt. I independently rehashed the declared identities without invoking a bank build: all 18 bank-freeze identities and all 23 experiment-freeze identities, including their protocol checks, matched. A resumed fit requires the same experiment fingerprint, cutoff, and fit options; each reconstructed model is hashed again. The complete transform, coefficient, bootstrap-coefficient, feature-count, and metadata payload survives restoration.

The native order ledger preserves quantities, prices, costs, signal/execution dates, reasons, and instruction identity. Saved instructions retain immutable targets and action metadata. Decision arrays preserve pre-instruction units, cash, and weights; daily traces preserve state summaries and model identities on holds too. Combined with the initial account and frozen input panel, the order ledger permits reconstruction of account holdings on dates that issued no instruction. `METRICS.json` is written last as the completed-path marker, and resumed paths require the other saved ledgers to exist.

## Independent verification performed

The complete current synthetic suite was run once by this reviewer:

```text
python -m unittest discover -s tests -v
Ran 63 tests in 1.065s
OK
```

Three additional small independent checks addressed integration risks beyond merely reading a passing test list:

1. Fit and serialize nonconstant, correlated artificial price/legacy/term features for every head and information arm; restore into a fresh `MonthlyFitCache`; compare mean and lower predictions. Maximum prediction difference: **0.0**.
2. Modify one saved TERM coefficient in that temporary checkpoint. Restoration rejects it with **`FIT_CACHE_MODEL_HASH_MISMATCH`**.
3. Save a 16-session, two-asset artificial native account containing three orders and three decision snapshots. Reload the saved order/daily files, reconstruct units/cash/NAV from the initial EUR10,000 account, and compare. Maximum cash and NAV differences were **1.8189894035458565e-12 EUR**. Saved decision quantities also matched exactly.

The existing suite additionally covers future-feature/label mutation, strict terminal-equals-cutoff exclusion, same-date US Close rejection, common support, duplicate-date weighting, Ridge scaling, paired blocks, cost/gap accounting, seed copying, stale-mark censoring, Close-versus-Open separation, scheduled HOLD, no-op behavior, initial/warmup fallback, missing-source PRICE fallback, and preceding-NAV segment accounting. No broad historical study was rerun to obtain this evidence.

## Deferred minor and interpretation notes

**No minor source change is requested before running the frozen matrix.** These distinctions should remain explicit in the final report:

- `positive_buffer_realized_mean` is the realized bank outcome conditional on that head qualifying independently. It is not necessarily conditional on winning the competing CASH/FRESH choice, and it is not a causal advantage measured from the subsequent learned account. Its existing name and runner documentation are appropriately narrower; avoid relabeling it as realized trading alpha.
- Holding-age fields measure sessions since the latest actual BUY, so a top-up resets that age. They do not measure the uninterrupted lifetime of the oldest surviving unit. The runner implementation document already states this limitation.
- Fit/path checkpoint writes are fail-fast rather than self-repairing. An interrupted gzip/JSON write may require discarding the incomplete checkpoint and regenerating it under the same freeze. A corrupt checkpoint is not an alternative accepted financial result. Atomic-write hardening would improve restart convenience but is not a reason to change the frozen financial experiment.

## Behaviors considered and left outside this code review

No threshold, feature, bootstrap, horizon, selector, training-state, or continuation redesign was proposed. Those would change the preregistered experiment rather than correct a demonstrated implementation defect. The review also did not add on-policy labels or train against the stress scenarios: both would violate the fixed bank/fitting contract.

I did not replace the native complete-path valuation rules. The five-calendar-day support condition is explicitly checked for label comparisons, while full accounts retain the inherited forward-filled native marking convention. Learned accounts may hold positions longer than the baseline anchor bank; any actual stale-held-mark dependence is a result-audit question to resolve from the saved paths, not a speculative reason to alter the strategy before observing the fixed run. This report makes no claim that such dependence is present or absent in the unreviewed full paths.

No external strategy research, remote branch operation, production workflow, live trade, or broad historical rerun was attempted. The later results review should determine whether all 18 ledgers completed, whether their saved economics reconcile, and whether conclusions honor failed forecast/reliability gates and the exploratory-data limitation. This report is not an approval to promote a model.

## Reviewed identities

Source identities checked at **2026-11-16T19:30:29.124400+00:00**. A change to a reviewed behavior requires a focused review of that change.

| File | SHA-256 |
| --- | --- |
| `docs/DESIGN_AND_PROTOCOL.md` | `8c826bb50a67bcf9bbb723aa0eb85f34b788b21713d2c756f8d12ef55995df84` |
| `src/advantage_model.py` | `153081fb3623fa1b9c12498f9c5c07c6845fd25cc7f27cc40a13f05ff52f1605` |
| `src/cboe_features.py` | `094c278adb6363136a2ffc2528d56c765b9508b2fe593893748fcf66c90db62c` |
| `src/replay_engine.py` | `ad4ebbb81620456e61bf0d833fd999c7a1a0026acb0a5f0370a0c51c33d39a1a` |
| `src/research_pipeline.py` | `64a09ca31077b24696de6d3d95395f9825e045fdc16422dd476f8cf968b84e35` |
| `src/run_olc111.py` | `69d7d98b0ffffa6144f2ef517d3109177b53b57d2fc452ce1d6a011dd7d1b03e` |
| `tests/test_advantage_model.py` | `603f4ecb176ef5c75eba573fdabb2a34df178260f827c84499fd906107c6f1de` |
| `tests/test_cboe_features.py` | `a403c6a1649cf73a65283637c1c274ef7d36b9edfae49e353efb85c7e1bd9b4b` |
| `tests/test_replay_engine.py` | `2d464d380ad77e0362d0f3ecc17c1b763c3d16fa4d5287a6585560132120c737` |
| `tests/test_research_pipeline.py` | `5d76ba374722bdf3088c4360efac7dbc33dc0f1c183a5bc5f7e2cd08b27e0e8b` |
| `tests/test_run_olc111.py` | `df24906a037c20aaed52cfdbad9dd5d5d2d15c88706d823979fb434fb19f374e` |
