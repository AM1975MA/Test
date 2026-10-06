# EU120 source and replay

The 120-price-series dataset is imported from the frozen GitHub Actions artifact `eu120-frozen-20260701` (run 36597035280, artifact 11046597169). Its manifest and selected membership were fixed without performance-based selection. Raw ticker CSV files live in `data/eu120/raw_ticker_csv/`.

`vendor/etf_trader_v2/` and `vendor/p45/` preserve the source snapshot used for the research lineage; the historical 46.9632% is a reference on the original 149, not a claim for EU120. The repository's earlier `europe120/vendor_etf_min.zip` is corrupt and must not be used.

Some members are US-listed and others trade outside EUR. Thus the snapshot represents European exposure, not 120 verified EUR-denominated listings. The prior `eu110_universe.csv` is a superseded candidate set; the frozen 120 with its quality gate is authoritative.
