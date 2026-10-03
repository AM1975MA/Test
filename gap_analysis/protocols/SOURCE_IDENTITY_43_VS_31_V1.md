# SOURCE_IDENTITY_43_VS_31_V1

Purpose: prove or reject byte-level source identity between the historical ETF_trader Annual V2 implementation underlying the 43.145952% reference and the vendored implementation used by the 31.603995% fresh-data replay.

## Frozen historical source

Repository: `AM1975MA/Etf_trader`  
Commit: `53f5939ab858ece6425e46266bd42b99b8bd1cab`

## Current replay source

Repository: `AM1975MA/Test`  
Branch: `research/evidence-v2`  
Vendored root: `vendor/etf_trader_v2/`

## Files required to match byte-for-byte

- `src/etf_trader/source_only/kernel.py`
- `src/etf_trader/source_only/features.py`
- `src/etf_trader/source_only/models.py`
- `src/etf_trader/source_only/_xgb_worker.py`
- `scripts/build_tit_r_source_only.py`
- `src/etf_trader/ma3/ensemble.py`
- `src/etf_trader/ma3/hybrid_producer.py`
- `src/etf_trader/ma3/producer.py`
- `src/etf_trader/ma3/ddfirst.py`
- `src/etf_trader/ma3/v6.py`

The Stage19 replay kernel is outside the Etf_trader repository and is separately gated to frozen Git blob:

- `vendor/p45/v2_stage19_kernel.py` expected Git blob `364c16f61d1866946827626e0d8f26dab276aca4`

## Existing expected productive blobs

The 31.603995% workflow already fail-closed against these Git blobs:

- kernel.py `045e57996b02d481bd23f6e4dfe53738d43008e5`
- features.py `b7f6520b2b5bc54fdc26178dea839bad8a8fecaf`
- models.py `fc642cce171facfcb92440a7708ee2428f120efe`
- _xgb_worker.py `2b2ebd4d35ff32e88be62edc61a464656f6f7d4b`
- build_tit_r_source_only.py `b06ae7d6960a91aa0c0896dca403f2c6b183467c`
- ensemble.py `4b23fd297df6bfcf71557af9a7aaf7ca96c9a223`
- hybrid_producer.py `acf83f2cee6876c89dfd9948cfbf30889af4c08e`
- producer.py `e691376e3a8e0ec1bd38cc5b85a8ebbfa35d0592`
- ddfirst.py `3794564fdfe8501c2c19e618bc7d1550884aeb53`
- v6.py `6c5d3fd6f54fb5ef5162f4b26d3ef9af2af34701`
- v2_stage19_kernel.py `364c16f61d1866946827626e0d8f26dab276aca4`

## Pass criterion

PASS only if all ten Etf_trader files are byte-identical between the historical commit and the vendored replay copy, and the Stage19 kernel matches its frozen blob. Any difference means source identity is not established and the 43% vs 31.6% data-vintage comparison must remain blocked.
