# V2 / P45 source lock

- ETF Trader V2 source: `AM1975MA/Etf_trader` at commit `2bf07bcda8aa23c3e3cbfa0bb800e3bc038090c4` (source package and MA3 builder under `vendor/etf_trader_v2/`).
- Frozen Stage19 reconstruction and original producer source: `AM1975MA/Trader_selector` branch `research/p45-continuous-posterior-router-20260928` at `bf8f5dc88ad746e795b5cc39028c7aff36c9f97c`. The exact architecture is `v2_stage19_kernel.py`; P43/P44/P45 router implementations are preserved here.
- Reference 149-ETF historical P45: CAGR 46.9632304%, MaxDD -27.0652283%, Sharpe 1.4918386. `REFERENCE_RESULT.json`, parity, and causal audits are diagnostic references only, never input data.
- The historical `run_p45_local.py` has absolute paths to a Stage19 bundle, monthly predictions, and frozen paths from its original research workspace. Its 46.96% run is not independently reproducible from these source files alone until those inputs are rebuilt and their hashes/parity validated.
- The EU120 experiment under `europe120/eu120_retrain/` is a new fit on different raw prices; its outputs cannot be described as a replication of the 149-ETF figure. Read only `AUDITED_RESULT.json` for a completed economic replay.
