# OLC110 — Critical protection and reentry design review

**15 November 2026. Design/research only. No new financial simulation or production edit.** This memo reviews the proposed experiment; the subsequently frozen OLC110 protocol is the executable authority. The parent researcher has adopted a small nested design rather than the initially considered exit-by-reentry factorial.

## Recommendation

Preserve `DEDUP_DUAL_TREND_OPP`, its monthly selected identities, nominal 50/50 slots, eligibility, correlation ceiling, and accounting conventions. Test whether a daily exit plus an explicitly separate rebound regime improves the timing of cash exposure. Then test whether genuine vacancies can be filled by a newly qualified opportunity. The intended return source remains the original ranker; unwanted exposure is the continuation of a selected ETF's decline. This is a research proposal, not a claim that an exit threshold caps actual losses.

The strongest hypothesis is **reentry repair**, not a better annual rank or a learned regime predictor. The OLC109 archived `DEDUP_DUAL_EXIT63` and `DEDUP_DUAL_TRAIL15` arms used `DEDUP_DUAL21`, not today's `DEDUP_DUAL_TREND_OPP`. Their weekly exits and monthly reentries are warnings, not matched controls for this study. They returned approximately 9.02%/9.49% CAGR with sampled drawdowns of −48.72%/−50.70%. The chosen unprotected reference is 25.7526% CAGR and approximately −37.92% sampled drawdown. All these are already inspected historical results. [L1–L3]

### Bounded matrix

The parent's 13 arms are defensible because they are nested mechanism and allocation controls, not a full parameter grid:

| Arms | Question isolated |
| --- | --- |
| `BASE`, `STATIC_HALF`, `STATIC_75` | Does timing add more than simply holding less risk? |
| `REFRESH_WEEKLY` | Context for the cost of refreshing the entire unchanged ranker more often. This is not a pure matched control for filling only vacancies. |
| `EXIT21_MONTHLY`, `EXIT21_SLOW` | Same exit and same slow recovery condition; monthly versus daily opportunity to recover. |
| `EXIT21_FAST`, `EXIT21_STAGED` | Fast rebound recognition; then the incremental effect of entering at half a slot before full confirmation. |
| `EXIT63_STAGED`, `TRAIL15_STAGED`, `VOLTRAIL_STAGED` | Three declared exit substitutions, with the same staged recovery. |
| `EXIT21_STAGED_FRESHW`, `EXIT21_STAGED_FRESHD` | Weekly versus daily fresh opportunities into genuinely vacant slots. Both must remain reported. |

Use the five existing scenarios for every arm. The parent also proposes a sixth, next-session accepted Close execution scenario: useful as execution sensitivity, explicitly separate from the next-Open contract, with appropriate sampled/Close drawdown labels. It must never fill at the signal Close. This gives 78 paths, not 78 independent hypotheses. No winner-conditioned additional grid should follow automatically.

## Exact initial rules and state coherence

All observations and calculations are available only after the completed signal Close. `mN = log(C_t / C_(t-N))`; averages and extrema use the causal accepted/forward-marked panel convention, and a **new entry or recovery signal requires an actually observed current Close**. Missing current observations cannot manufacture a crossover. Log the price-age and observed-count diagnostics inherited from V3.

| Rule | Initial specification |
| --- | --- |
| Main NORMAL exit | `C < SMA21 AND m5 < 0`. |
| Slow-exit substitution | `C < SMA63 AND m21 < 0`. |
| Fixed trailing substitution | `C / max(C[t-62:t+1]) - 1 <= -0.15`. Close maxima, not unavailable intraday highs. |
| Volatility trailing substitution | Same 63-Close peak, with width `b = clip(2.5 * sqrt(5) * sigma21, 0.05, 0.20)`; `sigma21` is sample standard deviation of 21 daily log returns. Recommended initial contract: freeze this width at the causal signal that starts a NORMAL price-regime episode, including initialization, and retain it until a valid new NORMAL episode. Do not reset it merely because the calendar month changes. |
| FAST recovery | `C > max(C[t-5:t]) AND C > SMA10 AND m5 > 0`. The maximum excludes today's Close; otherwise strict breakout is impossible. |
| SLOW recovery | `C > SMA63 AND m21 > 0`, **and the arm's NORMAL exit is false**. |
| REBOUND failure | `C < SMA10 AND m5 < 0`. |
| Probe/full capital | Half/full of a nominal 50% slot: target 25%/50% NAV, constrained by actual available cash. Remaining capital stays at zero yield. |

The exact constants are transparent analyst choices, not estimates of an optimum or quantities validated by the cited papers. Volatility scales the distance of one barrier; this is not ATR, because accepted high/low data are absent. Using a 21-day peak only in `VOLTRAIL` while retaining a 63-day peak in `TRAIL15` would change two mechanisms. An alternative ratcheted stop is coherent only if its initialization, ratchet, and reset rules are separately frozen; do not silently combine it with the fixed-width comparator.

### State machine

