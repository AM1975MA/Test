# OLC19 — first roadmap block complete, no strategy promotion

2 November 2026. Candidate and main unchanged. Zero new model fits. Protocol bfe8db8b2c9a3485573de1fae20c449b7f0db1d5 registered before outputs; parent adf38a42da93bf4137275da9199df7d90eab53f7. Full Italian report is in the delivered and persistently uploaded artifacts; this is the compact GitHub result record.

## What was implemented

128 distinct paths: six risk contracts x four frozen rankings x two markets x two rebalance fees =96, plus32 adverse stop-fill stress paths. Same original forecast proposals, ranking, memory and context; no threshold, lock duration or model search. Prearmed barrier remains .945*previousClose, not entry price or trailing high. Fees .001/.003 retain the original half-L1 turnover and stop sale commission; adverse stop friction .001/.005 is10/50bp, not a guaranteed fill bound.

Explicit ticker lock after fast exit: stopped on session k, cannot be repurchased at openings k+1,k+2,k+3; earliest admissible k+4, only if still selected and quote available. Excluded target weight is NOT reassigned to the other ticker or V6. Reentry is recorded only on a real simulated increase in units, not timer expiration. States NORMAL/REDUCED/EMERGENCY/REENTRY describe operation, not estimated market regimes. Three sessions are a predeclared inherited-duration control, not an optimum.

## Structural finding

COMBINED_NOLOCK=FAST_NOLOCK and COMBINED_LOCK3=FAST_LOCK3 for all48 matched economic paths, including cost stress. Capital, holdings, fees and target arrays are identical; only alarm telemetry differs. The ordinary EOD alarm uses the same barrier plus stricter weakness/market conditions, while fast protection on all primary holdings already triggers and imposes the same cooldown. Thus this combination adds complexity, not independent protection. This does not imply ordinary deterioration alarms are generally useless. A genuinely distinct early deterioration signal has NOT been implemented as a post-result rescue.

## Same contextual candidate: base costs

2021–2024,IMMEDIATE,50/50nominal:
|Risk contract|CAGR EU|MaxDD EU|CAGR USA|MaxDD USA|
|---|---:|---:|---:|---:|
|ALARM|22.09%|-24.04%|45.51%|-20.61%|
|FAST_NOLOCK|23.23%|-27.70%|47.49%|-19.98%|
|FAST_LOCK3|23.20%|-28.61%|50.77%|-20.23%|

The larger US CAGR is a retrospective policy outcome,not expected return or new ranking skill. EU drawdown worsens. Main stops fall12->10EU and50->40USA. With tripled rebalance cost LOCK3 gives19.88%EU/42.73%USA,MaxDD-30.48%/-22.07%. With50bp stop friction at base rebalance cost it gives22.60%/48.35%,MaxDD-29.04%/-20.81%.

Full February2019–July1,2026:
|Risk contract|CAGR EU|MaxDD EU|CAGR USA|MaxDD USA|
|---|---:|---:|---:|---:|
|ALARM|18.57%|-29.45%|39.55%|-34.21%|
|FAST_NOLOCK|18.78%|-28.13%|34.93%|-27.38%|
|FAST_LOCK3|19.76%|-28.61%|39.48%|-26.12%|

Full stops45->32EU and126->94USA versus FAST_NOLOCK. Relative to ALARM, USgrowth nearly unchanged and MaxDD magnitude falls8.09points;EUgrowth/risk improve on the full window. Not a uniform improvement in every period or metric.

February–March2020 actual period returns,NOT annualized: ALARM-20.14%EU/-20.60%USA;FAST_NOLOCK-14.11%/-13.84%;FAST_LOCK3-9.36%/-11.20%. These are risk-policy effects before contextual adaptation. Mean risky exposure before stops falls58.97->53.59%EU and63.82->57.70%USA versus NOLOCK: protection is partly less capital exposed,not predictive alpha.

## All rankings under identical FAST_LOCK3,2021–2024

|Ranking|CAGR EU|MaxDD EU|CAGR USA|MaxDD USA|
|---|---:|---:|---:|---:|
|ORIGINAL|20.80%|-22.81%|43.31%|-24.72%|
|CUM_FIT|23.82%|-28.53%|30.88%|-22.02%|
|STATIC_REVALUE|22.48%|-24.76%|37.07%|-20.36%|
|CONTEXT_REVALUE|23.20%|-28.61%|50.77%|-20.23%|

