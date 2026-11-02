# OLC18 — completed stop-contract investigation

2 November2026.192distinct accounts,zero new fitting, frozen ranking candidate and unchanged main. This completes the registered stop/execution block, NOT full strategy certification. No combined emergency-stop plus EOD policy was developed or validated here.

## Fixed contracts and chronological evidence
Protocol5b0f57e6a7a6e06bab0a37d7f7c30cb5ea308642 preceded the first160paths. It fixes8contracts,4ranking controls,2markets,2rebalance costs (128paths),plus32predeclared .005stop-fill stress paths. After observing immediate gross-sale/repurchase, net-target extension ca6ea619b441ace8174d61bb64859fd5e9a0a901 registered32additional paths before their outcomes. This is post-observation exploration,not an independent holdout.

All contracts use holdings-consistentV6,IMMEDIATE,nominal50/50,unchanged forecast/feature/ranking/memory and stop threshold priorClose*.945. That threshold is5.5%below PREVIOUS CLOSE,not entry or peak and not a maximum-loss guarantee. The original gap-based exposure/stop contract remains only a reference.

PREARM_WEAK/ALL place protection before the session using prior-close weakness/all holdings,respectively. Daily-bar proxy fill is min(Open,barrier),with10bp adverse friction and50bp stress. Intraday gaps or poor liquidity can produce worse fills; these are not statistical worst-case bounds. Same-day entries and barriers already crossed at opening are logged,not declared auction-perfect bracket executions.

EOD_LOW uses completed-day market/weakness/Low information then exits at next observed Open. EOD_CLOSE requires the Close below barrier. Their decisions never use the next Open. They are completed-day alarms,not intraday stops. Gross-fill replay fails rather than invents stale next-Open execution; no historical replay was blocked. USA lacks the original full observed-quote mask,so absence of stale marks is not certified.

## Main architectural finding: the alarm requests exposure, not necessarily liquidation
Inherited cooldown targets25%primary gross for3sessions,does not ban the ticker. In2021–24 all4EU and7USA candidateEOD_LOW exits are followed by a positive rebalance in the SAME ticker at that execution opening (audited before any later intraday stop). A gross sale and immediate repurchase is unnecessary if one can trade the net change to the desired holdings.

EOD_LOW_NET/EOD_CLOSE_NET retain overnight holdings,record alarm at close,and execute only the net ordinary target change next opening. Standalone stop-fill count iszero because these are alarms; alarm counts are recorded separately. No special stop fee/slippage is charged for a nonexistent separate liquidation,but ordinary net-order trading costs remain. True auction impact and exact sizing at an unknown opening price are still unverified.

All16real zero-friction gross/net comparisons across4rankings*2markets*2alarms agree within8.88e-16 NAV. Netting is operational simplification,not new rankingalpha. A repeated-alarm bug in the first net implementation was caught by real zero-cost verification and a RED synthetic test: it failed to refresh target when gross was unchanged. force_target correction passed GREEN; all32netpaths recomputed. Erroneous provisional outputs are logs/net_before_fix only,excluded from finalscorecard.

## Main2021–2024, EOD_LOW_NET, fee.001
Costs retain legacy half-L1 turnover convention,not calibrated per-side commission. CAGR252sessions; actualOpen-to-Open valuation dates. Figures are historical simulations,not expected returns.

|Ranking|CAGREU|MaxDDEU|CAGRUSA|MaxDDUSA|
|---|---:|---:|---:|---:|
|ORIGINAL|22.2160%|-21.4580%|40.8675%|-23.5302%|
|CUM_FIT|21.1149%|-29.3518%|41.9458%|-18.6710%|
|STATIC_REVALUE|20.4910%|-24.4608%|40.8918%|-20.6148%|
|CONTEXT_REVALUE|22.0869%|-24.0404%|45.5074%|-20.6148%|

Candidate beats same-memory static by1.596/4.616 CAGRpointsEU/USA,andCUM_FITby.972/3.562. EU is still slightly belowORIGINAL; USA risk not universally better. With fee.003 candidate19.7118/41.8696 versusstatic18.0310/37.4006 andCUM_FIT18.6539/38.4492. This shows the candidate advantage does not require retrospective same-open stop filling in this primary window,NOT universal validation.

EOD_CLOSE_NET candidate22.0978%EU/49.8994%USA,DD-24.0130/-20.1931. It losesEUtoCUM_FIT22.4102%;we do not choose it merely for49.9%USA.

