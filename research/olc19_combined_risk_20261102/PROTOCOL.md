# OLC19 — ordinary net alarm, fast protection and explicit reentry

2 November 2026. User approved ETF_Roadmap_Post_OLC18_20261102.md. First executable block of that roadmap, not a claim that all stages are complete. Parent adf38a42da93bf4137275da9199df7d90eab53f7; OLC18 checkpoint SHA25645000d14077625424c917afd32fcfceaa440044d2e5e817b5d599b87a3a83f31,148775757bytes,948member hashes verified. No main merge, orders, new ranker fits or threshold optimization.

## Frozen strategy and information
ORIGINAL,CUM_FIT,TOP2_STATIC_REVALUE,TOP2_CONTEXT_REVALUE. Same prepared prices,forecast pairs,50/50 target,prior-information systemic exposure,gross,V6 consistent with proposed pair,calendar and cost convention. Holdings removed by emergency are NOT replaced by another ticker or extra V6. Their target budget stays defensive. No change to candidate or same-metadata labels. Equity data/FX/survivorship/intraday/USA-observed-mask and same-auction fractional-size limitations remain open. This tests daily-bar execution contracts; it does not certify genuine intraday fills.

## Fixed design
Six contracts:
- BASE: no ordinary alarm or fast exit; reproduce OLC18 NO_STOP (other risk controls remain).
- ALARM: EOD_LOW_NET alone; reproduce exact OLC18 arrays.
- FAST_NOLOCK: prearmed stop on all primary holdings, no per-ticker exclusion; reproduce PREARM_ALL.
- COMBINED_NOLOCK: same fast stops plus EOD_LOW_NET. Isolates combination before adding exclusion.
- FAST_LOCK3: fast stops with stopped ticker ineligible at the next3 session openings; earliest reentry k+4 after stop on session k.
- COMBINED_LOCK3: both protections and identical ticker lock.

Fast barrier always .945*priorClose,not entry/high-water mark. Gap fill proxy=min(Open,barrier),adverse friction .001; stress .005. No fill guarantee. Newly purchased quantities and opening-breach round trips explicitly logged as execution limitations,not hidden. Primary holdings only,not a stop on defensive sleeve.

Ordinary alarm is evaluated at completed close from prior-close weakness,completed-day gap breadth/systemic predicate and observed opening/Low crossing,for positions held just after today's ordinary rebalance. When fast protection has already sold a position the same day's alarm can still request reduced exposure; emergency has priority. No nextOpen value is used by the alarm. It requests net25%primary gross for3future sessions under inherited cooldown. The two triggers share the max cooldown,never add durations.

Lock3 is ticker-specific; ranker proposals remain unchanged. Remove a locked ticker's original target mass without redistributing it to the other name; normalize the surviving target only after multiplying gross by its retained mass. Always preserve capital weights. A later monthly proposal cannot bypass lock; a genuinely different ticker may use its own original target share. Locks on primary tickers suppress any overlap in defensive alternate allocation. Ordinary alarm alone does not lock tickers. Missing observed quote defers entire ordinary rebalance; report target/actual divergence.

States reported NORMAL/REDUCED/EMERGENCY/REENTRY. EMERGENCY includes active primary exclusions or current fast exit; REDUCED includes cooldown/other gross restriction; REENTRY flags actual positive trade in a previously stopped name after expiry,not merely a timer expiry. Reentry uses the current unchanged proposal and risk budget; no price-dependent recovery condition or new ramp is fitted. This simple timed rule is a hypothesis,not an optimum. The initial fixed duration3 is inherited from cooldown,not selected on results.

## Matrix and comparisons
6contracts*4rankings*2markets*2rebalance-costs(.001/.003)=96paths. Fast4contracts*4rankings*2markets,fee.001,stopfriction.005=32stresspaths.128planned,reported only after completed verification. Full fee .001/.003 uses original half-L1 convention and stop sale fee; not per-side live costs. No additional threshold search after outputs.

First compare BASE/ALARM/FAST_LOCK3/COMBINED_LOCK3 as2x2; also LOCK3 vs NOLOCK to isolate reentry restriction. Report interactions,not arithmetic sums of standalone benefits. Identical contracts for both markets; no per-continent winner selection. Primary2021–24;fullFebruary2019–July1,2026;yearly;February–March2020,October2021–December2023. 2019–20 is pre-context-adaptation; no attribution of crash performance to context.

Native layer metric unchanged because no forecasts are refit; this lot evaluates risk/order/reentry tasks. Measures: netgrowth,MaxDD,dayloss tail,CVaR5,worst5/21interval return,time underwater,recovery,cost,turnover,stop/rebuy/lock/blockedquote counts. Describe foregone returns of locked names as diagnostics,not ex-post labels usable to trade. Paired monthly log differences,circular6-month blocks4000seed20261102,common calendar; no automatic rejection for zero-including intervals,no posterior probabilities,no pristine holdout claim.

## Tests and preservation
Write failing state-transition/target-mass/cooldown/gap/prefix tests before implementation. Minimal patch to authenticated parent code.48parent control paths must reproduce full arrays (BASE,ALARM,FAST_NOLOCK across both fees/markets/rankings). Independently reconstruct opening/nav from quantities,cash,fees andnextprice; event ledger reconciles; all models/savedpath reloads verified. Negative tests with repeated alarms,new proposals during lock,missingquotes and renewed stops. Clean restore required; self-review not independent external audit.

Save executable code,tests,protocol and summaries individually on research branch and complete binaries in persistent Library with byte hashes. No claim manifest equals uploaded binary. Separate future blocks:50blocked-context nulls with nested reselection,full raw-data certification,realintradayorder audit andshadow campaign. They are not implied complete by this risk experiment; no background execution promised.
