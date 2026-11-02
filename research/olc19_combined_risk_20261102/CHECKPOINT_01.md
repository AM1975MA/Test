# OLC19 checkpoint01 — first fixed matrix complete

2 November2026. No new ETF/model fits.128registeredpaths completed:96base+32stopfrictionstress.48parentcontrolpaths exactly reproduce OLC18BASE(NO_STOP),ALARM(EOD_LOW_NET),FAST_NOLOCK(PREARM_ALL) acrossbothmarkets,rankings,costs.240576bookintervals reconciled.15newtests and31parenttests passed before replay. Full saved-path reloading/cleanrestore still pending atthis checkpoint.

Structural finding: COMBINED_NOLOCK equals FAST_NOLOCK and COMBINED_LOCK3 equals FAST_LOCK3 in the candidate's observed portfolios. The ordinary alarm requires the SAME daily barrier plus extra weakness/market conditions; fast stops apply to every primary name and set the same cooldown. Thus an ordinary alarm adds no risk reduction once that fast policy acts. This is not evidence that ordinary alarms generally have no value. Do not tune a new barrier after observing the table; explicitly diagnose logical nesting first.

Candidate2021–24,fee.001: ALARM CAGR22.0869%EU/45.5074%USA,DD-24.0404/-20.6148;FAST_NOLOCK23.231%/47.485%,DD-27.703/-19.980;FAST_LOCK3~23.200%/50.772%,DD-28.608/-20.226. Lock3 reduces primary stops12->10EU,50->40USA. Its cost in Europe cannot be hidden by USgrowth.

FullFebruary2019–July2026,candidate,fee.001: FAST_NOLOCK18.778%EU/34.925%USA;FAST_LOCK3~19.764%/39.484%,DD-28.608/-26.120. ALARM18.573%/39.554%,DD-29.447/-34.214. These are policy-contract simulations with bar-price proxies,not live expectedreturns. All4rankingcontrols and adverseperiods are retained. Same-day buy/stop and missingquote assumptions must be disclosed.

No alpha,barrier,locklength orrankingparameter optimized;3sessions inherited as predeclared control. Larger50nullcontext study,data certification and fullorderexecution remain separate roadmap blocks,not completed here. Original/CUM_FIT/contextualcandidate unchanged ontheir parentbranches;mainunchanged.
