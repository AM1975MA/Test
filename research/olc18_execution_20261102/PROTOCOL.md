# OLC18 — separate stop eligibility, triggering and execution

2026-11-02. User authorizes continuation after OLC17. Parent2e715c294067ff52015cf946008d1226290e9a2d. Preserve ORIGINAL,CUM_FIT,TOP2_STATIC_REVALUE,TOP2_CONTEXT_REVALUE, all rankings/contexts/models and risk thresholds. No model fit, no main merge or trading. New isolated workspace. OLC17 archive63248847bytes SHA2563789bfda78e6f858c2dde85fa07f3d9823e878a07f3d823eeac32640d48e3187 is authenticated.

## Question and rationale
OLC17 localized European sensitivity to same-opening market confirmation of otherwise prior-close conditional stops. Test whether a simpler predeclared protection or an explicitly delayed daily alarm gives a more interpretable integration. Do not optimize a stop threshold or select different policies by market. A stop trigger is not a guaranteed fill; daily OHLC cannot certify exact intraday execution, liquidity or availability. SEC Investor Bulletin Stop/Stop-Limit/Trailing Orders and FINRA Understanding Order Types establish that distinction, not financial validation of our simulation.

## Fixed eight contracts
Use candidate-consistent V6 from OLC17 in every path. Nominal50/50,IMMEDIATE. Retain global prior-close gross,3-session cooldown and remaining engine logic.
1.LEGACY: current-gap exposure and stop activation; exact OLC17 LEGACY_V6 reference, not a live claim.
2.PREVIOUS: preceding-session gap/breadth for exposure and stop activation; exact ALL_PREOPEN_V6 control.
3.PREVIOUS_UNIFORM: same as2 but uniform10bp adverse stop-fill friction, including opening gaps; isolates fill-cost convention.
4.PREARM_WEAK: exposure uses preceding-session information. Eligible stop names determined by unchanged prior-close UH or SA. No current or previous market-breadth permission. Barrier priorClose*(1-.055), armed before the next session; fill proxy=min(Open,barrier) when observed Open/Low indicates trigger. Uniform10bp adverse friction. For new purchases the same planned barrier is conditional on entry; record same-day entries and already-breached opening fills rather than claiming auction-perfect bracket execution.
5.PREARM_ALL: as4, but all primary holdings eligible, no weakness gate. Same threshold and10bp friction. This is a distinct risk policy, not a prediction improvement.
6.EOD_LOW: exposure uses preceding-session information. At completed close, evaluate current market-gap confirmation, prior-close weakness and whether the completed session Low crossed the barrier. Exit at next observed Open, not retrospectively at barrier. This is a completed-day alarm, not an intraday stop.10bp adverse friction.
7.EOD_CLOSE: as6, but completed Close must breach the barrier. Distinguishes transient crossings from closing deterioration.10bp adverse friction.
8.NO_STOP: exposure uses preceding-session information, no stop; diagnostic ablation, not a recommended unprotected strategy.

For6/7 a signal cannot depend on the next Open; that price is only execution/valuation. Executions at the next Open occur before that opening's ordinary rebalance; stop cooldown is known from the previous close. Accounting must declare boundary timing and charge sale once. A missing observed next opening must not be silently filled with a stale mark: defer with an explicitly tested queue or block and disclose that replay if the simple implementation cannot fulfill it. No future-known candidate filtering.

Base matrix8contracts*4rankings*2markets*2legacy rebalance fees(.001/.003)=128 planned paths. Fill stress: policies4–7,50bp stop friction,fee.001,both markets,all4rankings=32 additional paths. Total160 planned, counts reported only after verification. All combinations frozen before outputs. No wider parameter sweep after inspection. Rebalance-cost convention remains half-L1,not per-side certification.

## Event evidence before policy decision
Log eligibility, bar trigger, planned barrier, opening versus intraday trigger, carried versus just-rebalanced quantity, next-Open execution, friction, missing-price status, and next scheduled rebalance. Independently count confirmed versus intraday-unobservable legacy events; gap below barrier must never fill at a better barrier price. FullC/rawmissing/USAobserved-mask limitations remain inherited. Under prearmed stops, discontinuous intraday gaps can still fill worse than barrier;10/50bp are sensitivity assumptions,not calibrated worst-case bounds.

Evaluate main2021–2024 and all2019–July2026/annual/2020crash windows; actual valuation dates,initialwarmup disclosed. Metric interpretation: growth,drawdown,turnover,stopcount,adverse episodes and candidate-minus-matched-static plusCUM_FIT. Do not choose by largest historical CAGR alone. Arithmetic decomposition is conditional,not unique causality. Common monthly bootstrap may describe uncertainty; no zero-containing interval automatic veto and no posterior success claim. History already searched.

## Verification and preservation plan
1.Verify parent manifests and11+19tests; preserve unchanged parent.
2.Write RED tests for eligibility, gap fill, delayed next-Open execution, nofuture decision, fee once and disabled stop. Implement minimal instrumented engine separately and watch GREEN.
3.Exact full-array parity for32parent reference paths; fresh independent holdings/cash reconstruction and metric calculation on all new paths. Stop-event log reconciles ledger exactly. No fit changes.
4.Summarize structural policy tradeoffs,not universal optimum. Intraday validation, large context nulls,nested robustness andprospective testing remain separate unfinished blocks.
5.Save tested modules, protocol andresults onresearch branch; full checkpoint andhash manifest inLibrary if upload succeeds. Verify clean restore. No background execution promise or claim allbinariesareGitHubassets.
