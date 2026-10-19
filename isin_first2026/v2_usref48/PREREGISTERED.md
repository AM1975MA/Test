# ETF Trader V2 EUROPE48 with original SPY/HYG/IEF/BIL/SHV, 2026-10-19

## User requested correction
Do NOT replace original ETF Trader V2 USD market references with IMEU, IHYG, EUNH. Instead use genuine original SPY/HYG/IEF USD histories restored unmodified from the archived ETF Trader 149 source OHLCV run 36551650325. Maintain 48 strictly-European underlying ISIN and unrestricted selection at every signal. USD instruments must NEVER be inserted into the Top1/Top2 forecast candidate universe.

## Frozen tests
All simulation outputs are EUR-referenced, 10bps cost per half turnover and original 5.5% stop 0.1% slippage. Run 2021-Feb through 2026-July on the same 1,374 European Open sessions and the exact same 65 ETF model signal dates. Do not use US same-day closing information not available at European Open. Use strict PRIOR US close for model/SPY feature training and USD-to-EUR FX mark; the source risk and V6 routines have their existing one-European-bar lag, with reference price series as of same dated US trading close; output on day T uses T-1 US closes. Ref-date alignment and SHA manifest are audited.

Controls preregistered PRIOR to observing new PnL:
1. **Old learned European scores + old EU market signals + EUR defensive**. Identical portfolio/predictions and cash risk to prior V2 1.6362%, -37.193% and must match at the level 1e-11.
2. **Old learned European scores + true original USD SPY/HYG/IEF refs + same EUR defensive**. Isolates the factor risk/regime change only; NO retraining.
3. **Freshly trained original source Titanium+MA3 with USD SPY prior-close explanatory factor + old European risk signals and EUR defensive**. Isolates predictive-model market-feature change only.
4. **Freshly trained USD SPY model + genuine USD SPY/HYG/IEF risk and V6 + same EUR defensive**. Primary proper comparison: original market reference restored, EU-only positions and EUR defensive sleeve maintained.
5. **Same as 4 except USD BIL/SHV as defensive investments priced in EUR using previous US-close and previous EURUSD FX rate**. This removes the proxy duration risk from the original US defensive sleeve, but *the holdings are no longer 100% European* during risk-off (although Top1 and Top2 always among 48 EU legal fund ISINs). Separate reference, not a pure EU-only portfolio. USD currency exposure included, not falsely labeled a EUR hedge, not broker-executable foreign ETF open bid/ask quote.

Existing USA ETF Trader 149 uses 7 dynamic clusters and 1 bond cash; 48 European cohort uses 5 dynamics + 1 government cohort with the same 48-source clustering and frozen learner hyperparameters; equality to a 149 full run CANNOT be claimed. 48 ETF fund 2026 survivor selection is not PIT; source High/Low derived corrections 49 bars may affect stop price; original vendor raw unchanged. Includes no production modification.

## Audit gates
Original EUR48 V2 exact equity/economics parity, all 65 monthly legal ISIN decisions, all risk/cash scenarios same full 1374 EU sessions, six annual EU48 source-only mature model fits, 48 unique ISIN no US markets eligible, US ref market date asof, source file SHA, FX branch baseline, no positional lookahead, cumulative EUR net NAV.

The result should not be called improvement if it arises from replacing Euro government defensive investments with offshore USD BIL/SHV: that adds economic currency exposure and counterparty/broker restrictions. All 5 results presented together, with final risk sign and result uncertainty, not parameter tuned ex-post.