## The cost of delayed protection
Full February2019–July1,2026 candidateEOD_LOW_NET CAGR18.5734%EU/39.5539%USA,DD-29.4465/-34.2143. Legacy candidate18.2303/44.7467,DD-32.0893/-25.5261. EOD_CLOSE_NET19.5024/42.8318,DD-28.3987/-34.2143. No single policy dominates growth and tail risk.

February–March2020 ACTUAL PERIOD RETURNS (notCAGR):
|Contract|EU|USA|
|---|---:|---:|
|LEGACY|-22.2407%|-6.1584%|
|PREVIOUS|-19.9574%|-15.0038%|
|PREARM_ALL|-14.1127%|-13.8423%|
|EOD_LOW_NET|-20.1353%|-20.5991%|

2019–20 precedes contextual adaptation; same initial weights,so these differences are risk-policy effects,not newly proved regime recognition. PREARM_ALL improves some crisis outcomes but generates50USAcandidate stops in2021–24 versus7legacy,126overfullhistory;fullUSACAGR34.9253%.26of50main stops close above barrier later that day: ex-post recovery description,not a claim these could have been predicted. 2025EU remains worse thanCUM_FITacross tested contracts.

## Conclusion
Keep contextual ranking and net daily exposure-alarm contract as research candidates. Separate selection, planned exposure and fast emergency protection. The last remains unresolved; no universal threshold or combined design is selected. Do not remove protection to maximizeCAGR. Do not promotePREARM_ALLfromonecrash orEOD_CLOSEfromonehighreturn. Larger contextnulls,nested robustness andprospective validation remain unexecuted blocks.

EOD_LOW_NETcandidate-minus-static annualizedmonthlylog differenceEU1.3393pp,descriptive95%CI[-3.5687,6.2394];USA3.2139pp,[-2.8826,9.2166]. Paired6monthblocks,4000draws,48months,reusedhistory. Not posterior probabilities or all-experiment multiplicity correction; zero is not automatic veto.

## Fresh verification and source identity
31newtests;30inheritedtests with3knownV6initial-historywarnings in separate roots.192savedpaths replayed with finalcode,allarrays exact;32parentreferences exact.360864bookintervals and7488metricvalues independently recomputed,maxerrors1.78e-15/2.12e-13.12future-prefixchecks,16zero-costgross/netpairs. Author review,not external audit.

All5source modules individually stored onGitHub and their Gitblobhashes match executedlocalcode at df957c00dca88bdc345f47b604be5ebac9633712.3testfiles andpytest.ini also versioned. Final chart is a staticPNG; the user-visible Python rendering endpoint failed,but the container-rendered image was opened and inspected.

## Actual persistence and clean restore
Library /ETF_Research/OLC18_Stop_20261102, all4uploadoperations returned succeeded:
- OLC18_Stop_Checkpoint_20261102.zip:148775736bytes,SHA25644b043029c426602e9318decad7c395c73ab60bd664f6a011a78ae47334c1e44;library_file_id libfile_07627e03f3cc81918945a3e3cd7f7b9c;file_id file_00000000fea481f4952b59578ea2ed99.
- OLC18_Stop_Risultati_20261102.zip:1782331bytes,SHA25675f9d55ac4bb09c6f43e60357233324b4d30dc4c0835391d17adf8520d132c5e;library_file_id libfile_bc763feb55ac81919ff65b5cd2b0a97d.
- OLC18_Report_Stop_20261102.md:library_file_id libfile_83d1f030599c819196062020f56de12b.
- OLC18_Restore_Verification.json:library_file_id libfile_d1c763666acc8191a1fc8fa8c463ed04.
These binaries are NOT GitHubreleaseassets. The manifest does not substitute for theirupload.

Clean restore:948individual file hashes verified,31tests passed,4representative actual accountreplays allarraysidentical(EUnetLow,USAnetClose,EUprearmed50bp,USAgrossEODLow). Separate from192workspaceverification. Complete checkpoint includes authenticatedparent,preparedinputs,all192paths/events/tests/source;autonomousforOLC18,notraw-market-dataorETFbase-trainingcertification. Reports/restoremetadata are inspectable separately.

Retained limitations: survivoruniverse,totalreturn/distributions/FX,liquidity,spread/marketimpact,same-auctionfractionalsizing andintradaychronology notcertified. SEC/FINRAstop-orderdocumentation is methodologicalguidance,notvalidationofourreturns. No main change,no live order,no background process.