Use `NORMAL`, `OFF`, and `REBOUND` price regimes, with an independent record of the account's executed slot state and pending instructions.

1. **NORMAL → OFF:** a declared exit emits a sale of the affected actual holding. Existing holdings remain real until the sale executes. When both slots are off and both sales fill, the account can be fully in cash.
2. **OFF → NORMAL:** SLOW confirmation may restore a full slot. In `EXIT21_MONTHLY` this is considered only at the monthly decision; in `EXIT21_SLOW` it is considered daily. SLOW takes precedence over FAST when both are valid.
3. **OFF → REBOUND:** FAST may restore the same monthly selected target. `FAST` enters a full slot; `STAGED` enters half a slot. The original exit condition is suspended during REBOUND; otherwise a rebound below its old long-trend or trailing reference can be immediately stopped out again.
4. **REBOUND → OFF:** REBOUND failure exits the position. **REBOUND → NORMAL:** valid SLOW confirmation restores full exposure and the normal exit rule.

Exit takes precedence over entry/promotion. In particular, SLOW can be true while EXIT21 is also true: a price may sit above SMA63 but below SMA21 while `m21 > 0` and `m5 < 0`. Without the explicit compatibility check, the slow recovery rule can undo a valid exit immediately. The same issue exists when SLOW is true but the chosen trailing barrier remains breached.

No extra five-session minimum hold is needed initially: it introduces another arbitrary delay and may defeat the rebound hypothesis. However, a probe cannot be promoted until **at least one Close strictly after its actual first buy fill**. For an Open fill, that session's later Close qualifies; for a Close fill, the same timestamp does not. An unfilled or merely signalled probe cannot be promoted. This distinction is essential under LAG2 and missing quotes.

At monthly refresh, preserve the regime of an unchanged identity. Changing slot order is not a new position and must not reset a stop or recovery clock. A different monthly target is assessed under the frozen admission/state rule. Log entry blocks as such, separately from executed risk exits. Applying global price regimes to unheld assets is causal; interpreting their hypothetical exposure as actual account state is not.

## Fresh opportunities

First offer the vacant slot to its currently selected monthly target under the appropriate recovery rule. Only when that route is unavailable should the fresh-opportunity arm search the **existing emerging-candidate rules**, with unchanged liquidity eligibility, percentile definitions, acceleration ordering, trend conditions, and deterministic tie breaks. The ranking engine must not learn from the realised cash episode.

For `FRESHW`, evaluate at the existing weekly Close schedule; `FRESHD` changes only this evaluation cadence. A candidate must be distinct and have trailing 126-return correlation at most 0.85 with **every remaining actual holding and every other committed slot/pending buy**, not merely the historical monthly leader. For simultaneous vacancies, process a frozen slot order and reserve the first candidate before evaluating the second. Record every rejection and the resulting cash vacancy.

Vacant means the old position has actually sold; a sell instruction, absent opening quote, or nominal zero target is insufficient. Do not replace a half-invested probe or add a third exposure. Buy a fresh opportunity initially at half a slot even if its global price regime is already NORMAL, then apply the same post-fill confirmation rule. Keep that identity until the next monthly refresh or its exit; do not repeatedly switch to each new highest acceleration name. A monthly refresh and a fresh-fill decision on the same Close must be resolved in that order, with no second action that contradicts the new monthly assignment.

## Execution and accounting safeguards

The existing `engine.py` deliberately exposes a **sell-only** guard. It cannot implement reentry safely by relaxing its addition check alone. Use an explicit event/action contract, with immutable signal time, maturation time, affected assets, target intent, and reason. Actual holdings, cash, fills, deferred instructions, global regime, and local probe state all need audit records. [L4]

- Next available accepted Open is the executable price; there is no fill at a barrier or signal Close. Every gap and every deferred sell remains part of the account's loss. Keep the existing lag/cost conditions and price-source qualifications.
- Off-calendar actions must preserve untouched quantities. The archived guard passes unchanged **Close weights** into a forced rebalance, then clamps targets at opening weights. This prevents buys but can still sell an untouched winner after an opening gap increases its weight. An action mask is needed to avoid this unrequested extra rebalance; otherwise it must be disclosed as a different policy. [L4–L5]
- A reduction never buys. A recovery buys only the nominated asset(s), from available cash after fees; it must not sell unrelated assets to force a nominal 50% target. Monthly full rebalances retain their original semantics.
- A new future instruction cannot cancel or rewrite today's already matured instruction. Repeated alerts must not indefinitely postpone an exit. Conversely, a stale queued buy must not resurrect a target invalidated by a newer matured instruction.
- Changes of holdings, wealth, and fees must be self-financing. Update execution-dependent clocks from actual fills. Record partial/deferred completion rather than assuming a target vector was achieved.

## Breadth, drawdown and cash opportunity cost

Do not initially add a market-wide timing veto. Raw breadth over 2,096 ETF listings overweights duplicated themes, and a broad equity index is a poor common risk proxy for gold miners, energy, volatility futures, bonds, and country funds. If breadth is later studied, use frozen economic/correlation groups with one vote per group, and define its independent mechanism before viewing its returns. For this study, record selected-target breadth and actual risk exposure descriptively.

