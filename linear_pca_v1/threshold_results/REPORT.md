# Residual variance threshold sensitivity: verified results

Actions38972470169 SUCCESS for both90/99. Original95andfullLINEAR reused.60newfits and6replays only. Artifact ZIP digests checked locally; all6equity paths independently reconciled to reportedCAGR,MaxDD,Sharpe within1e-12.

|Model|MeanCAGR|MeanMaxDD|MeanSharpe|CAGRspan pp|Top1 disagreement|OrderedTop2 disagreement|
|---|---:|---:|---:|---:|---:|---:|
|Full LINEAR|31.6508%|-28.4525%|1.08374|3.2018|20.7523%|52.8740%|
|Residual after90%|26.2927%|-27.1165%|0.94766|1.8342|17.5402%|41.4624%|
|Residual after95%|28.4233%|-29.4616%|1.03330|1.9450|17.5402%|36.1792%|
|Residual after99%|29.4874%|-32.6895%|1.04913|3.1384|21.3018%|38.2502%|

Residual dimensions:96-97at90%,82at95%,43-44at99%. Threshold is input variance, not information/profit share. Each restricted model retrained from zero with original split,standardization,L2 and numerical solver; all other V2layers unchanged. The resulting CAGR is of full V2, not an isolated residual signal.

2021mean:full1.8373%,90residual19.4151%,95residual29.2412%,99residual20.9209%.2023mean:full5.4766%,90residual5.1737%,95residual26.1294%,99residual14.2457%.

No candidate passes original annual-reference adoption gates. These results show tradeoffs and sensitivity, not absence of useful residual information.95improves2021/2023 but underperforms fullLINEAR in2018,2019,2020,2024,2025. The period and threshold study are exploratory; do not choose an ex-post year-by-year winner or claim an optimal threshold. Next mechanism analysis should use saved scores/choices before risk overlays and distinguish common/relative inputs without assuming high variance equals market direction. No new fits are needed for that first attribution.

Sources: https://github.com/AM1975MA/Test/actions/runs/38972470169 and https://github.com/AM1975MA/Test/actions/runs/38971107084 .
Artifacts90:12077946007 SHA25684a7f795bc88a7cac3a7be899bffe1a25d55b2393e2097c8a5502f91e034ed8e.
Artifacts99:12077083797 SHA256c1927c7a00bf81f39b610b021f0b0f994bab8302759522b5d585b3d3c568b8f8.