Contextual growth beats matched static in the primary window but EUrisk is worse. Full-windowEUcontext19.76% is belowstatic19.95% andCUM_FIT20.61%;USAcandidate39.48% versus31.73%/28.65%. 2025actualEUreturn17.95%candidate versus27.71%CUM_FIT/24.64%static. No per-market winning policy selected.

All stop/reentry episodes retained. Avoided decline and missed rebound both occur; e.g.XLE after2020-03-12 falls18.52% from nextOpen to earliest permitted reentry,UNG after2022-07-12 rises12.52%. These are chosen explanatory ticker moves,not counterfactual account gains or information known then. The finite lock is not a model predicting recovery.

## Inference and execution limits

Paired monthly6-block bootstrap,4000draws,seed20261102. LOCK3-minus-NOLOCK annualizedlog difference EU-.026points,95%[-.827,+.711];USA+2.198,[+.207,+4.396]. Not CAGR intervals,posterior probabilities or a correction for all previous research; zero is not an automatic veto. Many previously inspected periods and correlated markets remain limitations.

Daily-bar stop fills are proxies, not intraday verification. Same-opening fractional sizing remains inherited,not pre-auction fixed-share ordering. USA full observed-quote mask missing in parent; totalreturn/FX/distributions/delisted universe not certified.7of40mainUSA LOCK3 exits involve quantities increased that day;5are opening gaps. EU0of10increases,2gaps. Events are logged,not claimed automatically executable via auction brackets. SEC stop-order guidance distinguishes trigger and guaranteed fill; these simulation frictions do not eliminate that risk.

## Verification

19new tests,31parent OLC18 tests passed in their roots.128saved paths replayed with final code, all arrays exact;48original parent controls exact.240576 accounting intervals;4992base metric values plus9984additional risk values independently recomputed; maxerrors1.78e-15/1.48e-13/1.92e-15.16future perturbation checks preserve past decisions. Author review,not an external independent audit.

Five computational source modules and one19-test file individually onGitHub. All five remote blobs and test blob match the executed files at fdb17149fb3c446f6e68a026d10f233acba1487f. Parent948member hashes were verified before execution. Clean restore checks1513individual files,19tests and4representative true replays with all arrays identical; distinct from128workspace replays.

## Actual persistence

All six Library operations succeeded in /ETF_Research/OLC19_Rischio_Rientro_20261102:
- OLC19_Rischio_Rientro_Checkpoint_20261102.zip:165680538bytes;SHA2563b5799dae060c104408f581c70280cef8ce4d84c3978434d4e6ba81108f16540;library_file_id libfile_7a15283a9da08191bc611a65f11221a9;file_id file_00000000a0b481f481246cf7bb9efbd6.
- OLC19_Rischio_Rientro_Risultati_20261102.zip:2875586bytes;SHA256f574339c8c7ab25e159e83d8fb55fc4be2dc44bdc0ed06a9fbf96e6b24f4a021;library_file_id libfile_ca4dec18458081919acf77c64b62d8d9.
- OLC19_Report_Rischio_Rientro_20261102.md:library_file_id libfile_c77034f706008191add1a3db4457f354.
- OLC19_Restore_Verification.json:library_file_id libfile_24add6670070819197d10dcd8e28c9b4.
- OLC19_Confronti_20261102.csv:library_file_id libfile_e6da7c99efdc81918b043b3a99cec492.
The sixth successful operation created the folder. Binaries are NOT GitHub release assets. Full checkpoint is autonomous for this experiment from prepared inputs; it does not certify or rebuild all ETF models from raw data. The authoritative preregistration is linked by immutable Git object in the package.

## Decision / remaining roadmap

Keep explicit risk-state and reentry control as research candidates; do not promote3sessions or FAST_LOCK3 as universally best. Keep ORIGINAL,CUM_FIT and contextual candidate parent versions. Do not double-count nested alarm/stop benefit.

This completes the first combined-risk block only.50blocked-context nulls with full nested reselection,preordered quantities andrealintradayfills,data certification,shadow collection and residual-opportunity models are NOT executed in this lot. No background process,live order or main change.