Avoid making recovery conditional on the **actual cash account recovering its previous NAV peak**: with zero-yield cash, that condition cannot clear. A hypothetical fully invested target basket can provide a price signal, but must be labelled and must never replace actual portfolio weights or NAV. Persistent drawdown is a reason to inspect the source of losses, not proof that selling or buying now has positive expected value.

For each exit/probe/reentry, log signal-to-fill delay, executed cash duration, old and new quantities, gap loss, fees, and return to the next fixed 21-session endpoint. Add matched-state continuations starting from the same pre-event units, cash and queue, with/without the action. Report avoided losses **and missed positive returns**, including the original target's best rebound sessions while cash was held. For fresh fills compare against both cash and same-target recovery from that identical account. Event means are descriptive, not composable CAGR contributions; retain the full self-financing path as the primary result.

## What would falsify the proposal

The practical objective requires **higher BASE CAGR and a less negative sampled drawdown than BASE**, after costs; crossing 30% alone is insufficient. Report the original absolute goal separately. A candidate that only lowers exposure must also be assessed against `STATIC_HALF` and `STATIC_75` and on exposure, fees and operational days.

Evidence against promotion includes: a lower drawdown bought entirely by lower return; recovery lag erasing most saved losses; repeated REBOUND failures consuming the improvement; fresh replacements damaging the paired same-target comparison; an advantage disappearing under doubled costs or one/two extra sessions; or all of the advantage residing in a single inspected episode. Retain every year, particularly 2021, 2022, 2024 and partial 2026, and the previously declared descriptive segments. Operational frequency is an explicit outcome; do not quietly present daily monitoring as monthly trading.

Full-sample, annual and block-bootstrap evidence remains exploratory: all 2020–2026 observations and the prior failures have already influenced the design. No recycled segment becomes a pristine holdout. Provider adjustment vintage, current-catalogue survivorship, retrospective completed-day volume filtering of accepted Opens, venue turnover, and absent intraday extrema remain inherited limitations. [L1–L3]

## Primary research and traceability

These papers motivate questions, not the chosen thresholds or achievable ETF returns. Retrieval date: 15 November 2026.

| ID | Primary source, retrieval reference, implication |
| --- | --- |
| W1 | Kaminski & Lo, *When Do Stop-Loss Rules Stop Losses?*, JFM 2014. [MIT manuscript record](https://dspace.mit.edu/entities/publication/bb69ca4b-0cdc-487f-831d-63b2e84fafee), retrieval `turn139view0`; [publisher abstract](https://www.sciencedirect.com/science/article/abs/pii/S138641811300030X), retrieval `turn142search2`. Under their model, stop value depends on return dynamics: random-walk exposure reduction sacrifices expected return, while persistence can support a positive stopping premium. This makes the paired cash/reentry cost test central. |
| W2 | Daniel & Moskowitz, *Momentum Crashes*, working paper 2014 / JFE 2016. [Author's university manuscript](https://business.columbia.edu/sites/default/files-efs/pubfiles/4607/mom11.pdf), retrieval `turn143view1`; [NBER](https://www.nber.org/papers/w20439), retrieval `turn138search4`. Their momentum crashes coincide with rebounds after panic conditions, substantially through loser-side short exposure. This is a warning about reversal regimes, not direct evidence that long-only ETF cash reentry has an edge. |
| W3 | Moreira & Muir, *Volatility-Managed Portfolios*, JF 2017. [Publisher](https://onlinelibrary.wiley.com/doi/abs/10.1111/jofi.12513), retrieval `turn140view3`; [author manuscript](https://amoreira2.github.io/alan-moreira.github.io/VolPortfolios_published.pdf), retrieval `turn138search8`. Their factor volatility-management evidence motivates a risk-scale comparison; it does not validate a volatility-scaled trailing stop or guarantee CAGR improvement. |
| W4 | Cederburg, O'Doherty, Wang & Yan, *On the Performance of Volatility-Managed Portfolios*, JFE 2020. [Author's university paper](https://www.lehigh.edu/~xuy219/research/COWY.pdf), retrieval `turn143view0`. Across 103 equity strategies, direct comparisons do not show systematic superiority; implementable out-of-sample combinations weaken relative to ex-post spanning results. Do not learn overlay weights from the same sample. |

Local evidence read: **L1** `olc109/README_IT.md` and `RAPPORTO_OLC109_IT.md`; **L2** `docs/DESIGN_AND_PROTOCOL.md`, `docs/STAGE2_PROTOCOL.md`, `src/dedup_selectors.py`, `src/cluster_selectors.py`; **L3** `research/failure_diagnosis/DIAGNOSIS_V3.md` and `research/prior_repo/PRIOR_EVIDENCE_AND_FUSION.md`; **L4** `src/engine.py`; **L5** `source/src/core.py::rebalance`. No new performance estimate has been calculated for this memo.
