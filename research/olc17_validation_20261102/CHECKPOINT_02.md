# OLC17 checkpoint02 — actual decisions and holdings-consistent V6

2November2026. Candidate still frozen, zero new fits. All17EU/13USA final-pair disagreements in2021–June2026 traced against TOP2_STATIC_REVALUE. Saved per-decision tickers, actual entry/next-entry boundary, unchanged common forward21/42/63 outcomes when complete, paired portfolio log PnL, stop counts and arithmetic components.

Key exampleEU: signal2022-02-28 candidateEXV6.DE/VVSM.DE versus staticVVSM.DE/XB4A.DE. Actual entry2022-03-01, next-entry boundary2022-04-01. Legacy interval returns+5.1050% vs-.7877%, paired log advantage+.057698; candidate has0stops, static1. Both-preopen returns+2.9320% vs+2.1681%, paired log advantage+.007450. Same chosen pair; altered risk execution changes how much benefit is realized. Arithmetic components are conditional on actual paths, not a unique causal decomposition.

USA example signal2021-05-28: ICLN/TAN vs ICLN/IWN. Following entry-to-entry legacy returns+7.3279% vs+.4879%; paired log+.065851. Both-preopen+7.3376% vs+.4878%; paired log+.065943. Neither has a stop. The US advantage is not exclusively a same-open stop effect.

Main2021–2024 candidate-minus-static annualized log contributions, legacy:EUtotal1.6581pp, primary1.3959, direct-stop.1877, remaining frictions.0745. USA total3.7608pp, primary3.5551, direct-stop.2095, small defensive/friction offsets. Both-preopenEUtotal.0261pp, primary.1281, stop-.1166; USAtotal5.9459pp, primary5.9580, frictions-.0121. Stop effects also propagate into later primary units, so direct-stop component alone is not the total policy effect.

Concentration remains: against same-static, legacy2021–24 has11positive/13negative/24unchanged monthsEU and9/7/32USA. Three best differential months exceed the total log advantage in each market. This is a diagnostic, not deletion of months or a trading rule. Both-preopen does not make this a dispersed effect.

## V6 consistency
The frozen alternate stream can name a primary holding in the new strategy. InEU2022-07-21/22, ORIGINAL,STATIC_REVALUE andCONTEXT_REVALUE allocate an additional5.5%toVVSM.DE even though it is already primary. The originalV6 source explicitly excludes primary names.

Initial generic reconstruction reproducedUSA exactly but mismatchedEU on3dates; it used an inappropriate EXSA proxy and filled/missingness scope. We did NOT use that version for outcomes. Retrieved the actual European adapter from the verified Original39 checkpointSHA256826d2b03865e58317e6edb4aa920cc309d3fcfa164d3779499a648b1620b98b8. It retains genuine rawClose missingness, adds realSPY strictly before theEUdate as a nontradable reference, and excludes nonobserved candidates. With that exact contract, parentV6 streams reproduce exactly in BOTH markets. No threshold or parameter was tuned.

Then recomputedV6 for each actual primary pair using unchanged original criteria.32additional paths,112total in this validation block. Conditional-stop/exposure predicates and other risk streams unchanged within each comparison. All recalculated alternates exclude primary names. Initial NPZ ticker storage used object dtype and was rejected by allow_pickle=False; regenerated as Unicode and verified by two failing-then-passing tests. No label or price was changed.

Main2021–24,cost.001,holdings-consistentV6:
LEGACY candidateEU24.0032%/USA44.1531% vsstatic21.9641/38.8325 andCUM_FIT22.7526/38.9756.
BOTH_PREOPEN candidateEU20.3754%/USA52.3006% vsstatic20.3440/43.5088 andCUM_FIT20.7728/44.3462.
Thus the V6 mismatch is real but economically small here; repairing the integration does not explain away the main candidate result or resolve the European timing dependence.

11new tests pass(3expected insufficient-history numpy warnings),19parent tests pass. Final clean restoration/artifact preservation remains pending at this checkpoint. Source changes are confined to isolated validation; no main modification or candidate parameter change.
