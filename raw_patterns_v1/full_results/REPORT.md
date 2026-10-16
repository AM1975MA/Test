# Raw Flatten context: full V2 economic test

Actions38972549492 SUCCESS.90new neural fits,3frozen downloads,2017-2026annualwalk-forward,3canonicalV2replays. Raw-only training provenance,scalers,maturity and saved-parameter inference reconstructed independently without refitting. All3equity paths independently reconciled locally toCAGR,MaxDD,Sharpe within1e-12; artifact ZIP hashes verified.

| Metric | Full LINEAR reference | Flatten context |
|---|---:|---:|
|Mean CAGR|31.6508%|24.7911%|
|Mean MaxDD|-28.4525%|-28.4254%|
|Mean Sharpe|1.08374|0.90614|
|CAGR span|3.2018pp|7.2207pp|
|Top1 download disagreement|20.7523%|22.4007%|
|Ordered Top2 disagreement|52.8740%|39.2646%|

CAGRr1/r2/r3:20.9981%/25.1563%/28.2188%.2021mean-11.9787%,2023mean-16.0698%. At least one seed disagrees onTop1in95.8702%of mature date/download queries. Seed disagreement and download disagreement measure different effects. Three download vintages are correlated revisions of one market.

Decision: do not promote this tested configuration; failsCAGR/Sharpe/stability preservation gates. This is not proof that every neural architecture fails. Budget was fixed at20epochs/patience10, not a stationary-optimum certificate. OriginalLINEAR125uses different features/history/validation policy, so comparison is between full recipes, not architecture-only. Only Compact21was replaced; otherV2layers and risk/execution unchanged,Opportunityexcluded. No production change.

Models artifact12078015009 SHA256262429d2eb04a10633da7510dc51d3e0ba97e4d4aeeafa05200d98b2bebcd26c.
Comparison artifact12076604741 SHA256e751e4a12485db7d51734274ebef6571a9fb809aaef26f9ac6f072fb057860c7.
Source: https://github.com/AM1975MA/Test/actions/runs/38972549492 .
